"""
MODULUS - Tests for Analytics Dashboard
Session 17.x: Analytics tracking and dashboard for brand clients

Tests cover:
- AnalyticsEvent data class
- AnalyticsStore (in-memory storage)
- AnalyticsService (aggregation and metrics)
- Dashboard data generation
"""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.webapp.analytics import (
    AnalyticsEvent,
    AnalyticsStore,
    AnalyticsService,
    get_analytics_service,
    reset_analytics_service
)


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_service():
    """Reset analytics service before each test."""
    reset_analytics_service()
    yield
    reset_analytics_service()


@pytest.fixture
def sample_personalization_event():
    """Sample personalization event."""
    return {
        "event_type": "personalization",
        "brand_id": "energyx",
        "product_id": "energy_pro",
        "timestamp": datetime.now().isoformat(),
        "user_data": {
            "weight_kg": 75,
            "caffeine_sensitivity": "normal",
            "activity_time": "18:00"
        },
        "result": {
            "optimal_timing": "17:15",
            "response_time_ms": 45
        }
    }


@pytest.fixture
def sample_page_view_event():
    """Sample page view event."""
    return {
        "event_type": "page_view",
        "brand_id": "energyx",
        "product_id": "energy_pro",
        "timestamp": datetime.now().isoformat(),
        "page": "landing"
    }


@pytest.fixture
def sample_form_start_event():
    """Sample form start event."""
    return {
        "event_type": "form_start",
        "brand_id": "focuslab",
        "product_id": "focus_max",
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# AnalyticsEvent Tests
# =============================================================================

class TestAnalyticsEvent:
    """Tests for AnalyticsEvent data class."""

    def test_create_valid_event(self):
        """Create a valid analytics event."""
        event = AnalyticsEvent(
            event_type="personalization",
            brand_id="energyx",
            product_id="energy_pro",
            timestamp=datetime.now(),
            data={"weight_kg": 75}
        )
        
        assert event.event_type == "personalization"
        assert event.brand_id == "energyx"
        assert event.product_id == "energy_pro"
        assert event.data == {"weight_kg": 75}

    def test_event_with_all_fields(self):
        """Event with all optional fields."""
        now = datetime.now()
        event = AnalyticsEvent(
            event_type="page_view",
            brand_id="vitaplus",
            product_id="sleep_well",
            timestamp=now,
            data={"page": "landing"},
            session_id="sess_123",
            user_agent="Mozilla/5.0"
        )
        
        assert event.session_id == "sess_123"
        assert event.user_agent == "Mozilla/5.0"

    def test_event_to_dict(self):
        """Convert event to dictionary."""
        now = datetime.now()
        event = AnalyticsEvent(
            event_type="personalization",
            brand_id="energyx",
            product_id="energy_pro",
            timestamp=now,
            data={"test": "value"}
        )
        
        d = event.to_dict()
        assert d["event_type"] == "personalization"
        assert d["brand_id"] == "energyx"
        assert d["timestamp"] == now.isoformat()
        assert d["data"] == {"test": "value"}

    def test_event_from_dict(self):
        """Create event from dictionary."""
        now = datetime.now()
        data = {
            "event_type": "form_start",
            "brand_id": "focuslab",
            "product_id": "focus_max",
            "timestamp": now.isoformat(),
            "data": {}
        }
        
        event = AnalyticsEvent.from_dict(data)
        assert event.event_type == "form_start"
        assert event.brand_id == "focuslab"
        # Timestamp should be parsed back to datetime
        assert isinstance(event.timestamp, datetime)


# =============================================================================
# AnalyticsStore Tests
# =============================================================================

class TestAnalyticsStore:
    """Tests for in-memory analytics storage."""

    def test_store_initialization(self):
        """Store initializes empty."""
        store = AnalyticsStore()
        assert store.count() == 0

    def test_add_event(self):
        """Add single event to store."""
        store = AnalyticsStore()
        event = AnalyticsEvent(
            event_type="personalization",
            brand_id="energyx",
            product_id="energy_pro",
            timestamp=datetime.now(),
            data={}
        )
        
        store.add(event)
        assert store.count() == 1

    def test_add_multiple_events(self):
        """Add multiple events to store."""
        store = AnalyticsStore()
        for i in range(10):
            event = AnalyticsEvent(
                event_type="page_view",
                brand_id="energyx",
                product_id="energy_pro",
                timestamp=datetime.now(),
                data={"count": i}
            )
            store.add(event)
        
        assert store.count() == 10

    def test_get_events_by_brand(self):
        """Filter events by brand."""
        store = AnalyticsStore()
        
        # Add events for different brands
        store.add(AnalyticsEvent("page_view", "energyx", "energy_pro", datetime.now(), {}))
        store.add(AnalyticsEvent("page_view", "energyx", "energy_pro", datetime.now(), {}))
        store.add(AnalyticsEvent("page_view", "focuslab", "focus_max", datetime.now(), {}))
        
        energyx_events = store.get_by_brand("energyx")
        assert len(energyx_events) == 2
        
        focuslab_events = store.get_by_brand("focuslab")
        assert len(focuslab_events) == 1

    def test_get_events_by_type(self):
        """Filter events by type."""
        store = AnalyticsStore()
        
        store.add(AnalyticsEvent("page_view", "energyx", "energy_pro", datetime.now(), {}))
        store.add(AnalyticsEvent("personalization", "energyx", "energy_pro", datetime.now(), {}))
        store.add(AnalyticsEvent("page_view", "energyx", "energy_pro", datetime.now(), {}))
        
        page_views = store.get_by_type("page_view")
        assert len(page_views) == 2
        
        personalizations = store.get_by_type("personalization")
        assert len(personalizations) == 1

    def test_get_events_by_time_range(self):
        """Filter events by time range."""
        store = AnalyticsStore()
        
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        store.add(AnalyticsEvent("page_view", "energyx", "p1", now, {}))
        store.add(AnalyticsEvent("page_view", "energyx", "p1", yesterday, {}))
        store.add(AnalyticsEvent("page_view", "energyx", "p1", week_ago, {}))
        
        # Last 2 days
        recent = store.get_by_time_range(now - timedelta(days=2), now + timedelta(hours=1))
        assert len(recent) == 2

    def test_max_events_limit(self):
        """Store respects max events limit (memory protection)."""
        store = AnalyticsStore(max_events=100)
        
        # Add more than max
        for i in range(150):
            store.add(AnalyticsEvent("page_view", "test", "test", datetime.now(), {"i": i}))
        
        # Should be at max
        assert store.count() == 100
        # Oldest events should be removed (FIFO)

    def test_clear_events(self):
        """Clear all events from store."""
        store = AnalyticsStore()
        store.add(AnalyticsEvent("page_view", "test", "test", datetime.now(), {}))
        store.add(AnalyticsEvent("page_view", "test", "test", datetime.now(), {}))
        
        store.clear()
        assert store.count() == 0


# =============================================================================
# AnalyticsService Tests
# =============================================================================

class TestAnalyticsService:
    """Tests for analytics aggregation service."""

    def test_service_initialization(self):
        """Service initializes with store."""
        service = AnalyticsService()
        assert service is not None

    def test_track_page_view(self):
        """Track a page view event."""
        service = AnalyticsService()
        service.track_page_view(
            brand_id="energyx",
            product_id="energy_pro",
            page="landing"
        )
        
        assert service.store.count() == 1
        event = service.store.get_all()[0]
        assert event.event_type == "page_view"
        assert event.data["page"] == "landing"

    def test_track_form_start(self):
        """Track form start event."""
        service = AnalyticsService()
        service.track_form_start(
            brand_id="energyx",
            product_id="energy_pro"
        )
        
        assert service.store.count() == 1
        event = service.store.get_all()[0]
        assert event.event_type == "form_start"

    def test_track_personalization(self):
        """Track personalization completion event."""
        service = AnalyticsService()
        service.track_personalization(
            brand_id="energyx",
            product_id="energy_pro",
            user_data={
                "weight_kg": 75,
                "caffeine_sensitivity": "normal",
                "activity_time": "18:00"
            },
            result={
                "optimal_timing": "17:15",
                "response_time_ms": 45
            }
        )
        
        assert service.store.count() == 1
        event = service.store.get_all()[0]
        assert event.event_type == "personalization"
        assert event.data["user_data"]["weight_kg"] == 75
        assert event.data["result"]["optimal_timing"] == "17:15"

    def test_get_total_personalizations(self):
        """Get total number of personalizations."""
        service = AnalyticsService()
        
        # Add some events
        service.track_personalization("energyx", "p1", {}, {})
        service.track_personalization("energyx", "p2", {}, {})
        service.track_page_view("energyx", "p1", "landing")
        
        total = service.get_total_personalizations()
        assert total == 2

    def test_get_total_personalizations_by_brand(self):
        """Get personalizations filtered by brand."""
        service = AnalyticsService()
        
        service.track_personalization("energyx", "p1", {}, {})
        service.track_personalization("energyx", "p2", {}, {})
        service.track_personalization("focuslab", "p1", {}, {})
        
        total = service.get_total_personalizations(brand_id="energyx")
        assert total == 2

    def test_get_popular_products(self):
        """Get most popular products."""
        service = AnalyticsService()
        
        # Product A - 3 personalizations
        for _ in range(3):
            service.track_personalization("energyx", "product_a", {}, {})
        
        # Product B - 1 personalization
        service.track_personalization("energyx", "product_b", {}, {})
        
        # Product C - 5 personalizations
        for _ in range(5):
            service.track_personalization("focuslab", "product_c", {}, {})
        
        popular = service.get_popular_products(limit=2)
        
        assert len(popular) == 2
        assert popular[0]["product_id"] == "product_c"
        assert popular[0]["count"] == 5
        assert popular[1]["product_id"] == "product_a"
        assert popular[1]["count"] == 3

    def test_get_caffeine_sensitivity_distribution(self):
        """Get distribution of caffeine sensitivity."""
        service = AnalyticsService()
        
        # 3 normal, 2 slow, 1 fast
        for _ in range(3):
            service.track_personalization("b", "p", {"caffeine_sensitivity": "normal"}, {})
        for _ in range(2):
            service.track_personalization("b", "p", {"caffeine_sensitivity": "slow"}, {})
        service.track_personalization("b", "p", {"caffeine_sensitivity": "fast"}, {})
        
        dist = service.get_caffeine_sensitivity_distribution()
        
        assert dist["normal"] == 3
        assert dist["slow"] == 2
        assert dist["fast"] == 1

    def test_get_activity_time_distribution(self):
        """Get distribution of activity times."""
        service = AnalyticsService()
        
        # Various activity times
        service.track_personalization("b", "p", {"activity_time": "06:00"}, {})
        service.track_personalization("b", "p", {"activity_time": "07:30"}, {})
        service.track_personalization("b", "p", {"activity_time": "18:00"}, {})
        service.track_personalization("b", "p", {"activity_time": "19:30"}, {})
        service.track_personalization("b", "p", {"activity_time": "20:00"}, {})
        
        dist = service.get_activity_time_distribution()
        
        # Should be grouped by hour buckets
        assert "early_morning" in dist or "morning" in dist or len(dist) > 0

    def test_get_conversion_rate(self):
        """Calculate form start to personalization conversion rate."""
        service = AnalyticsService()
        
        # 10 form starts
        for _ in range(10):
            service.track_form_start("energyx", "p1")
        
        # 7 completions
        for _ in range(7):
            service.track_personalization("energyx", "p1", {}, {})
        
        rate = service.get_conversion_rate()
        assert rate == 70.0  # 70%

    def test_get_conversion_rate_by_brand(self):
        """Conversion rate filtered by brand."""
        service = AnalyticsService()
        
        # Brand A: 10 starts, 8 completions
        for _ in range(10):
            service.track_form_start("brand_a", "p1")
        for _ in range(8):
            service.track_personalization("brand_a", "p1", {}, {})
        
        # Brand B: 5 starts, 1 completion
        for _ in range(5):
            service.track_form_start("brand_b", "p1")
        service.track_personalization("brand_b", "p1", {}, {})
        
        rate_a = service.get_conversion_rate(brand_id="brand_a")
        rate_b = service.get_conversion_rate(brand_id="brand_b")
        
        assert rate_a == 80.0
        assert rate_b == 20.0

    def test_get_average_response_time(self):
        """Calculate average API response time."""
        service = AnalyticsService()
        
        service.track_personalization("b", "p", {}, {"response_time_ms": 50})
        service.track_personalization("b", "p", {}, {"response_time_ms": 30})
        service.track_personalization("b", "p", {}, {"response_time_ms": 40})
        
        avg = service.get_average_response_time()
        assert avg == 40.0

    def test_get_daily_stats(self):
        """Get daily statistics."""
        service = AnalyticsService()
        
        now = datetime.now()
        
        # Today's events
        service.track_personalization("b", "p", {}, {})
        service.track_personalization("b", "p", {}, {})
        service.track_page_view("b", "p", "landing")
        
        stats = service.get_daily_stats(now.date())
        
        assert stats["personalizations"] == 2
        assert stats["page_views"] == 1

    def test_get_weekly_trend(self):
        """Get weekly trend data."""
        service = AnalyticsService()
        
        # Just verify it returns proper structure
        trend = service.get_weekly_trend()
        assert len(trend) == 7
        assert all("date" in day and "count" in day for day in trend)


# =============================================================================
# Dashboard Data Tests
# =============================================================================

class TestDashboardData:
    """Tests for dashboard data generation."""

    def test_generate_dashboard_summary(self):
        """Generate complete dashboard summary."""
        service = AnalyticsService()
        
        # Populate with test data
        for i in range(20):
            service.track_page_view("energyx", "energy_pro", "landing")
        for i in range(15):
            service.track_form_start("energyx", "energy_pro")
        for i in range(10):
            service.track_personalization(
                "energyx", "energy_pro",
                {"caffeine_sensitivity": "normal" if i % 2 == 0 else "slow"},
                {"response_time_ms": 40 + i}
            )
        
        summary = service.get_dashboard_summary(brand_id="energyx")
        
        assert "total_personalizations" in summary
        assert "total_page_views" in summary
        assert "conversion_rate" in summary
        assert "avg_response_time" in summary
        assert "popular_products" in summary
        assert "caffeine_distribution" in summary
        assert "weekly_trend" in summary

    def test_dashboard_summary_empty_data(self):
        """Dashboard summary with no data."""
        service = AnalyticsService()
        summary = service.get_dashboard_summary(brand_id="nonexistent")
        
        assert summary["total_personalizations"] == 0
        assert summary["conversion_rate"] == 0.0

    def test_export_to_json(self):
        """Export analytics data to JSON."""
        service = AnalyticsService()
        service.track_personalization("b", "p", {}, {})
        
        json_data = service.export_to_json(brand_id="b")
        
        # Should be valid JSON
        parsed = json.loads(json_data)
        assert "events" in parsed
        assert "summary" in parsed


# =============================================================================
# Singleton/Global Instance Tests
# =============================================================================

class TestAnalyticsGlobal:
    """Tests for global analytics instance."""

    def test_get_analytics_service(self):
        """Get global analytics service instance."""
        service1 = get_analytics_service()
        service2 = get_analytics_service()
        
        # Should return same instance
        assert service1 is service2

    def test_reset_analytics_service(self):
        """Reset analytics service for testing."""
        service1 = get_analytics_service()
        service1.track_page_view("test", "test", "landing")
        
        reset_analytics_service()
        
        service2 = get_analytics_service()
        assert service2.store.count() == 0


# =============================================================================
# Performance Tests
# =============================================================================

class TestAnalyticsPerformance:
    """Performance tests for analytics."""

    def test_bulk_event_insertion(self):
        """Track many events quickly."""
        import time
        
        service = AnalyticsService()
        
        start = time.time()
        for i in range(1000):
            service.track_page_view("brand", "product", "landing")
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # Should complete in under 1 second
        assert service.store.count() == 1000

    def test_aggregation_performance(self):
        """Aggregations should be fast."""
        import time
        
        service = AnalyticsService()
        
        # Add 1000 events
        for i in range(1000):
            service.track_personalization(
                f"brand_{i % 3}",
                f"product_{i % 10}",
                {"caffeine_sensitivity": ["slow", "normal", "fast"][i % 3]},
                {"response_time_ms": 30 + (i % 50)}
            )
        
        start = time.time()
        summary = service.get_dashboard_summary(brand_id="brand_0")
        elapsed = time.time() - start
        
        assert elapsed < 0.5  # Dashboard should render in under 500ms


# =============================================================================
# Edge Cases
# =============================================================================

class TestAnalyticsEdgeCases:
    """Edge case tests."""

    def test_empty_user_data(self):
        """Handle missing user data gracefully."""
        service = AnalyticsService()
        service.track_personalization("b", "p", {}, {})
        
        # Should not crash
        dist = service.get_caffeine_sensitivity_distribution()
        assert "unknown" in dist or dist.get("unknown", 0) >= 0 or len(dist) == 0

    def test_invalid_activity_time(self):
        """Handle invalid activity time format."""
        service = AnalyticsService()
        service.track_personalization("b", "p", {"activity_time": "invalid"}, {})
        
        # Should not crash
        dist = service.get_activity_time_distribution()
        assert isinstance(dist, dict)

    def test_concurrent_access(self):
        """Thread-safe event addition."""
        import threading
        
        service = AnalyticsService()
        
        def add_events():
            for _ in range(100):
                service.track_page_view("b", "p", "landing")
        
        threads = [threading.Thread(target=add_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have all events (500 total)
        assert service.store.count() == 500
