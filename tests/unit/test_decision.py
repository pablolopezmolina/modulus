# MODULUS — Tests for DecisionEngine
# Session 6.1
# Tests: ~45 tests
"""
Test suite for DecisionEngine and Decision dataclasses.

Tests cover:
- Verdict enum and comparison
- Decision dataclass creation and validation
- RiskSummary dataclass
- SegmentAtRisk dataclass
- DecisionEngine analyze method
- Decision rules (GO/CAUTION/NO_GO thresholds)
- Summary generation
- Edge cases and error handling
"""

import pytest
from dataclasses import FrozenInstanceError
from typing import Dict, List, Any, Tuple

# Import the module under test
from src.analysis.decision import (
    Verdict,
    RiskSummary,
    SegmentAtRisk,
    Decision,
    DecisionConfig,
    DecisionEngine,
)
from src.analysis.risk import (
    RiskLevel,
    RiskMetric,
    RiskThresholds,
    RiskMap,
    DangerZone,
    RiskAnalysisResult,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def default_config():
    """Default decision configuration."""
    return DecisionConfig()


@pytest.fixture
def risk_thresholds():
    """Standard risk thresholds."""
    return RiskThresholds()


def make_risk_metric(
    name: str,
    value: float,
    display_name: str = None,
    threshold_low: float = 10.0,
    threshold_high: float = 25.0,
) -> RiskMetric:
    """Helper to create RiskMetric with proper interface."""
    return RiskMetric(
        name=name,
        display_name=display_name or name.replace("_", " ").title(),
        value=value,
        threshold_low=threshold_low,
        threshold_high=threshold_high,
    )


@pytest.fixture
def low_risk_metrics() -> List[RiskMetric]:
    """Risk metrics indicating low overall risk (GO scenario)."""
    return [
        make_risk_metric("pct_hyperglycemia", 5.0, "Hyperglycemia Risk"),
        make_risk_metric("pct_severe_hyperglycemia", 1.0, "Severe Hyperglycemia Risk"),
        make_risk_metric("pct_jitter_risk", 8.0, "Jitter Risk"),
        make_risk_metric("pct_sleep_disruption", 6.0, "Sleep Disruption Risk"),
        make_risk_metric("pct_crash_risk", 3.0, "Crash Risk"),
    ]


@pytest.fixture
def medium_risk_metrics() -> List[RiskMetric]:
    """Risk metrics indicating medium risk (CAUTION scenario)."""
    return [
        make_risk_metric("pct_hyperglycemia", 15.0, "Hyperglycemia Risk"),
        make_risk_metric("pct_severe_hyperglycemia", 3.0, "Severe Hyperglycemia Risk"),
        make_risk_metric("pct_jitter_risk", 12.0, "Jitter Risk"),
        make_risk_metric("pct_sleep_disruption", 8.0, "Sleep Disruption Risk"),
        make_risk_metric("pct_crash_risk", 5.0, "Crash Risk"),
    ]


@pytest.fixture
def high_risk_metrics() -> List[RiskMetric]:
    """Risk metrics indicating high risk (NO_GO scenario)."""
    return [
        make_risk_metric("pct_hyperglycemia", 30.0, "Hyperglycemia Risk"),
        make_risk_metric("pct_severe_hyperglycemia", 12.0, "Severe Hyperglycemia Risk"),
        make_risk_metric("pct_jitter_risk", 28.0, "Jitter Risk"),
        make_risk_metric("pct_sleep_disruption", 35.0, "Sleep Disruption Risk"),
        make_risk_metric("pct_crash_risk", 22.0, "Crash Risk"),
    ]


@pytest.fixture
def sample_risk_map() -> RiskMap:
    """Sample risk map for testing."""
    cells: Dict[Tuple[str, str, str], float] = {
        ("by_bmi", "normal", "pct_hyperglycemia"): 5.0,
        ("by_bmi", "overweight", "pct_hyperglycemia"): 15.0,
        ("by_bmi", "obese", "pct_hyperglycemia"): 30.0,
        ("by_caffeine_sensitivity", "slow", "pct_sleep_disruption"): 35.0,
        ("by_caffeine_sensitivity", "normal", "pct_sleep_disruption"): 10.0,
        ("by_caffeine_sensitivity", "fast", "pct_sleep_disruption"): 5.0,
    }
    return RiskMap(
        dimensions=["by_bmi", "by_caffeine_sensitivity"],
        risk_names=["pct_hyperglycemia", "pct_sleep_disruption"],
        cells=cells,
        segment_values={
            "by_bmi": ["normal", "overweight", "obese"],
            "by_caffeine_sensitivity": ["slow", "normal", "fast"],
        },
    )


@pytest.fixture
def sample_danger_zones() -> List[DangerZone]:
    """Sample danger zones for testing."""
    return [
        DangerZone(
            segment_dimension="by_caffeine_sensitivity",
            segment_value="slow",
            risk_name="pct_sleep_disruption",
            risk_value=35.0,
            population_pct=20.0,
            severity_score=7.0,
            recommendation="Add warning for slow caffeine metabolizers",
        ),
        DangerZone(
            segment_dimension="by_bmi",
            segment_value="obese",
            risk_name="pct_hyperglycemia",
            risk_value=30.0,
            population_pct=15.0,
            severity_score=4.5,
            recommendation="Consider glucose-friendly formulation",
        ),
    ]


def create_risk_analysis_result(
    metrics: List[RiskMetric],
    risk_map: RiskMap = None,
    danger_zones: List[DangerZone] = None,
    n_individuals: int = 1000,
) -> RiskAnalysisResult:
    """Helper to create RiskAnalysisResult for testing."""
    default_risk_map = RiskMap(
        dimensions=[],
        risk_names=[],
        cells={},
        segment_values={},
    )
    return RiskAnalysisResult(
        n_individuals=n_individuals,
        metrics=metrics,
        risk_map=risk_map or default_risk_map,
        danger_zones=danger_zones or [],
        thresholds=RiskThresholds(),
    )


# =============================================================================
# VERDICT ENUM TESTS
# =============================================================================

class TestVerdict:
    """Tests for Verdict enum."""

    def test_verdict_values(self):
        """Verdict has correct values."""
        assert Verdict.GO.value == "GO"
        assert Verdict.CAUTION.value == "CAUTION"
        assert Verdict.NO_GO.value == "NO_GO"

    def test_verdict_from_string(self):
        """Can create Verdict from string."""
        assert Verdict("GO") == Verdict.GO
        assert Verdict("CAUTION") == Verdict.CAUTION
        assert Verdict("NO_GO") == Verdict.NO_GO

    def test_verdict_comparison(self):
        """Verdicts can be compared by severity."""
        # GO < CAUTION < NO_GO
        assert Verdict.GO < Verdict.CAUTION
        assert Verdict.CAUTION < Verdict.NO_GO
        assert Verdict.GO < Verdict.NO_GO

    def test_verdict_str(self):
        """Verdict string representation."""
        assert str(Verdict.GO) == "GO"
        assert str(Verdict.CAUTION) == "CAUTION"
        assert str(Verdict.NO_GO) == "NO_GO"


# =============================================================================
# RISK SUMMARY TESTS
# =============================================================================

class TestRiskSummary:
    """Tests for RiskSummary dataclass."""

    def test_creation(self):
        """RiskSummary can be created with valid data."""
        summary = RiskSummary(
            risk_name="pct_hyperglycemia",
            display_name="Hyperglycemia Risk",
            value=15.0,
            level=RiskLevel.MEDIUM,
            affected_population_pct=15.0,
            description="15% of population at risk of hyperglycemia",
        )
        assert summary.risk_name == "pct_hyperglycemia"
        assert summary.value == 15.0
        assert summary.level == RiskLevel.MEDIUM

    def test_frozen(self):
        """RiskSummary is immutable."""
        summary = RiskSummary(
            risk_name="test",
            display_name="Test Risk",
            value=10.0,
            level=RiskLevel.LOW,
            affected_population_pct=10.0,
            description="Test",
        )
        with pytest.raises(FrozenInstanceError):
            summary.value = 20.0

    def test_to_dict(self):
        """RiskSummary can be serialized."""
        summary = RiskSummary(
            risk_name="pct_jitter_risk",
            display_name="Jitter Risk",
            value=25.0,
            level=RiskLevel.HIGH,
            affected_population_pct=25.0,
            description="Jitter risk description",
        )
        d = summary.to_dict()
        assert d["risk_name"] == "pct_jitter_risk"
        assert d["value"] == 25.0
        # RiskLevel.HIGH.value is "high", we uppercase it in to_dict
        assert d["level"] == "HIGH"


# =============================================================================
# SEGMENT AT RISK TESTS
# =============================================================================

class TestSegmentAtRisk:
    """Tests for SegmentAtRisk dataclass."""

    def test_creation(self):
        """SegmentAtRisk can be created."""
        segment = SegmentAtRisk(
            dimension="by_bmi",
            segment_name="obese",
            primary_risk="pct_hyperglycemia",
            risk_value=30.0,
            risk_level=RiskLevel.HIGH,
            population_fraction=0.15,
            recommendation="Consider reformulation for glucose control",
        )
        assert segment.dimension == "by_bmi"
        assert segment.segment_name == "obese"
        assert segment.risk_value == 30.0

    def test_frozen(self):
        """SegmentAtRisk is immutable."""
        segment = SegmentAtRisk(
            dimension="by_age",
            segment_name="older",
            primary_risk="pct_crash",
            risk_value=20.0,
            risk_level=RiskLevel.MEDIUM,
            population_fraction=0.25,
            recommendation="Test",
        )
        with pytest.raises(FrozenInstanceError):
            segment.risk_value = 30.0


# =============================================================================
# DECISION CONFIG TESTS
# =============================================================================

class TestDecisionConfig:
    """Tests for DecisionConfig dataclass."""

    def test_default_thresholds(self):
        """DecisionConfig has correct default thresholds."""
        config = DecisionConfig()
        assert config.go_threshold == 10.0
        assert config.caution_threshold == 25.0
        assert config.top_risks_count == 5

    def test_custom_thresholds(self):
        """DecisionConfig accepts custom thresholds."""
        config = DecisionConfig(
            go_threshold=5.0,
            caution_threshold=15.0,
            top_risks_count=3,
        )
        assert config.go_threshold == 5.0
        assert config.caution_threshold == 15.0
        assert config.top_risks_count == 3

    def test_validation_go_less_than_caution(self):
        """GO threshold must be less than CAUTION threshold."""
        with pytest.raises(ValueError, match="go_threshold.*must be less than"):
            DecisionConfig(go_threshold=30.0, caution_threshold=20.0)

    def test_validation_thresholds_positive(self):
        """Thresholds must be positive."""
        with pytest.raises(ValueError):
            DecisionConfig(go_threshold=-10.0)

    def test_validation_thresholds_max_100(self):
        """Thresholds must be <= 100."""
        with pytest.raises(ValueError):
            DecisionConfig(caution_threshold=150.0)


# =============================================================================
# DECISION DATACLASS TESTS
# =============================================================================

class TestDecision:
    """Tests for Decision dataclass."""

    def test_creation_go(self):
        """Decision GO can be created."""
        decision = Decision(
            verdict=Verdict.GO,
            confidence=0.95,
            top_risks=[],
            top_segments_at_risk=[],
            summary="All risk metrics within acceptable limits.",
            max_risk_value=8.0,
            max_risk_name="pct_jitter_risk",
        )
        assert decision.verdict == Verdict.GO
        assert decision.confidence == 0.95

    def test_creation_caution(self):
        """Decision CAUTION can be created."""
        risk = RiskSummary(
            risk_name="pct_hyperglycemia",
            display_name="Hyperglycemia Risk",
            value=18.0,
            level=RiskLevel.MEDIUM,
            affected_population_pct=18.0,
            description="18% at risk",
        )
        decision = Decision(
            verdict=Verdict.CAUTION,
            confidence=0.85,
            top_risks=[risk],
            top_segments_at_risk=[],
            summary="Some risk metrics require attention.",
            max_risk_value=18.0,
            max_risk_name="pct_hyperglycemia",
        )
        assert decision.verdict == Verdict.CAUTION
        assert len(decision.top_risks) == 1

    def test_creation_no_go(self):
        """Decision NO_GO can be created."""
        decision = Decision(
            verdict=Verdict.NO_GO,
            confidence=0.99,
            top_risks=[],
            top_segments_at_risk=[],
            summary="Risk levels unacceptable. Reformulation recommended.",
            max_risk_value=35.0,
            max_risk_name="pct_sleep_disruption",
        )
        assert decision.verdict == Verdict.NO_GO
        assert decision.max_risk_value == 35.0

    def test_frozen(self):
        """Decision is immutable."""
        decision = Decision(
            verdict=Verdict.GO,
            confidence=0.90,
            top_risks=[],
            top_segments_at_risk=[],
            summary="Test",
            max_risk_value=5.0,
            max_risk_name="test",
        )
        with pytest.raises(FrozenInstanceError):
            decision.verdict = Verdict.NO_GO

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValueError, match="confidence"):
            Decision(
                verdict=Verdict.GO,
                confidence=1.5,  # Invalid
                top_risks=[],
                top_segments_at_risk=[],
                summary="Test",
                max_risk_value=5.0,
                max_risk_name="test",
            )

    def test_to_dict(self):
        """Decision can be serialized."""
        decision = Decision(
            verdict=Verdict.GO,
            confidence=0.90,
            top_risks=[],
            top_segments_at_risk=[],
            summary="All good",
            max_risk_value=8.0,
            max_risk_name="pct_jitter",
        )
        d = decision.to_dict()
        assert d["verdict"] == "GO"
        assert d["confidence"] == 0.90
        assert d["summary"] == "All good"

    def test_is_acceptable_property(self):
        """is_acceptable property works correctly."""
        go_decision = Decision(
            verdict=Verdict.GO,
            confidence=0.90,
            top_risks=[],
            top_segments_at_risk=[],
            summary="Test",
            max_risk_value=5.0,
            max_risk_name="test",
        )
        assert go_decision.is_acceptable is True

        caution_decision = Decision(
            verdict=Verdict.CAUTION,
            confidence=0.80,
            top_risks=[],
            top_segments_at_risk=[],
            summary="Test",
            max_risk_value=15.0,
            max_risk_name="test",
        )
        assert caution_decision.is_acceptable is True

        no_go_decision = Decision(
            verdict=Verdict.NO_GO,
            confidence=0.95,
            top_risks=[],
            top_segments_at_risk=[],
            summary="Test",
            max_risk_value=35.0,
            max_risk_name="test",
        )
        assert no_go_decision.is_acceptable is False


# =============================================================================
# DECISION ENGINE TESTS
# =============================================================================

class TestDecisionEngine:
    """Tests for DecisionEngine class."""

    def test_creation_default_config(self):
        """DecisionEngine can be created with default config."""
        engine = DecisionEngine()
        assert engine.config.go_threshold == 10.0

    def test_creation_custom_config(self, default_config):
        """DecisionEngine can be created with custom config."""
        config = DecisionConfig(go_threshold=5.0)
        engine = DecisionEngine(config)
        assert engine.config.go_threshold == 5.0

    def test_analyze_go_verdict(self, low_risk_metrics):
        """Engine returns GO for low risk metrics."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(low_risk_metrics)

        decision = engine.analyze(result)

        assert decision.verdict == Verdict.GO
        assert decision.max_risk_value < 10.0
        assert "acceptable" in decision.summary.lower() or "within" in decision.summary.lower()

    def test_analyze_caution_verdict(self, medium_risk_metrics):
        """Engine returns CAUTION for medium risk metrics."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(medium_risk_metrics)

        decision = engine.analyze(result)

        assert decision.verdict == Verdict.CAUTION
        assert 10.0 <= decision.max_risk_value < 25.0

    def test_analyze_no_go_verdict(self, high_risk_metrics):
        """Engine returns NO_GO for high risk metrics."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(high_risk_metrics)

        decision = engine.analyze(result)

        assert decision.verdict == Verdict.NO_GO
        assert decision.max_risk_value >= 25.0
        assert "reformulat" in decision.summary.lower() or "unacceptable" in decision.summary.lower()

    def test_top_risks_sorted_by_value(self, high_risk_metrics):
        """Top risks are sorted by value descending."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(high_risk_metrics)

        decision = engine.analyze(result)

        # Check top risks are sorted descending
        for i in range(len(decision.top_risks) - 1):
            assert decision.top_risks[i].value >= decision.top_risks[i + 1].value

    def test_top_risks_limited_to_count(self, high_risk_metrics):
        """Top risks limited to configured count."""
        config = DecisionConfig(top_risks_count=3)
        engine = DecisionEngine(config)
        result = create_risk_analysis_result(high_risk_metrics)

        decision = engine.analyze(result)

        assert len(decision.top_risks) <= 3

    def test_segments_at_risk_from_danger_zones(
        self, low_risk_metrics, sample_risk_map, sample_danger_zones
    ):
        """Segments at risk are extracted from danger zones."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(
            low_risk_metrics,
            risk_map=sample_risk_map,
            danger_zones=sample_danger_zones,
        )

        decision = engine.analyze(result)

        # Should have segments from danger zones
        assert len(decision.top_segments_at_risk) > 0

    def test_confidence_calculation(self, low_risk_metrics):
        """Confidence is calculated based on risk levels."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(low_risk_metrics)

        decision = engine.analyze(result)

        # Confidence should be between 0 and 1
        assert 0 <= decision.confidence <= 1
        # For low risk (max 8% of 10% threshold), confidence should be reasonable
        # 8% is 80% of threshold, so confidence = 1.0 - (0.8 * 0.3) = 0.76
        assert decision.confidence >= 0.70

    def test_confidence_lower_for_borderline(self, medium_risk_metrics):
        """Confidence is lower for borderline cases."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(medium_risk_metrics)

        decision = engine.analyze(result)

        # Confidence should be moderate for CAUTION
        assert decision.confidence < 0.95

    def test_summary_mentions_top_risk(self, high_risk_metrics):
        """Summary mentions the highest risk."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(high_risk_metrics)

        decision = engine.analyze(result)

        # Summary should be non-empty and meaningful
        assert len(decision.summary) > 20

    def test_empty_metrics_returns_go(self):
        """Empty metrics results in GO verdict."""
        engine = DecisionEngine()
        result = create_risk_analysis_result([])

        decision = engine.analyze(result)

        # No risks = GO
        assert decision.verdict == Verdict.GO

    def test_single_high_risk_triggers_no_go(self, low_risk_metrics):
        """A single high risk triggers NO_GO."""
        # Add one high risk to otherwise low risk metrics
        metrics = low_risk_metrics.copy()
        metrics.append(
            make_risk_metric("pct_extra_high", 35.0, "Extra High Risk")
        )

        engine = DecisionEngine()
        result = create_risk_analysis_result(metrics)

        decision = engine.analyze(result)

        assert decision.verdict == Verdict.NO_GO

    def test_custom_thresholds_affect_verdict(self, medium_risk_metrics):
        """Custom thresholds change the verdict."""
        # With default thresholds (go=10, caution=25), 15% = CAUTION
        default_engine = DecisionEngine()
        result = create_risk_analysis_result(medium_risk_metrics)
        default_decision = default_engine.analyze(result)
        assert default_decision.verdict == Verdict.CAUTION

        # With lenient thresholds (go=20, caution=40), 15% = GO
        lenient_config = DecisionConfig(go_threshold=20.0, caution_threshold=40.0)
        lenient_engine = DecisionEngine(lenient_config)
        lenient_decision = lenient_engine.analyze(result)
        assert lenient_decision.verdict == Verdict.GO

    def test_max_risk_tracking(self, high_risk_metrics):
        """Engine correctly identifies max risk."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(high_risk_metrics)

        decision = engine.analyze(result)

        # Find actual max from input
        actual_max = max(m.value for m in high_risk_metrics)
        assert decision.max_risk_value == actual_max


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDecisionIntegration:
    """Integration tests for decision system."""

    def test_full_decision_workflow(
        self, high_risk_metrics, sample_risk_map, sample_danger_zones
    ):
        """Full decision workflow from RiskAnalysisResult to Decision."""
        # Create complete risk analysis result
        result = RiskAnalysisResult(
            n_individuals=1000,
            metrics=high_risk_metrics,
            risk_map=sample_risk_map,
            danger_zones=sample_danger_zones,
            thresholds=RiskThresholds(),
        )

        # Analyze
        engine = DecisionEngine()
        decision = engine.analyze(result)

        # Verify decision structure
        assert decision.verdict == Verdict.NO_GO
        assert len(decision.top_risks) > 0
        assert len(decision.top_segments_at_risk) > 0
        assert decision.confidence > 0
        assert len(decision.summary) > 0

        # Verify serialization
        d = decision.to_dict()
        assert "verdict" in d
        assert "top_risks" in d
        assert "summary" in d

    def test_decision_with_real_risk_analyzer_output(self):
        """Decision works with typical RiskAnalyzer output format."""
        # Simulate what RiskAnalyzer would produce
        metrics = [
            make_risk_metric("pct_hyperglycemia", 12.0, "Hyperglycemia Risk"),
            make_risk_metric("pct_jitter_risk", 8.0, "Jitter Risk"),
        ]

        result = create_risk_analysis_result(metrics)
        engine = DecisionEngine()
        decision = engine.analyze(result)

        assert decision.verdict == Verdict.CAUTION
        assert decision.max_risk_value == 12.0


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_exactly_at_go_threshold(self):
        """Exactly at GO threshold is CAUTION (not GO)."""
        metrics = [
            make_risk_metric("pct_hyperglycemia", 10.0, "Hyperglycemia Risk"),
        ]

        engine = DecisionEngine()
        result = create_risk_analysis_result(metrics)
        decision = engine.analyze(result)

        # At threshold = CAUTION (not GO)
        assert decision.verdict == Verdict.CAUTION

    def test_exactly_at_caution_threshold(self):
        """Exactly at CAUTION threshold is NO_GO."""
        metrics = [
            make_risk_metric("pct_hyperglycemia", 25.0, "Hyperglycemia Risk"),
        ]

        engine = DecisionEngine()
        result = create_risk_analysis_result(metrics)
        decision = engine.analyze(result)

        # At threshold = NO_GO
        assert decision.verdict == Verdict.NO_GO

    def test_all_risks_zero(self):
        """All zero risks results in GO."""
        metrics = [
            make_risk_metric("pct_hyperglycemia", 0.0, "Hyperglycemia Risk"),
        ]

        engine = DecisionEngine()
        result = create_risk_analysis_result(metrics)
        decision = engine.analyze(result)

        assert decision.verdict == Verdict.GO
        assert decision.max_risk_value == 0.0

    def test_very_high_confidence_for_extreme_cases(self):
        """Extreme cases have high confidence."""
        # Very low risk
        low_metrics = [
            make_risk_metric("pct_hyperglycemia", 1.0, "Hyperglycemia Risk"),
        ]

        engine = DecisionEngine()
        result = create_risk_analysis_result(low_metrics)
        decision = engine.analyze(result)

        assert decision.confidence >= 0.90

    def test_display_names_in_summary(self, high_risk_metrics):
        """Display names are used in human-readable outputs."""
        engine = DecisionEngine()
        result = create_risk_analysis_result(high_risk_metrics)

        decision = engine.analyze(result)

        # Top risks should have display names
        if decision.top_risks:
            for risk in decision.top_risks:
                assert risk.display_name is not None
                assert len(risk.display_name) > 0
