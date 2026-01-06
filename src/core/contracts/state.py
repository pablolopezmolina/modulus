# MODULUS - PhysiologicalState Contract
# 
# Define el contrato para el estado fisiológico del cuerpo.
# Ver CONTRACTS.md, Contract 2.3 para especificación completa.
#
# PhysiologicalState representa un "snapshot" del estado del cuerpo
# en un instante específico. Es INMUTABLE - cada step de simulación
# crea un NUEVO estado.

import math
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator


class PhysiologicalState(BaseModel):
    """
    Estado fisiológico del cuerpo en un instante.
    
    INMUTABLE: Cada step() de simulación crea un nuevo estado.
    
    Attributes:
        timestamp_minutes: Minutos desde inicio del día
        
        # Sistema Glucosa
        glucose_plasma_mg_dl: Glucosa plasmática (mg/dL)
        insulin_plasma_mu_l: Insulina plasmática (mU/L)
        glucose_gut_mg: Glucosa pendiente de absorber en intestino (mg)
        
        # Sistema Cafeína
        caffeine_plasma_mg_l: Cafeína plasmática (mg/L)
        adenosine_receptor_occupancy: Ocupación de receptores de adenosina (0-1)
        alertness_score: Puntuación de alerta (0-100)
        
        # Metadata
        is_fasted: Si está en ayunas
        hours_since_last_meal: Horas desde última comida
    """
    
    # Timestamp
    timestamp_minutes: float = Field(
        ...,
        ge=0.0,
        description="Minutos desde inicio del día"
    )
    
    # Sistema Glucosa
    glucose_plasma_mg_dl: float = Field(
        ...,
        description="Glucosa plasmática en mg/dL"
    )
    insulin_plasma_mu_l: float = Field(
        ...,
        ge=0.0,
        description="Insulina plasmática en mU/L"
    )
    glucose_gut_mg: float = Field(
        ...,
        ge=0.0,
        description="Glucosa en intestino pendiente de absorber (mg)"
    )
    
    # Sistema Cafeína
    caffeine_plasma_mg_l: float = Field(
        ...,
        ge=0.0,
        description="Cafeína plasmática en mg/L"
    )
    adenosine_receptor_occupancy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fracción de receptores de adenosina ocupados por cafeína (0-1)"
    )
    alertness_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Puntuación de alerta/vigilancia (0-100)"
    )
    
    # Metadata
    is_fasted: bool = Field(
        ...,
        description="True si no ha comido en las últimas horas"
    )
    hours_since_last_meal: float = Field(
        ...,
        ge=0.0,
        description="Horas transcurridas desde la última comida"
    )
    
    model_config = {
        "frozen": True,  # Inmutable
        "extra": "forbid",  # No permite campos extra
    }
    
    @field_validator("timestamp_minutes")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Timestamp debe ser >= 0."""
        if v < 0.0:
            raise ValueError(f"timestamp_minutes must be >= 0, got {v}")
        return v
    
    @field_validator("glucose_plasma_mg_dl")
    @classmethod
    def validate_glucose(cls, v: float) -> float:
        """
        Glucosa debe estar en rango fisiológico.
        
        Rangos:
        - 20 mg/dL: Hipoglucemia severa (coma)
        - 70-100: Normal en ayunas
        - 140: Límite post-prandial normal
        - 600: Hiperglucemia severa (cetoacidosis)
        """
        if math.isnan(v):
            raise ValueError("glucose_plasma_mg_dl cannot be NaN")
        if math.isinf(v):
            raise ValueError("glucose_plasma_mg_dl cannot be infinite")
        if v < 20.0:
            raise ValueError(f"glucose_plasma_mg_dl must be >= 20 mg/dL (severe hypoglycemia limit), got {v}")
        if v > 600.0:
            raise ValueError(f"glucose_plasma_mg_dl must be <= 600 mg/dL (severe hyperglycemia limit), got {v}")
        return v
    
    @field_validator("insulin_plasma_mu_l")
    @classmethod
    def validate_insulin(cls, v: float) -> float:
        """Insulina debe ser finita y no negativa."""
        if math.isnan(v):
            raise ValueError("insulin_plasma_mu_l cannot be NaN")
        if math.isinf(v):
            raise ValueError("insulin_plasma_mu_l cannot be infinite")
        if v < 0.0:
            raise ValueError(f"insulin_plasma_mu_l must be >= 0, got {v}")
        return v
    
    @field_validator("caffeine_plasma_mg_l")
    @classmethod
    def validate_caffeine(cls, v: float) -> float:
        """Cafeína debe ser finita y no negativa."""
        if math.isnan(v):
            raise ValueError("caffeine_plasma_mg_l cannot be NaN")
        if math.isinf(v):
            raise ValueError("caffeine_plasma_mg_l cannot be infinite")
        return v
    
    @field_validator("adenosine_receptor_occupancy")
    @classmethod
    def validate_receptor_occupancy(cls, v: float) -> float:
        """Ocupación de receptores debe estar en [0, 1]."""
        if math.isnan(v):
            raise ValueError("adenosine_receptor_occupancy cannot be NaN")
        if v < 0.0 or v > 1.0:
            raise ValueError(f"adenosine_receptor_occupancy must be in [0, 1], got {v}")
        return v
    
    @field_validator("alertness_score")
    @classmethod
    def validate_alertness(cls, v: float) -> float:
        """Alertness debe estar en [0, 100]."""
        if math.isnan(v):
            raise ValueError("alertness_score cannot be NaN")
        if v < 0.0 or v > 100.0:
            raise ValueError(f"alertness_score must be in [0, 100], got {v}")
        return v
    
    @classmethod
    def create_fasted_default(cls) -> "PhysiologicalState":
        """
        Factory method: crea un estado inicial en ayunas típico.
        
        Usado para inicializar simulaciones cuando no hay VirtualPerson.
        Valores basados en adulto sano promedio en ayunas.
        """
        return cls(
            timestamp_minutes=0.0,
            glucose_plasma_mg_dl=90.0,  # Normal en ayunas
            insulin_plasma_mu_l=8.0,     # Normal en ayunas
            glucose_gut_mg=0.0,          # Sin comida pendiente
            caffeine_plasma_mg_l=0.0,    # Sin cafeína
            adenosine_receptor_occupancy=0.0,
            alertness_score=50.0,        # Alerta basal
            is_fasted=True,
            hours_since_last_meal=8.0,   # Ayuno nocturno típico
        )
    
    def with_updates(self, **kwargs) -> "PhysiologicalState":
        """
        Crea un NUEVO estado con algunos valores actualizados.
        
        Como el estado es inmutable, este método es el patrón
        para "modificar" el estado.
        
        Example:
            new_state = old_state.with_updates(
                timestamp_minutes=old_state.timestamp_minutes + 1,
                glucose_plasma_mg_dl=95.0
            )
        """
        data = self.model_dump()
        data.update(kwargs)
        return PhysiologicalState(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el estado a diccionario serializable."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhysiologicalState":
        """Crea un estado desde un diccionario."""
        return cls(**data)
