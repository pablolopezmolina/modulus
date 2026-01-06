"""
MODULUS - Contract Tests
Version: 3.0

Tests that verify the contracts defined in CONTRACTS.md are enforced.
These tests should NEVER be deleted or modified to pass failing code.
"""

import pytest
import math
import sys
from pathlib import Path
import numpy as np
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.contracts.events import Event, EventType
from core.contracts.state import PhysiologicalState
from core.contracts.results import SimulationResult


# ============================================================================
# EVENT TESTS
# ============================================================================

class TestEventContract:
    """Tests for Event contract validation."""
    
    def test_event_valid_ingestion(self):
        """Valid ingestion event should be created."""
        event = Event(
            timestamp_minutes=60.0,
            event_type=EventType.INGESTION,
            payload={
                "compound_id": "caffeine",
                "amount": 100.0,
                "unit": "mg",
                "form": "powder",
            }
        )
        assert event.timestamp_minutes == 60.0
        assert event.event_type == EventType.INGESTION
    
    def test_event_valid_meal(self):
        """Valid meal event should be created."""
        event = Event(
            timestamp_minutes=420.0,
            event_type=EventType.MEAL,
            payload={
                "carbs_g": 50.0,
                "protein_g": 20.0,
                "fat_g": 10.0,
            }
        )
        assert event.event_type == EventType.MEAL
    
    def test_event_rejects_negative_timestamp(self):
        """Event should reject negative timestamp."""
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=-1.0,
                event_type=EventType.MEAL,
                payload={"carbs_g": 50.0}
            )
    
    def test_event_rejects_timestamp_over_1440(self):
        """Event should reject timestamp > 1440 (24 hours)."""
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=1441.0,
                event_type=EventType.MEAL,
                payload={"carbs_g": 50.0}
            )
    
    def test_event_rejects_ingestion_without_compound_id(self):
        """Ingestion event should require compound_id."""
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=60.0,
                event_type=EventType.INGESTION,
                payload={"amount": 100.0, "unit": "mg"}
            )
    
    def test_event_rejects_ingestion_with_zero_amount(self):
        """Ingestion event should reject zero amount."""
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=60.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "amount": 0.0, "unit": "mg"}
            )
    
    def test_event_rejects_ingestion_with_negative_amount(self):
        """Ingestion event should reject negative amount."""
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=60.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "amount": -10.0, "unit": "mg"}
            )
    
    def test_event_rejects_meal_without_carbs(self):
        """Meal event should require carbs_g."""
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type=EventType.MEAL,
                payload={"protein_g": 20.0}
            )
    
    def test_event_is_immutable(self):
        """Event should be frozen (immutable)."""
        event = Event.create_ingestion(60.0, "caffeine", 100.0)
        with pytest.raises(ValidationError):
            event.timestamp_minutes = 120.0
    
    def test_event_factory_ingestion(self):
        """Factory method for ingestion should work."""
        event = Event.create_ingestion(
            timestamp_minutes=60.0,
            compound_id="caffeine",
            amount=100.0,
            unit="mg",
            form="powder"
        )
        assert event.event_type == EventType.INGESTION
        assert event.payload["compound_id"] == "caffeine"
    
    def test_event_factory_meal(self):
        """Factory method for meal should work."""
        event = Event.create_meal(
            timestamp_minutes=420.0,
            carbs_g=50.0,
            protein_g=20.0,
            fat_g=10.0
        )
        assert event.event_type == EventType.MEAL
        assert event.payload["carbs_g"] == 50.0
    
    def test_event_to_dict_from_dict(self):
        """Event should round-trip through dict."""
        original = Event.create_ingestion(60.0, "caffeine", 100.0)
        data = original.to_dict()
        restored = Event.from_dict(data)
        assert restored.timestamp_minutes == original.timestamp_minutes
        assert restored.event_type == original.event_type


# ============================================================================
# PHYSIOLOGICAL STATE TESTS
# ============================================================================

class TestPhysiologicalStateContract:
    """Tests for PhysiologicalState contract validation."""
    
    def test_state_valid_fasted(self):
        """Valid fasted state should be created."""
        state = PhysiologicalState.create_fasted()
        assert state.glucose_plasma_mg_dl == 90.0
        assert state.is_fasted == True
    
    def test_state_valid_custom(self):
        """Custom state with valid values should be created."""
        state = PhysiologicalState(
            timestamp_minutes=60.0,
            glucose_plasma_mg_dl=120.0,
            insulin_plasma_mu_l=50.0,
            caffeine_plasma_mg_l=2.0,
            alertness_score=70.0,
        )
        assert state.glucose_plasma_mg_dl == 120.0
    
    def test_state_rejects_nan_glucose(self):
        """State should reject NaN glucose."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=float('nan'),
            )
    
    def test_state_rejects_inf_glucose(self):
        """State should reject Inf glucose."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=float('inf'),
            )
    
    def test_state_rejects_glucose_below_20(self):
        """State should reject glucose < 20 mg/dL (fatal hypoglycemia)."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=15.0,
            )
    
    def test_state_rejects_glucose_above_600(self):
        """State should reject glucose > 600 mg/dL (extreme hyperglycemia)."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=650.0,
            )
    
    def test_state_rejects_negative_insulin(self):
        """State should reject negative insulin."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=-5.0,
            )
    
    def test_state_rejects_negative_caffeine(self):
        """State should reject negative caffeine."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                caffeine_plasma_mg_l=-1.0,
            )
    
    def test_state_rejects_alertness_over_100(self):
        """State should reject alertness > 100."""
        with pytest.raises(ValidationError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                alertness_score=150.0,
            )
    
    def test_state_is_immutable(self):
        """State should be frozen (immutable)."""
        state = PhysiologicalState.create_fasted()
        with pytest.raises(ValidationError):
            state.glucose_plasma_mg_dl = 150.0
    
    def test_state_with_updates(self):
        """with_updates should return NEW state."""
        original = PhysiologicalState.create_fasted()
        updated = original.with_updates(glucose_plasma_mg_dl=120.0)
        assert updated.glucose_plasma_mg_dl == 120.0
        assert original.glucose_plasma_mg_dl == 90.0  # Original unchanged
    
    def test_state_to_dict(self):
        """to_dict should include all fields."""
        state = PhysiologicalState.create_fasted()
        data = state.to_dict()
        assert "glucose_plasma_mg_dl" in data
        assert "caffeine_plasma_mg_l" in data
        assert "is_fasted" in data


# ============================================================================
# SIMULATION RESULT TESTS
# ============================================================================

class TestSimulationResultContract:
    """Tests for SimulationResult contract validation."""
    
    def test_result_valid_basic(self):
        """Valid result should be created."""
        result = SimulationResult(
            time_points=[0.0, 1.0, 2.0],
            channels={"glucose": [90.0, 95.0, 100.0]},
            metrics={"is_valid": True},
        )
        assert len(result.time_points) == 3
        assert result.is_valid == True
    
    def test_result_rejects_time_not_starting_at_zero(self):
        """Result should reject time_points not starting at 0."""
        with pytest.raises(ValidationError):
            SimulationResult(
                time_points=[1.0, 2.0, 3.0],
                channels={"glucose": [90.0, 95.0, 100.0]},
            )
    
    def test_result_rejects_non_monotonic_time(self):
        """Result should reject non-monotonically increasing time."""
        with pytest.raises(ValidationError):
            SimulationResult(
                time_points=[0.0, 2.0, 1.0],
                channels={"glucose": [90.0, 95.0, 100.0]},
            )
    
    def test_result_rejects_channel_wrong_length(self):
        """Result should reject channel with wrong length."""
        with pytest.raises(ValidationError):
            SimulationResult(
                time_points=[0.0, 1.0, 2.0],
                channels={"glucose": [90.0, 95.0]},
            )
    
    def test_result_rejects_nan_in_channel(self):
        """Result should reject NaN values in channels."""
        with pytest.raises(ValidationError):
            SimulationResult(
                time_points=[0.0, 1.0, 2.0],
                channels={"glucose": [90.0, float('nan'), 100.0]},
            )
    
    def test_result_rejects_inf_in_time(self):
        """Result should reject Inf in time_points."""
        with pytest.raises(ValidationError):
            SimulationResult(
                time_points=[0.0, float('inf'), 2.0],
                channels={"glucose": [90.0, 95.0, 100.0]},
            )
    
    def test_result_adds_default_is_valid(self):
        """Result should add is_valid if not present."""
        result = SimulationResult(
            time_points=[0.0, 1.0, 2.0],
            channels={"glucose": [90.0, 95.0, 100.0]},
            metrics={},
        )
        assert result.is_valid == True
    
    def test_result_from_arrays(self):
        """from_arrays should convert numpy arrays."""
        time = np.array([0.0, 1.0, 2.0])
        glucose = np.array([90.0, 95.0, 100.0])
        
        result = SimulationResult.from_arrays(
            time_points=time,
            channels={"glucose": glucose},
        )
        assert len(result.time_points) == 3
        assert result.channels["glucose"][1] == 95.0
    
    def test_result_duration(self):
        """duration_minutes should compute correctly."""
        result = SimulationResult(
            time_points=[0.0, 60.0, 120.0],
            channels={"glucose": [90.0, 95.0, 100.0]},
        )
        assert result.duration_minutes == 120.0
    
    def test_result_get_channel_as_array(self):
        """get_channel_as_array should return numpy array."""
        result = SimulationResult(
            time_points=[0.0, 1.0, 2.0],
            channels={"glucose": [90.0, 95.0, 100.0]},
        )
        arr = result.get_channel_as_array("glucose")
        assert isinstance(arr, np.ndarray)
        assert len(arr) == 3
