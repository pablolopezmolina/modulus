# tests/unit/test_metrics.py
"""
Tests for the analysis.metrics module.

These tests verify that metrics are calculated correctly from
DaySimulationResult or raw numpy arrays.
"""

import numpy as np
import pytest
from typing import Dict, List

# Import the metrics module (will be created)
from src.analysis.metrics import (
    # Glucose metrics
    calculate_glucose_peak,
    calculate_glucose_time_to_peak,
    calculate_glucose_auc,
    calculate_time_above_glucose_threshold,
    
    # Caffeine metrics
    calculate_caffeine_peak,
    calculate_caffeine_half_life,
    
    # Alertness metrics
    calculate_alertness_peak,
    calculate_alertness_duration_above_threshold,
    
    # Risk metrics
    calculate_sleep_disruption_risk,
    
    # Batch calculator
    MetricsCalculator,
    calculate_all_metrics,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def time_24h():
    """Time array for 24h simulation with dt=1 minute."""
    return np.arange(0, 1441, dtype=float)  # 0 to 1440 inclusive


@pytest.fixture
def flat_glucose_curve(time_24h):
    """Flat glucose at 100 mg/dL (baseline)."""
    return np.full(len(time_24h), 100.0)


@pytest.fixture
def peak_glucose_curve(time_24h):
    """Glucose curve with a single peak at 30 minutes."""
    # Baseline 90, peak at 160 at t=30min
    curve = np.full(len(time_24h), 90.0)
    # Gaussian-like peak
    for i, t in enumerate(time_24h):
        if 0 <= t <= 120:
            curve[i] = 90 + 70 * np.exp(-((t - 30) ** 2) / (2 * 15 ** 2))
    return curve


@pytest.fixture
def caffeine_curve_100mg(time_24h):
    """Caffeine curve for 100mg dose at t=0, half-life ~5h."""
    # Simple exponential decay with peak at ~45 min
    # Cmax ~2 mg/L, half-life ~5h (300 min)
    curve = np.zeros(len(time_24h))
    t_max = 45  # minutes
    c_max = 2.0  # mg/L
    half_life = 300  # minutes (5 hours)
    k_el = np.log(2) / half_life
    
    for i, t in enumerate(time_24h):
        if t < t_max:
            # Absorption phase
            curve[i] = c_max * (t / t_max)
        else:
            # Elimination phase
            curve[i] = c_max * np.exp(-k_el * (t - t_max))
    
    return curve


@pytest.fixture
def alertness_curve(time_24h):
    """Alertness curve with peak at 60 min, dropping gradually."""
    curve = np.full(len(time_24h), 40.0)  # Baseline alertness
    # Peak alertness around 60-120 min after caffeine
    for i, t in enumerate(time_24h):
        if 30 <= t <= 480:
            # High alertness period
            if t <= 60:
                curve[i] = 40 + 45 * ((t - 30) / 30)
            elif t <= 120:
                curve[i] = 85
            else:
                # Gradual decline
                curve[i] = 85 * np.exp(-0.003 * (t - 120))
    return curve


# =============================================================================
# GLUCOSE METRICS TESTS
# =============================================================================

class TestGlucosePeak:
    """Tests for glucose peak calculation."""
    
    def test_flat_curve_returns_constant_value(self, time_24h, flat_glucose_curve):
        """Flat curve should return the constant value."""
        peak = calculate_glucose_peak(flat_glucose_curve)
        assert peak == 100.0
    
    def test_peak_curve_returns_maximum(self, time_24h, peak_glucose_curve):
        """Peak curve should return approximately 160."""
        peak = calculate_glucose_peak(peak_glucose_curve)
        assert 158 <= peak <= 162  # Allow small tolerance
    
    def test_empty_array_raises_error(self):
        """Empty array should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            calculate_glucose_peak(np.array([]))
    
    def test_returns_float(self, flat_glucose_curve):
        """Result should be a float."""
        peak = calculate_glucose_peak(flat_glucose_curve)
        assert isinstance(peak, (float, np.floating))


class TestGlucoseTimeToPeak:
    """Tests for glucose time-to-peak calculation."""
    
    def test_flat_curve_returns_zero(self, time_24h, flat_glucose_curve):
        """Flat curve should return 0 (first occurrence of max)."""
        time_to_peak = calculate_glucose_time_to_peak(time_24h, flat_glucose_curve)
        assert time_to_peak == 0.0
    
    def test_peak_at_30_minutes(self, time_24h, peak_glucose_curve):
        """Peak should be at approximately 30 minutes."""
        time_to_peak = calculate_glucose_time_to_peak(time_24h, peak_glucose_curve)
        assert 28 <= time_to_peak <= 32
    
    def test_mismatched_lengths_raises_error(self):
        """Mismatched array lengths should raise ValueError."""
        time = np.arange(100)
        glucose = np.arange(50)
        with pytest.raises(ValueError, match="length"):
            calculate_glucose_time_to_peak(time, glucose)


class TestGlucoseAUC:
    """Tests for glucose AUC calculation."""
    
    def test_flat_curve_auc(self, time_24h, flat_glucose_curve):
        """Flat curve AUC = value * duration."""
        auc = calculate_glucose_auc(time_24h, flat_glucose_curve)
        expected = 100.0 * 1440  # 100 mg/dL * 1440 minutes
        assert abs(auc - expected) < 1  # Small tolerance
    
    def test_auc_positive(self, time_24h, peak_glucose_curve):
        """AUC should always be positive."""
        auc = calculate_glucose_auc(time_24h, peak_glucose_curve)
        assert auc > 0
    
    def test_auc_with_baseline_subtraction(self, time_24h, peak_glucose_curve):
        """AUC above baseline should be less than total AUC."""
        total_auc = calculate_glucose_auc(time_24h, peak_glucose_curve)
        auc_above_baseline = calculate_glucose_auc(
            time_24h, peak_glucose_curve, baseline=90.0
        )
        assert auc_above_baseline < total_auc
        assert auc_above_baseline > 0


class TestTimeAboveGlucoseThreshold:
    """Tests for time above glucose threshold."""
    
    def test_flat_below_threshold(self, time_24h, flat_glucose_curve):
        """Curve below threshold should return 0%."""
        pct = calculate_time_above_glucose_threshold(
            time_24h, flat_glucose_curve, threshold=140
        )
        assert pct == 0.0
    
    def test_flat_above_threshold(self, time_24h):
        """Curve always above threshold should return 100%."""
        high_glucose = np.full(len(time_24h), 150.0)
        pct = calculate_time_above_glucose_threshold(
            time_24h, high_glucose, threshold=140
        )
        assert pct == 100.0
    
    def test_peak_curve_partial_time(self, time_24h, peak_glucose_curve):
        """Peak curve should have some time above 140."""
        pct = calculate_time_above_glucose_threshold(
            time_24h, peak_glucose_curve, threshold=140
        )
        assert 0 < pct < 100
    
    def test_returns_percentage(self, time_24h, peak_glucose_curve):
        """Result should be in range [0, 100]."""
        pct = calculate_time_above_glucose_threshold(
            time_24h, peak_glucose_curve, threshold=140
        )
        assert 0 <= pct <= 100


# =============================================================================
# CAFFEINE METRICS TESTS
# =============================================================================

class TestCaffeinePeak:
    """Tests for caffeine peak calculation."""
    
    def test_zero_caffeine(self, time_24h):
        """No caffeine should return 0."""
        zero_curve = np.zeros(len(time_24h))
        peak = calculate_caffeine_peak(zero_curve)
        assert peak == 0.0
    
    def test_100mg_peak(self, caffeine_curve_100mg):
        """100mg dose should give peak around 2 mg/L."""
        peak = calculate_caffeine_peak(caffeine_curve_100mg)
        assert 1.8 <= peak <= 2.2
    
    def test_returns_float(self, caffeine_curve_100mg):
        """Result should be a float."""
        peak = calculate_caffeine_peak(caffeine_curve_100mg)
        assert isinstance(peak, (float, np.floating))


class TestCaffeineHalfLife:
    """Tests for caffeine half-life calculation."""
    
    def test_estimated_half_life(self, time_24h, caffeine_curve_100mg):
        """Half-life should be approximately 5 hours (300 min)."""
        half_life = calculate_caffeine_half_life(time_24h, caffeine_curve_100mg)
        # Allow 20% tolerance
        assert 240 <= half_life <= 360
    
    def test_zero_caffeine_returns_nan(self, time_24h):
        """No caffeine should return NaN (cannot calculate half-life)."""
        zero_curve = np.zeros(len(time_24h))
        half_life = calculate_caffeine_half_life(time_24h, zero_curve)
        assert np.isnan(half_life)
    
    def test_flat_caffeine_returns_inf(self, time_24h):
        """Constant caffeine should return inf (never decays)."""
        flat_curve = np.full(len(time_24h), 2.0)
        half_life = calculate_caffeine_half_life(time_24h, flat_curve)
        assert np.isinf(half_life)


# =============================================================================
# ALERTNESS METRICS TESTS
# =============================================================================

class TestAlertnessPeak:
    """Tests for alertness peak calculation."""
    
    def test_baseline_alertness(self, time_24h):
        """Baseline alertness curve should return baseline value."""
        baseline = np.full(len(time_24h), 50.0)
        peak = calculate_alertness_peak(baseline)
        assert peak == 50.0
    
    def test_caffeine_boosts_alertness(self, alertness_curve):
        """Caffeine should boost alertness above baseline."""
        peak = calculate_alertness_peak(alertness_curve)
        assert peak > 60


class TestAlertnessDurationAboveThreshold:
    """Tests for alertness duration above threshold."""
    
    def test_always_below(self, time_24h):
        """Always below threshold should return 0 minutes."""
        low_alertness = np.full(len(time_24h), 30.0)
        duration = calculate_alertness_duration_above_threshold(
            time_24h, low_alertness, threshold=60
        )
        assert duration == 0.0
    
    def test_always_above(self, time_24h):
        """Always above threshold should return full duration."""
        high_alertness = np.full(len(time_24h), 80.0)
        duration = calculate_alertness_duration_above_threshold(
            time_24h, high_alertness, threshold=60
        )
        # With dt=1 and 1441 points (0 to 1440 inclusive), duration = 1441
        assert duration == float(len(time_24h))
    
    def test_partial_duration(self, time_24h, alertness_curve):
        """Should return partial duration for mixed curve."""
        duration = calculate_alertness_duration_above_threshold(
            time_24h, alertness_curve, threshold=60
        )
        assert 0 < duration < 1440


# =============================================================================
# RISK METRICS TESTS
# =============================================================================

class TestSleepDisruptionRisk:
    """Tests for sleep disruption risk calculation."""
    
    def test_no_caffeine_no_risk(self, time_24h):
        """No caffeine should have 0 risk."""
        zero_caffeine = np.zeros(len(time_24h))
        risk = calculate_sleep_disruption_risk(time_24h, zero_caffeine)
        assert risk == 0.0
    
    def test_high_evening_caffeine_high_risk(self, time_24h):
        """High caffeine at 22:00 should have high risk."""
        # Constant 2 mg/L caffeine
        high_caffeine = np.full(len(time_24h), 2.0)
        risk = calculate_sleep_disruption_risk(time_24h, high_caffeine)
        assert risk > 0.5  # More than 50% risk
    
    def test_low_evening_caffeine_low_risk(self, time_24h):
        """Low caffeine at 22:00 should have low risk."""
        # Caffeine that's nearly cleared by evening
        caffeine = np.zeros(len(time_24h))
        # Only high in the morning, low by evening
        caffeine[:480] = 2.0  # First 8 hours
        caffeine[480:] = 0.3  # After 8 hours, mostly cleared
        risk = calculate_sleep_disruption_risk(time_24h, caffeine)
        assert risk < 0.5
    
    def test_risk_between_0_and_1(self, time_24h, caffeine_curve_100mg):
        """Risk should always be between 0 and 1."""
        risk = calculate_sleep_disruption_risk(time_24h, caffeine_curve_100mg)
        assert 0 <= risk <= 1
    
    def test_risk_at_22h(self, time_24h, caffeine_curve_100mg):
        """Risk should be based on caffeine at 22:00 (1320 min)."""
        # The 100mg morning dose should have minimal caffeine at 22:00
        risk = calculate_sleep_disruption_risk(time_24h, caffeine_curve_100mg)
        # After ~22h, caffeine should be quite low
        assert risk < 0.3


# =============================================================================
# BATCH CALCULATOR TESTS
# =============================================================================

class TestCalculateAllMetrics:
    """Tests for the batch metrics calculator."""
    
    def test_returns_dict(self, time_24h, peak_glucose_curve, caffeine_curve_100mg, alertness_curve):
        """Should return a dictionary of metrics."""
        metrics = calculate_all_metrics(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        assert isinstance(metrics, dict)
    
    def test_contains_all_metrics(self, time_24h, peak_glucose_curve, caffeine_curve_100mg, alertness_curve):
        """Should contain all expected metrics."""
        metrics = calculate_all_metrics(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        
        expected_keys = [
            "glucose_peak",
            "glucose_time_to_peak",
            "glucose_auc",
            "time_above_glucose_140",
            "caffeine_peak",
            "caffeine_half_life",
            "alertness_peak",
            "alertness_duration_above_60",
            "sleep_disruption_risk",
        ]
        
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"
    
    def test_all_values_are_numbers(self, time_24h, peak_glucose_curve, caffeine_curve_100mg, alertness_curve):
        """All metric values should be numbers."""
        metrics = calculate_all_metrics(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        
        for key, value in metrics.items():
            assert isinstance(value, (int, float, np.number)), f"{key} is not a number: {type(value)}"


class TestMetricsCalculator:
    """Tests for the MetricsCalculator class."""
    
    def test_instantiation(self):
        """Should instantiate without error."""
        calc = MetricsCalculator()
        assert calc is not None
    
    def test_calculate_method(self, time_24h, peak_glucose_curve, caffeine_curve_100mg, alertness_curve):
        """Should have a calculate method that returns metrics."""
        calc = MetricsCalculator()
        metrics = calc.calculate(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        assert isinstance(metrics, dict)
        assert "glucose_peak" in metrics


# =============================================================================
# EDGE CASES TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_single_point_array(self):
        """Single point array should work for peak."""
        single = np.array([100.0])
        peak = calculate_glucose_peak(single)
        assert peak == 100.0
    
    def test_nan_in_array_handled(self, time_24h):
        """NaN values should be handled gracefully."""
        curve = np.full(len(time_24h), 100.0)
        curve[100] = np.nan
        # Should still calculate (using nanmax)
        peak = calculate_glucose_peak(curve)
        assert peak == 100.0
    
    def test_inf_in_array_handled(self, time_24h):
        """Inf values should raise ValueError."""
        curve = np.full(len(time_24h), 100.0)
        curve[100] = np.inf
        # Should raise ValueError for infinite values
        with pytest.raises(ValueError, match="infinite"):
            calculate_glucose_peak(curve)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestMetricsIntegration:
    """Integration tests for metrics module."""
    
    def test_realistic_scenario(self, time_24h, peak_glucose_curve, caffeine_curve_100mg, alertness_curve):
        """Test with realistic simulation data."""
        metrics = calculate_all_metrics(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        
        # Validate ranges
        assert 90 <= metrics["glucose_peak"] <= 200
        assert 0 <= metrics["glucose_time_to_peak"] <= 120
        assert metrics["glucose_auc"] > 0
        assert 0 <= metrics["time_above_glucose_140"] <= 100
        assert 0 <= metrics["caffeine_peak"] <= 10
        assert 0 <= metrics["alertness_peak"] <= 100
        assert 0 <= metrics["alertness_duration_above_60"] <= 1440
        assert 0 <= metrics["sleep_disruption_risk"] <= 1
    
    def test_deterministic(self, time_24h, peak_glucose_curve, caffeine_curve_100mg, alertness_curve):
        """Metrics should be deterministic."""
        metrics1 = calculate_all_metrics(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        metrics2 = calculate_all_metrics(
            time_minutes=time_24h,
            glucose_curve=peak_glucose_curve,
            caffeine_curve=caffeine_curve_100mg,
            alertness_curve=alertness_curve,
        )
        
        for key in metrics1:
            if not np.isnan(metrics1[key]):
                assert metrics1[key] == metrics2[key], f"{key} is not deterministic"
