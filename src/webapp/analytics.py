"""
MODULUS - Analytics Service
Session 17.x: Analytics tracking and dashboard for brand clients

This module provides:
- AnalyticsEvent: Data class for tracking events
- AnalyticsStore: In-memory storage for events (with optional persistence)
- AnalyticsService: Aggregation and metrics calculation
- Dashboard data generation for brand clients

Metrics tracked:
- Total personalizations
- Popular products
- Caffeine sensitivity distribution
- Activity time distribution
- Conversion rate (form start → completion)
- Average response time
- Weekly trends
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from collections import defaultdict
import threading
import json


# =============================================================================
# AnalyticsEvent - Data Class
# =============================================================================

@dataclass
class AnalyticsEvent:
    """
    Represents a single analytics event.
    
    Attributes:
        event_type: Type of event (page_view, form_start, personalization)
        brand_id: Brand identifier
        product_id: Product identifier
        timestamp: When the event occurred
        data: Additional event-specific data
        session_id: Optional session identifier
        user_agent: Optional user agent string
    """
    event_type: str
    brand_id: str
    product_id: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "brand_id": self.brand_id,
            "product_id": self.product_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "session_id": self.session_id,
            "user_agent": self.user_agent
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnalyticsEvent":
        """Create event from dictionary."""
        timestamp = d.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()
            
        return cls(
            event_type=d.get("event_type", "unknown"),
            brand_id=d.get("brand_id", "unknown"),
            product_id=d.get("product_id", "unknown"),
            timestamp=timestamp,
            data=d.get("data", {}),
            session_id=d.get("session_id"),
            user_agent=d.get("user_agent")
        )


# =============================================================================
# AnalyticsStore - In-Memory Storage
# =============================================================================

class AnalyticsStore:
    """
    Thread-safe in-memory storage for analytics events.
    
    Features:
    - FIFO eviction when max_events is reached
    - Filtering by brand, type, time range
    - Thread-safe operations
    
    Attributes:
        max_events: Maximum number of events to store (memory protection)
    """
    
    def __init__(self, max_events: int = 100000):
        """
        Initialize store.
        
        Args:
            max_events: Maximum events to keep in memory
        """
        self._events: List[AnalyticsEvent] = []
        self._max_events = max_events
        self._lock = threading.Lock()
    
    def add(self, event: AnalyticsEvent) -> None:
        """Add event to store (thread-safe)."""
        with self._lock:
            self._events.append(event)
            # FIFO eviction if over limit
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
    
    def count(self) -> int:
        """Get total event count."""
        with self._lock:
            return len(self._events)
    
    def get_all(self) -> List[AnalyticsEvent]:
        """Get all events (copy)."""
        with self._lock:
            return list(self._events)
    
    def get_by_brand(self, brand_id: str) -> List[AnalyticsEvent]:
        """Get events filtered by brand."""
        with self._lock:
            return [e for e in self._events if e.brand_id == brand_id]
    
    def get_by_type(self, event_type: str) -> List[AnalyticsEvent]:
        """Get events filtered by type."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]
    
    def get_by_time_range(
        self, 
        start: datetime, 
        end: datetime
    ) -> List[AnalyticsEvent]:
        """Get events within time range."""
        with self._lock:
            return [
                e for e in self._events 
                if start <= e.timestamp <= end
            ]
    
    def get_filtered(
        self,
        brand_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AnalyticsEvent]:
        """Get events with multiple filters."""
        with self._lock:
            result = self._events
            
            if brand_id:
                result = [e for e in result if e.brand_id == brand_id]
            if event_type:
                result = [e for e in result if e.event_type == event_type]
            if start_time:
                result = [e for e in result if e.timestamp >= start_time]
            if end_time:
                result = [e for e in result if e.timestamp <= end_time]
            
            return list(result)
    
    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            self._events = []


# =============================================================================
# AnalyticsService - Aggregation & Metrics
# =============================================================================

class AnalyticsService:
    """
    Service for tracking and aggregating analytics.
    
    Provides:
    - Event tracking methods
    - Metric calculations
    - Dashboard data generation
    """
    
    def __init__(self, store: Optional[AnalyticsStore] = None):
        """
        Initialize service.
        
        Args:
            store: Optional custom store (creates new if not provided)
        """
        self.store = store or AnalyticsStore()
    
    # -------------------------------------------------------------------------
    # Tracking Methods
    # -------------------------------------------------------------------------
    
    def _create_event(
        self,
        event_type: str,
        brand_id: str,
        product_id: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> AnalyticsEvent:
        """Create and return an analytics event."""
        return AnalyticsEvent(
            event_type=event_type,
            brand_id=brand_id,
            product_id=product_id,
            timestamp=timestamp or datetime.now(),
            data=data,
            session_id=session_id,
            user_agent=user_agent
        )
    
    def track_page_view(
        self,
        brand_id: str,
        product_id: str,
        page: str,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Track a page view event."""
        event = self._create_event(
            event_type="page_view",
            brand_id=brand_id,
            product_id=product_id,
            data={"page": page},
            session_id=session_id,
            user_agent=user_agent
        )
        self.store.add(event)
    
    def track_form_start(
        self,
        brand_id: str,
        product_id: str,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Track form start event."""
        event = self._create_event(
            event_type="form_start",
            brand_id=brand_id,
            product_id=product_id,
            data={},
            session_id=session_id,
            user_agent=user_agent
        )
        self.store.add(event)
    
    def track_personalization(
        self,
        brand_id: str,
        product_id: str,
        user_data: Dict[str, Any],
        result: Dict[str, Any],
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Track personalization completion event."""
        event = self._create_event(
            event_type="personalization",
            brand_id=brand_id,
            product_id=product_id,
            data={
                "user_data": user_data,
                "result": result
            },
            session_id=session_id,
            user_agent=user_agent
        )
        self.store.add(event)
    
    # -------------------------------------------------------------------------
    # Metric Calculations
    # -------------------------------------------------------------------------
    
    def get_total_personalizations(
        self, 
        brand_id: Optional[str] = None
    ) -> int:
        """Get total number of personalizations."""
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="personalization"
        )
        return len(events)
    
    def get_total_page_views(
        self,
        brand_id: Optional[str] = None
    ) -> int:
        """Get total number of page views."""
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="page_view"
        )
        return len(events)
    
    def get_total_form_starts(
        self,
        brand_id: Optional[str] = None
    ) -> int:
        """Get total number of form starts."""
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="form_start"
        )
        return len(events)
    
    def get_popular_products(
        self,
        brand_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most popular products by personalization count."""
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="personalization"
        )
        
        # Count by product
        counts: Dict[str, int] = defaultdict(int)
        for event in events:
            key = f"{event.brand_id}:{event.product_id}"
            counts[event.product_id] += 1
        
        # Sort by count
        sorted_products = sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"product_id": product_id, "count": count}
            for product_id, count in sorted_products
        ]
    
    def get_caffeine_sensitivity_distribution(
        self,
        brand_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get distribution of caffeine sensitivity."""
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="personalization"
        )
        
        distribution: Dict[str, int] = defaultdict(int)
        for event in events:
            user_data = event.data.get("user_data", {})
            sensitivity = user_data.get("caffeine_sensitivity", "unknown")
            distribution[sensitivity] += 1
        
        return dict(distribution)
    
    def get_activity_time_distribution(
        self,
        brand_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get distribution of activity times.
        Groups by time buckets: early_morning, morning, afternoon, evening, night
        """
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="personalization"
        )
        
        buckets = {
            "early_morning": 0,  # 05:00-08:59
            "morning": 0,        # 09:00-11:59
            "afternoon": 0,      # 12:00-16:59
            "evening": 0,        # 17:00-20:59
            "night": 0           # 21:00-04:59
        }
        
        for event in events:
            user_data = event.data.get("user_data", {})
            activity_time = user_data.get("activity_time", "")
            
            try:
                if ":" in activity_time:
                    hour = int(activity_time.split(":")[0])
                    
                    if 5 <= hour < 9:
                        buckets["early_morning"] += 1
                    elif 9 <= hour < 12:
                        buckets["morning"] += 1
                    elif 12 <= hour < 17:
                        buckets["afternoon"] += 1
                    elif 17 <= hour < 21:
                        buckets["evening"] += 1
                    else:
                        buckets["night"] += 1
            except (ValueError, IndexError):
                pass  # Skip invalid times
        
        return buckets
    
    def get_conversion_rate(
        self,
        brand_id: Optional[str] = None
    ) -> float:
        """
        Calculate conversion rate (form starts to completions).
        Returns percentage (0-100).
        """
        form_starts = self.get_total_form_starts(brand_id)
        completions = self.get_total_personalizations(brand_id)
        
        if form_starts == 0:
            return 0.0
        
        return (completions / form_starts) * 100
    
    def get_average_response_time(
        self,
        brand_id: Optional[str] = None
    ) -> float:
        """Get average API response time in milliseconds."""
        events = self.store.get_filtered(
            brand_id=brand_id,
            event_type="personalization"
        )
        
        times = []
        for event in events:
            result = event.data.get("result", {})
            response_time = result.get("response_time_ms")
            if response_time is not None:
                times.append(response_time)
        
        if not times:
            return 0.0
        
        return sum(times) / len(times)
    
    def get_daily_stats(
        self,
        day: date,
        brand_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get statistics for a specific day."""
        start = datetime.combine(day, datetime.min.time())
        end = datetime.combine(day, datetime.max.time())
        
        all_events = self.store.get_filtered(
            brand_id=brand_id,
            start_time=start,
            end_time=end
        )
        
        stats = {
            "page_views": 0,
            "form_starts": 0,
            "personalizations": 0
        }
        
        for event in all_events:
            if event.event_type == "page_view":
                stats["page_views"] += 1
            elif event.event_type == "form_start":
                stats["form_starts"] += 1
            elif event.event_type == "personalization":
                stats["personalizations"] += 1
        
        return stats
    
    def get_weekly_trend(
        self,
        brand_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get daily counts for the last 7 days."""
        today = date.today()
        trend = []
        
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            stats = self.get_daily_stats(day, brand_id)
            trend.append({
                "date": day.isoformat(),
                "count": stats["personalizations"],
                "page_views": stats["page_views"]
            })
        
        return trend
    
    # -------------------------------------------------------------------------
    # Dashboard Summary
    # -------------------------------------------------------------------------
    
    def get_dashboard_summary(
        self,
        brand_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete dashboard summary.
        
        Returns dict with all metrics needed for dashboard display.
        """
        return {
            "total_personalizations": self.get_total_personalizations(brand_id),
            "total_page_views": self.get_total_page_views(brand_id),
            "total_form_starts": self.get_total_form_starts(brand_id),
            "conversion_rate": round(self.get_conversion_rate(brand_id), 1),
            "avg_response_time": round(self.get_average_response_time(brand_id), 1),
            "popular_products": self.get_popular_products(brand_id, limit=5),
            "caffeine_distribution": self.get_caffeine_sensitivity_distribution(brand_id),
            "activity_distribution": self.get_activity_time_distribution(brand_id),
            "weekly_trend": self.get_weekly_trend(brand_id),
            "generated_at": datetime.now().isoformat()
        }
    
    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------
    
    def export_to_json(
        self,
        brand_id: Optional[str] = None,
        include_events: bool = True
    ) -> str:
        """
        Export analytics data to JSON string.
        
        Args:
            brand_id: Optional filter by brand
            include_events: Whether to include raw events
        
        Returns:
            JSON string with summary and optionally events
        """
        data = {
            "summary": self.get_dashboard_summary(brand_id),
            "exported_at": datetime.now().isoformat()
        }
        
        if include_events:
            events = self.store.get_filtered(brand_id=brand_id)
            data["events"] = [e.to_dict() for e in events]
        
        return json.dumps(data, indent=2)


# =============================================================================
# Global Instance (Singleton Pattern)
# =============================================================================

_analytics_service: Optional[AnalyticsService] = None
_service_lock = threading.Lock()


def get_analytics_service() -> AnalyticsService:
    """Get global analytics service instance."""
    global _analytics_service
    
    with _service_lock:
        if _analytics_service is None:
            _analytics_service = AnalyticsService()
        return _analytics_service


def reset_analytics_service() -> None:
    """Reset analytics service (for testing)."""
    global _analytics_service
    
    with _service_lock:
        _analytics_service = None
