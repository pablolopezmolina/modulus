import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class SimulationInput:
    duration_minutes: float = 240.0
    time_step_minutes: float = 1.0

    def get_time_vector(self) -> np.ndarray:
        if self.duration_minutes <= 0 or self.time_step_minutes <= 0:
            return np.array([], dtype=float)
        return np.arange(
            0.0,
            float(self.duration_minutes) + float(self.time_step_minutes),
            float(self.time_step_minutes),
            dtype=float,
        )


@dataclass
class SimulationResult:
    time_points: np.ndarray
    channels: Dict[str, np.ndarray]
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_channel(self, name: str) -> Optional[np.ndarray]:
        return self.channels.get(name)


class PhysiologicalModel(ABC):
    @abstractmethod
    def simulate(self, inputs: SimulationInput) -> SimulationResult:
        raise NotImplementedError
