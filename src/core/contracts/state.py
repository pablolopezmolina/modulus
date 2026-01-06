"""
MODULUS Contracts - Physiological State
Version: 3.0

PhysiologicalState represents the state of the body at a single instant.
It is IMMUTABLE - each simulation step creates a NEW state.

This ensures:
- Reproducibility (same input = same output)
- Easy debugging (inspect any past state)
- Safe parallelization (no race conditions)
"""

import math
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PhysiologicalState(BaseModel):
    """
    Snapshot of the body's physiological state at a single instant.

    IMMUTABLE (frozen=True) - every step() creates a NEW state.

    All numerical values must be:
    - Finite (no NaN, no Inf)
    - Within physiological ranges
    """
    model_config = ConfigDict(frozen=True)

    # Timestamp
    timestamp_minutes: float = Field(
        default=0.0,
        ge=0,
        description="Minutes from start of simulation"
    )

    # Glucose System
    glucose_plasma_mg_dl: float = Field(
        default=90.0,
        ge=20,
        le=600,
        description="Plasma glucose (mg/dL). Normal fasting: 70-100"
    )
    insulin_plasma_mu_l: float = Field(
        default=10.0,
        ge=0,
        le=500,
        description="Plasma insulin (mU/L). Normal fasting: 5-15"
    )
    glucose_gut_mg: float = Field(
        default=0.0,
        ge=0,
        description="Glucose pending absorption in gut (mg)"
    )

    # Caffeine System
    caffeine_plasma_mg_l: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Plasma caffeine (mg/L). Toxic >20mg/L"
    )
    adenosine_receptor_occupancy: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Fraction of adenosine receptors blocked (0-1)"
    )
    alertness_score: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Subjective alertness (0-100%)"
    )

    # Metabolic context
    is_fasted: bool = Field(
        default=True,
        description="Whether in fasted state (>4h since meal)"
    )
    hours_since_last_meal: float = Field(
        default=12.0,
        ge=0,
        description="Hours since last meal"
    )

    @field_validator(
        "timestamp_minutes",
        "glucose_plasma_mg_dl",
        "insulin_plasma_mu_l",
        "glucose_gut_mg",
        "caffeine_plasma_mg_l",
        "adenosine_receptor_occupancy",
        "alertness_score",
        "hours_since_last_meal",
        mode="after"
    )
    @classmethod
    def validate_finite(cls, v: float) -> float:
        """Ensure all numerical values are finite (not NaN or Inf)."""
        if not math.isfinite(v):
            raise ValueError(f"Value must be finite, got {v}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump()

    @classmethod
    def create_fasted(
        cls,
        timestamp_minutes: float = 0.0,
        fasting_glucose: float = 90.0,
        fasting_insulin: float = 10.0,
    ) -> "PhysiologicalState":
        """
        Factory method to create a fasted state (typical morning).
        """
        return cls(
            timestamp_minutes=timestamp_minutes,
            glucose_plasma_mg_dl=fasting_glucose,
            insulin_plasma_mu_l=fasting_insulin,
            glucose_gut_mg=0.0,
            caffeine_plasma_mg_l=0.0,
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,
            is_fasted=True,
            hours_since_last_meal=12.0,
        )

    def with_updates(self, **kwargs) -> "PhysiologicalState":
        """
        Create a new state with some fields updated.

        Since PhysiologicalState is frozen, this returns a NEW instance.
        """
        data = self.model_dump()
        data.update(kwargs)
        return PhysiologicalState(**data)
