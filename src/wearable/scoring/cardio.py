"""
Cardio fitness (Apple-Watch-style)
==================================

Apple Watch's "Cardio Fitness" *is* a VO2max estimate, categorised against
age/sex norms. The Fenix 5 Plus already computes a VO2max (Firstbeat
analytics), so the primary path is simply to ingest and categorise it. When
VO2max is absent we fall back to the Uth–Sørensen estimate from the
HRmax/HRrest ratio (Uth et al., *Eur J Appl Physiol* 2004):

    VO2max ≈ 15.3 × (HRmax / HRrest)

Categorisation uses the Cooper Institute / ACSM age- and sex-based percentile
bands (the same normative family Apple and Garmin reference). A **fitness age**
is derived from where the VO2max sits relative to the age-50th-percentile curve.

VO2max is the single best-validated predictor of all-cause mortality among
fitness metrics (Mandsager et al., *JAMA Netw Open* 2018), which is why it
anchors the longevity score too.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from src.wearable.baseline import clamp
from src.wearable.models import DailyRecord, Sex, UserProfile
from src.wearable.scoring.common import ScoreComponent, ScoreResult

# Approx VO2max (ml/kg/min) for the 50th percentile by sex and age decade.
# Derived from Cooper Institute normative tables (ages 20-29 .. 60+).
_VO2_P50 = {
    Sex.male: {20: 48.0, 30: 46.0, 40: 43.0, 50: 39.0, 60: 35.0},
    Sex.female: {20: 41.0, 30: 39.0, 40: 36.0, 50: 33.0, 60: 30.0},
}


def _decade(age: int) -> int:
    return max(20, min(60, (age // 10) * 10))


def _p50_for(sex: Sex, age: int) -> float:
    return _VO2_P50[sex][_decade(age)]


def estimate_vo2max_from_hr(hr_max: float, hr_rest: float) -> Optional[float]:
    """Uth–Sørensen estimate; returns None if inputs are unusable."""
    if hr_rest <= 0 or hr_max <= hr_rest:
        return None
    return 15.3 * (hr_max / hr_rest)


def fitness_age(vo2max: float, sex: Sex, actual_age: int) -> int:
    """
    Age at which ``vo2max`` would equal the 50th-percentile norm. Walks the
    normative curve and returns the closest decade-interpolated age.
    """
    table = _VO2_P50[sex]
    ages = sorted(table)
    # If fitter than the youngest p50, cap at 20; if worse than oldest, extrapolate.
    if vo2max >= table[ages[0]]:
        return 20
    if vo2max <= table[ages[-1]]:
        # Linear extrapolation beyond 60 using the last slope.
        slope = (table[60] - table[50]) / 10.0  # negative
        extra = (vo2max - table[60]) / slope if slope != 0 else 0
        return int(round(min(90, 60 + extra)))
    for a0, a1 in zip(ages, ages[1:]):
        v0, v1 = table[a0], table[a1]
        if v1 <= vo2max <= v0:
            frac = (v0 - vo2max) / (v0 - v1) if v0 != v1 else 0
            return int(round(a0 + frac * (a1 - a0)))
    return actual_age


def _band(score: float) -> str:
    if score >= 80:
        return "superior"
    if score >= 60:
        return "above_average"
    if score >= 40:
        return "average"
    if score >= 20:
        return "below_average"
    return "low"


def score_cardio_fitness(
    record: DailyRecord,
    profile: UserProfile,
) -> ScoreResult:
    """
    Categorise cardio fitness for ``record`` against age/sex norms.

    The 0..100 score maps VO2max to a percentile-like position around the
    age/sex median (50th percentile -> 50), and the notes carry the VO2max,
    fitness age and category.
    """
    age = profile.age_on(record.date)
    components: List[ScoreComponent] = []
    notes: List[str] = []
    missing: List[str] = []

    vo2 = record.metrics.vo2max if record.metrics else None
    source = "device"
    if vo2 is None:
        rhr = record.best_resting_hr()
        if rhr is not None:
            vo2 = estimate_vo2max_from_hr(profile.hr_max(record.date), rhr)
            source = "estimated_from_hr"
    if vo2 is None:
        missing.append("vo2max")
        return ScoreResult(kind="cardio_fitness", score=0.0, band="low", components=[],
                           notes=["No VO2max and no resting HR to estimate it."],
                           inputs_missing=missing)

    p50 = _p50_for(profile.sex, age)
    # Map VO2max to a 0..100 score: p50 -> 50, and ±35% spans the full range.
    span = 0.35 * p50
    score = clamp(50.0 + (vo2 - p50) / span * 50.0)
    fage = fitness_age(vo2, profile.sex, age)

    components.append(ScoreComponent(
        name="vo2max", value=score, weight=1.0,
        detail=f"{vo2:.1f} ml/kg/min ({source}); age/sex median {p50:.0f}",
    ))
    notes.append(f"Estimated VO2max {vo2:.1f} ml/kg/min.")
    notes.append(f"Fitness age ~{fage} (chronological {age}).")
    if fage < age:
        notes.append("Cardiorespiratory fitness above your age group — protective for longevity.")

    return ScoreResult(
        kind="cardio_fitness",
        score=round(score, 1),
        band=_band(score),
        components=components,
        notes=notes,
        inputs_missing=missing,
    )


def cardio_facts(record: DailyRecord, profile: UserProfile) -> Tuple[Optional[float], Optional[int]]:
    """Return ``(vo2max, fitness_age)`` for downstream engines; None if absent."""
    vo2 = record.metrics.vo2max if record.metrics else None
    if vo2 is None:
        rhr = record.best_resting_hr()
        if rhr is not None:
            vo2 = estimate_vo2max_from_hr(profile.hr_max(record.date), rhr)
    if vo2 is None:
        return None, None
    return vo2, fitness_age(vo2, profile.sex, profile.age_on(record.date))
