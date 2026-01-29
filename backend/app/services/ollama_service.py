"""Ollama Service for health checking and AI operations.

This service handles communication with the Ollama API, including:
- Health checking to verify service availability
- Model availability verification
- Text generation with retry logic
- Circuit breaker for reliability
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default timeout for Ollama API calls (seconds)
DEFAULT_TIMEOUT = 60
DEFAULT_HEALTH_TIMEOUT = 10

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_BACKOFF = 2.0


class OllamaErrorCode(str, Enum):
    """Error codes for Ollama connection issues."""

    CONNECTION_ERROR = "CONNECTION_ERROR"
    TIMEOUT = "TIMEOUT"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    SERVER_ERROR = "SERVER_ERROR"
    DISABLED = "DISABLED"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    UNKNOWN = "UNKNOWN"


# Pydantic models for Ollama API
class OllamaConfig(BaseModel):
    """Configuration for Ollama client."""

    host_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model: str = Field(default="codellama:13b", description="Model to use for generation")
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Request timeout in seconds")
    enabled: bool = Field(default=True, description="Whether Ollama is enabled")
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, description="Maximum retry attempts")
    retry_delay: float = Field(default=DEFAULT_RETRY_DELAY, description="Initial retry delay")
    retry_backoff: float = Field(default=DEFAULT_RETRY_BACKOFF, description="Retry backoff multiplier")


class OllamaGenerateRequest(BaseModel):
    """Request payload for Ollama generate endpoint."""

    model: str = Field(description="Model name")
    prompt: str = Field(description="Prompt text")
    stream: bool = Field(default=False, description="Whether to stream response")
    options: dict[str, Any] = Field(
        default_factory=lambda: {"temperature": 0.2, "num_predict": 2048},
        description="Generation options",
    )


class OllamaGenerateResponse(BaseModel):
    """Response from Ollama generate endpoint."""

    model: str = Field(description="Model used")
    response: str = Field(description="Generated text")
    done: bool = Field(description="Whether generation is complete")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    context: list[int] | None = Field(default=None, description="Context tokens")
    total_duration: int | None = Field(default=None, description="Total duration in nanoseconds")
    load_duration: int | None = Field(default=None, description="Model load duration in nanoseconds")
    prompt_eval_count: int | None = Field(default=None, description="Prompt tokens evaluated")
    eval_count: int | None = Field(default=None, description="Response tokens generated")


class OllamaMetrics(BaseModel):
    """Metrics from an Ollama operation."""

    request_time_ms: int = Field(description="Request duration in milliseconds")
    prompt_tokens: int | None = Field(default=None, description="Prompt token count")
    completion_tokens: int | None = Field(default=None, description="Completion token count")
    total_duration_ms: int | None = Field(default=None, description="Total processing duration")
    success: bool = Field(description="Whether operation succeeded")
    retry_count: int = Field(default=0, description="Number of retries needed")


class OllamaResult(BaseModel):
    """Result of an Ollama generation operation."""

    success: bool = Field(description="Whether operation succeeded")
    response: str | None = Field(default=None, description="Generated response text")
    error_code: OllamaErrorCode | None = Field(default=None, description="Error code if failed")
    error_message: str | None = Field(default=None, description="Error message if failed")
    metrics: OllamaMetrics | None = Field(default=None, description="Operation metrics")
    raw_response: OllamaGenerateResponse | None = Field(default=None, description="Raw API response")


# Circuit Breaker Implementation
class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, skip calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for Ollama service reliability.

    Prevents cascading failures by opening the circuit when
    too many failures occur, allowing the system to recover.
    """

    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: datetime | None = None
    success_count: int = 0

    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Need 3 successes to close
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info("Circuit breaker closed - service recovered")
        elif self.state == CircuitState.CLOSED:
            self.success_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        self.success_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker reopened - recovery failed")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened - %d failures exceeded threshold",
                self.failure_count,
            )

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker half-open - testing recovery")
                    return True
            return False

        # HALF_OPEN - allow one test call
        return True

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


@dataclass
class OllamaHealthResult:
    """Result of an Ollama health check."""

    success: bool
    message: str
    model_available: bool = False
    models_found: list[str] | None = None
    response_time_ms: int = 0
    error_code: OllamaErrorCode | None = None


def check_ollama_health(
    host_url: str,
    model_name: str,
    enabled: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> OllamaHealthResult:
    """Check health of Ollama service.

    Verifies that the Ollama server is accessible and the configured
    model is available.

    Args:
        host_url: Ollama server URL (e.g., http://localhost:11434)
        model_name: Expected model name to verify availability
        enabled: Whether Ollama is enabled in configuration
        timeout: Request timeout in seconds

    Returns:
        OllamaHealthResult with connection status and details
    """
    start_time = time.time()

    # If Ollama is disabled, return not configured status
    if not enabled:
        return OllamaHealthResult(
            success=False,
            message="Ollama is disabled",
            error_code=OllamaErrorCode.DISABLED,
        )

    try:
        # Call the Ollama API to list available models
        api_url = f"{host_url.rstrip('/')}/api/tags"
        logger.info("Checking Ollama health at: %s", api_url)

        with httpx.Client(timeout=timeout) as client:
            response = client.get(api_url)

        response_time_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if the configured model is available
            # Model names can have tags like "codellama:13b" or just "codellama"
            model_available = any(
                model_name == m or model_name.split(":")[0] == m.split(":")[0]
                for m in model_names
            )

            if model_available:
                return OllamaHealthResult(
                    success=True,
                    message=f"Connected to Ollama - model '{model_name}' available",
                    model_available=True,
                    models_found=model_names,
                    response_time_ms=response_time_ms,
                )
            else:
                return OllamaHealthResult(
                    success=False,
                    message=f"Model '{model_name}' not found on Ollama server",
                    model_available=False,
                    models_found=model_names,
                    response_time_ms=response_time_ms,
                    error_code=OllamaErrorCode.MODEL_NOT_FOUND,
                )

        elif response.status_code >= 500:
            logger.error("Ollama server error: %d", response.status_code)
            return OllamaHealthResult(
                success=False,
                message=f"Ollama server error (HTTP {response.status_code})",
                response_time_ms=response_time_ms,
                error_code=OllamaErrorCode.SERVER_ERROR,
            )

        else:
            logger.warning("Unexpected Ollama response: %d", response.status_code)
            return OllamaHealthResult(
                success=False,
                message=f"Unexpected response from Ollama (HTTP {response.status_code})",
                response_time_ms=response_time_ms,
                error_code=OllamaErrorCode.UNKNOWN,
            )

    except httpx.TimeoutException:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("Ollama connection timed out after %dms", response_time_ms)
        return OllamaHealthResult(
            success=False,
            message=f"Connection timed out after {timeout} seconds",
            response_time_ms=response_time_ms,
            error_code=OllamaErrorCode.TIMEOUT,
        )

    except httpx.ConnectError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.warning("Ollama connection error: %s", str(e))
        return OllamaHealthResult(
            success=False,
            message="Unable to connect to Ollama server",
            response_time_ms=response_time_ms,
            error_code=OllamaErrorCode.CONNECTION_ERROR,
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.exception("Unexpected error checking Ollama health: %s", str(e))
        return OllamaHealthResult(
            success=False,
            message=f"Unexpected error: {str(e)}",
            response_time_ms=response_time_ms,
            error_code=OllamaErrorCode.UNKNOWN,
        )


# Type variable for retry decorator
T = TypeVar("T")


class OllamaClient:
    """Async client for Ollama API with retry logic and circuit breaker.

    Provides reliable communication with the Ollama service including:
    - Async HTTP requests with configurable timeout
    - Exponential backoff retry logic
    - Circuit breaker for fault tolerance
    - Model availability verification with caching
    - Metrics collection for monitoring
    """

    def __init__(self, config: OllamaConfig | None = None):
        """Initialize the Ollama client.

        Args:
            config: OllamaConfig instance. If None, uses defaults.
        """
        self.config = config or OllamaConfig()
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker()
        self._model_cache: dict[str, Any] = {}
        self._model_cache_time: datetime | None = None
        self._model_cache_ttl = 300  # 5 minutes cache

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout, connect=10.0),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _retry_with_backoff(
        self,
        func: Callable[[], T],
        operation_name: str = "operation",
    ) -> T:
        """Execute a function with retry logic and exponential backoff.

        Args:
            func: Async callable to execute
            operation_name: Name for logging purposes

        Returns:
            Result from the function

        Raises:
            The last exception if all retries fail
        """
        last_exception: Exception | None = None
        delay = self.config.retry_delay

        for attempt in range(self.config.max_retries):
            try:
                return await func()
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        "Ollama %s attempt %d/%d failed: %s. Retrying in %.1fs",
                        operation_name,
                        attempt + 1,
                        self.config.max_retries,
                        str(e),
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= self.config.retry_backoff
            except httpx.HTTPStatusError as e:
                last_exception = e
                # Only retry on 5xx errors
                if e.response.status_code >= 500:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(
                            "Ollama %s attempt %d/%d got %d. Retrying in %.1fs",
                            operation_name,
                            attempt + 1,
                            self.config.max_retries,
                            e.response.status_code,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        delay *= self.config.retry_backoff
                else:
                    # Don't retry 4xx errors
                    raise

        # All retries failed
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Ollama {operation_name} failed after {self.config.max_retries} retries")

    async def is_available(self) -> bool:
        """Check if Ollama service is reachable.

        Returns:
            True if Ollama is responding, False otherwise
        """
        if not self.config.enabled:
            return False

        try:
            client = await self._get_client()
            url = f"{self.config.host_url.rstrip('/')}/api/tags"
            response = await client.get(url, timeout=DEFAULT_HEALTH_TIMEOUT)
            return response.status_code == 200
        except Exception as e:
            logger.debug("Ollama availability check failed: %s", str(e))
            return False

    async def check_model_available(self, force_refresh: bool = False) -> bool:
        """Verify the configured model is available.

        Args:
            force_refresh: If True, bypass cache and check directly

        Returns:
            True if model is available, False otherwise
        """
        if not self.config.enabled:
            return False

        # Check cache
        now = datetime.now(timezone.utc)
        if (
            not force_refresh
            and self._model_cache_time
            and (now - self._model_cache_time).total_seconds() < self._model_cache_ttl
        ):
            return self._model_cache.get("available", False)

        try:
            client = await self._get_client()
            url = f"{self.config.host_url.rstrip('/')}/api/tags"
            response = await client.get(url, timeout=DEFAULT_HEALTH_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Check if configured model exists
                model_available = any(
                    self.config.model == m or self.config.model.split(":")[0] == m.split(":")[0]
                    for m in model_names
                )

                # Update cache
                self._model_cache = {
                    "available": model_available,
                    "models": model_names,
                }
                self._model_cache_time = now

                return model_available

            return False

        except Exception as e:
            logger.warning("Model availability check failed: %s", str(e))
            return False

    async def get_available_models(self) -> list[str]:
        """Get list of available models from Ollama.

        Returns:
            List of model names
        """
        await self.check_model_available()
        return self._model_cache.get("models", [])

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **options: Any,
    ) -> OllamaResult:
        """Generate text completion using Ollama.

        Args:
            prompt: The prompt text
            model: Model to use (defaults to config model)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **options: Additional Ollama options

        Returns:
            OllamaResult with success status and response
        """
        start_time = time.time()
        retry_count = 0

        # Check if Ollama is enabled
        if not self.config.enabled:
            return OllamaResult(
                success=False,
                error_code=OllamaErrorCode.DISABLED,
                error_message="Ollama is disabled in configuration",
            )

        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            elapsed_since_failure = None
            if self._circuit_breaker.last_failure_time:
                elapsed_since_failure = (
                    datetime.now(timezone.utc) - self._circuit_breaker.last_failure_time
                ).total_seconds()

            return OllamaResult(
                success=False,
                error_code=OllamaErrorCode.CIRCUIT_OPEN,
                error_message=(
                    f"Circuit breaker is open. "
                    f"Recovery in {max(0, self._circuit_breaker.recovery_timeout - (elapsed_since_failure or 0)):.0f}s"
                ),
            )

        # Prepare request
        request_model = model or self.config.model
        request_options = {
            "temperature": temperature,
            "num_predict": max_tokens,
            **options,
        }

        request_data = OllamaGenerateRequest(
            model=request_model,
            prompt=prompt,
            stream=False,
            options=request_options,
        )

        async def make_request() -> httpx.Response:
            nonlocal retry_count
            retry_count += 1
            client = await self._get_client()
            url = f"{self.config.host_url.rstrip('/')}/api/generate"
            response = await client.post(
                url,
                json=request_data.model_dump(),
            )
            response.raise_for_status()
            return response

        try:
            # Execute with retry
            response = await self._retry_with_backoff(make_request, "generate")

            # Parse response
            response_time_ms = int((time.time() - start_time) * 1000)
            response_data = response.json()

            # Validate response format
            if "response" not in response_data:
                self._circuit_breaker.record_failure()
                return OllamaResult(
                    success=False,
                    error_code=OllamaErrorCode.INVALID_RESPONSE,
                    error_message="Response missing 'response' field",
                    metrics=OllamaMetrics(
                        request_time_ms=response_time_ms,
                        success=False,
                        retry_count=retry_count - 1,
                    ),
                )

            # Create response object
            ollama_response = OllamaGenerateResponse(
                model=response_data.get("model", request_model),
                response=response_data["response"],
                done=response_data.get("done", True),
                created_at=response_data.get("created_at"),
                context=response_data.get("context"),
                total_duration=response_data.get("total_duration"),
                load_duration=response_data.get("load_duration"),
                prompt_eval_count=response_data.get("prompt_eval_count"),
                eval_count=response_data.get("eval_count"),
            )

            # Calculate metrics
            total_duration_ms = None
            if ollama_response.total_duration:
                total_duration_ms = ollama_response.total_duration // 1_000_000  # ns to ms

            metrics = OllamaMetrics(
                request_time_ms=response_time_ms,
                prompt_tokens=ollama_response.prompt_eval_count,
                completion_tokens=ollama_response.eval_count,
                total_duration_ms=total_duration_ms,
                success=True,
                retry_count=retry_count - 1,
            )

            # Log success
            logger.info(
                "Ollama generation completed",
                extra={
                    "event": "ollama_request",
                    "model": request_model,
                    "prompt_length": len(prompt),
                    "response_length": len(ollama_response.response),
                    "duration_ms": response_time_ms,
                    "tokens_prompt": ollama_response.prompt_eval_count,
                    "tokens_completion": ollama_response.eval_count,
                    "success": True,
                    "retries": retry_count - 1,
                },
            )

            # Record success in circuit breaker
            self._circuit_breaker.record_success()

            return OllamaResult(
                success=True,
                response=ollama_response.response,
                metrics=metrics,
                raw_response=ollama_response,
            )

        except httpx.TimeoutException:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._circuit_breaker.record_failure()
            logger.warning(
                "Ollama request timed out after %dms",
                response_time_ms,
                extra={
                    "event": "ollama_request",
                    "model": request_model,
                    "success": False,
                    "error": "timeout",
                    "retries": retry_count - 1,
                },
            )
            return OllamaResult(
                success=False,
                error_code=OllamaErrorCode.TIMEOUT,
                error_message=f"Request timed out after {self.config.timeout}s",
                metrics=OllamaMetrics(
                    request_time_ms=response_time_ms,
                    success=False,
                    retry_count=retry_count - 1,
                ),
            )

        except httpx.ConnectError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._circuit_breaker.record_failure()
            logger.warning(
                "Ollama connection error: %s",
                str(e),
                extra={
                    "event": "ollama_request",
                    "model": request_model,
                    "success": False,
                    "error": "connection",
                    "retries": retry_count - 1,
                },
            )
            return OllamaResult(
                success=False,
                error_code=OllamaErrorCode.CONNECTION_ERROR,
                error_message="Unable to connect to Ollama server",
                metrics=OllamaMetrics(
                    request_time_ms=response_time_ms,
                    success=False,
                    retry_count=retry_count - 1,
                ),
            )

        except httpx.HTTPStatusError as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Check for model not found (typically 404)
            if e.response.status_code == 404:
                error_code = OllamaErrorCode.MODEL_NOT_FOUND
                error_message = f"Model '{request_model}' not found. Install it with: ollama pull {request_model}"
            elif e.response.status_code >= 500:
                self._circuit_breaker.record_failure()
                error_code = OllamaErrorCode.SERVER_ERROR
                error_message = f"Ollama server error (HTTP {e.response.status_code})"
            else:
                error_code = OllamaErrorCode.UNKNOWN
                error_message = f"HTTP error: {e.response.status_code}"

            logger.warning(
                "Ollama HTTP error: %s",
                error_message,
                extra={
                    "event": "ollama_request",
                    "model": request_model,
                    "success": False,
                    "status_code": e.response.status_code,
                    "retries": retry_count - 1,
                },
            )

            return OllamaResult(
                success=False,
                error_code=error_code,
                error_message=error_message,
                metrics=OllamaMetrics(
                    request_time_ms=response_time_ms,
                    success=False,
                    retry_count=retry_count - 1,
                ),
            )

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._circuit_breaker.record_failure()
            logger.exception(
                "Unexpected error during Ollama request: %s",
                str(e),
                extra={
                    "event": "ollama_request",
                    "model": request_model,
                    "success": False,
                    "error": str(e),
                    "retries": retry_count - 1,
                },
            )
            return OllamaResult(
                success=False,
                error_code=OllamaErrorCode.UNKNOWN,
                error_message=f"Unexpected error: {str(e)}",
                metrics=OllamaMetrics(
                    request_time_ms=response_time_ms,
                    success=False,
                    retry_count=retry_count - 1,
                ),
            )

    def get_circuit_breaker_status(self) -> dict:
        """Get the current circuit breaker status.

        Returns:
            Dictionary with circuit breaker state and metrics
        """
        return self._circuit_breaker.get_status()

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._circuit_breaker.state = CircuitState.CLOSED
        self._circuit_breaker.failure_count = 0
        self._circuit_breaker.success_count = 0
        self._circuit_breaker.last_failure_time = None
        logger.info("Circuit breaker manually reset")


# Global client instance
_ollama_client: OllamaClient | None = None


def get_ollama_client(config: OllamaConfig | None = None) -> OllamaClient:
    """Get or create the global Ollama client instance.

    Args:
        config: Optional configuration. If provided and different
               from current config, creates new client.

    Returns:
        OllamaClient instance
    """
    global _ollama_client

    if _ollama_client is None:
        _ollama_client = OllamaClient(config)
    elif config is not None:
        # Check if config changed
        current_config = _ollama_client.config
        if (
            current_config.host_url != config.host_url
            or current_config.model != config.model
            or current_config.enabled != config.enabled
        ):
            # Config changed, create new client
            _ollama_client = OllamaClient(config)

    return _ollama_client


async def check_ollama_health_async(
    host_url: str,
    model_name: str,
    enabled: bool = True,
    timeout: int = DEFAULT_HEALTH_TIMEOUT,
) -> OllamaHealthResult:
    """Async version of check_ollama_health.

    Args:
        host_url: Ollama server URL
        model_name: Model to verify
        enabled: Whether Ollama is enabled
        timeout: Request timeout in seconds

    Returns:
        OllamaHealthResult with connection status
    """
    start_time = time.time()

    if not enabled:
        return OllamaHealthResult(
            success=False,
            message="Ollama is disabled",
            error_code=OllamaErrorCode.DISABLED,
        )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            api_url = f"{host_url.rstrip('/')}/api/tags"
            response = await client.get(api_url)

        response_time_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            model_available = any(
                model_name == m or model_name.split(":")[0] == m.split(":")[0]
                for m in model_names
            )

            if model_available:
                return OllamaHealthResult(
                    success=True,
                    message=f"Connected to Ollama - model '{model_name}' available",
                    model_available=True,
                    models_found=model_names,
                    response_time_ms=response_time_ms,
                )
            else:
                return OllamaHealthResult(
                    success=False,
                    message=f"Model '{model_name}' not found on Ollama server",
                    model_available=False,
                    models_found=model_names,
                    response_time_ms=response_time_ms,
                    error_code=OllamaErrorCode.MODEL_NOT_FOUND,
                )

        elif response.status_code >= 500:
            return OllamaHealthResult(
                success=False,
                message=f"Ollama server error (HTTP {response.status_code})",
                response_time_ms=response_time_ms,
                error_code=OllamaErrorCode.SERVER_ERROR,
            )
        else:
            return OllamaHealthResult(
                success=False,
                message=f"Unexpected response from Ollama (HTTP {response.status_code})",
                response_time_ms=response_time_ms,
                error_code=OllamaErrorCode.UNKNOWN,
            )

    except httpx.TimeoutException:
        response_time_ms = int((time.time() - start_time) * 1000)
        return OllamaHealthResult(
            success=False,
            message=f"Connection timed out after {timeout} seconds",
            response_time_ms=response_time_ms,
            error_code=OllamaErrorCode.TIMEOUT,
        )

    except httpx.ConnectError:
        response_time_ms = int((time.time() - start_time) * 1000)
        return OllamaHealthResult(
            success=False,
            message="Unable to connect to Ollama server",
            response_time_ms=response_time_ms,
            error_code=OllamaErrorCode.CONNECTION_ERROR,
        )

    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.exception("Unexpected error checking Ollama health: %s", str(e))
        return OllamaHealthResult(
            success=False,
            message=f"Unexpected error: {str(e)}",
            response_time_ms=response_time_ms,
            error_code=OllamaErrorCode.UNKNOWN,
        )
