"""
Deterministic synthetic data source.

Generates physiologically plausible daily records for a date range using a
seeded RNG. Used by tests and the demo so the scoring stack can be exercised
without real FIT files.
"""

from __future__ import annotations

import random
from datetime import date as date_cls, datetime, time, timedelta
from typing import List, Optional

from src.wearable.ingestion.base import DataSource
from src.wearable.models import DailyMetrics, DailyRecord, SleepRecord, SleepStages


class SyntheticSource(DataSource):
    """Seeded generator of realistic-looking daily records."""

    def __init__(self, start: date_cls, days: int = 30, seed: int = 42):
        self._start = start
        self._days = days
        self._seed = seed

    def records(
        self,
        start: Optional[date_cls] = None,
        end: Optional[date_cls] = None,
    ) -> List[DailyRecord]:
        rng = random.Random(self._seed)
        out: List[DailyRecord] = []
        for i in range(self._days):
            d = self._start + timedelta(days=i)
            if start and d < start:
                # Still advance the RNG so output stays deterministic per index.
                _ = rng.random()
                continue
            if end and d > end:
                break
            out.append(self._make_day(d, rng))
        return out

    def _make_day(self, d: date_cls, rng: random.Random) -> DailyRecord:
        tib = rng.uniform(420, 510)  # time in bed, minutes
        eff = rng.uniform(0.82, 0.95)
        asleep = tib * eff
        deep = asleep * rng.uniform(0.13, 0.22)
        rem = asleep * rng.uniform(0.18, 0.26)
        light = asleep - deep - rem
        awake = tib - asleep

        bedtime = datetime.combine(d - timedelta(days=1), time(hour=23, minute=rng.randint(0, 59)))
        wake_time = bedtime + timedelta(minutes=tib)

        sleep = SleepRecord(
            date=d,
            bedtime=bedtime,
            wake_time=wake_time,
            time_in_bed_min=round(tib, 1),
            stages=SleepStages(
                deep_min=round(deep, 1),
                light_min=round(light, 1),
                rem_min=round(rem, 1),
                awake_min=round(awake, 1),
            ),
            sleep_onset_latency_min=round(rng.uniform(5, 25), 1),
            awakenings=rng.randint(0, 4),
            avg_hr_bpm=round(rng.uniform(50, 60), 1),
            lowest_hr_bpm=round(rng.uniform(42, 50), 1),
            avg_hrv_ms=round(rng.uniform(45, 75), 1),
            avg_respiration_brpm=round(rng.uniform(13, 16), 1),
            avg_spo2_pct=round(rng.uniform(94, 98), 1),
        )

        metrics = DailyMetrics(
            date=d,
            resting_hr_bpm=round(rng.uniform(48, 56), 1),
            hrv_overnight_ms=sleep.avg_hrv_ms,
            respiration_brpm=sleep.avg_respiration_brpm,
            spo2_avg_pct=sleep.avg_spo2_pct,
            body_battery_high=rng.randint(70, 100),
            body_battery_low=rng.randint(5, 30),
            stress_avg=rng.randint(20, 45),
            steps=rng.randint(5000, 14000),
            active_kcal=round(rng.uniform(400, 900), 0),
            intensity_minutes=rng.randint(20, 90),
            vo2max=round(rng.uniform(44, 52), 1),
            body_temp_deviation_c=round(rng.uniform(-0.3, 0.3), 2),
        )

        return DailyRecord(date=d, sleep=sleep, metrics=metrics, manual=[])
