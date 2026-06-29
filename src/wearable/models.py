"""
MODULUS Wearable — Sensor data models
=====================================

Pydantic v2 models describing the physiological data a Garmin Fenix 5 Plus
records and that downstream scoring engines consume.

All models are validated and JSON-serialisable. Numeric fields carry
physiological bounds so that corrupt FIT data is rejected early.
"""

from __future__ import annotations

import math
from datetime import date as date_cls, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator


class Sex(str, Enum):
    """Biological sex — required for age/sex-normalised fitness norms."""

    male = "male"
    female = "female"


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    """Static traits used to normalise scores (cardio norms, HR max, etc.)."""

    user_id: str = Field(default="me", description="Stable user identifier")
    birth_year: int = Field(..., ge=1900, le=2025, description="Year of birth")
    sex: Sex = Field(..., description="Biological sex")
    height_cm: Optional[float] = Field(default=None, gt=50, lt=260)
    weight_kg: Optional[float] = Field(default=None, gt=20, lt=400)
    sleep_need_hours: float = Field(
        default=8.0,
        ge=4.0,
        le=12.0,
        description="Personal sleep need; WHOOP/Oura compare TST against this.",
    )

    def age_on(self, on: date_cls) -> int:
        """Age in whole years on a given date (birthday approximated by year)."""
        return max(0, on.year - self.birth_year)

    def hr_max(self, on: Optional[date_cls] = None) -> float:
        """Estimated maximum heart rate (Tanaka 2001: 208 - 0.7 * age)."""
        ref = on or datetime.now().date()
        return 208.0 - 0.7 * self.age_on(ref)


# ---------------------------------------------------------------------------
# Sleep
# ---------------------------------------------------------------------------


class SleepStages(BaseModel):
    """Minutes spent in each sleep stage during a single sleep period."""

    deep_min: float = Field(default=0.0, ge=0, le=1440)
    light_min: float = Field(default=0.0, ge=0, le=1440)
    rem_min: float = Field(default=0.0, ge=0, le=1440)
    awake_min: float = Field(default=0.0, ge=0, le=1440)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def asleep_min(self) -> float:
        """Total time actually asleep (deep + light + rem)."""
        return self.deep_min + self.light_min + self.rem_min

    def fraction(self, stage: str) -> float:
        """Fraction of *asleep* time spent in ``stage`` (0..1)."""
        total = self.asleep_min
        if total <= 0:
            return 0.0
        return float(getattr(self, f"{stage}_min")) / total


class SleepRecord(BaseModel):
    """A single night's sleep as recorded by the watch."""

    date: date_cls = Field(..., description="Calendar date the sleep is attributed to (wake day)")
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None

    time_in_bed_min: float = Field(..., ge=0, le=1440)
    stages: SleepStages = Field(default_factory=SleepStages)

    sleep_onset_latency_min: float = Field(
        default=0.0, ge=0, le=600, description="Minutes from bed to first sleep"
    )
    awakenings: int = Field(default=0, ge=0, description="Number of awakenings")

    avg_hr_bpm: Optional[float] = Field(default=None, ge=20, le=220)
    lowest_hr_bpm: Optional[float] = Field(default=None, ge=20, le=220)
    avg_hrv_ms: Optional[float] = Field(
        default=None, ge=0, le=500, description="Overnight HRV (rMSSD, ms)"
    )
    avg_respiration_brpm: Optional[float] = Field(default=None, ge=3, le=40)
    avg_spo2_pct: Optional[float] = Field(default=None, ge=50, le=100)

    @field_validator("avg_hr_bpm", "lowest_hr_bpm", "avg_hrv_ms")
    @classmethod
    def _finite(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("value must be finite")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_sleep_min(self) -> float:
        return self.stages.asleep_min

    @computed_field  # type: ignore[prop-decorator]
    @property
    def efficiency_pct(self) -> float:
        """Sleep efficiency = asleep / time-in-bed (%)."""
        if self.time_in_bed_min <= 0:
            return 0.0
        return 100.0 * self.stages.asleep_min / self.time_in_bed_min


# ---------------------------------------------------------------------------
# Daily (non-sleep) metrics
# ---------------------------------------------------------------------------


class DailyMetrics(BaseModel):
    """Daytime / all-day aggregates recorded by the watch for one calendar day."""

    date: date_cls

    resting_hr_bpm: Optional[float] = Field(default=None, ge=20, le=150)
    hrv_overnight_ms: Optional[float] = Field(
        default=None, ge=0, le=500, description="Garmin overnight HRV status (rMSSD, ms)"
    )
    respiration_brpm: Optional[float] = Field(default=None, ge=3, le=40)
    spo2_avg_pct: Optional[float] = Field(default=None, ge=50, le=100)

    body_battery_high: Optional[int] = Field(default=None, ge=0, le=100)
    body_battery_low: Optional[int] = Field(default=None, ge=0, le=100)
    stress_avg: Optional[int] = Field(default=None, ge=0, le=100)

    steps: Optional[int] = Field(default=None, ge=0, le=200000)
    active_kcal: Optional[float] = Field(default=None, ge=0, le=20000)
    intensity_minutes: Optional[int] = Field(
        default=None, ge=0, le=5000, description="Garmin moderate+vigorous minutes (weighted)"
    )
    vo2max: Optional[float] = Field(
        default=None, ge=10, le=90, description="Estimated VO2max (ml/kg/min)"
    )
    body_temp_deviation_c: Optional[float] = Field(
        default=None, ge=-5, le=5, description="Skin/body temp deviation from baseline (°C)"
    )

    @field_validator("resting_hr_bpm", "hrv_overnight_ms", "vo2max")
    @classmethod
    def _finite(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("value must be finite")
        return v


# ---------------------------------------------------------------------------
# Aggregated daily record
# ---------------------------------------------------------------------------


class DailyRecord(BaseModel):
    """
    Everything known about a single day: the watch metrics, the sleep that
    led into it, and any manual self-reported inputs.

    ``manual`` holds serialised :class:`~src.wearable.manual.ManualInput`
    payloads (kept as dicts here to avoid a circular import; the manual
    module owns their schema).
    """

    date: date_cls
    sleep: Optional[SleepRecord] = None
    metrics: Optional[DailyMetrics] = None
    manual: List[Dict] = Field(default_factory=list)

    def best_hrv_ms(self) -> Optional[float]:
        """Prefer the dedicated overnight HRV, fall back to the sleep record's."""
        if self.metrics and self.metrics.hrv_overnight_ms is not None:
            return self.metrics.hrv_overnight_ms
        if self.sleep and self.sleep.avg_hrv_ms is not None:
            return self.sleep.avg_hrv_ms
        return None

    def best_resting_hr(self) -> Optional[float]:
        """Prefer the all-day resting HR, fall back to the sleep low HR."""
        if self.metrics and self.metrics.resting_hr_bpm is not None:
            return self.metrics.resting_hr_bpm
        if self.sleep and self.sleep.lowest_hr_bpm is not None:
            return self.sleep.lowest_hr_bpm
        return None
