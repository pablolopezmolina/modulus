"""
Readiness score (Oura-style)
============================

Oura's readiness blends several "contributors": previous-night sleep, sleep
balance, resting heart rate, HRV balance, body temperature, recovery index and
activity balance (Oura documentation). It also reacts to how you *feel*.

This implementation covers the contributors that a Fenix 5 Plus + manual inputs
can supply:

- **Previous sleep**  — last night's sleep score.
- **HRV balance**     — overnight HRV vs personal baseline.
- **Resting HR**      — RHR vs baseline (inverse).
- **Body temperature**— deviation from baseline (illness / cycle / overtraining).
- **Subjective**      — manual fatigue-on-waking rating (the user's own read).

Subjective wake fatigue is included because readiness is ultimately about
whether you're ready for the day, and self-report adds signal the sensors miss.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.wearable.baseline import Baseline, clamp, gaussian_percentile
from src.wearable.manual import ManualKind
from src.wearable.models import DailyRecord
from src.wearable.scoring.common import ScoreComponent, ScoreResult, band_quality
from src.wearable.scoring.sleep import score_sleep


@dataclass(frozen=True)
class ReadinessWeights:
    previous_sleep: float = 0.30
    hrv_balance: float = 0.25
    resting_hr: float = 0.20
    body_temperature: float = 0.10
    subjective: float = 0.15


def _latest_wake_fatigue(record: DailyRecord) -> Optional[int]:
    ratings = [
        e.get("rating")
        for e in record.manual
        if e.get("kind") == ManualKind.fatigue_wake.value and e.get("rating") is not None
    ]
    return ratings[-1] if ratings else None


def score_readiness(
    record: DailyRecord,
    hrv_baseline: Optional[Baseline] = None,
    rhr_baseline: Optional[Baseline] = None,
    temp_baseline: Optional[Baseline] = None,
    sleep_need_hours: float = 8.0,
    weights: Optional[ReadinessWeights] = None,
) -> ScoreResult:
    """Compute an Oura-style readiness score (0..100) for ``record``."""
    w = weights or ReadinessWeights()
    components = []
    missing = []
    notes = []

    # --- Previous sleep ---
    if record.sleep is not None:
        sleep_res = score_sleep(record.sleep, sleep_need_hours=sleep_need_hours)
        components.append(ScoreComponent(name="previous_sleep", value=sleep_res.score,
                                         weight=w.previous_sleep,
                                         detail=f"sleep score {sleep_res.score:.0f}"))
    else:
        missing.append("sleep")

    # --- HRV balance ---
    hrv = record.best_hrv_ms()
    if hrv is not None and hrv_baseline is not None and hrv_baseline.std > 0:
        hrv_score = gaussian_percentile(hrv_baseline.z_score(hrv))
        components.append(ScoreComponent(name="hrv_balance", value=hrv_score,
                                         weight=w.hrv_balance,
                                         detail=f"{hrv:.0f} ms vs {hrv_baseline.mean:.0f} ms"))
    elif hrv is not None:
        components.append(ScoreComponent(name="hrv_balance",
                                         value=clamp((hrv - 20.0) / 80.0 * 100.0),
                                         weight=w.hrv_balance,
                                         detail=f"{hrv:.0f} ms (no baseline yet)"))
    else:
        missing.append("hrv")

    # --- Resting HR ---
    rhr = record.best_resting_hr()
    if rhr is not None and rhr_baseline is not None and rhr_baseline.std > 0:
        rhr_score = gaussian_percentile(-rhr_baseline.z_score(rhr))
        components.append(ScoreComponent(name="resting_hr", value=rhr_score,
                                         weight=w.resting_hr,
                                         detail=f"{rhr:.0f} bpm vs {rhr_baseline.mean:.0f} bpm"))
    elif rhr is not None:
        components.append(ScoreComponent(name="resting_hr",
                                         value=clamp((80.0 - rhr) / 40.0 * 100.0),
                                         weight=w.resting_hr,
                                         detail=f"{rhr:.0f} bpm (no baseline yet)"))
    else:
        missing.append("resting_hr")

    # --- Body temperature ---
    temp_dev = record.metrics.body_temp_deviation_c if record.metrics else None
    if temp_dev is not None:
        # 0 deviation -> 100; ±1°C -> ~0. Either direction penalised.
        temp_score = clamp(100.0 - abs(temp_dev) * 100.0)
        components.append(ScoreComponent(name="body_temperature", value=temp_score,
                                         weight=w.body_temperature,
                                         detail=f"{temp_dev:+.1f}°C vs baseline"))
        if abs(temp_dev) >= 0.5:
            notes.append("Body temperature deviating from baseline.")

    # --- Subjective wake fatigue ---
    fatigue = _latest_wake_fatigue(record)
    if fatigue is not None:
        # 1 (rested) -> 100, 10 (exhausted) -> 0.
        subj = clamp((10 - fatigue) / 9.0 * 100.0)
        components.append(ScoreComponent(name="subjective", value=subj,
                                         weight=w.subjective,
                                         detail=f"wake fatigue {fatigue}/10"))

    if not components:
        return ScoreResult(kind="readiness", score=0.0, band="pay_attention",
                           components=[], notes=["Insufficient data."],
                           inputs_missing=missing)

    overall = ScoreResult.blend(components)
    band = band_quality(overall)
    if band == "pay_attention":
        notes.append("Readiness low — consider an easy day.")

    return ScoreResult(
        kind="readiness",
        score=round(overall, 1),
        band=band,
        components=components,
        notes=notes,
        inputs_missing=missing,
    )
