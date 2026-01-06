"""
MODULUS Contracts - Simulation Results
Version: 3.0

SimulationResult contains the output of a physiological model simulation.
All results must satisfy strict contracts for downstream consumers.
"""

import math
from typing import Dict, Any, List, Optional
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class SimulationResult(BaseModel):
    """
    Result of a physiological model simulation.

    CONTRACTS:
    - time_points must be monotonically increasing
    - time_points[0] must be 0.0
    - All channels must have len(channel) == len(time_points)
    - metrics must include at least {"is_valid": bool}
    - No NaN or Inf values in any channel
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    time_points: List[float] = Field(
        ...,
        min_length=1,
        description="Time points in minutes, monotonically increasing, starting at 0"
    )
    channels: Dict[str, List[float]] = Field(
        ...,
        description="Named time series data, each with same length as time_points"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scalar metrics computed from the simulation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the simulation"
    )

    @field_validator("time_points", mode="after")
    @classmethod
    def validate_time_points(cls, v: List[float]) -> List[float]:
        """Validate time_points contract."""
        if len(v) == 0:
            raise ValueError("time_points cannot be empty")

        # Must start at 0
        if v[0] != 0.0:
            raise ValueError(f"time_points must start at 0.0, got {v[0]}")

        # Must be monotonically increasing
        for i in range(1, len(v)):
            if v[i] <= v[i-1]:
                raise ValueError(
                    f"time_points must be monotonically increasing. "
                    f"Found {v[i]} <= {v[i-1]} at index {i}"
                )

        # No NaN or Inf
        for i, val in enumerate(v):
            if not math.isfinite(val):
                raise ValueError(f"time_points[{i}] is not finite: {val}")

        return v

    @model_validator(mode="after")
    def validate_channels_and_metrics(self) -> "SimulationResult":
        """Validate channels have correct length and add is_valid if missing."""
        expected_len = len(self.time_points)

        for name, channel in self.channels.items():
            if len(channel) != expected_len:
                raise ValueError(
                    f"Channel '{name}' has length {len(channel)}, "
                    f"expected {expected_len}"
                )
            for i, val in enumerate(channel):
                if not math.isfinite(val):
                    raise ValueError(f"Channel '{name}'[{i}] is not finite: {val}")

        # Add is_valid if not present
        if "is_valid" not in self.metrics and "is_sim_valid" not in self.metadata:
            # Create new dict with is_valid
            new_metrics = dict(self.metrics)
            new_metrics["is_valid"] = True
            object.__setattr__(self, "metrics", new_metrics)

        return self

    def get_channel(self, name: str) -> Optional[List[float]]:
        """Get a channel by name, returns None if not found."""
        return self.channels.get(name)

    def get_channel_as_array(self, name: str) -> Optional[np.ndarray]:
        """Get a channel as numpy array."""
        channel = self.channels.get(name)
        if channel is not None:
            return np.array(channel)
        return None

    @property
    def time_array(self) -> np.ndarray:
        """Get time_points as numpy array."""
        return np.array(self.time_points)

    @property
    def duration_minutes(self) -> float:
        """Total duration of simulation in minutes."""
        return self.time_points[-1] - self.time_points[0]

    @property
    def is_valid(self) -> bool:
        """Whether the simulation completed successfully."""
        return self.metrics.get("is_valid", True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump()

    @classmethod
    def from_arrays(
        cls,
        time_points: np.ndarray,
        channels: Dict[str, np.ndarray],
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SimulationResult":
        """Create SimulationResult from numpy arrays."""
        return cls(
            time_points=time_points.tolist(),
            channels={k: v.tolist() for k, v in channels.items()},
            metrics=metrics or {"is_valid": True},
            metadata=metadata or {},
        )
