# ==========================
# 4) tests/unit/test_sanity.py
# ==========================

import numpy as np
import warnings

from src.core.models.glucose import DallaManModel, DallaManParams, GlucoseInput
from src.core.models.caffeine import EliteCaffeineModel, CaffeineInput


class PoisonDeepcopy:
    def __deepcopy__(self, memo):
        raise RuntimeError("deepcopy boom")


def test_glucose_numeric_string_is_accepted():
    model = DallaManModel()
    res = model.simulate(GlucoseInput(carbs_g="50", duration_minutes=10))
    assert res.metadata["has_usable_data"] is True
    assert res.metadata["solver_failure_mode"] is None


def test_toxic_carbs_is_invalid_input():
    model = DallaManModel()
    inp = GlucoseInput(carbs_g="50g", duration_minutes=10)
    res = model.simulate(inp)
    assert res.metadata["solver_failure_mode"] == "invalid_input"


def test_deepcopy_failure_no_crash():
    model = DallaManModel()
    model.calibration_report["poison"] = PoisonDeepcopy()
    res = model.simulate(GlucoseInput(carbs_g=50, duration_minutes=10))
    assert res.metadata["has_usable_data"] is True
    assert "calibration_report_copy_failed" in res.metadata


def test_priority_determinism_in_safe_landing(monkeypatch):
    model = DallaManModel()
    model.p.Gb = 110.0  # mutación

    inp = GlucoseInput(carbs_g=50, duration_minutes=10)
    monkeypatch.setattr(inp, "get_time_vector", lambda: np.array([0.0, 0.0], dtype=float))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = model.simulate(inp)

    assert res.metadata["solver_failure_mode"] == "invalid_time_input"
    assert "basal_params_mutated" in res.metadata["scientific_invalid_reasons"]


def test_glucose_rollback_on_failed_calibration_keeps_previous_snapshot():
    model = DallaManModel()
    old_snapshot = dict(model._calibration_params_snapshot)
    assert old_snapshot

    model.p.Gb = -50.0  # inválido
    model.recalibrate()

    # No debe haber destruido el snapshot anterior
    assert model._calibration_params_snapshot == old_snapshot
    assert "last_recalibration_error" in model.calibration_report


def test_glucose_recalibrate_safe_copy_does_not_crash_with_poison_report():
    model = DallaManModel()
    model.calibration_report["poison"] = PoisonDeepcopy()

    model.p.Gb = -50.0
    model.recalibrate()

    assert "last_recalibration_error" in model.calibration_report


def test_dead_model_reports_not_calibrated_when_born_dead():
    # Micromejora: este test es estable incluso con rollback,
    # porque el modelo nace sin snapshot previo "salvable".
    bad_params = DallaManParams(Vg="x")
    model = DallaManModel(params=bad_params)

    res = model.simulate(GlucoseInput(carbs_g=10, duration_minutes=10))

    assert res.metadata["solver_failure_mode"] == "invalid_model_state"
    assert "model_not_calibrated" in res.metadata["scientific_invalid_reasons"]


def test_caffeine_sanity_and_pd():
    model = EliteCaffeineModel()
    res = model.simulate(CaffeineInput(dose_mg=200, body_weight_kg=75, duration_minutes=180))

    assert res.metadata["has_usable_data"] is True
    assert "pk_params" in res.metadata
    assert "pd_params" in res.metadata
    assert "warnings" in res.metadata
    assert "alertness_score" in res.channels

    # Validación: Tmax ~35 min con ka=0.11
    assert 25 < res.metrics["Tmax"] < 50


def test_caffeine_toxic_input_is_invalid_input():
    model = EliteCaffeineModel()
    res = model.simulate(CaffeineInput(dose_mg="200mg", body_weight_kg=75, duration_minutes=10))
    assert res.metadata["solver_failure_mode"] == "invalid_input"