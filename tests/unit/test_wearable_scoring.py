"""Unit tests for the wearable scoring engines and data models."""

import datetime as dt

import pytest

from src.wearable.baseline import Baseline, clamp, gaussian_percentile, lerp_score
from src.wearable.ingestion import SyntheticSource
from src.wearable.models import (
    DailyMetrics,
    DailyRecord,
    Sex,
    SleepRecord,
    SleepStages,
    UserProfile,
)
from src.wearable.scoring import (
    score_cardio_fitness,
    score_longevity,
    score_readiness,
    score_recovery,
    score_sleep,
)
from src.wearable.scoring.cardio import estimate_vo2max_from_hr, fitness_age


@pytest.fixture
def good_night():
    return SleepRecord(
        date=dt.date(2026, 1, 10),
        time_in_bed_min=480,
        stages=SleepStages(deep_min=90, light_min=240, rem_min=120, awake_min=30),
        sleep_onset_latency_min=10,
        awakenings=1,
        avg_hrv_ms=70,
        lowest_hr_bpm=46,
    )


# --- Baseline maths ---------------------------------------------------------


class TestBaseline:
    def test_from_values_basic(self):
        bl = Baseline.from_values([10, 12, 14])
        assert bl is not None
        assert bl.n == 3
        assert bl.mean == pytest.approx(12.0)

    def test_from_values_empty_is_none(self):
        assert Baseline.from_values([]) is None
        assert Baseline.from_values([None, None]) is None

    def test_zscore_zero_std(self):
        bl = Baseline.from_values([5, 5, 5])
        assert bl.z_score(5) == 0.0

    def test_gaussian_percentile_monotonic(self):
        assert gaussian_percentile(0) == pytest.approx(50.0, abs=0.5)
        assert gaussian_percentile(2) > gaussian_percentile(-2)

    def test_lerp_invert(self):
        assert lerp_score(5, 45, 5) == pytest.approx(100.0)  # short latency -> high
        assert lerp_score(45, 45, 5) == pytest.approx(0.0)
        assert clamp(150) == 100.0


# --- Sleep model + score ----------------------------------------------------


class TestSleep:
    def test_efficiency_and_fractions(self, good_night):
        assert good_night.total_sleep_min == 450
        assert good_night.efficiency_pct == pytest.approx(93.75)
        assert good_night.stages.fraction("rem") == pytest.approx(120 / 450)

    def test_score_in_range_and_bands(self, good_night):
        res = score_sleep(good_night, sleep_need_hours=8.0)
        assert 0 <= res.score <= 100
        assert res.score > 70  # a genuinely good night
        assert res.kind == "sleep"
        assert {c.name for c in res.components} >= {"duration", "efficiency", "rem", "deep"}

    def test_short_sleep_scores_lower(self, good_night):
        short = good_night.model_copy(update={
            "stages": SleepStages(deep_min=30, light_min=120, rem_min=40, awake_min=20),
            "time_in_bed_min": 230,
        })
        assert score_sleep(short).score < score_sleep(good_night).score


# --- Recovery ---------------------------------------------------------------


class TestRecovery:
    def test_high_hrv_beats_low_hrv(self, good_night):
        hist_hrv = Baseline.from_values([50, 52, 48, 51, 49])
        hist_rhr = Baseline.from_values([50, 51, 49, 50, 50])
        high = DailyRecord(date=dt.date(2026, 1, 10),
                           sleep=good_night,
                           metrics=DailyMetrics(date=dt.date(2026, 1, 10),
                                                hrv_overnight_ms=70, resting_hr_bpm=48))
        low = DailyRecord(date=dt.date(2026, 1, 10),
                          sleep=good_night,
                          metrics=DailyMetrics(date=dt.date(2026, 1, 10),
                                               hrv_overnight_ms=35, resting_hr_bpm=58))
        r_high = score_recovery(high, hrv_baseline=hist_hrv, rhr_baseline=hist_rhr)
        r_low = score_recovery(low, hrv_baseline=hist_hrv, rhr_baseline=hist_rhr)
        assert r_high.score > r_low.score
        assert r_high.band in {"green", "yellow", "red"}

    def test_missing_data_reports_missing(self):
        rec = DailyRecord(date=dt.date(2026, 1, 10))
        res = score_recovery(rec)
        assert res.score == 0.0
        assert "hrv" in res.inputs_missing


# --- Readiness --------------------------------------------------------------


class TestReadiness:
    def test_wake_fatigue_lowers_readiness(self, good_night):
        base = DailyRecord(date=dt.date(2026, 1, 10), sleep=good_night,
                           metrics=DailyMetrics(date=dt.date(2026, 1, 10),
                                                hrv_overnight_ms=60, resting_hr_bpm=50))
        tired = base.model_copy(update={
            "manual": [{"kind": "fatigue_wake", "rating": 9,
                        "timestamp": "2026-01-10T07:00:00"}]
        })
        rested = base.model_copy(update={
            "manual": [{"kind": "fatigue_wake", "rating": 1,
                        "timestamp": "2026-01-10T07:00:00"}]
        })
        assert score_readiness(tired).score < score_readiness(rested).score


# --- Cardio fitness ---------------------------------------------------------


class TestCardio:
    def test_vo2max_estimate(self):
        v = estimate_vo2max_from_hr(190, 50)
        assert v == pytest.approx(15.3 * 190 / 50)
        assert estimate_vo2max_from_hr(190, 0) is None

    def test_fitness_age_better_than_chrono(self):
        # A 50yo male with a 30yo's VO2max should read younger.
        assert fitness_age(46.0, Sex.male, 50) < 50

    def test_score_uses_device_vo2max(self):
        prof = UserProfile(birth_year=1980, sex=Sex.male)
        rec = DailyRecord(date=dt.date(2026, 1, 10),
                          metrics=DailyMetrics(date=dt.date(2026, 1, 10), vo2max=50))
        res = score_cardio_fitness(rec, prof)
        assert res.score > 50  # above the 40-something male median
        assert any("VO2max" in n for n in res.notes)


# --- Longevity --------------------------------------------------------------


class TestLongevity:
    def test_composite_over_window(self):
        prof = UserProfile(birth_year=1985, sex=Sex.female)
        recs = SyntheticSource(dt.date(2026, 1, 1), days=30, seed=3).records()
        res = score_longevity(recs, prof)
        assert 0 <= res.score <= 100
        assert res.kind == "longevity"
        assert any("not medical advice" in n for n in res.notes)

    def test_empty_records(self):
        prof = UserProfile(birth_year=1985, sex=Sex.female)
        res = score_longevity([], prof)
        assert res.score == 0.0
        assert "records" in res.inputs_missing
