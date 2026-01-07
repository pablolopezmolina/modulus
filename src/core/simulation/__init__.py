"""
Simulation Module: Orchestrators for 24h simulations.

This module provides high-level simulation orchestrators that combine
models, timelines, and states to produce complete simulation results.

Exports:
    - DaySimulator: Simulates a single person for 24 hours
    - DaySimulationResult: Result dataclass with curves and metrics
"""

from src.core.simulation.day_simulator import (
    DaySimulator,
    DaySimulationResult,
)

__all__ = [
    "DaySimulator",
    "DaySimulationResult",
]
