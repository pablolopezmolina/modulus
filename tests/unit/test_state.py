"""
MODULUS - PhysiologicalState Unit Tests
Session 2.1: State module with factory methods and helpers

Tests Contract 2.3 compliance plus extensions.
"""

import pytest
import math
from dataclasses import FrozenInstanceError

# Import from state module (will re-export from contracts)
from src.core.state import (
    PhysiologicalState,
    create_fasted_state,
    create_initial_state,
    GLUCOSE_RANGE,
    INSULIN_RANGE,
    CAFFEINE_RANGE,
    ALERTNESS_RANGE,
)
from src.core.population.person import VirtualPerson, create_reference_person


# =============================================================================
# CONTRACT 2.3: Basic PhysiologicalState Tests
# =============================================================================

class TestPhysiologicalStateBasic:
    """Test basic Contract 2.3 compliance."""

    def test_create_valid_state(self):
        """Valid state should be created without errors."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.timestamp_minutes == 0.0
        assert state.glucose_plasma_mg_dl == 90.0
        assert state.is_fasted is True

    def test_immutability(self):
        """PhysiologicalState must be frozen (immutable)."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        with pytest.raises(FrozenInstanceError):
            state.glucose_plasma_mg_dl = 100.0


# =============================================================================
# VALIDATION: Timestamp
# =============================================================================

class TestTimestampValidation:
    """Test timestamp validation per Contract 2.3."""

    def test_timestamp_zero_valid(self):
        """Timestamp 0 is valid (start of day)."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.timestamp_minutes == 0.0

    def test_timestamp_1440_valid(self):
        """Timestamp 1440 is valid (end of 24h)."""
        state = PhysiologicalState(
            timestamp_minutes=1440.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.timestamp_minutes == 1440.0

    def test_timestamp_negative_invalid(self):
        """Negative timestamp should be rejected."""
        with pytest.raises(ValueError, match="timestamp"):
            PhysiologicalState(
                timestamp_minutes=-1.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_timestamp_nan_invalid(self):
        """NaN timestamp should be rejected."""
        with pytest.raises(ValueError):
            PhysiologicalState(
                timestamp_minutes=float('nan'),
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_timestamp_inf_invalid(self):
        """Infinite timestamp should be rejected."""
        with pytest.raises(ValueError):
            PhysiologicalState(
                timestamp_minutes=float('inf'),
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Glucose
# =============================================================================

class TestGlucoseValidation:
    """Test glucose range validation."""

    def test_glucose_normal_range(self):
        """Normal fasting glucose (70-100 mg/dL) should be valid."""
        for glucose in [70.0, 85.0, 100.0]:
            state = PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=glucose,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )
            assert state.glucose_plasma_mg_dl == glucose

    def test_glucose_postprandial_high(self):
        """Postprandial glucose up to 200 mg/dL should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=180.0,
            insulin_plasma_mu_l=50.0,
            glucose_gut_mg=1000.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=False,
            hours_since_last_meal=1.0,
        )
        assert state.glucose_plasma_mg_dl == 180.0

    def test_glucose_too_low_invalid(self):
        """Glucose < 20 mg/dL (severe hypoglycemia) should be rejected."""
        with pytest.raises(ValueError, match="glucose"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=15.0,  # Dangerously low
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_glucose_too_high_invalid(self):
        """Glucose > 600 mg/dL (extreme hyperglycemia) should be rejected."""
        with pytest.raises(ValueError, match="glucose"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=650.0,  # Unrealistic
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_glucose_nan_invalid(self):
        """NaN glucose should be rejected."""
        with pytest.raises(ValueError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=float('nan'),
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Insulin
# =============================================================================

class TestInsulinValidation:
    """Test insulin range validation."""

    def test_insulin_normal_fasting(self):
        """Normal fasting insulin (5-15 mU/L) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=10.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.insulin_plasma_mu_l == 10.0

    def test_insulin_postprandial_high(self):
        """Postprandial insulin up to 200 mU/L should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=150.0,
            insulin_plasma_mu_l=150.0,  # High but possible
            glucose_gut_mg=500.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=False,
            hours_since_last_meal=1.0,
        )
        assert state.insulin_plasma_mu_l == 150.0

    def test_insulin_negative_invalid(self):
        """Negative insulin should be rejected."""
        with pytest.raises(ValueError, match="insulin"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=-5.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_insulin_too_high_invalid(self):
        """Insulin > 1000 mU/L should be rejected."""
        with pytest.raises(ValueError, match="insulin"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=1500.0,  # Unrealistic
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Caffeine
# =============================================================================

class TestCaffeineValidation:
    """Test caffeine range validation."""

    def test_caffeine_zero(self):
        """Zero caffeine should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.caffeine_plasma_mg_l == 0.0

    def test_caffeine_typical_coffee(self):
        """Typical coffee caffeine level (1-3 mg/L) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=2.5,
            adenosine_receptor_occupancy=0.5,
            alertness_score=70.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.caffeine_plasma_mg_l == 2.5

    def test_caffeine_negative_invalid(self):
        """Negative caffeine should be rejected."""
        with pytest.raises(ValueError, match="caffeine"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=-1.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_caffeine_too_high_invalid(self):
        """Caffeine > 100 mg/L (toxic) should be rejected."""
        with pytest.raises(ValueError, match="caffeine"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=150.0,  # Lethal dose
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Adenosine Receptor Occupancy
# =============================================================================

class TestAdenosineOccupancyValidation:
    """Test adenosine receptor occupancy validation (0-1)."""

    def test_occupancy_zero(self):
        """Zero occupancy (no caffeine effect) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.adenosine_receptor_occupancy == 0.0

    def test_occupancy_one(self):
        """Full occupancy (max caffeine effect) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=10.0,
            adenosine_receptor_occupancy=1.0,
            alertness_score=95.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.adenosine_receptor_occupancy == 1.0

    def test_occupancy_negative_invalid(self):
        """Negative occupancy should be rejected."""
        with pytest.raises(ValueError, match="adenosine"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=-0.1,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_occupancy_over_one_invalid(self):
        """Occupancy > 1 should be rejected."""
        with pytest.raises(ValueError, match="adenosine"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=1.5,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Alertness Score
# =============================================================================

class TestAlertnessValidation:
    """Test alertness score validation (0-100)."""

    def test_alertness_zero(self):
        """Zero alertness (fully asleep) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=180.0,  # 3 AM
            glucose_plasma_mg_dl=85.0,
            insulin_plasma_mu_l=5.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=0.0,
            is_fasted=True,
            hours_since_last_meal=10.0,
        )
        assert state.alertness_score == 0.0

    def test_alertness_hundred(self):
        """Full alertness (100%) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=600.0,  # 10 AM
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=3.0,
            adenosine_receptor_occupancy=0.6,
            alertness_score=100.0,
            is_fasted=False,
            hours_since_last_meal=2.0,
        )
        assert state.alertness_score == 100.0

    def test_alertness_negative_invalid(self):
        """Negative alertness should be rejected."""
        with pytest.raises(ValueError, match="alertness"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=-10.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )

    def test_alertness_over_hundred_invalid(self):
        """Alertness > 100 should be rejected."""
        with pytest.raises(ValueError, match="alertness"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=110.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Glucose Gut (pending absorption)
# =============================================================================

class TestGlucoseGutValidation:
    """Test glucose_gut_mg validation."""

    def test_glucose_gut_zero(self):
        """Zero glucose in gut (fasted) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.glucose_gut_mg == 0.0

    def test_glucose_gut_after_meal(self):
        """Glucose in gut after meal should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=30.0,
            glucose_plasma_mg_dl=120.0,
            insulin_plasma_mu_l=30.0,
            glucose_gut_mg=50000.0,  # 50g remaining
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=False,
            hours_since_last_meal=0.5,
        )
        assert state.glucose_gut_mg == 50000.0

    def test_glucose_gut_negative_invalid(self):
        """Negative glucose in gut should be rejected."""
        with pytest.raises(ValueError, match="glucose_gut"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=-100.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0,
            )


# =============================================================================
# VALIDATION: Hours Since Last Meal
# =============================================================================

class TestHoursSinceLastMealValidation:
    """Test hours_since_last_meal validation."""

    def test_hours_zero(self):
        """Zero hours (just ate) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=720.0,  # Noon
            glucose_plasma_mg_dl=150.0,
            insulin_plasma_mu_l=50.0,
            glucose_gut_mg=30000.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=60.0,
            is_fasted=False,
            hours_since_last_meal=0.0,
        )
        assert state.hours_since_last_meal == 0.0

    def test_hours_overnight(self):
        """Overnight fast (8-12 hours) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=420.0,  # 7 AM
            glucose_plasma_mg_dl=85.0,
            insulin_plasma_mu_l=5.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=40.0,
            is_fasted=True,
            hours_since_last_meal=10.0,
        )
        assert state.hours_since_last_meal == 10.0

    def test_hours_negative_invalid(self):
        """Negative hours should be rejected."""
        with pytest.raises(ValueError, match="hours_since"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=-2.0,
            )


# =============================================================================
# FACTORY METHODS
# =============================================================================

class TestCreateFastedState:
    """Test create_fasted_state factory method."""

    def test_create_fasted_state_basic(self):
        """Create fasted state with reference person."""
        person = create_reference_person()
        state = create_fasted_state(person)
        
        assert state.timestamp_minutes == 0.0
        assert state.is_fasted is True
        assert state.hours_since_last_meal == 8.0  # Default overnight fast
        assert state.glucose_gut_mg == 0.0  # No food pending
        assert state.caffeine_plasma_mg_l == 0.0  # No caffeine

    def test_create_fasted_state_uses_person_glucose(self):
        """Fasted state uses person's fasting glucose."""
        person = create_reference_person()
        state = create_fasted_state(person)
        
        # Should use person's fasting glucose
        assert state.glucose_plasma_mg_dl == person.fasting_glucose_mg_dl

    def test_create_fasted_state_uses_person_insulin(self):
        """Fasted state uses person's fasting insulin."""
        person = create_reference_person()
        state = create_fasted_state(person)
        
        # Should use person's fasting insulin
        assert state.insulin_plasma_mu_l == person.fasting_insulin_mu_l

    def test_create_fasted_state_custom_timestamp(self):
        """Create fasted state at specific timestamp."""
        person = create_reference_person()
        state = create_fasted_state(person, timestamp_minutes=420.0)  # 7 AM
        
        assert state.timestamp_minutes == 420.0
        assert state.is_fasted is True

    def test_create_fasted_state_custom_hours(self):
        """Create fasted state with custom fasting hours."""
        person = create_reference_person()
        state = create_fasted_state(person, hours_since_last_meal=12.0)
        
        assert state.hours_since_last_meal == 12.0
        assert state.is_fasted is True


class TestCreateInitialState:
    """Test create_initial_state factory method."""

    def test_create_initial_state_defaults(self):
        """Create initial state with sane defaults."""
        person = create_reference_person()
        state = create_initial_state(person)
        
        assert state.timestamp_minutes == 0.0
        assert state.glucose_plasma_mg_dl == person.fasting_glucose_mg_dl
        assert state.insulin_plasma_mu_l == person.fasting_insulin_mu_l

    def test_create_initial_state_with_caffeine(self):
        """Create initial state with habitual caffeine user baseline."""
        person = create_reference_person()
        state = create_initial_state(person, include_baseline_caffeine=True)
        
        # If person has habitual caffeine intake, might start with some
        # For now, baseline is 0 unless explicitly modeled
        assert state.caffeine_plasma_mg_l >= 0.0


# =============================================================================
# WITH_UPDATES METHOD
# =============================================================================

class TestWithUpdates:
    """Test with_updates() method for creating modified states."""

    def test_with_updates_single_field(self):
        """Update single field creates new state."""
        state1 = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        
        state2 = state1.with_updates(glucose_plasma_mg_dl=120.0)
        
        # Original unchanged
        assert state1.glucose_plasma_mg_dl == 90.0
        # New state has update
        assert state2.glucose_plasma_mg_dl == 120.0
        # Other fields unchanged
        assert state2.timestamp_minutes == state1.timestamp_minutes
        assert state2.insulin_plasma_mu_l == state1.insulin_plasma_mu_l

    def test_with_updates_multiple_fields(self):
        """Update multiple fields at once."""
        state1 = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        
        state2 = state1.with_updates(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=150.0,
            insulin_plasma_mu_l=50.0,
            is_fasted=False,
            hours_since_last_meal=1.0,
        )
        
        assert state2.timestamp_minutes == 60.0
        assert state2.glucose_plasma_mg_dl == 150.0
        assert state2.insulin_plasma_mu_l == 50.0
        assert state2.is_fasted is False
        assert state2.hours_since_last_meal == 1.0

    def test_with_updates_validates(self):
        """with_updates validates the new state."""
        state1 = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        
        with pytest.raises(ValueError, match="glucose"):
            state1.with_updates(glucose_plasma_mg_dl=-10.0)

    def test_with_updates_returns_new_instance(self):
        """with_updates always returns a new instance."""
        state1 = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        
        state2 = state1.with_updates()  # No changes
        
        assert state1 is not state2
        assert state1 == state2  # Equal content


# =============================================================================
# COMPUTED PROPERTIES
# =============================================================================

class TestComputedProperties:
    """Test computed properties of PhysiologicalState."""

    def test_time_hours(self):
        """time_hours property converts minutes to hours."""
        state = PhysiologicalState(
            timestamp_minutes=150.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.time_hours == 2.5

    def test_is_hypoglycemic(self):
        """is_hypoglycemic returns True when glucose < 70."""
        low_glucose = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=55.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert low_glucose.is_hypoglycemic is True
        
        normal_glucose = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert normal_glucose.is_hypoglycemic is False

    def test_is_hyperglycemic(self):
        """is_hyperglycemic returns True when glucose > 140."""
        high_glucose = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=180.0,
            insulin_plasma_mu_l=50.0,
            glucose_gut_mg=1000.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=False,
            hours_since_last_meal=1.0,
        )
        assert high_glucose.is_hyperglycemic is True
        
        normal_glucose = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert normal_glucose.is_hyperglycemic is False

    def test_has_caffeine(self):
        """has_caffeine returns True when caffeine > 0.1 mg/L."""
        with_caffeine = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=2.0,
            adenosine_receptor_occupancy=0.4,
            alertness_score=70.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert with_caffeine.has_caffeine is True
        
        no_caffeine = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert no_caffeine.has_caffeine is False


# =============================================================================
# SERIALIZATION
# =============================================================================

class TestSerialization:
    """Test state serialization for reproducibility."""

    def test_to_dict(self):
        """State can be converted to dict."""
        state = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=120.0,
            insulin_plasma_mu_l=30.0,
            glucose_gut_mg=5000.0,
            caffeine_plasma_mg_l=1.5,
            adenosine_receptor_occupancy=0.3,
            alertness_score=65.0,
            is_fasted=False,
            hours_since_last_meal=1.0,
        )
        
        d = state.to_dict()
        
        assert d["timestamp_minutes"] == 60.0
        assert d["glucose_plasma_mg_dl"] == 120.0
        assert d["is_fasted"] is False

    def test_from_dict(self):
        """State can be created from dict."""
        d = {
            "timestamp_minutes": 60.0,
            "glucose_plasma_mg_dl": 120.0,
            "insulin_plasma_mu_l": 30.0,
            "glucose_gut_mg": 5000.0,
            "caffeine_plasma_mg_l": 1.5,
            "adenosine_receptor_occupancy": 0.3,
            "alertness_score": 65.0,
            "is_fasted": False,
            "hours_since_last_meal": 1.0,
        }
        
        state = PhysiologicalState.from_dict(d)
        
        assert state.timestamp_minutes == 60.0
        assert state.glucose_plasma_mg_dl == 120.0

    def test_roundtrip(self):
        """to_dict -> from_dict produces equal state."""
        state1 = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=120.0,
            insulin_plasma_mu_l=30.0,
            glucose_gut_mg=5000.0,
            caffeine_plasma_mg_l=1.5,
            adenosine_receptor_occupancy=0.3,
            alertness_score=65.0,
            is_fasted=False,
            hours_since_last_meal=1.0,
        )
        
        state2 = PhysiologicalState.from_dict(state1.to_dict())
        
        assert state1 == state2


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_boundary_glucose_min(self):
        """Glucose at minimum boundary (20) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=20.0,  # Boundary
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.glucose_plasma_mg_dl == 20.0

    def test_boundary_glucose_max(self):
        """Glucose at maximum boundary (600) should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=600.0,  # Boundary
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.glucose_plasma_mg_dl == 600.0

    def test_all_zeros_caffeine_system(self):
        """All zeros in caffeine system should be valid."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=0.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        assert state.caffeine_plasma_mg_l == 0.0
        assert state.alertness_score == 0.0

    def test_equality(self):
        """Two states with same values should be equal."""
        state1 = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        state2 = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        
        assert state1 == state2

    def test_hashable(self):
        """PhysiologicalState should be hashable (for use in sets/dicts)."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0,
        )
        
        # Should not raise
        hash_value = hash(state)
        assert isinstance(hash_value, int)
        
        # Should work in set
        s = {state}
        assert state in s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
