"""
DaySimulator: 24-hour simulation orchestrator.

Contract: 5.1

Orchestrates a full day (24h) simulation using StateIntegrator and produces
DaySimulationResult with curves and metrics.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np

from src.core.population import VirtualPerson
from src.core.timeline import Timeline
from src.core.state import PhysiologicalState, StateIntegrator, create_fasted_state


@dataclass(frozen=True)
class DaySimulationResult:
    """
    Result of a 24-hour simulation for a single person.
    
    Contract 5.1:
    - states has len = 1440/dt_minutes + 1
    - All curves have same length as time_minutes
    - metrics includes at least core metrics
    
    Attributes:
        person_id: Identifier of the simulated person
        timeline: The timeline of events that was simulated
        states: List of PhysiologicalState, one per timestep
        time_minutes: numpy array of time points
        glucose_curve: Plasma glucose over time (mg/dL)
        insulin_curve: Plasma insulin over time (mU/L)
        caffeine_curve: Plasma caffeine over time (mg/L)
        alertness_curve: Alertness score over time (0-100)
        metrics: Calculated metrics dictionary
        is_valid: Whether simulation completed successfully
        warnings: List of warning messages
    """
    person_id: str
    timeline: Timeline
    states: List[PhysiologicalState]
    time_minutes: np.ndarray
    glucose_curve: np.ndarray
    insulin_curve: np.ndarray
    caffeine_curve: np.ndarray
    alertness_curve: np.ndarray
    metrics: Dict[str, Any]
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate that curves match time_minutes length."""
        n_points = len(self.time_minutes)
        
        if len(self.glucose_curve) != n_points:
            raise ValueError(f"glucose_curve length {len(self.glucose_curve)} != time_minutes length {n_points}")
        if len(self.insulin_curve) != n_points:
            raise ValueError(f"insulin_curve length {len(self.insulin_curve)} != time_minutes length {n_points}")
        if len(self.caffeine_curve) != n_points:
            raise ValueError(f"caffeine_curve length {len(self.caffeine_curve)} != time_minutes length {n_points}")
        if len(self.alertness_curve) != n_points:
            raise ValueError(f"alertness_curve length {len(self.alertness_curve)} != time_minutes length {n_points}")
        if len(self.states) != n_points:
            raise ValueError(f"states length {len(self.states)} != time_minutes length {n_points}")


class DaySimulator:
    """
    Orchestrates 24-hour physiological simulation.
    
    Contract 5.1:
    - __init__(person) - simplified version without library/interactions
    - simulate(timeline, dt_minutes=1.0) -> DaySimulationResult
    
    Usage:
        from src.core.population.person import create_reference_person
        person = create_reference_person()
        simulator = DaySimulator(person=person)
        result = simulator.simulate(timeline)
    """
    
    # Simulation constants
    DAY_DURATION_MINUTES = 1440  # 24 hours
    
    def __init__(
        self,
        person: VirtualPerson,
        library: Optional[Any] = None,  # For future Contract 5.1 compliance
        interaction_graph: Optional[Any] = None  # For future Contract 5.1 compliance
    ):
        """
        Initialize DaySimulator.
        
        Args:
            person: VirtualPerson to simulate
            library: IngredientLibrary (optional, for future use)
            interaction_graph: InteractionGraph (optional, for future use)
        """
        self.person = person
        self.library = library  # Reserved for future use
        self.interaction_graph = interaction_graph  # Reserved for future use
        
        # Create state integrator
        self._integrator = StateIntegrator(person=person)
    
    def simulate(
        self,
        timeline: Timeline,
        dt_minutes: float = 1.0
    ) -> DaySimulationResult:
        """
        Simulate a full 24-hour day.
        
        Args:
            timeline: Timeline of events to simulate
            dt_minutes: Time step in minutes (default: 1.0)
            
        Returns:
            DaySimulationResult with curves and metrics
        """
        warnings: List[str] = []
        
        # Create initial fasted state using standalone factory function
        initial_state = create_fasted_state(self.person)
        
        # Run simulation via StateIntegrator
        states = self._integrator.simulate_timeline(
            initial_state=initial_state,
            timeline=timeline,
            dt_minutes=dt_minutes
        )
        
        # Extract curves from states
        time_minutes = np.array([s.timestamp_minutes for s in states])
        glucose_curve = np.array([s.glucose_plasma_mg_dl for s in states])
        insulin_curve = np.array([s.insulin_plasma_mu_l for s in states])
        caffeine_curve = np.array([s.caffeine_plasma_mg_l for s in states])
        alertness_curve = np.array([s.alertness_score for s in states])
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            time_minutes=time_minutes,
            glucose_curve=glucose_curve,
            insulin_curve=insulin_curve,
            caffeine_curve=caffeine_curve,
            alertness_curve=alertness_curve
        )
        
        # Build result
        return DaySimulationResult(
            person_id=self.person.person_id,
            timeline=timeline,
            states=states,
            time_minutes=time_minutes,
            glucose_curve=glucose_curve,
            insulin_curve=insulin_curve,
            caffeine_curve=caffeine_curve,
            alertness_curve=alertness_curve,
            metrics=metrics,
            is_valid=True,
            warnings=warnings
        )
    
    def _calculate_metrics(
        self,
        time_minutes: np.ndarray,
        glucose_curve: np.ndarray,
        insulin_curve: np.ndarray,
        caffeine_curve: np.ndarray,
        alertness_curve: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculate core metrics from simulation curves.
        
        Returns dict with at least:
        - is_valid: bool
        - glucose_peak: float
        - caffeine_peak: float
        - alertness_peak: float
        """
        metrics: Dict[str, Any] = {
            "is_valid": True,
        }
        
        # Glucose metrics
        metrics["glucose_peak"] = float(np.max(glucose_curve))
        metrics["glucose_min"] = float(np.min(glucose_curve))
        metrics["glucose_mean"] = float(np.mean(glucose_curve))
        
        # Time to glucose peak
        peak_idx = int(np.argmax(glucose_curve))
        metrics["glucose_time_to_peak"] = float(time_minutes[peak_idx])
        
        # Insulin metrics
        metrics["insulin_peak"] = float(np.max(insulin_curve))
        metrics["insulin_mean"] = float(np.mean(insulin_curve))
        
        # Caffeine metrics
        metrics["caffeine_peak"] = float(np.max(caffeine_curve))
        if np.max(caffeine_curve) > 0:
            # Find approximate half-life by finding when caffeine drops to 50% of peak
            caffeine_peak_idx = int(np.argmax(caffeine_curve))
            peak_value = caffeine_curve[caffeine_peak_idx]
            half_value = peak_value / 2
            
            # Find first index after peak where caffeine drops below half
            post_peak = caffeine_curve[caffeine_peak_idx:]
            below_half = np.where(post_peak <= half_value)[0]
            
            if len(below_half) > 0:
                half_life_idx = caffeine_peak_idx + below_half[0]
                half_life_minutes = time_minutes[half_life_idx] - time_minutes[caffeine_peak_idx]
                metrics["caffeine_half_life_hours"] = float(half_life_minutes / 60)
            else:
                metrics["caffeine_half_life_hours"] = None  # Didn't reach half-life in simulation
        else:
            metrics["caffeine_half_life_hours"] = None
        
        # Alertness metrics
        metrics["alertness_peak"] = float(np.max(alertness_curve))
        metrics["alertness_min"] = float(np.min(alertness_curve))
        metrics["alertness_mean"] = float(np.mean(alertness_curve))
        
        # Duration above alertness threshold (60)
        above_60 = alertness_curve >= 60
        minutes_above_60 = float(np.sum(above_60))  # With dt=1, this is in minutes
        metrics["alertness_duration_above_60"] = minutes_above_60
        
        return metrics
