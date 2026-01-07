"""
MODULUS - PhysiologicalState Implementation
Session 2.1: State representation for 24h timeline simulation

Contract 2.3 compliant implementation with factory methods and helpers.
Extends the base PhysiologicalState from contracts/state.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from src.core.population.person import VirtualPerson


# =============================================================================
# VALIDATION RANGES (physiologically plausible)
# =============================================================================

# Glucose: 20-600 mg/dL (from severe hypoglycemia to extreme hyperglycemia)
GLUCOSE_RANGE = (20.0, 600.0)

# Insulin: 0-1000 mU/L (from zero to hyperinsulinemia)
INSULIN_RANGE = (0.0, 1000.0)

# Caffeine: 0-100 mg/L (0 to lethal dose territory)
CAFFEINE_RANGE = (0.0, 100.0)

# Alertness: 0-100% (asleep to fully alert)
ALERTNESS_RANGE = (0.0, 100.0)

# Adenosine receptor occupancy: 0-1 (none to full)
ADENOSINE_RANGE = (0.0, 1.0)

# Glucose gut: >= 0 (can't be negative)
GLUCOSE_GUT_MIN = 0.0

# Hours since last meal: >= 0
HOURS_SINCE_MEAL_MIN = 0.0

# Timestamp: >= 0 (no negative time)
TIMESTAMP_MIN = 0.0


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def _validate_finite(value: float, name: str) -> None:
    """Validate that a value is finite (not NaN or Inf)."""
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")


def _validate_range(value: float, name: str, min_val: float, max_val: float) -> None:
    """Validate that a value is within range [min_val, max_val]."""
    _validate_finite(value, name)
    if value < min_val or value > max_val:
        raise ValueError(
            f"{name} must be in range [{min_val}, {max_val}], got {value}"
        )


def _validate_min(value: float, name: str, min_val: float) -> None:
    """Validate that a value is >= min_val."""
    _validate_finite(value, name)
    if value < min_val:
        raise ValueError(f"{name} must be >= {min_val}, got {value}")


# =============================================================================
# PHYSIOLOGICAL STATE
# =============================================================================

@dataclass(frozen=True)
class PhysiologicalState:
    """
    Immutable snapshot of the body's physiological state at a moment in time.
    
    Contract 2.3 compliant:
    - All numeric values must be finite (not NaN, not Inf)
    - All values must be in physiologically plausible ranges
    - timestamp_minutes must be >= 0
    
    This is the "bus" for communication between physiological systems.
    Each simulation step creates a NEW state (immutability).
    
    Attributes:
        timestamp_minutes: Minutes since start of day (0 = midnight)
        
        Glucose System:
            glucose_plasma_mg_dl: Plasma glucose concentration
            insulin_plasma_mu_l: Plasma insulin concentration
            glucose_gut_mg: Glucose in gut pending absorption
        
        Caffeine System:
            caffeine_plasma_mg_l: Plasma caffeine concentration
            adenosine_receptor_occupancy: Fraction of adenosine receptors blocked (0-1)
            alertness_score: Subjective alertness (0-100%)
        
        Metadata:
            is_fasted: Whether person is in fasted state
            hours_since_last_meal: Hours since last meal
    """
    
    # Timestamp
    timestamp_minutes: float
    
    # Glucose System
    glucose_plasma_mg_dl: float
    insulin_plasma_mu_l: float
    glucose_gut_mg: float
    
    # Caffeine System
    caffeine_plasma_mg_l: float
    adenosine_receptor_occupancy: float
    alertness_score: float
    
    # Metadata
    is_fasted: bool
    hours_since_last_meal: float
    
    def __post_init__(self) -> None:
        """Validate all fields after initialization."""
        # Timestamp validation
        _validate_min(self.timestamp_minutes, "timestamp_minutes", TIMESTAMP_MIN)
        
        # Glucose system validation
        _validate_range(
            self.glucose_plasma_mg_dl, "glucose_plasma_mg_dl",
            GLUCOSE_RANGE[0], GLUCOSE_RANGE[1]
        )
        _validate_range(
            self.insulin_plasma_mu_l, "insulin_plasma_mu_l",
            INSULIN_RANGE[0], INSULIN_RANGE[1]
        )
        _validate_min(self.glucose_gut_mg, "glucose_gut_mg", GLUCOSE_GUT_MIN)
        
        # Caffeine system validation
        _validate_range(
            self.caffeine_plasma_mg_l, "caffeine_plasma_mg_l",
            CAFFEINE_RANGE[0], CAFFEINE_RANGE[1]
        )
        _validate_range(
            self.adenosine_receptor_occupancy, "adenosine_receptor_occupancy",
            ADENOSINE_RANGE[0], ADENOSINE_RANGE[1]
        )
        _validate_range(
            self.alertness_score, "alertness_score",
            ALERTNESS_RANGE[0], ALERTNESS_RANGE[1]
        )
        
        # Metadata validation
        _validate_min(
            self.hours_since_last_meal, "hours_since_last_meal",
            HOURS_SINCE_MEAL_MIN
        )
    
    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================
    
    @property
    def time_hours(self) -> float:
        """Timestamp in hours (convenience)."""
        return self.timestamp_minutes / 60.0
    
    @property
    def is_hypoglycemic(self) -> bool:
        """True if glucose < 70 mg/dL (clinical hypoglycemia threshold)."""
        return self.glucose_plasma_mg_dl < 70.0
    
    @property
    def is_hyperglycemic(self) -> bool:
        """True if glucose > 140 mg/dL (postprandial hyperglycemia threshold)."""
        return self.glucose_plasma_mg_dl > 140.0
    
    @property
    def has_caffeine(self) -> bool:
        """True if caffeine level is meaningful (> 0.1 mg/L)."""
        return self.caffeine_plasma_mg_l > 0.1
    
    # =========================================================================
    # IMMUTABLE UPDATE
    # =========================================================================
    
    def with_updates(self, **kwargs: Any) -> PhysiologicalState:
        """
        Create a new state with some fields updated.
        
        This is the primary way to create modified states while maintaining
        immutability. The new state is validated.
        
        Args:
            **kwargs: Fields to update (e.g., glucose_plasma_mg_dl=120.0)
        
        Returns:
            New PhysiologicalState with updates applied
            
        Raises:
            ValueError: If updated state would be invalid
        """
        current = asdict(self)
        current.update(kwargs)
        return PhysiologicalState(**current)
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhysiologicalState:
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_fasted_state(
    person: "VirtualPerson",
    timestamp_minutes: float = 0.0,
    hours_since_last_meal: float = 8.0,
    baseline_alertness: float = 50.0,
) -> PhysiologicalState:
    """
    Create a fasted state for a person.
    
    Uses the person's fasting glucose and insulin levels.
    Assumes no caffeine and no food in gut.
    
    Args:
        person: VirtualPerson to create state for
        timestamp_minutes: Time of day (default 0 = midnight)
        hours_since_last_meal: Hours since last meal (default 8 = overnight)
        baseline_alertness: Baseline alertness score (default 50%)
    
    Returns:
        PhysiologicalState representing fasted condition
    """
    return PhysiologicalState(
        timestamp_minutes=timestamp_minutes,
        glucose_plasma_mg_dl=person.fasting_glucose_mg_dl,
        insulin_plasma_mu_l=person.fasting_insulin_mu_l,
        glucose_gut_mg=0.0,
        caffeine_plasma_mg_l=0.0,
        adenosine_receptor_occupancy=0.0,
        alertness_score=baseline_alertness,
        is_fasted=True,
        hours_since_last_meal=hours_since_last_meal,
    )


def create_initial_state(
    person: "VirtualPerson",
    timestamp_minutes: float = 0.0,
    include_baseline_caffeine: bool = False,
) -> PhysiologicalState:
    """
    Create the initial state for starting a simulation.
    
    By default, this is equivalent to create_fasted_state.
    Can optionally include baseline caffeine for habitual users.
    
    Args:
        person: VirtualPerson to create state for
        timestamp_minutes: Starting time (default 0)
        include_baseline_caffeine: Whether to include baseline caffeine
                                   for habitual users (default False)
    
    Returns:
        PhysiologicalState for simulation start
    """
    # For now, initial state is fasted state
    # Future: could model circadian variations in baseline
    
    caffeine_level = 0.0
    adenosine_occupancy = 0.0
    
    if include_baseline_caffeine and person.habitual_caffeine_mg > 0:
        # Habitual users might have some baseline, but we start clean
        # This could be extended to model residual caffeine from previous day
        caffeine_level = 0.0
        adenosine_occupancy = 0.0
    
    return PhysiologicalState(
        timestamp_minutes=timestamp_minutes,
        glucose_plasma_mg_dl=person.fasting_glucose_mg_dl,
        insulin_plasma_mu_l=person.fasting_insulin_mu_l,
        glucose_gut_mg=0.0,
        caffeine_plasma_mg_l=caffeine_level,
        adenosine_receptor_occupancy=adenosine_occupancy,
        alertness_score=50.0,  # Baseline alertness
        is_fasted=True,
        hours_since_last_meal=8.0,  # Default overnight fast
    )
