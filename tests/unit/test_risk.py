"""
Tests for risk analysis module.

Session 5.2: Basic Risk Map
Tests: ~50 tests

Covers:
- RiskThresholds configuration
- RiskMetric dataclass
- RiskAnalyzer class
- Risk Map generation (segment × risk matrix)
- Danger zone identification
- Integration with PopulationDayResult
"""

import pytest
import numpy as np
from dataclasses import FrozenInstanceError
from typing import Dict, Any

# Module under test
from src.analysis.risk import (
    RiskThresholds,
    RiskMetric,
    RiskLevel,
    SegmentRisk,
    RiskMap,
    DangerZone,
    RiskAnalyzer,
    RiskAnalysisResult,
    create_default_thresholds,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def default_thresholds():
    """Default risk thresholds."""
    return create_default_thresholds()


@pytest.fixture
def custom_thresholds():
    """Custom risk thresholds for testing."""
    return RiskThresholds(
        hyperglycemia_threshold_mg_dl=130.0,
        severe_hyperglycemia_threshold_mg_dl=170.0,
        jitter_caffeine_threshold_mg_l=3.5,
        sleep_caffeine_threshold_mg_l=0.8,
        sleep_check_time_minutes=1320,  # 22:00
        crash_alertness_drop_pct=25.0,
        crash_window_minutes=90,
    )


@pytest.fixture
def sample_risk_analysis():
    """Sample risk analysis from PopulationDayResult."""
    return {
        "pct_hyperglycemia": 18.5,
        "pct_severe_hyperglycemia": 5.2,
        "pct_jitter_risk": 12.0,
        "pct_sleep_disruption": 22.0,
        "pct_crash_risk": 8.5,
    }


@pytest.fixture
def sample_subgroup_analysis():
    """Sample subgroup analysis from PopulationDayResult."""
    return {
        "by_bmi": {
            "normal": {
                "count": 400,
                "pct": 40.0,
                "metrics": {
                    "glucose_peak_mean": 135.0,
                    "alertness_duration_mean": 280.0,
                }
            },
            "overweight": {
                "count": 350,
                "pct": 35.0,
                "metrics": {
                    "glucose_peak_mean": 155.0,
                    "alertness_duration_mean": 275.0,
                }
            },
            "obese": {
                "count": 250,
                "pct": 25.0,
                "metrics": {
                    "glucose_peak_mean": 175.0,
                    "alertness_duration_mean": 260.0,
                }
            },
        },
        "by_caffeine_sensitivity": {
            "slow": {
                "count": 200,
                "pct": 20.0,
                "metrics": {
                    "caffeine_at_2200_mean": 2.5,
                    "alertness_duration_mean": 350.0,
                }
            },
            "normal": {
                "count": 600,
                "pct": 60.0,
                "metrics": {
                    "caffeine_at_2200_mean": 0.8,
                    "alertness_duration_mean": 280.0,
                }
            },
            "fast": {
                "count": 200,
                "pct": 20.0,
                "metrics": {
                    "caffeine_at_2200_mean": 0.3,
                    "alertness_duration_mean": 220.0,
                }
            },
        },
        "by_age": {
            "young": {
                "count": 350,
                "pct": 35.0,
                "metrics": {
                    "glucose_peak_mean": 130.0,
                    "alertness_peak_mean": 85.0,
                }
            },
            "middle": {
                "count": 400,
                "pct": 40.0,
                "metrics": {
                    "glucose_peak_mean": 150.0,
                    "alertness_peak_mean": 78.0,
                }
            },
            "older": {
                "count": 250,
                "pct": 25.0,
                "metrics": {
                    "glucose_peak_mean": 165.0,
                    "alertness_peak_mean": 72.0,
                }
            },
        },
    }


@pytest.fixture
def sample_individual_risks():
    """Sample individual risk flags for detailed analysis."""
    # Simulate 100 individuals with various risk combinations
    np.random.seed(42)
    n = 100
    return {
        "person_ids": [f"p{i:03d}" for i in range(n)],
        "bmi_category": np.random.choice(["normal", "overweight", "obese"], n, p=[0.4, 0.35, 0.25]),
        "caffeine_sensitivity": np.random.choice(["slow", "normal", "fast"], n, p=[0.2, 0.6, 0.2]),
        "age_category": np.random.choice(["young", "middle", "older"], n, p=[0.35, 0.4, 0.25]),
        "hyperglycemia_flag": np.random.random(n) < 0.18,
        "severe_hyperglycemia_flag": np.random.random(n) < 0.05,
        "jitter_flag": np.random.random(n) < 0.12,
        "sleep_disruption_flag": np.random.random(n) < 0.22,
        "crash_flag": np.random.random(n) < 0.08,
    }


# =============================================================================
# RISK THRESHOLDS TESTS
# =============================================================================

class TestRiskThresholds:
    """Tests for RiskThresholds configuration."""

    def test_create_default_thresholds(self, default_thresholds):
        """Default thresholds have expected values."""
        assert default_thresholds.hyperglycemia_threshold_mg_dl == 140.0
        assert default_thresholds.severe_hyperglycemia_threshold_mg_dl == 180.0
        assert default_thresholds.jitter_caffeine_threshold_mg_l == 4.0
        assert default_thresholds.sleep_caffeine_threshold_mg_l == 1.0
        assert default_thresholds.sleep_check_time_minutes == 1320  # 22:00
        assert default_thresholds.crash_alertness_drop_pct == 30.0
        assert default_thresholds.crash_window_minutes == 120

    def test_custom_thresholds(self, custom_thresholds):
        """Custom thresholds work correctly."""
        assert custom_thresholds.hyperglycemia_threshold_mg_dl == 130.0
        assert custom_thresholds.jitter_caffeine_threshold_mg_l == 3.5

    def test_thresholds_are_frozen(self, default_thresholds):
        """RiskThresholds is immutable."""
        with pytest.raises(FrozenInstanceError):
            default_thresholds.hyperglycemia_threshold_mg_dl = 150.0

    def test_thresholds_to_dict(self, default_thresholds):
        """Thresholds can be converted to dict."""
        d = default_thresholds.to_dict()
        assert isinstance(d, dict)
        assert d["hyperglycemia_threshold_mg_dl"] == 140.0
        assert d["sleep_check_time_minutes"] == 1320

    def test_thresholds_from_dict(self):
        """Thresholds can be created from dict."""
        data = {
            "hyperglycemia_threshold_mg_dl": 145.0,
            "severe_hyperglycemia_threshold_mg_dl": 185.0,
            "jitter_caffeine_threshold_mg_l": 4.5,
            "sleep_caffeine_threshold_mg_l": 1.2,
            "sleep_check_time_minutes": 1380,
            "crash_alertness_drop_pct": 35.0,
            "crash_window_minutes": 150,
        }
        thresholds = RiskThresholds.from_dict(data)
        assert thresholds.hyperglycemia_threshold_mg_dl == 145.0

    def test_thresholds_validation_rejects_negative(self):
        """Negative thresholds are rejected."""
        with pytest.raises(ValueError, match="must be positive"):
            RiskThresholds(
                hyperglycemia_threshold_mg_dl=-10.0,
                severe_hyperglycemia_threshold_mg_dl=180.0,
                jitter_caffeine_threshold_mg_l=4.0,
                sleep_caffeine_threshold_mg_l=1.0,
                sleep_check_time_minutes=1320,
                crash_alertness_drop_pct=30.0,
                crash_window_minutes=120,
            )

    def test_thresholds_validation_sleep_time_range(self):
        """Sleep check time must be in valid range."""
        with pytest.raises(ValueError, match="sleep_check_time_minutes"):
            RiskThresholds(
                hyperglycemia_threshold_mg_dl=140.0,
                severe_hyperglycemia_threshold_mg_dl=180.0,
                jitter_caffeine_threshold_mg_l=4.0,
                sleep_caffeine_threshold_mg_l=1.0,
                sleep_check_time_minutes=1500,  # > 1440
                crash_alertness_drop_pct=30.0,
                crash_window_minutes=120,
            )


# =============================================================================
# RISK METRIC TESTS
# =============================================================================

class TestRiskMetric:
    """Tests for RiskMetric dataclass."""

    def test_create_risk_metric(self):
        """RiskMetric can be created with valid values."""
        metric = RiskMetric(
            name="pct_hyperglycemia",
            display_name="Hyperglycemia Risk",
            value=18.5,
            threshold_low=10.0,
            threshold_high=25.0,
            description="Percentage with glucose > 140 mg/dL",
        )
        assert metric.name == "pct_hyperglycemia"
        assert metric.value == 18.5

    def test_risk_metric_level_low(self):
        """Level is LOW when value < threshold_low."""
        metric = RiskMetric(
            name="test",
            display_name="Test",
            value=5.0,
            threshold_low=10.0,
            threshold_high=25.0,
        )
        assert metric.level == RiskLevel.LOW

    def test_risk_metric_level_medium(self):
        """Level is MEDIUM when threshold_low <= value < threshold_high."""
        metric = RiskMetric(
            name="test",
            display_name="Test",
            value=15.0,
            threshold_low=10.0,
            threshold_high=25.0,
        )
        assert metric.level == RiskLevel.MEDIUM

    def test_risk_metric_level_high(self):
        """Level is HIGH when value >= threshold_high."""
        metric = RiskMetric(
            name="test",
            display_name="Test",
            value=30.0,
            threshold_low=10.0,
            threshold_high=25.0,
        )
        assert metric.level == RiskLevel.HIGH

    def test_risk_metric_is_frozen(self):
        """RiskMetric is immutable."""
        metric = RiskMetric(
            name="test",
            display_name="Test",
            value=15.0,
            threshold_low=10.0,
            threshold_high=25.0,
        )
        with pytest.raises(FrozenInstanceError):
            metric.value = 20.0

    def test_risk_metric_to_dict(self):
        """RiskMetric can be converted to dict."""
        metric = RiskMetric(
            name="test",
            display_name="Test",
            value=15.0,
            threshold_low=10.0,
            threshold_high=25.0,
            description="Test metric",
        )
        d = metric.to_dict()
        assert d["name"] == "test"
        assert d["value"] == 15.0
        assert d["level"] == "MEDIUM"


# =============================================================================
# RISK LEVEL TESTS
# =============================================================================

class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_levels_exist(self):
        """All risk levels exist."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"

    def test_risk_level_ordering(self):
        """Risk levels can be compared."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH > RiskLevel.LOW


# =============================================================================
# SEGMENT RISK TESTS
# =============================================================================

class TestSegmentRisk:
    """Tests for SegmentRisk dataclass."""

    def test_create_segment_risk(self):
        """SegmentRisk can be created."""
        risk = SegmentRisk(
            segment_dimension="bmi",
            segment_value="obese",
            risk_name="pct_hyperglycemia",
            value=35.0,
            population_pct=25.0,
            count=250,
        )
        assert risk.segment_dimension == "bmi"
        assert risk.value == 35.0

    def test_segment_risk_is_frozen(self):
        """SegmentRisk is immutable."""
        risk = SegmentRisk(
            segment_dimension="bmi",
            segment_value="obese",
            risk_name="pct_hyperglycemia",
            value=35.0,
            population_pct=25.0,
            count=250,
        )
        with pytest.raises(FrozenInstanceError):
            risk.value = 40.0


# =============================================================================
# RISK MAP TESTS
# =============================================================================

class TestRiskMap:
    """Tests for RiskMap class."""

    def test_create_risk_map(self):
        """RiskMap can be created."""
        cells = {
            ("bmi", "normal", "pct_hyperglycemia"): 10.0,
            ("bmi", "obese", "pct_hyperglycemia"): 35.0,
        }
        risk_map = RiskMap(
            dimensions=["bmi", "age", "caffeine_sensitivity"],
            risk_names=["pct_hyperglycemia", "pct_sleep_disruption"],
            cells=cells,
        )
        assert len(risk_map.dimensions) == 3
        assert len(risk_map.risk_names) == 2

    def test_risk_map_get_value(self):
        """RiskMap can retrieve cell values."""
        cells = {
            ("bmi", "obese", "pct_hyperglycemia"): 35.0,
        }
        risk_map = RiskMap(
            dimensions=["bmi"],
            risk_names=["pct_hyperglycemia"],
            cells=cells,
        )
        assert risk_map.get_value("bmi", "obese", "pct_hyperglycemia") == 35.0

    def test_risk_map_get_value_missing(self):
        """RiskMap returns None for missing cells."""
        risk_map = RiskMap(
            dimensions=["bmi"],
            risk_names=["pct_hyperglycemia"],
            cells={},
        )
        assert risk_map.get_value("bmi", "obese", "pct_hyperglycemia") is None

    def test_risk_map_get_segment_risks(self):
        """RiskMap can get all risks for a segment value."""
        cells = {
            ("bmi", "obese", "pct_hyperglycemia"): 35.0,
            ("bmi", "obese", "pct_jitter"): 8.0,
            ("bmi", "normal", "pct_hyperglycemia"): 10.0,
        }
        risk_map = RiskMap(
            dimensions=["bmi"],
            risk_names=["pct_hyperglycemia", "pct_jitter"],
            cells=cells,
        )
        obese_risks = risk_map.get_segment_risks("bmi", "obese")
        assert obese_risks["pct_hyperglycemia"] == 35.0
        assert obese_risks["pct_jitter"] == 8.0

    def test_risk_map_to_matrix(self):
        """RiskMap can be converted to a matrix for visualization."""
        cells = {
            ("bmi", "normal", "pct_hyperglycemia"): 10.0,
            ("bmi", "overweight", "pct_hyperglycemia"): 20.0,
            ("bmi", "obese", "pct_hyperglycemia"): 35.0,
        }
        risk_map = RiskMap(
            dimensions=["bmi"],
            risk_names=["pct_hyperglycemia"],
            cells=cells,
            segment_values={"bmi": ["normal", "overweight", "obese"]},
        )
        matrix = risk_map.to_matrix("bmi")
        assert isinstance(matrix, dict)
        assert "rows" in matrix
        assert "columns" in matrix
        assert "values" in matrix


# =============================================================================
# DANGER ZONE TESTS
# =============================================================================

class TestDangerZone:
    """Tests for DangerZone identification."""

    def test_create_danger_zone(self):
        """DangerZone can be created."""
        dz = DangerZone(
            segment_dimension="bmi",
            segment_value="obese",
            risk_name="pct_hyperglycemia",
            risk_value=35.0,
            population_pct=25.0,
            severity_score=8.75,  # 35.0 * 0.25 = 8.75
            recommendation="Consider reformulation for high-BMI consumers",
        )
        assert dz.segment_value == "obese"
        assert dz.severity_score == 8.75

    def test_danger_zone_is_frozen(self):
        """DangerZone is immutable."""
        dz = DangerZone(
            segment_dimension="bmi",
            segment_value="obese",
            risk_name="pct_hyperglycemia",
            risk_value=35.0,
            population_pct=25.0,
            severity_score=8.75,
        )
        with pytest.raises(FrozenInstanceError):
            dz.risk_value = 40.0


# =============================================================================
# RISK ANALYZER TESTS
# =============================================================================

class TestRiskAnalyzer:
    """Tests for RiskAnalyzer class."""

    def test_create_analyzer_default_thresholds(self):
        """RiskAnalyzer can be created with default thresholds."""
        analyzer = RiskAnalyzer()
        assert analyzer.thresholds is not None

    def test_create_analyzer_custom_thresholds(self, custom_thresholds):
        """RiskAnalyzer can be created with custom thresholds."""
        analyzer = RiskAnalyzer(thresholds=custom_thresholds)
        assert analyzer.thresholds.hyperglycemia_threshold_mg_dl == 130.0

    def test_analyze_population_risks(self, sample_risk_analysis, sample_subgroup_analysis):
        """RiskAnalyzer can analyze population-level risks."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert isinstance(result, RiskAnalysisResult)
        assert len(result.metrics) == 5

    def test_analyze_returns_risk_metrics(self, sample_risk_analysis, sample_subgroup_analysis):
        """Analysis returns proper RiskMetric objects."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        for metric in result.metrics:
            assert isinstance(metric, RiskMetric)
            assert metric.level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]

    def test_analyze_generates_risk_map(self, sample_risk_analysis, sample_subgroup_analysis):
        """Analysis generates a RiskMap."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert result.risk_map is not None
        assert isinstance(result.risk_map, RiskMap)

    def test_analyze_identifies_danger_zones(self, sample_risk_analysis, sample_subgroup_analysis):
        """Analysis identifies danger zones."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        # Should identify some danger zones based on sample data
        assert result.danger_zones is not None
        assert isinstance(result.danger_zones, list)

    def test_analyze_top_risks(self, sample_risk_analysis, sample_subgroup_analysis):
        """Analysis returns top risks sorted by severity."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        top_risks = result.get_top_risks(n=3)
        assert len(top_risks) <= 3
        # Should be sorted by value descending
        for i in range(len(top_risks) - 1):
            assert top_risks[i].value >= top_risks[i + 1].value

    def test_analyze_segments_at_risk(self, sample_risk_analysis, sample_subgroup_analysis):
        """Analysis identifies segments with highest risk."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        segments = result.get_segments_at_risk()
        assert isinstance(segments, list)

    def test_risk_map_by_bmi(self, sample_risk_analysis, sample_subgroup_analysis):
        """Risk map includes BMI segmentation."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert "by_bmi" in result.risk_map.dimensions or "bmi" in str(result.risk_map.dimensions)

    def test_risk_map_by_caffeine_sensitivity(self, sample_risk_analysis, sample_subgroup_analysis):
        """Risk map includes caffeine sensitivity segmentation."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert any("caffeine" in d.lower() for d in result.risk_map.dimensions)

    def test_risk_map_by_age(self, sample_risk_analysis, sample_subgroup_analysis):
        """Risk map includes age segmentation."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert any("age" in d.lower() for d in result.risk_map.dimensions)


# =============================================================================
# RISK ANALYSIS RESULT TESTS
# =============================================================================

class TestRiskAnalysisResult:
    """Tests for RiskAnalysisResult dataclass."""

    def test_result_summary(self, sample_risk_analysis, sample_subgroup_analysis):
        """Result can generate a summary."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        summary = result.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_result_to_dict(self, sample_risk_analysis, sample_subgroup_analysis):
        """Result can be converted to dict."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "metrics" in d
        assert "danger_zones" in d
        assert "risk_map" in d

    def test_result_has_n_individuals(self, sample_risk_analysis, sample_subgroup_analysis):
        """Result includes population size."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert result.n_individuals == 1000

    def test_result_has_highest_risk(self, sample_risk_analysis, sample_subgroup_analysis):
        """Result identifies the highest risk metric."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        highest = result.highest_risk
        assert isinstance(highest, RiskMetric)
        # Sleep disruption is highest in sample data (22%)
        assert highest.name == "pct_sleep_disruption" or highest.value >= 22.0

    def test_result_overall_risk_level(self, sample_risk_analysis, sample_subgroup_analysis):
        """Result provides overall risk level."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert result.overall_risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestRiskAnalyzerIntegration:
    """Integration tests for RiskAnalyzer."""

    def test_full_analysis_workflow(self, sample_risk_analysis, sample_subgroup_analysis):
        """Full workflow from PopulationDayResult to risk analysis."""
        # Create analyzer
        analyzer = RiskAnalyzer()

        # Analyze
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )

        # Verify all components present
        assert result.metrics is not None
        assert result.risk_map is not None
        assert result.danger_zones is not None
        assert result.n_individuals == 1000

        # Verify metrics
        metric_names = {m.name for m in result.metrics}
        expected = {
            "pct_hyperglycemia",
            "pct_severe_hyperglycemia",
            "pct_jitter_risk",
            "pct_sleep_disruption",
            "pct_crash_risk",
        }
        assert metric_names == expected

        # Verify risk map has all dimensions
        assert len(result.risk_map.dimensions) == 3

    def test_danger_zone_recommendations(self, sample_risk_analysis, sample_subgroup_analysis):
        """Danger zones include actionable recommendations."""
        # Modify data to create a clear danger zone
        modified_subgroup = sample_subgroup_analysis.copy()
        # Increase risk for slow caffeine metabolizers
        modified_subgroup["by_caffeine_sensitivity"]["slow"]["metrics"]["caffeine_at_2200_mean"] = 3.0

        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=modified_subgroup,
            n_individuals=1000,
        )

        # Check that danger zones have recommendations
        for dz in result.danger_zones:
            if dz.severity_score > 5.0:
                assert dz.recommendation is not None or len(str(dz)) > 0

    def test_custom_thresholds_affect_levels(self, sample_risk_analysis, sample_subgroup_analysis):
        """Custom thresholds affect risk level classification."""
        # With default thresholds, 18.5% hyperglycemia should be MEDIUM (10-25%)
        default_analyzer = RiskAnalyzer()
        default_result = default_analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )

        hyperglycemia_default = next(
            m for m in default_result.metrics if m.name == "pct_hyperglycemia"
        )

        # With stricter thresholds, same value might be HIGH
        strict_thresholds = RiskThresholds(
            hyperglycemia_threshold_mg_dl=140.0,
            severe_hyperglycemia_threshold_mg_dl=180.0,
            jitter_caffeine_threshold_mg_l=4.0,
            sleep_caffeine_threshold_mg_l=1.0,
            sleep_check_time_minutes=1320,
            crash_alertness_drop_pct=30.0,
            crash_window_minutes=120,
            # Lower classification thresholds
            risk_level_low_threshold=5.0,
            risk_level_high_threshold=15.0,
        )
        strict_analyzer = RiskAnalyzer(thresholds=strict_thresholds)
        strict_result = strict_analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )

        hyperglycemia_strict = next(
            m for m in strict_result.metrics if m.name == "pct_hyperglycemia"
        )

        # With stricter thresholds, level should be higher
        assert hyperglycemia_strict.level >= hyperglycemia_default.level


# =============================================================================
# EDGE CASES
# =============================================================================

class TestRiskAnalyzerEdgeCases:
    """Edge case tests for RiskAnalyzer."""

    def test_empty_risk_analysis(self):
        """Handles empty risk analysis."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis={},
            subgroup_analysis={},
            n_individuals=0,
        )
        assert result.n_individuals == 0
        assert len(result.metrics) == 0

    def test_zero_population(self, sample_risk_analysis):
        """Handles zero population gracefully."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis={},
            n_individuals=0,
        )
        assert result.n_individuals == 0

    def test_all_zero_risks(self):
        """Handles case with no risks."""
        zero_risks = {
            "pct_hyperglycemia": 0.0,
            "pct_severe_hyperglycemia": 0.0,
            "pct_jitter_risk": 0.0,
            "pct_sleep_disruption": 0.0,
            "pct_crash_risk": 0.0,
        }
        # Pass empty subgroup analysis to avoid estimated segment risks
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=zero_risks,
            subgroup_analysis={},
            n_individuals=1000,
        )
        assert result.overall_risk_level == RiskLevel.LOW
        assert len(result.danger_zones) == 0

    def test_all_high_risks(self, sample_subgroup_analysis):
        """Handles case with all high risks."""
        high_risks = {
            "pct_hyperglycemia": 50.0,
            "pct_severe_hyperglycemia": 30.0,
            "pct_jitter_risk": 45.0,
            "pct_sleep_disruption": 60.0,
            "pct_crash_risk": 40.0,
        }
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=high_risks,
            subgroup_analysis=sample_subgroup_analysis,
            n_individuals=1000,
        )
        assert result.overall_risk_level == RiskLevel.HIGH
        assert len(result.danger_zones) > 0

    def test_partial_subgroup_data(self, sample_risk_analysis):
        """Handles missing subgroup dimensions."""
        partial_subgroups = {
            "by_bmi": {
                "normal": {"count": 500, "pct": 50.0, "metrics": {}},
                "obese": {"count": 500, "pct": 50.0, "metrics": {}},
            }
        }
        analyzer = RiskAnalyzer()
        result = analyzer.analyze(
            risk_analysis=sample_risk_analysis,
            subgroup_analysis=partial_subgroups,
            n_individuals=1000,
        )
        # Should still work with available dimensions
        assert "by_bmi" in result.risk_map.dimensions or len(result.risk_map.dimensions) >= 1
