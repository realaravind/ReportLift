"""Classification and Scoring Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class ReportClassification(str, Enum):
    """Report type classification based on visual composition."""

    SIMPLE = "Simple"
    TABULAR = "Tabular"
    ANALYTICAL = "Analytical"
    MIXED = "Mixed"
    COMPLEX = "Complex"


class ConversionStatus(str, Enum):
    """Conversion readiness status based on score."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class PenaltyCategory(str, Enum):
    """Categories of scoring penalties."""

    STORED_PROCEDURE = "stored_procedure"
    SUBREPORT = "subreport"
    CUSTOM_VB_FUNCTION = "custom_vb_function"
    RUNNING_VALUE = "running_value"
    MAP = "map"
    GAUGE = "gauge"
    RECURSIVE_GROUP = "recursive_group"
    LOOKUP = "lookup"
    COMPLEX_EXPRESSION = "complex_expression"


class PenaltyItem(BaseModel):
    """Individual penalty applied to the score."""

    category: PenaltyCategory
    item_name: str
    penalty_percent: int
    reason: str


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of score calculation."""

    base_score: int = 100
    penalties: list[PenaltyItem] = Field(default_factory=list)
    final_score: int = 0

    @computed_field
    @property
    def total_penalty(self) -> int:
        """Total penalty deducted from base score."""
        return sum(p.penalty_percent for p in self.penalties)

    @computed_field
    @property
    def penalty_count(self) -> int:
        """Total number of penalties applied."""
        return len(self.penalties)

    def penalties_by_category(self) -> dict[str, list[PenaltyItem]]:
        """Group penalties by category."""
        result: dict[str, list[PenaltyItem]] = {}
        for penalty in self.penalties:
            category = penalty.category.value
            if category not in result:
                result[category] = []
            result[category].append(penalty)
        return result

    def category_totals(self) -> dict[str, int]:
        """Get total penalty per category."""
        totals: dict[str, int] = {}
        for penalty in self.penalties:
            category = penalty.category.value
            if category not in totals:
                totals[category] = 0
            totals[category] += penalty.penalty_percent
        return totals


class ClassificationResult(BaseModel):
    """Complete classification and scoring result."""

    classification: ReportClassification
    score: int
    status: ConversionStatus
    breakdown: ScoreBreakdown
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Classification rationale
    tabular_ratio: float = 0.0
    analytical_ratio: float = 0.0
    complexity_indicators: list[str] = Field(default_factory=list)

    def to_storage_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "classification": self.classification.value,
            "score": self.score,
            "status": self.status.value,
            "breakdown": self.breakdown.model_dump(),
            "tabular_ratio": self.tabular_ratio,
            "analytical_ratio": self.analytical_ratio,
            "complexity_indicators": self.complexity_indicators,
        }


class StatusThresholds(BaseModel):
    """Configurable thresholds for status assignment."""

    green_min: int = 70
    yellow_min: int = 40

    def get_status(self, score: int) -> ConversionStatus:
        """Determine status based on score."""
        if score >= self.green_min:
            return ConversionStatus.GREEN
        elif score >= self.yellow_min:
            return ConversionStatus.YELLOW
        else:
            return ConversionStatus.RED


class PenaltyWeights(BaseModel):
    """Configurable penalty weights for scoring."""

    stored_procedure: int = 15
    subreport: int = 20
    custom_vb_function: int = 25
    running_value: int = 10
    map: int = 15
    gauge: int = 15
    recursive_group: int = 10
    lookup: int = 5
    complex_expression: int = 3

    # Maximum penalties per category (caps)
    max_stored_procedure: int = 45  # Max 3 SPs
    max_subreport: int = 40  # Max 2 subreports
    max_custom_vb_function: int = 50  # Max 2 functions
    max_running_value: int = 30  # Max 3 running values
    max_map: int = 30  # Max 2 maps
    max_gauge: int = 30  # Max 2 gauges
    max_recursive_group: int = 20  # Max 2 recursive groups
    max_lookup: int = 15  # Max 3 lookups
    max_complex_expression: int = 15  # Max 5 complex expressions

    def get_penalty(self, category: PenaltyCategory) -> int:
        """Get penalty weight for a category."""
        weights = {
            PenaltyCategory.STORED_PROCEDURE: self.stored_procedure,
            PenaltyCategory.SUBREPORT: self.subreport,
            PenaltyCategory.CUSTOM_VB_FUNCTION: self.custom_vb_function,
            PenaltyCategory.RUNNING_VALUE: self.running_value,
            PenaltyCategory.MAP: self.map,
            PenaltyCategory.GAUGE: self.gauge,
            PenaltyCategory.RECURSIVE_GROUP: self.recursive_group,
            PenaltyCategory.LOOKUP: self.lookup,
            PenaltyCategory.COMPLEX_EXPRESSION: self.complex_expression,
        }
        return weights.get(category, 0)

    def get_max_penalty(self, category: PenaltyCategory) -> int:
        """Get maximum penalty cap for a category."""
        caps = {
            PenaltyCategory.STORED_PROCEDURE: self.max_stored_procedure,
            PenaltyCategory.SUBREPORT: self.max_subreport,
            PenaltyCategory.CUSTOM_VB_FUNCTION: self.max_custom_vb_function,
            PenaltyCategory.RUNNING_VALUE: self.max_running_value,
            PenaltyCategory.MAP: self.max_map,
            PenaltyCategory.GAUGE: self.max_gauge,
            PenaltyCategory.RECURSIVE_GROUP: self.max_recursive_group,
            PenaltyCategory.LOOKUP: self.max_lookup,
            PenaltyCategory.COMPLEX_EXPRESSION: self.max_complex_expression,
        }
        return caps.get(category, 100)
