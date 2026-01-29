"""Tests for conversion flagging service."""

from datetime import datetime, timezone
import pytest

from app.services.conversion_flagging import (
    VerificationStatus,
    VerificationAction,
    ConversionFlag,
    UncertainConversionDetails,
    VerificationRequest,
    VerificationResult,
    VerificationRecord,
    UncertainConversionsSummary,
    ConversionFlaggingService,
    get_flagging_service,
)
from app.services.sp_rewriter_ai import AIConfidenceLevel, AIRewriteAttempt


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert VerificationStatus.PENDING.value == "pending"
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.REJECTED.value == "rejected"


class TestVerificationAction:
    """Tests for VerificationAction enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert VerificationAction.VERIFY.value == "verify"
        assert VerificationAction.REJECT.value == "reject"


class TestConversionFlag:
    """Tests for ConversionFlag schema."""

    def test_uncertain_flag(self):
        """Test creating uncertain flag."""
        flag = ConversionFlag(
            is_uncertain=True,
            confidence_level=AIConfidenceLevel.LOW,
            confidence_score=0.30,
            reason="Low confidence - significant uncertainty",
            review_priority="high",
        )
        assert flag.is_uncertain is True
        assert flag.confidence_score == 0.30
        assert flag.review_priority == "high"

    def test_confident_flag(self):
        """Test creating confident flag."""
        flag = ConversionFlag(
            is_uncertain=False,
            confidence_level=AIConfidenceLevel.HIGH,
            confidence_score=0.90,
            reason="High confidence",
            review_priority="low",
        )
        assert flag.is_uncertain is False
        assert flag.confidence_score == 0.90


class TestUncertainConversionDetails:
    """Tests for UncertainConversionDetails schema."""

    def test_basic_creation(self):
        """Test creating uncertain conversion details."""
        flag = ConversionFlag(
            is_uncertain=True,
            confidence_level=AIConfidenceLevel.MEDIUM,
            confidence_score=0.65,
            reason="Medium confidence",
            review_priority="medium",
        )

        details = UncertainConversionDetails(
            rewrite_id="test-123",
            sp_name="sp_GetCustomers",
            sp_definition="CREATE PROCEDURE sp_GetCustomers AS SELECT * FROM customers",
            generated_sql="SELECT * FROM customers;",
            confidence_level=AIConfidenceLevel.MEDIUM,
            confidence_score=0.65,
            ai_explanation="Simple conversion",
            flag=flag,
            verification_status=VerificationStatus.PENDING,
            review_recommendations=["Review SQL", "Test with data"],
        )

        assert details.sp_name == "sp_GetCustomers"
        assert details.verification_status == VerificationStatus.PENDING
        assert len(details.review_recommendations) == 2


class TestVerificationRequest:
    """Tests for VerificationRequest schema."""

    def test_verify_request(self):
        """Test verify request."""
        request = VerificationRequest(
            action=VerificationAction.VERIFY,
            notes="Looks good after review",
        )
        assert request.action == VerificationAction.VERIFY
        assert request.notes == "Looks good after review"

    def test_reject_request(self):
        """Test reject request."""
        request = VerificationRequest(
            action=VerificationAction.REJECT,
            notes="SQL logic is incorrect",
        )
        assert request.action == VerificationAction.REJECT


class TestVerificationResult:
    """Tests for VerificationResult schema."""

    def test_verification_result(self):
        """Test creating verification result."""
        result = VerificationResult(
            rewrite_id="test-123",
            previous_status=VerificationStatus.PENDING,
            new_status=VerificationStatus.VERIFIED,
            verified_by="user@example.com",
            verified_at=datetime.now(timezone.utc),
            notes="Approved",
        )
        assert result.new_status == VerificationStatus.VERIFIED
        assert result.verified_by == "user@example.com"


class TestVerificationRecord:
    """Tests for VerificationRecord schema."""

    def test_record_creation(self):
        """Test creating verification record."""
        record = VerificationRecord(
            rewrite_id="test-123",
            sp_name="sp_Test",
            user_id="user-456",
            user_email="user@example.com",
            action=VerificationAction.VERIFY,
            previous_status=VerificationStatus.PENDING,
            new_status=VerificationStatus.VERIFIED,
            confidence_level=AIConfidenceLevel.MEDIUM,
            notes="Reviewed and approved",
        )
        assert record.sp_name == "sp_Test"
        assert record.action == VerificationAction.VERIFY
        assert record.id is not None  # Auto-generated


class TestUncertainConversionsSummary:
    """Tests for UncertainConversionsSummary schema."""

    def test_summary_defaults(self):
        """Test summary default values."""
        summary = UncertainConversionsSummary()
        assert summary.total_ai_rewrites == 0
        assert summary.uncertain_count == 0
        assert summary.pending_review_count == 0

    def test_summary_with_values(self):
        """Test summary with values."""
        summary = UncertainConversionsSummary(
            total_ai_rewrites=10,
            uncertain_count=5,
            high_confidence_count=5,
            medium_confidence_count=3,
            low_confidence_count=2,
            pending_review_count=3,
            verified_count=1,
            rejected_count=1,
        )
        assert summary.total_ai_rewrites == 10
        assert summary.uncertain_count == 5


class TestConversionFlaggingService:
    """Tests for ConversionFlaggingService."""

    def test_evaluate_confidence_high(self):
        """Test evaluating high confidence."""
        service = ConversionFlaggingService()
        is_uncertain, score, reason = service.evaluate_confidence(AIConfidenceLevel.HIGH)

        assert is_uncertain is False
        assert score == 0.90
        assert "High confidence" in reason

    def test_evaluate_confidence_medium(self):
        """Test evaluating medium confidence."""
        service = ConversionFlaggingService()
        is_uncertain, score, reason = service.evaluate_confidence(AIConfidenceLevel.MEDIUM)

        assert is_uncertain is True  # Default setting flags medium as uncertain
        assert score == 0.65
        assert "Medium confidence" in reason

    def test_evaluate_confidence_low(self):
        """Test evaluating low confidence."""
        service = ConversionFlaggingService()
        is_uncertain, score, reason = service.evaluate_confidence(AIConfidenceLevel.LOW)

        assert is_uncertain is True
        assert score == 0.30
        assert "Low confidence" in reason

    def test_create_flag_high(self):
        """Test creating flag for high confidence."""
        service = ConversionFlaggingService()
        flag = service.create_flag(AIConfidenceLevel.HIGH)

        assert flag.is_uncertain is False
        assert flag.confidence_level == AIConfidenceLevel.HIGH
        assert flag.review_priority == "low"

    def test_create_flag_medium(self):
        """Test creating flag for medium confidence."""
        service = ConversionFlaggingService()
        flag = service.create_flag(AIConfidenceLevel.MEDIUM)

        assert flag.is_uncertain is True
        assert flag.review_priority == "medium"

    def test_create_flag_low(self):
        """Test creating flag for low confidence."""
        service = ConversionFlaggingService()
        flag = service.create_flag(AIConfidenceLevel.LOW)

        assert flag.is_uncertain is True
        assert flag.review_priority == "high"

    def test_verify_conversion_verify_action(self):
        """Test verifying a conversion."""
        service = ConversionFlaggingService()
        request = VerificationRequest(
            action=VerificationAction.VERIFY,
            notes="Looks correct",
        )

        result = service.verify_conversion(
            rewrite_id="test-123",
            sp_name="sp_Test",
            confidence_level=AIConfidenceLevel.MEDIUM,
            request=request,
            user_id="user-456",
            user_email="user@example.com",
        )

        assert result.previous_status == VerificationStatus.PENDING
        assert result.new_status == VerificationStatus.VERIFIED
        assert result.verified_by == "user@example.com"

    def test_verify_conversion_reject_action(self):
        """Test rejecting a conversion."""
        service = ConversionFlaggingService()
        request = VerificationRequest(
            action=VerificationAction.REJECT,
            notes="SQL is incorrect",
        )

        result = service.verify_conversion(
            rewrite_id="test-456",
            sp_name="sp_Bad",
            confidence_level=AIConfidenceLevel.LOW,
            request=request,
            user_id="user-789",
        )

        assert result.new_status == VerificationStatus.REJECTED

    def test_get_verification_status_default(self):
        """Test getting verification status for unknown rewrite."""
        service = ConversionFlaggingService()
        status = service.get_verification_status("unknown-id")
        assert status == VerificationStatus.PENDING

    def test_get_verification_status_after_verify(self):
        """Test getting verification status after verification."""
        service = ConversionFlaggingService()

        # Verify first
        request = VerificationRequest(action=VerificationAction.VERIFY)
        service.verify_conversion(
            rewrite_id="test-status",
            sp_name="sp_Test",
            confidence_level=AIConfidenceLevel.MEDIUM,
            request=request,
        )

        # Check status
        status = service.get_verification_status("test-status")
        assert status == VerificationStatus.VERIFIED

    def test_get_verification_history(self):
        """Test getting verification history."""
        service = ConversionFlaggingService()

        # Perform verification
        request = VerificationRequest(
            action=VerificationAction.VERIFY,
            notes="Approved",
        )
        service.verify_conversion(
            rewrite_id="test-history",
            sp_name="sp_Test",
            confidence_level=AIConfidenceLevel.MEDIUM,
            request=request,
            user_email="user@example.com",
        )

        # Get history
        history = service.get_verification_history("test-history")
        assert len(history) == 1
        assert history[0].action == VerificationAction.VERIFY
        assert history[0].notes == "Approved"

    def test_generate_rejected_placeholder(self):
        """Test generating rejected placeholder SQL."""
        service = ConversionFlaggingService()
        placeholder = service.generate_rejected_placeholder(
            sp_name="sp_BadConversion",
            user_email="admin@example.com",
            rejection_notes="Logic is wrong",
        )

        assert "sp_BadConversion" in placeholder
        assert "admin@example.com" in placeholder
        assert "Logic is wrong" in placeholder
        assert "MANUAL_CONVERSION_REQUIRED" in placeholder

    def test_create_uncertain_details(self):
        """Test creating uncertain details from attempt."""
        service = ConversionFlaggingService()

        attempt = AIRewriteAttempt(
            sp_name="sp_Complex",
            sp_definition="CREATE PROCEDURE sp_Complex AS ...",
            generated_sql="SELECT * FROM complex;",
            confidence=AIConfidenceLevel.LOW,
            explanation="Complex logic detected",
            is_valid=True,
        )

        details = service.create_uncertain_details(attempt)

        assert details.sp_name == "sp_Complex"
        assert details.confidence_level == AIConfidenceLevel.LOW
        assert details.flag.is_uncertain is True
        assert len(details.review_recommendations) > 0


class TestGetFlaggingService:
    """Tests for get_flagging_service function."""

    def test_returns_singleton(self):
        """Test that function returns singleton."""
        service1 = get_flagging_service()
        service2 = get_flagging_service()
        assert service1 is service2

    def test_service_is_functional(self):
        """Test that returned service works."""
        service = get_flagging_service()
        flag = service.create_flag(AIConfidenceLevel.HIGH)
        assert flag is not None
