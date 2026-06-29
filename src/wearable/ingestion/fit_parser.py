"""
Garmin FIT file parser
======================

Parses the ``.FIT`` files a Garmin Fenix 5 Plus produces (sleep, wellness /
monitoring, HRV status, VO2max) into :class:`DailyRecord`s. This is the primary
data path: it works fully offline from files exported via Garmin Connect
("Export Original") or copied over USB from ``GARMIN/Activity`` and
``GARMIN/Monitor`` — no credentials, no unofficial API.

FIT is a profiled binary format; field names vary slightly across firmware and
file types, so every extractor tries a list of candidate field names and
tolerates anything missing. The decode step (file IO) is separated from the
:func:`build_records` aggregation so the mapping logic is unit-testable without
real binary files.

Decoding uses the official ``garmin-fit-sdk`` (pure Python). If it is not
installed, :data:`FIT_AVAILABLE` is ``False`` and constructing
:class:`FitFileSource` raises a clear error, while :func:`build_records`
still works on pre-decoded message dicts.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_cls, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.wearable.ingestion.base import DataSource
from src.wearable.models import DailyMetrics, DailyRecord, SleepRecord, SleepStages

try:  # pragma: no cover - exercised by environment, not logic
    from garmin_fit_sdk import Decoder, Stream

    FIT_AVAILABLE = True
except Exception:  # pragma: no cover
    Decoder = None  # type: ignore
    Stream = None  # type: ignore
    FIT_AVAILABLE = False


# Sleep-stage enum values used by Garmin's ``sleep_level`` message.
_SLEEP_LEVEL = {0: "awake", 1: "awake", 2: "light", 3: "deep", 4: "rem"}


def _first(msg: Dict[str, Any], *names: str) -> Any:
    """Return the first present, non-None field among ``names``."""
    for n in names:
        if n in msg and msg[n] is not None:
            return msg[n]
    return None


def _as_date(value: Any) -> Optional[date_cls]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_cls):
        return value
    return None


class _DayBuilder:
    """Mutable accumulator for one calendar day, finalised into models."""

    def __init__(self, day: date_cls):
        self.day = day
        self.deep = 0.0
        self.light = 0.0
        self.rem = 0.0
        self.awake = 0.0
        self.has_stages = False
        self.latency: Optional[float] = None
        self.awakenings: Optional[int] = None
        self.bedtime: Optional[datetime] = None
        self.wake_time: Optional[datetime] = None
        self.sleep_hr: Optional[float] = None
        self.sleep_lowest_hr: Optional[float] = None
        self.sleep_hrv: Optional[float] = None
        self.sleep_resp: Optional[float] = None
        self.sleep_spo2: Optional[float] = None

        self.resting_hr: Optional[float] = None
        self.hrv_overnight: Optional[float] = None
        self.respiration: Optional[float] = None
        self.spo2: Optional[float] = None
        self.stress: Optional[int] = None
        self.steps: Optional[int] = None
        self.active_kcal: Optional[float] = None
        self.intensity_minutes: Optional[int] = None
        self.vo2max: Optional[float] = None
        self.body_temp_dev: Optional[float] = None

    def to_record(self) -> DailyRecord:
        sleep: Optional[SleepRecord] = None
        tib = self.deep + self.light + self.rem + self.awake
        if self.has_stages and tib > 0:
            sleep = SleepRecord(
                date=self.day,
                bedtime=self.bedtime,
                wake_time=self.wake_time,
                time_in_bed_min=round(tib, 1),
                stages=SleepStages(
                    deep_min=round(self.deep, 1),
                    light_min=round(self.light, 1),
                    rem_min=round(self.rem, 1),
                    awake_min=round(self.awake, 1),
                ),
                sleep_onset_latency_min=self.latency or 0.0,
                awakenings=self.awakenings or 0,
                avg_hr_bpm=self.sleep_hr,
                lowest_hr_bpm=self.sleep_lowest_hr,
                avg_hrv_ms=self.sleep_hrv,
                avg_respiration_brpm=self.sleep_resp,
                avg_spo2_pct=self.sleep_spo2,
            )

        metrics = DailyMetrics(
            date=self.day,
            resting_hr_bpm=self.resting_hr,
            hrv_overnight_ms=self.hrv_overnight or self.sleep_hrv,
            respiration_brpm=self.respiration or self.sleep_resp,
            spo2_avg_pct=self.spo2 or self.sleep_spo2,
            stress_avg=self.stress,
            steps=self.steps,
            active_kcal=self.active_kcal,
            intensity_minutes=self.intensity_minutes,
            vo2max=self.vo2max,
            body_temp_deviation_c=self.body_temp_dev,
        )
        return DailyRecord(date=self.day, sleep=sleep, metrics=metrics, manual=[])


def build_records(messages: Dict[str, List[Dict[str, Any]]]) -> List[DailyRecord]:
    """
    Aggregate decoded FIT messages (``{message_name: [field_dict, ...]}``) into
    per-day :class:`DailyRecord`s. Pure function — no IO — so it is fully unit
    testable with hand-built message dicts.
    """
    builders: Dict[date_cls, _DayBuilder] = {}

    def builder_for(day: Optional[date_cls]) -> Optional[_DayBuilder]:
        if day is None:
            return None
        if day not in builders:
            builders[day] = _DayBuilder(day)
        return builders[day]

    # --- Sleep stages (time-series of sleep_level) ---
    _accumulate_sleep_levels(messages, builders, builder_for)

    # --- Sleep assessment summary (scores, respiration, awakenings) ---
    for msg in messages.get("sleep_assessment_mesgs", []):
        day = _as_date(_first(msg, "timestamp", "local_timestamp"))
        b = builder_for(day)
        if b is None:
            continue
        b.awakenings = _first(msg, "awakenings_count", "num_awakenings") or b.awakenings
        b.sleep_resp = _first(msg, "average_respiration_rate", "avg_respiration_rate") or b.sleep_resp
        b.sleep_hrv = _first(msg, "average_hrv", "avg_hrv") or b.sleep_hrv

    # --- HRV status (overnight rMSSD) ---
    for msg in messages.get("hrv_status_summary_mesgs", []):
        day = _as_date(_first(msg, "timestamp", "local_timestamp"))
        b = builder_for(day)
        if b is None:
            continue
        b.hrv_overnight = _first(msg, "last_night_average", "weekly_average") or b.hrv_overnight

    # --- Monitoring (steps, resting HR, calories, intensity minutes) ---
    _accumulate_monitoring(messages, builders, builder_for)

    # --- VO2max (max_met_data: max_met in METs -> ml/kg/min via ×3.5) ---
    for msg in messages.get("max_met_data_mesgs", []):
        day = _as_date(_first(msg, "timestamp", "update_time", "local_timestamp"))
        vo2 = _first(msg, "vo2_max", "vo2max")
        if vo2 is None:
            mets = _first(msg, "max_met")
            vo2 = mets * 3.5 if mets is not None else None
        b = builder_for(day)
        if b is not None and vo2 is not None:
            b.vo2max = float(vo2)

    # --- Respiration / SpO2 / Stress daily summaries ---
    for msg in messages.get("respiration_rate_mesgs", []):
        day = _as_date(_first(msg, "timestamp"))
        rate = _first(msg, "respiration_rate")
        b = builder_for(day)
        if b is not None and rate is not None and rate > 0:
            b.respiration = float(rate)
    for msg in messages.get("stress_level_mesgs", []):
        day = _as_date(_first(msg, "stress_level_time", "timestamp"))
        val = _first(msg, "stress_level_value")
        b = builder_for(day)
        if b is not None and val is not None and val >= 0:
            b.stress = int(val)

    return [builders[d].to_record() for d in sorted(builders)]


def _accumulate_sleep_levels(messages, builders, builder_for) -> None:
    """Sum minutes per stage from consecutive ``sleep_level`` samples."""
    samples = messages.get("sleep_level_mesgs", [])
    timed = []
    for msg in samples:
        ts = _first(msg, "timestamp")
        lvl = _first(msg, "sleep_level")
        if isinstance(ts, datetime) and lvl is not None:
            timed.append((ts, int(lvl)))
    timed.sort(key=lambda t: t[0])
    for (ts, lvl), (ts_next, _) in zip(timed, timed[1:]):
        minutes = (ts_next - ts).total_seconds() / 60.0
        if minutes <= 0 or minutes > 240:  # guard against gaps between sessions
            continue
        stage = _SLEEP_LEVEL.get(lvl, "light")
        # Attribute the night to the wake day (the date of the last sample).
        b = builder_for(timed[-1][0].date())
        if b is None:
            continue
        b.has_stages = True
        setattr(b, stage, getattr(b, stage) + minutes)
        if b.bedtime is None:
            b.bedtime = timed[0][0]
        b.wake_time = timed[-1][0]


def _accumulate_monitoring(messages, builders, builder_for) -> None:
    """Pull daily totals from ``monitoring``/``monitoring_info`` messages."""
    # Per-day running max for cumulative fields (steps reset at midnight).
    steps_by_day: Dict[date_cls, int] = defaultdict(int)
    for msg in messages.get("monitoring_mesgs", []):
        day = _as_date(_first(msg, "timestamp", "local_timestamp"))
        if day is None:
            continue
        b = builder_for(day)
        if b is None:
            continue
        steps = _first(msg, "steps", "cumulative_steps")
        if steps is not None:
            steps_by_day[day] = max(steps_by_day[day], int(steps))
        rhr = _first(msg, "resting_heart_rate")
        if rhr is not None and rhr > 0:
            b.resting_hr = float(rhr)
        kcal = _first(msg, "active_calories", "calories")
        if kcal is not None:
            b.active_kcal = float(kcal)
        intensity = _first(msg, "moderate_activity_minutes", "intensity_minutes")
        if intensity is not None:
            b.intensity_minutes = int(intensity)

    for day, steps in steps_by_day.items():
        b = builder_for(day)
        if b is not None:
            b.steps = steps


def decode_fit_file(path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Decode a single FIT file into ``{message_name: [field_dict, ...]}``.

    The garmin-fit-sdk returns keys like ``'sleep_level_mesgs'``; we keep them
    verbatim so :func:`build_records` can dispatch on them.
    """
    if not FIT_AVAILABLE:
        raise RuntimeError(
            "garmin-fit-sdk is not installed. Run `pip install garmin-fit-sdk` "
            "to parse FIT files."
        )
    stream = Stream.from_file(path)
    decoder = Decoder(stream)
    messages, _errors = decoder.read()
    return messages


class FitFileSource(DataSource):
    """A :class:`DataSource` backed by one or more Garmin FIT files."""

    def __init__(self, paths: Sequence[str]):
        if not FIT_AVAILABLE:
            raise RuntimeError(
                "garmin-fit-sdk is not installed. Run `pip install garmin-fit-sdk`."
            )
        self._paths = [str(p) for p in paths]

    @classmethod
    def from_directory(cls, directory: str, pattern: str = "*.fit") -> "FitFileSource":
        """Build a source from every FIT file in ``directory`` (case-insensitive)."""
        base = Path(directory)
        files = sorted(set(base.glob(pattern)) | set(base.glob(pattern.upper())))
        return cls([str(f) for f in files])

    def records(
        self,
        start: Optional[date_cls] = None,
        end: Optional[date_cls] = None,
    ) -> List[DailyRecord]:
        merged: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for path in self._paths:
            for key, msgs in decode_fit_file(path).items():
                if isinstance(msgs, list):
                    merged[key].extend(msgs)
        records = build_records(merged)
        if start:
            records = [r for r in records if r.date >= start]
        if end:
            records = [r for r in records if r.date <= end]
        return records
