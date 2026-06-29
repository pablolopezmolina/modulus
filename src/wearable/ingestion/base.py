"""Abstract data-source interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date as date_cls
from typing import List, Optional

from src.wearable.models import DailyRecord


class DataSource(ABC):
    """A source of :class:`DailyRecord`s, regardless of origin."""

    @abstractmethod
    def records(
        self,
        start: Optional[date_cls] = None,
        end: Optional[date_cls] = None,
    ) -> List[DailyRecord]:
        """Return daily records in ``[start, end]`` (inclusive), sorted by date."""
        raise NotImplementedError
