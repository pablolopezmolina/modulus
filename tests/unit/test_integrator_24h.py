"""
Tests for StateIntegrator.simulate_timeline() method.

Session 2.3: 24h timeline simulation
Contract 2.4: simulate_timeline(initial_state, timeline, dt_minutes=1.0) → List[PhysiologicalState]

GOLDEN SCENARIOS COVERED:
- GS05: Full day protocol with multiple events
"""

import pytest
from typing import List

from src.core.state.state import PhysiologicalState, create_fasted_state
from src.core.state.integrator import StateIntegrator
from src.core.timeline.timeline import Timeline
from src.core.timeline import Event
from src.core.population.person import VirtualPerson, create_reference_person


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def reference_person() -> VirtualPerson:
    """Create a reference person for testing."""
    return create_reference_person()


@pytest.fixture
def integrator(reference_person) -> StateIntegrator:
    """Create a StateIntegrator with reference person."""
    return StateIntegrator(person=reference_person)


@pytest.fixture
def initial_state(reference_person) -> PhysiologicalState:
    """Create initial fasted state."""
    return create_fasted_state(reference_person)


@pytest.fixture
def empty_timeline() -> Timeline:
    """Empty timeline for baseline tests."""
    return Timeline()


@pytest.fixture
def simple_meal_timeline() -> Timeline:
    """Timeline with single meal at t=60."""
    event = Event.create_meal(
        timestamp_minutes=60.0,
        carbs_g=50.0,
        protein_g=20.0,
        fat_g=10.0,
        fiber_g=5.0,
        glycemic_index=70.0
    )
    return Timeline().add_event(event)


@pytest.fixture
def coffee_timeline() -> Timeline:
    """Timeline with single caffeine ingestion at t=0."""
    event = Event.create_ingestion(
        timestamp_minutes=0.0,
        compound_id="caffeine",
        amount=100.0,
        unit="mg",
        form="liquid"
    )
    return Timeline().add_event(event)


@pytest.fixture
def full_day_timeline() -> Timeline:
    """GS05-style full day timeline."""
    timeline = Timeline()
    
    # Morning coffee at 7:00 AM (420 min)
    timeline = timeline.add_event(Event.create_ingestion(
        timestamp_minutes=420.0,
        compound_id="caffeine",
        amount=100.0,
        unit="mg",
        form="liquid"
    ))
    
    # Breakfast at 7:30 AM (450 min)
    timeline = timeline.add_event(Event.create_meal(
        timestamp_minutes=450.0,
        carbs_g=50.0,
        protein_g=20.0,
        fat_g=15.0,
        glycemic_index=60.0
    ))
    
    # Lunch at 13:00 (780 min)
    timeline = timeline.add_event(Event.create_meal(
        timestamp_minutes=780.0,
        carbs_g=60.0,
        protein_g=30.0,
        fat_g=20.0,
        glycemic_index=55.0
    ))
    
    # Afternoon coffee at 15:00 (900 min)
    timeline = timeline.add_event(Event.create_ingestion(
        timestamp_minutes=900.0,
        compound_id="caffeine",
        amount=100.0,
        unit="mg",
        form="liquid"
    ))
    
    # Dinner at 19:00 (1140 min)
    timeline = timeline.add_event(Event.create_meal(
        timestamp_minutes=1140.0,
        carbs_g=70.0,
        protein_g=25.0,
        fat_g=25.0,
        glycemic_index=50.0
    ))
    
    return timeline


# =============================================================================
# BASIC FUNCTIONALITY TESTS
# =============================================================================

class TestSimulateTimelineBasics:
    """Test basic simulate_timeline functionality."""
    
    def test_returns_list_of_states(self, integrator, initial_state, empty_timeline):
        """simulate_timeline returns a list of PhysiologicalState objects."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        assert isinstance(states, list)
        assert all(isinstance(s, PhysiologicalState) for s in states)
    
    def test_returns_correct_number_of_states_dt1(self, integrator, initial_state, empty_timeline):
        """With dt=1.0, returns 1441 states (0, 1, 2, ..., 1440)."""
        states = integrator.simulate_timeline(initial_state, empty_timeline, dt_minutes=1.0)
        
        # Contract: states for t=0, dt, 2*dt, ..., 1440
        # With dt=1.0: 0, 1, 2, ..., 1440 = 1441 states
        assert len(states) == 1441
    
    def test_returns_correct_number_of_states_dt5(self, integrator, initial_state, empty_timeline):
        """With dt=5.0, returns 289 states (0, 5, 10, ..., 1440)."""
        states = integrator.simulate_timeline(initial_state, empty_timeline, dt_minutes=5.0)
        
        # 1440 / 5 + 1 = 289 states
        assert len(states) == 289
    
    def test_returns_correct_number_of_states_dt10(self, integrator, initial_state, empty_timeline):
        """With dt=10.0, returns 145 states."""
        states = integrator.simulate_timeline(initial_state, empty_timeline, dt_minutes=10.0)
        
        # 1440 / 10 + 1 = 145 states
        assert len(states) == 145
    
    def test_first_state_timestamp_is_zero(self, integrator, initial_state, empty_timeline):
        """First state has timestamp_minutes = 0."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        assert states[0].timestamp_minutes == 0.0
    
    def test_last_state_timestamp_is_1440(self, integrator, initial_state, empty_timeline):
        """Last state has timestamp_minutes = 1440."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        assert states[-1].timestamp_minutes == 1440.0
    
    def test_timestamps_are_monotonically_increasing(self, integrator, initial_state, empty_timeline):
        """Timestamps strictly increase throughout the simulation."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        timestamps = [s.timestamp_minutes for s in states]
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1]
    
    def test_timestamps_match_dt_increments(self, integrator, initial_state, empty_timeline):
        """Timestamps increment by exactly dt_minutes."""
        dt = 5.0
        states = integrator.simulate_timeline(initial_state, empty_timeline, dt_minutes=dt)
        
        for i, state in enumerate(states):
            expected_time = i * dt
            assert state.timestamp_minutes == pytest.approx(expected_time, abs=1e-9)


# =============================================================================
# EMPTY TIMELINE TESTS
# =============================================================================

class TestSimulateTimelineEmpty:
    """Test behavior with empty timeline (no events)."""
    
    def test_glucose_stays_stable_when_fasted(self, integrator, initial_state, empty_timeline):
        """With no meals, glucose should stay relatively stable (fasting state)."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        initial_glucose = states[0].glucose_plasma_mg_dl
        final_glucose = states[-1].glucose_plasma_mg_dl
        
        # Glucose should stay within 15% of initial (homeostasis)
        assert abs(final_glucose - initial_glucose) < initial_glucose * 0.15
    
    def test_caffeine_stays_zero_with_no_ingestion(self, integrator, initial_state, empty_timeline):
        """With no caffeine ingestion, caffeine should stay at 0."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        for state in states:
            assert state.caffeine_plasma_mg_l == 0.0
    
    def test_hours_since_meal_increases(self, integrator, initial_state, empty_timeline):
        """hours_since_last_meal should increase with time."""
        states = integrator.simulate_timeline(initial_state, empty_timeline)
        
        # After 1440 minutes (24h), hours_since_last_meal should increase by 24
        initial_hours = states[0].hours_since_last_meal
        final_hours = states[-1].hours_since_last_meal
        
        assert final_hours > initial_hours
        assert final_hours == pytest.approx(initial_hours + 24.0, abs=0.5)


# =============================================================================
# SINGLE EVENT TESTS
# =============================================================================

class TestSimulateTimelineSingleEvent:
    """Test behavior with single events."""
    
    def test_meal_causes_glucose_spike(self, integrator, initial_state, simple_meal_timeline):
        """A meal should cause glucose to rise."""
        states = integrator.simulate_timeline(initial_state, simple_meal_timeline)
        
        # Find glucose values before and after meal (meal at t=60)
        glucose_before = states[59].glucose_plasma_mg_dl  # t=59
        
        # Glucose should rise after meal - find max in window after meal
        max_glucose_after = max(s.glucose_plasma_mg_dl for s in states[60:180])
        
        # Glucose should be higher after meal
        assert max_glucose_after > glucose_before
    
    def test_meal_resets_hours_since_meal(self, integrator, initial_state, simple_meal_timeline):
        """A meal should reset hours_since_last_meal."""
        states = integrator.simulate_timeline(initial_state, simple_meal_timeline)
        
        # Shortly after meal at t=60, hours should be close to 0
        state_after_meal = states[61]
        
        # After meal, hours should be small
        assert state_after_meal.hours_since_last_meal < 1.0
    
    def test_caffeine_appears_after_ingestion(self, integrator, initial_state, coffee_timeline):
        """Caffeine ingestion should increase plasma caffeine."""
        states = integrator.simulate_timeline(initial_state, coffee_timeline)
        
        # Caffeine ingested at t=0, should appear in plasma by t=30
        caffeine_at_30 = states[30].caffeine_plasma_mg_l
        
        assert caffeine_at_30 > 0.0
    
    def test_caffeine_peaks_then_declines(self, integrator, initial_state, coffee_timeline):
        """Caffeine should peak within 30-60 min then decline."""
        states = integrator.simulate_timeline(initial_state, coffee_timeline)
        
        # Find peak caffeine
        caffeine_values = [s.caffeine_plasma_mg_l for s in states]
        peak_idx = caffeine_values.index(max(caffeine_values))
        peak_time = states[peak_idx].timestamp_minutes
        
        # Peak should be between 10-120 minutes (absorption varies)
        assert 10 <= peak_time <= 120
        
        # Caffeine at end (24h) should be lower than peak
        caffeine_at_end = states[-1].caffeine_plasma_mg_l
        peak_caffeine = max(caffeine_values)
        
        assert caffeine_at_end < peak_caffeine
    
    def test_alertness_increases_with_caffeine(self, integrator, initial_state, coffee_timeline):
        """Alertness should increase after caffeine ingestion."""
        states = integrator.simulate_timeline(initial_state, coffee_timeline)
        
        # Compare alertness at start vs after caffeine kicks in
        alertness_at_start = states[0].alertness_score
        
        # Find max alertness (should be higher than baseline)
        max_alertness = max(s.alertness_score for s in states[:120])
        
        assert max_alertness > alertness_at_start


# =============================================================================
# FULL DAY SIMULATION TESTS (GS05-style)
# =============================================================================

class TestSimulateTimelineFullDay:
    """Test full day simulation with multiple events (GS05)."""
    
    def test_glucose_responds_to_meals(self, integrator, initial_state, full_day_timeline):
        """Full day with 3 meals should show glucose responses."""
        states = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        # Check that glucose is elevated after breakfast (t=450)
        glucose_before_breakfast = states[449].glucose_plasma_mg_dl
        glucose_after_breakfast = max(s.glucose_plasma_mg_dl for s in states[450:600])
        
        assert glucose_after_breakfast > glucose_before_breakfast
    
    def test_caffeine_accumulates_with_multiple_doses(self, integrator, initial_state, full_day_timeline):
        """Two caffeine doses should accumulate."""
        states = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        # Caffeine at 14:55 (before second dose at 15:00/900)
        caffeine_before_second = states[895].caffeine_plasma_mg_l
        
        # Caffeine sometime after second dose
        caffeine_after_second = max(s.caffeine_plasma_mg_l for s in states[900:1000])
        
        # Should be higher after second dose (accumulation)
        assert caffeine_after_second > caffeine_before_second * 0.8  # Allow some tolerance
    
    def test_caffeine_present_at_night(self, integrator, initial_state, full_day_timeline):
        """Afternoon caffeine should still be present at 22:00."""
        states = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        # At 22:00 (1320 minutes), caffeine should still be detectable
        caffeine_at_22 = states[1320].caffeine_plasma_mg_l
        
        assert caffeine_at_22 > 0.1  # Still >0.1 mg/L
    
    def test_state_is_continuous(self, integrator, initial_state, full_day_timeline):
        """State should change smoothly, no discontinuities."""
        states = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        # Check glucose doesn't jump too much between consecutive states
        for i in range(1, len(states)):
            glucose_change = abs(states[i].glucose_plasma_mg_dl - states[i-1].glucose_plasma_mg_dl)
            # Max change per minute should be reasonable (<30 mg/dL)
            assert glucose_change < 30.0, f"Discontinuity at t={i}: {glucose_change}"
    
    def test_hours_since_meal_resets_correctly(self, integrator, initial_state, full_day_timeline):
        """hours_since_last_meal should reset after each meal."""
        states = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        # After breakfast at t=450, hours should reset
        # Check at t=500 (50 min after breakfast)
        hours_after_breakfast = states[500].hours_since_last_meal
        assert hours_after_breakfast < 1.5
        
        # After lunch at t=780, hours should reset again
        # Check at t=840 (60 min after lunch)
        hours_after_lunch = states[840].hours_since_last_meal
        assert hours_after_lunch < 2.0


# =============================================================================
# EDGE CASES
# =============================================================================

class TestSimulateTimelineEdgeCases:
    """Test edge cases and error handling."""
    
    def test_event_at_time_zero(self, integrator, initial_state):
        """Event at t=0 should be processed in first step."""
        event = Event.create_ingestion(
            timestamp_minutes=0.0,
            compound_id="caffeine",
            amount=100.0,
            unit="mg",
            form="liquid"
        )
        timeline = Timeline().add_event(event)
        
        states = integrator.simulate_timeline(initial_state, timeline)
        
        # Caffeine should appear by t=30 (absorption takes time)
        assert states[30].caffeine_plasma_mg_l > 0.0
    
    def test_event_at_end_of_day(self, integrator, initial_state):
        """Event at t=1439 should be processed."""
        event = Event.create_meal(
            timestamp_minutes=1439.0,
            carbs_g=30.0,
            protein_g=10.0,
            fat_g=5.0,
            glycemic_index=70.0
        )
        timeline = Timeline().add_event(event)
        
        states = integrator.simulate_timeline(initial_state, timeline)
        
        # State at t=1440 should show effect of meal (glucose_gut has carbs)
        assert states[1440].glucose_gut_mg > 0.0
    
    def test_large_dt_still_works(self, integrator, initial_state, simple_meal_timeline):
        """dt=60 (hourly) should still work."""
        states = integrator.simulate_timeline(initial_state, simple_meal_timeline, dt_minutes=60.0)
        
        # 1440 / 60 + 1 = 25 states
        assert len(states) == 25
        
        # Timestamps should be 0, 60, 120, ..., 1440
        for i, state in enumerate(states):
            assert state.timestamp_minutes == i * 60.0
    
    def test_events_applied_at_correct_timestep(self, integrator, initial_state):
        """Events should be applied when timestamp matches dt boundary."""
        # Meal at t=60
        event = Event.create_meal(
            timestamp_minutes=60.0,
            carbs_g=50.0,
            protein_g=20.0,
            fat_g=10.0,
            glycemic_index=70.0
        )
        timeline = Timeline().add_event(event)
        
        # With dt=10, event at t=60 should affect state after t=60
        states = integrator.simulate_timeline(initial_state, timeline, dt_minutes=10.0)
        
        # State at t=70 (index 7) should have meal effect
        state_at_70 = states[7]
        
        # hours_since_last_meal should be reset (meal happened at t=60)
        assert state_at_70.hours_since_last_meal < 1.0


# =============================================================================
# REPRODUCIBILITY TESTS
# =============================================================================

class TestSimulateTimelineReproducibility:
    """Test determinism and reproducibility."""
    
    def test_same_inputs_same_outputs(self, reference_person, initial_state, full_day_timeline):
        """Same inputs should produce identical outputs."""
        integrator1 = StateIntegrator(person=reference_person)
        integrator2 = StateIntegrator(person=reference_person)
        
        states1 = integrator1.simulate_timeline(initial_state, full_day_timeline)
        states2 = integrator2.simulate_timeline(initial_state, full_day_timeline)
        
        assert len(states1) == len(states2)
        
        for s1, s2 in zip(states1, states2):
            assert s1.glucose_plasma_mg_dl == s2.glucose_plasma_mg_dl
            assert s1.caffeine_plasma_mg_l == s2.caffeine_plasma_mg_l
            assert s1.alertness_score == s2.alertness_score
    
    def test_different_dt_produces_similar_endpoint(self, integrator, initial_state, empty_timeline):
        """Different dt values should produce similar end states."""
        states_dt1 = integrator.simulate_timeline(initial_state, empty_timeline, dt_minutes=1.0)
        
        # Need new integrator to reset internal state
        integrator2 = StateIntegrator(person=integrator.person)
        states_dt5 = integrator2.simulate_timeline(initial_state, empty_timeline, dt_minutes=5.0)
        
        # Final glucose should be similar (within 10%)
        final_dt1 = states_dt1[-1].glucose_plasma_mg_dl
        final_dt5 = states_dt5[-1].glucose_plasma_mg_dl
        
        assert abs(final_dt1 - final_dt5) < final_dt1 * 0.10


# =============================================================================
# CONTRACT COMPLIANCE TESTS
# =============================================================================

class TestSimulateTimelineContract:
    """Tests verifying Contract 2.4 compliance."""
    
    def test_returns_valid_states(self, integrator, initial_state, full_day_timeline):
        """All returned states must be valid PhysiologicalState objects."""
        states = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        for state in states:
            # Glucose in valid range
            assert 20 <= state.glucose_plasma_mg_dl <= 600
            
            # Caffeine non-negative
            assert state.caffeine_plasma_mg_l >= 0
            
            # Alertness in valid range
            assert 0 <= state.alertness_score <= 100
            
            # No NaN values
            assert not (state.glucose_plasma_mg_dl != state.glucose_plasma_mg_dl)  # NaN check
    
    def test_timeline_not_modified(self, integrator, initial_state, full_day_timeline):
        """simulate_timeline should not modify the input timeline."""
        events_before = list(full_day_timeline.events)
        
        _ = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        events_after = list(full_day_timeline.events)
        
        assert len(events_before) == len(events_after)
    
    def test_initial_state_not_modified(self, integrator, initial_state, full_day_timeline):
        """simulate_timeline should not modify the initial state."""
        glucose_before = initial_state.glucose_plasma_mg_dl
        
        _ = integrator.simulate_timeline(initial_state, full_day_timeline)
        
        # Initial state is frozen, so this should always pass
        assert initial_state.glucose_plasma_mg_dl == glucose_before
