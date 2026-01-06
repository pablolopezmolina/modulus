"""
Golden Scenario 10: Reproducibility / Determinism
=================================================

Purpose:
    Validate that simulations are fully deterministic and reproducible.
    Same inputs must ALWAYS produce identical outputs.

This is critical for:
    - Scientific reproducibility
    - Evidence bundles and audit trails
    - Regression testing
    - Customer confidence (€200k+ products)

Source:
    Internal requirement - Modulus reproducibility guarantee.
"""
import pytest
import numpy as np

from src.core.models.glucose import DallaManModel, GlucoseInput, DallaManParams
from src.core.models.caffeine import EliteCaffeineModel, CaffeineInput, CaffeineParams


class TestGS10_GlucoseReproducibility:
    """Test that glucose simulations are perfectly reproducible."""

    def test_glucose_exact_reproducibility(self):
        """Test that identical inputs produce identical outputs."""
        # Create identical models and inputs
        params = DallaManParams()
        model1 = DallaManModel(params=params)
        model2 = DallaManModel(params=params)
        
        inputs = GlucoseInput(
            carbs_g=75.0,
            duration_minutes=240.0,
            time_step_minutes=1.0,
        )
        
        # Run simulations
        result1 = model1.simulate(inputs)
        result2 = model2.simulate(inputs)
        
        # Time points must be EXACTLY equal
        np.testing.assert_array_equal(
            result1.time_points,
            result2.time_points,
            err_msg="Time points must be exactly equal"
        )
        
        # Glucose curve must be EXACTLY equal
        np.testing.assert_array_equal(
            result1.channels["plasma_glucose"],
            result2.channels["plasma_glucose"],
            err_msg="Glucose curves must be exactly equal"
        )
        
        # Insulin curve must be EXACTLY equal
        np.testing.assert_array_equal(
            result1.channels["plasma_insulin"],
            result2.channels["plasma_insulin"],
            err_msg="Insulin curves must be exactly equal"
        )

    def test_glucose_metrics_reproducibility(self):
        """Test that metrics are exactly reproducible."""
        params = DallaManParams()
        model1 = DallaManModel(params=params)
        model2 = DallaManModel(params=params)
        
        inputs = GlucoseInput(
            carbs_g=50.0,
            duration_minutes=180.0,
            time_step_minutes=1.0,
        )
        
        result1 = model1.simulate(inputs)
        result2 = model2.simulate(inputs)
        
        # All metrics must be exactly equal
        assert result1.metrics == result2.metrics, \
            f"Metrics must be exactly equal.\nRun1: {result1.metrics}\nRun2: {result2.metrics}"

    def test_glucose_multiple_runs(self):
        """Test reproducibility across 5 runs."""
        params = DallaManParams()
        inputs = GlucoseInput(
            carbs_g=60.0,
            duration_minutes=120.0,
            time_step_minutes=1.0,
        )
        
        # Run 5 times
        results = []
        for _ in range(5):
            model = DallaManModel(params=params)
            results.append(model.simulate(inputs))
        
        # All runs must produce identical glucose curves
        reference = results[0].channels["plasma_glucose"]
        for i, result in enumerate(results[1:], start=2):
            np.testing.assert_array_equal(
                reference,
                result.channels["plasma_glucose"],
                err_msg=f"Run {i} produced different results than run 1"
            )


class TestGS10_CaffeineReproducibility:
    """Test that caffeine simulations are perfectly reproducible."""

    def test_caffeine_exact_reproducibility(self):
        """Test that identical inputs produce identical outputs."""
        params = CaffeineParams()
        model1 = EliteCaffeineModel(params=params)
        model2 = EliteCaffeineModel(params=params)
        
        inputs = CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=78.0,
            duration_minutes=480.0,
            time_step_minutes=1.0,
        )
        
        result1 = model1.simulate(inputs)
        result2 = model2.simulate(inputs)
        
        # Time points must be EXACTLY equal
        np.testing.assert_array_equal(
            result1.time_points,
            result2.time_points,
            err_msg="Time points must be exactly equal"
        )
        
        # Caffeine curve must be EXACTLY equal
        np.testing.assert_array_equal(
            result1.channels["plasma_caffeine"],
            result2.channels["plasma_caffeine"],
            err_msg="Caffeine curves must be exactly equal"
        )
        
        # Alertness curve must be EXACTLY equal
        np.testing.assert_array_equal(
            result1.channels["alertness_score"],
            result2.channels["alertness_score"],
            err_msg="Alertness curves must be exactly equal"
        )

    def test_caffeine_metrics_reproducibility(self):
        """Test that caffeine metrics are exactly reproducible."""
        params = CaffeineParams()
        model1 = EliteCaffeineModel(params=params)
        model2 = EliteCaffeineModel(params=params)
        
        inputs = CaffeineInput(
            dose_mg=150.0,
            body_weight_kg=70.0,
            duration_minutes=240.0,
            time_step_minutes=1.0,
        )
        
        result1 = model1.simulate(inputs)
        result2 = model2.simulate(inputs)
        
        # All metrics must be exactly equal
        assert result1.metrics == result2.metrics, \
            f"Metrics must be exactly equal.\nRun1: {result1.metrics}\nRun2: {result2.metrics}"

    def test_caffeine_multiple_runs(self):
        """Test reproducibility across 5 runs."""
        params = CaffeineParams()
        inputs = CaffeineInput(
            dose_mg=200.0,
            body_weight_kg=80.0,
            duration_minutes=360.0,
            time_step_minutes=1.0,
        )
        
        results = []
        for _ in range(5):
            model = EliteCaffeineModel(params=params)
            results.append(model.simulate(inputs))
        
        reference = results[0].channels["plasma_caffeine"]
        for i, result in enumerate(results[1:], start=2):
            np.testing.assert_array_equal(
                reference,
                result.channels["plasma_caffeine"],
                err_msg=f"Run {i} produced different results than run 1"
            )


class TestGS10_DifferentInputsDifferentOutputs:
    """Test that different inputs produce different outputs (sanity check)."""

    def test_different_glucose_doses(self):
        """Test that different carb doses produce different results."""
        params = DallaManParams()
        
        inputs_50 = GlucoseInput(carbs_g=50.0, duration_minutes=240.0, time_step_minutes=1.0)
        inputs_100 = GlucoseInput(carbs_g=100.0, duration_minutes=240.0, time_step_minutes=1.0)
        
        model1 = DallaManModel(params=params)
        model2 = DallaManModel(params=params)
        
        result_50 = model1.simulate(inputs_50)
        result_100 = model2.simulate(inputs_100)
        
        # Peak glucose should be different
        peak_50 = float(np.max(result_50.channels["plasma_glucose"]))
        peak_100 = float(np.max(result_100.channels["plasma_glucose"]))
        
        assert peak_100 > peak_50, \
            "100g carbs should produce higher peak than 50g"

    def test_different_caffeine_doses(self):
        """Test that different caffeine doses produce different results."""
        params = CaffeineParams()
        
        inputs_100 = CaffeineInput(dose_mg=100.0, body_weight_kg=78.0, duration_minutes=240.0, time_step_minutes=1.0)
        inputs_200 = CaffeineInput(dose_mg=200.0, body_weight_kg=78.0, duration_minutes=240.0, time_step_minutes=1.0)
        
        model1 = EliteCaffeineModel(params=params)
        model2 = EliteCaffeineModel(params=params)
        
        result_100 = model1.simulate(inputs_100)
        result_200 = model2.simulate(inputs_200)
        
        # Peak caffeine should be different
        peak_100 = float(np.max(result_100.channels["plasma_caffeine"]))
        peak_200 = float(np.max(result_200.channels["plasma_caffeine"]))
        
        assert peak_200 > peak_100, \
            "200mg caffeine should produce higher peak than 100mg"


class TestGS10_ParameterSensitivity:
    """Test that parameter changes produce expected changes in output."""

    def test_glucose_different_params(self):
        """Test that different Gb produces different baseline."""
        params_normal = DallaManParams(Gb=95.0)
        params_high = DallaManParams(Gb=110.0)
        
        inputs = GlucoseInput(carbs_g=50.0, duration_minutes=240.0, time_step_minutes=1.0)
        
        model_normal = DallaManModel(params=params_normal)
        model_high = DallaManModel(params=params_high)
        
        result_normal = model_normal.simulate(inputs)
        result_high = model_high.simulate(inputs)
        
        # Initial glucose should reflect Gb
        initial_normal = float(result_normal.channels["plasma_glucose"][0])
        initial_high = float(result_high.channels["plasma_glucose"][0])
        
        assert initial_high > initial_normal, \
            "Higher Gb should produce higher initial glucose"

    def test_caffeine_different_params(self):
        """Test that different elimination rate changes half-life."""
        # Higher kel = faster elimination = shorter half-life
        params_slow = CaffeineParams(kel=0.002)  # Slower elimination
        params_fast = CaffeineParams(kel=0.004)  # Faster elimination
        
        inputs = CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=78.0,
            duration_minutes=720.0,  # 12 hours
            time_step_minutes=1.0,
        )
        
        model_slow = EliteCaffeineModel(params=params_slow)
        model_fast = EliteCaffeineModel(params=params_fast)
        
        result_slow = model_slow.simulate(inputs)
        result_fast = model_fast.simulate(inputs)
        
        # At 6 hours (360 min), slow metabolizer should have more caffeine
        caffeine_slow_6h = float(result_slow.channels["plasma_caffeine"][360])
        caffeine_fast_6h = float(result_fast.channels["plasma_caffeine"][360])
        
        assert caffeine_slow_6h > caffeine_fast_6h, \
            "Slow metabolizer should have more caffeine at 6 hours"


class TestGS10_ValidityConsistency:
    """Test that validity flags are consistent across runs."""

    def test_glucose_validity_reproducible(self):
        """Test that validity determination is reproducible."""
        params = DallaManParams()
        inputs = GlucoseInput(carbs_g=75.0, duration_minutes=240.0, time_step_minutes=1.0)
        
        results = []
        for _ in range(3):
            model = DallaManModel(params=params)
            results.append(model.simulate(inputs))
        
        # All should have same validity
        validity = [r.metadata.get("is_sim_valid") for r in results]
        assert len(set(validity)) == 1, \
            f"Validity should be consistent: {validity}"

    def test_caffeine_validity_reproducible(self):
        """Test that validity determination is reproducible."""
        params = CaffeineParams()
        inputs = CaffeineInput(dose_mg=100.0, body_weight_kg=78.0, duration_minutes=240.0, time_step_minutes=1.0)
        
        results = []
        for _ in range(3):
            model = EliteCaffeineModel(params=params)
            results.append(model.simulate(inputs))
        
        validity = [r.metadata.get("is_sim_valid") for r in results]
        assert len(set(validity)) == 1, \
            f"Validity should be consistent: {validity}"
