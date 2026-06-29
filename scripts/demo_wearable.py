"""
Demo: MODULUS Wearable (Garmin health analytics)
================================================

Generates 45 days of synthetic Fenix-5-Plus-style data, logs a couple of
manual inputs, and prints sleep / recovery / readiness / cardio-fitness scores
for the latest day plus a longevity index over the window.

    python scripts/demo_wearable.py
"""

import datetime as dt
import os
import sys

# Ensure the repo root is importable when run as `python scripts/demo_wearable.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.wearable.baseline import Baseline  # noqa: E402
from src.wearable.ingestion import SyntheticSource  # noqa: E402
from src.wearable.models import Sex, UserProfile  # noqa: E402
from src.wearable.scoring import (  # noqa: E402
    score_cardio_fitness,
    score_longevity,
    score_readiness,
    score_recovery,
    score_sleep,
)


def main() -> None:
    profile = UserProfile(birth_year=1988, sex=Sex.male, sleep_need_hours=8.0)
    records = SyntheticSource(dt.date(2026, 1, 1), days=45, seed=2026).records()

    latest = records[-1]
    history = records[:-1]
    hrv_bl = Baseline.from_values(r.best_hrv_ms() for r in history)
    rhr_bl = Baseline.from_values(r.best_resting_hr() for r in history)

    print(f"=== MODULUS Wearable demo — {latest.date} ===\n")

    sleep = score_sleep(latest.sleep, sleep_need_hours=profile.sleep_need_hours)
    recovery = score_recovery(latest, hrv_baseline=hrv_bl, rhr_baseline=rhr_bl)
    readiness = score_readiness(latest, hrv_baseline=hrv_bl, rhr_baseline=rhr_bl)
    cardio = score_cardio_fitness(latest, profile)
    longevity = score_longevity(records, profile)

    for res in (sleep, recovery, readiness, cardio, longevity):
        print(f"{res.kind:>14}: {res.score:5.1f}  [{res.band}]")
        for c in res.components:
            print(f"               - {c.name:<16} {c.value:5.1f}  ({c.detail})")
        for note in res.notes:
            print(f"               · {note}")
        print()


if __name__ == "__main__":
    main()
