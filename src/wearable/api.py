"""
MODULUS Wearable — REST API
===========================

FastAPI application exposing the Garmin health-analytics stack:

- Profile management.
- Ingestion of FIT files (by server-side path/directory) and synthetic demo data.
- Manual self-reported inputs.
- Daily scores (sleep, recovery, readiness, cardio fitness).
- Longevity index over a window.

Run with::

    uvicorn src.wearable.api:app --reload --port 8010
"""

from __future__ import annotations

import os
from datetime import date as date_cls, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.wearable.baseline import Baseline
from src.wearable.ingestion import FIT_AVAILABLE, FitFileSource, SyntheticSource
from src.wearable.manual import ManualInput, parse_manual
from src.wearable.models import DailyRecord, UserProfile
from src.wearable.scoring import (
    score_cardio_fitness,
    score_longevity,
    score_readiness,
    score_recovery,
    score_sleep,
)
from src.wearable.store import HealthStore

app = FastAPI(
    title="MODULUS Wearable — Garmin Health Analytics",
    description=(
        "Recovery, sleep, readiness, cardio-fitness and longevity analytics from "
        "Garmin Fenix 5 Plus data. Scores are transparent, peer-reviewed-physiology "
        "based approximations of the constructs measured by WHOOP / Oura / Apple "
        "Watch — not reproductions of their proprietary algorithms."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STORE_DIR = os.environ.get("MODULUS_WEARABLE_STORE", "storage/wearable")
store = HealthStore(_STORE_DIR)


# ---------------------------------------------------------------------------
# Baseline helper
# ---------------------------------------------------------------------------


def _baselines(records: List[DailyRecord], target: date_cls, window: int = 60) -> Dict:
    """Build trailing-window personal baselines (excluding the target day)."""
    cutoff = target - timedelta(days=window)
    hist = [r for r in records if cutoff <= r.date < target]
    hrv = Baseline.from_values(r.best_hrv_ms() for r in hist)
    rhr = Baseline.from_values(r.best_resting_hr() for r in hist)
    resp = Baseline.from_values(
        r.metrics.respiration_brpm for r in hist if r.metrics and r.metrics.respiration_brpm
    )
    temp = Baseline.from_values(
        r.metrics.body_temp_deviation_c for r in hist if r.metrics and r.metrics.body_temp_deviation_c is not None
    )
    return {"hrv": hrv, "rhr": rhr, "resp": resp, "temp": temp, "n": len(hist)}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class IngestFitRequest(BaseModel):
    user_id: str = "me"
    directory: Optional[str] = Field(default=None, description="Directory of .FIT files")
    paths: Optional[List[str]] = Field(default=None, description="Explicit FIT file paths")


class IngestSyntheticRequest(BaseModel):
    user_id: str = "me"
    start: date_cls
    days: int = Field(default=30, ge=1, le=365)
    seed: int = 42


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@app.get("/health", tags=["status"])
async def health():
    return {"status": "healthy", "fit_available": FIT_AVAILABLE, "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@app.post("/profile", tags=["profile"])
async def save_profile(profile: UserProfile):
    store.save_profile(profile)
    return {"saved": True, "user_id": profile.user_id}


@app.get("/profile/{user_id}", tags=["profile"])
async def get_profile(user_id: str = "me"):
    profile = store.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@app.post("/ingest/fit", tags=["ingestion"])
async def ingest_fit(req: IngestFitRequest):
    if not FIT_AVAILABLE:
        raise HTTPException(status_code=503, detail="garmin-fit-sdk not installed on server")
    if not req.directory and not req.paths:
        raise HTTPException(status_code=400, detail="Provide 'directory' or 'paths'")
    try:
        source = (
            FitFileSource.from_directory(req.directory)
            if req.directory
            else FitFileSource(req.paths or [])
        )
        records = source.records()
    except Exception as exc:  # surface parse errors clearly
        raise HTTPException(status_code=400, detail=f"FIT parsing failed: {exc}")
    n = store.upsert_many(records, req.user_id)
    return {"ingested_days": n, "dates": [str(r.date) for r in records]}


@app.post("/ingest/synthetic", tags=["ingestion"])
async def ingest_synthetic(req: IngestSyntheticRequest):
    """Generate deterministic demo data so the stack can be explored offline."""
    source = SyntheticSource(start=req.start, days=req.days, seed=req.seed)
    records = source.records()
    n = store.upsert_many(records, req.user_id)
    return {"ingested_days": n, "start": str(req.start), "days": req.days}


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@app.get("/records", tags=["records"])
async def get_records(
    user_id: str = "me",
    start: Optional[date_cls] = Query(default=None),
    end: Optional[date_cls] = Query(default=None),
):
    return store.get_records(user_id, start, end)


# ---------------------------------------------------------------------------
# Manual inputs
# ---------------------------------------------------------------------------


@app.post("/manual/{day}", tags=["manual"])
async def add_manual(day: date_cls, entry: dict, user_id: str = "me"):
    try:
        parsed: ManualInput = parse_manual(entry)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid manual input: {exc}")
    store.add_manual(day, parsed, user_id)
    return {"saved": True, "day": str(day), "kind": parsed.kind.value}


@app.get("/manual/{day}", tags=["manual"])
async def list_manual(day: date_cls, user_id: str = "me"):
    return store.list_manual(day, user_id)


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------


@app.get("/scores/{day}", tags=["scores"])
async def daily_scores(day: date_cls, user_id: str = "me"):
    record = store.get_record(day, user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"No record for {day}")
    profile = store.get_profile(user_id)
    sleep_need = profile.sleep_need_hours if profile else 8.0

    history = store.get_records(user_id, end=day)
    bl = _baselines(history, day)

    out: Dict = {"date": str(day), "baseline_days": bl["n"]}
    if record.sleep:
        out["sleep"] = score_sleep(record.sleep, sleep_need_hours=sleep_need)
    out["recovery"] = score_recovery(
        record, hrv_baseline=bl["hrv"], rhr_baseline=bl["rhr"],
        resp_baseline=bl["resp"], sleep_need_hours=sleep_need,
    )
    out["readiness"] = score_readiness(
        record, hrv_baseline=bl["hrv"], rhr_baseline=bl["rhr"],
        temp_baseline=bl["temp"], sleep_need_hours=sleep_need,
    )
    if profile:
        out["cardio_fitness"] = score_cardio_fitness(record, profile)
    else:
        out["cardio_fitness_note"] = "Save a profile (birth_year, sex) to enable cardio fitness."
    return out


@app.get("/longevity", tags=["scores"])
async def longevity(
    user_id: str = "me",
    window_days: int = Query(default=30, ge=7, le=365),
):
    profile = store.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=400, detail="Save a profile first (birth_year, sex).")
    end = max((r.date for r in store.get_records(user_id)), default=datetime.now().date())
    start = end - timedelta(days=window_days)
    records = store.get_records(user_id, start=start, end=end)
    if not records:
        raise HTTPException(status_code=404, detail="No records in window")
    return score_longevity(records, profile)


@app.get("/dashboard", tags=["scores"])
async def dashboard(user_id: str = "me"):
    """Latest-day scores plus the longevity index — one call for a UI."""
    records = store.get_records(user_id)
    if not records:
        raise HTTPException(status_code=404, detail="No data ingested yet")
    latest = records[-1].date
    scores = await daily_scores(latest, user_id)
    profile = store.get_profile(user_id)
    result = {"latest_date": str(latest), "scores": scores}
    if profile:
        result["longevity"] = score_longevity(records[-30:], profile)
    return result


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8010)
