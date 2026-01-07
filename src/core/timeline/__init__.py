"""
MODULUS Timeline Engine - Event management for 24h simulations.

This module provides the Event and Timeline classes for managing
sequences of events (meals, ingestions, exercise, sleep) over a 24-hour period.

FASE 1: 24h Engine
- Sesión 1.1: Event (this module re-exports from contracts)
- Sesión 1.2: Timeline (to be added)

The Event class is defined in src.core.contracts.events to maintain
a single source of truth. This module re-exports it for convenience.
"""

from src.core.contracts.events import Event, EventType

__all__ = ["Event", "EventType"]
