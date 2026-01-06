"""
MODULUS Contracts - Event definitions
Version: 3.0

Events represent things that happen at a point in time:
- Ingestion of a compound
- Meal consumption
- Exercise
- Sleep periods

All Events are IMMUTABLE (frozen=True in Pydantic config).
"""

from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field, model_validator, ConfigDict


class EventType(str, Enum):
    """Types of events that can occur in a timeline."""
    INGESTION = "ingestion"
    MEAL = "meal"
    EXERCISE = "exercise"
    SLEEP = "sleep"


class Event(BaseModel):
    """
    An event that occurs at a specific time in the timeline.

    IMMUTABLE - once created, cannot be modified.

    Constraints:
    - timestamp_minutes must be in [0, 1440] (24 hours)
    - event_type must be a valid EventType
    - payload must contain required fields for the event_type
    """
    model_config = ConfigDict(frozen=True)

    timestamp_minutes: float = Field(
        ...,
        ge=0,
        le=1440,
        description="Minutes from start of day (0-1440)"
    )
    event_type: EventType = Field(..., description="Type of event")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")

    @model_validator(mode="after")
    def validate_payload_for_type(self) -> "Event":
        """Validate that payload matches event_type requirements."""
        if self.event_type == EventType.INGESTION:
            required = {"compound_id", "amount", "unit"}
            missing = required - set(self.payload.keys())
            if missing:
                raise ValueError(f"Ingestion payload missing: {missing}")
            if self.payload["amount"] <= 0:
                raise ValueError("Ingestion amount must be positive")
            if not self.payload["compound_id"]:
                raise ValueError("compound_id cannot be empty")

        elif self.event_type == EventType.MEAL:
            if "carbs_g" not in self.payload:
                raise ValueError("Meal payload requires 'carbs_g'")
            if self.payload["carbs_g"] < 0:
                raise ValueError("carbs_g must be non-negative")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp_minutes": self.timestamp_minutes,
            "event_type": self.event_type.value,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        return cls(
            timestamp_minutes=data["timestamp_minutes"],
            event_type=EventType(data["event_type"]),
            payload=data["payload"],
        )

    @classmethod
    def create_ingestion(
        cls,
        timestamp_minutes: float,
        compound_id: str,
        amount: float,
        unit: str = "mg",
        form: str = "powder",
    ) -> "Event":
        """Factory method for creating ingestion events."""
        return cls(
            timestamp_minutes=timestamp_minutes,
            event_type=EventType.INGESTION,
            payload={
                "compound_id": compound_id,
                "amount": amount,
                "unit": unit,
                "form": form,
            },
        )

    @classmethod
    def create_meal(
        cls,
        timestamp_minutes: float,
        carbs_g: float,
        protein_g: float = 0,
        fat_g: float = 0,
        fiber_g: float = 0,
        glycemic_index: float = 70,
    ) -> "Event":
        """Factory method for creating meal events."""
        return cls(
            timestamp_minutes=timestamp_minutes,
            event_type=EventType.MEAL,
            payload={
                "carbs_g": carbs_g,
                "protein_g": protein_g,
                "fat_g": fat_g,
                "fiber_g": fiber_g,
                "glycemic_index": glycemic_index,
            },
        )
