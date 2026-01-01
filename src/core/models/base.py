"""
Base classes for MODULUS simulation models.

All simulation models (glucose, caffeine, protein, etc.) inherit from these base classes
to ensure consistent interfaces and behavior.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass
import numpy as np


@dataclass
class ModelParameters:
    """Base class for model parameters"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary"""
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create parameters from dictionary"""
        return cls(**data)


@dataclass
class SimulationResult:
    """Container for simulation results"""
    
    time_points: np.ndarray  # Time points (minutes or hours)
    values: np.ndarray  # Simulated values
    units: str  # Units of measurement
    metadata: Dict[str, Any]  # Additional information
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'time_points': self.time_points.tolist(),
            'values': self.values.tolist(),
            'units': self.units,
            'metadata': self.metadata
        }


class BaseModel(ABC):
    """
    Abstract base class for all metabolic models.
    
    All models (glucose, caffeine, protein) inherit from this class and implement
    the simulate() method.
    """
    
    def __init__(self, parameters: ModelParameters):
        """
        Initialize model with parameters.
        
        Args:
            parameters: Model-specific parameters
        """
        self.parameters = parameters
        self.validated = False
    
    @abstractmethod
    def simulate(self, 
                 inputs: Dict[str, Any], 
                 duration: float,
                 time_step: float = 1.0) -> SimulationResult:
        """
        Run the simulation.
        
        Args:
            inputs: Model-specific inputs (e.g., meal composition, dose)
            duration: Simulation duration (minutes or hours)
            time_step: Time step for output (minutes or hours)
            
        Returns:
            SimulationResult with time series data
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate model parameters against literature benchmarks.
        
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    def get_peak(self, result: SimulationResult) -> tuple[float, float]:
        """
        Extract peak value and time from simulation result.
        
        Args:
            result: Simulation result
            
        Returns:
            Tuple of (peak_time, peak_value)
        """
        peak_idx = np.argmax(result.values)
        return result.time_points[peak_idx], result.values[peak_idx]
    
    def get_auc(self, result: SimulationResult, 
                start_time: float = 0, 
                end_time: float = None) -> float:
        """
        Calculate area under curve.
        
        Args:
            result: Simulation result
            start_time: Start time for AUC calculation
            end_time: End time (None = use full duration)
            
        Returns:
            AUC value
        """
        if end_time is None:
            end_time = result.time_points[-1]
        
        mask = (result.time_points >= start_time) & (result.time_points <= end_time)
        time_subset = result.time_points[mask]
        values_subset = result.values[mask]
        
        return np.trapz(values_subset, time_subset)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(validated={self.validated})"


@dataclass
class PersonParameters:
    """
    Parameters for a virtual individual.
    
    These are sampled from population distributions and used to personalize
    model parameters.
    """
    
    # Demographics
    age: float  # years
    sex: str  # 'male' or 'female'
    weight: float  # kg
    height: float  # cm
    bmi: float  # kg/m^2
    
    # Metabolic
    fasting_glucose: float  # mg/dL
    fasting_insulin: float  # μU/mL
    insulin_sensitivity: float  # dimensionless (1.0 = normal)
    
    # Genotypes
    cyp1a2_genotype: str  # 'slow', 'normal', or 'fast'
    
    # Lifestyle
    physical_activity: str  # 'sedentary', 'light', 'moderate', 'vigorous'
    caffeine_habituation: float  # mg/day
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.__dict__


class ModelRegistry:
    """Registry of available models"""
    
    _models: Dict[str, type[BaseModel]] = {}
    
    @classmethod
    def register(cls, name: str, model_class: type[BaseModel]):
        """Register a model"""
        cls._models[name] = model_class
    
    @classmethod
    def get_model(cls, name: str) -> type[BaseModel]:
        """Get a model class by name"""
        if name not in cls._models:
            raise ValueError(f"Model '{name}' not registered")
        return cls._models[name]
    
    @classmethod
    def list_models(cls) -> List[str]:
        """List all registered models"""
        return list(cls._models.keys())
