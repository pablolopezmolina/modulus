"""
Recovery score (WHOOP-style)
============================

WHOOP's recovery is dominated by **heart-rate variability** measured during
sleep, contextualised against the user's own rolling baseline, with resting
heart rate, sleep quality and respiratory rate as supporting signals
(see WHOOP's published methodology overviews; the exact blend is proprietary).

This implementation:

1. Scores overnight HRV as a percentile of the personal baseline (higher = better).
   HRV is the single strongest driver — autonomic / parasympathetic tone is a
   well-established readiness marker (Plews et al., *Sports Med* 2013).
2. Scores resting HR inversely against baseline (an elevated RHR suppresses
   recovery).
3. Folds in the night's sleep score.
4. Penalises respiratory-rate deviation from baseline (an early illness signal).

All weights are tunable. Output is a 0..100 % with a traffic-light band, the
same shape WHOOP presents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.wearable.baseline import Baseline, clamp, gaussian_percentile
from src.wearable.models import DailyRecord
from src.wearable.scoring.common import ScoreComponent, ScoreResult, band_traffic_light
from src.wearable.scoring.sleep import score_sleep


@dataclass(frozen=True)
class RecoveryWeights:
    hrv: float = 0.50
    resting_hr: float = 0.25
    sleep: float = 0.20
    respiration: float = 0.05


def score_recovery(
    record: DailyRecord,
    hrv_baseline: Optional[Baseline] = None,
    rhr_baseline: Optional[Baseline] = None,
    resp_baseline: Optional[Baseline] = None,
    sleep_need_hours: float = 8.0,
    weights: Optional[RecoveryWeights] = None,
) -> ScoreResult:
    """
    Compute a WHOOP-style recovery percentage for ``record``.

    Baselines should be built from the trailing ~30-60 days (excluding today).
    When a baseline is missing the component is scored against fixed
    physiological anchors so the engine still returns a usable number.
    """
    w = weights or RecoveryWeights()
    components = []
    missing = []
    notes = []

    # --- HRV (parasympathetic tone) ---
    hrv = record.best_hrv_ms()
    if hrv is not None:
        if hrv_baseline is not None and hrv_baseline.std > 0:
            hrv_score = gaussian_percentile(hrv_baseline.z_score(hrv))
            detail = f"{hrv:.0f} ms vs baseline {hrv_baseline.mean:.0f} ms"
        else:
            # No baseline: anchor 20 ms -> 0, 100 ms -> 100 (rough adult span).
            hrv_score = clamp((hrv - 20.0) / (100.0 - 20.0) * 100.0)
            detail = f"{hrv:.0f} ms (no baseline yet)"
        components.append(ScoreComponent(name="hrv", value=hrv_score, weight=w.hrv, detail=detail))
    else:
        missing.append("hrv")

    # --- Resting heart rate (inverse) ---
    rhr = record.best_resting_hr()
    if rhr is not None:
        if rhr_baseline is not None and rhr_baseline.std > 0:
            # Lower-than-baseline RHR is good -> invert the z-score.
            rhr_score = gaussian_percentile(-rhr_baseline.z_score(rhr))
            detail = f"{rhr:.0f} bpm vs baseline {rhr_baseline.mean:.0f} bpm"
        else:
            # Anchor 40 bpm -> 100, 80 bpm -> 0.
            rhr_score = clamp((80.0 - rhr) / (80.0 - 40.0) * 100.0)
            detail = f"{rhr:.0f} bpm (no baseline yet)"
        components.append(ScoreComponent(name="resting_hr", value=rhr_score,
                                         weight=w.resting_hr, detail=detail))
    else:
        missing.append("resting_hr")

    # --- Sleep ---
    if record.sleep is not None:
        sleep_res = score_sleep(record.sleep, sleep_need_hours=sleep_need_hours)
        components.append(ScoreComponent(name="sleep", value=sleep_res.score,
                                         weight=w.sleep, detail=f"sleep score {sleep_res.score:.0f}"))
    else:
        missing.append("sleep")

    # --- Respiratory rate stability ---
    resp = None
    if record.metrics and record.metrics.respiration_brpm is not None:
        resp = record.metrics.respiration_brpm
    elif record.sleep and record.sleep.avg_respiration_brpm is not None:
        resp = record.sleep.avg_respiration_brpm
    if resp is not None and resp_baseline is not None and resp_baseline.std > 0:
        # Deviation in EITHER direction is penalised.
        dev = abs(resp_baseline.z_score(resp))
        resp_score = clamp(100.0 - dev * 33.0)  # ~3 SD deviation -> 0
        components.append(ScoreComponent(name="respiration", value=resp_score,
                                         weight=w.respiration,
                                         detail=f"{resp:.1f} brpm vs baseline {resp_baseline.mean:.1f}"))
        if dev >= 1.5:
            notes.append("Respiratory rate elevated vs baseline — possible strain/illness.")

    if not components:
        notes.append("Insufficient data to compute recovery.")
        return ScoreResult(kind="recovery", score=0.0, band="red", components=[],
                           notes=notes, inputs_missing=missing)

    overall = ScoreResult.blend(components)
    band = band_traffic_light(overall)
    if band == "red":
        notes.append("Low recovery — prioritise rest, avoid high strain today.")
    elif band == "green":
        notes.append("Well recovered — your body can take on strain today.")

    return ScoreResult(
        kind="recovery",
        score=round(overall, 1),
        band=band,
        components=components,
        notes=notes,
        inputs_missing=missing,
    )
