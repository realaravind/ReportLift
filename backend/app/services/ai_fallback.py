"""AI Fallback Service for Graceful Degradation.

This service manages AI availability checking, fallback logic, and
tracking for when Ollama is unavailable or disabled.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.services.ollama_service import OllamaClient, get_ollama_client

logger = logging.getLogger(__name__)


class AIStatus(str, Enum):
    """AI service status."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class ConversionMethod(str, Enum):
    """Method used for conversion."""

    RULE_BASED = "rule_based"
    AI_ASSISTED = "ai_assisted"
    AI_FALLBACK = "ai_fallback"  # AI was enabled but unavailable
    MANUAL = "manual"  # Flagged for manual conversion


class AIStatusResponse(BaseModel):
    """Response schema for AI status."""

    enabled: bool = Field(description="Whether AI is enabled in settings")
    status: AIStatus = Field(description="Current AI status")
    last_available: datetime | None = Field(default=None, description="Last successful connection")
    last_checked: datetime | None = Field(default=None, description="Last availability check")
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    circuit_breaker_state: str | None = Field(default=None, description="Circuit breaker state")
    model_name: str | None = Field(default=None, description="Configured model name")
    message: str = Field(description="Human-readable status message")


class ConversionMethodBreakdown(BaseModel):
    """Breakdown of conversion methods used."""

    rule_based_count: int = Field(default=0, description="Rule-based conversions")
    ai_assisted_count: int = Field(default=0, description="AI-assisted conversions")
    ai_fallback_count: int = Field(default=0, description="AI fallback conversions")
    manual_count: int = Field(default=0, description="Manual conversions required")
    total_count: int = Field(default=0, description="Total conversions")

    @property
    def ai_usage_percentage(self) -> float:
        """Percentage of conversions using AI."""
        if self.total_count == 0:
            return 0.0
        return round((self.ai_assisted_count / self.total_count) * 100, 1)

    @property
    def fallback_percentage(self) -> float:
        """Percentage of conversions that used fallback."""
        if self.total_count == 0:
            return 0.0
        return round((self.ai_fallback_count / self.total_count) * 100, 1)


class FallbackEvent(BaseModel):
    """Log entry for a fallback event."""

    event: str = Field(default="ai_fallback", description="Event type")
    conversion_id: str | None = Field(default=None, description="Conversion ID")
    item_name: str = Field(description="Item that fell back")
    item_type: str = Field(description="Type of item (sp, expression, etc.)")
    reason: str = Field(description="Reason for fallback")
    fallback_method: str = Field(description="Method used as fallback")
    success: bool = Field(description="Whether fallback succeeded")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AIFallbackService:
    """Service for managing AI availability and fallback logic.

    Tracks AI service state and provides graceful degradation when
    Ollama is unavailable or disabled.
    """

    # Configuration
    max_consecutive_failures: int = 5
    health_check_interval_seconds: int = 60
    _ai_enabled: bool = True

    # State tracking
    _last_available: datetime | None = None
    _last_checked: datetime | None = None
    _consecutive_failures: int = 0
    _current_status: AIStatus = AIStatus.AVAILABLE

    # Session metrics
    _session_method_counts: dict = field(default_factory=lambda: {
        ConversionMethod.RULE_BASED: 0,
        ConversionMethod.AI_ASSISTED: 0,
        ConversionMethod.AI_FALLBACK: 0,
        ConversionMethod.MANUAL: 0,
    })
    _fallback_events: list = field(default_factory=list)

    # Ollama client (injected)
    _ollama_client: OllamaClient | None = None

    def __post_init__(self):
        """Initialize after dataclass creation."""
        # Ensure _session_method_counts is properly initialized
        if self._session_method_counts is None:
            self._session_method_counts = {
                ConversionMethod.RULE_BASED: 0,
                ConversionMethod.AI_ASSISTED: 0,
                ConversionMethod.AI_FALLBACK: 0,
                ConversionMethod.MANUAL: 0,
            }
        if self._fallback_events is None:
            self._fallback_events = []

    def _get_ollama_client(self) -> OllamaClient:
        """Get or create Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = get_ollama_client()
        return self._ollama_client

    def set_ai_enabled(self, enabled: bool) -> None:
        """Set whether AI is enabled.

        Args:
            enabled: Whether to enable AI
        """
        self._ai_enabled = enabled
        if not enabled:
            self._current_status = AIStatus.DISABLED
        else:
            # Reset status to trigger fresh check
            self._current_status = AIStatus.AVAILABLE

    def is_ai_enabled(self) -> bool:
        """Check if AI is enabled in settings.

        Returns:
            True if AI is enabled
        """
        return self._ai_enabled

    async def is_ai_available(self, force_check: bool = False) -> bool:
        """Check if AI (Ollama) is available.

        Args:
            force_check: Force fresh check, ignoring recent checks

        Returns:
            True if AI is available and working
        """
        if not self.is_ai_enabled():
            self._current_status = AIStatus.DISABLED
            return False

        # Check if we should skip based on recent check
        now = datetime.now(timezone.utc)
        if not force_check and self._last_checked:
            elapsed = (now - self._last_checked).total_seconds()
            if elapsed < self.health_check_interval_seconds:
                # Use cached status
                return self._current_status == AIStatus.AVAILABLE

        self._last_checked = now

        try:
            client = self._get_ollama_client()
            available = await client.is_available()

            if available:
                self._last_available = now
                self._consecutive_failures = 0
                self._current_status = AIStatus.AVAILABLE
                return True
            else:
                self._record_failure("Ollama not responding")
                return False

        except Exception as e:
            logger.warning("AI availability check failed: %s", str(e))
            self._record_failure(str(e))
            return False

    def _record_failure(self, reason: str) -> None:
        """Record an AI failure.

        Args:
            reason: Reason for failure
        """
        self._consecutive_failures += 1

        if self._consecutive_failures >= self.max_consecutive_failures:
            self._current_status = AIStatus.UNAVAILABLE
            logger.warning(
                "AI marked as unavailable after %d consecutive failures",
                self._consecutive_failures,
            )
        elif self._consecutive_failures > 0:
            self._current_status = AIStatus.DEGRADED

    def record_conversion(self, method: ConversionMethod) -> None:
        """Record a conversion method used.

        Args:
            method: The conversion method used
        """
        if method not in self._session_method_counts:
            self._session_method_counts[method] = 0
        self._session_method_counts[method] += 1

    def record_fallback(
        self,
        item_name: str,
        item_type: str,
        reason: str,
        fallback_method: str,
        success: bool,
        conversion_id: str | None = None,
    ) -> None:
        """Record a fallback event.

        Args:
            item_name: Name of the item that fell back
            item_type: Type of item (sp, expression, etc.)
            reason: Reason for fallback
            fallback_method: Method used as fallback
            success: Whether fallback succeeded
            conversion_id: Optional conversion ID
        """
        event = FallbackEvent(
            conversion_id=conversion_id,
            item_name=item_name,
            item_type=item_type,
            reason=reason,
            fallback_method=fallback_method,
            success=success,
        )

        self._fallback_events.append(event)
        self.record_conversion(ConversionMethod.AI_FALLBACK)

        # Log structured event
        logger.warning(
            "AI fallback event",
            extra=event.model_dump(),
        )

    def get_status(self) -> AIStatusResponse:
        """Get current AI status for dashboard.

        Returns:
            AIStatusResponse with current status details
        """
        client = self._get_ollama_client()

        # Get circuit breaker status
        cb_status = client.get_circuit_breaker_status()

        # Build message
        if self._current_status == AIStatus.DISABLED:
            message = "AI assistance is disabled. Using rule-based conversion only."
        elif self._current_status == AIStatus.AVAILABLE:
            message = "AI service is available and functioning normally."
        elif self._current_status == AIStatus.DEGRADED:
            message = f"AI service is degraded ({self._consecutive_failures} failures). Some requests may fail."
        else:  # UNAVAILABLE
            message = (
                f"AI service is unavailable after {self._consecutive_failures} failures. "
                "Using rule-based conversion as fallback."
            )

        return AIStatusResponse(
            enabled=self._ai_enabled,
            status=self._current_status,
            last_available=self._last_available,
            last_checked=self._last_checked,
            consecutive_failures=self._consecutive_failures,
            circuit_breaker_state=cb_status.get("state"),
            model_name=client.config.model if client.config else None,
            message=message,
        )

    def get_method_breakdown(self) -> ConversionMethodBreakdown:
        """Get breakdown of conversion methods used.

        Returns:
            ConversionMethodBreakdown with counts
        """
        return ConversionMethodBreakdown(
            rule_based_count=self._session_method_counts.get(ConversionMethod.RULE_BASED, 0),
            ai_assisted_count=self._session_method_counts.get(ConversionMethod.AI_ASSISTED, 0),
            ai_fallback_count=self._session_method_counts.get(ConversionMethod.AI_FALLBACK, 0),
            manual_count=self._session_method_counts.get(ConversionMethod.MANUAL, 0),
            total_count=sum(self._session_method_counts.values()),
        )

    def get_fallback_events(self) -> list[FallbackEvent]:
        """Get list of fallback events from this session.

        Returns:
            List of FallbackEvent objects
        """
        return self._fallback_events.copy()

    def reset_session_metrics(self) -> None:
        """Reset session metrics for a new conversion run."""
        self._session_method_counts = {
            ConversionMethod.RULE_BASED: 0,
            ConversionMethod.AI_ASSISTED: 0,
            ConversionMethod.AI_FALLBACK: 0,
            ConversionMethod.MANUAL: 0,
        }
        self._fallback_events = []

    def should_use_ai(self, complexity: str) -> bool:
        """Determine if AI should be used for an item based on complexity.

        Args:
            complexity: Item complexity level (SIMPLE, MODERATE, COMPLEX)

        Returns:
            True if AI should be attempted
        """
        if not self._ai_enabled:
            return False

        if self._current_status == AIStatus.UNAVAILABLE:
            return False

        # Simple items always use rule-based
        if complexity.upper() == "SIMPLE":
            return False

        return True

    def check_high_fallback_rate(self, threshold: float = 0.5) -> bool:
        """Check if fallback rate is above threshold.

        Args:
            threshold: Fallback rate threshold (0.0-1.0)

        Returns:
            True if fallback rate exceeds threshold
        """
        breakdown = self.get_method_breakdown()
        if breakdown.total_count == 0:
            return False

        fallback_rate = breakdown.ai_fallback_count / breakdown.total_count
        if fallback_rate > threshold:
            logger.warning(
                "High fallback rate detected",
                extra={
                    "event": "high_fallback_rate",
                    "fallback_count": breakdown.ai_fallback_count,
                    "total_count": breakdown.total_count,
                    "fallback_rate": fallback_rate,
                    "threshold": threshold,
                    "severity": "warning",
                },
            )
            return True

        return False


# =============================================================================
# Singleton Instance
# =============================================================================


_ai_fallback_service: AIFallbackService | None = None


def get_ai_fallback_service() -> AIFallbackService:
    """Get or create the global AI fallback service instance.

    Returns:
        AIFallbackService instance
    """
    global _ai_fallback_service
    if _ai_fallback_service is None:
        _ai_fallback_service = AIFallbackService()
    return _ai_fallback_service


def reset_ai_fallback_service() -> None:
    """Reset the global AI fallback service (for testing)."""
    global _ai_fallback_service
    _ai_fallback_service = None
