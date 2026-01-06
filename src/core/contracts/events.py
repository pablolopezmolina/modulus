# MODULUS - Event Contract
# 
# Define el contrato para eventos en el timeline.
# Ver CONTRACTS.md, Contract 2.1 para especificación completa.
#
# Un Event representa algo que ocurre en un momento específico:
# - ingestion: Toma de un suplemento/compuesto
# - meal: Comida con macronutrientes
# - exercise: Actividad física
# - sleep: Período de sueño

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class EventType(str, Enum):
    """Tipos de eventos soportados en el timeline."""
    INGESTION = "ingestion"
    MEAL = "meal"
    EXERCISE = "exercise"
    SLEEP = "sleep"


class Event(BaseModel):
    """
    Un evento en el timeline de 24h.
    
    INMUTABLE: Una vez creado, no puede modificarse.
    
    Attributes:
        timestamp_minutes: Minutos desde inicio del día (0-1440)
        event_type: Tipo de evento (ingestion, meal, exercise, sleep)
        payload: Datos específicos del evento según su tipo
        
    Payload por tipo:
        ingestion: {compound_id, amount, unit, form}
        meal: {carbs_g, protein_g, fat_g, fiber_g, glycemic_index}
        exercise: {intensity, duration_minutes, type}
        sleep: {duration_minutes}
    """
    
    timestamp_minutes: float = Field(
        ...,
        ge=0.0,
        le=1440.0,
        description="Minutos desde inicio del día (0 = medianoche, 1440 = fin del día)"
    )
    event_type: EventType = Field(
        ...,
        description="Tipo de evento"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Datos específicos del evento"
    )
    
    model_config = {
        "frozen": True,  # Inmutable
        "extra": "forbid",  # No permite campos extra
    }
    
    @field_validator("timestamp_minutes")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Valida que el timestamp esté en rango válido."""
        if v < 0.0:
            raise ValueError(f"timestamp_minutes must be >= 0, got {v}")
        if v > 1440.0:
            raise ValueError(f"timestamp_minutes must be <= 1440, got {v}")
        return v
    
    @model_validator(mode="after")
    def validate_payload_for_type(self) -> "Event":
        """Valida que el payload contenga los campos requeridos para el tipo."""
        required_fields = {
            EventType.INGESTION: {"compound_id", "amount", "unit", "form"},
            EventType.MEAL: {"carbs_g", "protein_g", "fat_g", "fiber_g", "glycemic_index"},
            EventType.EXERCISE: {"intensity", "duration_minutes"},
            EventType.SLEEP: {"duration_minutes"},
        }
        
        required = required_fields.get(self.event_type, set())
        missing = required - set(self.payload.keys())
        
        if missing:
            raise ValueError(
                f"Event type '{self.event_type.value}' requires fields: {missing}"
            )
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario serializable."""
        return {
            "timestamp_minutes": self.timestamp_minutes,
            "event_type": self.event_type.value,
            "payload": self.payload,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Crea un evento desde un diccionario."""
        return cls(
            timestamp_minutes=data["timestamp_minutes"],
            event_type=EventType(data["event_type"]),
            payload=data["payload"],
        )
    
    def __hash__(self) -> int:
        """Hash para poder usar en sets/dicts."""
        return hash((self.timestamp_minutes, self.event_type, tuple(sorted(self.payload.items()))))
