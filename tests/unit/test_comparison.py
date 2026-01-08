# MODULUS - A/B Comparison Engine Tests
# Session 10.2: Test-first development
# ==============================================================================

"""
Tests for the A/B Comparison Engine.

The comparison engine takes two PopulationSimulationResult objects and produces
a detailed comparison including:
- Metric deltas with statistical significance
- Winner determination per metric
- Overall recommendation
- Visual-ready comparison data
"""

import pytest
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

# Import from the correct module path
from src.analysis.comparison import (
    ComparisonEngine,
    ComparisonConfig,
    Comparison,
    MetricComparison,
    RiskComparison,
    Winner,
    METRIC_DIRECTIONS,
    compare_formulations,
    format_comparison_for_pdf,
)


# ==============================================================================
# MOCK DATA STRUCTURES (Based on Contract 5.2)
# ==============================================================================

@dataclass
class MockPopulationSimulationResult:
    """Mock PopulationSimulationResult for testing comparison engine."""
    n_individuals: int
    n_valid: int
    time_minutes: np.ndarray
    
    # Percentiles
    glucose_percentiles: Dict[str, np.ndarray]
    alertness_percentiles: Dict[str, np.ndarray]
    caffeine_percentiles: Dict[str, np.ndarray]
    
    # Statistics
    metrics_stats: Dict[str, Dict[str, float]]
    
    # Risk analysis
    risk_analysis: Dict[str, float]
    
    # Subgroup analysis
    subgroup_analysis: Dict[str, Dict[str, Any]]
    
    # Metadata
    formulation_name: str = "Unknown"
    simulation_seed: int = 42


def create_mock_result_a() -> MockPopulationSimulationResult:
    """Create mock result A (baseline product)."""
    time = np.arange(0, 1441, 1.0)
    return MockPopulationSimulationResult(
        n_individuals=1000,
        n_valid=980,
        time_minutes=time,
        glucose_percentiles={
            "p5": np.full(1441, 85.0),
            "p25": np.full(1441, 95.0),
            "p50": np.full(1441, 110.0),
            "p75": np.full(1441, 130.0),
            "p95": np.full(1441, 155.0),
        },
        alertness_percentiles={
            "p5": np.full(1441, 40.0),
            "p25": np.full(1441, 55.0),
            "p50": np.full(1441, 70.0),
            "p75": np.full(1441, 80.0),
            "p95": np.full(1441, 90.0),
        },
        caffeine_percentiles={
            "p5": np.full(1441, 0.5),
            "p25": np.full(1441, 1.0),
            "p50": np.full(1441, 2.0),
            "p75": np.full(1441, 3.0),
            "p95": np.full(1441, 4.5),
        },
        metrics_stats={
            "glucose_peak": {"mean": 145.0, "std": 25.0, "p10": 115.0, "p90": 175.0},
            "glucose_auc": {"mean": 14500.0, "std": 2000.0, "p10": 12000.0, "p90": 17000.0},
            "alertness_peak": {"mean": 75.0, "std": 12.0, "p10": 58.0, "p90": 88.0},
            "alertness_duration_above_60": {"mean": 240.0, "std": 60.0, "p10": 160.0, "p90": 320.0},
            "caffeine_peak": {"mean": 2.5, "std": 0.8, "p10": 1.5, "p90": 3.5},
            "time_to_alertness_peak": {"mean": 45.0, "std": 15.0, "p10": 25.0, "p90": 70.0},
        },
        risk_analysis={
            "pct_hyperglycemia": 0.18,  # 18%
            "pct_severe_hyperglycemia": 0.05,  # 5%
            "pct_jitter_risk": 0.12,  # 12%
            "pct_sleep_disruption": 0.22,  # 22%
            "pct_crash_risk": 0.08,  # 8%
        },
        subgroup_analysis={
            "by_bmi": {"normal": {"n": 400}, "overweight": {"n": 350}, "obese": {"n": 250}},
            "by_age": {"young": {"n": 350}, "middle": {"n": 400}, "older": {"n": 250}},
        },
        formulation_name="Product A",
    )


def create_mock_result_b() -> MockPopulationSimulationResult:
    """Create mock result B (improved product)."""
    time = np.arange(0, 1441, 1.0)
    return MockPopulationSimulationResult(
        n_individuals=1000,
        n_valid=985,
        time_minutes=time,
        glucose_percentiles={
            "p5": np.full(1441, 82.0),
            "p25": np.full(1441, 92.0),
            "p50": np.full(1441, 105.0),  # Lower than A
            "p75": np.full(1441, 125.0),
            "p95": np.full(1441, 145.0),
        },
        alertness_percentiles={
            "p5": np.full(1441, 45.0),
            "p25": np.full(1441, 60.0),
            "p50": np.full(1441, 75.0),  # Higher than A
            "p75": np.full(1441, 85.0),
            "p95": np.full(1441, 92.0),
        },
        caffeine_percentiles={
            "p5": np.full(1441, 0.4),
            "p25": np.full(1441, 0.8),
            "p50": np.full(1441, 1.5),  # Lower than A
            "p75": np.full(1441, 2.2),
            "p95": np.full(1441, 3.0),
        },
        metrics_stats={
            "glucose_peak": {"mean": 135.0, "std": 22.0, "p10": 108.0, "p90": 165.0},  # Lower
            "glucose_auc": {"mean": 13800.0, "std": 1800.0, "p10": 11500.0, "p90": 16000.0},
            "alertness_peak": {"mean": 78.0, "std": 10.0, "p10": 64.0, "p90": 90.0},  # Higher
            "alertness_duration_above_60": {"mean": 280.0, "std": 55.0, "p10": 200.0, "p90": 360.0},  # Higher
            "caffeine_peak": {"mean": 1.8, "std": 0.6, "p10": 1.0, "p90": 2.5},  # Lower
            "time_to_alertness_peak": {"mean": 40.0, "std": 12.0, "p10": 22.0, "p90": 60.0},  # Faster
        },
        risk_analysis={
            "pct_hyperglycemia": 0.12,  # Lower risk
            "pct_severe_hyperglycemia": 0.03,  # Lower
            "pct_jitter_risk": 0.06,  # Lower
            "pct_sleep_disruption": 0.15,  # Lower
            "pct_crash_risk": 0.05,  # Lower
        },
        subgroup_analysis={
            "by_bmi": {"normal": {"n": 410}, "overweight": {"n": 345}, "obese": {"n": 245}},
            "by_age": {"young": {"n": 355}, "middle": {"n": 395}, "older": {"n": 250}},
        },
        formulation_name="Product B",
    )


def create_mock_result_similar() -> MockPopulationSimulationResult:
    """Create mock result similar to A (for tie testing)."""
    time = np.arange(0, 1441, 1.0)
    return MockPopulationSimulationResult(
        n_individuals=1000,
        n_valid=982,
        time_minutes=time,
        glucose_percentiles={
            "p5": np.full(1441, 84.0),
            "p25": np.full(1441, 94.0),
            "p50": np.full(1441, 109.0),  # Very close to A
            "p75": np.full(1441, 129.0),
            "p95": np.full(1441, 154.0),
        },
        alertness_percentiles={
            "p5": np.full(1441, 41.0),
            "p25": np.full(1441, 56.0),
            "p50": np.full(1441, 71.0),  # Very close to A
            "p75": np.full(1441, 81.0),
            "p95": np.full(1441, 91.0),
        },
        caffeine_percentiles={
            "p5": np.full(1441, 0.48),
            "p25": np.full(1441, 0.98),
            "p50": np.full(1441, 1.98),
            "p75": np.full(1441, 2.98),
            "p95": np.full(1441, 4.48),
        },
        metrics_stats={
            "glucose_peak": {"mean": 144.0, "std": 24.5, "p10": 114.5, "p90": 174.0},  # ~same
            "glucose_auc": {"mean": 14450.0, "std": 1980.0, "p10": 11980.0, "p90": 16950.0},
            "alertness_peak": {"mean": 75.5, "std": 11.8, "p10": 58.5, "p90": 88.5},  # ~same
            "alertness_duration_above_60": {"mean": 242.0, "std": 58.0, "p10": 162.0, "p90": 318.0},
            "caffeine_peak": {"mean": 2.48, "std": 0.78, "p10": 1.48, "p90": 3.48},
            "time_to_alertness_peak": {"mean": 44.5, "std": 14.8, "p10": 25.2, "p90": 69.5},
        },
        risk_analysis={
            "pct_hyperglycemia": 0.175,  # ~same
            "pct_severe_hyperglycemia": 0.048,
            "pct_jitter_risk": 0.118,
            "pct_sleep_disruption": 0.218,
            "pct_crash_risk": 0.078,
        },
        subgroup_analysis={
            "by_bmi": {"normal": {"n": 402}, "overweight": {"n": 348}, "obese": {"n": 252}},
            "by_age": {"young": {"n": 352}, "middle": {"n": 398}, "older": {"n": 252}},
        },
        formulation_name="Product A'",
    )


# ==============================================================================
# TESTS: MetricComparison
# ==============================================================================

class TestMetricComparison:
    """Tests for individual metric comparison."""
    
    def test_metric_comparison_creation(self):
        """MetricComparison is created with required fields."""
        mc = MetricComparison(
            metric_name="glucose_peak",
            value_a=145.0,
            value_b=135.0,
            delta=-10.0,
            delta_percent=-6.9,
            winner="B",
            is_significant=True,
            p_value=0.001,
            effect_size=0.42,
            better_direction="lower",
        )
        
        assert mc.metric_name == "glucose_peak"
        assert mc.value_a == 145.0
        assert mc.value_b == 135.0
        assert mc.delta == -10.0
        assert mc.winner == "B"
        assert mc.is_significant is True
    
    def test_metric_comparison_immutable(self):
        """MetricComparison should be immutable (frozen dataclass)."""
        mc = MetricComparison(
            metric_name="glucose_peak",
            value_a=145.0,
            value_b=135.0,
            delta=-10.0,
            delta_percent=-6.9,
            winner="B",
            is_significant=True,
            p_value=0.001,
            effect_size=0.42,
            better_direction="lower",
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            mc.value_a = 200.0
    
    def test_metric_comparison_to_dict(self):
        """MetricComparison can be serialized to dict."""
        mc = MetricComparison(
            metric_name="glucose_peak",
            value_a=145.0,
            value_b=135.0,
            delta=-10.0,
            delta_percent=-6.9,
            winner="B",
            is_significant=True,
            p_value=0.001,
            effect_size=0.42,
            better_direction="lower",
        )
        
        d = mc.to_dict()
        assert d["metric_name"] == "glucose_peak"
        assert d["value_a"] == 145.0
        assert d["winner"] == "B"


# ==============================================================================
# TESTS: RiskComparison  
# ==============================================================================

class TestRiskComparison:
    """Tests for risk comparison."""
    
    def test_risk_comparison_creation(self):
        """RiskComparison is created with required fields."""
        rc = RiskComparison(
            risk_name="pct_hyperglycemia",
            value_a=0.18,
            value_b=0.12,
            delta=-0.06,
            delta_percent=-33.3,
            winner="B",
            absolute_improvement=0.06,
        )
        
        assert rc.risk_name == "pct_hyperglycemia"
        assert rc.value_a == 0.18
        assert rc.winner == "B"
        assert rc.absolute_improvement == 0.06
    
    def test_risk_comparison_lower_is_better(self):
        """For risk, lower values should win."""
        # B has lower risk
        rc = RiskComparison(
            risk_name="pct_jitter_risk",
            value_a=0.12,
            value_b=0.06,
            delta=-0.06,
            delta_percent=-50.0,
            winner="B",
            absolute_improvement=0.06,
        )
        
        assert rc.winner == "B"


# ==============================================================================
# TESTS: Comparison Result
# ==============================================================================

class TestComparison:
    """Tests for the full Comparison result object."""
    
    def test_comparison_creation(self):
        """Comparison is created with all required fields."""
        comparison = Comparison(
            formulation_a_name="Product A",
            formulation_b_name="Product B",
            n_individuals_a=1000,
            n_individuals_b=1000,
            metric_comparisons={
                "glucose_peak": MetricComparison(
                    metric_name="glucose_peak",
                    value_a=145.0,
                    value_b=135.0,
                    delta=-10.0,
                    delta_percent=-6.9,
                    winner="B",
                    is_significant=True,
                    p_value=0.001,
                    effect_size=0.42,
                    better_direction="lower",
                ),
            },
            risk_comparisons={
                "pct_hyperglycemia": RiskComparison(
                    risk_name="pct_hyperglycemia",
                    value_a=0.18,
                    value_b=0.12,
                    delta=-0.06,
                    delta_percent=-33.3,
                    winner="B",
                    absolute_improvement=0.06,
                ),
            },
            winner_by_metric={"glucose_peak": Winner.B},
            winner_by_risk={"pct_hyperglycemia": Winner.B},
            overall_winner=Winner.B,
            overall_confidence=0.85,
            summary="Product B shows significant improvements in glucose control and risk reduction.",
        )
        
        assert comparison.formulation_a_name == "Product A"
        assert comparison.overall_winner == Winner.B
    
    def test_comparison_to_dict(self):
        """Comparison can be serialized to dict."""
        comparison = Comparison(
            formulation_a_name="Product A",
            formulation_b_name="Product B",
            n_individuals_a=1000,
            n_individuals_b=1000,
            metric_comparisons={},
            risk_comparisons={},
            winner_by_metric={},
            winner_by_risk={},
            overall_winner=Winner.B,
            overall_confidence=0.85,
            summary="B wins.",
        )
        
        d = comparison.to_dict()
        assert d["formulation_a_name"] == "Product A"
        assert d["overall_winner"] == "B"
    
    def test_comparison_get_top_differences(self):
        """Comparison.get_top_differences() returns sorted differences."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        top_diffs = comparison.get_top_differences(n=3)
        
        assert len(top_diffs) <= 3
        # Should be sorted by absolute delta percent
        if len(top_diffs) >= 2:
            assert abs(top_diffs[0]["delta_percent"]) >= abs(top_diffs[1]["delta_percent"])


# ==============================================================================
# TESTS: Winner Enum
# ==============================================================================

class TestWinnerEnum:
    """Tests for the Winner enumeration."""
    
    def test_winner_values(self):
        """Winner enum has correct values."""
        assert Winner.A.value == "A"
        assert Winner.B.value == "B"
        assert Winner.TIE.value == "TIE"
    
    def test_winner_string_representation(self):
        """Winner can be converted to string."""
        assert str(Winner.A) == "Winner.A"
        assert Winner.A.value == "A"


# ==============================================================================
# TESTS: ComparisonEngine Basic
# ==============================================================================

class TestComparisonEngineBasic:
    """Basic tests for ComparisonEngine."""
    
    def test_engine_creation(self):
        """ComparisonEngine can be instantiated."""
        engine = ComparisonEngine()
        assert engine is not None
    
    def test_engine_creation_with_config(self):
        """ComparisonEngine accepts configuration."""
        config = ComparisonConfig(
            significance_threshold=0.01,
            tie_threshold_percent=2.0,
        )
        engine = ComparisonEngine(config=config)
        
        assert engine.config.significance_threshold == 0.01
        assert engine.config.tie_threshold_percent == 2.0
    
    def test_compare_returns_comparison(self):
        """ComparisonEngine.compare() returns Comparison object."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        assert isinstance(comparison, Comparison)
    
    def test_compare_preserves_names(self):
        """Comparison preserves formulation names."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        assert comparison.formulation_a_name == "Product A"
        assert comparison.formulation_b_name == "Product B"


# ==============================================================================
# TESTS: Metric Comparison Logic
# ==============================================================================

class TestMetricComparisonLogic:
    """Tests for metric comparison calculations."""
    
    def test_glucose_peak_comparison(self):
        """Lower glucose peak should be better."""
        result_a = create_mock_result_a()  # glucose_peak mean = 145
        result_b = create_mock_result_b()  # glucose_peak mean = 135
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["glucose_peak"]
        assert mc.value_a > mc.value_b
        assert mc.delta < 0  # B - A is negative
        assert mc.winner == "B"  # B is better (lower)
    
    def test_alertness_peak_comparison(self):
        """Higher alertness peak should be better."""
        result_a = create_mock_result_a()  # alertness_peak mean = 75
        result_b = create_mock_result_b()  # alertness_peak mean = 78
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["alertness_peak"]
        assert mc.value_b > mc.value_a
        assert mc.delta > 0  # B - A is positive
        # Note: with 5% tie threshold, 4% difference may be TIE
        assert mc.winner in ["B", "TIE"]
    
    def test_alertness_duration_comparison(self):
        """Longer alertness duration should be better."""
        result_a = create_mock_result_a()  # alertness_duration_above_60 = 240
        result_b = create_mock_result_b()  # alertness_duration_above_60 = 280
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["alertness_duration_above_60"]
        assert mc.delta > 0  # B - A is positive
        assert mc.winner == "B"  # B is better (longer duration)
    
    def test_delta_percent_calculation(self):
        """Delta percent is calculated correctly."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["glucose_peak"]
        # delta = 135 - 145 = -10
        # delta_percent = -10 / 145 * 100 = -6.9%
        expected_delta_percent = (135.0 - 145.0) / 145.0 * 100
        assert abs(mc.delta_percent - expected_delta_percent) < 0.1
    
    def test_tie_detection(self):
        """Similar values should be detected as tie."""
        result_a = create_mock_result_a()
        result_similar = create_mock_result_similar()
        
        config = ComparisonConfig(tie_threshold_percent=5.0)  # 5% threshold
        engine = ComparisonEngine(config=config)
        comparison = engine.compare(result_a, result_similar)
        
        # Glucose peak: 145 vs 144 = 0.69% difference -> TIE
        mc = comparison.metric_comparisons["glucose_peak"]
        assert mc.winner == "TIE"


# ==============================================================================
# TESTS: Risk Comparison Logic
# ==============================================================================

class TestRiskComparisonLogic:
    """Tests for risk comparison calculations."""
    
    def test_hyperglycemia_risk_comparison(self):
        """Lower hyperglycemia risk should be better."""
        result_a = create_mock_result_a()  # 18%
        result_b = create_mock_result_b()  # 12%
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        rc = comparison.risk_comparisons["pct_hyperglycemia"]
        assert rc.value_a == 0.18
        assert rc.value_b == 0.12
        assert rc.winner == "B"
        assert rc.absolute_improvement == 0.06
    
    def test_all_risks_compared(self):
        """All risk metrics should be compared."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        expected_risks = [
            "pct_hyperglycemia",
            "pct_severe_hyperglycemia",
            "pct_jitter_risk",
            "pct_sleep_disruption",
            "pct_crash_risk",
        ]
        
        for risk in expected_risks:
            assert risk in comparison.risk_comparisons
    
    def test_risk_winner_by_risk(self):
        """winner_by_risk dict should be populated correctly."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        # B has lower risks across the board, but some may be TIE if within threshold
        # At minimum, most risks should favor B
        b_wins = sum(1 for w in comparison.winner_by_risk.values() if w == Winner.B)
        a_wins = sum(1 for w in comparison.winner_by_risk.values() if w == Winner.A)
        
        # B should win more risk comparisons than A
        assert b_wins > a_wins
        # B should win at least 3 out of 5 risks
        assert b_wins >= 3


# ==============================================================================
# TESTS: Statistical Significance
# ==============================================================================

class TestStatisticalSignificance:
    """Tests for statistical significance calculations."""
    
    def test_significance_with_large_n(self):
        """Large N should produce significant results for clear differences."""
        result_a = create_mock_result_a()  # n=1000
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        # Glucose peak difference (145 vs 135) with n=1000 should be significant
        mc = comparison.metric_comparisons["glucose_peak"]
        assert mc.is_significant is True
        assert mc.p_value is not None
        assert mc.p_value < 0.05
    
    def test_effect_size_calculation(self):
        """Effect size (Cohen's d) should be calculated."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["glucose_peak"]
        assert mc.effect_size is not None
        # Cohen's d for glucose: (135-145) / pooled_std
        # With std_a=25, std_b=22, difference=-10
        # Should be a moderate effect size
        assert 0.1 < abs(mc.effect_size) < 1.0
    
    def test_significance_for_similar_values(self):
        """Similar values should not be significant."""
        result_a = create_mock_result_a()
        result_similar = create_mock_result_similar()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_similar)
        
        mc = comparison.metric_comparisons["glucose_peak"]
        # 145 vs 144 with similar std should not be significant
        assert mc.is_significant is False


# ==============================================================================
# TESTS: Overall Winner Determination
# ==============================================================================

class TestOverallWinner:
    """Tests for overall winner determination."""
    
    def test_clear_winner_determination(self):
        """Clear winner should be determined when one product dominates."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()  # Better on all metrics
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        assert comparison.overall_winner == Winner.B
        assert comparison.overall_confidence > 0.7
    
    def test_tie_when_similar(self):
        """Tie should be declared when products are similar."""
        result_a = create_mock_result_a()
        result_similar = create_mock_result_similar()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_similar)
        
        # Most metrics should be TIE
        tie_count = sum(1 for w in comparison.winner_by_metric.values() if w == Winner.TIE)
        total_metrics = len(comparison.winner_by_metric)
        
        # If more than half are ties, overall should likely be TIE
        if tie_count > total_metrics / 2:
            assert comparison.overall_winner == Winner.TIE
    
    def test_confidence_score_range(self):
        """Confidence score should be between 0 and 1."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        assert 0.0 <= comparison.overall_confidence <= 1.0


# ==============================================================================
# TESTS: Summary Generation
# ==============================================================================

class TestSummaryGeneration:
    """Tests for summary text generation."""
    
    def test_summary_not_empty(self):
        """Summary should not be empty."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        assert comparison.summary is not None
        assert len(comparison.summary) > 0
    
    def test_summary_mentions_winner(self):
        """Summary should mention the winning product."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        if comparison.overall_winner == Winner.B:
            assert "Product B" in comparison.summary or "B" in comparison.summary
    
    def test_summary_mentions_key_improvements(self):
        """Summary should mention key improvements."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        # Summary should mention at least one of the key differences
        keywords = ["glucose", "alertness", "risk", "sleep", "jitter", "improvement", "lower", "higher"]
        has_keyword = any(kw.lower() in comparison.summary.lower() for kw in keywords)
        assert has_keyword


# ==============================================================================
# TESTS: Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_compare_same_result(self):
        """Comparing same result should give TIE."""
        result_a = create_mock_result_a()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_a)
        
        assert comparison.overall_winner == Winner.TIE
        # All metrics should be TIE
        for winner in comparison.winner_by_metric.values():
            assert winner == Winner.TIE
    
    def test_missing_metric_handled(self):
        """Missing metrics should be handled gracefully."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        # Remove a metric from B
        del result_b.metrics_stats["time_to_alertness_peak"]
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        # Should still work, just not compare that metric
        assert "time_to_alertness_peak" not in comparison.metric_comparisons
    
    def test_zero_value_handling(self):
        """Zero values should not cause division by zero."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        # Set a value to zero
        result_a.metrics_stats["caffeine_peak"]["mean"] = 0.0
        
        engine = ComparisonEngine()
        # Should not raise ZeroDivisionError
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["caffeine_peak"]
        # Delta percent should handle zero (use absolute or special value)
        assert mc.delta_percent is not None


# ==============================================================================
# TESTS: Multi-Product Comparison
# ==============================================================================

class TestMultiProductComparison:
    """Tests for comparing more than 2 products."""
    
    def test_compare_multiple_returns_list(self):
        """compare_multiple should return list of pairwise comparisons."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        result_c = create_mock_result_similar()
        
        engine = ComparisonEngine()
        comparisons = engine.compare_multiple([result_a, result_b, result_c])
        
        # Should have 3 pairwise comparisons: A-B, A-C, B-C
        assert len(comparisons) == 3
    
    def test_compare_multiple_ranking(self):
        """compare_multiple should produce ranking."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        result_c = create_mock_result_similar()
        
        engine = ComparisonEngine()
        ranking = engine.rank_products([result_a, result_b, result_c])
        
        # B should be ranked first (best product)
        assert ranking[0]["name"] == "Product B"


# ==============================================================================
# TESTS: Serialization
# ==============================================================================

class TestSerialization:
    """Tests for serialization to dict/JSON."""
    
    def test_comparison_to_dict(self):
        """Full comparison can be serialized to dict."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        d = comparison.to_dict()
        
        assert "formulation_a_name" in d
        assert "formulation_b_name" in d
        assert "metric_comparisons" in d
        assert "risk_comparisons" in d
        assert "overall_winner" in d
        assert "summary" in d
    
    def test_comparison_to_json_string(self):
        """Comparison can be serialized to JSON string."""
        import json
        
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        json_str = comparison.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["formulation_a_name"] == "Product A"


# ==============================================================================
# TESTS: PDF/Report Ready Output
# ==============================================================================

class TestReportReady:
    """Tests for report-ready output formats."""
    
    def test_format_for_pdf(self):
        """format_for_pdf returns structured data for PDF generation."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        pdf_data = comparison.format_for_pdf()
        
        assert "title" in pdf_data
        assert "executive_summary" in pdf_data
        assert "metric_table" in pdf_data
        assert "risk_table" in pdf_data
        assert "winner_summary" in pdf_data
    
    def test_metric_table_format(self):
        """Metric table is formatted correctly for PDF."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        pdf_data = comparison.format_for_pdf()
        metric_table = pdf_data["metric_table"]
        
        # Should have headers and rows
        assert "headers" in metric_table
        assert "rows" in metric_table
        assert len(metric_table["rows"]) > 0
        
        # Each row should have values for both products
        first_row = metric_table["rows"][0]
        assert "metric" in first_row
        assert "value_a" in first_row
        assert "value_b" in first_row
        assert "delta" in first_row
        assert "winner" in first_row


# ==============================================================================
# TESTS: ComparisonConfig
# ==============================================================================

class TestComparisonConfig:
    """Tests for ComparisonConfig."""
    
    def test_default_config(self):
        """Default config has sensible values."""
        config = ComparisonConfig()
        
        assert config.significance_threshold == 0.05
        assert config.tie_threshold_percent == 5.0
        assert config.min_effect_size == 0.2
    
    def test_custom_config(self):
        """Custom config values are respected."""
        config = ComparisonConfig(
            tie_threshold_percent=10.0,  # Very wide threshold
        )
        
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine(config=config)
        comparison = engine.compare(result_a, result_b)
        
        # With wide threshold, glucose_peak (145 vs 135 = 6.9% diff) might be TIE
        mc = comparison.metric_comparisons["glucose_peak"]
        # 6.9% < 10% threshold, should be TIE
        assert mc.winner == "TIE"


# ==============================================================================
# TESTS: Metric Direction Configuration
# ==============================================================================

class TestMetricDirections:
    """Tests for metric direction configuration (higher/lower is better)."""
    
    def test_default_directions(self):
        """Default metric directions are correct."""
        # Lower is better for glucose
        assert METRIC_DIRECTIONS["glucose_peak"] == "lower"
        assert METRIC_DIRECTIONS["glucose_auc"] == "lower"
        
        # Higher is better for alertness
        assert METRIC_DIRECTIONS["alertness_peak"] == "higher"
        assert METRIC_DIRECTIONS["alertness_duration_above_60"] == "higher"
        
        # Lower is better for time metrics (faster)
        assert METRIC_DIRECTIONS["time_to_alertness_peak"] == "lower"
    
    def test_custom_direction_respected(self):
        """Custom metric direction is respected."""
        config = ComparisonConfig(
            metric_directions={"caffeine_peak": "lower"}  # Lower caffeine = better
        )
        
        result_a = create_mock_result_a()  # caffeine_peak = 2.5
        result_b = create_mock_result_b()  # caffeine_peak = 1.8
        
        engine = ComparisonEngine(config=config)
        comparison = engine.compare(result_a, result_b)
        
        mc = comparison.metric_comparisons["caffeine_peak"]
        assert mc.winner == "B"  # Lower is better


# ==============================================================================
# TESTS: Convenience Functions
# ==============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_compare_formulations_function(self):
        """compare_formulations convenience function works."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        comparison = compare_formulations(result_a, result_b)
        
        assert isinstance(comparison, Comparison)
        assert comparison.overall_winner == Winner.B
    
    def test_format_comparison_for_pdf_function(self):
        """format_comparison_for_pdf convenience function works."""
        result_a = create_mock_result_a()
        result_b = create_mock_result_b()
        
        engine = ComparisonEngine()
        comparison = engine.compare(result_a, result_b)
        
        pdf_data = format_comparison_for_pdf(comparison)
        
        assert "title" in pdf_data
        assert "metric_table" in pdf_data


# ==============================================================================
# Run tests if executed directly
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
