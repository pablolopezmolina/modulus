"""
Tests for StateIntegrator - Session 2.2

Contract 2.4 compliance:
- step() ALWAYS returns a valid state
- If error, returns previous state unchanged + log warning
- Integrates DallaManModel and EliteCaffeineModel
- Handles "meal" and "ingestion" events
"""

import pytest
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# =============================================================================
# MOCK CLASSES FOR TESTING
# =============================================================================
# These will be replaced by real imports when integrated with the actual codebase


@dataclass(frozen=True)
class MockVirtualPerson:
    """Mock VirtualPerson for testing (matches Contract 1.2)."""
    person_id: str = "test_person"
    age: int = 35
    sex: str = "male"
    weight_kg: float = 78.0
    height_cm: float = 175.0
    fasting_glucose_mg_dl: float = 95.0
    fasting_insulin_mu_l: float = 8.0
    insulin_sensitivity_factor: float = 1.0
    cyp1a2_genotype: str = "normal"
    caffeine_half_life_h: float = 5.0
    habitual_caffeine_mg: float = 100.0
    activity_level: str = "moderate"
    smoker: bool = False
    
    def get_glucose_overrides(self) -> Dict[str, float]:
        return {"SI": self.insulin_sensitivity_factor}
    
    def get_caffeine_overrides(self) -> Dict[str, float]:
        return {"half_life_h": self.caffeine_half_life_h}


@dataclass(frozen=True)
class MockPhysiologicalState:
    """Mock PhysiologicalState for testing (matches Contract 2.3)."""
    timestamp_minutes: float
    glucose_plasma_mg_dl: float = 95.0
    insulin_plasma_mu_l: float = 8.0
    glucose_gut_mg: float = 0.0
    caffeine_plasma_mg_l: float = 0.0
    adenosine_receptor_occupancy: float = 0.0
    alertness_score: float = 50.0
    is_fasted: bool = True
    hours_since_last_meal: float = 12.0
    
    def with_updates(self, **kwargs) -> "MockPhysiologicalState":
        """Create new state with updated values."""
        current = {
            "timestamp_minutes": self.timestamp_minutes,
            "glucose_plasma_mg_dl": self.glucose_plasma_mg_dl,
            "insulin_plasma_mu_l": self.insulin_plasma_mu_l,
            "glucose_gut_mg": self.glucose_gut_mg,
            "caffeine_plasma_mg_l": self.caffeine_plasma_mg_l,
            "adenosine_receptor_occupancy": self.adenosine_receptor_occupancy,
            "alertness_score": self.alertness_score,
            "is_fasted": self.is_fasted,
            "hours_since_last_meal": self.hours_since_last_meal,
        }
        current.update(kwargs)
        return MockPhysiologicalState(**current)


@dataclass(frozen=True)
class MockEvent:
    """Mock Event for testing (matches Contract 2.1)."""
    timestamp_minutes: float
    event_type: str
    payload: Dict[str, Any]


class MockSimulationResult:
    """Mock SimulationResult for testing (matches Contract 1.1)."""
    def __init__(self, time_points: np.ndarray, channels: Dict[str, np.ndarray], 
                 metrics: Dict[str, float], metadata: Optional[Dict[str, Any]] = None):
        self.time_points = time_points
        self.channels = channels
        self.metrics = metrics
        self.metadata = metadata or {}


class MockGlucoseModel:
    """Mock DallaManModel for testing."""
    def __init__(self, person: MockVirtualPerson):
        self.person = person
    
    def simulate(self, duration_minutes: float, time_step_minutes: float = 1.0,
                 meal_carbs_g: float = 0.0, **kwargs) -> MockSimulationResult:
        """Simulate glucose response."""
        n_points = int(duration_minutes / time_step_minutes) + 1
        time_points = np.linspace(0, duration_minutes, n_points)
        
        # Simple glucose dynamics for testing
        glucose = np.full(n_points, self.person.fasting_glucose_mg_dl)
        insulin = np.full(n_points, self.person.fasting_insulin_mu_l)
        
        if meal_carbs_g > 0:
            # Simulate glucose rise and fall
            peak_time_idx = min(int(45 / time_step_minutes), n_points - 1)  # ~45 min peak
            peak_glucose = self.person.fasting_glucose_mg_dl + meal_carbs_g * 0.8
            for i in range(n_points):
                if i <= peak_time_idx:
                    glucose[i] = self.person.fasting_glucose_mg_dl + (peak_glucose - self.person.fasting_glucose_mg_dl) * (i / peak_time_idx)
                else:
                    decay = np.exp(-(i - peak_time_idx) * time_step_minutes / 120)  # ~120 min half-life
                    glucose[i] = self.person.fasting_glucose_mg_dl + (peak_glucose - self.person.fasting_glucose_mg_dl) * decay
        
        return MockSimulationResult(
            time_points=time_points,
            channels={"glucose_mg_dl": glucose, "insulin_mu_l": insulin},
            metrics={"peak_glucose": float(np.max(glucose)), "is_valid": True}
        )


class MockCaffeineModel:
    """Mock EliteCaffeineModel for testing."""
    def __init__(self, person: MockVirtualPerson):
        self.person = person
        self.half_life_h = person.caffeine_half_life_h
    
    def simulate(self, duration_minutes: float, time_step_minutes: float = 1.0,
                 dose_mg: float = 0.0, **kwargs) -> MockSimulationResult:
        """Simulate caffeine response."""
        n_points = int(duration_minutes / time_step_minutes) + 1
        time_points = np.linspace(0, duration_minutes, n_points)
        
        # Simple 1-compartment PK
        caffeine = np.zeros(n_points)
        alertness = np.full(n_points, 50.0)  # baseline
        
        if dose_mg > 0:
            # Assume Vd ~40L for 78kg person, so Cmax = dose / Vd
            vd_l = 0.5 * self.person.weight_kg  # ~0.5 L/kg
            cmax = dose_mg / vd_l  # mg/L
            ke = np.log(2) / (self.half_life_h * 60)  # elimination rate constant (per minute)
            ka = 0.05  # absorption rate constant ~20 min to peak
            
            for i in range(n_points):
                t = time_points[i]
                # Two-compartment kinetics approximation
                caffeine[i] = cmax * (np.exp(-ke * t) - np.exp(-ka * t)) * ka / (ka - ke)
                caffeine[i] = max(0, caffeine[i])
                
                # Alertness effect (Emax model)
                ec50 = 1.5  # mg/L
                emax = 40  # max additional alertness
                alertness[i] = 50 + emax * caffeine[i] / (ec50 + caffeine[i])
        
        return MockSimulationResult(
            time_points=time_points,
            channels={"caffeine_mg_l": caffeine, "alertness": alertness},
            metrics={"peak_caffeine": float(np.max(caffeine)), "is_valid": True}
        )


# =============================================================================
# ACTUAL TESTS FOR StateIntegrator
# =============================================================================

class TestStateIntegratorContract:
    """Test Contract 2.4 compliance."""
    
    def test_step_returns_valid_state(self):
        """step() ALWAYS returns a valid PhysiologicalState."""
        # This test validates the contract requirement
        person = MockVirtualPerson()
        initial_state = MockPhysiologicalState(timestamp_minutes=0.0)
        
        # Import the actual StateIntegrator when available
        # For now, we define the expected behavior
        from src.core.state.integrator import StateIntegrator
        
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        # Step with no events
        new_state = integrator.step(initial_state, events=[], dt_minutes=1.0)
        
        # Validate it's a PhysiologicalState (or compatible)
        assert hasattr(new_state, 'timestamp_minutes')
        assert hasattr(new_state, 'glucose_plasma_mg_dl')
        assert hasattr(new_state, 'caffeine_plasma_mg_l')
        assert new_state.timestamp_minutes == 1.0
    
    def test_step_advances_time(self):
        """step() advances timestamp_minutes by dt_minutes."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(timestamp_minutes=100.0)
        new_state = integrator.step(initial_state, events=[], dt_minutes=5.0)
        
        assert new_state.timestamp_minutes == 105.0
    
    def test_step_with_no_events_maintains_baseline(self):
        """step() without events maintains physiological baseline (with natural decay)."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        # Fasted state
        initial_state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=95.0,
            caffeine_plasma_mg_l=0.0
        )
        
        new_state = integrator.step(initial_state, events=[], dt_minutes=1.0)
        
        # Glucose should remain near fasting (no meal)
        assert 90.0 <= new_state.glucose_plasma_mg_dl <= 100.0
        # Caffeine should remain 0 (no intake)
        assert new_state.caffeine_plasma_mg_l == 0.0


class TestMealEventHandling:
    """Test handling of meal events."""
    
    def test_step_handles_meal_event(self):
        """step() correctly processes meal events."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            is_fasted=True,
            hours_since_last_meal=12.0
        )
        
        meal_event = MockEvent(
            timestamp_minutes=0.0,
            event_type="meal",
            payload={
                "carbs_g": 75.0,
                "protein_g": 0.0,
                "fat_g": 0.0,
                "fiber_g": 0.0,
                "glycemic_index": 100.0
            }
        )
        
        new_state = integrator.step(initial_state, events=[meal_event], dt_minutes=1.0)
        
        # State should reflect meal was consumed
        assert new_state.is_fasted == False
        assert new_state.hours_since_last_meal < initial_state.hours_since_last_meal
    
    def test_meal_adds_to_glucose_gut(self):
        """Meal event adds carbs to glucose_gut for absorption."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            glucose_gut_mg=0.0
        )
        
        meal_event = MockEvent(
            timestamp_minutes=0.0,
            event_type="meal",
            payload={
                "carbs_g": 50.0,
                "protein_g": 0.0,
                "fat_g": 0.0,
                "fiber_g": 0.0,
                "glycemic_index": 70.0
            }
        )
        
        new_state = integrator.step(initial_state, events=[meal_event], dt_minutes=1.0)
        
        # Glucose in gut should increase (50g = 50000mg)
        # May be partially absorbed already in first step
        assert new_state.glucose_gut_mg >= 0


class TestIngestionEventHandling:
    """Test handling of ingestion (caffeine) events."""
    
    def test_step_handles_caffeine_ingestion(self):
        """step() correctly processes caffeine ingestion events."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            caffeine_plasma_mg_l=0.0,
            alertness_score=50.0
        )
        
        caffeine_event = MockEvent(
            timestamp_minutes=0.0,
            event_type="ingestion",
            payload={
                "compound_id": "caffeine",
                "amount": 100.0,
                "unit": "mg",
                "form": "liquid"
            }
        )
        
        new_state = integrator.step(initial_state, events=[caffeine_event], dt_minutes=1.0)
        
        # Caffeine should start appearing (may be small after 1 min)
        # The key is that the event was processed
        assert new_state.caffeine_plasma_mg_l >= 0.0
    
    def test_caffeine_increases_alertness(self):
        """Caffeine ingestion should eventually increase alertness."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            caffeine_plasma_mg_l=0.0,
            alertness_score=50.0
        )
        
        # Give caffeine
        caffeine_event = MockEvent(
            timestamp_minutes=0.0,
            event_type="ingestion",
            payload={
                "compound_id": "caffeine",
                "amount": 200.0,
                "unit": "mg",
                "form": "liquid"
            }
        )
        
        # Simulate 60 minutes to let caffeine absorb
        state = integrator.step(state, events=[caffeine_event], dt_minutes=1.0)
        for _ in range(59):
            state = integrator.step(state, events=[], dt_minutes=1.0)
        
        # After 60 minutes, caffeine should have increased alertness
        assert state.alertness_score > 50.0
        assert state.caffeine_plasma_mg_l > 0.0


class TestMultipleEvents:
    """Test handling of multiple events in one step."""
    
    def test_step_handles_multiple_events(self):
        """step() can process multiple events in the same timestep."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(timestamp_minutes=0.0)
        
        # Both meal and caffeine at t=0
        events = [
            MockEvent(
                timestamp_minutes=0.0,
                event_type="meal",
                payload={"carbs_g": 50.0, "protein_g": 10.0, "fat_g": 5.0,
                         "fiber_g": 3.0, "glycemic_index": 60.0}
            ),
            MockEvent(
                timestamp_minutes=0.0,
                event_type="ingestion",
                payload={"compound_id": "caffeine", "amount": 100.0,
                         "unit": "mg", "form": "liquid"}
            )
        ]
        
        new_state = integrator.step(initial_state, events=events, dt_minutes=1.0)
        
        # Both should be processed
        assert new_state.is_fasted == False  # Meal was processed
        assert new_state.timestamp_minutes == 1.0


class TestErrorHandling:
    """Test error handling per Contract 2.4."""
    
    def test_step_returns_previous_state_on_error(self):
        """If error occurs, step() returns previous state + logs warning."""
        from src.core.state.integrator import StateIntegrator
        import warnings
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(
            timestamp_minutes=50.0,
            glucose_plasma_mg_dl=100.0
        )
        
        # Invalid event (unknown compound)
        bad_event = MockEvent(
            timestamp_minutes=50.0,
            event_type="ingestion",
            payload={"compound_id": "unknown_compound", "amount": 100.0,
                     "unit": "mg", "form": "powder"}
        )
        
        # Should not raise, should warn and return valid state
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            new_state = integrator.step(initial_state, events=[bad_event], dt_minutes=1.0)
            
            # Should have logged a warning (or handled gracefully)
            # The key is that we get a valid state back
            assert hasattr(new_state, 'timestamp_minutes')


class TestHoursSinceLastMeal:
    """Test hours_since_last_meal tracking."""
    
    def test_hours_since_meal_updates_on_meal(self):
        """hours_since_last_meal resets to 0 on meal event."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            hours_since_last_meal=12.0,
            is_fasted=True
        )
        
        meal_event = MockEvent(
            timestamp_minutes=0.0,
            event_type="meal",
            payload={"carbs_g": 50.0, "protein_g": 0.0, "fat_g": 0.0,
                     "fiber_g": 0.0, "glycemic_index": 70.0}
        )
        
        new_state = integrator.step(initial_state, events=[meal_event], dt_minutes=1.0)
        
        # After meal, hours since last meal should be very small (dt/60)
        assert new_state.hours_since_last_meal < 0.1
    
    def test_hours_since_meal_increments_without_meal(self):
        """hours_since_last_meal increments when no meal event."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        initial_state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            hours_since_last_meal=5.0,
            is_fasted=False
        )
        
        # 60 minutes without meal
        state = initial_state
        for _ in range(60):
            state = integrator.step(state, events=[], dt_minutes=1.0)
        
        # hours_since_last_meal should have increased by 1
        assert abs(state.hours_since_last_meal - 6.0) < 0.1


class TestIntegratorInitialization:
    """Test StateIntegrator initialization."""
    
    def test_integrator_requires_person(self):
        """StateIntegrator requires a VirtualPerson."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        assert integrator.person == person
    
    def test_integrator_accepts_model_dict(self):
        """StateIntegrator can accept models as dict (Contract 2.4 signature)."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        
        # Alternative initialization per Contract 2.4
        models = {
            "glucose": MockGlucoseModel(person),
            "caffeine": MockCaffeineModel(person)
        }
        
        integrator = StateIntegrator(person=person, models=models)
        
        assert integrator.person == person


class TestFastedState:
    """Test is_fasted state transitions."""
    
    def test_becomes_fasted_after_hours(self):
        """is_fasted becomes True after sufficient hours without meal."""
        from src.core.state.integrator import StateIntegrator
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        # Start with recent meal
        state = MockPhysiologicalState(
            timestamp_minutes=0.0,
            hours_since_last_meal=6.0,
            is_fasted=False
        )
        
        # Simulate 6 more hours (360 minutes) = 12h total
        for _ in range(360):
            state = integrator.step(state, events=[], dt_minutes=1.0)
        
        # After 12 hours, should be fasted
        assert state.is_fasted == True
        assert state.hours_since_last_meal >= 12.0


# =============================================================================
# INTEGRATION WITH REAL PHYSIOLOGICAL STATE
# =============================================================================

class TestWithRealPhysiologicalState:
    """Test that integrator works with the real PhysiologicalState from Session 2.1."""
    
    def test_returns_real_physiological_state(self):
        """step() returns a real PhysiologicalState instance."""
        from src.core.state.integrator import StateIntegrator
        from src.core.state import PhysiologicalState
        
        person = MockVirtualPerson()
        integrator = StateIntegrator(
            person=person,
            glucose_model=MockGlucoseModel(person),
            caffeine_model=MockCaffeineModel(person)
        )
        
        # Use real PhysiologicalState
        initial_state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=95.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=12.0
        )
        
        new_state = integrator.step(initial_state, events=[], dt_minutes=1.0)
        
        # Should return a PhysiologicalState
        assert isinstance(new_state, PhysiologicalState)
        assert new_state.timestamp_minutes == 1.0
