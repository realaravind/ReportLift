"""Conversion Flagging Service.

This service handles flagging of uncertain AI conversions and
tracking user verification decisions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.sp_rewriter_ai import AIConfidenceLevel, AIRewriteAttempt

logger = logging.getLogger(__name__)


# ============================================
# Enums and Constants
# ============================================


class VerificationStatus(str, Enum):
    """Status of verification for uncertain conversions."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VerificationAction(str, Enum):
    """User actions for verification."""
    VERIFY = "verify"
    REJECT = "reject"


# ============================================
# Pydantic Schemas
# ============================================


class ConversionFlag(BaseModel):
    """Flag information for an uncertain conversion."""

    is_uncertain: bool = Field(description="Whether this conversion is flagged as uncertain")
    confidence_level: AIConfidenceLevel = Field(description="AI confidence level")
    confidence_score: float = Field(description="Numeric confidence score (0.0-1.0)")
    reason: str = Field(description="Reason for flagging")
    review_priority: str = Field(description="Priority for review: high, medium, low")


class UncertainConversionDetails(BaseModel):
    """Detailed information about an uncertain conversion for review."""

    rewrite_id: str = Field(description="Unique ID of the rewrite attempt")
    sp_name: str = Field(description="Name of the stored procedure")
    sp_definition: str = Field(description="Original SP definition")
    generated_sql: Optional[str] = Field(default=None, description="AI-generated SQL")
    confidence_level: AIConfidenceLevel = Field(description="AI confidence level")
    confidence_score: float = Field(description="Numeric confidence score")
    ai_explanation: Optional[str] = Field(default=None, description="AI's explanation")
    flag: ConversionFlag = Field(description="Flag information")
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    review_recommendations: list[str] = Field(default_factory=list)


class VerificationRequest(BaseModel):
    """Request to verify or reject a conversion."""

    action: VerificationAction = Field(description="Verification action: verify or reject")
    notes: Optional[str] = Field(default=None, description="User notes about the decision")


class VerificationResult(BaseModel):
    """Result of a verification action."""

    rewrite_id: str = Field(description="ID of the verified rewrite")
    previous_status: VerificationStatus = Field(description="Status before verification")
    new_status: VerificationStatus = Field(description="New status after verification")
    verified_by: Optional[str] = Field(default=None, description="User who verified")
    verified_at: datetime = Field(description="When verification occurred")
    notes: Optional[str] = Field(default=None, description="Verification notes")


class VerificationRecord(BaseModel):
    """Record of a verification decision for audit trail."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    rewrite_id: str = Field(description="ID of the rewrite")
    sp_name: str = Field(description="Name of the SP")
    user_id: Optional[str] = Field(default=None, description="User who verified")
    user_email: Optional[str] = Field(default=None, description="User email")
    action: VerificationAction = Field(description="Action taken")
    previous_status: VerificationStatus = Field(description="Previous status")
    new_status: VerificationStatus = Field(description="New status")
    confidence_level: AIConfidenceLevel = Field(description="AI confidence level")
    notes: Optional[str] = Field(default=None, description="User notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UncertainConversionsSummary(BaseModel):
    """Summary of uncertain conversions for a conversion job."""

    total_ai_rewrites: int = Field(default=0, description="Total AI rewrites in this conversion")
    uncertain_count: int = Field(default=0, description="Number flagged as uncertain")
    high_confidence_count: int = Field(default=0, description="Number with high confidence")
    medium_confidence_count: int = Field(default=0, description="Number with medium confidence")
    low_confidence_count: int = Field(default=0, description="Number with low confidence")
    pending_review_count: int = Field(default=0, description="Number pending user review")
    verified_count: int = Field(default=0, description="Number verified by user")
    rejected_count: int = Field(default=0, description="Number rejected by user")


# ============================================
# Flagging Service
# ============================================


class ConversionFlaggingService:
    """Service for flagging and tracking uncertain conversions."""

    def __init__(self):
        """Initialize the flagging service."""
        # In-memory storage for verification tracking (for now)
        # In production, this would be stored in a database
        self._verification_records: dict[str, VerificationRecord] = {}
        self._rewrite_statuses: dict[str, VerificationStatus] = {}

    def evaluate_confidence(
        self,
        confidence_level: AIConfidenceLevel,
    ) -> tuple[bool, float, str]:
        """Evaluate if a conversion should be flagged as uncertain.

        Args:
            confidence_level: AI confidence level

        Returns:
            Tuple of (is_uncertain, confidence_score, reason)
        """
        # Map confidence level to score
        if confidence_level == AIConfidenceLevel.HIGH:
            score = 0.90
            is_uncertain = False
            reason = "High confidence - AI is confident in the conversion"
        elif confidence_level == AIConfidenceLevel.MEDIUM:
            score = 0.65
            is_uncertain = settings.flag_uncertain_for_medium
            reason = "Medium confidence - some uncertainty in conversion"
        else:  # LOW
            score = 0.30
            is_uncertain = settings.flag_uncertain_for_low
            reason = "Low confidence - significant uncertainty in conversion"

        return is_uncertain, score, reason

    def create_flag(
        self,
        confidence_level: AIConfidenceLevel,
    ) -> ConversionFlag:
        """Create a flag for a conversion based on confidence.

        Args:
            confidence_level: AI confidence level

        Returns:
            ConversionFlag with evaluation results
        """
        is_uncertain, score, reason = self.evaluate_confidence(confidence_level)

        # Determine review priority
        if score < settings.confidence_medium_threshold:
            priority = "high"
        elif score < settings.confidence_high_threshold:
            priority = "medium"
        else:
            priority = "low"

        return ConversionFlag(
            is_uncertain=is_uncertain,
            confidence_level=confidence_level,
            confidence_score=score,
            reason=reason,
            review_priority=priority,
        )

    def create_uncertain_details(
        self,
        attempt: AIRewriteAttempt,
    ) -> UncertainConversionDetails:
        """Create detailed uncertain conversion info from a rewrite attempt.

        Args:
            attempt: AI rewrite attempt record

        Returns:
            UncertainConversionDetails for UI display
        """
        # Create flag
        confidence = attempt.confidence or AIConfidenceLevel.LOW
        flag = self.create_flag(confidence)

        # Get existing verification status
        rewrite_id = str(uuid4())  # In production, this would be from the attempt
        status = self._rewrite_statuses.get(rewrite_id, VerificationStatus.PENDING)

        # Generate review recommendations
        recommendations = self._generate_review_recommendations(
            confidence,
            attempt.validation_error,
        )

        return UncertainConversionDetails(
            rewrite_id=rewrite_id,
            sp_name=attempt.sp_name,
            sp_definition=attempt.sp_definition,
            generated_sql=attempt.generated_sql,
            confidence_level=confidence,
            confidence_score=flag.confidence_score,
            ai_explanation=attempt.explanation,
            flag=flag,
            verification_status=status,
            review_recommendations=recommendations,
        )

    def _generate_review_recommendations(
        self,
        confidence: AIConfidenceLevel,
        validation_error: Optional[str],
    ) -> list[str]:
        """Generate review recommendations based on confidence and errors.

        Args:
            confidence: AI confidence level
            validation_error: Validation error if any

        Returns:
            List of review recommendations
        """
        recommendations = []

        if validation_error:
            recommendations.append(f"Fix validation error: {validation_error}")

        if confidence == AIConfidenceLevel.LOW:
            recommendations.extend([
                "Carefully review the entire generated SQL",
                "Compare row counts between original SP and converted query",
                "Test with sample data before using in production",
                "Consider manual rewrite if logic is complex",
            ])
        elif confidence == AIConfidenceLevel.MEDIUM:
            recommendations.extend([
                "Review SQL conversion for accuracy",
                "Verify function mappings are correct",
                "Test with edge case parameters",
            ])
        else:
            recommendations.append("Quick sanity check recommended")

        return recommendations

    def verify_conversion(
        self,
        rewrite_id: str,
        sp_name: str,
        confidence_level: AIConfidenceLevel,
        request: VerificationRequest,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> VerificationResult:
        """Process a verify/reject action for a conversion.

        Args:
            rewrite_id: ID of the rewrite to verify
            sp_name: Name of the SP
            confidence_level: AI confidence level
            request: Verification request
            user_id: ID of the user making the decision
            user_email: Email of the user

        Returns:
            VerificationResult with the outcome
        """
        previous_status = self._rewrite_statuses.get(rewrite_id, VerificationStatus.PENDING)

        # Determine new status based on action
        if request.action == VerificationAction.VERIFY:
            new_status = VerificationStatus.VERIFIED
        else:
            new_status = VerificationStatus.REJECTED

        # Update status
        self._rewrite_statuses[rewrite_id] = new_status

        # Create verification record for audit
        record = VerificationRecord(
            rewrite_id=rewrite_id,
            sp_name=sp_name,
            user_id=user_id,
            user_email=user_email,
            action=request.action,
            previous_status=previous_status,
            new_status=new_status,
            confidence_level=confidence_level,
            notes=request.notes,
        )
        self._verification_records[record.id] = record

        # Log the verification
        logger.info(
            "Conversion verification: %s",
            rewrite_id,
            extra={
                "event": "conversion_verification",
                "rewrite_id": rewrite_id,
                "sp_name": sp_name,
                "action": request.action.value,
                "previous_status": previous_status.value,
                "new_status": new_status.value,
                "confidence": confidence_level.value,
                "user_id": user_id,
            },
        )

        return VerificationResult(
            rewrite_id=rewrite_id,
            previous_status=previous_status,
            new_status=new_status,
            verified_by=user_email or user_id,
            verified_at=record.created_at,
            notes=request.notes,
        )

    def get_verification_status(
        self,
        rewrite_id: str,
    ) -> VerificationStatus:
        """Get the current verification status of a rewrite.

        Args:
            rewrite_id: ID of the rewrite

        Returns:
            Current VerificationStatus
        """
        return self._rewrite_statuses.get(rewrite_id, VerificationStatus.PENDING)

    def get_verification_history(
        self,
        rewrite_id: str,
    ) -> list[VerificationRecord]:
        """Get verification history for a rewrite.

        Args:
            rewrite_id: ID of the rewrite

        Returns:
            List of VerificationRecords
        """
        return [
            record for record in self._verification_records.values()
            if record.rewrite_id == rewrite_id
        ]

    def generate_rejected_placeholder(
        self,
        sp_name: str,
        user_email: Optional[str] = None,
        rejection_notes: Optional[str] = None,
    ) -> str:
        """Generate placeholder SQL for a rejected conversion.

        Args:
            sp_name: Name of the rejected SP
            user_email: Email of user who rejected
            rejection_notes: Notes from the rejection

        Returns:
            Placeholder SQL with TODO comments
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines = [
            "-- =============================================",
            "-- TODO: Manual conversion required",
            f"-- Original SP: {sp_name}",
            "-- Reason: AI conversion rejected by user",
        ]

        if user_email:
            lines.append(f"-- Rejected by: {user_email}")

        lines.append(f"-- Rejected at: {timestamp}")

        if rejection_notes:
            lines.append(f"-- Notes: {rejection_notes}")

        lines.extend([
            "-- =============================================",
            "",
            "-- Placeholder query (replace with manual conversion):",
            "SELECT",
            "    'MANUAL_CONVERSION_REQUIRED' as status,",
            f"    '{sp_name}' as original_sp",
            ";",
        ])

        return "\n".join(lines)


# Global service instance
_flagging_service: Optional[ConversionFlaggingService] = None


def get_flagging_service() -> ConversionFlaggingService:
    """Get the global flagging service instance."""
    global _flagging_service
    if _flagging_service is None:
        _flagging_service = ConversionFlaggingService()
    return _flagging_service
