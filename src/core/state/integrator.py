"""
StateIntegrator - Session 2.2 + 2.3

Contract 2.4 compliance:
- step() ALWAYS returns a valid PhysiologicalState
- If error occurs, returns previous state + logs warning
- Integrates glucose and caffeine models
- simulate_timeline() returns states for t=0, dt, 2*dt, ..., 1440

The StateIntegrator is the bridge between:
- Timeline/Events (what happens during the day)
- Models (how the body responds)
- State (snapshot of body at any moment)
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Protocol, Union, runtime_checkable, TYPE_CHECKING

import numpy as np

from src.core.state.state import PhysiologicalState

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from src.core.timeline.timeline import Timeline


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# PROTOCOLS FOR TYPE HINTS
# =============================================================================

@runtime_checkable
class PhysiologicalModel(Protocol):
    """Protocol for physiological models (Contract 1.1)."""
    
    def simulate(
        self,
        duration_minutes: float,
        time_step_minutes: float = 1.0,
        **kwargs
    ) -> Any:
        """Run a simulation and return SimulationResult."""
        ...


@runtime_checkable
class PersonLike(Protocol):
    """Protocol for VirtualPerson-like objects."""
    
    weight_kg: float
    fasting_glucose_mg_dl: float
    fasting_insulin_mu_l: float
    caffeine_half_life_h: float


@runtime_checkable  
class EventLike(Protocol):
    """Protocol for Event-like objects."""
    
    timestamp_minutes: float
    event_type: str
    payload: Dict[str, Any]


# =============================================================================
# CONSTANTS
# =============================================================================

# Fasting threshold in hours
FASTING_THRESHOLD_HOURS = 10.0

# Caffeine parameters
DEFAULT_VD_L_PER_KG = 0.5  # Volume of distribution (L/kg)
DEFAULT_KA = 0.05  # Absorption rate constant (1/min) ~20 min to peak

# Glucose absorption rate (mg/min at peak)
DEFAULT_GLUCOSE_ABSORPTION_RATE = 500.0  # mg/min from gut

# Alertness parameters (Emax model)
ALERTNESS_BASELINE = 50.0
ALERTNESS_EMAX = 40.0  # Max additional alertness from caffeine
CAFFEINE_EC50 = 1.5  # mg/L for 50% max effect

# Simulation constants
TOTAL_DAY_MINUTES = 1440.0  # 24 hours


# =============================================================================
# STATE INTEGRATOR
# =============================================================================

class StateIntegrator:
    """
    Integrates physiological models to advance state through time.
    
    Contract 2.4:
    - step() ALWAYS returns a valid PhysiologicalState
    - If error, returns previous state + logs warning
    - Handles "meal" and "ingestion" events
    - simulate_timeline() returns states for t=0, dt, 2*dt, ..., 1440
    
    Example:
        person = VirtualPerson.create_reference()
        integrator = StateIntegrator(person, glucose_model, caffeine_model)
        
        state = PhysiologicalState.create_fasted_state()
        for event in timeline:
            events_at_t = [e for e in timeline if e.timestamp_minutes == t]
            state = integrator.step(state, events_at_t, dt_minutes=1.0)
    """
    
    def __init__(
        self,
        person: PersonLike,
        glucose_model: Optional[PhysiologicalModel] = None,
        caffeine_model: Optional[PhysiologicalModel] = None,
        models: Optional[Dict[str, PhysiologicalModel]] = None
    ):
        """
        Initialize the StateIntegrator.
        
        Args:
            person: VirtualPerson with metabolic parameters
            glucose_model: DallaManModel instance (optional if using models dict)
            caffeine_model: EliteCaffeineModel instance (optional if using models dict)
            models: Dict mapping model names to model instances (alternative to individual args)
        
        The models dict approach matches Contract 2.4 signature:
            models = {"glucose": glucose_model, "caffeine": caffeine_model}
        """
        self.person = person
        
        # Handle both initialization styles
        if models is not None:
            self.glucose_model = models.get("glucose")
            self.caffeine_model = models.get("caffeine")
        else:
            self.glucose_model = glucose_model
            self.caffeine_model = caffeine_model
        
        # Track pending doses (for multi-step absorption)
        self._pending_caffeine_mg: float = 0.0
        self._pending_glucose_mg: float = 0.0  # In addition to glucose_gut
    
    def step(
        self,
        current_state: PhysiologicalState,
        events: List[EventLike],
        dt_minutes: float
    ) -> PhysiologicalState:
        """
        Advance the physiological state by dt_minutes.
        
        Contract 2.4:
        - ALWAYS returns a valid PhysiologicalState
        - If error, returns previous state + logs warning
        
        Args:
            current_state: Current PhysiologicalState
            events: List of events occurring at this timestep
            dt_minutes: Time step in minutes
        
        Returns:
            New PhysiologicalState at time = current_time + dt_minutes
        """
        try:
            # Process events first (adds to pending pools)
            new_state_dict = self._process_events(current_state, events, dt_minutes)
            
            # Advance glucose dynamics
            new_state_dict = self._step_glucose(current_state, new_state_dict, dt_minutes)
            
            # Advance caffeine dynamics
            new_state_dict = self._step_caffeine(current_state, new_state_dict, dt_minutes)
            
            # Update time-based fields
            new_state_dict = self._step_time_tracking(current_state, new_state_dict, events, dt_minutes)
            
            # Update timestamp
            new_state_dict["timestamp_minutes"] = current_state.timestamp_minutes + dt_minutes
            
            # Create new state (uses with_updates for immutability)
            new_state = current_state.with_updates(**new_state_dict)
            
            return new_state
            
        except Exception as e:
            # Contract 2.4: If error, return previous state + log warning
            logger.warning(f"Error in step(): {e}. Returning previous state.")
            warnings.warn(f"StateIntegrator.step() error: {e}")
            
            # Return state with only timestamp advanced (minimal change)
            try:
                return current_state.with_updates(
                    timestamp_minutes=current_state.timestamp_minutes + dt_minutes
                )
            except Exception:
                # If even that fails, return the original state
                return current_state
    
    def simulate_timeline(
        self,
        initial_state: PhysiologicalState,
        timeline: "Timeline",
        dt_minutes: float = 1.0
    ) -> List[PhysiologicalState]:
        """
        Simulate a full 24-hour period.
        
        Contract 2.4:
        - Returns states for t=0, dt, 2*dt, ..., 1440
        - Uses step() internally for each timestep
        - Applies events when their timestamp falls within the current step
        
        Args:
            initial_state: Starting physiological state (will be adjusted to t=0)
            timeline: Timeline of events for the day
            dt_minutes: Time step size in minutes (default 1.0)
            
        Returns:
            List of PhysiologicalState, one per timestep
            Length = int(1440 / dt_minutes) + 1
            
        Example:
            timeline = Timeline().add_event(
                Event.create_meal(timestamp_minutes=60.0, carbs_g=50.0, ...)
            )
            states = integrator.simulate_timeline(initial_state, timeline, dt_minutes=1.0)
            # states[0] is at t=0, states[60] is at t=60 (when meal occurs)
        """
        # Reset pending doses at start of simulation
        self._pending_caffeine_mg = 0.0
        self._pending_glucose_mg = 0.0
        
        # Calculate number of steps
        n_steps = int(TOTAL_DAY_MINUTES / dt_minutes) + 1
        
        # Initialize states list with initial state at t=0
        current_state = initial_state.with_updates(timestamp_minutes=0.0)
        states: List[PhysiologicalState] = [current_state]
        
        # Pre-process events into a lookup by timestep index
        # Event at time t goes into step index = floor(t / dt)
        event_lookup: Dict[int, List[EventLike]] = {}
        for event in timeline.events:
            step_index = int(event.timestamp_minutes / dt_minutes)
            if step_index not in event_lookup:
                event_lookup[step_index] = []
            event_lookup[step_index].append(event)
        
        # Run simulation: generate states for t=dt, 2*dt, ..., 1440
        for step_idx in range(1, n_steps):
            # Current time at START of this step
            current_time = (step_idx - 1) * dt_minutes
            
            # Get events that occur during this step interval [current_time, current_time + dt)
            # These are events with step_index == step_idx - 1
            events_this_step = event_lookup.get(step_idx - 1, [])
            
            # Apply step to advance state
            current_state = self.step(current_state, events_this_step, dt_minutes)
            states.append(current_state)
        
        return states
    
    def _process_events(
        self,
        current_state: PhysiologicalState,
        events: List[EventLike],
        dt_minutes: float
    ) -> Dict[str, Any]:
        """
        Process events and return state updates.
        
        Returns a dict with state field updates (not a full state).
        """
        updates: Dict[str, Any] = {}
        
        for event in events:
            try:
                # Handle both string and enum event_type
                event_type = event.event_type
                if hasattr(event_type, 'value'):
                    event_type = event_type.value
                
                if event_type == "meal":
                    meal_updates = self._process_meal_event(current_state, event)
                    updates.update(meal_updates)
                    
                elif event_type == "ingestion":
                    ingestion_updates = self._process_ingestion_event(current_state, event)
                    updates.update(ingestion_updates)
                    
                elif event_type in ("exercise", "sleep"):
                    # TODO: Implement in future sessions
                    logger.debug(f"Event type '{event_type}' not yet implemented")
                    
                else:
                    logger.warning(f"Unknown event type: {event_type}")
                    
            except Exception as e:
                # Log but continue processing other events
                logger.warning(f"Error processing event {event.event_type}: {e}")
                warnings.warn(f"Failed to process {event.event_type} event: {e}")
        
        return updates
    
    def _process_meal_event(
        self,
        current_state: PhysiologicalState,
        event: EventLike
    ) -> Dict[str, Any]:
        """
        Process a meal event.
        
        Adds carbohydrates to the gut for absorption.
        """
        payload = event.payload
        
        # Extract carbs (required field per Contract 2.1)
        carbs_g = payload.get("carbs_g", 0.0)
        
        # Convert to mg (1g = 1000mg)
        carbs_mg = carbs_g * 1000.0
        
        # Add to pending glucose (gut pool)
        # The glucose_gut_mg represents carbs waiting to be absorbed
        new_glucose_gut = current_state.glucose_gut_mg + carbs_mg
        
        return {
            "glucose_gut_mg": new_glucose_gut,
            "is_fasted": False,
            "hours_since_last_meal": 0.0  # Reset on meal
        }
    
    def _process_ingestion_event(
        self,
        current_state: PhysiologicalState,
        event: EventLike
    ) -> Dict[str, Any]:
        """
        Process an ingestion event (caffeine, supplements, etc).
        """
        payload = event.payload
        compound_id = payload.get("compound_id", "")
        amount = payload.get("amount", 0.0)
        unit = payload.get("unit", "mg")
        
        # Convert to mg if needed
        if unit == "g":
            amount_mg = amount * 1000.0
        elif unit == "mg":
            amount_mg = amount
        elif unit == "mcg":
            amount_mg = amount / 1000.0
        else:
            amount_mg = amount  # Assume mg
        
        updates: Dict[str, Any] = {}
        
        if compound_id == "caffeine":
            # Add to pending caffeine for absorption
            self._pending_caffeine_mg += amount_mg
            # Ingesting caffeine is not a meal, so don't change is_fasted
            
        # TODO: Add other compounds in future sessions
        # For unknown compounds, log warning but don't fail
        elif compound_id not in ("caffeine",):
            logger.warning(f"Unknown compound: {compound_id}")
        
        return updates
    
    def _step_glucose(
        self,
        current_state: PhysiologicalState,
        updates: Dict[str, Any],
        dt_minutes: float
    ) -> Dict[str, Any]:
        """
        Advance glucose dynamics by dt_minutes.
        
        Simple model:
        1. Absorb glucose from gut at a rate dependent on amount
        2. Increase plasma glucose based on absorption
        3. Decrease plasma glucose based on insulin-mediated uptake
        4. Decay back towards fasting baseline
        """
        # Get current values (use updates if available)
        glucose_gut = updates.get("glucose_gut_mg", current_state.glucose_gut_mg)
        glucose_plasma = current_state.glucose_plasma_mg_dl
        insulin_plasma = current_state.insulin_plasma_mu_l
        
        # Fasting values from person
        fasting_glucose = self.person.fasting_glucose_mg_dl
        fasting_insulin = self.person.fasting_insulin_mu_l
        
        # ===== GLUCOSE ABSORPTION FROM GUT =====
        # First-order absorption with rate proportional to amount
        absorption_rate = 0.02  # 2% per minute of gut contents
        glucose_absorbed_mg = glucose_gut * absorption_rate * dt_minutes
        
        # Ensure we don't absorb more than available
        glucose_absorbed_mg = min(glucose_absorbed_mg, glucose_gut)
        
        # Update gut contents
        new_glucose_gut = glucose_gut - glucose_absorbed_mg
        
        # ===== PLASMA GLUCOSE UPDATE =====
        # Convert absorbed glucose to plasma concentration
        # Assume ~5L of blood, glucose distributes in ~20L extracellular fluid
        distribution_volume_dl = 200.0  # 20L = 200 dL
        
        # Absorption increases plasma glucose
        delta_glucose_from_absorption = glucose_absorbed_mg / distribution_volume_dl
        
        # ===== GLUCOSE CLEARANCE =====
        # Simple first-order decay towards baseline
        # Rate depends on how far above baseline
        clearance_rate = 0.01  # 1% per minute when at double fasting
        deviation = glucose_plasma - fasting_glucose
        delta_glucose_clearance = deviation * clearance_rate * dt_minutes
        
        # Net change
        new_glucose_plasma = glucose_plasma + delta_glucose_from_absorption - delta_glucose_clearance
        
        # Clamp to physiological range
        new_glucose_plasma = max(20.0, min(600.0, new_glucose_plasma))
        
        # ===== INSULIN (simplified) =====
        # Insulin rises with glucose, decays towards fasting
        insulin_sensitivity = 0.02  # Response to glucose deviation
        glucose_deviation = new_glucose_plasma - fasting_glucose
        
        target_insulin = fasting_insulin + glucose_deviation * insulin_sensitivity * fasting_insulin
        insulin_decay = 0.01  # Rate of return to target
        
        delta_insulin = (target_insulin - insulin_plasma) * insulin_decay * dt_minutes
        new_insulin_plasma = insulin_plasma + delta_insulin
        new_insulin_plasma = max(0.0, min(1000.0, new_insulin_plasma))
        
        updates["glucose_gut_mg"] = max(0.0, new_glucose_gut)
        updates["glucose_plasma_mg_dl"] = new_glucose_plasma
        updates["insulin_plasma_mu_l"] = new_insulin_plasma
        
        return updates
    
    def _step_caffeine(
        self,
        current_state: PhysiologicalState,
        updates: Dict[str, Any],
        dt_minutes: float
    ) -> Dict[str, Any]:
        """
        Advance caffeine dynamics by dt_minutes.
        
        Simple 1-compartment model:
        1. Absorb pending caffeine dose
        2. Eliminate caffeine based on half-life
        3. Calculate alertness from caffeine concentration
        """
        caffeine_plasma = current_state.caffeine_plasma_mg_l
        
        # ===== CAFFEINE ABSORPTION =====
        if self._pending_caffeine_mg > 0:
            # First-order absorption
            ka = DEFAULT_KA  # ~20 min to peak
            absorbed_fraction = 1 - np.exp(-ka * dt_minutes)
            caffeine_absorbed_mg = self._pending_caffeine_mg * absorbed_fraction
            self._pending_caffeine_mg -= caffeine_absorbed_mg
            
            # Convert to plasma concentration
            # Vd = 0.5 L/kg, so for 78 kg person: 39L
            vd_l = DEFAULT_VD_L_PER_KG * self.person.weight_kg
            delta_caffeine = caffeine_absorbed_mg / vd_l  # mg/L
            
            caffeine_plasma += delta_caffeine
        
        # ===== CAFFEINE ELIMINATION =====
        half_life_h = self.person.caffeine_half_life_h
        half_life_min = half_life_h * 60.0
        ke = np.log(2) / half_life_min  # Elimination rate constant
        
        caffeine_plasma *= np.exp(-ke * dt_minutes)
        
        # Clamp to valid range
        caffeine_plasma = max(0.0, min(100.0, caffeine_plasma))
        
        # ===== ALERTNESS =====
        # Emax model: E = E0 + Emax * C / (EC50 + C)
        alertness = ALERTNESS_BASELINE + ALERTNESS_EMAX * caffeine_plasma / (CAFFEINE_EC50 + caffeine_plasma)
        alertness = max(0.0, min(100.0, alertness))
        
        # ===== ADENOSINE RECEPTOR OCCUPANCY =====
        # Simplified: inverse relationship with caffeine
        # More caffeine = more receptor blocking = lower occupancy by adenosine
        max_occupancy = 1.0
        caffeine_ic50 = 1.0  # mg/L for 50% block
        occupancy = max_occupancy / (1 + caffeine_plasma / caffeine_ic50)
        occupancy = max(0.0, min(1.0, occupancy))
        
        updates["caffeine_plasma_mg_l"] = caffeine_plasma
        updates["alertness_score"] = alertness
        updates["adenosine_receptor_occupancy"] = occupancy
        
        return updates
    
    def _step_time_tracking(
        self,
        current_state: PhysiologicalState,
        updates: Dict[str, Any],
        events: List[EventLike],
        dt_minutes: float
    ) -> Dict[str, Any]:
        """
        Update time-based tracking fields.
        """
        # Check if a meal occurred in this step
        # Handle both string and enum event_type
        had_meal = False
        for e in events:
            event_type = e.event_type
            if hasattr(event_type, 'value'):
                event_type = event_type.value
            if event_type == "meal":
                had_meal = True
                break
        
        if had_meal:
            # Already set in _process_meal_event
            if "hours_since_last_meal" not in updates:
                updates["hours_since_last_meal"] = dt_minutes / 60.0
            else:
                # Meal was processed, add small increment for this dt
                updates["hours_since_last_meal"] = dt_minutes / 60.0
        else:
            # No meal: increment hours since last meal
            current_hours = updates.get(
                "hours_since_last_meal",
                current_state.hours_since_last_meal
            )
            updates["hours_since_last_meal"] = current_hours + (dt_minutes / 60.0)
        
        # Update is_fasted based on hours
        hours = updates.get("hours_since_last_meal", current_state.hours_since_last_meal)
        if hours >= FASTING_THRESHOLD_HOURS:
            updates["is_fasted"] = True
        elif "is_fasted" not in updates:
            updates["is_fasted"] = current_state.is_fasted
        
        return updates


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["StateIntegrator"]
