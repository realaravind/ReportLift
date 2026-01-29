"""Tests for Ollama service including OllamaClient, CircuitBreaker, and health checks."""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from app.services.ollama_service import (
    OllamaConfig,
    OllamaGenerateRequest,
    OllamaGenerateResponse,
    OllamaMetrics,
    OllamaResult,
    OllamaErrorCode,
    CircuitState,
    CircuitBreaker,
    OllamaHealthResult,
    OllamaClient,
    check_ollama_health,
    check_ollama_health_async,
    get_ollama_client,
)


class TestOllamaConfig:
    """Tests for OllamaConfig schema."""

    def test_default_values(self):
        """Test default configuration values."""
        config = OllamaConfig()
        assert config.host_url == "http://localhost:11434"
        assert config.model == "codellama:13b"
        assert config.timeout == 60
        assert config.enabled is True
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff == 2.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = OllamaConfig(
            host_url="http://192.168.1.10:11434",
            model="llama2:7b",
            timeout=120,
            enabled=False,
            max_retries=5,
            retry_delay=0.5,
            retry_backoff=1.5,
        )
        assert config.host_url == "http://192.168.1.10:11434"
        assert config.model == "llama2:7b"
        assert config.timeout == 120
        assert config.enabled is False
        assert config.max_retries == 5
        assert config.retry_delay == 0.5
        assert config.retry_backoff == 1.5


class TestOllamaGenerateRequest:
    """Tests for OllamaGenerateRequest schema."""

    def test_basic_request(self):
        """Test creating a basic generate request."""
        request = OllamaGenerateRequest(
            model="codellama:13b",
            prompt="Convert this SQL to Snowflake",
        )
        assert request.model == "codellama:13b"
        assert request.prompt == "Convert this SQL to Snowflake"
        assert request.stream is False
        assert "temperature" in request.options
        assert request.options["temperature"] == 0.2

    def test_custom_options(self):
        """Test custom generation options."""
        request = OllamaGenerateRequest(
            model="llama2",
            prompt="Test prompt",
            stream=True,
            options={"temperature": 0.8, "num_predict": 4096},
        )
        assert request.stream is True
        assert request.options["temperature"] == 0.8
        assert request.options["num_predict"] == 4096


class TestOllamaGenerateResponse:
    """Tests for OllamaGenerateResponse schema."""

    def test_minimal_response(self):
        """Test minimal response fields."""
        response = OllamaGenerateResponse(
            model="codellama:13b",
            response="SELECT * FROM table",
            done=True,
        )
        assert response.model == "codellama:13b"
        assert response.response == "SELECT * FROM table"
        assert response.done is True
        assert response.total_duration is None
        assert response.prompt_eval_count is None

    def test_full_response(self):
        """Test response with all fields."""
        response = OllamaGenerateResponse(
            model="codellama:13b",
            response="SELECT * FROM table",
            done=True,
            created_at="2026-01-25T10:00:00Z",
            context=[1, 2, 3],
            total_duration=5000000000,
            load_duration=1000000000,
            prompt_eval_count=100,
            eval_count=50,
        )
        assert response.total_duration == 5000000000
        assert response.prompt_eval_count == 100
        assert response.eval_count == 50


class TestOllamaMetrics:
    """Tests for OllamaMetrics schema."""

    def test_success_metrics(self):
        """Test metrics for successful operation."""
        metrics = OllamaMetrics(
            request_time_ms=3500,
            prompt_tokens=100,
            completion_tokens=50,
            total_duration_ms=3200,
            success=True,
            retry_count=0,
        )
        assert metrics.request_time_ms == 3500
        assert metrics.prompt_tokens == 100
        assert metrics.completion_tokens == 50
        assert metrics.success is True
        assert metrics.retry_count == 0

    def test_failure_metrics(self):
        """Test metrics for failed operation."""
        metrics = OllamaMetrics(
            request_time_ms=5000,
            success=False,
            retry_count=3,
        )
        assert metrics.success is False
        assert metrics.retry_count == 3
        assert metrics.prompt_tokens is None


class TestOllamaResult:
    """Tests for OllamaResult schema."""

    def test_success_result(self):
        """Test successful result."""
        result = OllamaResult(
            success=True,
            response="Generated SQL code",
            metrics=OllamaMetrics(
                request_time_ms=1000,
                success=True,
            ),
        )
        assert result.success is True
        assert result.response == "Generated SQL code"
        assert result.error_code is None

    def test_error_result(self):
        """Test error result."""
        result = OllamaResult(
            success=False,
            error_code=OllamaErrorCode.CONNECTION_ERROR,
            error_message="Unable to connect to Ollama server",
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.CONNECTION_ERROR
        assert result.response is None


class TestCircuitBreaker:
    """Tests for CircuitBreaker implementation."""

    def test_initial_state(self):
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.can_execute() is True

    def test_record_success_resets_failures(self):
        """Test that success resets failure count."""
        cb = CircuitBreaker()
        cb.failure_count = 3
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_failures_open_circuit(self):
        """Test that enough failures open the circuit."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_circuit_recovery_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Simulate time passing
        cb.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=2)

        # Should transition to half-open
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed(self):
        """Test circuit closes after 3 successes in half-open state."""
        cb = CircuitBreaker(failure_threshold=2)
        cb.state = CircuitState.HALF_OPEN
        cb.success_count = 0

        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        """Test circuit reopens on failure in half-open state."""
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_get_status(self):
        """Test get_status returns correct information."""
        cb = CircuitBreaker()
        cb.failure_count = 2
        cb.last_failure_time = datetime.now(timezone.utc)

        status = cb.get_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 2
        assert status["last_failure_time"] is not None


class TestOllamaHealthResult:
    """Tests for OllamaHealthResult dataclass."""

    def test_success_result(self):
        """Test successful health result."""
        result = OllamaHealthResult(
            success=True,
            message="Connected to Ollama",
            model_available=True,
            models_found=["codellama:13b", "llama2:7b"],
            response_time_ms=150,
        )
        assert result.success is True
        assert result.model_available is True
        assert len(result.models_found) == 2

    def test_failure_result(self):
        """Test failed health result."""
        result = OllamaHealthResult(
            success=False,
            message="Connection refused",
            error_code=OllamaErrorCode.CONNECTION_ERROR,
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.CONNECTION_ERROR


class TestCheckOllamaHealth:
    """Tests for synchronous check_ollama_health function."""

    def test_disabled_returns_disabled_error(self):
        """Test disabled Ollama returns DISABLED error."""
        result = check_ollama_health(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=False,
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.DISABLED

    @patch("httpx.Client")
    def test_connection_success(self, mock_client_class):
        """Test successful connection."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "codellama:13b"}]
        }
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = check_ollama_health(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=True,
        )
        assert result.success is True
        assert result.model_available is True

    @patch("httpx.Client")
    def test_model_not_found(self, mock_client_class):
        """Test model not available."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama2:7b"}]
        }
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = check_ollama_health(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=True,
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.MODEL_NOT_FOUND
        assert result.model_available is False


class TestOllamaClient:
    """Tests for OllamaClient class."""

    def test_init_with_defaults(self):
        """Test client initialization with default config."""
        client = OllamaClient()
        assert client.config.host_url == "http://localhost:11434"
        assert client.config.model == "codellama:13b"

    def test_init_with_custom_config(self):
        """Test client initialization with custom config."""
        config = OllamaConfig(
            host_url="http://192.168.1.10:11434",
            model="llama2:7b",
        )
        client = OllamaClient(config)
        assert client.config.host_url == "http://192.168.1.10:11434"
        assert client.config.model == "llama2:7b"

    @pytest.mark.asyncio
    async def test_is_available_disabled(self):
        """Test is_available returns False when disabled."""
        config = OllamaConfig(enabled=False)
        client = OllamaClient(config)
        result = await client.is_available()
        assert result is False
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_disabled(self):
        """Test generate returns error when disabled."""
        config = OllamaConfig(enabled=False)
        client = OllamaClient(config)
        result = await client.generate("Test prompt")
        assert result.success is False
        assert result.error_code == OllamaErrorCode.DISABLED
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_circuit_open(self):
        """Test generate returns error when circuit is open."""
        config = OllamaConfig(enabled=True)
        client = OllamaClient(config)

        # Force circuit open
        client._circuit_breaker.state = CircuitState.OPEN
        client._circuit_breaker.last_failure_time = datetime.now(timezone.utc)

        result = await client.generate("Test prompt")
        assert result.success is False
        assert result.error_code == OllamaErrorCode.CIRCUIT_OPEN
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        config = OllamaConfig(enabled=True)
        client = OllamaClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "codellama:13b",
            "response": "SELECT * FROM users",
            "done": True,
            "total_duration": 5000000000,
            "prompt_eval_count": 100,
            "eval_count": 50,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await client.generate("Convert to Snowflake SQL")

        assert result.success is True
        assert result.response == "SELECT * FROM users"
        assert result.metrics is not None
        assert result.metrics.prompt_tokens == 100
        assert result.metrics.completion_tokens == 50
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_timeout(self):
        """Test timeout handling."""
        config = OllamaConfig(enabled=True, timeout=1, max_retries=1)
        client = OllamaClient(config)

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_get_client.return_value = mock_client

            result = await client.generate("Test prompt")

        assert result.success is False
        assert result.error_code == OllamaErrorCode.TIMEOUT
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_connection_error(self):
        """Test connection error handling."""
        config = OllamaConfig(enabled=True, max_retries=1)
        client = OllamaClient(config)

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_get_client.return_value = mock_client

            result = await client.generate("Test prompt")

        assert result.success is False
        assert result.error_code == OllamaErrorCode.CONNECTION_ERROR
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_model_not_found(self):
        """Test model not found error handling."""
        config = OllamaConfig(enabled=True, max_retries=1)
        client = OllamaClient(config)

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            error = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            result = await client.generate("Test prompt")

        assert result.success is False
        assert result.error_code == OllamaErrorCode.MODEL_NOT_FOUND
        await client.close()

    @pytest.mark.asyncio
    async def test_check_model_available_caching(self):
        """Test model availability caching."""
        config = OllamaConfig(enabled=True)
        client = OllamaClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "codellama:13b"}]
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            # First call - should hit API
            result1 = await client.check_model_available()
            assert result1 is True
            assert mock_client.get.call_count == 1

            # Second call - should use cache
            result2 = await client.check_model_available()
            assert result2 is True
            assert mock_client.get.call_count == 1  # Still 1

            # Force refresh - should hit API again
            result3 = await client.check_model_available(force_refresh=True)
            assert result3 is True
            assert mock_client.get.call_count == 2

        await client.close()

    def test_get_circuit_breaker_status(self):
        """Test getting circuit breaker status."""
        client = OllamaClient()
        status = client.get_circuit_breaker_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 0

    def test_reset_circuit_breaker(self):
        """Test resetting circuit breaker."""
        client = OllamaClient()
        client._circuit_breaker.state = CircuitState.OPEN
        client._circuit_breaker.failure_count = 5

        client.reset_circuit_breaker()

        assert client._circuit_breaker.state == CircuitState.CLOSED
        assert client._circuit_breaker.failure_count == 0


class TestGetOllamaClient:
    """Tests for get_ollama_client factory function."""

    def test_returns_singleton(self):
        """Test that function returns singleton instance."""
        # Reset global client
        import app.services.ollama_service as service
        service._ollama_client = None

        client1 = get_ollama_client()
        client2 = get_ollama_client()
        assert client1 is client2

    def test_config_change_creates_new_client(self):
        """Test that config change creates new client."""
        import app.services.ollama_service as service
        service._ollama_client = None

        config1 = OllamaConfig(host_url="http://localhost:11434")
        config2 = OllamaConfig(host_url="http://192.168.1.10:11434")

        client1 = get_ollama_client(config1)
        client2 = get_ollama_client(config2)

        assert client1 is not client2
        assert client2.config.host_url == "http://192.168.1.10:11434"


@pytest.mark.asyncio
class TestCheckOllamaHealthAsync:
    """Tests for async check_ollama_health_async function."""

    async def test_disabled_returns_disabled_error(self):
        """Test disabled Ollama returns DISABLED error."""
        result = await check_ollama_health_async(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=False,
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.DISABLED

    @patch("httpx.AsyncClient")
    async def test_connection_success(self, mock_client_class):
        """Test successful async connection."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "codellama:13b"}]
        }
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await check_ollama_health_async(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=True,
        )
        assert result.success is True
        assert result.model_available is True

    @patch("httpx.AsyncClient")
    async def test_timeout_error(self, mock_client_class):
        """Test timeout handling."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await check_ollama_health_async(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=True,
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.TIMEOUT

    @patch("httpx.AsyncClient")
    async def test_connection_error(self, mock_client_class):
        """Test connection error handling."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await check_ollama_health_async(
            host_url="http://localhost:11434",
            model_name="codellama:13b",
            enabled=True,
        )
        assert result.success is False
        assert result.error_code == OllamaErrorCode.CONNECTION_ERROR
