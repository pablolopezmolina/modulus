"""
Risk Analysis Module for MODULUS.

Session 5.2: Basic Risk Map (original)
Session 10.1: Full Risk Map with 6 segmentations (extended)

This module provides:
- RiskThresholds: Configurable thresholds for risk classification
- RiskMetric: Individual risk measurement with severity level
- RiskMap: Matrix of segment × risk for visualization
- DangerZone: Identification of high-risk population segments
- RiskAnalyzer: Main analyzer class
- RiskAnalysisResult: Complete risk analysis output

NEW in Session 10.1:
- SegmentationType: Enum for 6 segmentation dimensions
- RiskType: Enum for risk types
- SegmentClassifier: Classifies individuals across all dimensions
- RiskMatrixCell: Immutable cell with danger zone flag
- RiskMatrix: Full 6-dimensional risk matrix
- FullRiskMapAnalyzer: Analyzer for complete risk matrix
- DangerZoneDetector: Identifies high-risk cells

The module consumes PopulationDayResult (from session 5.1) and produces
structured risk analysis for the Decision Engine (session 6.1).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __lt__(self, other: "RiskLevel") -> bool:
        """Enable comparison between risk levels."""
        order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
        return order[self] < order[other]

    def __le__(self, other: "RiskLevel") -> bool:
        return self == other or self < other

    def __gt__(self, other: "RiskLevel") -> bool:
        return not self <= other

    def __ge__(self, other: "RiskLevel") -> bool:
        return not self < other

    @classmethod
    def from_percentage(cls, pct: float, low_threshold: float = 10.0, high_threshold: float = 25.0) -> "RiskLevel":
        """Get risk level from percentage value."""
        if pct < low_threshold:
            return cls.LOW
        elif pct >= high_threshold:
            return cls.HIGH
        else:
            return cls.MEDIUM


class SegmentationType(Enum):
    """
    Segmentation dimensions for population analysis.
    
    Session 10.1: Extended from 3 to 6 segmentations.
    """
    # Original 3 segmentations (Pack 1)
    BMI = "by_bmi"
    AGE = "by_age"
    CAFFEINE_SENSITIVITY = "by_caffeine_sensitivity"
    
    # New 3 segmentations (Pack 2)
    INSULIN_SENSITIVITY = "by_insulin_sensitivity"
    ACTIVITY_LEVEL = "by_activity_level"
    HABITUAL_CAFFEINE = "by_habitual_caffeine"


class RiskType(Enum):
    """
    Types of risks evaluated.
    
    Session 10.1: Formalized risk types.
    """
    HYPERGLYCEMIA = "pct_hyperglycemia"
    SEVERE_HYPERGLYCEMIA = "pct_severe_hyperglycemia"
    HYPOGLYCEMIA = "pct_hypoglycemia"
    JITTER = "pct_jitter_risk"
    SLEEP_DISRUPTION = "pct_sleep_disruption"
    CRASH = "pct_crash_risk"


# =============================================================================
# SEGMENT VALUES
# =============================================================================

# Segment value definitions for each segmentation type
SEGMENT_VALUES = {
    SegmentationType.BMI: ["normal", "overweight", "obese"],
    SegmentationType.AGE: ["young", "middle", "older"],
    SegmentationType.CAFFEINE_SENSITIVITY: ["slow", "normal", "fast"],
    SegmentationType.INSULIN_SENSITIVITY: ["sensitive", "normal", "resistant"],
    SegmentationType.ACTIVITY_LEVEL: ["sedentary", "moderate", "active"],
    SegmentationType.HABITUAL_CAFFEINE: ["naive", "moderate", "heavy"],
}


# =============================================================================
# RISK THRESHOLDS
# =============================================================================

@dataclass(frozen=True)
class RiskThresholds:
    """
    Configurable thresholds for risk assessment.

    These define:
    1. Physiological thresholds (what triggers a risk)
    2. Classification thresholds (what % is low/medium/high)
    """

    # Physiological thresholds
    hyperglycemia_threshold_mg_dl: float = 140.0
    severe_hyperglycemia_threshold_mg_dl: float = 180.0
    jitter_caffeine_threshold_mg_l: float = 4.0
    sleep_caffeine_threshold_mg_l: float = 1.0
    sleep_check_time_minutes: float = 1320  # 22:00
    crash_alertness_drop_pct: float = 30.0
    crash_window_minutes: float = 120

    # Classification thresholds (% of population)
    risk_level_low_threshold: float = 10.0  # <10% = LOW
    risk_level_high_threshold: float = 25.0  # >=25% = HIGH, 10-25% = MEDIUM

    def __post_init__(self):
        """Validate thresholds."""
        # Check positive values
        positive_fields = [
            "hyperglycemia_threshold_mg_dl",
            "severe_hyperglycemia_threshold_mg_dl",
            "jitter_caffeine_threshold_mg_l",
            "sleep_caffeine_threshold_mg_l",
            "crash_alertness_drop_pct",
            "crash_window_minutes",
        ]
        for field_name in positive_fields:
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")

        # Check sleep check time in valid range
        if not 0 <= self.sleep_check_time_minutes <= 1440:
            raise ValueError(
                f"sleep_check_time_minutes must be in [0, 1440], got {self.sleep_check_time_minutes}"
            )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "hyperglycemia_threshold_mg_dl": self.hyperglycemia_threshold_mg_dl,
            "severe_hyperglycemia_threshold_mg_dl": self.severe_hyperglycemia_threshold_mg_dl,
            "jitter_caffeine_threshold_mg_l": self.jitter_caffeine_threshold_mg_l,
            "sleep_caffeine_threshold_mg_l": self.sleep_caffeine_threshold_mg_l,
            "sleep_check_time_minutes": self.sleep_check_time_minutes,
            "crash_alertness_drop_pct": self.crash_alertness_drop_pct,
            "crash_window_minutes": self.crash_window_minutes,
            "risk_level_low_threshold": self.risk_level_low_threshold,
            "risk_level_high_threshold": self.risk_level_high_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "RiskThresholds":
        """Create from dictionary."""
        return cls(**data)


def create_default_thresholds() -> RiskThresholds:
    """Factory for default risk thresholds."""
    return RiskThresholds()


# =============================================================================
# RISK METRIC
# =============================================================================

@dataclass(frozen=True)
class RiskMetric:
    """
    A single risk measurement with severity classification.

    Attributes:
        name: Internal identifier (e.g., "pct_hyperglycemia")
        display_name: Human-readable name
        value: The risk percentage (0-100)
        threshold_low: Below this = LOW risk
        threshold_high: At or above this = HIGH risk
        description: Optional explanation
    """

    name: str
    display_name: str
    value: float
    threshold_low: float = 10.0
    threshold_high: float = 25.0
    description: str = ""

    @property
    def level(self) -> RiskLevel:
        """Determine risk level based on value and thresholds."""
        if self.value < self.threshold_low:
            return RiskLevel.LOW
        elif self.value >= self.threshold_high:
            return RiskLevel.HIGH
        else:
            return RiskLevel.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "value": self.value,
            "level": self.level.value.upper(),
            "threshold_low": self.threshold_low,
            "threshold_high": self.threshold_high,
            "description": self.description,
        }


# =============================================================================
# SEGMENT RISK
# =============================================================================

@dataclass(frozen=True)
class SegmentRisk:
    """
    Risk for a specific population segment.

    Represents one cell in the risk map matrix.
    """

    segment_dimension: str  # e.g., "bmi", "age", "caffeine_sensitivity"
    segment_value: str  # e.g., "obese", "young", "slow"
    risk_name: str  # e.g., "pct_hyperglycemia"
    value: float  # Risk percentage for this segment
    population_pct: float  # What % of total population is in this segment
    count: int  # Number of individuals in this segment

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "segment_dimension": self.segment_dimension,
            "segment_value": self.segment_value,
            "risk_name": self.risk_name,
            "value": self.value,
            "population_pct": self.population_pct,
            "count": self.count,
        }


# =============================================================================
# RISK MAP (Original API)
# =============================================================================

@dataclass
class RiskMap:
    """
    Matrix of segment × risk values.

    Enables visualization of which segments have highest risk for each metric.
    """

    dimensions: List[str]  # e.g., ["by_bmi", "by_age", "by_caffeine_sensitivity"]
    risk_names: List[str]  # e.g., ["pct_hyperglycemia", "pct_sleep_disruption"]
    cells: Dict[Tuple[str, str, str], float]  # (dimension, value, risk) -> percentage
    segment_values: Dict[str, List[str]] = field(default_factory=dict)

    def get_value(
        self, dimension: str, segment_value: str, risk_name: str
    ) -> Optional[float]:
        """Get risk value for a specific cell."""
        key = (dimension, segment_value, risk_name)
        return self.cells.get(key)

    def get_segment_risks(
        self, dimension: str, segment_value: str
    ) -> Dict[str, float]:
        """Get all risks for a specific segment."""
        result = {}
        for (dim, val, risk), value in self.cells.items():
            if dim == dimension and val == segment_value:
                result[risk] = value
        return result

    def get_risk_across_segments(
        self, dimension: str, risk_name: str
    ) -> Dict[str, float]:
        """Get a specific risk across all values in a dimension."""
        result = {}
        for (dim, val, risk), value in self.cells.items():
            if dim == dimension and risk == risk_name:
                result[val] = value
        return result

    def to_matrix(self, dimension: str) -> Dict[str, Any]:
        """
        Convert to matrix format for visualization.

        Returns:
            {
                "rows": ["normal", "overweight", "obese"],
                "columns": ["pct_hyperglycemia", "pct_jitter", ...],
                "values": [[10, 5], [20, 8], [35, 10]]
            }
        """
        if dimension not in self.segment_values:
            # Try to infer from cells
            segment_vals = sorted(set(
                val for (dim, val, _) in self.cells.keys() if dim == dimension
            ))
        else:
            segment_vals = self.segment_values[dimension]

        rows = segment_vals
        columns = self.risk_names

        values = []
        for seg_val in rows:
            row = []
            for risk in columns:
                val = self.get_value(dimension, seg_val, risk)
                row.append(val if val is not None else 0.0)
            values.append(row)

        return {
            "dimension": dimension,
            "rows": rows,
            "columns": columns,
            "values": values,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dimensions": self.dimensions,
            "risk_names": self.risk_names,
            "cells": {
                f"{dim}|{val}|{risk}": value
                for (dim, val, risk), value in self.cells.items()
            },
            "segment_values": self.segment_values,
        }


# =============================================================================
# DANGER ZONE
# =============================================================================

@dataclass(frozen=True)
class DangerZone:
    """
    A specific segment with unacceptably high risk.

    Danger zones are flagged for special attention in reports
    and recommendations.
    """

    segment_dimension: str
    segment_value: str
    risk_name: str
    risk_value: float
    population_pct: float
    severity_score: float  # risk_value * (population_pct / 100)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "segment_dimension": self.segment_dimension,
            "segment_value": self.segment_value,
            "risk_name": self.risk_name,
            "risk_value": self.risk_value,
            "population_pct": self.population_pct,
            "severity_score": self.severity_score,
            "recommendation": self.recommendation,
        }


# =============================================================================
# RISK ANALYSIS RESULT
# =============================================================================

@dataclass
class RiskAnalysisResult:
    """
    Complete result of risk analysis.

    This is the primary output of RiskAnalyzer and feeds into
    the DecisionEngine.
    """

    n_individuals: int
    metrics: List[RiskMetric]
    risk_map: RiskMap
    danger_zones: List[DangerZone]
    thresholds: RiskThresholds

    @property
    def highest_risk(self) -> Optional[RiskMetric]:
        """Get the metric with highest risk value."""
        if not self.metrics:
            return None
        return max(self.metrics, key=lambda m: m.value)

    @property
    def overall_risk_level(self) -> RiskLevel:
        """
        Determine overall risk level.

        Based on the highest individual risk level.
        """
        if not self.metrics:
            return RiskLevel.LOW
        return max(m.level for m in self.metrics)

    def get_top_risks(self, n: int = 5) -> List[RiskMetric]:
        """Get top N risks sorted by value."""
        return sorted(self.metrics, key=lambda m: m.value, reverse=True)[:n]

    def get_segments_at_risk(
        self, min_risk_pct: float = 25.0
    ) -> List[SegmentRisk]:
        """
        Get segments with risk above threshold.

        Returns list of SegmentRisk objects sorted by risk value.
        """
        segments = []
        for (dim, val, risk), value in self.risk_map.cells.items():
            if value >= min_risk_pct:
                # Get population info if available
                segments.append(SegmentRisk(
                    segment_dimension=dim,
                    segment_value=val,
                    risk_name=risk,
                    value=value,
                    population_pct=0.0,  # Not always available
                    count=0,
                ))
        return sorted(segments, key=lambda s: s.value, reverse=True)

    def get_summary(self) -> str:
        """Generate a text summary of risk analysis."""
        if not self.metrics:
            return "No risk data available."

        highest = self.highest_risk
        level = self.overall_risk_level

        summary_parts = [
            f"Risk Analysis Summary (N={self.n_individuals:,})",
            f"Overall Risk Level: {level.value.upper()}",
        ]

        if highest:
            summary_parts.append(
                f"Highest Risk: {highest.display_name} at {highest.value:.1f}%"
            )

        if self.danger_zones:
            summary_parts.append(f"Danger Zones Identified: {len(self.danger_zones)}")

        return "\n".join(summary_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "n_individuals": self.n_individuals,
            "overall_risk_level": self.overall_risk_level.value,
            "metrics": [m.to_dict() for m in self.metrics],
            "risk_map": self.risk_map.to_dict(),
            "danger_zones": [dz.to_dict() for dz in self.danger_zones],
            "thresholds": self.thresholds.to_dict(),
        }


# =============================================================================
# RISK ANALYZER (Original API)
# =============================================================================

# Risk metric definitions
RISK_METRIC_DEFINITIONS = {
    "pct_hyperglycemia": {
        "display_name": "Hyperglycemia Risk",
        "description": "Percentage of population with glucose > 140 mg/dL at any point",
    },
    "pct_severe_hyperglycemia": {
        "display_name": "Severe Hyperglycemia Risk",
        "description": "Percentage of population with glucose > 180 mg/dL",
    },
    "pct_jitter_risk": {
        "display_name": "Jitter/Anxiety Risk",
        "description": "Percentage with caffeine concentration > 4 mg/L",
    },
    "pct_sleep_disruption": {
        "display_name": "Sleep Disruption Risk",
        "description": "Percentage with significant caffeine at bedtime (22:00)",
    },
    "pct_crash_risk": {
        "display_name": "Energy Crash Risk",
        "description": "Percentage experiencing >30% alertness drop within 2 hours",
    },
}

# Recommendations for danger zones
DANGER_ZONE_RECOMMENDATIONS = {
    ("by_bmi", "obese", "pct_hyperglycemia"): (
        "Consider reducing carbohydrate content or adding fiber "
        "to slow glucose absorption for high-BMI consumers."
    ),
    ("by_bmi", "obese", "pct_severe_hyperglycemia"): (
        "Add prominent warning label: 'Not recommended for individuals with "
        "diabetes or prediabetes.' Consider reformulation."
    ),
    ("by_caffeine_sensitivity", "slow", "pct_sleep_disruption"): (
        "Add timing recommendation: 'Take before 2 PM' for caffeine-sensitive "
        "individuals. Consider reduced-caffeine variant."
    ),
    ("by_caffeine_sensitivity", "slow", "pct_jitter_risk"): (
        "Reduce caffeine dose or add L-Theanine to reduce jitter in "
        "slow caffeine metabolizers."
    ),
    ("by_age", "older", "pct_hyperglycemia"): (
        "Consider age-specific dosing guidance. Older adults may benefit "
        "from reduced carbohydrate portions."
    ),
    # New recommendations for extended segmentations (Session 10.1)
    ("by_insulin_sensitivity", "resistant", "pct_hyperglycemia"): (
        "Consider reformulation for insulin-resistant consumers. "
        "Add fiber or reduce simple carbohydrates."
    ),
    ("by_insulin_sensitivity", "resistant", "pct_severe_hyperglycemia"): (
        "Strong warning for diabetic/prediabetic consumers. "
        "Consider separate low-glycemic product line."
    ),
    ("by_activity_level", "sedentary", "pct_hyperglycemia"): (
        "Recommend consuming with physical activity. "
        "Consider reduced-carbohydrate version for sedentary users."
    ),
    ("by_habitual_caffeine", "naive", "pct_jitter_risk"): (
        "Include warning for caffeine-naive consumers. "
        "Suggest starting with half serving."
    ),
    ("by_habitual_caffeine", "naive", "pct_sleep_disruption"): (
        "Caffeine-naive users should avoid afternoon consumption. "
        "Add prominent timing guidance."
    ),
}


class RiskAnalyzer:
    """
    Main analyzer for population risk assessment.

    Takes raw risk data from PopulationDayResult and produces
    a structured RiskAnalysisResult with:
    - Classified risk metrics
    - Risk map by segment
    - Identified danger zones
    - Recommendations
    """

    def __init__(self, thresholds: Optional[RiskThresholds] = None):
        """
        Initialize analyzer.

        Args:
            thresholds: Optional custom thresholds. Uses defaults if not provided.
        """
        self.thresholds = thresholds or create_default_thresholds()

    def analyze(
        self,
        risk_analysis: Dict[str, float],
        subgroup_analysis: Dict[str, Dict[str, Any]],
        n_individuals: int,
    ) -> RiskAnalysisResult:
        """
        Perform complete risk analysis.

        Args:
            risk_analysis: Dict of risk_name -> percentage from PopulationDayResult
            subgroup_analysis: Dict of dimension -> segment data from PopulationDayResult
            n_individuals: Total population size

        Returns:
            RiskAnalysisResult with all analysis components
        """
        # Build risk metrics
        metrics = self._build_risk_metrics(risk_analysis)

        # Build risk map
        risk_map = self._build_risk_map(subgroup_analysis, list(risk_analysis.keys()))

        # Identify danger zones
        danger_zones = self._identify_danger_zones(subgroup_analysis, risk_map)

        return RiskAnalysisResult(
            n_individuals=n_individuals,
            metrics=metrics,
            risk_map=risk_map,
            danger_zones=danger_zones,
            thresholds=self.thresholds,
        )

    def _build_risk_metrics(
        self, risk_analysis: Dict[str, float]
    ) -> List[RiskMetric]:
        """Build list of RiskMetric objects from raw data."""
        metrics = []
        for name, value in risk_analysis.items():
            definition = RISK_METRIC_DEFINITIONS.get(name, {})
            metrics.append(RiskMetric(
                name=name,
                display_name=definition.get("display_name", name.replace("_", " ").title()),
                value=value,
                threshold_low=self.thresholds.risk_level_low_threshold,
                threshold_high=self.thresholds.risk_level_high_threshold,
                description=definition.get("description", ""),
            ))
        return metrics

    def _build_risk_map(
        self,
        subgroup_analysis: Dict[str, Dict[str, Any]],
        risk_names: List[str],
    ) -> RiskMap:
        """Build risk map from subgroup analysis."""
        dimensions = list(subgroup_analysis.keys())
        cells: Dict[Tuple[str, str, str], float] = {}
        segment_values: Dict[str, List[str]] = {}

        for dim, segments in subgroup_analysis.items():
            segment_values[dim] = list(segments.keys())

            for seg_value, seg_data in segments.items():
                # Try to extract risk values from segment metrics
                seg_metrics = seg_data.get("metrics", {})

                # Map metric names to risk names
                risk_mappings = {
                    "glucose_peak_mean": "pct_hyperglycemia",
                    "caffeine_at_2200_mean": "pct_sleep_disruption",
                }

                # For now, we estimate segment risks based on available metrics
                # In a full implementation, we'd track individual risk flags per person
                for metric_name, metric_value in seg_metrics.items():
                    if metric_name in risk_mappings:
                        risk_name = risk_mappings[metric_name]
                        # Estimate risk based on metric value
                        estimated_risk = self._estimate_segment_risk(
                            metric_name, metric_value, dim, seg_value
                        )
                        if estimated_risk is not None:
                            cells[(dim, seg_value, risk_name)] = estimated_risk

        return RiskMap(
            dimensions=dimensions,
            risk_names=risk_names,
            cells=cells,
            segment_values=segment_values,
        )

    def _estimate_segment_risk(
        self,
        metric_name: str,
        metric_value: float,
        dimension: str,
        segment_value: str,
    ) -> Optional[float]:
        """
        Estimate segment-specific risk from aggregate metrics.

        This is a simplified estimation. Full implementation would track
        individual risk flags per person per segment.
        """
        if metric_name == "glucose_peak_mean":
            # Estimate hyperglycemia risk based on mean glucose peak
            # Higher mean -> higher proportion above threshold
            threshold = self.thresholds.hyperglycemia_threshold_mg_dl
            if metric_value < threshold - 20:
                return 5.0  # Low risk
            elif metric_value < threshold:
                return 15.0  # Moderate risk
            elif metric_value < threshold + 20:
                return 35.0  # High risk
            else:
                return 55.0  # Very high risk

        elif metric_name == "caffeine_at_2200_mean":
            # Estimate sleep disruption risk based on caffeine at bedtime
            threshold = self.thresholds.sleep_caffeine_threshold_mg_l
            if metric_value < threshold * 0.5:
                return 5.0
            elif metric_value < threshold:
                return 15.0
            elif metric_value < threshold * 2:
                return 40.0
            else:
                return 70.0

        return None

    def _identify_danger_zones(
        self,
        subgroup_analysis: Dict[str, Dict[str, Any]],
        risk_map: RiskMap,
    ) -> List[DangerZone]:
        """Identify segments with dangerously high risk."""
        danger_zones = []
        danger_threshold = self.thresholds.risk_level_high_threshold

        for (dim, seg_val, risk_name), risk_value in risk_map.cells.items():
            if risk_value >= danger_threshold:
                # Get population percentage for this segment
                pop_pct = 0.0
                if dim in subgroup_analysis and seg_val in subgroup_analysis[dim]:
                    pop_pct = subgroup_analysis[dim][seg_val].get("pct", 0.0)

                # Calculate severity score (risk x population impact)
                severity = risk_value * (pop_pct / 100.0)

                # Get recommendation
                recommendation = DANGER_ZONE_RECOMMENDATIONS.get(
                    (dim, seg_val, risk_name),
                    f"Consider intervention for {seg_val} segment regarding {risk_name}."
                )

                danger_zones.append(DangerZone(
                    segment_dimension=dim,
                    segment_value=seg_val,
                    risk_name=risk_name,
                    risk_value=risk_value,
                    population_pct=pop_pct,
                    severity_score=severity,
                    recommendation=recommendation,
                ))

        # Sort by severity score
        return sorted(danger_zones, key=lambda dz: dz.severity_score, reverse=True)


# =============================================================================
# SESSION 10.1: FULL RISK MAP (6 SEGMENTATIONS)
# =============================================================================

# Segment classification thresholds
SEGMENT_THRESHOLDS = {
    SegmentationType.BMI: {
        "overweight": 25.0,  # BMI >= 25
        "obese": 30.0,       # BMI >= 30
    },
    SegmentationType.AGE: {
        "middle": 36,        # Age >= 36
        "older": 56,         # Age >= 56
    },
    SegmentationType.CAFFEINE_SENSITIVITY: {
        # Based on CYP1A2 genotype mapping
        "slow": "slow",
        "normal": "normal",
        "fast": "fast",
    },
    SegmentationType.INSULIN_SENSITIVITY: {
        "sensitive": 1.2,    # ISF > 1.2
        "resistant": 0.8,    # ISF < 0.8
    },
    SegmentationType.ACTIVITY_LEVEL: {
        # Maps from VirtualPerson activity_level
        "sedentary": ["sedentary"],
        "moderate": ["light", "moderate"],
        "active": ["active", "very_active"],
    },
    SegmentationType.HABITUAL_CAFFEINE: {
        "naive": 50.0,       # < 50 mg/day
        "heavy": 300.0,      # >= 300 mg/day
    },
}


@dataclass(frozen=True)
class RiskMatrixCell:
    """
    A single cell in the full risk matrix.
    
    Represents risk for a specific segment-risk combination.
    """
    risk_percentage: float
    population_percentage: float
    count: int
    is_danger_zone: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_percentage": self.risk_percentage,
            "population_percentage": self.population_percentage,
            "count": self.count,
            "is_danger_zone": self.is_danger_zone,
        }


@dataclass
class RiskMatrix:
    """
    Full 6-dimensional risk matrix.
    
    Session 10.1: Extended risk map with all 6 segmentations.
    """
    
    # Storage: (segmentation_type, segment_value, risk_type) -> cell
    _cells: Dict[Tuple[SegmentationType, str, RiskType], RiskMatrixCell] = field(
        default_factory=dict
    )
    
    # Population counts per segment
    _segment_counts: Dict[Tuple[SegmentationType, str], int] = field(
        default_factory=dict
    )
    
    # Total population
    total_population: int = 0
    
    def add_cell(
        self,
        segmentation: SegmentationType,
        segment_value: str,
        risk_type: RiskType,
        cell: RiskMatrixCell,
    ) -> None:
        """Add a cell to the matrix."""
        key = (segmentation, segment_value, risk_type)
        self._cells[key] = cell
    
    def get_cell(
        self,
        segmentation: SegmentationType,
        segment_value: str,
        risk_type: RiskType,
    ) -> Optional[RiskMatrixCell]:
        """Get a specific cell."""
        key = (segmentation, segment_value, risk_type)
        return self._cells.get(key)
    
    def get_segment_risks(
        self,
        segmentation: SegmentationType,
        segment_value: str,
    ) -> Dict[RiskType, RiskMatrixCell]:
        """Get all risks for a specific segment."""
        result = {}
        for (seg_type, seg_val, risk_type), cell in self._cells.items():
            if seg_type == segmentation and seg_val == segment_value:
                result[risk_type] = cell
        return result
    
    def get_risk_by_segmentation(
        self,
        segmentation: SegmentationType,
        risk_type: RiskType,
    ) -> Dict[str, RiskMatrixCell]:
        """Get a specific risk across all segments in a dimension."""
        result = {}
        for (seg_type, seg_val, r_type), cell in self._cells.items():
            if seg_type == segmentation and r_type == risk_type:
                result[seg_val] = cell
        return result
    
    def get_all_danger_zones(self) -> List[Tuple[SegmentationType, str, RiskType, RiskMatrixCell]]:
        """Get all cells marked as danger zones."""
        return [
            (seg_type, seg_val, risk_type, cell)
            for (seg_type, seg_val, risk_type), cell in self._cells.items()
            if cell.is_danger_zone
        ]
    
    def get_table_for_segmentation(
        self,
        segmentation: SegmentationType,
    ) -> Dict[str, Any]:
        """
        Get matrix table for a specific segmentation.
        
        Returns:
            {
                "rows": ["normal", "overweight", "obese"],
                "columns": ["HYPERGLYCEMIA", "JITTER", ...],
                "values": [[10.0, 5.0], [20.0, 8.0], ...]
            }
        """
        segment_vals = SEGMENT_VALUES.get(segmentation, [])
        risk_types = list(RiskType)
        
        values = []
        for seg_val in segment_vals:
            row = []
            for risk_type in risk_types:
                cell = self.get_cell(segmentation, seg_val, risk_type)
                row.append(cell.risk_percentage if cell else 0.0)
            values.append(row)
        
        return {
            "segmentation": segmentation.value,
            "rows": segment_vals,
            "columns": [rt.name for rt in risk_types],
            "values": values,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        cells_dict = {}
        for (seg_type, seg_val, risk_type), cell in self._cells.items():
            key = f"{seg_type.value}|{seg_val}|{risk_type.value}"
            cells_dict[key] = cell.to_dict()
        
        return {
            "total_population": self.total_population,
            "cells": cells_dict,
            "segment_counts": {
                f"{seg_type.value}|{seg_val}": count
                for (seg_type, seg_val), count in self._segment_counts.items()
            },
        }


class SegmentClassifier:
    """
    Classifies individuals into segments across all 6 dimensions.
    
    Session 10.1: Supports all 6 segmentation types.
    """
    
    @staticmethod
    def classify_bmi(bmi: float) -> str:
        """Classify BMI into normal/overweight/obese."""
        thresholds = SEGMENT_THRESHOLDS[SegmentationType.BMI]
        if bmi >= thresholds["obese"]:
            return "obese"
        elif bmi >= thresholds["overweight"]:
            return "overweight"
        return "normal"
    
    @staticmethod
    def classify_age(age: int) -> str:
        """Classify age into young/middle/older."""
        thresholds = SEGMENT_THRESHOLDS[SegmentationType.AGE]
        if age >= thresholds["older"]:
            return "older"
        elif age >= thresholds["middle"]:
            return "middle"
        return "young"
    
    @staticmethod
    def classify_caffeine_sensitivity(genotype: str) -> str:
        """Classify caffeine sensitivity from CYP1A2 genotype."""
        return genotype.lower() if genotype.lower() in ["slow", "normal", "fast"] else "normal"
    
    @staticmethod
    def classify_insulin_sensitivity(isf: float) -> str:
        """Classify insulin sensitivity factor."""
        thresholds = SEGMENT_THRESHOLDS[SegmentationType.INSULIN_SENSITIVITY]
        if isf > thresholds["sensitive"]:
            return "sensitive"
        elif isf < thresholds["resistant"]:
            return "resistant"
        return "normal"
    
    @staticmethod
    def classify_activity_level(activity: str) -> str:
        """Classify activity level into sedentary/moderate/active."""
        mappings = SEGMENT_THRESHOLDS[SegmentationType.ACTIVITY_LEVEL]
        activity_lower = activity.lower()
        for category, levels in mappings.items():
            if activity_lower in levels:
                return category
        return "moderate"  # Default
    
    @staticmethod
    def classify_habitual_caffeine(mg_per_day: float) -> str:
        """Classify habitual caffeine intake."""
        thresholds = SEGMENT_THRESHOLDS[SegmentationType.HABITUAL_CAFFEINE]
        if mg_per_day < thresholds["naive"]:
            return "naive"
        elif mg_per_day >= thresholds["heavy"]:
            return "heavy"
        return "moderate"
    
    def classify_person(self, person: Any) -> Dict[SegmentationType, str]:
        """
        Classify a VirtualPerson across all 6 dimensions.
        
        Args:
            person: VirtualPerson object with required attributes
            
        Returns:
            Dict mapping SegmentationType to segment value
        """
        return {
            SegmentationType.BMI: self.classify_bmi(person.bmi),
            SegmentationType.AGE: self.classify_age(person.age),
            SegmentationType.CAFFEINE_SENSITIVITY: self.classify_caffeine_sensitivity(
                person.cyp1a2_genotype
            ),
            SegmentationType.INSULIN_SENSITIVITY: self.classify_insulin_sensitivity(
                person.insulin_sensitivity_factor
            ),
            SegmentationType.ACTIVITY_LEVEL: self.classify_activity_level(
                person.activity_level
            ),
            SegmentationType.HABITUAL_CAFFEINE: self.classify_habitual_caffeine(
                person.habitual_caffeine_mg
            ),
        }


class DangerZoneDetector:
    """
    Detects danger zones in risk matrix.
    
    Session 10.1: Configurable threshold for danger zone identification.
    """
    
    def __init__(self, threshold: float = 25.0):
        """
        Initialize detector.
        
        Args:
            threshold: Risk percentage above which is considered danger zone
        """
        self.threshold = threshold
    
    def is_danger_zone(self, risk_percentage: float) -> bool:
        """Check if a risk percentage constitutes a danger zone."""
        return risk_percentage >= self.threshold
    
    def find_danger_zones(
        self,
        risk_matrix: RiskMatrix,
    ) -> List[DangerZone]:
        """
        Find all danger zones in the risk matrix.
        
        Returns:
            List of DangerZone objects sorted by severity
        """
        danger_zones = []
        
        for (seg_type, seg_val, risk_type), cell in risk_matrix._cells.items():
            if cell.is_danger_zone:
                severity = cell.risk_percentage * (cell.population_percentage / 100.0)
                
                recommendation = DANGER_ZONE_RECOMMENDATIONS.get(
                    (seg_type.value, seg_val, risk_type.value),
                    f"Consider intervention for {seg_val} segment regarding {risk_type.name}."
                )
                
                danger_zones.append(DangerZone(
                    segment_dimension=seg_type.value,
                    segment_value=seg_val,
                    risk_name=risk_type.value,
                    risk_value=cell.risk_percentage,
                    population_pct=cell.population_percentage,
                    severity_score=severity,
                    recommendation=recommendation,
                ))
        
        return sorted(danger_zones, key=lambda dz: dz.severity_score, reverse=True)


class FullRiskMapAnalyzer:
    """
    Analyzer for complete 6-dimensional risk matrix.
    
    Session 10.1: Extends basic risk analysis with full segmentation.
    """
    
    def __init__(
        self,
        thresholds: Optional[RiskThresholds] = None,
        danger_threshold: float = 25.0,
    ):
        """
        Initialize analyzer.
        
        Args:
            thresholds: Risk thresholds for classification
            danger_threshold: Percentage above which is danger zone
        """
        self.thresholds = thresholds or create_default_thresholds()
        self.classifier = SegmentClassifier()
        self.danger_detector = DangerZoneDetector(danger_threshold)
    
    def analyze(
        self,
        population: List[Any],  # List of VirtualPerson
        individual_results: List[Dict[str, Any]],  # Per-person simulation results
    ) -> RiskMatrix:
        """
        Build complete risk matrix from population results.
        
        Args:
            population: List of VirtualPerson objects
            individual_results: List of dicts with per-person metrics
            
        Returns:
            RiskMatrix with all 6 segmentations x 6 risk types
        """
        matrix = RiskMatrix()
        matrix.total_population = len(population)
        
        # Count individuals and risk occurrences per segment
        segment_counts: Dict[Tuple[SegmentationType, str], int] = {}
        risk_counts: Dict[Tuple[SegmentationType, str, RiskType], int] = {}
        
        for person, result in zip(population, individual_results):
            # Classify person across all dimensions
            classifications = self.classifier.classify_person(person)
            
            # Check which risks apply to this person
            person_risks = self._evaluate_risks(result)
            
            # Update counts
            for seg_type, seg_val in classifications.items():
                key = (seg_type, seg_val)
                segment_counts[key] = segment_counts.get(key, 0) + 1
                
                for risk_type, has_risk in person_risks.items():
                    if has_risk:
                        risk_key = (seg_type, seg_val, risk_type)
                        risk_counts[risk_key] = risk_counts.get(risk_key, 0) + 1
        
        # Store segment counts
        matrix._segment_counts = segment_counts
        
        # Build cells
        for seg_type in SegmentationType:
            for seg_val in SEGMENT_VALUES.get(seg_type, []):
                seg_key = (seg_type, seg_val)
                seg_count = segment_counts.get(seg_key, 0)
                
                pop_pct = (seg_count / matrix.total_population * 100) if matrix.total_population > 0 else 0
                
                for risk_type in RiskType:
                    risk_key = (seg_type, seg_val, risk_type)
                    risk_count = risk_counts.get(risk_key, 0)
                    
                    risk_pct = (risk_count / seg_count * 100) if seg_count > 0 else 0
                    
                    cell = RiskMatrixCell(
                        risk_percentage=risk_pct,
                        population_percentage=pop_pct,
                        count=seg_count,
                        is_danger_zone=self.danger_detector.is_danger_zone(risk_pct),
                    )
                    
                    matrix.add_cell(seg_type, seg_val, risk_type, cell)
        
        return matrix
    
    def _evaluate_risks(self, result: Dict[str, Any]) -> Dict[RiskType, bool]:
        """
        Evaluate which risks apply to an individual result.
        
        Args:
            result: Dict with metrics like glucose_peak, caffeine_at_2200, etc.
            
        Returns:
            Dict mapping RiskType to whether the person has that risk
        """
        return {
            RiskType.HYPERGLYCEMIA: result.get("glucose_peak", 0) > self.thresholds.hyperglycemia_threshold_mg_dl,
            RiskType.SEVERE_HYPERGLYCEMIA: result.get("glucose_peak", 0) > self.thresholds.severe_hyperglycemia_threshold_mg_dl,
            RiskType.HYPOGLYCEMIA: result.get("glucose_min", 100) < 70,
            RiskType.JITTER: result.get("caffeine_peak", 0) > self.thresholds.jitter_caffeine_threshold_mg_l,
            RiskType.SLEEP_DISRUPTION: result.get("caffeine_at_2200", 0) > self.thresholds.sleep_caffeine_threshold_mg_l,
            RiskType.CRASH: result.get("alertness_drop_max", 0) > self.thresholds.crash_alertness_drop_pct,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_risk_matrix_from_results(
    population: List[Any],
    individual_results: List[Dict[str, Any]],
    thresholds: Optional[RiskThresholds] = None,
    danger_threshold: float = 25.0,
) -> RiskMatrix:
    """
    Convenience function to create full risk matrix.
    
    Args:
        population: List of VirtualPerson objects
        individual_results: List of per-person result dicts
        thresholds: Optional risk thresholds
        danger_threshold: Threshold for danger zone (default 25%)
        
    Returns:
        Complete RiskMatrix with all segments and risks
    """
    analyzer = FullRiskMapAnalyzer(thresholds, danger_threshold)
    return analyzer.analyze(population, individual_results)


def get_top_danger_zones(
    risk_matrix: RiskMatrix,
    n: int = 5,
) -> List[DangerZone]:
    """
    Get top N danger zones from risk matrix.
    
    Args:
        risk_matrix: RiskMatrix to analyze
        n: Number of danger zones to return
        
    Returns:
        List of top N DangerZone objects by severity
    """
    detector = DangerZoneDetector()
    all_zones = detector.find_danger_zones(risk_matrix)
    return all_zones[:n]


def format_risk_map_for_pdf(
    risk_matrix: RiskMatrix,
    segmentation: SegmentationType,
) -> Dict[str, Any]:
    """
    Format risk matrix for PDF generation.
    
    Args:
        risk_matrix: RiskMatrix to format
        segmentation: Which segmentation dimension to display
        
    Returns:
        Dict suitable for PDF table generation
    """
    table = risk_matrix.get_table_for_segmentation(segmentation)
    
    # Add formatting hints
    formatted = {
        "title": f"Risk Analysis by {segmentation.name.replace('_', ' ').title()}",
        "segments": table["rows"],
        "risks": table["columns"],
        "values": table["values"],
        "danger_threshold": 25.0,
    }
    
    return formatted


# =============================================================================
# BACKWARDS COMPATIBILITY ALIASES
# =============================================================================

# Alias for test compatibility
BasicRiskAnalyzer = RiskAnalyzer
