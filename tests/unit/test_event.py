"""
Tests for Timeline Event module.

FASE 1, Sesión 1.1: Event (dataclass + validación)

Estos tests verifican que el módulo timeline/ expone correctamente
el Event definido en contracts/ y que cumple el Contract 2.1.
"""
import pytest
from typing import Dict, Any


class TestTimelineEventExports:
    """Verify timeline module exports Event correctly."""

    def test_event_importable_from_timeline(self):
        """Event should be importable from src.core.timeline."""
        from src.core.timeline import Event
        assert Event is not None

    def test_event_type_importable_from_timeline(self):
        """EventType should be importable from src.core.timeline."""
        from src.core.timeline import EventType
        assert EventType is not None

    def test_event_is_same_as_contracts(self):
        """Event from timeline should be the same class as from contracts."""
        from src.core.timeline import Event as TimelineEvent
        from src.core.contracts.events import Event as ContractEvent
        
        assert TimelineEvent is ContractEvent


class TestContract21Compliance:
    """
    Tests that Event complies with Contract 2.1 from CONTRACTS.md.
    
    Contract 2.1:
    - timestamp_minutes DEBE estar en [0, 1440]
    - event_type DEBE ser uno de los tipos definidos
    - payload DEBE contener los campos requeridos para su tipo
    """

    def test_timestamp_at_zero(self):
        """timestamp_minutes=0 (midnight) is valid."""
        from src.core.timeline import Event, EventType
        
        event = Event(
            timestamp_minutes=0.0,
            event_type=EventType.MEAL,
            payload={"carbs_g": 30.0}
        )
        assert event.timestamp_minutes == 0.0

    def test_timestamp_at_1440(self):
        """timestamp_minutes=1440 (end of day) is valid."""
        from src.core.timeline import Event, EventType
        
        event = Event(
            timestamp_minutes=1440.0,
            event_type=EventType.MEAL,
            payload={"carbs_g": 30.0}
        )
        assert event.timestamp_minutes == 1440.0

    def test_timestamp_negative_rejected(self):
        """timestamp_minutes < 0 should be rejected."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=-1.0,
                event_type=EventType.MEAL,
                payload={"carbs_g": 30.0}
            )

    def test_timestamp_over_1440_rejected(self):
        """timestamp_minutes > 1440 should be rejected."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=1441.0,
                event_type=EventType.MEAL,
                payload={"carbs_g": 30.0}
            )

    def test_valid_event_types(self):
        """All defined event types should be accepted."""
        from src.core.timeline import Event, EventType
        
        # Ingestion
        e1 = Event(
            timestamp_minutes=420.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100.0, "unit": "mg"}
        )
        assert e1.event_type == EventType.INGESTION
        
        # Meal
        e2 = Event(
            timestamp_minutes=480.0,
            event_type=EventType.MEAL,
            payload={"carbs_g": 50.0}
        )
        assert e2.event_type == EventType.MEAL
        
        # Exercise
        e3 = Event(
            timestamp_minutes=1080.0,
            event_type=EventType.EXERCISE,
            payload={"type": "resistance", "duration_minutes": 60}
        )
        assert e3.event_type == EventType.EXERCISE
        
        # Sleep
        e4 = Event(
            timestamp_minutes=1380.0,
            event_type=EventType.SLEEP,
            payload={"duration_hours": 8.0}
        )
        assert e4.event_type == EventType.SLEEP

    def test_invalid_event_type_rejected(self):
        """Invalid event_type should be rejected."""
        from src.core.timeline import Event
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type="invalid_type",  # Not a valid EventType
                payload={}
            )

    def test_ingestion_requires_compound_id(self):
        """Ingestion payload must have compound_id."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type=EventType.INGESTION,
                payload={"amount": 100.0, "unit": "mg"}  # Missing compound_id
            )

    def test_ingestion_requires_amount(self):
        """Ingestion payload must have amount."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "unit": "mg"}  # Missing amount
            )

    def test_ingestion_requires_unit(self):
        """Ingestion payload must have unit."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "amount": 100.0}  # Missing unit
            )

    def test_meal_requires_carbs_g(self):
        """Meal payload must have carbs_g."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=480.0,
                event_type=EventType.MEAL,
                payload={"protein_g": 20.0}  # Missing carbs_g
            )


class TestEventImmutability:
    """Tests for Event immutability (frozen=True)."""

    def test_event_is_frozen(self):
        """Event should be immutable (frozen)."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        event = Event(
            timestamp_minutes=420.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100.0, "unit": "mg"}
        )
        
        # Attempting to modify should raise an error
        with pytest.raises(ValidationError):
            event.timestamp_minutes = 500.0

    def test_event_equality(self):
        """Events with same values should be equal."""
        from src.core.timeline import Event, EventType
        
        event1 = Event(
            timestamp_minutes=420.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100.0, "unit": "mg"}
        )
        
        event2 = Event(
            timestamp_minutes=420.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100.0, "unit": "mg"}
        )
        
        # Events with same values should be equal
        assert event1 == event2
        
    # NOTE: Event is NOT hashable because payload is a dict (mutable).
    # This is acceptable since Events are used in Lists (Timeline), not Sets.
    # If hashability is needed in the future, payload would need to be
    # converted to a frozen structure (e.g., tuple of tuples).


class TestEventSerialization:
    """Tests for Event to_dict/from_dict methods."""

    def test_to_dict(self):
        """Event should serialize to dict correctly."""
        from src.core.timeline import Event, EventType
        
        event = Event(
            timestamp_minutes=420.0,
            event_type=EventType.INGESTION,
            payload={"compound_id": "caffeine", "amount": 100.0, "unit": "mg", "form": "capsule"}
        )
        
        d = event.to_dict()
        
        assert d["timestamp_minutes"] == 420.0
        assert d["event_type"] == "ingestion"  # String, not enum
        assert d["payload"]["compound_id"] == "caffeine"

    def test_from_dict(self):
        """Event should deserialize from dict correctly."""
        from src.core.timeline import Event
        
        data = {
            "timestamp_minutes": 420.0,
            "event_type": "ingestion",
            "payload": {"compound_id": "caffeine", "amount": 100.0, "unit": "mg", "form": "capsule"}
        }
        
        event = Event.from_dict(data)
        
        assert event.timestamp_minutes == 420.0
        assert event.payload["compound_id"] == "caffeine"

    def test_roundtrip_serialization(self):
        """to_dict → from_dict should produce equal event."""
        from src.core.timeline import Event, EventType
        
        original = Event(
            timestamp_minutes=720.0,  # Noon
            event_type=EventType.MEAL,
            payload={"carbs_g": 60.0, "protein_g": 25.0, "fat_g": 15.0, "fiber_g": 8.0, "glycemic_index": 55.0}
        )
        
        d = original.to_dict()
        restored = Event.from_dict(d)
        
        assert restored.timestamp_minutes == original.timestamp_minutes
        assert restored.event_type == original.event_type
        assert restored.payload == original.payload


class TestEventFactoryMethods:
    """Tests for Event factory methods."""

    def test_create_ingestion(self):
        """create_ingestion factory should work correctly."""
        from src.core.timeline import Event, EventType
        
        event = Event.create_ingestion(
            timestamp_minutes=420.0,
            compound_id="caffeine",
            amount=100.0,
            unit="mg",
            form="capsule"
        )
        
        assert event.timestamp_minutes == 420.0
        assert event.event_type == EventType.INGESTION
        assert event.payload["compound_id"] == "caffeine"
        assert event.payload["amount"] == 100.0
        assert event.payload["unit"] == "mg"
        assert event.payload["form"] == "capsule"

    def test_create_ingestion_defaults(self):
        """create_ingestion should have sensible defaults."""
        from src.core.timeline import Event
        
        event = Event.create_ingestion(
            timestamp_minutes=420.0,
            compound_id="caffeine",
            amount=100.0
        )
        
        assert event.payload["unit"] == "mg"  # Default
        assert event.payload["form"] == "powder"  # Default

    def test_create_meal(self):
        """create_meal factory should work correctly."""
        from src.core.timeline import Event, EventType
        
        event = Event.create_meal(
            timestamp_minutes=480.0,
            carbs_g=50.0,
            protein_g=20.0,
            fat_g=15.0,
            fiber_g=5.0,
            glycemic_index=55.0
        )
        
        assert event.timestamp_minutes == 480.0
        assert event.event_type == EventType.MEAL
        assert event.payload["carbs_g"] == 50.0
        assert event.payload["protein_g"] == 20.0
        assert event.payload["fat_g"] == 15.0
        assert event.payload["fiber_g"] == 5.0
        assert event.payload["glycemic_index"] == 55.0

    def test_create_meal_defaults(self):
        """create_meal should have sensible defaults."""
        from src.core.timeline import Event
        
        event = Event.create_meal(
            timestamp_minutes=480.0,
            carbs_g=50.0
        )
        
        assert event.payload["carbs_g"] == 50.0
        assert event.payload["protein_g"] == 0  # Default
        assert event.payload["fat_g"] == 0  # Default
        assert event.payload["fiber_g"] == 0  # Default
        assert event.payload["glycemic_index"] == 70  # Default


class TestEventEdgeCases:
    """Tests for edge cases and business rules."""

    def test_ingestion_amount_must_be_positive(self):
        """Ingestion amount must be > 0."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "caffeine", "amount": 0.0, "unit": "mg"}
            )

    def test_ingestion_compound_id_not_empty(self):
        """Ingestion compound_id cannot be empty string."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=420.0,
                event_type=EventType.INGESTION,
                payload={"compound_id": "", "amount": 100.0, "unit": "mg"}
            )

    def test_meal_carbs_not_negative(self):
        """Meal carbs_g must be >= 0."""
        from src.core.timeline import Event, EventType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Event(
                timestamp_minutes=480.0,
                event_type=EventType.MEAL,
                payload={"carbs_g": -10.0}
            )

    def test_fractional_timestamp(self):
        """Fractional timestamps should work (e.g., 7:30 = 450.5)."""
        from src.core.timeline import Event, EventType
        
        event = Event(
            timestamp_minutes=450.5,  # 7:30:30 AM
            event_type=EventType.MEAL,
            payload={"carbs_g": 30.0}
        )
        
        assert event.timestamp_minutes == 450.5