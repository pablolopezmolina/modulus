"""
MODULUS Wearable — Manual self-reported inputs
==============================================

The watch only sees physiology. A lot of what drives recovery and longevity
is behavioural / subjective, so the app accepts manual inputs:

- Bowel movements (count, Bristol stool scale).
- Supplements (compound, dose, route, timing).
- Peptides (name, dose, route, timing).
- Emotional / mood state (valence + arousal, or a label).
- Subjective fatigue on waking and before sleep (1..10).
- Post-meal nap desire (0..10).

All entries share a common envelope (:class:`ManualInput`) so they can be
stored together in :attr:`DailyRecord.manual` and replayed by the scoring
engines (e.g. subjective fatigue feeds the readiness score).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class ManualKind(str, Enum):
    bowel = "bowel"
    supplement = "supplement"
    peptide = "peptide"
    mood = "mood"
    fatigue_wake = "fatigue_wake"
    fatigue_sleep = "fatigue_sleep"
    nap_desire = "nap_desire"


class _Base(BaseModel):
    """Common envelope for every manual entry."""

    kind: ManualKind
    timestamp: datetime = Field(default_factory=datetime.now)
    note: Optional[str] = Field(default=None, max_length=1000)


DoseUnit = Literal["mg", "mcg", "g", "iu", "ml", "drops", "caps", "units"]
Route = Literal["oral", "sublingual", "subcutaneous", "intramuscular", "topical", "nasal", "other"]


class BowelMovement(_Base):
    """A single bowel movement. Bristol scale 1 (hard) .. 7 (liquid)."""

    kind: Literal[ManualKind.bowel] = ManualKind.bowel
    bristol_scale: Optional[int] = Field(default=None, ge=1, le=7)
    count: int = Field(default=1, ge=1, le=20)


class Supplement(_Base):
    """A supplement intake event."""

    kind: Literal[ManualKind.supplement] = ManualKind.supplement
    compound: str = Field(..., min_length=1, max_length=120)
    dose: float = Field(..., gt=0)
    unit: DoseUnit = "mg"
    route: Route = "oral"


class Peptide(_Base):
    """A peptide administration event."""

    kind: Literal[ManualKind.peptide] = ManualKind.peptide
    name: str = Field(..., min_length=1, max_length=120)
    dose: float = Field(..., gt=0)
    unit: DoseUnit = "mcg"
    route: Route = "subcutaneous"


class MoodState(_Base):
    """
    Emotional state on the circumplex model of affect (Russell, 1980):
    valence (unpleasant -1 .. +1 pleasant) and arousal (calm 0 .. 1 activated).
    An optional free label can also be given.
    """

    kind: Literal[ManualKind.mood] = ManualKind.mood
    valence: float = Field(..., ge=-1.0, le=1.0)
    arousal: float = Field(default=0.5, ge=0.0, le=1.0)
    label: Optional[str] = Field(default=None, max_length=60)


class FatigueOnWaking(_Base):
    """Subjective tiredness right after waking (1 = fully rested, 10 = exhausted)."""

    kind: Literal[ManualKind.fatigue_wake] = ManualKind.fatigue_wake
    rating: int = Field(..., ge=1, le=10)


class FatigueBeforeSleep(_Base):
    """Subjective tiredness right before bed (1 = wide awake, 10 = exhausted)."""

    kind: Literal[ManualKind.fatigue_sleep] = ManualKind.fatigue_sleep
    rating: int = Field(..., ge=1, le=10)


class NapDesire(_Base):
    """Desire to nap after eating (0 = none, 10 = irresistible)."""

    kind: Literal[ManualKind.nap_desire] = ManualKind.nap_desire
    rating: int = Field(..., ge=0, le=10)


ManualInput = Union[
    BowelMovement,
    Supplement,
    Peptide,
    MoodState,
    FatigueOnWaking,
    FatigueBeforeSleep,
    NapDesire,
]

_KIND_TO_MODEL = {
    ManualKind.bowel: BowelMovement,
    ManualKind.supplement: Supplement,
    ManualKind.peptide: Peptide,
    ManualKind.mood: MoodState,
    ManualKind.fatigue_wake: FatigueOnWaking,
    ManualKind.fatigue_sleep: FatigueBeforeSleep,
    ManualKind.nap_desire: NapDesire,
}


def parse_manual(data: dict) -> ManualInput:
    """Reconstruct the correct manual-input subtype from a stored dict."""
    kind = ManualKind(data["kind"])
    model = _KIND_TO_MODEL[kind]
    return model.model_validate(data)
