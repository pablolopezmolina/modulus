# MODULUS - SimulationResult Contract
# 
# Define el contrato para resultados de simulación.
# Ver CONTRACTS.md, Contract 1.1 para especificación completa.
#
# SimulationResult es el output de cualquier modelo fisiológico.
# Contiene series temporales (channels) y métricas agregadas.

import numpy as np
from typing import Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator


class SimulationResult(BaseModel):
    """
    Resultado de una simulación fisiológica.
    
    Contiene:
    - time_points: Array de tiempos (debe empezar en 0, ser monotónico)
    - channels: Dict de series temporales (glucosa, insulina, etc.)
    - metrics: Métricas escalares (peak, AUC, etc.)
    - metadata: Info adicional (modelo, versión, etc.)
    
    CONTRATOS:
    - time_points[0] DEBE ser 0.0
    - time_points DEBE ser monotónicamente creciente
    - Todos los channels DEBEN tener len(channel) == len(time_points)
    - metrics DEBE incluir "is_valid"
    - Si is_valid=False, channels pueden estar vacíos
    - Ningún channel puede contener NaN o Inf
    """
    
    time_points: np.ndarray = Field(
        ...,
        description="Array de puntos temporales (minutos)"
    )
    channels: Dict[str, np.ndarray] = Field(
        ...,
        description="Series temporales por nombre (glucose, insulin, etc.)"
    )
    metrics: Dict[str, Any] = Field(
        ...,
        description="Métricas escalares calculadas"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Información adicional (modelo, versión, etc.)"
    )
    
    model_config = {
        "arbitrary_types_allowed": True,  # Permite np.ndarray
        "frozen": True,  # Inmutable
    }
    
    @field_validator("time_points", mode="before")
    @classmethod
    def convert_time_points(cls, v) -> np.ndarray:
        """Convierte a numpy array si no lo es."""
        if not isinstance(v, np.ndarray):
            v = np.array(v, dtype=np.float64)
        return v
    
    @field_validator("channels", mode="before")
    @classmethod
    def convert_channels(cls, v) -> Dict[str, np.ndarray]:
        """Convierte valores de channels a numpy arrays."""
        result = {}
        for key, value in v.items():
            if not isinstance(value, np.ndarray):
                result[key] = np.array(value, dtype=np.float64)
            else:
                result[key] = value
        return result
    
    @model_validator(mode="after")
    def validate_result(self) -> "SimulationResult":
        """Valida todas las invariantes del resultado."""
        
        # 1. time_points debe empezar en 0
        if len(self.time_points) > 0 and self.time_points[0] != 0.0:
            raise ValueError(
                f"time_points must start at 0, got {self.time_points[0]}"
            )
        
        # 2. time_points debe ser monotónicamente creciente
        if len(self.time_points) > 1:
            diffs = np.diff(self.time_points)
            if not np.all(diffs > 0):
                raise ValueError(
                    "time_points must be monotonically increasing"
                )
        
        # 3. metrics debe tener is_valid
        if "is_valid" not in self.metrics:
            raise ValueError(
                "metrics must include 'is_valid' key"
            )
        
        # 4. Si is_valid=True, validar channels
        if self.metrics.get("is_valid", False):
            n_points = len(self.time_points)
            
            for name, channel in self.channels.items():
                # 4a. Longitud correcta
                if len(channel) != n_points:
                    raise ValueError(
                        f"Channel '{name}' has length {len(channel)}, "
                        f"expected {n_points} (same as time_points)"
                    )
                
                # 4b. No NaN
                if np.any(np.isnan(channel)):
                    raise ValueError(
                        f"Channel '{name}' contains NaN values"
                    )
                
                # 4c. No Inf
                if np.any(np.isinf(channel)):
                    raise ValueError(
                        f"Channel '{name}' contains infinite values"
                    )
        
        return self
    
    def get_channel(self, name: str) -> np.ndarray:
        """Obtiene un channel por nombre."""
        if name not in self.channels:
            raise KeyError(f"Channel '{name}' not found. Available: {list(self.channels.keys())}")
        return self.channels[name]
    
    def get_metric(self, name: str, default: Any = None) -> Any:
        """Obtiene una métrica por nombre."""
        return self.metrics.get(name, default)
    
    @property
    def is_valid(self) -> bool:
        """Shortcut para metrics['is_valid']."""
        return self.metrics.get("is_valid", False)
    
    @property
    def duration_minutes(self) -> float:
        """Duración total de la simulación en minutos."""
        if len(self.time_points) == 0:
            return 0.0
        return float(self.time_points[-1] - self.time_points[0])
    
    @property
    def n_points(self) -> int:
        """Número de puntos temporales."""
        return len(self.time_points)
    
    @property
    def channel_names(self) -> List[str]:
        """Lista de nombres de channels disponibles."""
        return list(self.channels.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario serializable (para JSON).
        
        Los numpy arrays se convierten a listas.
        """
        return {
            "time_points": self.time_points.tolist(),
            "channels": {k: v.tolist() for k, v in self.channels.items()},
            "metrics": self.metrics,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationResult":
        """Crea un resultado desde un diccionario."""
        return cls(
            time_points=np.array(data["time_points"]),
            channels={k: np.array(v) for k, v in data["channels"].items()},
            metrics=data["metrics"],
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def create_invalid(cls, error: str) -> "SimulationResult":
        """
        Factory method: crea un resultado inválido.
        
        Usado cuando una simulación falla pero queremos
        devolver un objeto consistente.
        """
        return cls(
            time_points=np.array([0.0]),
            channels={},
            metrics={"is_valid": False, "error": error},
            metadata={},
        )
