"""Common result types shared by every scoring engine."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScoreComponent(BaseModel):
    """A single named contributor to an overall score."""

    name: str
    value: float = Field(..., ge=0, le=100, description="Sub-score 0..100")
    weight: float = Field(..., ge=0, description="Relative weight in the blend")
    detail: Optional[str] = Field(default=None, description="Human-readable explanation")


class ScoreResult(BaseModel):
    """Output of a scoring engine: an overall 0..100 score plus its breakdown."""

    kind: str = Field(..., description="Which engine produced this (e.g. 'recovery')")
    score: float = Field(..., ge=0, le=100)
    band: str = Field(..., description="Qualitative band, e.g. 'green' / 'good'")
    components: List[ScoreComponent] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    inputs_missing: List[str] = Field(
        default_factory=list, description="Metrics that were unavailable"
    )

    @staticmethod
    def blend(components: List[ScoreComponent]) -> float:
        """Weighted mean of component values; 0 if there is no weight."""
        total_w = sum(c.weight for c in components)
        if total_w <= 0:
            return 0.0
        return sum(c.value * c.weight for c in components) / total_w

    def as_summary(self) -> Dict[str, float]:
        """Flat dict of component name -> value, plus the overall score."""
        out = {c.name: round(c.value, 1) for c in self.components}
        out["overall"] = round(self.score, 1)
        return out


def band_traffic_light(score: float) -> str:
    """WHOOP-style three-colour band."""
    if score >= 67:
        return "green"
    if score >= 34:
        return "yellow"
    return "red"


def band_quality(score: float) -> str:
    """Oura-style qualitative band."""
    if score >= 85:
        return "optimal"
    if score >= 70:
        return "good"
    if score >= 60:
        return "fair"
    return "pay_attention"
