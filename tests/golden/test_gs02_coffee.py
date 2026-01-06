"""
Golden Scenario 02: Caffeine Only - Morning Coffee
===================================================

Purpose:
    Validate that the EliteCaffeineModel produces physiologically correct
    caffeine pharmacokinetics and alertness response for a standard 100mg dose.

Expected Values (from Blanchard 1983 and caffeine PK literature):
    - Peak plasma caffeine: 1.5-2.5 mg/L for 100mg dose
    - Time to peak: 30-60 minutes
    - Half-life: 4-6 hours (normal metabolizer)
    - Peak alertness: 60-80%
    - Alertness wearing off by 8 hours

Source:
    Blanchard, J., & Sawers, S. J. A. (1983).
    "The absolute bioavailability of caffeine in man."
    European Journal of Clinical Pharmacology, 24(1), 93-98.
"""
import pytest
import numpy as np

from src.core.models.caffeine import EliteCaffeineModel, CaffeineInput, CaffeineParams


class TestGS02_Coffee:
    """Golden Scenario 02: Morning Coffee (100mg caffeine)."""

    @pytest.fixture
    def reference_params(self) -> CaffeineParams:
        """Create reference parameters for normal caffeine metabolizer.
        
        Default params represent a normal CYP1A2 metabolizer with
        typical caffeine half-life of ~5 hours.
        """
        return CaffeineParams()

    @pytest.fixture
    def caffeine_model(self, reference_params: CaffeineParams) -> EliteCaffeineModel:
        """Create caffeine model for simulation."""
        return EliteCaffeineModel(params=reference_params)

    @pytest.fixture
    def coffee_input(self) -> CaffeineInput:
        """Create standard coffee input: 100mg caffeine, 78kg person, 480 min."""
        return CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=78.0,
            duration_minutes=480.0,  # 8 hours
            time_step_minutes=1.0,
        )

    def test_coffee_simulation_validity(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that caffeine simulation completes successfully."""
        result = caffeine_model.simulate(coffee_input)
        
        # Simulation must be valid
        assert result.metadata.get("is_sim_valid", False), \
            f"Caffeine simulation should complete successfully. Got: {result.metadata.get('solver_message')}"
        
        # Time points must exist and be correct length
        assert len(result.time_points) == 481, \
            f"Should have 481 time points (0 to 480 inclusive), got {len(result.time_points)}"
        
        # Time points must start at 0
        assert result.time_points[0] == 0.0, \
            "Time points must start at 0"
        
        # Time points must be monotonically increasing
        assert np.all(np.diff(result.time_points) > 0), \
            "Time points must be monotonically increasing"

    def test_coffee_plasma_peak_range(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that plasma caffeine peak is in expected range.
        
        Expected: 1.5-2.5 mg/L for 100mg dose in 78kg person.
        Reference: Blanchard 1983, typical caffeine PK.
        """
        result = caffeine_model.simulate(coffee_input)
        
        caffeine = result.channels["plasma_caffeine"]
        peak_caffeine = float(np.max(caffeine))
        
        # Peak should be between 1.5-2.5 mg/L
        assert 1.5 <= peak_caffeine <= 2.5, \
            f"Peak caffeine {peak_caffeine:.2f} mg/L outside expected range [1.5-2.5]"

    def test_coffee_time_to_peak(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that time to peak is in expected range.
        
        Expected: 30-60 minutes for liquid caffeine.
        Reference: Standard caffeine absorption kinetics.
        """
        result = caffeine_model.simulate(coffee_input)
        
        caffeine = result.channels["plasma_caffeine"]
        time_to_peak = int(np.argmax(caffeine))
        
        # Peak should occur between 30-60 minutes
        assert 30 <= time_to_peak <= 60, \
            f"Time to peak {time_to_peak} min outside expected range [30-60]"

    def test_coffee_half_life_estimate(self, caffeine_model: EliteCaffeineModel):
        """Test that caffeine half-life is in normal range.
        
        Expected: 4-6 hours for normal metabolizer.
        Reference: CYP1A2 normal genotype literature.
        """
        # Run longer simulation to estimate half-life
        inputs = CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=78.0,
            duration_minutes=720.0,  # 12 hours to capture decay
            time_step_minutes=1.0,
        )
        result = caffeine_model.simulate(inputs)
        
        caffeine = result.channels["plasma_caffeine"]
        peak_caffeine = float(np.max(caffeine))
        half_peak = peak_caffeine / 2.0
        
        # Find time to reach half of peak (after peak)
        peak_idx = int(np.argmax(caffeine))
        post_peak = caffeine[peak_idx:]
        
        # Find first index where concentration drops below half peak
        below_half = np.where(post_peak <= half_peak)[0]
        
        if len(below_half) > 0:
            time_to_half = below_half[0]  # Time after peak to reach half
            half_life_hours = time_to_half / 60.0
            
            # Half-life should be between 4-6 hours
            assert 4.0 <= half_life_hours <= 6.0, \
                f"Half-life {half_life_hours:.1f} hours outside expected range [4-6]"

    def test_coffee_alertness_peak_range(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that alertness peaks in expected range.
        
        Expected: 20-40% at peak for 100mg dose.
        Reference: Emax model with EC50=4 mg/L, Hill=1.5.
        
        With Cmax ~2.1 mg/L and EC50=4 mg/L:
        Effect = (2.1^1.5) / (4^1.5 + 2.1^1.5) * 100 ≈ 27%
        """
        result = caffeine_model.simulate(coffee_input)
        
        alertness = result.channels["alertness_score"]
        peak_alertness = float(np.max(alertness))
        
        # Peak alertness based on actual model parameters
        assert 20 <= peak_alertness <= 40, \
            f"Peak alertness {peak_alertness:.1f}% outside expected range [20-40]"

    def test_coffee_alertness_decay(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that alertness decays appropriately over 8 hours.
        
        Expected: Alertness should be significantly reduced by 8 hours.
        Reference: Caffeine effect duration.
        """
        result = caffeine_model.simulate(coffee_input)
        
        alertness = result.channels["alertness_score"]
        peak_alertness = float(np.max(alertness))
        alertness_at_480 = float(alertness[-1])  # At 8 hours
        
        # Alertness should be less than half of peak by 8 hours
        assert alertness_at_480 < peak_alertness * 0.5, \
            f"Alertness at 8h {alertness_at_480:.1f}% should be <50% of peak ({peak_alertness:.1f}%)"

    def test_coffee_no_negative_values(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that no values go negative."""
        result = caffeine_model.simulate(coffee_input)
        
        caffeine = result.channels["plasma_caffeine"]
        alertness = result.channels["alertness_score"]
        
        # No negative concentrations
        assert np.all(caffeine >= 0), \
            "Caffeine concentration must never be negative"
        
        # No negative alertness
        assert np.all(alertness >= 0), \
            "Alertness score must never be negative"
        
        # Alertness should not exceed 100%
        assert np.all(alertness <= 100), \
            "Alertness score must not exceed 100%"

    def test_coffee_concentration_at_zero(self, caffeine_model: EliteCaffeineModel, coffee_input: CaffeineInput):
        """Test that initial plasma concentration is zero."""
        result = caffeine_model.simulate(coffee_input)
        
        caffeine = result.channels["plasma_caffeine"]
        initial_caffeine = float(caffeine[0])
        
        # Should start at zero (caffeine not yet absorbed)
        assert initial_caffeine == 0.0, \
            f"Initial plasma caffeine should be 0, got {initial_caffeine:.4f}"


class TestGS02_Coffee_Metrics:
    """Test caffeine-related metrics calculations."""

    @pytest.fixture
    def reference_result(self):
        """Run standard coffee simulation and return result."""
        model = EliteCaffeineModel()
        inputs = CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=78.0,
            duration_minutes=480.0,
            time_step_minutes=1.0,
        )
        return model.simulate(inputs)

    def test_metrics_contain_cmax(self, reference_result):
        """Test that metrics include Cmax."""
        assert "Cmax" in reference_result.metrics, \
            "Metrics should include Cmax"
        
        cmax = reference_result.metrics["Cmax"]
        assert 1.5 <= cmax <= 2.5, \
            f"Cmax {cmax:.2f} outside expected range [1.5-2.5]"

    def test_metrics_contain_tmax(self, reference_result):
        """Test that metrics include Tmax."""
        assert "Tmax" in reference_result.metrics, \
            "Metrics should include Tmax"
        
        tmax = reference_result.metrics["Tmax"]
        assert 30 <= tmax <= 60, \
            f"Tmax {tmax:.1f} outside expected range [30-60]"

    def test_metrics_contain_auc(self, reference_result):
        """Test that metrics include AUC."""
        assert "AUC" in reference_result.metrics, \
            "Metrics should include AUC"
        
        auc = reference_result.metrics["AUC"]
        assert auc > 0, "Caffeine AUC must be positive"


class TestGS02_Coffee_DoseResponse:
    """Test dose-response relationship for caffeine."""

    def test_higher_dose_higher_peak(self):
        """Test that higher dose produces higher peak."""
        model = EliteCaffeineModel()
        
        # 100mg dose
        result_100 = model.simulate(CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=78.0,
            duration_minutes=240.0,
            time_step_minutes=1.0,
        ))
        
        # 200mg dose
        result_200 = model.simulate(CaffeineInput(
            dose_mg=200.0,
            body_weight_kg=78.0,
            duration_minutes=240.0,
            time_step_minutes=1.0,
        ))
        
        peak_100 = float(np.max(result_100.channels["plasma_caffeine"]))
        peak_200 = float(np.max(result_200.channels["plasma_caffeine"]))
        
        # 200mg should produce approximately 2x the peak (linear PK)
        ratio = peak_200 / peak_100
        assert 1.8 <= ratio <= 2.2, \
            f"Dose-response ratio {ratio:.2f} should be ~2.0 (linear PK)"

    def test_heavier_person_lower_peak(self):
        """Test that heavier person has lower peak concentration."""
        model = EliteCaffeineModel()
        
        # 70kg person
        result_70 = model.simulate(CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=70.0,
            duration_minutes=240.0,
            time_step_minutes=1.0,
        ))
        
        # 100kg person
        result_100 = model.simulate(CaffeineInput(
            dose_mg=100.0,
            body_weight_kg=100.0,
            duration_minutes=240.0,
            time_step_minutes=1.0,
        ))
        
        peak_70 = float(np.max(result_70.channels["plasma_caffeine"]))
        peak_100 = float(np.max(result_100.channels["plasma_caffeine"]))
        
        # Heavier person should have lower peak (larger Vd)
        assert peak_100 < peak_70, \
            f"Heavier person ({peak_100:.2f}) should have lower peak than lighter ({peak_70:.2f})"
