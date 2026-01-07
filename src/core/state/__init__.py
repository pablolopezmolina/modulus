"""
State module for MODULUS.

This module provides:
- PhysiologicalState: Immutable snapshot of body state at a moment
- StateIntegrator: Advances state through time using physiological models
- Factory functions for creating states
- Validation constants for physiological ranges

Contract 2.3 (PhysiologicalState):
- All numeric values MUST be finite (no NaN, no Inf)
- All values MUST be in physiological ranges
- timestamp_minutes MUST be >= 0

Contract 2.4 (StateIntegrator):
- step() ALWAYS returns a valid PhysiologicalState
- If error, returns previous state + logs warning
- simulate_timeline() returns states for t=0, dt, 2*dt, ..., 1440
"""

from src.core.state.state import (
    PhysiologicalState,
    create_fasted_state,
    create_initial_state,
    # Validation range constants
    GLUCOSE_RANGE,
    INSULIN_RANGE,
    CAFFEINE_RANGE,
    ALERTNESS_RANGE,
    ADENOSINE_RANGE,
    GLUCOSE_GUT_MIN,
    HOURS_SINCE_MEAL_MIN,
    TIMESTAMP_MIN,
)
from src.core.state.integrator import StateIntegrator

__all__ = [
    # Main classes
    "PhysiologicalState",
    "StateIntegrator",
    # Factory functions
    "create_fasted_state",
    "create_initial_state",
    # Validation constants
    "GLUCOSE_RANGE",
    "INSULIN_RANGE",
    "CAFFEINE_RANGE",
    "ALERTNESS_RANGE",
    "ADENOSINE_RANGE",
    "GLUCOSE_GUT_MIN",
    "HOURS_SINCE_MEAL_MIN",
    "TIMESTAMP_MIN",
]
