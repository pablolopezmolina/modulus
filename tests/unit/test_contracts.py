# MODULUS - Contract Tests
# Sesión 0.1: Validar que los contratos Pydantic funcionan correctamente
#
# Estos tests verifican que:
# - Event rechaza timestamps inválidos
# - PhysiologicalState rechaza valores no fisiológicos
# - SimulationResult cumple sus invariantes

import pytest
import numpy as np
from typing import Dict, Any

from src.core.contracts.events import Event, EventType
from src.core.contracts.state import PhysiologicalState
from src.core.contracts.results import SimulationResult


# ============================================================================
# EVENT TESTS
# ============================================================================

class TestEvent:
    """Tests para el contrato Event (Contract 2.1)."""

    def test_valid_ingestion_event(self):
        """Un evento de ingesta válido debe crearse correctamente."""
        event = Event(
            timestamp_minutes=60.0,
            event_type=EventType.INGESTION,
            payload={
                "compound_id": "caffeine",
                "amount": 100.0,
                "unit": "mg",
                "form": "capsule"
            }
        )
        assert event.timestamp_minutes == 60.0
        assert event.event_type == EventType.INGESTION
        assert event.payload["compound_id"] == "caffeine"

    def test_valid_meal_event(self):
        """Un evento de comida válido debe crearse correctamente."""
        event = Event(
            timestamp_minutes=480.0,  # 8:00 AM
            event_type=EventType.MEAL,
            payload={
                "carbs_g": 50.0,
                "protein_g": 20.0,
                "fat_g": 15.0,
                "fiber_g": 5.0,
                "glycemic_index": 55.0
            }
        )
        assert event.timestamp_minutes == 480.0
        assert event.event_type == EventType.MEAL

    def test_reject_negative_timestamp(self):
        """Event debe rechazar timestamp negativo."""
        with pytest.raises(ValueError, match="timestamp_minutes"):
            Event(
                timestamp_minutes=-1.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "amount": 100, "unit": "mg", "form": "capsule"}
            )

    def test_reject_timestamp_over_1440(self):
        """Event debe rechazar timestamp > 1440 (más de 24h)."""
        with pytest.raises(ValueError, match="timestamp_minutes"):
            Event(
                timestamp_minutes=1441.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "amount": 100, "unit": "mg", "form": "capsule"}
            )

    def test_timestamp_at_boundaries(self):
        """Event debe aceptar timestamps en los límites (0 y 1440)."""
        event_start = Event(
            timestamp_minutes=0.0,
            event_type=EventType.MEAL,
            payload={"carbs_g": 50, "protein_g": 20, "fat_g": 10, "fiber_g": 5, "glycemic_index": 50}
        )
        event_end = Event(
            timestamp_minutes=1440.0,
            event_type=EventType.SLEEP,
            payload={"duration_minutes": 480}
        )
        assert event_start.timestamp_minutes == 0.0
        assert event_end.timestamp_minutes == 1440.0

    def test_event_is_immutable(self):
        """Event debe ser inmutable (frozen)."""
        event = Event(
            timestamp_minutes=60.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100, "unit": "mg", "form": "capsule"}
        )
        with pytest.raises((AttributeError, TypeError, Exception)):
            event.timestamp_minutes = 120.0

    def test_event_to_dict(self):
        """Event debe poder convertirse a diccionario."""
        event = Event(
            timestamp_minutes=60.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100, "unit": "mg", "form": "capsule"}
        )
        d = event.to_dict()
        assert d["timestamp_minutes"] == 60.0
        assert d["event_type"] == "ingestion"

    def test_event_from_dict(self):
        """Event debe poder crearse desde diccionario."""
        d = {
            "timestamp_minutes": 60.0,
            "event_type": "ingestion",
            "payload": {"compound_id": "caffeine", "amount": 100, "unit": "mg", "form": "capsule"}
        }
        event = Event.from_dict(d)
        assert event.timestamp_minutes == 60.0
        assert event.event_type == EventType.INGESTION


# ============================================================================
# PHYSIOLOGICAL STATE TESTS
# ============================================================================

class TestPhysiologicalState:
    """Tests para el contrato PhysiologicalState (Contract 2.3)."""

    def test_valid_state(self):
        """Un estado fisiológico válido debe crearse correctamente."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0
        )
        assert state.glucose_plasma_mg_dl == 90.0
        assert state.is_fasted is True

    def test_reject_negative_glucose(self):
        """State debe rechazar glucosa negativa."""
        with pytest.raises(ValueError, match="glucose_plasma_mg_dl"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=-10.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0
            )

    def test_reject_nan_glucose(self):
        """State debe rechazar glucosa NaN."""
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
                hours_since_last_meal=8.0
            )

    def test_reject_infinite_values(self):
        """State debe rechazar valores infinitos."""
        with pytest.raises(ValueError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=float('inf'),
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0
            )

    def test_reject_negative_timestamp(self):
        """State debe rechazar timestamp negativo."""
        with pytest.raises(ValueError, match="timestamp_minutes"):
            PhysiologicalState(
                timestamp_minutes=-5.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0
            )

    def test_reject_alertness_out_of_range(self):
        """State debe rechazar alertness fuera de [0, 100]."""
        with pytest.raises(ValueError, match="alertness_score"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=150.0,  # > 100
                is_fasted=True,
                hours_since_last_meal=8.0
            )

    def test_reject_receptor_occupancy_out_of_range(self):
        """State debe rechazar adenosine_receptor_occupancy fuera de [0, 1]."""
        with pytest.raises(ValueError, match="adenosine_receptor_occupancy"):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=90.0,
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=1.5,  # > 1
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0
            )

    def test_state_is_immutable(self):
        """PhysiologicalState debe ser inmutable (frozen)."""
        state = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0
        )
        with pytest.raises((AttributeError, TypeError, Exception)):
            state.glucose_plasma_mg_dl = 120.0

    def test_physiological_ranges_glucose(self):
        """Glucosa debe estar en rango fisiológico [20, 600] mg/dL."""
        # Hipoglucemia severa (límite bajo)
        state_low = PhysiologicalState(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=20.0,
            insulin_plasma_mu_l=8.0,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=8.0
        )
        assert state_low.glucose_plasma_mg_dl == 20.0

        # Demasiado bajo
        with pytest.raises(ValueError):
            PhysiologicalState(
                timestamp_minutes=0.0,
                glucose_plasma_mg_dl=10.0,  # < 20
                insulin_plasma_mu_l=8.0,
                glucose_gut_mg=0.0,
                caffeine_plasma_mg_l=0.0,
                adenosine_receptor_occupancy=0.0,
                alertness_score=50.0,
                is_fasted=True,
                hours_since_last_meal=8.0
            )


# ============================================================================
# SIMULATION RESULT TESTS
# ============================================================================

class TestSimulationResult:
    """Tests para el contrato SimulationResult (Contract 1.1)."""

    def test_valid_result(self):
        """Un resultado de simulación válido debe crearse correctamente."""
        time_points = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        result = SimulationResult(
            time_points=time_points,
            channels={
                "glucose": np.array([90.0, 95.0, 120.0, 110.0, 95.0]),
                "insulin": np.array([8.0, 12.0, 25.0, 20.0, 10.0])
            },
            metrics={"is_valid": True, "peak_glucose": 120.0},
            metadata={"model": "test", "version": "1.0"}
        )
        assert len(result.time_points) == 5
        assert result.metrics["is_valid"] is True

    def test_time_points_must_start_at_zero(self):
        """time_points debe empezar en 0."""
        with pytest.raises(ValueError, match="time_points.*must start at 0"):
            SimulationResult(
                time_points=np.array([1.0, 2.0, 3.0]),  # No empieza en 0
                channels={"glucose": np.array([90.0, 95.0, 100.0])},
                metrics={"is_valid": True},
                metadata={}
            )

    def test_time_points_must_be_monotonic(self):
        """time_points debe ser monotónicamente creciente."""
        with pytest.raises(ValueError, match="monotonically increasing"):
            SimulationResult(
                time_points=np.array([0.0, 2.0, 1.0, 3.0]),  # No monotónico
                channels={"glucose": np.array([90.0, 95.0, 100.0, 105.0])},
                metrics={"is_valid": True},
                metadata={}
            )

    def test_channels_must_match_time_points_length(self):
        """Cada channel debe tener la misma longitud que time_points."""
        with pytest.raises(ValueError, match="length"):
            SimulationResult(
                time_points=np.array([0.0, 1.0, 2.0]),
                channels={"glucose": np.array([90.0, 95.0])},  # Solo 2 valores
                metrics={"is_valid": True},
                metadata={}
            )

    def test_metrics_must_have_is_valid(self):
        """metrics debe incluir 'is_valid'."""
        with pytest.raises(ValueError, match="is_valid"):
            SimulationResult(
                time_points=np.array([0.0, 1.0, 2.0]),
                channels={"glucose": np.array([90.0, 95.0, 100.0])},
                metrics={"peak_glucose": 100.0},  # Falta is_valid
                metadata={}
            )

    def test_empty_channels_allowed_if_invalid(self):
        """Channels pueden estar vacíos si is_valid=False."""
        result = SimulationResult(
            time_points=np.array([0.0]),
            channels={},
            metrics={"is_valid": False, "error": "simulation failed"},
            metadata={}
        )
        assert result.metrics["is_valid"] is False

    def test_result_channels_no_nan(self):
        """Channels no deben contener NaN."""
        with pytest.raises(ValueError, match="NaN"):
            SimulationResult(
                time_points=np.array([0.0, 1.0, 2.0]),
                channels={"glucose": np.array([90.0, float('nan'), 100.0])},
                metrics={"is_valid": True},
                metadata={}
            )

    def test_result_channels_no_inf(self):
        """Channels no deben contener Inf."""
        with pytest.raises(ValueError, match="infinite"):
            SimulationResult(
                time_points=np.array([0.0, 1.0, 2.0]),
                channels={"glucose": np.array([90.0, float('inf'), 100.0])},
                metrics={"is_valid": True},
                metadata={}
            )


# ============================================================================
# EDGE CASES AND INTEGRATION
# ============================================================================

class TestContractIntegration:
    """Tests de integración entre contratos."""

    def test_event_types_are_complete(self):
        """Todos los tipos de evento definidos deben existir."""
        assert EventType.INGESTION.value == "ingestion"
        assert EventType.MEAL.value == "meal"
        assert EventType.EXERCISE.value == "exercise"
        assert EventType.SLEEP.value == "sleep"

    def test_state_can_be_created_from_defaults(self):
        """Debe existir un factory method para estado inicial."""
        # Este test verifica que existe el método, la implementación
        # real usará VirtualPerson cuando esté disponible
        state = PhysiologicalState.create_fasted_default()
        assert state.is_fasted is True
        assert state.timestamp_minutes == 0.0
        assert 70 <= state.glucose_plasma_mg_dl <= 110  # Rango ayunas normal
