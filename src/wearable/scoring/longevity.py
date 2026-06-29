"""
Longevity index (composite)
===========================

No wearable vendor publishes a validated "longevity score" — and neither do we
claim one. This is a **transparent heuristic composite** of metrics that each
have a documented association with all-cause mortality, intended for personal
trend tracking, *not* clinical prediction.

Components and evidence:

- **Cardiorespiratory fitness (VO2max)** — strongest modifiable predictor of
  all-cause mortality; benefit continues at the high end with no observed
  ceiling (Mandsager et al., *JAMA Netw Open* 2018). Weight 0.35.
- **Daily steps** — risk drops steeply up to ~7,000-8,000 steps/day, plateauing
  after (Paluch et al., *Lancet Public Health* 2022). Weight 0.20.
- **Sleep** — duration (U-shaped optimum ~7-8 h) *and* regularity, with
  regularity an even stronger mortality predictor than duration
  (Windred et al., *Sleep* 2023). Weight 0.20.
- **Resting heart rate** — elevated RHR is associated with higher mortality
  (Zhang et al., *CMAJ* 2016). Weight 0.15.
- **HRV** — reduced HRV is associated with higher mortality / morbidity
  (Jarczok et al., 2022 meta-analysis). Weight 0.10.

The composite is reported as a 0..100 index plus a qualitative "pace" label.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import List, Optional

from src.wearable.baseline import clamp, lerp_score
from src.wearable.models import DailyRecord, UserProfile
from src.wearable.scoring.cardio import cardio_facts
from src.wearable.scoring.common import ScoreComponent, ScoreResult


@dataclass(frozen=True)
class LongevityWeights:
    cardio: float = 0.35
    steps: float = 0.20
    sleep: float = 0.20
    resting_hr: float = 0.15
    hrv: float = 0.10


def _mean(values: List[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.mean(vals) if vals else None


def _sleep_midpoint_minutes(rec: DailyRecord) -> Optional[float]:
    """Minute-of-day of the sleep midpoint, for regularity (handles wrap past midnight)."""
    s = rec.sleep
    if not s or not s.bedtime or not s.wake_time:
        return None
    mid = s.bedtime + (s.wake_time - s.bedtime) / 2
    return mid.hour * 60.0 + mid.minute


def score_longevity(
    records: List[DailyRecord],
    profile: UserProfile,
    weights: Optional[LongevityWeights] = None,
) -> ScoreResult:
    """
    Compute a composite longevity index from a window of daily records
    (typically the trailing 7-30 days).
    """
    w = weights or LongevityWeights()
    components: List[ScoreComponent] = []
    missing: List[str] = []
    notes: List[str] = []

    if not records:
        return ScoreResult(kind="longevity", score=0.0, band="unknown", components=[],
                           notes=["No records provided."], inputs_missing=["records"])

    latest = max(records, key=lambda r: r.date)

    # --- Cardio fitness ---
    vo2, fage = cardio_facts(latest, profile)
    if vo2 is not None:
        # Reuse the same age/sex anchoring as the cardio engine via lerp:
        # 25 ml/kg/min -> 0, 55 -> 100 (broad adult span; weighting handles age).
        cardio_score = lerp_score(vo2, 25.0, 55.0)
        components.append(ScoreComponent(name="cardio", value=cardio_score, weight=w.cardio,
                                         detail=f"VO2max {vo2:.1f}, fitness age ~{fage}"))
    else:
        missing.append("vo2max")

    # --- Steps ---
    steps = _mean([r.metrics.steps for r in records if r.metrics and r.metrics.steps is not None])
    if steps is not None:
        # Benefit ramps 2,000 -> 8,000 then plateaus.
        steps_score = lerp_score(steps, 2000.0, 8000.0)
        components.append(ScoreComponent(name="steps", value=steps_score, weight=w.steps,
                                         detail=f"avg {steps:.0f} steps/day"))
    else:
        missing.append("steps")

    # --- Sleep duration + regularity ---
    durations = [r.sleep.total_sleep_min / 60.0 for r in records if r.sleep]
    sleep_subscores: List[float] = []
    if durations:
        avg_dur = statistics.mean(durations)
        # U-shaped: 7.5h ideal, penalise away from it (±2.5h -> 0).
        dur_score = clamp(100.0 - abs(avg_dur - 7.5) / 2.5 * 100.0)
        sleep_subscores.append(dur_score)
    midpoints = [m for m in (_sleep_midpoint_minutes(r) for r in records) if m is not None]
    if len(midpoints) >= 3:
        reg_sd = statistics.pstdev(midpoints)
        # SD of sleep midpoint: <30 min -> 100, >120 min -> 0.
        reg_score = lerp_score(reg_sd, 120.0, 30.0)
        sleep_subscores.append(reg_score)
        if reg_sd > 90:
            notes.append("Irregular sleep timing — regularity strongly predicts longevity.")
    if sleep_subscores:
        components.append(ScoreComponent(name="sleep", value=statistics.mean(sleep_subscores),
                                         weight=w.sleep,
                                         detail=f"{len(durations)} nights analysed"))
    else:
        missing.append("sleep")

    # --- Resting HR ---
    rhrs = [r.best_resting_hr() for r in records]
    rhr = _mean([v for v in rhrs if v is not None])
    if rhr is not None:
        # 45 bpm -> 100, 85 bpm -> 0.
        rhr_score = lerp_score(rhr, 85.0, 45.0)
        components.append(ScoreComponent(name="resting_hr", value=rhr_score, weight=w.resting_hr,
                                         detail=f"avg {rhr:.0f} bpm"))
    else:
        missing.append("resting_hr")

    # --- HRV ---
    hrvs = [r.best_hrv_ms() for r in records]
    hrv = _mean([v for v in hrvs if v is not None])
    if hrv is not None:
        hrv_score = lerp_score(hrv, 20.0, 90.0)
        components.append(ScoreComponent(name="hrv", value=hrv_score, weight=w.hrv,
                                         detail=f"avg {hrv:.0f} ms"))
    else:
        missing.append("hrv")

    if not components:
        return ScoreResult(kind="longevity", score=0.0, band="unknown", components=[],
                           notes=["Insufficient data."], inputs_missing=missing)

    overall = ScoreResult.blend(components)
    band = (
        "excellent" if overall >= 80 else
        "good" if overall >= 65 else
        "moderate" if overall >= 50 else
        "needs_work"
    )
    notes.append(
        "Heuristic composite of mortality-linked metrics — for personal tracking, "
        "not medical advice."
    )

    return ScoreResult(
        kind="longevity",
        score=round(overall, 1),
        band=band,
        components=components,
        notes=notes,
        inputs_missing=missing,
    )
