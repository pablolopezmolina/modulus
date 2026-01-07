"""
Test Suite: DaySimulator (Session 3.1)
Contract: 5.1

Tests for DaySimulator that orchestrates 24h simulation and produces
DaySimulationResult with curves and metrics.
"""

import pytest
import numpy as np
from dataclasses import FrozenInstanceError


# Helper to create a reference person
def get_reference_person():
    """Get a reference VirtualPerson for testing."""
    from src.core.population.person import create_reference_person
    return create_reference_person()


# Helper to create a fasted state
def get_fasted_state(person):
    """Get a fasted PhysiologicalState for testing."""
    from src.core.state import create_fasted_state
    return create_fasted_state(person)


class TestDaySimulationResultContract:
    """Test DaySimulationResult dataclass contract."""
    
    def test_result_has_required_fields(self):
        """DaySimulationResult has all required fields from Contract 5.1."""
        from src.core.simulation import DaySimulationResult
        from src.core.timeline import Timeline
        
        # Create a minimal valid state for testing
        person = get_reference_person()
        state = get_fasted_state(person)
        
        # Create minimal valid result
        result = DaySimulationResult(
            person_id="test_001",
            timeline=Timeline(),
            states=[state],
            time_minutes=np.array([0.0]),
            glucose_curve=np.array([90.0]),
            insulin_curve=np.array([5.0]),
            caffeine_curve=np.array([0.0]),
            alertness_curve=np.array([50.0]),
            metrics={"is_valid": True},
            is_valid=True,
            warnings=[]
        )
        
        # Verify all fields exist
        assert hasattr(result, 'person_id')
        assert hasattr(result, 'timeline')
        assert hasattr(result, 'states')
        assert hasattr(result, 'time_minutes')
        assert hasattr(result, 'glucose_curve')
        assert hasattr(result, 'insulin_curve')
        assert hasattr(result, 'caffeine_curve')
        assert hasattr(result, 'alertness_curve')
        assert hasattr(result, 'metrics')
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'warnings')
    
    def test_result_is_frozen(self):
        """DaySimulationResult should be immutable."""
        from src.core.simulation import DaySimulationResult
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        state = get_fasted_state(person)
        
        result = DaySimulationResult(
            person_id="test_001",
            timeline=Timeline(),
            states=[state],
            time_minutes=np.array([0.0]),
            glucose_curve=np.array([90.0]),
            insulin_curve=np.array([5.0]),
            caffeine_curve=np.array([0.0]),
            alertness_curve=np.array([50.0]),
            metrics={},
            is_valid=True,
            warnings=[]
        )
        
        with pytest.raises(FrozenInstanceError):
            result.person_id = "changed"
    
    def test_curves_are_numpy_arrays(self):
        """All curve fields should be numpy arrays."""
        from src.core.simulation import DaySimulationResult
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        state1 = get_fasted_state(person)
        state2 = state1.with_updates(timestamp_minutes=1.0)
        
        result = DaySimulationResult(
            person_id="test_001",
            timeline=Timeline(),
            states=[state1, state2],
            time_minutes=np.array([0.0, 1.0]),
            glucose_curve=np.array([90.0, 92.0]),
            insulin_curve=np.array([5.0, 8.0]),
            caffeine_curve=np.array([0.0, 0.0]),
            alertness_curve=np.array([50.0, 50.0]),
            metrics={},
            is_valid=True,
            warnings=[]
        )
        
        assert isinstance(result.time_minutes, np.ndarray)
        assert isinstance(result.glucose_curve, np.ndarray)
        assert isinstance(result.insulin_curve, np.ndarray)
        assert isinstance(result.caffeine_curve, np.ndarray)
        assert isinstance(result.alertness_curve, np.ndarray)
    
    def test_curves_same_length_as_time(self):
        """All curves must have same length as time_minutes."""
        from src.core.simulation import DaySimulationResult
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        state1 = get_fasted_state(person)
        state2 = state1.with_updates(timestamp_minutes=1.0)
        state3 = state1.with_updates(timestamp_minutes=2.0)
        
        time = np.array([0.0, 1.0, 2.0])
        result = DaySimulationResult(
            person_id="test_001",
            timeline=Timeline(),
            states=[state1, state2, state3],
            time_minutes=time,
            glucose_curve=np.array([90.0, 92.0, 91.0]),
            insulin_curve=np.array([5.0, 8.0, 7.0]),
            caffeine_curve=np.array([0.0, 0.0, 0.0]),
            alertness_curve=np.array([50.0, 50.0, 50.0]),
            metrics={},
            is_valid=True,
            warnings=[]
        )
        
        assert len(result.glucose_curve) == len(result.time_minutes)
        assert len(result.insulin_curve) == len(result.time_minutes)
        assert len(result.caffeine_curve) == len(result.time_minutes)
        assert len(result.alertness_curve) == len(result.time_minutes)
    
    def test_mismatched_curve_length_raises_error(self):
        """Mismatched curve length should raise ValueError."""
        from src.core.simulation import DaySimulationResult
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        state = get_fasted_state(person)
        
        with pytest.raises(ValueError, match="glucose_curve length"):
            DaySimulationResult(
                person_id="test_001",
                timeline=Timeline(),
                states=[state],
                time_minutes=np.array([0.0]),
                glucose_curve=np.array([90.0, 91.0]),  # Wrong length
                insulin_curve=np.array([5.0]),
                caffeine_curve=np.array([0.0]),
                alertness_curve=np.array([50.0]),
                metrics={},
                is_valid=True,
                warnings=[]
            )


class TestDaySimulatorInit:
    """Test DaySimulator initialization."""
    
    def test_init_with_person(self):
        """DaySimulator can be initialized with a VirtualPerson."""
        from src.core.simulation import DaySimulator
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        assert simulator.person == person
    
    def test_init_stores_person_id(self):
        """DaySimulator stores person_id from person."""
        from src.core.simulation import DaySimulator
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        assert simulator.person.person_id == person.person_id


class TestDaySimulatorSimulate:
    """Test DaySimulator.simulate() method."""
    
    def test_simulate_empty_timeline(self):
        """simulate() with empty timeline returns valid result."""
        from src.core.simulation import DaySimulator, DaySimulationResult
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        timeline = Timeline()
        
        result = simulator.simulate(timeline)
        
        assert isinstance(result, DaySimulationResult)
        assert result.is_valid
        assert result.person_id == person.person_id
    
    def test_simulate_returns_correct_number_of_points_dt1(self):
        """With dt=1.0, returns 1441 points (0 to 1440 inclusive)."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        timeline = Timeline()
        
        result = simulator.simulate(timeline, dt_minutes=1.0)
        
        # 24h = 1440 minutes, +1 for t=0
        assert len(result.time_minutes) == 1441
        assert len(result.glucose_curve) == 1441
        assert len(result.states) == 1441
    
    def test_simulate_returns_correct_number_of_points_dt5(self):
        """With dt=5.0, returns 289 points."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        timeline = Timeline()
        
        result = simulator.simulate(timeline, dt_minutes=5.0)
        
        # 1440 / 5 + 1 = 289
        assert len(result.time_minutes) == 289
        assert len(result.glucose_curve) == 289
    
    def test_simulate_time_starts_at_zero(self):
        """time_minutes starts at 0."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert result.time_minutes[0] == 0.0
    
    def test_simulate_time_ends_at_1440(self):
        """time_minutes ends at 1440."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert result.time_minutes[-1] == 1440.0
    
    def test_simulate_time_monotonically_increasing(self):
        """time_minutes is monotonically increasing."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert np.all(np.diff(result.time_minutes) > 0)
    
    def test_simulate_includes_timeline_in_result(self):
        """Result includes the input timeline."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        event = Event.create_meal(timestamp_minutes=420.0, carbs_g=50.0)
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        assert result.timeline == timeline
    
    def test_simulate_preserves_person_id(self):
        """Result has correct person_id."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert result.person_id == person.person_id


class TestDaySimulatorGlucose:
    """Test glucose response in DaySimulator."""
    
    def test_glucose_baseline_without_meal(self):
        """Without meals, glucose stays near fasting level."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        # Fasting glucose is ~90 mg/dL for reference person
        # Should stay relatively stable
        assert np.all(result.glucose_curve >= 70)
        assert np.all(result.glucose_curve <= 120)
    
    def test_glucose_rises_after_meal(self):
        """Glucose rises after a meal."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        # Breakfast at 7am with 50g carbs
        event = Event.create_meal(
            timestamp_minutes=420.0,  # 7:00 AM
            carbs_g=50.0,
            glycemic_index=70
        )
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        # Find glucose values before and after meal
        idx_before = 400  # ~6:40 AM
        idx_after_peak = 450  # ~7:30 AM (around peak time)
        
        # Glucose should rise after meal
        assert result.glucose_curve[idx_after_peak] > result.glucose_curve[idx_before]
    
    def test_glucose_peak_within_physiological_range(self):
        """Peak glucose is within physiological limits."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        # Large carb load
        event = Event.create_meal(
            timestamp_minutes=420.0,
            carbs_g=75.0,  # OGTT-style load
            glycemic_index=100
        )
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        # Peak should be within healthy range
        peak = np.max(result.glucose_curve)
        assert peak >= 100  # Should rise
        assert peak <= 300  # But not dangerously high


class TestDaySimulatorCaffeine:
    """Test caffeine response in DaySimulator."""
    
    def test_caffeine_zero_without_ingestion(self):
        """Without caffeine ingestion, plasma caffeine stays zero."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert np.all(result.caffeine_curve == 0.0)
    
    def test_caffeine_appears_after_ingestion(self):
        """Caffeine appears in plasma after ingestion."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        # Morning coffee at 7am
        event = Event.create_ingestion(
            timestamp_minutes=420.0,  # 7:00 AM
            compound_id="caffeine",
            amount=100.0,
            unit="mg"
        )
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        # Caffeine should be zero before ingestion
        assert result.caffeine_curve[400] == 0.0
        
        # Caffeine should be present after
        assert result.caffeine_curve[480] > 0.0  # 8:00 AM
    
    def test_caffeine_decays_over_time(self):
        """Caffeine decays over time after peak."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        # Early morning coffee
        event = Event.create_ingestion(
            timestamp_minutes=360.0,  # 6:00 AM
            compound_id="caffeine",
            amount=100.0,
            unit="mg"
        )
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        # Find peak (should be ~30-60 min after ingestion)
        peak_idx = np.argmax(result.caffeine_curve)
        
        # Value at end of day should be less than peak
        assert result.caffeine_curve[-1] < result.caffeine_curve[peak_idx]


class TestDaySimulatorAlertness:
    """Test alertness in DaySimulator."""
    
    def test_alertness_always_in_range(self):
        """Alertness is always between 0 and 100."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        event = Event.create_ingestion(
            timestamp_minutes=420.0,
            compound_id="caffeine",
            amount=200.0,
            unit="mg"
        )
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        assert np.all(result.alertness_curve >= 0)
        assert np.all(result.alertness_curve <= 100)
    
    def test_alertness_increases_with_caffeine(self):
        """Alertness increases with caffeine intake."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        # Baseline without caffeine
        result_no_caffeine = simulator.simulate(Timeline())
        
        # With caffeine
        event = Event.create_ingestion(
            timestamp_minutes=420.0,
            compound_id="caffeine",
            amount=100.0,
            unit="mg"
        )
        timeline = Timeline().add_event(event)
        result_caffeine = simulator.simulate(timeline)
        
        # Peak alertness should be higher with caffeine
        peak_no_caffeine = np.max(result_no_caffeine.alertness_curve)
        peak_caffeine = np.max(result_caffeine.alertness_curve)
        
        assert peak_caffeine > peak_no_caffeine


class TestDaySimulatorMetrics:
    """Test metrics calculation in DaySimulator."""
    
    def test_metrics_contains_is_valid(self):
        """metrics dict contains 'is_valid' key."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert "is_valid" in result.metrics
    
    def test_metrics_contains_glucose_peak(self):
        """metrics dict contains glucose peak."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        event = Event.create_meal(timestamp_minutes=420.0, carbs_g=50.0)
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        assert "glucose_peak" in result.metrics
        assert result.metrics["glucose_peak"] == np.max(result.glucose_curve)
    
    def test_metrics_contains_caffeine_peak(self):
        """metrics dict contains caffeine peak."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        event = Event.create_ingestion(
            timestamp_minutes=420.0,
            compound_id="caffeine",
            amount=100.0,
            unit="mg"
        )
        timeline = Timeline().add_event(event)
        
        result = simulator.simulate(timeline)
        
        assert "caffeine_peak" in result.metrics
        assert result.metrics["caffeine_peak"] == np.max(result.caffeine_curve)
    
    def test_metrics_contains_alertness_peak(self):
        """metrics dict contains alertness peak."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert "alertness_peak" in result.metrics


class TestDaySimulatorWarnings:
    """Test warnings generation in DaySimulator."""
    
    def test_warnings_is_list(self):
        """warnings is always a list."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert isinstance(result.warnings, list)
    
    def test_empty_timeline_no_warnings(self):
        """Empty timeline should not generate warnings."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert len(result.warnings) == 0


class TestDaySimulatorReproducibility:
    """Test reproducibility of DaySimulator."""
    
    def test_same_inputs_same_outputs(self):
        """Same inputs produce exactly same outputs."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline, Event
        
        person = get_reference_person()
        event = Event.create_meal(timestamp_minutes=420.0, carbs_g=50.0)
        timeline = Timeline().add_event(event)
        
        simulator1 = DaySimulator(person=person)
        simulator2 = DaySimulator(person=person)
        
        result1 = simulator1.simulate(timeline)
        result2 = simulator2.simulate(timeline)
        
        # Curves should be exactly equal
        np.testing.assert_array_equal(result1.glucose_curve, result2.glucose_curve)
        np.testing.assert_array_equal(result1.caffeine_curve, result2.caffeine_curve)
        np.testing.assert_array_equal(result1.alertness_curve, result2.alertness_curve)


class TestDaySimulatorStates:
    """Test states list in DaySimulationResult."""
    
    def test_states_are_physiological_states(self):
        """states list contains PhysiologicalState objects."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        from src.core.state import PhysiologicalState
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert len(result.states) > 0
        assert all(isinstance(s, PhysiologicalState) for s in result.states)
    
    def test_states_timestamps_match_time_minutes(self):
        """State timestamps match time_minutes array."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        for i, state in enumerate(result.states):
            assert state.timestamp_minutes == result.time_minutes[i]
    
    def test_curves_extracted_from_states(self):
        """Curves are correctly extracted from states."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        # Glucose curve should match state values
        for i, state in enumerate(result.states):
            assert result.glucose_curve[i] == state.glucose_plasma_mg_dl
            assert result.caffeine_curve[i] == state.caffeine_plasma_mg_l
            assert result.alertness_curve[i] == state.alertness_score


class TestDaySimulatorInsulin:
    """Test insulin curve in DaySimulator."""
    
    def test_insulin_curve_exists(self):
        """Result includes insulin curve."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        assert hasattr(result, 'insulin_curve')
        assert isinstance(result.insulin_curve, np.ndarray)
    
    def test_insulin_matches_states(self):
        """Insulin curve matches state values."""
        from src.core.simulation import DaySimulator
        from src.core.timeline import Timeline
        
        person = get_reference_person()
        simulator = DaySimulator(person=person)
        
        result = simulator.simulate(Timeline())
        
        for i, state in enumerate(result.states):
            assert result.insulin_curve[i] == state.insulin_plasma_mu_l
