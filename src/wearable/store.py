"""
MODULUS Wearable — Persistence
==============================

A deliberately simple JSON-file store: one file per user under a base
directory, holding their profile and a date-keyed map of daily records.
Good enough for a single-user personal app; swap for a real DB later behind
the same :class:`HealthStore` interface.
"""

from __future__ import annotations

import json
from datetime import date as date_cls
from pathlib import Path
from typing import Dict, List, Optional

from src.wearable.manual import ManualInput, parse_manual
from src.wearable.models import DailyRecord, UserProfile


class HealthStore:
    """JSON-backed store for one or more users' daily records + profile."""

    def __init__(self, base_dir: str):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str) -> Path:
        safe = "".join(c for c in user_id if c.isalnum() or c in "-_") or "user"
        return self._base / f"{safe}.json"

    def _load_raw(self, user_id: str) -> Dict:
        path = self._path(user_id)
        if not path.exists():
            return {"profile": None, "records": {}}
        return json.loads(path.read_text())

    def _save_raw(self, user_id: str, data: Dict) -> None:
        self._path(user_id).write_text(json.dumps(data, indent=2, default=str))

    # --- Profile ---

    def save_profile(self, profile: UserProfile) -> None:
        data = self._load_raw(profile.user_id)
        data["profile"] = profile.model_dump(mode="json")
        self._save_raw(profile.user_id, data)

    def get_profile(self, user_id: str = "me") -> Optional[UserProfile]:
        data = self._load_raw(user_id)
        if not data.get("profile"):
            return None
        return UserProfile.model_validate(data["profile"])

    # --- Records ---

    def upsert_record(self, record: DailyRecord, user_id: str = "me") -> None:
        data = self._load_raw(user_id)
        data["records"][str(record.date)] = record.model_dump(mode="json")
        self._save_raw(user_id, data)

    def upsert_many(self, records: List[DailyRecord], user_id: str = "me") -> int:
        data = self._load_raw(user_id)
        for record in records:
            data["records"][str(record.date)] = record.model_dump(mode="json")
        self._save_raw(user_id, data)
        return len(records)

    def get_record(self, day: date_cls, user_id: str = "me") -> Optional[DailyRecord]:
        data = self._load_raw(user_id)
        raw = data["records"].get(str(day))
        return DailyRecord.model_validate(raw) if raw else None

    def get_records(
        self,
        user_id: str = "me",
        start: Optional[date_cls] = None,
        end: Optional[date_cls] = None,
    ) -> List[DailyRecord]:
        data = self._load_raw(user_id)
        records = [DailyRecord.model_validate(r) for r in data["records"].values()]
        if start:
            records = [r for r in records if r.date >= start]
        if end:
            records = [r for r in records if r.date <= end]
        return sorted(records, key=lambda r: r.date)

    # --- Manual inputs ---

    def add_manual(self, day: date_cls, entry: ManualInput, user_id: str = "me") -> DailyRecord:
        """Append a manual input to a day's record, creating the day if needed."""
        record = self.get_record(day, user_id) or DailyRecord(date=day)
        record.manual.append(entry.model_dump(mode="json"))
        self.upsert_record(record, user_id)
        return record

    def list_manual(self, day: date_cls, user_id: str = "me") -> List[ManualInput]:
        record = self.get_record(day, user_id)
        if not record:
            return []
        return [parse_manual(e) for e in record.manual]
