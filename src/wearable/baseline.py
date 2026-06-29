"""
MODULUS Wearable — Personal baseline
====================================

Recovery / readiness scores are meaningless in absolute terms: a HRV of 45 ms
is excellent for one person and poor for another. WHOOP and Oura both score
against a rolling *personal* baseline. This module provides a small, dependency
-light rolling-window statistic used everywhere downstream.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Baseline:
    """Mean / standard deviation of a metric over a personal history window."""

    mean: float
    std: float
    n: int

    @classmethod
    def from_values(cls, values: Iterable[float]) -> Optional["Baseline"]:
        vals: List[float] = [float(v) for v in values if v is not None and math.isfinite(float(v))]
        if not vals:
            return None
        n = len(vals)
        mean = sum(vals) / n
        if n < 2:
            std = 0.0
        else:
            var = sum((v - mean) ** 2 for v in vals) / (n - 1)
            std = math.sqrt(var)
        return cls(mean=mean, std=std, n=n)

    def z_score(self, value: float) -> float:
        """Standard score of ``value`` against the baseline (0 if std==0)."""
        if self.std <= 0:
            return 0.0
        return (value - self.mean) / self.std

    def pct_of_baseline(self, value: float) -> float:
        """``value`` as a percentage of the baseline mean (100 == on baseline)."""
        if self.mean == 0:
            return 100.0
        return 100.0 * value / self.mean


def gaussian_percentile(z: float) -> float:
    """
    Cumulative normal probability for a z-score, returned as a 0..100
    percentile. Uses the erf-based CDF; good enough for scoring display.
    """
    return 100.0 * 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp ``value`` to the inclusive range [lo, hi]."""
    return max(lo, min(hi, value))


def lerp_score(value: float, low: float, high: float, invert: bool = False) -> float:
    """
    Linearly map ``value`` in [low, high] to a 0..100 score.

    ``low`` maps to 0 and ``high`` maps to 100 (clamped). When ``invert`` is
    True the mapping is reversed (``low`` -> 100), which is handy for
    "lower is better" metrics such as resting heart rate or sleep latency.
    """
    if high == low:
        return 50.0
    frac = (value - low) / (high - low)
    score = 100.0 * frac
    if invert:
        score = 100.0 - score
    return clamp(score)
