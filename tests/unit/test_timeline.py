"""
Unit tests for Timeline.

Tests Contract 2.2 compliance:
- events SIEMPRE ordenados por timestamp_minutes
- add_event() retorna NUEVA Timeline (inmutabilidad)
- Dos eventos NO pueden tener exactamente el mismo timestamp
- get_events_in_range(start, end) → List[Event]
- validate() → bool
- to_json() / from_json() serialization
"""

import pytest
import json
from typing import List

from src.core.timeline import Event, Timeline


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_events() -> List[Event]:
    """Create sample events in non-chronological order for testing."""
    return [
        Event.create_meal(
            timestamp_minutes=450,  # 7:30 AM breakfast
            carbs_g=50, protein_g=20, fat_g=15, glycemic_index=60
        ),
        Event.create_ingestion(
            timestamp_minutes=420,  # 7:00 AM morning coffee
            compound_id="caffeine", amount=100, unit="mg"
        ),
        Event.create_meal(
            timestamp_minutes=780,  # 1:00 PM lunch
            carbs_g=60, protein_g=30, fat_g=20, glycemic_index=55
        ),
    ]


@pytest.fixture
def empty_timeline() -> Timeline:
    """Create an empty timeline."""
    return Timeline()


@pytest.fixture
def populated_timeline(sample_events) -> Timeline:
    """Create a timeline with sample events."""
    return Timeline(events=sample_events)


# ============================================================================
# CONSTRUCTION TESTS
# ============================================================================

class TestTimelineConstruction:
    """Test Timeline creation and initialization."""
    
    def test_create_empty_timeline(self):
        """Empty timeline should have no events."""
        timeline = Timeline()
        assert len(timeline.events) == 0
        assert timeline.is_empty
    
    def test_create_timeline_with_events(self, sample_events):
        """Timeline with events should store them."""
        timeline = Timeline(events=sample_events)
        assert len(timeline.events) == 3
        assert not timeline.is_empty
    
    def test_events_are_sorted_on_construction(self, sample_events):
        """Events should be sorted by timestamp even if passed unsorted."""
        # sample_events are: 450, 420, 780 (unsorted)
        timeline = Timeline(events=sample_events)
        
        timestamps = [e.timestamp_minutes for e in timeline.events]
        assert timestamps == sorted(timestamps)
        assert timestamps == [420, 450, 780]
    
    def test_timeline_from_single_event(self):
        """Timeline can be created from a single event."""
        event = Event.create_ingestion(
            timestamp_minutes=60, compound_id="caffeine", amount=50, unit="mg"
        )
        timeline = Timeline(events=[event])
        assert len(timeline.events) == 1
        assert timeline.events[0] == event


# ============================================================================
# IMMUTABILITY TESTS (Contract 2.2)
# ============================================================================

class TestTimelineImmutability:
    """Test that Timeline is immutable."""
    
    def test_events_attribute_is_tuple(self, populated_timeline):
        """Events should be stored as tuple (immutable)."""
        assert isinstance(populated_timeline.events, tuple)
    
    def test_cannot_modify_events_list(self, populated_timeline):
        """Attempting to modify events should raise error."""
        with pytest.raises((TypeError, AttributeError)):
            populated_timeline.events[0] = Event.create_meal(
                timestamp_minutes=0, carbs_g=10, glycemic_index=50
            )
    
    def test_cannot_append_to_events(self, populated_timeline):
        """Attempting to append to events should raise error."""
        with pytest.raises(AttributeError):
            populated_timeline.events.append(Event.create_meal(
                timestamp_minutes=0, carbs_g=10, glycemic_index=50
            ))
    
    def test_add_event_returns_new_timeline(self, populated_timeline):
        """add_event should return a NEW Timeline, not modify existing."""
        original_len = len(populated_timeline.events)
        original_id = id(populated_timeline)
        
        new_event = Event.create_ingestion(
            timestamp_minutes=900, compound_id="caffeine", amount=50, unit="mg"
        )
        new_timeline = populated_timeline.add_event(new_event)
        
        # Original unchanged
        assert len(populated_timeline.events) == original_len
        assert id(populated_timeline) == original_id
        
        # New timeline has additional event
        assert len(new_timeline.events) == original_len + 1
        assert id(new_timeline) != original_id


# ============================================================================
# ADD_EVENT TESTS (Contract 2.2)
# ============================================================================

class TestAddEvent:
    """Test add_event functionality."""
    
    def test_add_event_maintains_sort_order(self, populated_timeline):
        """Added event should be inserted in correct chronological position."""
        # populated_timeline has: 420, 450, 780
        new_event = Event.create_meal(
            timestamp_minutes=600,  # Between 450 and 780
            carbs_g=20, glycemic_index=40
        )
        new_timeline = populated_timeline.add_event(new_event)
        
        timestamps = [e.timestamp_minutes for e in new_timeline.events]
        assert timestamps == [420, 450, 600, 780]
    
    def test_add_event_at_beginning(self, populated_timeline):
        """Event with smallest timestamp should be first."""
        new_event = Event.create_ingestion(
            timestamp_minutes=0, compound_id="water", amount=500, unit="ml"
        )
        new_timeline = populated_timeline.add_event(new_event)
        
        assert new_timeline.events[0].timestamp_minutes == 0
    
    def test_add_event_at_end(self, populated_timeline):
        """Event with largest timestamp should be last."""
        new_event = Event.create_meal(
            timestamp_minutes=1200, carbs_g=50, glycemic_index=50
        )
        new_timeline = populated_timeline.add_event(new_event)
        
        assert new_timeline.events[-1].timestamp_minutes == 1200
    
    def test_add_event_to_empty_timeline(self, empty_timeline):
        """Can add event to empty timeline."""
        event = Event.create_ingestion(
            timestamp_minutes=420, compound_id="caffeine", amount=100, unit="mg"
        )
        new_timeline = empty_timeline.add_event(event)
        
        assert len(new_timeline.events) == 1
        assert new_timeline.events[0] == event
    
    def test_duplicate_timestamp_raises_error(self, populated_timeline):
        """Adding event with existing timestamp should raise ValueError."""
        # 420 already exists in populated_timeline
        duplicate_event = Event.create_ingestion(
            timestamp_minutes=420, compound_id="taurine", amount=500, unit="mg"
        )
        
        with pytest.raises(ValueError, match="timestamp.*already exists"):
            populated_timeline.add_event(duplicate_event)
    
    def test_add_multiple_events_fluent(self, empty_timeline):
        """Can chain add_event calls fluently."""
        timeline = (
            empty_timeline
            .add_event(Event.create_ingestion(
                timestamp_minutes=420, compound_id="caffeine", amount=100, unit="mg"
            ))
            .add_event(Event.create_meal(
                timestamp_minutes=450, carbs_g=50, glycemic_index=60
            ))
            .add_event(Event.create_meal(
                timestamp_minutes=780, carbs_g=60, glycemic_index=55
            ))
        )
        
        assert len(timeline.events) == 3
        timestamps = [e.timestamp_minutes for e in timeline.events]
        assert timestamps == [420, 450, 780]


# ============================================================================
# GET_EVENTS_IN_RANGE TESTS (Contract 2.2)
# ============================================================================

class TestGetEventsInRange:
    """Test get_events_in_range functionality."""
    
    def test_get_events_in_middle_range(self, populated_timeline):
        """Get events within a specific range."""
        # populated_timeline has: 420, 450, 780
        events = populated_timeline.get_events_in_range(400, 500)
        
        assert len(events) == 2
        timestamps = [e.timestamp_minutes for e in events]
        assert timestamps == [420, 450]
    
    def test_range_includes_boundaries(self, populated_timeline):
        """Range should be inclusive [start, end]."""
        events = populated_timeline.get_events_in_range(420, 450)
        
        assert len(events) == 2
        assert events[0].timestamp_minutes == 420
        assert events[1].timestamp_minutes == 450
    
    def test_get_all_events_with_full_range(self, populated_timeline):
        """Range 0-1440 should return all events."""
        events = populated_timeline.get_events_in_range(0, 1440)
        assert len(events) == len(populated_timeline.events)
    
    def test_empty_range_returns_empty_list(self, populated_timeline):
        """Range with no events should return empty list."""
        events = populated_timeline.get_events_in_range(500, 700)
        assert len(events) == 0
        assert events == []
    
    def test_get_events_from_empty_timeline(self, empty_timeline):
        """Getting events from empty timeline returns empty list."""
        events = empty_timeline.get_events_in_range(0, 1440)
        assert events == []
    
    def test_invalid_range_raises_error(self, populated_timeline):
        """Start > end should raise ValueError."""
        with pytest.raises(ValueError, match="start.*must be.*end"):
            populated_timeline.get_events_in_range(500, 400)
    
    def test_negative_start_raises_error(self, populated_timeline):
        """Negative start should raise ValueError."""
        with pytest.raises(ValueError):
            populated_timeline.get_events_in_range(-10, 100)
    
    def test_end_beyond_1440_raises_error(self, populated_timeline):
        """End > 1440 should raise ValueError."""
        with pytest.raises(ValueError):
            populated_timeline.get_events_in_range(0, 1500)


# ============================================================================
# VALIDATE TESTS (Contract 2.2)
# ============================================================================

class TestValidate:
    """Test validate functionality."""
    
    def test_empty_timeline_is_valid(self, empty_timeline):
        """Empty timeline should be valid."""
        assert empty_timeline.validate() is True
    
    def test_sorted_timeline_is_valid(self, populated_timeline):
        """Properly sorted timeline should be valid."""
        assert populated_timeline.validate() is True
    
    def test_no_duplicate_timestamps_is_valid(self, populated_timeline):
        """Timeline without duplicate timestamps is valid."""
        # populated_timeline has unique timestamps
        assert populated_timeline.validate() is True


# ============================================================================
# SERIALIZATION TESTS (Contract 2.2)
# ============================================================================

class TestSerialization:
    """Test to_json and from_json functionality."""
    
    def test_to_json_empty_timeline(self, empty_timeline):
        """Empty timeline serializes to valid JSON."""
        json_str = empty_timeline.to_json()
        data = json.loads(json_str)
        
        assert "events" in data
        assert data["events"] == []
    
    def test_to_json_with_events(self, populated_timeline):
        """Timeline with events serializes correctly."""
        json_str = populated_timeline.to_json()
        data = json.loads(json_str)
        
        assert len(data["events"]) == 3
        # Events should be in sorted order
        timestamps = [e["timestamp_minutes"] for e in data["events"]]
        assert timestamps == sorted(timestamps)
    
    def test_from_json_empty_timeline(self):
        """Can deserialize empty timeline."""
        json_str = '{"events": []}'
        timeline = Timeline.from_json(json_str)
        
        assert len(timeline.events) == 0
    
    def test_from_json_with_events(self, populated_timeline):
        """Can deserialize timeline with events."""
        json_str = populated_timeline.to_json()
        restored = Timeline.from_json(json_str)
        
        assert len(restored.events) == len(populated_timeline.events)
        for orig, rest in zip(populated_timeline.events, restored.events):
            assert orig.timestamp_minutes == rest.timestamp_minutes
            assert orig.event_type == rest.event_type
    
    def test_roundtrip_serialization(self, populated_timeline):
        """Serializing and deserializing should preserve data."""
        json_str = populated_timeline.to_json()
        restored = Timeline.from_json(json_str)
        
        # Serialize again and compare
        json_str2 = restored.to_json()
        assert json_str == json_str2
    
    def test_from_json_sorts_events(self):
        """from_json should sort events even if JSON is unsorted."""
        # Manually create unsorted JSON
        json_str = json.dumps({
            "events": [
                {"timestamp_minutes": 780, "event_type": "meal", 
                 "payload": {"carbs_g": 60, "protein_g": 30, "fat_g": 20, "glycemic_index": 55}},
                {"timestamp_minutes": 420, "event_type": "ingestion",
                 "payload": {"compound_id": "caffeine", "amount": 100, "unit": "mg", "form": "liquid"}},
            ]
        })
        
        timeline = Timeline.from_json(json_str)
        timestamps = [e.timestamp_minutes for e in timeline.events]
        assert timestamps == [420, 780]


# ============================================================================
# UTILITY METHOD TESTS
# ============================================================================

class TestUtilityMethods:
    """Test utility methods and properties."""
    
    def test_len_returns_event_count(self, populated_timeline, empty_timeline):
        """len(timeline) should return number of events."""
        assert len(populated_timeline) == 3
        assert len(empty_timeline) == 0
    
    def test_is_empty_property(self, populated_timeline, empty_timeline):
        """is_empty should correctly identify empty timelines."""
        assert empty_timeline.is_empty is True
        assert populated_timeline.is_empty is False
    
    def test_first_event_property(self, populated_timeline):
        """first_event should return event with smallest timestamp."""
        assert populated_timeline.first_event.timestamp_minutes == 420
    
    def test_first_event_on_empty_raises(self, empty_timeline):
        """first_event on empty timeline should raise."""
        with pytest.raises(ValueError, match="empty"):
            _ = empty_timeline.first_event
    
    def test_last_event_property(self, populated_timeline):
        """last_event should return event with largest timestamp."""
        assert populated_timeline.last_event.timestamp_minutes == 780
    
    def test_last_event_on_empty_raises(self, empty_timeline):
        """last_event on empty timeline should raise."""
        with pytest.raises(ValueError, match="empty"):
            _ = empty_timeline.last_event
    
    def test_duration_property(self, populated_timeline):
        """duration should return time span from first to last event."""
        # Events at 420, 450, 780
        assert populated_timeline.duration_minutes == 780 - 420  # 360
    
    def test_duration_on_empty_is_zero(self, empty_timeline):
        """duration on empty timeline should be 0."""
        assert empty_timeline.duration_minutes == 0
    
    def test_duration_single_event(self):
        """duration with single event should be 0."""
        event = Event.create_ingestion(
            timestamp_minutes=420, compound_id="caffeine", amount=100, unit="mg"
        )
        timeline = Timeline(events=[event])
        assert timeline.duration_minutes == 0
    
    def test_iter_returns_events_in_order(self, populated_timeline):
        """Iterating timeline should yield events in chronological order."""
        timestamps = [e.timestamp_minutes for e in populated_timeline]
        assert timestamps == [420, 450, 780]
    
    def test_contains_event_by_timestamp(self, populated_timeline):
        """Can check if timestamp exists in timeline."""
        assert populated_timeline.has_event_at(420) is True
        assert populated_timeline.has_event_at(500) is False
    
    def test_get_event_at_timestamp(self, populated_timeline):
        """Can get event at specific timestamp."""
        event = populated_timeline.get_event_at(420)
        assert event is not None
        assert event.timestamp_minutes == 420
    
    def test_get_event_at_nonexistent_returns_none(self, populated_timeline):
        """Getting event at nonexistent timestamp returns None."""
        assert populated_timeline.get_event_at(500) is None


# ============================================================================
# REPR AND STRING TESTS
# ============================================================================

class TestReprAndString:
    """Test string representations."""
    
    def test_repr_empty_timeline(self, empty_timeline):
        """Empty timeline has informative repr."""
        repr_str = repr(empty_timeline)
        assert "Timeline" in repr_str
        assert "0 events" in repr_str
    
    def test_repr_populated_timeline(self, populated_timeline):
        """Populated timeline has informative repr."""
        repr_str = repr(populated_timeline)
        assert "Timeline" in repr_str
        assert "3 events" in repr_str
    
    def test_str_shows_event_summary(self, populated_timeline):
        """str should show summary of events."""
        str_repr = str(populated_timeline)
        assert "420" in str_repr or "7:00" in str_repr  # timestamp or time
        assert "780" in str_repr or "13:00" in str_repr


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_events_at_day_boundaries(self):
        """Events at exact 0 and 1440 should work."""
        start_event = Event.create_ingestion(
            timestamp_minutes=0, compound_id="water", amount=500, unit="ml"
        )
        end_event = Event.create_meal(
            timestamp_minutes=1440, carbs_g=30, glycemic_index=50
        )
        
        timeline = Timeline(events=[start_event, end_event])
        assert len(timeline.events) == 2
        assert timeline.events[0].timestamp_minutes == 0
        assert timeline.events[1].timestamp_minutes == 1440
    
    def test_very_close_timestamps_allowed(self):
        """Events with very close (but different) timestamps are allowed."""
        event1 = Event.create_ingestion(
            timestamp_minutes=420.0, compound_id="caffeine", amount=100, unit="mg"
        )
        event2 = Event.create_ingestion(
            timestamp_minutes=420.001, compound_id="taurine", amount=500, unit="mg"
        )
        
        timeline = Timeline(events=[event1, event2])
        assert len(timeline.events) == 2
    
    def test_float_timestamp_precision(self):
        """Timeline handles float timestamps correctly."""
        event = Event.create_ingestion(
            timestamp_minutes=420.5, compound_id="caffeine", amount=100, unit="mg"
        )
        timeline = Timeline(events=[event])
        assert timeline.events[0].timestamp_minutes == 420.5
    
    def test_many_events_performance(self):
        """Timeline handles many events efficiently."""
        events = [
            Event.create_meal(
                timestamp_minutes=float(i), carbs_g=10, glycemic_index=50
            )
            for i in range(0, 1441, 10)  # 145 events
        ]
        
        timeline = Timeline(events=events)
        assert len(timeline.events) == 145
        assert timeline.validate() is True
