"""
Risk Analysis Module for MODULUS.

Session 5.2: Basic Risk Map

This module provides:
- RiskThresholds: Configurable thresholds for risk classification
- RiskMetric: Individual risk measurement with severity level
- RiskMap: Matrix of segment × risk for visualization
- DangerZone: Identification of high-risk population segments
- RiskAnalyzer: Main analyzer class
- RiskAnalysisResult: Complete risk analysis output

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
# RISK MAP
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
# RISK ANALYZER
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
            # Higher mean → higher proportion above threshold
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

                # Calculate severity score (risk × population impact)
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
