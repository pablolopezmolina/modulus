"""
Timeline module - Ordered sequence of events for 24-hour simulation.

This module provides the Timeline Engine (Layer 2) for MODULUS.

Contract 2.1: Event
Contract 2.2: Timeline

Exports
-------
Event : dataclass
    A single event in the timeline (re-exported from contracts).
Timeline : class
    Immutable, ordered sequence of events.

Examples
--------
>>> from src.core.timeline import Event, Timeline
>>>
>>> # Create events
>>> coffee = Event.create_ingestion(
...     timestamp_minutes=420,  # 7:00 AM
...     compound_id="caffeine",
...     amount=100,
...     unit="mg"
... )
>>> breakfast = Event.create_meal(
...     timestamp_minutes=450,  # 7:30 AM
...     carbs_g=50,
...     protein_g=20,
...     fat_g=15,
...     glycemic_index=60
... )
>>>
>>> # Build timeline (events are auto-sorted)
>>> timeline = Timeline()
>>> timeline = timeline.add_event(breakfast)
>>> timeline = timeline.add_event(coffee)
>>>
>>> # Events are in chronological order
>>> [e.timestamp_minutes for e in timeline]
[420, 450]
"""

# Re-export Event and EventType from contracts (single source of truth)
from ..contracts import Event, EventType

# Export Timeline (relative import within package)
from .timeline import Timeline

__all__ = ["Event", "EventType", "Timeline"]
