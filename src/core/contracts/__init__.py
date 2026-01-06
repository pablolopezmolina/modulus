# MODULUS - Contracts Module
# 
# Este módulo define los contratos (interfaces) entre componentes.
# TODOS los datos que cruzan fronteras entre módulos deben usar estos tipos.
#
# Contratos definidos:
# - Event: Un evento en el timeline (ingesta, comida, ejercicio, sueño)
# - PhysiologicalState: Estado del cuerpo en un instante
# - SimulationResult: Resultado de una simulación
#
# ⚠️  ESTOS TIPOS SON INMUTABLES
# ⚠️  CAMBIAR UN CONTRATO REQUIERE ACTUALIZAR CONTRACTS.md

from src.core.contracts.events import Event, EventType
from src.core.contracts.state import PhysiologicalState
from src.core.contracts.results import SimulationResult

__all__ = [
    "Event",
    "EventType", 
    "PhysiologicalState",
    "SimulationResult",
]
