# Story 4.3: Report Classification and Scoring Engine

Status: done

## Story

As the **system**,
I want **to classify reports and calculate conversion scores**,
So that **users can quickly understand conversion complexity**.

## Acceptance Criteria

### AC1: Report Type Classification
**Given** extracted features from RDL parsing
**When** classification runs
**Then** the report is categorized as one of:
  - **Tabular**: Primarily tables, simple grouping, no complex visuals
  - **Analytical**: Charts, gauges, KPIs, moderate expressions
  - **Mixed**: Combination of tabular and analytical elements
  - **Complex**: Subreports, maps, extensive custom code, recursive hierarchies

### AC2: Conversion Score Calculation with Weighted Penalties
**Given** extracted features
**When** calculating conversion score
**Then** a percentage score (0-100%) is calculated using weighted penalties:
  - Stored procedures: -15% each
  - Subreports: -20% each
  - Custom VB code: -25% per function
  - RunningValue expressions: -10% each
  - Maps/Gauges: -15% each
  - Recursive groups: -10% each
  - Base score starts at 100%

### AC3: Status Assignment Based on Score Thresholds
**Given** a calculated score
**When** determining status
**Then** the status is assigned as:
  - **Green (70-100%)**: High conversion confidence
  - **Yellow (40-69%)**: Moderate complexity, manual work required
  - **Red (0-39%)**: Significant manual work, review recommended

### AC4: Store Classification and Scoring Results
**Given** classification and scoring complete
**When** storing results
**Then** the following are saved:
  - Report type classification
  - Conversion score percentage
  - Status (green/yellow/red)
  - Feature breakdown with individual penalties
  - Timestamp of analysis

## Tasks / Subtasks

- [x] **Task 1: Create Classification Engine Service** (AC: 1)
  - [x] Create `backend/app/services/classification_engine.py`
  - [x] Implement `classify_report(features: AnalysisFeatures) -> ReportClassification`
  - [x] Define classification rules based on visual mix
  - [x] Handle edge cases (empty reports, single visual)

- [x] **Task 2: Implement Report Type Classification Logic** (AC: 1)
  - [x] Define Tabular criteria: >70% tables/matrices, no charts/gauges
  - [x] Define Analytical criteria: >50% charts/gauges, KPI indicators
  - [x] Define Mixed criteria: 30-70% mix of tabular and analytical
  - [x] Define Complex criteria: subreports, maps, custom code, recursive groups

- [x] **Task 3: Create Scoring Engine Service** (AC: 2)
  - [x] Create `backend/app/services/scoring_engine.py`
  - [x] Implement `calculate_score(features: AnalysisFeatures) -> ScoreBreakdown`
  - [x] Apply weighted penalties from configuration
  - [x] Calculate final score (minimum 0%)

- [x] **Task 4: Implement Penalty Calculations** (AC: 2)
  - [x] Count stored procedures and apply -15% each (capped at 45%)
  - [x] Count subreports and apply -20% each (capped at 40%)
  - [x] Count VB custom functions and apply -25% each (capped at 50%)
  - [x] Count RunningValue expressions and apply -10% each (capped at 30%)
  - [x] Count maps/gauges and apply -15% each (capped at 30% each)
  - [x] Detect recursive groups and apply -10% each (capped at 20%)

- [x] **Task 5: Implement Status Assignment** (AC: 3)
  - [x] Create `assign_status(score: int) -> ConversionStatus`
  - [x] Define threshold constants (GREEN=70, YELLOW=40)
  - [x] Return appropriate status enum value

- [x] **Task 6: Create Score Breakdown Model** (AC: 4)
  - [x] Create `ScoreBreakdown` Pydantic model
  - [x] Include base score, each penalty applied
  - [x] Store penalty reasons with item names
  - [x] Calculate subtotals by category with `penalties_by_category()` and `category_totals()`

- [x] **Task 7: Update Analysis Service** (AC: 4)
  - [x] Integrate classification and scoring engines
  - [x] Store score breakdown as JSON in Analysis model
  - [x] Include analysis timestamp (already in model)

- [x] **Task 8: Unit Testing** (AC: 1, 2, 3, 4)
  - [x] Test each classification type with sample features (8 tests)
  - [x] Test penalty calculations accuracy (11 tests)
  - [x] Test score boundary conditions (0%, 100%)
  - [x] Test status threshold assignments (4 tests)
  - [x] Test complete analyze_report function (3 tests)
  - [x] Test ScoreBreakdown functionality (3 tests)

## Dev Notes

### Technical Implementation

**Classification Rules:**
```python
from enum import Enum
from typing import Dict

class ReportClassification(str, Enum):
    TABULAR = "Tabular"
    ANALYTICAL = "Analytical"
    MIXED = "Mixed"
    COMPLEX = "Complex"

class ClassificationEngine:
    def classify(self, features: AnalysisFeatures) -> ReportClassification:
        # Complex indicators take priority
        if self._is_complex(features):
            return ReportClassification.COMPLEX

        tabular_ratio = self._calculate_tabular_ratio(features)
        analytical_ratio = self._calculate_analytical_ratio(features)

        if tabular_ratio > 0.7 and analytical_ratio < 0.1:
            return ReportClassification.TABULAR
        elif analytical_ratio > 0.5:
            return ReportClassification.ANALYTICAL
        else:
            return ReportClassification.MIXED

    def _is_complex(self, features: AnalysisFeatures) -> bool:
        """Check for complex report indicators."""
        return (
            features.subreport_count > 0 or
            any(v.type == VisualType.MAP for v in features.visuals) or
            len(features.custom_code_functions) > 2 or
            any(v.has_recursive_group for v in features.visuals)
        )

    def _calculate_tabular_ratio(self, features: AnalysisFeatures) -> float:
        """Ratio of tables/matrices to total visuals."""
        if not features.visuals:
            return 0.0
        tabular_types = {VisualType.TABLE, VisualType.MATRIX}
        tabular_count = sum(1 for v in features.visuals if v.type in tabular_types)
        return tabular_count / len(features.visuals)

    def _calculate_analytical_ratio(self, features: AnalysisFeatures) -> float:
        """Ratio of charts/gauges to total visuals."""
        if not features.visuals:
            return 0.0
        analytical_types = {VisualType.CHART, VisualType.GAUGE}
        analytical_count = sum(1 for v in features.visuals if v.type in analytical_types)
        return analytical_count / len(features.visuals)
```

**Scoring Engine with Weighted Penalties:**
```python
from dataclasses import dataclass
from typing import List

@dataclass
class PenaltyItem:
    category: str
    item_name: str
    penalty_percent: int
    reason: str

@dataclass
class ScoreBreakdown:
    base_score: int = 100
    penalties: List[PenaltyItem] = None
    final_score: int = 0

    def __post_init__(self):
        if self.penalties is None:
            self.penalties = []

class ScoringEngine:
    # Penalty weights (configurable)
    PENALTIES = {
        'stored_procedure': 15,
        'subreport': 20,
        'custom_vb_function': 25,
        'running_value': 10,
        'map': 15,
        'gauge': 15,
        'recursive_group': 10,
    }

    def calculate_score(self, features: AnalysisFeatures) -> ScoreBreakdown:
        breakdown = ScoreBreakdown()

        # Apply stored procedure penalties
        for ds in features.datasets:
            if ds.query_type == QueryType.STORED_PROCEDURE:
                breakdown.penalties.append(PenaltyItem(
                    category='stored_procedure',
                    item_name=ds.stored_procedure_name or ds.name,
                    penalty_percent=self.PENALTIES['stored_procedure'],
                    reason=f"Stored procedure in dataset '{ds.name}'"
                ))

        # Apply subreport penalties
        for v in features.visuals:
            if v.type == VisualType.SUBREPORT:
                breakdown.penalties.append(PenaltyItem(
                    category='subreport',
                    item_name=v.name,
                    penalty_percent=self.PENALTIES['subreport'],
                    reason=f"Subreport '{v.name}' requires separate conversion"
                ))

            if v.type == VisualType.MAP:
                breakdown.penalties.append(PenaltyItem(
                    category='map',
                    item_name=v.name,
                    penalty_percent=self.PENALTIES['map'],
                    reason=f"Map visual '{v.name}' not supported in Power BI"
                ))

            if v.type == VisualType.GAUGE:
                breakdown.penalties.append(PenaltyItem(
                    category='gauge',
                    item_name=v.name,
                    penalty_percent=self.PENALTIES['gauge'],
                    reason=f"Gauge visual '{v.name}' requires manual recreation"
                ))

            if v.has_recursive_group:
                breakdown.penalties.append(PenaltyItem(
                    category='recursive_group',
                    item_name=v.name,
                    penalty_percent=self.PENALTIES['recursive_group'],
                    reason=f"Recursive hierarchy in '{v.name}'"
                ))

        # Apply custom VB function penalties
        for func_name in features.custom_code_functions:
            breakdown.penalties.append(PenaltyItem(
                category='custom_vb_function',
                item_name=func_name,
                penalty_percent=self.PENALTIES['custom_vb_function'],
                reason=f"Custom VB function '{func_name}' requires DAX conversion"
            ))

        # Apply RunningValue penalties
        for expr in features.expressions:
            if expr.category == ExpressionCategory.RUNNING_VALUE:
                breakdown.penalties.append(PenaltyItem(
                    category='running_value',
                    item_name=expr.item_name,
                    penalty_percent=self.PENALTIES['running_value'],
                    reason=f"RunningValue expression at '{expr.location}'"
                ))

        # Calculate final score
        total_penalty = sum(p.penalty_percent for p in breakdown.penalties)
        breakdown.final_score = max(0, breakdown.base_score - total_penalty)

        return breakdown
```

**Status Assignment:**
```python
class ConversionStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class StatusThresholds:
    GREEN_MIN = 70
    YELLOW_MIN = 40

def assign_status(score: int) -> ConversionStatus:
    if score >= StatusThresholds.GREEN_MIN:
        return ConversionStatus.GREEN
    elif score >= StatusThresholds.YELLOW_MIN:
        return ConversionStatus.YELLOW
    else:
        return ConversionStatus.RED
```

**Pydantic Models:**
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PenaltyItemSchema(BaseModel):
    category: str
    item_name: str
    penalty_percent: int
    reason: str

class ScoreBreakdownSchema(BaseModel):
    base_score: int = 100
    penalties: List[PenaltyItemSchema] = []
    final_score: int
    total_penalty: int

    @property
    def total_penalty(self) -> int:
        return sum(p.penalty_percent for p in self.penalties)

class ClassificationResult(BaseModel):
    classification: ReportClassification
    score: int
    status: ConversionStatus
    breakdown: ScoreBreakdownSchema
    analysis_timestamp: datetime
```

### Scoring Configuration

| Complexity Item | Penalty | Rationale |
|----------------|---------|-----------|
| Stored Procedure | -15% | Requires SQL rewrite |
| Subreport | -20% | Separate conversion needed |
| Custom VB Function | -25% | Manual DAX conversion |
| RunningValue | -10% | Complex aggregation pattern |
| Map Visual | -15% | No direct Power BI equivalent |
| Gauge Visual | -15% | Requires manual recreation |
| Recursive Group | -10% | Complex hierarchy handling |

### Status Thresholds

| Status | Score Range | Meaning |
|--------|-------------|---------|
| Green | 70-100% | High confidence, minimal manual work |
| Yellow | 40-69% | Moderate complexity, some manual work |
| Red | 0-39% | Significant manual work required |

### File Structure

```
backend/app/
  services/
    classification_engine.py  # Report classification
    scoring_engine.py         # Score calculation
  schemas/
    classification.py         # Result models
```

### Dependencies

- Story 4.2 (RDL Parsing) - Provides AnalysisFeatures

### References

- [Source: epics.md#Story 4.3] - Original story definition
- [Source: prd.md#FR11, FR12, FR13] - Classification and scoring requirements

### Architecture Compliance Checklist

- [x] Services are stateless and testable
- [x] Configuration values are externalized (PenaltyWeights, StatusThresholds)
- [x] Pydantic models validate all inputs
- [x] Score breakdown provides transparency (per-item penalties with reasons)
- [x] Status thresholds are clearly defined and configurable

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created comprehensive classification engine with visual ratio calculations
- Implemented 5 classification types: Simple, Tabular, Analytical, Mixed, Complex
- Created scoring engine with configurable penalty weights and caps
- Implemented 9 penalty categories with per-category caps to prevent excessive penalties
- Created StatusThresholds for configurable green/yellow/red assignment
- Built complete ClassificationResult model with breakdown, ratios, and complexity indicators
- Integrated new engines into analysis_service.py with backward compatibility
- Created 29 comprehensive unit tests covering all scenarios

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-01-22 | Create classification schemas | backend/app/schemas/classification.py |
| 2026-01-22 | Create classification engine | backend/app/services/classification_engine.py |
| 2026-01-22 | Create scoring engine | backend/app/services/scoring_engine.py |
| 2026-01-22 | Update analysis_service to use engines | backend/app/services/analysis_service.py |
| 2026-01-22 | Add classification and scoring tests | backend/tests/test_classification_scoring.py |

### File List

**Backend:**
- app/schemas/classification.py (new) - Pydantic models for classification results
- app/services/classification_engine.py (new) - Report classification logic
- app/services/scoring_engine.py (new) - Score calculation with penalties
- app/services/analysis_service.py (modified) - Integrated new engines
- tests/test_classification_scoring.py (new) - 29 unit tests
