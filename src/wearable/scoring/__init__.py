"""
MODULUS Wearable — Scoring engines
==================================

Transparent approximations of the constructs measured by commercial wearables:

- :mod:`sleep`     — Oura/WHOOP-style sleep quality score.
- :mod:`recovery`  — WHOOP-style HRV-driven recovery (%).
- :mod:`readiness` — Oura-style daily readiness.
- :mod:`cardio`    — Apple-Watch-style cardio fitness (VO2max + fitness age).
- :mod:`longevity` — Composite longevity index from mortality-linked metrics.

None of these reproduce the proprietary algorithms exactly (those are
unpublished); they target the same physiology with documented, tunable maths.
"""

from src.wearable.scoring.common import ScoreComponent, ScoreResult
from src.wearable.scoring.sleep import score_sleep
from src.wearable.scoring.recovery import score_recovery
from src.wearable.scoring.readiness import score_readiness
from src.wearable.scoring.cardio import score_cardio_fitness
from src.wearable.scoring.longevity import score_longevity

__all__ = [
    "ScoreComponent",
    "ScoreResult",
    "score_sleep",
    "score_recovery",
    "score_readiness",
    "score_cardio_fitness",
    "score_longevity",
]
