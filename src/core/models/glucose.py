# src/core/models/glucose.py
# MODULUS — Glucose (Dalla Man) Model
#
# V9.0 "Launch-grade" steady-state:
# - Basal calibration is made CONSISTENT with the ODE (dynamic HE, consistent S_b usage)
# - Optional steady-state refinement solves dydt=0 for the real system (D=0) via scipy.optimize.root
# - No noisy warnings by default; steady-state diagnostics are stored in calibration_report
# - NumPy 2.0 compatible (np.trapezoid instead of np.trapz)
# - Transactional recalibrate() with rollback + poison-safe deepcopy
#
# IMPORTANT:
# This file assumes your base.py exposes:
#   PhysiologicalModel, SimulationInput, SimulationResult
# as used below.

import copy
import warnings
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, root

from .base import PhysiologicalModel, SimulationInput, SimulationResult


def _auc(y: np.ndarray, x: np.ndarray) -> float:
    # NumPy 2.0 removed np.trapz; np.trapezoid is the replacement.
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


@dataclass(kw_only=True)
class GlucoseInput(SimulationInput):
    carbs_g: float


@dataclass
class DallaManParams:
    BW: float = 78.0
    Gb: float = 95.0
    Ib: float = 25.0
    Vg: float = 1.88
    k1: float = 0.065
    k2: float = 0.079
    Vi: float = 0.05
    m1: float = 0.190
    m2: float = 0.484
    m4: float = 0.194
    m5: float = 0.0304
    m6: float = 0.6471
    HEb: float = 0.6
    kmax: float = 0.0558
    kmin: float = 0.0080
    kabs: float = 0.057
    kgri: float = 0.0558
    f: float = 0.90
    b: float = 0.82
    d: float = 0.010
    kp1: float = 2.70
    kp2: float = 0.0021
    kp3: float = 0.009
    kp4: float = 0.0618
    ki: float = 0.0079
    Fcns: float = 1.0
    Vm0: float = 2.50
    Vmx: float = 0.047
    Km0: float = 225.59
    p2U: float = 0.0331
    K: float = 2.30
    alpha: float = 0.050
    beta: float = 0.11
    gamma: float = 0.5
    ke1: float = 0.0005
    ke2: float = 339.0


class DallaManModel(PhysiologicalModel):
    STATE_NAMES = ["Gp", "Gt", "Ip", "Il", "Qsto1", "Qsto2", "Qgut", "X", "I1", "Id", "Ipo", "Y"]
    STATE_TYPES = [0, 0, 0, 0, 0, 0, 0, 2, 1, 1, 0, 2]

    BASAL_DEPENDENCY_KEYS: Set[str] = {
        "BW",
        "Gb",
        "Ib",
        "Vg",
        "Vi",
        "k1",
        "k2",
        "Fcns",
        "Vm0",
        "Km0",
        "m1",
        "m2",
        "m4",
        "m5",
        "m6",
        "HEb",
        "gamma",
        "kp1",
        "kp2",
        "kp3",
        "kp4",
        "ki",
        "ke1",
        "ke2",
        "alpha",
        "beta",
        "p2U",
    }

    INVALID_REASON_PRIORITY = [
        "model_not_calibrated",
        "basal_params_crash",
        "basal_params_mutated",
        "ib_calibration_failed",
        "ib_fallback_used",
        "steady_state_failed",
    ]

    _BASAL_ATTRS: Tuple[str, ...] = (
        "Gp_b",
        "Gt_b",
        "Ip_b",
        "Il_b",
        "Ipo_b",
        "S_b",
        "U_b",
        "E_b",
        "EGP_b",
        "renal_threshold_mass",
        "HE_b",
        "m3_b",
    )

    def __init__(self, params: Optional[DallaManParams] = None):
        super().__init__()
        self.p = params or DallaManParams()
        self.calibration_report: Dict[str, Any] = {}
        self._calibration_params_snapshot: Dict[str, float] = {}
        self.dt_check_minutes = 1.0

        # Steady-state refinement controls
        self.steady_refine_enabled = True
        self.steady_refine_tol = 1e-10
        self.steady_refine_maxfev = 800

        self.recalibrate()

    def _safe_deepcopy_report(self, report: Any) -> Tuple[Any, Optional[str]]:
        try:
            return copy.deepcopy(report), None
        except Exception as e:
            try:
                if isinstance(report, dict):
                    return dict(report), f"{type(e).__name__}: {str(e)}"
            except Exception:
                pass
            return report, f"{type(e).__name__}: {str(e)}"

    def _snapshot_basal_state(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {}
        for k in self._BASAL_ATTRS:
            if hasattr(self, k):
                snap[k] = getattr(self, k)
        return snap

    def _restore_basal_state(self, snap: Dict[str, Any]) -> None:
        for k, v in snap.items():
            setattr(self, k, v)

    def _has_basal_state(self) -> bool:
        required = (
            "Gp_b",
            "Gt_b",
            "Ip_b",
            "Il_b",
            "Ipo_b",
            "S_b",
            "U_b",
            "E_b",
            "renal_threshold_mass",
        )
        return all(hasattr(self, a) for a in required)

    def recalibrate(self) -> None:
        """
        Recalibración transaccional:
        - Si recalibrate falla, rollback al último estado interno válido.
        - Si el modelo "nace muerto" (params tóxicos desde el inicio), deja flags claros.
        """
        old_report, copy_err = self._safe_deepcopy_report(self.calibration_report)
        old_snapshot = copy.deepcopy(self._calibration_params_snapshot)
        old_basal = self._snapshot_basal_state()
        old_Ib = getattr(self.p, "Ib", None)

        try:
            self._validate_all_params_numeric()
            self._validate_params_or_raise()
            self._calibrate_basal()

            if copy_err:
                self.calibration_report.setdefault("diagnostics", {})
                self.calibration_report["diagnostics"]["recalibrate_backup_copy_warning"] = copy_err

        except Exception as e:
            # Rollback TOTAL
            self.calibration_report = old_report if isinstance(old_report, dict) else {}
            self._calibration_params_snapshot = old_snapshot
            self._restore_basal_state(old_basal)

            if old_Ib is not None:
                try:
                    self.p.Ib = old_Ib
                except Exception:
                    pass

            if not isinstance(self.calibration_report, dict):
                self.calibration_report = {}

            self.calibration_report["last_recalibration_error"] = {
                "error_type": type(e).__name__,
                "message": str(e),
            }

            # Si no hay nada a lo que volver, el modelo está crítico
            if (not self._calibration_params_snapshot) and (not self._has_basal_state()):
                self.calibration_report.setdefault("flags", {})
                self.calibration_report["flags"]["calibration_critical_failure"] = True
                self.calibration_report["steady_state_ok"] = False
                self.calibration_report.setdefault("diagnostics", {})
                self.calibration_report["diagnostics"]["calibration_failed"] = type(e).__name__

    def _validate_all_params_numeric(self) -> None:
        bad = []
        for k, v in asdict(self.p).items():
            try:
                fv = float(v)
                if not np.isfinite(fv):
                    bad.append(f"{k}=non_finite")
            except Exception:
                bad.append(f"{k}=non_numeric({type(v).__name__})")
        if bad:
            raise ValueError("Toxic params detected: " + "; ".join(bad))

    def _validate_params_or_raise(self) -> None:
        p = self.p
        eps = 1e-9
        errors = []

        # Basales fisiológicos
        if p.Gb <= 0:
            errors.append(f"Gb<=0 ({p.Gb})")
        if p.Ib <= 0:
            errors.append(f"Ib<=0 ({p.Ib})")

        # Volúmenes y BW
        if p.Vg <= 0:
            errors.append(f"Vg<=0 ({p.Vg})")
        if p.Vi <= 0:
            errors.append(f"Vi<=0 ({p.Vi})")
        if p.BW <= 0:
            errors.append(f"BW<=0 ({p.BW})")

        # Parámetros críticos
        if p.gamma <= 0:
            errors.append(f"gamma<=0 ({p.gamma})")
        if p.ki <= 0:
            errors.append(f"ki<=0 ({p.ki})")
        if p.p2U <= 0:
            errors.append(f"p2U<=0 ({p.p2U})")
        if p.alpha <= 0:
            errors.append(f"alpha<=0 ({p.alpha})")

        if not (0.0 < p.b < 1.0):
            errors.append("b_out_of_range")
        elif abs(1.0 - p.b) < eps:
            errors.append("b_near_singularity")

        if not (0.0 < p.HEb < 1.0):
            errors.append("HEb_out_of_range")
        elif abs(1.0 - p.HEb) < eps:
            errors.append("HEb_near_singularity")

        if p.d <= 0:
            errors.append("d_out_of_range")
        elif p.d < eps:
            errors.append("d_near_singularity")

        if errors:
            raise ValueError(f"Parámetros inválidos: {'; '.join(errors)}")

    def _validate_inputs_or_raise(self, inputs: GlucoseInput) -> None:
        try:
            carbs = float(inputs.carbs_g)
        except Exception:
            raise ValueError(f"Invalid carbs_g type: {type(inputs.carbs_g).__name__}")
        if not np.isfinite(carbs) or carbs < 0:
            raise ValueError(f"Invalid carbs_g value: {carbs}")

    def _basal_param_diffs(self, current: Dict[str, float], snapshot: Dict[str, float]) -> List[str]:
        diffs = []
        for k in sorted(self.BASAL_DEPENDENCY_KEYS):
            v_c = current.get(k)
            v_s = snapshot.get(k)
            if v_c is None or v_s is None:
                diffs.append(k)
                continue
            if not (np.isfinite(v_c) and np.isfinite(v_s)):
                diffs.append(k)
                continue
            if not np.isclose(v_c, v_s, rtol=1e-12, atol=1e-12):
                diffs.append(k)
        return diffs

    def _resolve_scientific_reason(self, meta: Dict[str, Any]) -> None:
        reasons = meta.get("scientific_invalid_reasons", [])
        if not reasons:
            meta["scientific_invalid_reason"] = None
            return
        for r in self.INVALID_REASON_PRIORITY:
            if r in reasons:
                meta["scientific_invalid_reason"] = r
                return
        meta["scientific_invalid_reason"] = reasons[0]

    def _append_calibration_reasons(self, meta: Dict[str, Any], add_reason_func: Callable[[str], None]) -> None:
        flags = meta.get("flags", {})
        if not flags.get("ib_calibration_ok", True):
            add_reason_func("ib_calibration_failed")
        if flags.get("ib_used_fallback", False):
            add_reason_func("ib_fallback_used")
        if meta.get("steady_state_ok") is False:
            add_reason_func("steady_state_failed")

    def _mass_to_conc(self, m: float) -> float:
        return m / self.p.Vg

    def _conc_to_mass(self, c: float) -> float:
        return c * self.p.Vg

    def _get_tolerance_for_state(self, idx: int) -> float:
        return 1e-4 if self.STATE_TYPES[idx] == 1 else 1e-6

    def _kempt(self, Qsto: float, D: float) -> float:
        p = self.p
        if D <= 0:
            return p.kmax
        da = 2.0 * D * (1.0 - p.b)
        db = 2.0 * D * p.d
        if abs(da) < 1e-9 or abs(db) < 1e-9:
            return p.kmax
        return p.kmin + (p.kmax - p.kmin) / 2.0 * (
            np.tanh(5.0 / da * (Qsto - p.b * D)) - np.tanh(5.0 / db * (Qsto - p.d * D)) + 2.0
        )

    # -------------------------
    # ODE (production)
    # -------------------------
    def _odes(self, t: float, y: List[float], D: float) -> List[float]:
        p = self.p
        Gp, Gt, Ip, Il, Qsto1, Qsto2, Qgut, X, I1, Id, Ipo, Y = y

        G_conc = max(Gp, 0.0) / p.Vg
        I_conc = max(Ip, 0.0) / p.Vi

        Qsto = Qsto1 + Qsto2
        kempt = self._kempt(Qsto, D)
        Ra = p.f * p.kabs * Qgut / p.BW

        EGP = max(
            0.0,
            (p.kp1 - p.kp2 * Gp - p.kp3 * Id - p.kp4 * Ipo)
            * (1.0 + 0.8 * (p.Gb - G_conc) / p.Gb if G_conc < p.Gb else 1.0),
        )
        Uii = p.Fcns
        Vm = p.Vm0 + p.Vmx * max(X, 0.0)
        Uid = Vm * Gt / (p.Km0 + Gt)
        E = p.ke1 * max(0.0, Gp - self.renal_threshold_mass)

        S = p.gamma * Ipo
        Spo = max(0.0, Y + self.S_b)

        HE = np.clip(-p.m5 * S + p.m6, 0.0, 0.95)
        m3 = HE * p.m1 / (1.0 - HE)

        dY = -p.alpha * Y + p.alpha * (
            p.beta * (G_conc - p.Gb) if p.beta * (G_conc - p.Gb) >= -self.S_b else -self.S_b
        )

        return [
            EGP + Ra - Uii - E - p.k1 * Gp + p.k2 * Gt,
            -Uid + p.k1 * Gp - p.k2 * Gt,
            -(p.m1 + p.m4) * Ip + p.m2 * Il + S,
            p.m1 * Ip - (p.m2 + m3) * Il,
            -p.kgri * Qsto1,
            p.kgri * Qsto1 - kempt * Qsto2,
            kempt * Qsto2 - p.kabs * Qgut,
            -p.p2U * X + p.p2U * (I_conc - p.Ib),
            -p.ki * (I1 - I_conc),
            -p.ki * (Id - I1),
            -p.gamma * Ipo + Spo,
            dY,
        ]

    # -------------------------
    # ODE variant for basal refinement (uses S_b derived from current state)
    # -------------------------
    def _odes_for_basal_refine(self, y: List[float]) -> List[float]:
        """
        D=0, Qsto/Qgut=0, BUT:
        - Uses S_b derived from (Ip, Il, Ipo) inside this call (self-consistent)
        - Sets I1=Id=I_conc and X=I_conc - Ib to make those states steady by construction
        """
        p = self.p
        Gp, Gt, Ip, Il, Ipo, Y = y

        G_conc = max(Gp, 0.0) / p.Vg
        I_conc = max(Ip, 0.0) / p.Vi

        # Construct steady-by-design auxiliary states
        X = I_conc - p.Ib
        I1 = I_conc
        Id = I_conc

        # Derive S_b consistent with current basal candidate
        S = p.gamma * Ipo
        HE = np.clip(-p.m5 * S + p.m6, 0.0, 0.95)
        m3 = HE * p.m1 / (1.0 - HE)
        S_b_local = m3 * Il + p.m4 * Ip  # same structure as calibration: S = m3*Il + m4*Ip
        Spo = max(0.0, Y + S_b_local)

        EGP = max(
            0.0,
            (p.kp1 - p.kp2 * Gp - p.kp3 * Id - p.kp4 * Ipo)
            * (1.0 + 0.8 * (p.Gb - G_conc) / p.Gb if G_conc < p.Gb else 1.0),
        )
        Uii = p.Fcns
        Vm = p.Vm0 + p.Vmx * max(X, 0.0)
        Uid = Vm * Gt / (p.Km0 + Gt)
        E = p.ke1 * max(0.0, Gp - self.renal_threshold_mass)

        dY = -p.alpha * Y + p.alpha * (
            p.beta * (G_conc - p.Gb) if p.beta * (G_conc - p.Gb) >= -S_b_local else -S_b_local
        )

        # Return residuals for the subset we are solving: [dGp,dGt,dIp,dIl,dIpo,dY]
        dGp = EGP - Uii - E - p.k1 * Gp + p.k2 * Gt  # Ra=0 at D=0
        dGt = -Uid + p.k1 * Gp - p.k2 * Gt
        dIp = -(p.m1 + p.m4) * Ip + p.m2 * Il + S
        dIl = p.m1 * Ip - (p.m2 + m3) * Il
        dIpo = -p.gamma * Ipo + Spo

        # Note: dX,dI1,dId are exactly 0 by construction of X,I1,Id.

        return [dGp, dGt, dIp, dIl, dIpo, dY]

    # -------------------------
    # Basal calibration + refinement
    # -------------------------
    def _calibrate_basal(self) -> None:
        p = self.p
        default_Ib = float(p.Ib)

        flags = {"gt_calibration_ok": False, "ib_calibration_ok": False, "ib_used_fallback": False}
        diag: Dict[str, Any] = {}

        # 1) Primary masses at basal
        self.Gp_b = self._conc_to_mass(float(p.Gb))

        # 2) Solve for Gt (brentq) if possible
        try:
            self.Gt_b = brentq(
                lambda Gt: (p.k1 * self.Gp_b) - (p.k2 * Gt) - (p.Vm0 * Gt / (p.Km0 + Gt)),
                0.1,
                self.Gp_b * 2.0,
            )
            flags["gt_calibration_ok"] = True
        except Exception:
            self.Gt_b = self.Gp_b

        # 3) Basal utilization and renal
        self.U_b = float(p.Fcns + (p.Vm0 * self.Gt_b / (p.Km0 + self.Gt_b)))
        self.renal_threshold_mass = self._conc_to_mass(float(p.ke2))
        self.E_b = float(p.ke1 * (self.Gp_b - self.renal_threshold_mass) if self.Gp_b > self.renal_threshold_mass else 0.0)

        # 4) Calibrate Ib by balance (EGP_b = U_b + E_b) using a basal-consistent liver extraction approximation
        #    NOTE: This is an initial guess; we then refine by steady-state root solve.
        def ib_eq(Ib: float) -> float:
            Ip = Ib * p.Vi
            # First-pass HE uses HEb (approx), but we immediately correct below.
            m3 = p.HEb * p.m1 / (1.0 - p.HEb)
            Il = p.m1 * Ip / (p.m2 + m3)
            S = m3 * Il + p.m4 * Ip
            Ipo = S / p.gamma
            EGP = (p.kp1 - p.kp2 * self.Gp_b - p.kp3 * Ib - p.kp4 * Ipo)
            return float(EGP - (self.U_b + self.E_b))

        try:
            vl = ib_eq(1.0)
            vh = ib_eq(500.0)
            if np.isfinite(vl) and np.isfinite(vh) and (vl * vh <= 0):
                p.Ib = float(brentq(ib_eq, 1.0, 500.0))
                flags["ib_calibration_ok"] = True
                diag["ib_residual_at_root"] = float(ib_eq(p.Ib))
            else:
                raise ValueError("No crossing")
        except Exception as e:
            p.Ib = default_Ib
            flags["ib_used_fallback"] = True
            diag["failure_reason"] = str(e)

        # 5) Build basal insulin masses from Ib guess
        self.Ip_b = float(p.Ib * p.Vi)

        # 6) Make basal CONSISTENT with ODE liver extraction rule:
        #    HE = clip(-m5*S + m6), m3 = HE*m1/(1-HE)
        #
        #    We do a small fixed-point iteration to get consistent (Il,S,Ipo,HE,m3).
        Il = float(self.Ip_b * p.m1 / (p.m2 + (p.HEb * p.m1 / (1.0 - p.HEb))))
        Ipo = float((p.HEb * p.m1 / (1.0 - p.HEb)) * Il + p.m4 * self.Ip_b) / float(p.gamma)

        for _ in range(30):
            S = float(p.gamma * Ipo)
            HE = float(np.clip(-p.m5 * S + p.m6, 0.0, 0.95))
            m3 = float(HE * p.m1 / (1.0 - HE))
            Il_new = float(p.m1 * self.Ip_b / (p.m2 + m3))
            S_b_new = float(m3 * Il_new + p.m4 * self.Ip_b)
            Ipo_new = float(S_b_new / p.gamma)

            if np.isfinite(Il_new) and np.isfinite(Ipo_new):
                if abs(Il_new - Il) < 1e-10 and abs(Ipo_new - Ipo) < 1e-10:
                    Il, Ipo = Il_new, Ipo_new
                    break
                Il, Ipo = Il_new, Ipo_new

        self.Il_b = float(Il)
        self.Ipo_b = float(Ipo)
        self.HE_b = float(np.clip(-p.m5 * (p.gamma * self.Ipo_b) + p.m6, 0.0, 0.95))
        self.m3_b = float(self.HE_b * p.m1 / (1.0 - self.HE_b))

        # Basal secretion proxy consistent with current basal
        self.S_b = float(self.m3_b * self.Il_b + p.m4 * self.Ip_b)

        # 7) Basal EGP consistent with definitions
        self.EGP_b = float(p.kp1 - p.kp2 * self.Gp_b - p.kp3 * p.Ib - p.kp4 * self.Ipo_b)

        # 8) Steady-state refinement (dydt=0)
        refine_info = self._steady_state_refine_if_enabled()
        diag["steady_state_refine"] = refine_info

        # 9) Build report and snapshot (only after full success)
        self.calibration_report = {
            "flags": flags,
            "diagnostics": diag,
            "dt_check_minutes": self.dt_check_minutes,
            "fluxes_mg_kg_min": {
                "EGP_b": float(self.EGP_b),
                "Balance_Error": float(self.EGP_b - (self.U_b + self.E_b)),
            },
        }

        self._calibration_params_snapshot = {k: float(getattr(p, k)) for k in self.BASAL_DEPENDENCY_KEYS}

        # 10) Final steady-state check (no warnings; only metadata)
        self._check_steady_state_full()

    def _steady_state_refine_if_enabled(self) -> Dict[str, Any]:
        """
        Solve dydt=0 for [Gp,Gt,Ip,Il,Ipo,Y] under D=0, Q=0.
        Stores results into basal state if successful; otherwise keeps the current guess.
        """
        info: Dict[str, Any] = {
            "enabled": bool(self.steady_refine_enabled),
            "success": False,
            "message": None,
            "max_abs_residual": None,
            "nfev": None,
        }
        if not self.steady_refine_enabled:
            return info

        p = self.p

        x0 = np.array(
            [self.Gp_b, self.Gt_b, self.Ip_b, self.Il_b, self.Ipo_b, 0.0],
            dtype=float,
        )

        def fun(x: np.ndarray) -> np.ndarray:
            # Enforce non-negativity softly to avoid solver wandering into nonsense
            Gp, Gt, Ip, Il, Ipo, Y = x
            Gp = float(max(Gp, 1e-12))
            Gt = float(max(Gt, 1e-12))
            Ip = float(max(Ip, 1e-12))
            Il = float(max(Il, 1e-12))
            Ipo = float(max(Ipo, 0.0))
            Y = float(Y)  # can be negative

            res = self._odes_for_basal_refine([Gp, Gt, Ip, Il, Ipo, Y])
            return np.array(res, dtype=float)

        try:
            sol = root(
                fun,
                x0,
                method="hybr",
                tol=self.steady_refine_tol,
                options={"maxfev": int(self.steady_refine_maxfev)},
            )
            info["success"] = bool(sol.success)
            info["message"] = str(sol.message)
            info["nfev"] = int(getattr(sol, "nfev", 0)) if getattr(sol, "nfev", None) is not None else None

            if bool(sol.success) and sol.x is not None and np.isfinite(sol.x).all():
                r = fun(sol.x)
                info["max_abs_residual"] = float(np.max(np.abs(r))) if r.size else None

                Gp, Gt, Ip, Il, Ipo, Y = sol.x
                self.Gp_b = float(max(Gp, 1e-12))
                self.Gt_b = float(max(Gt, 1e-12))
                self.Ip_b = float(max(Ip, 1e-12))
                self.Il_b = float(max(Il, 1e-12))
                self.Ipo_b = float(max(Ipo, 0.0))

                # Update Ib to match refined Ip (this matters for consistency of X dynamics)
                try:
                    self.p.Ib = float(self.Ip_b / p.Vi)
                except Exception:
                    pass

                # Update derived basal quantities
                S = float(p.gamma * self.Ipo_b)
                self.HE_b = float(np.clip(-p.m5 * S + p.m6, 0.0, 0.95))
                self.m3_b = float(self.HE_b * p.m1 / (1.0 - self.HE_b))
                self.S_b = float(self.m3_b * self.Il_b + p.m4 * self.Ip_b)
                self.EGP_b = float(p.kp1 - p.kp2 * self.Gp_b - p.kp3 * self.p.Ib - p.kp4 * self.Ipo_b)

                # If Y converged far from 0, it's still mathematically valid—keep it.
                # It's a model-specific basal offset.

        except Exception as e:
            info["success"] = False
            info["message"] = f"{type(e).__name__}: {str(e)}"

        return info

    def _check_steady_state_full(self, rtol: float = 1e-5) -> None:
        """
        Checks drift at basal with the *production ODE* (D=0).
        Does NOT emit warnings. Stores diagnostics in calibration_report.
        """
        p = self.p

        # Build a basal state vector for the full ODE
        I_conc = float(self.Ip_b / p.Vi) if p.Vi > 0 else float(p.Ib)
        X = float(I_conc - p.Ib)
        y_basal = [
            float(self.Gp_b),
            float(self.Gt_b),
            float(self.Ip_b),
            float(self.Il_b),
            0.0,
            0.0,
            0.0,
            X,
            I_conc,
            I_conc,
            float(self.Ipo_b),
            0.0,
        ]

        dydt = self._odes(0.0, y_basal, D=0.0)

        failed = []
        is_steady = True
        max_proj = 0.0

        for i, deriv in enumerate(dydt):
            proj = abs(float(deriv)) * float(self.dt_check_minutes)
            max_proj = max(max_proj, proj)
            threshold = float(self._get_tolerance_for_state(i) + (rtol * max(1.0, abs(y_basal[i]))))
            if proj > threshold:
                is_steady = False
                failed.append({"state": self.STATE_NAMES[i], "drift": proj, "threshold": threshold})

        self.calibration_report.setdefault("diagnostics", {})
        self.calibration_report["steady_state_ok"] = bool(is_steady)
        self.calibration_report["failed_states"] = failed
        self.calibration_report["diagnostics"]["steady_state_max_projected_drift"] = float(max_proj)

    # -------------------------
    # Simulation
    # -------------------------
    def simulate(self, inputs: GlucoseInput) -> SimulationResult:
        p = self.p

        # Make metadata robust to poison deepcopy
        try:
            meta = copy.deepcopy(self.calibration_report)
        except Exception as e:
            meta = {"calibration_report_copy_failed": str(e), "flags": {}, "steady_state_ok": None}

        meta.update(
            {
                "basal_params_changed": [],
                "params_changed_since_calibration": False,
                "scientific_invalid_reasons": [],
                "scientific_invalid_reason": None,
                "solver_success": None,
                "solver_message": None,
                "solver_failure_mode": None,
                "has_usable_data": False,
                "is_sim_valid": False,
                "warnings": [],
                "units": {
                    "time": "min",
                    "carbs": "g",
                    "plasma_glucose": "mg/dL",
                    "plasma_insulin": "mU/L",
                },
                "input_summary": {
                    "carbs_g": None,
                    "duration_minutes": None,
                    "time_step_minutes": None,
                },
            }
        )

        sol = None
        failure_mode = None
        _seen = set()

        def add_reason(r: str) -> None:
            if r not in _seen:
                _seen.add(r)
                meta["scientific_invalid_reasons"].append(r)

        # 0) TIME VECTOR (safe)
        try:
            t_eval = inputs.get_time_vector()
        except Exception as e:
            t_eval = np.array([], dtype=float)
            failure_mode = "invalid_input"
            meta["solver_message"] = f"Time vector crashed: {type(e).__name__}"

        # input summary
        try:
            meta["input_summary"]["carbs_g"] = float(inputs.carbs_g)
            meta["input_summary"]["duration_minutes"] = float(inputs.duration_minutes)
            meta["input_summary"]["time_step_minutes"] = float(inputs.time_step_minutes)
        except Exception:
            pass

        # 1) MUTATION / CALIBRATION GUARD
        if failure_mode is None:
            if not self._calibration_params_snapshot:
                if not self._has_basal_state():
                    # Professional behavior: model not calibrated => invalid_model_state immediately
                    add_reason("model_not_calibrated")
                    meta["solver_message"] = meta["solver_message"] or "Model not calibrated"
                    failure_mode = "invalid_model_state"
                else:
                    meta["params_changed_since_calibration"] = True
                    add_reason("basal_params_crash")
                    meta["solver_message"] = meta["solver_message"] or "Calibration snapshot missing"
            else:
                try:
                    diffs = self._basal_param_diffs(
                        {k: float(getattr(p, k)) for k in self.BASAL_DEPENDENCY_KEYS},
                        self._calibration_params_snapshot,
                    )
                    if diffs:
                        meta["params_changed_since_calibration"] = True
                        meta["basal_params_changed"] = diffs
                        add_reason("basal_params_mutated")
                except Exception as e:
                    meta["params_changed_since_calibration"] = True
                    add_reason("basal_params_crash")
                    meta["solver_message"] = f"Param check crashed: {type(e).__name__}"

        # 2) PARAMS + INPUT CHECKS (only if model state is usable)
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
            except Exception as e:
                failure_mode = "invalid_input"
                meta["solver_message"] = str(e)

        # 3) TIME GUARD
        if failure_mode is None:
            try:
                if len(t_eval) < 2 or (not np.isfinite(t_eval).all()):
                    failure_mode = "invalid_time_input"
                else:
                    max_abs_t = float(np.max(np.abs(t_eval)))
                    if not np.isfinite(max_abs_t):
                        failure_mode = "invalid_time_input"
                    else:
                        eps = max(1e-12, 1e-12 * max(1.0, max_abs_t))
                        if not np.all(np.diff(t_eval) > eps):
                            failure_mode = "invalid_time_input"
                if failure_mode:
                    meta["solver_message"] = "Invalid time input"
            except Exception as e:
                failure_mode = "invalid_time_input"
                meta["solver_message"] = f"Time check crashed: {e}"

        # 4) SOLVER
        if failure_mode is None:
            if not self._has_basal_state():
                failure_mode = "invalid_model_state"
                meta["solver_message"] = "Basal state missing"
                add_reason("model_not_calibrated")
            else:
                D = float(inputs.carbs_g) * 1000.0  # grams -> mg
                y0 = [
                    float(self.Gp_b),
                    float(self.Gt_b),
                    float(self.Ip_b),
                    float(self.Il_b),
                    D,
                    0.0,
                    0.0,
                    float((self.Ip_b / p.Vi) - p.Ib),  # X
                    float(self.Ip_b / p.Vi),          # I1
                    float(self.Ip_b / p.Vi),          # Id
                    float(self.Ipo_b),
                    0.0,
                ]
                try:
                    sol = solve_ivp(
                        lambda t, y: self._odes(t, y, D),
                        (t_eval[0], t_eval[-1]),
                        y0,
                        t_eval=t_eval,
                        method="BDF",
                        rtol=1e-6,
                        atol=1e-8,
                    )
                except Exception as e:
                    class Mock:
                        pass

                    sol = Mock()
                    sol.success = False
                    sol.message = f"SciPy Crash: {str(e)}"
                    sol.y = None
                    sol.t = None
                    failure_mode = "scipy_exception"

        # 5) POST-SOLVER SHAPE/TIME CHECKS
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
                elif not (np.isfinite(sol.y).all()):
                    failure_mode = "non_finite_output"

        # 6) FAILURE PATH
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

            self._append_calibration_reasons(meta, add_reason)
            self._resolve_scientific_reason(meta)

            return SimulationResult(
                time_points=t_eval,
                channels={"plasma_glucose": nan, "plasma_insulin": nan},
                metrics={
                    "peak_glucose": np.nan,
                    "time_to_peak": np.nan,
                    "auc_glucose": np.nan,
                    "final_glucose": np.nan,
                },
                metadata=meta,
            )

        # 7) DATA PATH
        G_conc = sol.y[0] / p.Vg
        I_conc = sol.y[2] / p.Vi

        idx = int(np.argmax(G_conc))
        metrics = {
            "peak_glucose": float(G_conc[idx]),
            "time_to_peak": float(t_eval[idx]),
            "auc_glucose": float(_auc(G_conc, t_eval)),
            "final_glucose": float(G_conc[-1]),
        }

        meta["solver_success"] = True
        meta["solver_message"] = getattr(sol, "message", None)
        meta["solver_failure_mode"] = None

        self._append_calibration_reasons(meta, add_reason)
        self._resolve_scientific_reason(meta)

        meta["is_sim_valid"] = (len(meta["scientific_invalid_reasons"]) == 0)
        meta["has_usable_data"] = meta["is_sim_valid"]

        # Soft warnings (not invalidating)
        try:
            if np.isfinite(metrics["peak_glucose"]) and metrics["peak_glucose"] > 300:
                meta["warnings"].append("peak_glucose_high_outlier")
            if np.isfinite(metrics["final_glucose"]) and metrics["final_glucose"] < 40:
                meta["warnings"].append("final_glucose_low_outlier")
        except Exception:
            pass

        return SimulationResult(
            time_points=t_eval,
            channels={"plasma_glucose": G_conc, "plasma_insulin": I_conc},
            metrics=metrics,
            metadata=meta,
        )