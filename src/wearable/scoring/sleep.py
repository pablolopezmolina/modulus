"""
Sleep score (Oura / WHOOP-style)
================================

Combines the components both vendors are known to use, with transparent maths:

- **Duration**   — total sleep time vs. personal need (WHOOP "sleep need").
- **Efficiency** — asleep / time-in-bed. Healthy adults ~85-95 %.
- **REM**        — REM as a fraction of sleep; ~20-25 % is typical/ideal.
- **Deep**       — slow-wave sleep; ~13-23 % is typical/ideal.
- **Latency**    — time to fall asleep; ~10-20 min is healthy.
- **Restfulness**— penalised by awakenings.

Stage references: Hirshkowitz et al., *Sleep Health* 2015 (duration);
Ohayon et al., *Sleep* 2004 (stage normative values).

The weights below are exposed as a dataclass so they can be tuned to better
track a specific device's output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.wearable.baseline import clamp, lerp_score
from src.wearable.models import SleepRecord
from src.wearable.scoring.common import ScoreComponent, ScoreResult, band_quality


@dataclass(frozen=True)
class SleepWeights:
    duration: float = 0.35
    efficiency: float = 0.20
    rem: float = 0.15
    deep: float = 0.15
    latency: float = 0.075
    restfulness: float = 0.075


def _triangular(value: float, lo: float, ideal_lo: float, ideal_hi: float, hi: float) -> float:
    """
    Plateau/triangular scorer: 100 inside [ideal_lo, ideal_hi], ramping to 0
    at ``lo`` below and ``hi`` above. Used for "a healthy band" metrics where
    both too little and too much are sub-optimal (REM %, deep %).
    """
    if value < ideal_lo:
        return lerp_score(value, lo, ideal_lo)
    if value > ideal_hi:
        return lerp_score(value, hi, ideal_hi)  # inverted ramp: hi->0, ideal_hi->100
    return 100.0


def score_sleep(
    sleep: SleepRecord,
    sleep_need_hours: float = 8.0,
    weights: Optional[SleepWeights] = None,
) -> ScoreResult:
    """Compute a 0..100 sleep score for one night."""
    w = weights or SleepWeights()
    components = []
    missing = []

    need_min = sleep_need_hours * 60.0
    tst = sleep.total_sleep_min
    duration_score = clamp(100.0 * tst / need_min) if need_min > 0 else 0.0
    components.append(
        ScoreComponent(
            name="duration",
            value=duration_score,
            weight=w.duration,
            detail=f"{tst/60:.1f}h of {sleep_need_hours:.1f}h need",
        )
    )

    eff = sleep.efficiency_pct
    eff_score = lerp_score(eff, 75.0, 95.0)
    components.append(
        ScoreComponent(name="efficiency", value=eff_score, weight=w.efficiency,
                       detail=f"{eff:.0f}% efficiency")
    )

    if tst > 0:
        rem_pct = 100.0 * sleep.stages.fraction("rem")
        deep_pct = 100.0 * sleep.stages.fraction("deep")
        rem_score = _triangular(rem_pct, 8.0, 20.0, 25.0, 40.0)
        deep_score = _triangular(deep_pct, 5.0, 13.0, 23.0, 35.0)
        components.append(ScoreComponent(name="rem", value=rem_score, weight=w.rem,
                                         detail=f"{rem_pct:.0f}% REM"))
        components.append(ScoreComponent(name="deep", value=deep_score, weight=w.deep,
                                         detail=f"{deep_pct:.0f}% deep"))
    else:
        missing.append("sleep_stages")

    lat_score = lerp_score(sleep.sleep_onset_latency_min, 45.0, 5.0, invert=False)
    # lerp with low=45 -> 0, high=5 -> 100 means shorter latency scores higher.
    components.append(ScoreComponent(name="latency", value=lat_score, weight=w.latency,
                                     detail=f"{sleep.sleep_onset_latency_min:.0f} min to sleep"))

    # Restfulness: 0 awakenings -> 100, 8+ -> 0.
    rest_score = lerp_score(float(sleep.awakenings), 8.0, 0.0)
    components.append(ScoreComponent(name="restfulness", value=rest_score, weight=w.restfulness,
                                     detail=f"{sleep.awakenings} awakenings"))

    overall = ScoreResult.blend(components)
    notes = []
    if duration_score < 70:
        notes.append("Sleep duration below personal need.")
    if eff < 85:
        notes.append("Low sleep efficiency — time in bed not well used.")

    return ScoreResult(
        kind="sleep",
        score=round(overall, 1),
        band=band_quality(overall),
        components=components,
        notes=notes,
        inputs_missing=missing,
    )
