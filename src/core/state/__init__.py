"""
MODULUS - State Module
Session 2.1: Physiological state representation for 24h simulation

This module provides:
- PhysiologicalState: Immutable snapshot of body state at a moment
- Factory functions for creating states
- Validation constants for physiological ranges

Contract 2.3 compliant.

Example usage:
    from src.core.state import PhysiologicalState, create_fasted_state
    from src.core.population.person import VirtualPerson
    
    person = VirtualPerson.create_reference()
    initial_state = create_fasted_state(person)
    
    # Update state immutably
    new_state = initial_state.with_updates(
        timestamp_minutes=60.0,
        glucose_plasma_mg_dl=150.0,
    )
"""

from src.core.state.state import (
    # Main class
    PhysiologicalState,
    
    # Factory functions
    create_fasted_state,
    create_initial_state,
    
    # Validation ranges (useful for tests and other modules)
    GLUCOSE_RANGE,
    INSULIN_RANGE,
    CAFFEINE_RANGE,
    ALERTNESS_RANGE,
    ADENOSINE_RANGE,
    GLUCOSE_GUT_MIN,
    HOURS_SINCE_MEAL_MIN,
    TIMESTAMP_MIN,
)

__all__ = [
    # Main class
    "PhysiologicalState",
    
    # Factory functions
    "create_fasted_state",
    "create_initial_state",
    
    # Validation ranges
    "GLUCOSE_RANGE",
    "INSULIN_RANGE",
    "CAFFEINE_RANGE",
    "ALERTNESS_RANGE",
    "ADENOSINE_RANGE",
    "GLUCOSE_GUT_MIN",
    "HOURS_SINCE_MEAL_MIN",
    "TIMESTAMP_MIN",
]
