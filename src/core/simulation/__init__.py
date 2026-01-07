"""
Simulation module for MODULUS.

Contains:
- DaySimulator: Single person 24h simulation
- PopulationDaySimulator: Population simulation with streaming aggregation
"""

from src.core.simulation.day_simulator import (
    DaySimulator,
    DaySimulationResult,
)
from src.core.simulation.population_day_simulator import (
    PopulationDaySimulator,
    PopulationDayResult,
    PopulationSimulationConfig,
)

__all__ = [
    # Day simulation
    'DaySimulator',
    'DaySimulationResult',
    # Population simulation
    'PopulationDaySimulator',
    'PopulationDayResult',
    'PopulationSimulationConfig',
]
