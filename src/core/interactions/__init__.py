"""
MODULUS - Interaction Engine (Capa 4)

This module handles compound-compound interactions and context-based rules.

Contracts:
- Contract 3.3: Interaction dataclass
- Contract 4.1: InteractionGraph

Key interactions modeled:
1. Caffeine + L-Theanine → reduced jitter (-50%)
2. Caffeine + food → delayed absorption
3. Carbs + protein/fat/fiber → slower absorption
4. Creatine + carbs → enhanced uptake
5. High-dose caffeine (>300mg) → increased jitter
6. Afternoon caffeine → sleep disruption
7. Tyrosine + caffeine → enhanced focus
"""
from .interaction import Interaction, ContextInteraction
from .graph import InteractionGraph


__all__ = [
    "Interaction",
    "ContextInteraction", 
    "InteractionGraph",
]
