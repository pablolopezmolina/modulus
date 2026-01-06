import numpy as np
from scipy.integrate import solve_ivp
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from .base import PhysiologicalModel, SimulationInput, SimulationResult


@dataclass(kw_only=True)
class CaffeineInput(SimulationInput):
    dose_mg: float
    body_weight_kg: float
    # Campos extra opcionales (no rompen tests, te dan más producto)
    tolerance_days: int = 0
    sleep_debt_hours: float = 0.0


@dataclass
class CaffeineParams:
    """
    Unidades internas:
    - ka: min^-1
    - kel: min^-1
    - Vd_per_kg: L/kg
    - concentración: mg/L
    """

    ka: float = 0.11
    kel: float = 0.0025
    Vd_per_kg: float = 0.6
    bioavailability: float = 1.0

    ec50_mg_l: float = 4.0
    hill_coeff: float = 1.5


class EliteCaffeineModel(PhysiologicalModel):
    STATE_NAMES = ["Q_gut", "Q_central"]

    def __init__(self, params: Optional[CaffeineParams] = None):
        self.p = params or CaffeineParams()

    def _validate_all_params_numeric(self) -> None:
        bad = []
        for k, v in asdict(self.p).items():
            try:
                fv = float(v)
            except Exception:
                bad.append(f"{k}=non_numeric({type(v).__name__})")
                continue
            if not np.isfinite(fv):
                bad.append(f"{k}=non_finite")
        if bad:
            raise ValueError("Toxic params: " + "; ".join(bad))

    def _validate_params_or_raise(self) -> None:
        p = self.p
        e = []
        if p.Vd_per_kg <= 0:
            e.append("Vd_per_kg<=0")
        if p.ka <= 0:
            e.append("ka<=0")
        if p.kel < 0:
            e.append("kel<0")
        if not (0 <= p.bioavailability <= 1):
            e.append("F out of range")
        if p.ec50_mg_l <= 0:
            e.append("ec50<=0")
        if p.hill_coeff <= 0:
            e.append("hill_coeff<=0")
        if e:
            raise ValueError(f"Invalid: {'; '.join(e)}")

    def _validate_inputs_or_raise(self, inputs: CaffeineInput) -> None:
        try:
            dose = float(inputs.dose_mg)
        except Exception:
            raise ValueError(f"Invalid dose_mg type: {type(inputs.dose_mg).__name__}")
        try:
            bw = float(inputs.body_weight_kg)
        except Exception:
            raise ValueError(f"Invalid body_weight_kg type: {type(inputs.body_weight_kg).__name__}")

        if not np.isfinite(dose) or dose < 0:
            raise ValueError(f"Invalid dose_mg value: {dose}")
        if not np.isfinite(bw) or bw <= 0:
            raise ValueError(f"Invalid body_weight_kg value: {bw}")

        # Extras opcionales: si vienen, validamos suave
        try:
            td = int(inputs.tolerance_days)
            if td < 0:
                raise ValueError("tolerance_days<0")
        except Exception:
            raise ValueError(f"Invalid tolerance_days: {inputs.tolerance_days}")

        try:
            sd = float(inputs.sleep_debt_hours)
            if not np.isfinite(sd) or sd < 0:
                raise ValueError("sleep_debt_hours<0")
        except Exception:
            raise ValueError(f"Invalid sleep_debt_hours: {inputs.sleep_debt_hours}")

    def _odes(self, t, y, params: CaffeineParams):
        Q_gut, Q_central = y
        return [
            -params.ka * Q_gut,
            (params.ka * Q_gut) - (params.kel * Q_central),
        ]

    def _calculate_alertness(self, conc_mg_l: np.ndarray) -> np.ndarray:
        p = self.p
        C = np.clip(conc_mg_l, 0.0, np.inf)
        c_pow = np.power(C, p.hill_coeff)
        ec50_pow = float(p.ec50_mg_l) ** float(p.hill_coeff)
        effect = (c_pow / (ec50_pow + c_pow)) * 100.0
        return np.clip(effect, 0.0, 100.0)

    @staticmethod
    def _tmax_theoretical_minutes(ka: float, kel: float) -> Optional[float]:
        if not (np.isfinite(ka) and np.isfinite(kel)):
            return None
        if ka <= kel or kel <= 0:
            return None
        return float(np.log(ka / kel) / (ka - kel))

    def simulate(self, inputs: CaffeineInput) -> SimulationResult:
        p = self.p

        sol = None
        failure_mode = None
        meta: Dict[str, Any] = {
            "solver_success": None,
            "solver_message": None,
            "solver_failure_mode": None,
            "has_usable_data": False,
            "is_sim_valid": False,
            "warnings": [],
            "units": {
                "time": "min",
                "dose": "mg",
                "concentration": "mg/L",
                "ka": "min^-1",
                "kel": "min^-1",
                "Vd_per_kg": "L/kg",
            },
            "pk_params": {
                "ka": float(p.ka),
                "kel": float(p.kel),
                "Vd_per_kg": float(p.Vd_per_kg),
                "bioavailability": float(p.bioavailability),
                "tmax_theoretical_min": self._tmax_theoretical_minutes(float(p.ka), float(p.kel)),
            },
            "pd_model": "emax_hill_v1",
            "pd_params": {
                "ec50_mg_l": float(p.ec50_mg_l),
                "hill_coeff": float(p.hill_coeff),
            },
            "input_summary": {
                "dose_mg": None,
                "body_weight_kg": None,
                "duration_minutes": None,
                "time_step_minutes": None,
                "tolerance_days": None,
                "sleep_debt_hours": None,
            },
        }

        # 0. SAFE TIME
        try:
            t_eval = inputs.get_time_vector()
        except Exception as e:
            t_eval = np.array([], dtype=float)
            failure_mode = "invalid_input"
            meta["solver_message"] = f"Time crash: {e}"

        # 1. CHECKS
        if failure_mode is None:
            try:
                self._validate_all_params_numeric()
                self._validate_params_or_raise()
            except Exception as e:
                failure_mode = "invalid_params"
                meta["solver_message"] = str(e)

        if failure_mode is None:
            try:
                self._validate_inputs_or_raise(inputs)
                meta["input_summary"]["dose_mg"] = float(inputs.dose_mg)
                meta["input_summary"]["body_weight_kg"] = float(inputs.body_weight_kg)
                meta["input_summary"]["duration_minutes"] = float(inputs.duration_minutes)
                meta["input_summary"]["time_step_minutes"] = float(inputs.time_step_minutes)
                meta["input_summary"]["tolerance_days"] = int(inputs.tolerance_days)
                meta["input_summary"]["sleep_debt_hours"] = float(inputs.sleep_debt_hours)
            except Exception as e:
                failure_mode = "invalid_input"
                meta["solver_message"] = str(e)

        # 2. TIME GUARD
        if failure_mode is None:
            try:
                if len(t_eval) < 2 or not np.isfinite(t_eval).all():
                    failure_mode = "invalid_time_input"
                else:
                    eps = max(1e-12, 1e-12 * max(1.0, float(np.max(np.abs(t_eval)))))
                    if not np.all(np.diff(t_eval) > eps):
                        failure_mode = "invalid_time_input"
                if failure_mode:
                    meta["solver_message"] = "Invalid time input"
            except Exception as e:
                failure_mode = "invalid_time_input"
                meta["solver_message"] = f"Time check: {e}"

        # 3. SOLVER
        if failure_mode is None:
            y0 = [float(inputs.dose_mg) * p.bioavailability, 0.0]
            try:
                sol = solve_ivp(
                    lambda t, y: self._odes(t, y, p),
                    (t_eval[0], t_eval[-1]),
                    y0,
                    t_eval=t_eval,
                    method="LSODA",
                    rtol=1e-6,
                    atol=1e-8,
                )
            except Exception as e:

                class Mock:
                    pass

                sol = Mock()
                sol.success = False
                sol.message = str(e)
                sol.y = None
                sol.t = None
                failure_mode = "scipy_exception"

        # 4. POST-SOLVER
        if failure_mode is None:
            if not bool(getattr(sol, "success", False)):
                failure_mode = "solver_reported_failure"
            else:
                n_t = len(t_eval)
                n_s = len(sol.t) if getattr(sol, "t", None) is not None else 0
                if not (
                    (sol.y is not None)
                    and (getattr(sol.y, "ndim", 0) == 2)
                    and (sol.y.shape[1] == n_s)
                    and (n_s > 0)
                ):
                    failure_mode = "state_shape_mismatch"
                elif not (
                    (n_s == n_t)
                    and (np.isfinite(sol.t).all() if n_s > 0 else False)
                    and np.allclose(sol.t, t_eval, rtol=1e-12, atol=1e-12)
                ):
                    failure_mode = "time_vector_mismatch"
                elif not np.isfinite(sol.y).all():
                    failure_mode = "non_finite_output"

        if failure_mode:
            nan = np.full(len(t_eval), np.nan, dtype=float)
            meta["solver_success"] = bool(getattr(sol, "success", False)) if sol else False
            if meta["solver_message"] is None:
                meta["solver_message"] = getattr(sol, "message", "Unknown") if sol else "Pre-check"
            if failure_mode == "solver_reported_failure" and sol is not None:
                meta["solver_message"] = getattr(sol, "message", meta["solver_message"])
            meta["solver_failure_mode"] = failure_mode
            meta["is_sim_valid"] = False
            meta["has_usable_data"] = False
            return SimulationResult(
                time_points=t_eval,
                channels={"plasma_caffeine": nan, "alertness_score": nan},
                metrics={"Tmax": np.nan, "Cmax": np.nan, "AUC": np.nan},
                metadata=meta,
            )

        # DATA PATH
        Q_central = sol.y[1]
        Vd_l = max(p.Vd_per_kg * float(inputs.body_weight_kg), 1e-9)
        conc = np.clip(Q_central / Vd_l, 0.0, np.inf)
        alertness = self._calculate_alertness(conc)

        idx = int(np.argmax(conc))
        metrics = {
            "Tmax": float(t_eval[idx]),
            "Cmax": float(conc[idx]),
            # NumPy 2.0: trapz eliminado -> trapezoid
            "AUC": float(np.trapz(conc, t_eval)),
        }

        meta["solver_success"] = True
        meta["solver_message"] = getattr(sol, "message", None)
        meta["solver_failure_mode"] = None
        meta["is_sim_valid"] = True
        meta["has_usable_data"] = True

        return SimulationResult(
            time_points=t_eval,
            channels={"plasma_caffeine": conc, "alertness_score": alertness},
            metrics=metrics,
            metadata=meta,
        )
