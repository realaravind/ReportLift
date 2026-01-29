"""Tests for the AI fallback service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_fallback import (
    AIFallbackService,
    AIStatus,
    AIStatusResponse,
    ConversionMethod,
    ConversionMethodBreakdown,
    FallbackEvent,
    get_ai_fallback_service,
    reset_ai_fallback_service,
)


class TestAIStatus:
    """Tests for AIStatus enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert AIStatus.AVAILABLE.value == "available"
        assert AIStatus.DEGRADED.value == "degraded"
        assert AIStatus.UNAVAILABLE.value == "unavailable"
        assert AIStatus.DISABLED.value == "disabled"


class TestConversionMethod:
    """Tests for ConversionMethod enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert ConversionMethod.RULE_BASED.value == "rule_based"
        assert ConversionMethod.AI_ASSISTED.value == "ai_assisted"
        assert ConversionMethod.AI_FALLBACK.value == "ai_fallback"
        assert ConversionMethod.MANUAL.value == "manual"


class TestConversionMethodBreakdown:
    """Tests for ConversionMethodBreakdown schema."""

    def test_default_values(self):
        """Test default values."""
        breakdown = ConversionMethodBreakdown()
        assert breakdown.rule_based_count == 0
        assert breakdown.total_count == 0

    def test_ai_usage_percentage(self):
        """Test AI usage percentage calculation."""
        breakdown = ConversionMethodBreakdown(
            ai_assisted_count=3,
            rule_based_count=7,
            total_count=10,
        )
        assert breakdown.ai_usage_percentage == 30.0

    def test_ai_usage_percentage_zero_total(self):
        """Test AI usage percentage with zero total."""
        breakdown = ConversionMethodBreakdown()
        assert breakdown.ai_usage_percentage == 0.0

    def test_fallback_percentage(self):
        """Test fallback percentage calculation."""
        breakdown = ConversionMethodBreakdown(
            ai_fallback_count=2,
            total_count=10,
        )
        assert breakdown.fallback_percentage == 20.0


class TestFallbackEvent:
    """Tests for FallbackEvent schema."""

    def test_event_creation(self):
        """Test creating fallback event."""
        event = FallbackEvent(
            item_name="sp_Complex",
            item_type="stored_procedure",
            reason="Connection timeout",
            fallback_method="rule_based",
            success=True,
        )
        assert event.item_name == "sp_Complex"
        assert event.success is True
        assert event.timestamp is not None


class TestAIStatusResponse:
    """Tests for AIStatusResponse schema."""

    def test_status_response(self):
        """Test creating status response."""
        response = AIStatusResponse(
            enabled=True,
            status=AIStatus.AVAILABLE,
            message="AI is available",
        )
        assert response.enabled is True
        assert response.status == AIStatus.AVAILABLE


class TestAIFallbackService:
    """Tests for AIFallbackService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        reset_ai_fallback_service()
        return AIFallbackService()

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = MagicMock()
        client.is_available = AsyncMock(return_value=True)
        client.config = MagicMock()
        client.config.model = "codellama:13b"
        client.get_circuit_breaker_status = MagicMock(return_value={"state": "closed"})
        return client

    def test_is_ai_enabled_default(self, service):
        """Test AI is enabled by default."""
        assert service.is_ai_enabled() is True

    def test_set_ai_disabled(self, service):
        """Test disabling AI."""
        service.set_ai_enabled(False)
        assert service.is_ai_enabled() is False
        assert service._current_status == AIStatus.DISABLED

    def test_set_ai_enabled(self, service):
        """Test enabling AI."""
        service.set_ai_enabled(False)
        service.set_ai_enabled(True)
        assert service.is_ai_enabled() is True
        assert service._current_status == AIStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_is_ai_available_when_disabled(self, service):
        """Test AI availability when disabled."""
        service.set_ai_enabled(False)
        available = await service.is_ai_available()
        assert available is False
        assert service._current_status == AIStatus.DISABLED

    @pytest.mark.asyncio
    async def test_is_ai_available_success(self, service, mock_ollama_client):
        """Test AI availability check success."""
        service._ollama_client = mock_ollama_client

        available = await service.is_ai_available(force_check=True)

        assert available is True
        assert service._current_status == AIStatus.AVAILABLE
        assert service._consecutive_failures == 0
        assert service._last_available is not None

    @pytest.mark.asyncio
    async def test_is_ai_available_failure(self, service, mock_ollama_client):
        """Test AI availability check failure."""
        mock_ollama_client.is_available = AsyncMock(return_value=False)
        service._ollama_client = mock_ollama_client

        available = await service.is_ai_available(force_check=True)

        assert available is False
        assert service._consecutive_failures == 1
        assert service._current_status == AIStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_is_ai_available_multiple_failures_marks_unavailable(
        self, service, mock_ollama_client
    ):
        """Test multiple failures marks AI as unavailable."""
        mock_ollama_client.is_available = AsyncMock(return_value=False)
        service._ollama_client = mock_ollama_client
        service.max_consecutive_failures = 3

        # First failure
        await service.is_ai_available(force_check=True)
        assert service._current_status == AIStatus.DEGRADED

        # Second failure
        await service.is_ai_available(force_check=True)
        assert service._current_status == AIStatus.DEGRADED

        # Third failure - should mark unavailable
        await service.is_ai_available(force_check=True)
        assert service._current_status == AIStatus.UNAVAILABLE
        assert service._consecutive_failures == 3

    def test_record_conversion(self, service):
        """Test recording conversion method."""
        service.record_conversion(ConversionMethod.AI_ASSISTED)
        service.record_conversion(ConversionMethod.AI_ASSISTED)
        service.record_conversion(ConversionMethod.RULE_BASED)

        breakdown = service.get_method_breakdown()
        assert breakdown.ai_assisted_count == 2
        assert breakdown.rule_based_count == 1
        assert breakdown.total_count == 3

    def test_record_fallback(self, service):
        """Test recording fallback event."""
        service.record_fallback(
            item_name="sp_Test",
            item_type="stored_procedure",
            reason="Timeout",
            fallback_method="rule_based",
            success=True,
        )

        events = service.get_fallback_events()
        assert len(events) == 1
        assert events[0].item_name == "sp_Test"

        breakdown = service.get_method_breakdown()
        assert breakdown.ai_fallback_count == 1

    def test_get_status(self, service, mock_ollama_client):
        """Test getting AI status."""
        service._ollama_client = mock_ollama_client

        status = service.get_status()

        assert status.enabled is True
        assert status.status == AIStatus.AVAILABLE
        assert "available" in status.message.lower() or "normally" in status.message.lower()

    def test_get_status_disabled(self, service, mock_ollama_client):
        """Test getting AI status when disabled."""
        service._ollama_client = mock_ollama_client
        service.set_ai_enabled(False)

        status = service.get_status()

        assert status.enabled is False
        assert status.status == AIStatus.DISABLED
        assert "disabled" in status.message.lower()

    def test_get_method_breakdown(self, service):
        """Test getting method breakdown."""
        service.record_conversion(ConversionMethod.AI_ASSISTED)
        service.record_conversion(ConversionMethod.RULE_BASED)
        service.record_conversion(ConversionMethod.RULE_BASED)

        breakdown = service.get_method_breakdown()

        assert breakdown.ai_assisted_count == 1
        assert breakdown.rule_based_count == 2
        assert breakdown.total_count == 3

    def test_reset_session_metrics(self, service):
        """Test resetting session metrics."""
        service.record_conversion(ConversionMethod.AI_ASSISTED)
        service.record_fallback(
            item_name="test",
            item_type="sp",
            reason="test",
            fallback_method="rule_based",
            success=True,
        )

        service.reset_session_metrics()

        breakdown = service.get_method_breakdown()
        assert breakdown.total_count == 0

        events = service.get_fallback_events()
        assert len(events) == 0

    def test_should_use_ai_simple(self, service):
        """Test should_use_ai for simple complexity."""
        assert service.should_use_ai("SIMPLE") is False

    def test_should_use_ai_complex(self, service):
        """Test should_use_ai for complex complexity."""
        assert service.should_use_ai("COMPLEX") is True

    def test_should_use_ai_disabled(self, service):
        """Test should_use_ai when disabled."""
        service.set_ai_enabled(False)
        assert service.should_use_ai("COMPLEX") is False

    def test_should_use_ai_unavailable(self, service):
        """Test should_use_ai when unavailable."""
        service._current_status = AIStatus.UNAVAILABLE
        assert service.should_use_ai("COMPLEX") is False

    def test_check_high_fallback_rate_true(self, service):
        """Test high fallback rate detection."""
        # 6 fallbacks out of 10 = 60%
        for _ in range(6):
            service.record_conversion(ConversionMethod.AI_FALLBACK)
        for _ in range(4):
            service.record_conversion(ConversionMethod.RULE_BASED)

        assert service.check_high_fallback_rate(threshold=0.5) is True

    def test_check_high_fallback_rate_false(self, service):
        """Test low fallback rate."""
        # 2 fallbacks out of 10 = 20%
        for _ in range(2):
            service.record_conversion(ConversionMethod.AI_FALLBACK)
        for _ in range(8):
            service.record_conversion(ConversionMethod.RULE_BASED)

        assert service.check_high_fallback_rate(threshold=0.5) is False

    def test_check_high_fallback_rate_empty(self, service):
        """Test fallback rate with no conversions."""
        assert service.check_high_fallback_rate() is False


class TestGetAiFallbackService:
    """Tests for get_ai_fallback_service function."""

    def test_returns_singleton(self):
        """Test that function returns same instance."""
        reset_ai_fallback_service()
        service1 = get_ai_fallback_service()
        service2 = get_ai_fallback_service()
        assert service1 is service2

    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        service1 = get_ai_fallback_service()
        reset_ai_fallback_service()
        service2 = get_ai_fallback_service()
        assert service1 is not service2


class TestAIFallbackServiceCaching:
    """Tests for AI availability caching."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        reset_ai_fallback_service()
        return AIFallbackService(health_check_interval_seconds=60)

    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = MagicMock()
        client.is_available = AsyncMock(return_value=True)
        client.config = MagicMock()
        client.config.model = "codellama:13b"
        client.get_circuit_breaker_status = MagicMock(return_value={"state": "closed"})
        return client

    @pytest.mark.asyncio
    async def test_caches_availability_check(self, service, mock_ollama_client):
        """Test that availability check is cached."""
        service._ollama_client = mock_ollama_client

        # First check
        await service.is_ai_available(force_check=True)
        assert mock_ollama_client.is_available.call_count == 1

        # Second check (should use cache)
        await service.is_ai_available(force_check=False)
        assert mock_ollama_client.is_available.call_count == 1  # Still 1

    @pytest.mark.asyncio
    async def test_force_check_bypasses_cache(self, service, mock_ollama_client):
        """Test that force_check bypasses cache."""
        service._ollama_client = mock_ollama_client

        # First check
        await service.is_ai_available(force_check=True)
        assert mock_ollama_client.is_available.call_count == 1

        # Force check
        await service.is_ai_available(force_check=True)
        assert mock_ollama_client.is_available.call_count == 2
