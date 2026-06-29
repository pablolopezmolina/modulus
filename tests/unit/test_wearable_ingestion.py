"""Unit tests for FIT aggregation, the manual-input store, and the REST API."""

import datetime as dt

import pytest

from src.wearable.ingestion.fit_parser import build_records
from src.wearable.manual import BowelMovement, Supplement, parse_manual
from src.wearable.models import UserProfile, Sex
from src.wearable.store import HealthStore


# --- FIT message aggregation (no binary file needed) ------------------------


def _ts(h, m=0):
    return dt.datetime(2026, 1, 10, h, m)


class TestBuildRecords:
    def test_sleep_levels_sum_into_stages(self):
        # deep 30m -> light 60m -> rem 30m -> light 90m -> awake (end marker).
        # Each segment is < the 240m inter-session guard so all are counted.
        msgs = {
            "sleep_level_mesgs": [
                {"timestamp": dt.datetime(2026, 1, 9, 23, 0), "sleep_level": 3},
                {"timestamp": dt.datetime(2026, 1, 9, 23, 30), "sleep_level": 2},
                {"timestamp": dt.datetime(2026, 1, 10, 0, 30), "sleep_level": 4},
                {"timestamp": dt.datetime(2026, 1, 10, 1, 0), "sleep_level": 2},
                {"timestamp": dt.datetime(2026, 1, 10, 2, 30), "sleep_level": 1},
            ],
            "hrv_status_summary_mesgs": [
                {"timestamp": dt.datetime(2026, 1, 10, 6, 0), "last_night_average": 62}
            ],
            "max_met_data_mesgs": [
                {"timestamp": dt.datetime(2026, 1, 10, 6, 0), "max_met": 13.0}
            ],
        }
        recs = build_records(msgs)
        assert len(recs) == 1
        rec = recs[0]
        assert rec.date == dt.date(2026, 1, 10)
        assert rec.sleep is not None
        assert rec.sleep.stages.deep_min == pytest.approx(30)
        assert rec.sleep.stages.light_min == pytest.approx(150)  # 60 + 90
        assert rec.sleep.stages.rem_min == pytest.approx(30)
        assert rec.metrics.hrv_overnight_ms == 62
        assert rec.metrics.vo2max == pytest.approx(13.0 * 3.5)

    def test_monitoring_steps_take_daily_max(self):
        msgs = {
            "monitoring_mesgs": [
                {"timestamp": _ts(9), "steps": 1000, "resting_heart_rate": 52},
                {"timestamp": _ts(18), "steps": 8000},
                {"timestamp": _ts(12), "steps": 4000},
            ],
        }
        recs = build_records(msgs)
        assert recs[0].metrics.steps == 8000
        assert recs[0].metrics.resting_hr_bpm == 52

    def test_empty_messages(self):
        assert build_records({}) == []


# --- Manual inputs ----------------------------------------------------------


class TestManual:
    def test_roundtrip_parse(self):
        s = Supplement(compound="magnesium glycinate", dose=400, unit="mg")
        again = parse_manual(s.model_dump(mode="json"))
        assert isinstance(again, Supplement)
        assert again.compound == "magnesium glycinate"

    def test_bristol_bounds(self):
        with pytest.raises(Exception):
            BowelMovement(bristol_scale=9)


# --- Store ------------------------------------------------------------------


class TestStore:
    def test_profile_and_record_roundtrip(self, tmp_path):
        store = HealthStore(str(tmp_path))
        prof = UserProfile(user_id="me", birth_year=1990, sex=Sex.male)
        store.save_profile(prof)
        assert store.get_profile("me").birth_year == 1990

    def test_add_manual_creates_day(self, tmp_path):
        store = HealthStore(str(tmp_path))
        day = dt.date(2026, 1, 10)
        store.add_manual(day, BowelMovement(bristol_scale=4))
        store.add_manual(day, Supplement(compound="creatine", dose=5, unit="g"))
        entries = store.list_manual(day)
        assert len(entries) == 2
        assert {e.kind.value for e in entries} == {"bowel", "supplement"}


# --- API --------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MODULUS_WEARABLE_STORE", str(tmp_path))
    # Re-import the app with the patched store dir.
    import importlib

    from src.wearable import api as api_module

    importlib.reload(api_module)
    from fastapi.testclient import TestClient

    return TestClient(api_module.app)


class TestApi:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_full_flow(self, client):
        # Profile
        assert client.post("/profile", json={
            "user_id": "me", "birth_year": 1988, "sex": "male", "sleep_need_hours": 8.0,
        }).status_code == 200

        # Synthetic ingest
        r = client.post("/ingest/synthetic", json={
            "user_id": "me", "start": "2026-01-01", "days": 40, "seed": 11,
        })
        assert r.status_code == 200
        assert r.json()["ingested_days"] == 40

        # Manual input
        assert client.post("/manual/2026-02-09", json={
            "kind": "fatigue_wake", "rating": 3,
        }).status_code == 200

        # Daily scores (a day with baseline history behind it)
        r = client.get("/scores/2026-02-09")
        assert r.status_code == 200
        body = r.json()
        assert "recovery" in body and 0 <= body["recovery"]["score"] <= 100
        assert "readiness" in body
        assert "cardio_fitness" in body

        # Longevity
        r = client.get("/longevity?window_days=30")
        assert r.status_code == 200
        assert 0 <= r.json()["score"] <= 100

        # Dashboard
        assert client.get("/dashboard").status_code == 200

    def test_scores_missing_day_404(self, client):
        assert client.get("/scores/2099-01-01").status_code == 404
