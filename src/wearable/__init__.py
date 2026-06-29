"""
MODULUS Wearable — Garmin Health Analytics
==========================================

Personal health analytics layer that ingests sensor data recorded by a
Garmin Fenix 5 Plus (and compatible devices) and computes recovery, sleep,
readiness, cardio-fitness and longevity scores.

Design philosophy
-----------------
The proprietary scoring algorithms of WHOOP, Oura and Apple Watch are
**closed source and unpublished**. This package does NOT claim to reproduce
them bit-for-bit — that is not possible from the outside. Instead it
implements transparent, peer-reviewed-physiology-based *approximations* that
target the same constructs (overnight HRV-driven recovery, sleep-stage based
sleep quality, Oura-style readiness, Apple-style cardio fitness) so the
resulting scores are directionally comparable and, crucially, fully auditable.

Every scoring function documents its scientific basis and its weights are
exposed as configuration so they can be tuned to match observed device output.

Modules
-------
- ``models``       : Pydantic data models for ingested sensor data.
- ``manual``       : Models for manual self-reported inputs.
- ``baseline``     : Rolling personal-baseline helper (mean / std / z-score).
- ``ingestion``    : Data sources (FIT file parser, synthetic generator).
- ``scoring``      : Sleep / recovery / readiness / cardio / longevity engines.
- ``store``        : Simple JSON-backed persistence.
- ``api``          : FastAPI application exposing the above.
"""

from src.wearable.models import (
    SleepStages,
    SleepRecord,
    DailyMetrics,
    DailyRecord,
    UserProfile,
    Sex,
)

__all__ = [
    "SleepStages",
    "SleepRecord",
    "DailyMetrics",
    "DailyRecord",
    "UserProfile",
    "Sex",
]

__version__ = "0.1.0"
