"""
Timeline - Ordered sequence of Events in a 24-hour day.

Contract 2.2 Compliance:
- events: List[Event] ALWAYS sorted by timestamp_minutes
- add_event() returns NEW Timeline (immutability)
- get_events_in_range(start, end) → List[Event]
- validate() → bool
- Two events CANNOT have exactly the same timestamp

This module is part of MODULUS Engine v3.0 "Decision & Compliance OS".
"""

from __future__ import annotations

import json
from typing import List, Optional, Iterator, Tuple

from ..contracts import Event


class Timeline:
    """
    Immutable, ordered sequence of Events in a 24-hour day.
    
    Events are always maintained in chronological order by timestamp_minutes.
    All modifications return a new Timeline instance (immutability).
    
    Contract 2.2 Compliance:
    - events ALWAYS sorted by timestamp_minutes
    - add_event() returns NEW Timeline
    - Duplicate timestamps are not allowed
    
    Examples
    --------
    >>> timeline = Timeline()
    >>> timeline = timeline.add_event(Event.create_ingestion(
    ...     timestamp_minutes=420, compound_id="caffeine", amount=100, unit="mg"
    ... ))
    >>> len(timeline)
    1
    
    >>> # Events are always sorted
    >>> timeline = Timeline(events=[
    ...     Event.create_meal(timestamp_minutes=780, carbs_g=60, glycemic_index=55),
    ...     Event.create_meal(timestamp_minutes=420, carbs_g=50, glycemic_index=60),
    ... ])
    >>> [e.timestamp_minutes for e in timeline]
    [420, 780]
    """
    
    __slots__ = ('_events',)
    
    def __init__(self, events: Optional[List[Event]] = None):
        """
        Create a Timeline with optional initial events.
        
        Parameters
        ----------
        events : List[Event], optional
            Initial events. Will be sorted by timestamp. If None, creates empty timeline.
        
        Raises
        ------
        ValueError
            If any two events have the same timestamp_minutes.
        """
        if events is None:
            events = []
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp_minutes)
        
        # Check for duplicate timestamps
        self._check_no_duplicate_timestamps(sorted_events)
        
        # Store as immutable tuple
        self._events: Tuple[Event, ...] = tuple(sorted_events)
    
    @staticmethod
    def _check_no_duplicate_timestamps(events: List[Event]) -> None:
        """
        Verify no two events have the same timestamp.
        
        Raises
        ------
        ValueError
            If duplicate timestamps found.
        """
        if len(events) < 2:
            return
        
        for i in range(len(events) - 1):
            if events[i].timestamp_minutes == events[i + 1].timestamp_minutes:
                raise ValueError(
                    f"Duplicate timestamp {events[i].timestamp_minutes} found. "
                    "Two events cannot have exactly the same timestamp."
                )
    
    # ========================================================================
    # PROPERTIES
    # ========================================================================
    
    @property
    def events(self) -> Tuple[Event, ...]:
        """
        Get all events as an immutable tuple.
        
        Returns
        -------
        Tuple[Event, ...]
            Events in chronological order.
        """
        return self._events
    
    @property
    def is_empty(self) -> bool:
        """Check if timeline has no events."""
        return len(self._events) == 0
    
    @property
    def first_event(self) -> Event:
        """
        Get the first (earliest) event.
        
        Returns
        -------
        Event
            The event with the smallest timestamp.
        
        Raises
        ------
        ValueError
            If timeline is empty.
        """
        if self.is_empty:
            raise ValueError("Cannot get first_event from empty timeline")
        return self._events[0]
    
    @property
    def last_event(self) -> Event:
        """
        Get the last (latest) event.
        
        Returns
        -------
        Event
            The event with the largest timestamp.
        
        Raises
        ------
        ValueError
            If timeline is empty.
        """
        if self.is_empty:
            raise ValueError("Cannot get last_event from empty timeline")
        return self._events[-1]
    
    @property
    def duration_minutes(self) -> float:
        """
        Get the time span from first to last event.
        
        Returns
        -------
        float
            Duration in minutes (0 if empty or single event).
        """
        if len(self._events) < 2:
            return 0.0
        return self._events[-1].timestamp_minutes - self._events[0].timestamp_minutes
    
    # ========================================================================
    # CORE METHODS (Contract 2.2)
    # ========================================================================
    
    def add_event(self, event: Event) -> Timeline:
        """
        Add an event, returning a NEW Timeline.
        
        The original Timeline is not modified (immutability).
        Events are automatically sorted by timestamp.
        
        Parameters
        ----------
        event : Event
            The event to add.
        
        Returns
        -------
        Timeline
            A new Timeline containing all existing events plus the new one.
        
        Raises
        ------
        ValueError
            If an event with the same timestamp already exists.
        
        Examples
        --------
        >>> timeline = Timeline()
        >>> new_timeline = timeline.add_event(Event.create_ingestion(
        ...     timestamp_minutes=420, compound_id="caffeine", amount=100, unit="mg"
        ... ))
        >>> len(timeline)  # Original unchanged
        0
        >>> len(new_timeline)
        1
        """
        # Check for duplicate timestamp
        if self.has_event_at(event.timestamp_minutes):
            raise ValueError(
                f"Event at timestamp {event.timestamp_minutes} already exists. "
                "Two events cannot have exactly the same timestamp."
            )
        
        # Create new list with all events plus new one
        new_events = list(self._events) + [event]
        
        # Return new Timeline (constructor handles sorting)
        return Timeline(events=new_events)
    
    def get_events_in_range(
        self, 
        start: float, 
        end: float
    ) -> List[Event]:
        """
        Get all events within a time range (inclusive).
        
        Parameters
        ----------
        start : float
            Start of range in minutes (inclusive). Must be >= 0.
        end : float
            End of range in minutes (inclusive). Must be <= 1440.
        
        Returns
        -------
        List[Event]
            Events with timestamp in [start, end], in chronological order.
        
        Raises
        ------
        ValueError
            If start > end, start < 0, or end > 1440.
        
        Examples
        --------
        >>> events = timeline.get_events_in_range(400, 500)
        """
        # Validate range
        if start < 0:
            raise ValueError(f"start must be >= 0, got {start}")
        if end > 1440:
            raise ValueError(f"end must be <= 1440, got {end}")
        if start > end:
            raise ValueError(f"start ({start}) must be <= end ({end})")
        
        return [
            e for e in self._events
            if start <= e.timestamp_minutes <= end
        ]
    
    def validate(self) -> bool:
        """
        Verify timeline consistency.
        
        Checks:
        - Events are sorted by timestamp
        - No duplicate timestamps
        
        Returns
        -------
        bool
            True if timeline is valid, False otherwise.
        
        Note
        ----
        A properly constructed Timeline should always be valid.
        This method is useful for debugging or verifying after deserialization.
        """
        if len(self._events) < 2:
            return True
        
        # Check sorted order and no duplicates
        for i in range(len(self._events) - 1):
            curr_ts = self._events[i].timestamp_minutes
            next_ts = self._events[i + 1].timestamp_minutes
            
            if curr_ts >= next_ts:
                return False
        
        return True
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def has_event_at(self, timestamp_minutes: float) -> bool:
        """
        Check if an event exists at the given timestamp.
        
        Parameters
        ----------
        timestamp_minutes : float
            The timestamp to check.
        
        Returns
        -------
        bool
            True if an event exists at this exact timestamp.
        """
        return any(e.timestamp_minutes == timestamp_minutes for e in self._events)
    
    def get_event_at(self, timestamp_minutes: float) -> Optional[Event]:
        """
        Get the event at the given timestamp.
        
        Parameters
        ----------
        timestamp_minutes : float
            The timestamp to look for.
        
        Returns
        -------
        Event or None
            The event at this timestamp, or None if not found.
        """
        for event in self._events:
            if event.timestamp_minutes == timestamp_minutes:
                return event
        return None
    
    # ========================================================================
    # SERIALIZATION (Contract 2.2)
    # ========================================================================
    
    def to_json(self) -> str:
        """
        Serialize timeline to JSON string.
        
        Returns
        -------
        str
            JSON string representation.
        
        Examples
        --------
        >>> json_str = timeline.to_json()
        >>> restored = Timeline.from_json(json_str)
        """
        data = {
            "events": [e.to_dict() for e in self._events]
        }
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> Timeline:
        """
        Deserialize timeline from JSON string.
        
        Parameters
        ----------
        json_str : str
            JSON string (from to_json()).
        
        Returns
        -------
        Timeline
            Restored Timeline instance.
        
        Note
        ----
        Events will be sorted automatically even if JSON is unsorted.
        """
        data = json.loads(json_str)
        events = [Event.from_dict(e) for e in data["events"]]
        return cls(events=events)
    
    def to_dict(self) -> dict:
        """
        Convert timeline to dictionary.
        
        Returns
        -------
        dict
            Dictionary representation.
        """
        return {
            "events": [e.to_dict() for e in self._events]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Timeline:
        """
        Create timeline from dictionary.
        
        Parameters
        ----------
        data : dict
            Dictionary with "events" key.
        
        Returns
        -------
        Timeline
            New Timeline instance.
        """
        events = [Event.from_dict(e) for e in data["events"]]
        return cls(events=events)
    
    # ========================================================================
    # DUNDER METHODS
    # ========================================================================
    
    def __len__(self) -> int:
        """Return number of events."""
        return len(self._events)
    
    def __iter__(self) -> Iterator[Event]:
        """Iterate over events in chronological order."""
        return iter(self._events)
    
    def __repr__(self) -> str:
        """Return detailed string representation."""
        n = len(self._events)
        if n == 0:
            return "Timeline(0 events)"
        
        first_ts = self._events[0].timestamp_minutes
        last_ts = self._events[-1].timestamp_minutes
        return f"Timeline({n} events, {first_ts:.0f}-{last_ts:.0f} min)"
    
    def __str__(self) -> str:
        """Return human-readable string representation."""
        if self.is_empty:
            return "Timeline: empty"
        
        lines = [f"Timeline ({len(self._events)} events):"]
        for event in self._events:
            # Convert minutes to HH:MM format
            hours = int(event.timestamp_minutes // 60)
            mins = int(event.timestamp_minutes % 60)
            time_str = f"{hours:02d}:{mins:02d}"
            lines.append(f"  {time_str} - {event.event_type}")
        
        return "\n".join(lines)
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another Timeline."""
        if not isinstance(other, Timeline):
            return NotImplemented
        return self._events == other._events
    
    def __hash__(self) -> int:
        """Hash based on events tuple."""
        # Note: This works because Event.to_dict() returns consistent output
        # and we store events as a tuple. However, since Event is not hashable
        # (due to dict payload), we hash the JSON representation
        return hash(self.to_json())
