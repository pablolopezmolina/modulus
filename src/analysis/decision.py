# MODULUS — Decision Engine
# Session 6.1
#
# Decision engine that analyzes risk results and produces Go/Caution/No-Go verdicts.
#
# This is a core component of Pack 1 (€50k) - the Decision Page.
"""
Decision Engine for MODULUS Protocol Assessment.

This module provides the decision-making logic that converts risk analysis
results into actionable verdicts: GO, CAUTION, or NO_GO.

Classes:
    Verdict: Enum for decision outcomes
    RiskSummary: Summary of a single risk for reporting
    SegmentAtRisk: Identifies at-risk population segments
    Decision: Complete decision output
    DecisionConfig: Configuration for decision thresholds
    DecisionEngine: Main engine that analyzes risks and produces decisions

Decision Rules:
    GO: All risk metrics < 10% (configurable)
    CAUTION: Any risk metric 10-25%
    NO_GO: Any risk metric >= 25%

Example:
    >>> from src.analysis.decision import DecisionEngine
    >>> from src.analysis.risk import RiskAnalyzer
    >>>
    >>> # Get risk analysis result
    >>> risk_result = risk_analyzer.analyze(population_result)
    >>>
    >>> # Make decision
    >>> engine = DecisionEngine()
    >>> decision = engine.analyze(risk_result)
    >>>
    >>> print(f"Verdict: {decision.verdict}")
    >>> print(f"Summary: {decision.summary}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

from src.analysis.risk import (
    RiskLevel,
    RiskMetric,
    RiskMap,
    DangerZone,
    RiskAnalysisResult,
)


# =============================================================================
# VERDICT ENUM
# =============================================================================

class Verdict(str, Enum):
    """
    Decision verdict enum.

    GO: Product is safe to launch as-is
    CAUTION: Product may proceed with modifications/warnings
    NO_GO: Product requires reformulation before launch

    Inherits from str for easy serialization and comparison.
    """
    GO = "GO"
    CAUTION = "CAUTION"
    NO_GO = "NO_GO"

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other: "Verdict") -> bool:
        """Enable severity comparison: GO < CAUTION < NO_GO."""
        order = {Verdict.GO: 0, Verdict.CAUTION: 1, Verdict.NO_GO: 2}
        if isinstance(other, Verdict):
            return order[self] < order[other]
        return NotImplemented

    def __le__(self, other: "Verdict") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Verdict") -> bool:
        if isinstance(other, Verdict):
            return other < self
        return NotImplemented

    def __ge__(self, other: "Verdict") -> bool:
        return self == other or self > other


# =============================================================================
# RISK SUMMARY (for reporting)
# =============================================================================

@dataclass(frozen=True)
class RiskSummary:
    """
    Summary of a single risk for inclusion in decision output.

    Provides human-readable risk information for reports and Decision Page.

    Attributes:
        risk_name: Internal identifier (e.g., "pct_hyperglycemia")
        display_name: Human-readable name (e.g., "Hyperglycemia Risk")
        value: Risk percentage (0-100)
        level: RiskLevel classification
        affected_population_pct: Percentage of population affected (0-100)
        description: Human-readable description for reports
    """
    risk_name: str
    display_name: str
    value: float
    level: RiskLevel
    affected_population_pct: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "risk_name": self.risk_name,
            "display_name": self.display_name,
            "value": self.value,
            "level": self.level.value.upper(),
            "affected_population_pct": self.affected_population_pct,
            "description": self.description,
        }


# =============================================================================
# SEGMENT AT RISK
# =============================================================================

@dataclass(frozen=True)
class SegmentAtRisk:
    """
    Identifies a population segment with elevated risk.

    Used to highlight specific demographics that may need warnings
    or special consideration in labeling.

    Attributes:
        dimension: Segmentation dimension (e.g., "by_bmi", "by_caffeine_sensitivity")
        segment_name: Specific segment (e.g., "obese", "slow")
        primary_risk: The main risk affecting this segment
        risk_value: The risk percentage for this segment
        risk_level: Classification of the risk
        population_fraction: Fraction of total population in this segment
        recommendation: Specific action recommended for this segment
    """
    dimension: str
    segment_name: str
    primary_risk: str
    risk_value: float
    risk_level: RiskLevel
    population_fraction: float
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "dimension": self.dimension,
            "segment_name": self.segment_name,
            "primary_risk": self.primary_risk,
            "risk_value": self.risk_value,
            "risk_level": self.risk_level.value.upper(),
            "population_fraction": self.population_fraction,
            "recommendation": self.recommendation,
        }


# =============================================================================
# DECISION CONFIG
# =============================================================================

@dataclass(frozen=True)
class DecisionConfig:
    """
    Configuration for decision thresholds.

    Default thresholds per ROADMAP:
        GO: < 10% risk in all categories
        CAUTION: 10-25% risk in any category
        NO_GO: >= 25% risk in any category

    Note: Thresholds are in percentage units (0-100), matching RiskMetric.value.

    Attributes:
        go_threshold: Maximum risk for GO verdict (exclusive)
        caution_threshold: Maximum risk for CAUTION verdict (exclusive)
        top_risks_count: Number of top risks to include in report
    """
    go_threshold: float = 10.0  # <10% = GO
    caution_threshold: float = 25.0  # <25% = CAUTION, >=25% = NO_GO
    top_risks_count: int = 5

    def __post_init__(self):
        """Validate configuration."""
        if self.go_threshold < 0:
            raise ValueError("go_threshold must be non-negative")
        if self.caution_threshold < 0:
            raise ValueError("caution_threshold must be non-negative")
        if self.go_threshold > 100.0:
            raise ValueError("go_threshold must be <= 100.0")
        if self.caution_threshold > 100.0:
            raise ValueError("caution_threshold must be <= 100.0")
        if self.go_threshold >= self.caution_threshold:
            raise ValueError(
                f"go_threshold ({self.go_threshold}) must be less than "
                f"caution_threshold ({self.caution_threshold})"
            )
        if self.top_risks_count < 1:
            raise ValueError("top_risks_count must be >= 1")


# =============================================================================
# DECISION OUTPUT
# =============================================================================

@dataclass(frozen=True)
class Decision:
    """
    Complete decision output from DecisionEngine.

    This is the primary output for the Decision Page in Pack 1.

    Attributes:
        verdict: GO, CAUTION, or NO_GO
        confidence: Confidence in the verdict (0-1)
        top_risks: Top N risks sorted by severity
        top_segments_at_risk: Population segments with highest risk
        summary: Human-readable summary (2-3 sentences)
        max_risk_value: The highest risk value found (0-100)
        max_risk_name: Name of the highest risk metric

    Properties:
        is_acceptable: True if verdict is GO or CAUTION
    """
    verdict: Verdict
    confidence: float
    top_risks: List[RiskSummary]
    top_segments_at_risk: List[SegmentAtRisk]
    summary: str
    max_risk_value: float
    max_risk_name: str

    def __post_init__(self):
        """Validate decision fields."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"confidence must be between 0 and 1, got {self.confidence}")
        if self.max_risk_value < 0:
            raise ValueError(f"max_risk_value must be non-negative, got {self.max_risk_value}")

    @property
    def is_acceptable(self) -> bool:
        """Whether the product is acceptable for launch (GO or CAUTION)."""
        return self.verdict in (Verdict.GO, Verdict.CAUTION)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON export."""
        return {
            "verdict": str(self.verdict),
            "confidence": self.confidence,
            "top_risks": [r.to_dict() for r in self.top_risks],
            "top_segments_at_risk": [s.to_dict() for s in self.top_segments_at_risk],
            "summary": self.summary,
            "max_risk_value": self.max_risk_value,
            "max_risk_name": self.max_risk_name,
            "is_acceptable": self.is_acceptable,
        }


# =============================================================================
# DISPLAY NAME MAPPING
# =============================================================================

# Human-readable names for risk metrics (fallback if not in RiskMetric)
RISK_DISPLAY_NAMES: Dict[str, str] = {
    "pct_hyperglycemia": "Hyperglycemia Risk",
    "pct_severe_hyperglycemia": "Severe Hyperglycemia Risk",
    "pct_jitter_risk": "Jitter/Anxiety Risk",
    "pct_sleep_disruption": "Sleep Disruption Risk",
    "pct_crash_risk": "Energy Crash Risk",
    "pct_hypoglycemia": "Hypoglycemia Risk",
    "pct_gi_distress": "GI Distress Risk",
}


def get_display_name(risk_name: str) -> str:
    """Get human-readable name for a risk metric."""
    return RISK_DISPLAY_NAMES.get(
        risk_name,
        risk_name.replace("pct_", "").replace("_", " ").title()
    )


# =============================================================================
# DECISION ENGINE
# =============================================================================

class DecisionEngine:
    """
    Engine that analyzes risk results and produces decisions.

    The DecisionEngine takes a RiskAnalysisResult and applies decision rules
    to produce a verdict (GO/CAUTION/NO_GO) with supporting information.

    Decision Rules (default thresholds):
        GO: All risk metrics < 10%
        CAUTION: Any risk metric 10-25%
        NO_GO: Any risk metric >= 25%

    Example:
        >>> engine = DecisionEngine()
        >>> decision = engine.analyze(risk_result)
        >>> print(decision.verdict)  # Verdict.GO
        >>> print(decision.summary)

    Custom thresholds:
        >>> config = DecisionConfig(go_threshold=5.0, caution_threshold=15.0)
        >>> engine = DecisionEngine(config)
    """

    def __init__(self, config: Optional[DecisionConfig] = None):
        """
        Initialize DecisionEngine.

        Args:
            config: Optional custom configuration. Uses defaults if None.
        """
        self.config = config or DecisionConfig()

    def analyze(self, risk_result: RiskAnalysisResult) -> Decision:
        """
        Analyze risk results and produce a decision.

        Args:
            risk_result: RiskAnalysisResult from RiskAnalyzer

        Returns:
            Decision with verdict, top risks, segments at risk, and summary
        """
        # Extract risk metrics (List[RiskMetric])
        metrics = risk_result.metrics

        # Handle empty metrics
        if not metrics:
            return Decision(
                verdict=Verdict.GO,
                confidence=1.0,
                top_risks=[],
                top_segments_at_risk=[],
                summary="No risk metrics to evaluate. Assessment indicates no concerns.",
                max_risk_value=0.0,
                max_risk_name="none",
            )

        # Calculate max risk
        max_metric = max(metrics, key=lambda m: m.value)
        max_risk_value = max_metric.value
        max_risk_name = max_metric.name

        # Determine verdict
        verdict = self._determine_verdict(max_risk_value)

        # Calculate confidence
        confidence = self._calculate_confidence(max_risk_value, verdict)

        # Get top risks
        top_risks = self._get_top_risks(metrics)

        # Get segments at risk from danger zones
        segments_at_risk = self._get_segments_at_risk(risk_result.danger_zones)

        # Generate summary
        summary = self._generate_summary(verdict, max_risk_value, max_risk_name, top_risks)

        return Decision(
            verdict=verdict,
            confidence=confidence,
            top_risks=top_risks,
            top_segments_at_risk=segments_at_risk,
            summary=summary,
            max_risk_value=max_risk_value,
            max_risk_name=max_risk_name,
        )

    def _determine_verdict(self, max_risk_value: float) -> Verdict:
        """
        Determine verdict based on maximum risk value.

        Args:
            max_risk_value: Highest risk percentage across all metrics (0-100)

        Returns:
            Verdict enum value
        """
        if max_risk_value < self.config.go_threshold:
            return Verdict.GO
        elif max_risk_value < self.config.caution_threshold:
            return Verdict.CAUTION
        else:
            return Verdict.NO_GO

    def _calculate_confidence(self, max_risk_value: float, verdict: Verdict) -> float:
        """
        Calculate confidence in the verdict.

        Confidence is higher when:
        - Risk values are far from thresholds (clear-cut cases)
        - Risk values are very low (strong GO) or very high (strong NO_GO)

        Args:
            max_risk_value: Highest risk percentage (0-100)
            verdict: Determined verdict

        Returns:
            Confidence score between 0 and 1
        """
        go_thresh = self.config.go_threshold
        caution_thresh = self.config.caution_threshold

        if verdict == Verdict.GO:
            # Distance from GO threshold (closer to 0 = higher confidence)
            if max_risk_value == 0:
                return 1.0
            # Linear scale: 0% risk = 1.0 confidence, at threshold = 0.7
            relative_pos = max_risk_value / go_thresh
            return max(0.7, 1.0 - (relative_pos * 0.3))

        elif verdict == Verdict.CAUTION:
            # CAUTION has lower confidence (borderline cases)
            # Midpoint of CAUTION range has lowest confidence
            range_width = caution_thresh - go_thresh
            midpoint = go_thresh + (range_width / 2)

            # Distance from midpoint (further = higher confidence)
            distance_from_mid = abs(max_risk_value - midpoint) / (range_width / 2)
            # Base confidence 0.7 at midpoint, up to 0.85 at edges
            return min(0.85, 0.7 + (distance_from_mid * 0.15))

        else:  # NO_GO
            # Distance from CAUTION threshold (further = higher confidence)
            excess = max_risk_value - caution_thresh
            # Every 10% above threshold adds confidence
            confidence = min(0.99, 0.8 + (excess / 100.0))
            return confidence

    def _get_top_risks(self, metrics: List[RiskMetric]) -> List[RiskSummary]:
        """
        Get top N risks sorted by value descending.

        Args:
            metrics: List of RiskMetric objects

        Returns:
            List of RiskSummary for top risks
        """
        # Sort by value descending
        sorted_metrics = sorted(metrics, key=lambda m: m.value, reverse=True)

        # Take top N
        top_metrics = sorted_metrics[:self.config.top_risks_count]

        # Convert to RiskSummary
        summaries = []
        for metric in top_metrics:
            # Use display_name from metric, or fall back to our mapping
            display_name = metric.display_name or get_display_name(metric.name)
            affected_pct = metric.value

            # Generate description
            description = self._generate_risk_description(metric, affected_pct)

            summaries.append(RiskSummary(
                risk_name=metric.name,
                display_name=display_name,
                value=metric.value,
                level=metric.level,
                affected_population_pct=affected_pct,
                description=description,
            ))

        return summaries

    def _generate_risk_description(self, metric: RiskMetric, affected_pct: float) -> str:
        """Generate human-readable description for a risk."""
        display_name = metric.display_name or get_display_name(metric.name)
        display_lower = display_name.lower()

        if metric.level == RiskLevel.LOW:
            return f"{affected_pct:.1f}% of population shows {display_lower} (within acceptable limits)"
        elif metric.level == RiskLevel.MEDIUM:
            return f"{affected_pct:.1f}% of population shows elevated {display_lower} (requires attention)"
        else:
            return f"{affected_pct:.1f}% of population at high {display_lower} (action required)"

    def _get_segments_at_risk(self, danger_zones: List[DangerZone]) -> List[SegmentAtRisk]:
        """
        Convert danger zones to segments at risk.

        Args:
            danger_zones: List of DangerZone from risk analysis

        Returns:
            List of SegmentAtRisk for reporting
        """
        segments = []

        for zone in danger_zones:
            # Determine risk level from value
            if zone.risk_value >= self.config.caution_threshold:
                level = RiskLevel.HIGH
            elif zone.risk_value >= self.config.go_threshold:
                level = RiskLevel.MEDIUM
            else:
                level = RiskLevel.LOW

            segments.append(SegmentAtRisk(
                dimension=zone.segment_dimension,
                segment_name=zone.segment_value,
                primary_risk=zone.risk_name,
                risk_value=zone.risk_value,
                risk_level=level,
                population_fraction=zone.population_pct / 100.0 if zone.population_pct else 0.0,
                recommendation=zone.recommendation,
            ))

        # Sort by risk value descending
        segments.sort(key=lambda s: s.risk_value, reverse=True)

        return segments

    def _generate_summary(
        self,
        verdict: Verdict,
        max_risk_value: float,
        max_risk_name: str,
        top_risks: List[RiskSummary],
    ) -> str:
        """
        Generate human-readable summary for Decision Page.

        Args:
            verdict: The determined verdict
            max_risk_value: Highest risk value (0-100)
            max_risk_name: Name of highest risk
            top_risks: List of top risk summaries

        Returns:
            2-3 sentence summary for Decision Page
        """
        max_display = get_display_name(max_risk_name)

        if verdict == Verdict.GO:
            return (
                f"All risk metrics are within acceptable limits. "
                f"The highest identified risk is {max_display.lower()} at {max_risk_value:.1f}%, "
                f"which is below the {self.config.go_threshold:.0f}% threshold. "
                f"Product is recommended for launch."
            )

        elif verdict == Verdict.CAUTION:
            # Mention top concern
            concern_text = ""
            if top_risks:
                concern_names = [r.display_name.lower() for r in top_risks[:2]]
                if len(concern_names) == 1:
                    concern_text = f"Primary concern: {concern_names[0]}. "
                else:
                    concern_text = f"Primary concerns: {concern_names[0]} and {concern_names[1]}. "

            return (
                f"Product shows moderate risk levels requiring attention. "
                f"{concern_text}"
                f"The highest risk ({max_display.lower()}) affects {max_risk_value:.1f}% of the population. "
                f"Consider adding label warnings or minor reformulation."
            )

        else:  # NO_GO
            return (
                f"Risk levels are unacceptable for product launch. "
                f"{max_display} affects {max_risk_value:.1f}% of the population, "
                f"exceeding the {self.config.caution_threshold:.0f}% threshold. "
                f"Reformulation is strongly recommended before proceeding."
            )
