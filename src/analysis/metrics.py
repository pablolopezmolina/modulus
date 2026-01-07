# src/analysis/metrics.py
"""
MODULUS Metrics Calculator.

This module provides pure functions for calculating metabolic and performance
metrics from simulation results. All functions are stateless and deterministic.

Metrics Categories:
1. Glucose Metrics: peak, time_to_peak, AUC, time_above_threshold
2. Caffeine Metrics: peak, half_life
3. Alertness Metrics: peak, duration_above_threshold
4. Risk Metrics: sleep_disruption_risk

Usage:
    from src.analysis.metrics import calculate_all_metrics
    
    metrics = calculate_all_metrics(
        time_minutes=result.time_minutes,
        glucose_curve=result.glucose_curve,
        caffeine_curve=result.caffeine_curve,
        alertness_curve=result.alertness_curve,
    )
"""

from typing import Dict, Optional, Union
import numpy as np

# Type alias for numeric values
NumericValue = Union[int, float, np.floating]


# =============================================================================
# GLUCOSE METRICS
# =============================================================================

def calculate_glucose_peak(glucose_curve: np.ndarray) -> float:
    """
    Calculate the peak (maximum) glucose value.
    
    Args:
        glucose_curve: Glucose values in mg/dL over time
        
    Returns:
        Peak glucose value in mg/dL
        
    Raises:
        ValueError: If glucose_curve is empty or contains invalid values
    """
    if len(glucose_curve) == 0:
        raise ValueError("glucose_curve cannot be empty")
    
    # Check for inf values
    if np.any(np.isinf(glucose_curve)):
        raise ValueError("glucose_curve contains infinite values")
    
    # Use nanmax to handle any NaN values gracefully
    peak = np.nanmax(glucose_curve)
    return float(peak)


def calculate_glucose_time_to_peak(
    time_minutes: np.ndarray,
    glucose_curve: np.ndarray,
) -> float:
    """
    Calculate the time to reach peak glucose.
    
    Args:
        time_minutes: Time points in minutes
        glucose_curve: Glucose values in mg/dL
        
    Returns:
        Time to peak glucose in minutes
        
    Raises:
        ValueError: If arrays have different lengths or are empty
    """
    if len(time_minutes) != len(glucose_curve):
        raise ValueError("time_minutes and glucose_curve must have same length")
    
    if len(glucose_curve) == 0:
        raise ValueError("Arrays cannot be empty")
    
    # Find index of maximum (first occurrence if multiple)
    peak_idx = np.nanargmax(glucose_curve)
    return float(time_minutes[peak_idx])


def calculate_glucose_auc(
    time_minutes: np.ndarray,
    glucose_curve: np.ndarray,
    baseline: Optional[float] = None,
) -> float:
    """
    Calculate the Area Under the Curve (AUC) for glucose.
    
    Uses trapezoidal integration. If baseline is provided, calculates
    the incremental AUC above baseline.
    
    Args:
        time_minutes: Time points in minutes
        glucose_curve: Glucose values in mg/dL
        baseline: Optional baseline to subtract (default: 0)
        
    Returns:
        AUC in mg/dL * minutes
    """
    if len(time_minutes) != len(glucose_curve):
        raise ValueError("time_minutes and glucose_curve must have same length")
    
    if baseline is not None:
        # Incremental AUC above baseline (negative parts counted as 0)
        adjusted_curve = np.maximum(glucose_curve - baseline, 0)
    else:
        adjusted_curve = glucose_curve
    
    # Trapezoidal integration
    # Use trapezoid (numpy >= 2.0) or fallback to trapz
    if hasattr(np, 'trapezoid'):
        auc = np.trapezoid(adjusted_curve, time_minutes)
    else:
        auc = np.trapz(adjusted_curve, time_minutes)
    return float(auc)


def calculate_time_above_glucose_threshold(
    time_minutes: np.ndarray,
    glucose_curve: np.ndarray,
    threshold: float = 140.0,
) -> float:
    """
    Calculate the percentage of time glucose is above a threshold.
    
    Args:
        time_minutes: Time points in minutes
        glucose_curve: Glucose values in mg/dL
        threshold: Glucose threshold in mg/dL (default: 140, pre-diabetic level)
        
    Returns:
        Percentage of time above threshold (0-100)
    """
    if len(time_minutes) != len(glucose_curve):
        raise ValueError("time_minutes and glucose_curve must have same length")
    
    if len(glucose_curve) == 0:
        return 0.0
    
    # Count points above threshold
    above_threshold = glucose_curve > threshold
    n_above = np.sum(above_threshold)
    
    # Calculate percentage
    percentage = (n_above / len(glucose_curve)) * 100.0
    return float(percentage)


# =============================================================================
# CAFFEINE METRICS
# =============================================================================

def calculate_caffeine_peak(caffeine_curve: np.ndarray) -> float:
    """
    Calculate the peak (maximum) caffeine concentration.
    
    Args:
        caffeine_curve: Caffeine concentrations in mg/L over time
        
    Returns:
        Peak caffeine concentration in mg/L
    """
    if len(caffeine_curve) == 0:
        raise ValueError("caffeine_curve cannot be empty")
    
    peak = np.nanmax(caffeine_curve)
    return float(peak)


def calculate_caffeine_half_life(
    time_minutes: np.ndarray,
    caffeine_curve: np.ndarray,
) -> float:
    """
    Estimate caffeine half-life from the elimination phase.
    
    Calculates half-life by finding when caffeine drops to 50% of peak.
    Returns NaN if no caffeine present, inf if caffeine never decays.
    
    Args:
        time_minutes: Time points in minutes
        caffeine_curve: Caffeine concentrations in mg/L
        
    Returns:
        Estimated half-life in minutes, NaN if cannot calculate, inf if no decay
    """
    if len(caffeine_curve) == 0:
        return float("nan")
    
    peak = np.nanmax(caffeine_curve)
    
    # No caffeine present
    if peak < 0.01:  # Threshold for "no caffeine"
        return float("nan")
    
    # Find peak index
    peak_idx = np.nanargmax(caffeine_curve)
    
    # Only look at elimination phase (after peak)
    elim_curve = caffeine_curve[peak_idx:]
    elim_time = time_minutes[peak_idx:]
    
    if len(elim_curve) < 2:
        return float("nan")
    
    # Find half-max concentration
    half_peak = peak / 2.0
    
    # Find where concentration drops below half-peak
    below_half = elim_curve < half_peak
    
    if not np.any(below_half):
        # Caffeine never drops to half - infinite half-life
        return float("inf")
    
    # First index where caffeine is below half-peak
    half_idx = np.argmax(below_half)
    
    if half_idx == 0:
        # Already at half at peak (shouldn't happen normally)
        return float("nan")
    
    # Calculate half-life as time from peak to half-peak
    half_life = elim_time[half_idx] - elim_time[0]
    return float(half_life)


# =============================================================================
# ALERTNESS METRICS
# =============================================================================

def calculate_alertness_peak(alertness_curve: np.ndarray) -> float:
    """
    Calculate the peak alertness score.
    
    Args:
        alertness_curve: Alertness scores (0-100) over time
        
    Returns:
        Peak alertness score (0-100)
    """
    if len(alertness_curve) == 0:
        raise ValueError("alertness_curve cannot be empty")
    
    peak = np.nanmax(alertness_curve)
    return float(peak)


def calculate_alertness_duration_above_threshold(
    time_minutes: np.ndarray,
    alertness_curve: np.ndarray,
    threshold: float = 60.0,
) -> float:
    """
    Calculate total duration alertness is above a threshold.
    
    Args:
        time_minutes: Time points in minutes
        alertness_curve: Alertness scores (0-100)
        threshold: Alertness threshold (default: 60, "good alertness")
        
    Returns:
        Total duration above threshold in minutes
    """
    if len(time_minutes) != len(alertness_curve):
        raise ValueError("time_minutes and alertness_curve must have same length")
    
    if len(alertness_curve) == 0:
        return 0.0
    
    # For uniform time spacing, we can simply count
    above = alertness_curve > threshold
    
    # Assuming dt=1 minute (standard), count equals duration
    # For non-uniform spacing, would need to integrate
    if len(time_minutes) > 1:
        dt = time_minutes[1] - time_minutes[0]
    else:
        dt = 1.0
    
    duration = np.sum(above) * dt
    return float(duration)


# =============================================================================
# RISK METRICS
# =============================================================================

def calculate_sleep_disruption_risk(
    time_minutes: np.ndarray,
    caffeine_curve: np.ndarray,
    bedtime_minutes: float = 1320.0,  # 22:00 = 10 PM
    threshold_mg_l: float = 1.0,
) -> float:
    """
    Calculate risk of sleep disruption based on caffeine at bedtime.
    
    Risk is calculated as a sigmoid function of caffeine level at bedtime:
    - 0 risk at 0 mg/L
    - 50% risk at threshold (default 1 mg/L)
    - Approaches 100% at high levels
    
    Args:
        time_minutes: Time points in minutes
        caffeine_curve: Caffeine concentrations in mg/L
        bedtime_minutes: Time of bedtime in minutes (default: 22:00)
        threshold_mg_l: Caffeine level for 50% risk (default: 1.0 mg/L)
        
    Returns:
        Risk score between 0 and 1
    """
    if len(caffeine_curve) == 0:
        return 0.0
    
    # Find caffeine level at bedtime
    # Find closest time point to bedtime
    if bedtime_minutes > time_minutes[-1]:
        # Bedtime is beyond simulation - use last value
        caffeine_at_bedtime = caffeine_curve[-1]
    elif bedtime_minutes < time_minutes[0]:
        # Bedtime is before simulation - use first value
        caffeine_at_bedtime = caffeine_curve[0]
    else:
        # Interpolate or find nearest
        idx = np.searchsorted(time_minutes, bedtime_minutes)
        if idx >= len(caffeine_curve):
            idx = len(caffeine_curve) - 1
        caffeine_at_bedtime = caffeine_curve[idx]
    
    # No caffeine = no risk
    if caffeine_at_bedtime < 0.01:
        return 0.0
    
    # Sigmoid function for risk
    # risk = 1 / (1 + exp(-k*(x - threshold)))
    # We want: risk(0) ≈ 0, risk(threshold) = 0.5, risk(2*threshold) ≈ 0.88
    k = 2.0 / threshold_mg_l  # Steepness parameter
    x = caffeine_at_bedtime
    
    risk = 1.0 / (1.0 + np.exp(-k * (x - threshold_mg_l)))
    
    return float(risk)


# =============================================================================
# BATCH CALCULATOR
# =============================================================================

class MetricsCalculator:
    """
    Batch metrics calculator for DaySimulationResult.
    
    This class provides a convenient interface for calculating all metrics
    at once, with optional customization of thresholds.
    
    Example:
        calc = MetricsCalculator(glucose_threshold=140, alertness_threshold=60)
        metrics = calc.calculate(
            time_minutes=result.time_minutes,
            glucose_curve=result.glucose_curve,
            caffeine_curve=result.caffeine_curve,
            alertness_curve=result.alertness_curve,
        )
    """
    
    def __init__(
        self,
        glucose_threshold: float = 140.0,
        alertness_threshold: float = 60.0,
        bedtime_minutes: float = 1320.0,
        caffeine_risk_threshold: float = 1.0,
    ):
        """
        Initialize the calculator with optional threshold customization.
        
        Args:
            glucose_threshold: Threshold for hyperglycemia (default: 140 mg/dL)
            alertness_threshold: Threshold for "good alertness" (default: 60%)
            bedtime_minutes: Bedtime for sleep risk calc (default: 22:00)
            caffeine_risk_threshold: Caffeine for 50% sleep risk (default: 1 mg/L)
        """
        self.glucose_threshold = glucose_threshold
        self.alertness_threshold = alertness_threshold
        self.bedtime_minutes = bedtime_minutes
        self.caffeine_risk_threshold = caffeine_risk_threshold
    
    def calculate(
        self,
        time_minutes: np.ndarray,
        glucose_curve: np.ndarray,
        caffeine_curve: np.ndarray,
        alertness_curve: np.ndarray,
    ) -> Dict[str, float]:
        """
        Calculate all metrics from simulation curves.
        
        Args:
            time_minutes: Time array in minutes
            glucose_curve: Glucose concentrations in mg/dL
            caffeine_curve: Caffeine concentrations in mg/L
            alertness_curve: Alertness scores (0-100)
            
        Returns:
            Dictionary with all calculated metrics
        """
        return calculate_all_metrics(
            time_minutes=time_minutes,
            glucose_curve=glucose_curve,
            caffeine_curve=caffeine_curve,
            alertness_curve=alertness_curve,
            glucose_threshold=self.glucose_threshold,
            alertness_threshold=self.alertness_threshold,
            bedtime_minutes=self.bedtime_minutes,
            caffeine_risk_threshold=self.caffeine_risk_threshold,
        )


def calculate_all_metrics(
    time_minutes: np.ndarray,
    glucose_curve: np.ndarray,
    caffeine_curve: np.ndarray,
    alertness_curve: np.ndarray,
    glucose_threshold: float = 140.0,
    alertness_threshold: float = 60.0,
    bedtime_minutes: float = 1320.0,
    caffeine_risk_threshold: float = 1.0,
) -> Dict[str, float]:
    """
    Calculate all standard metrics from simulation curves.
    
    This is the main entry point for batch metric calculation.
    
    Args:
        time_minutes: Time array in minutes
        glucose_curve: Glucose concentrations in mg/dL
        caffeine_curve: Caffeine concentrations in mg/L
        alertness_curve: Alertness scores (0-100)
        glucose_threshold: Threshold for hyperglycemia (default: 140 mg/dL)
        alertness_threshold: Threshold for "good alertness" (default: 60%)
        bedtime_minutes: Bedtime for sleep risk calc (default: 22:00)
        caffeine_risk_threshold: Caffeine for 50% sleep risk (default: 1 mg/L)
        
    Returns:
        Dictionary containing:
        - glucose_peak: Peak glucose (mg/dL)
        - glucose_time_to_peak: Time to peak glucose (minutes)
        - glucose_auc: Area under glucose curve (mg/dL * min)
        - time_above_glucose_140: % time above threshold
        - caffeine_peak: Peak caffeine (mg/L)
        - caffeine_half_life: Estimated half-life (minutes)
        - alertness_peak: Peak alertness (0-100)
        - alertness_duration_above_60: Duration above threshold (minutes)
        - sleep_disruption_risk: Sleep disruption risk (0-1)
    """
    metrics = {}
    
    # Glucose metrics
    metrics["glucose_peak"] = calculate_glucose_peak(glucose_curve)
    metrics["glucose_time_to_peak"] = calculate_glucose_time_to_peak(
        time_minutes, glucose_curve
    )
    metrics["glucose_auc"] = calculate_glucose_auc(time_minutes, glucose_curve)
    metrics["time_above_glucose_140"] = calculate_time_above_glucose_threshold(
        time_minutes, glucose_curve, threshold=glucose_threshold
    )
    
    # Caffeine metrics
    metrics["caffeine_peak"] = calculate_caffeine_peak(caffeine_curve)
    metrics["caffeine_half_life"] = calculate_caffeine_half_life(
        time_minutes, caffeine_curve
    )
    
    # Alertness metrics
    metrics["alertness_peak"] = calculate_alertness_peak(alertness_curve)
    metrics["alertness_duration_above_60"] = calculate_alertness_duration_above_threshold(
        time_minutes, alertness_curve, threshold=alertness_threshold
    )
    
    # Risk metrics
    metrics["sleep_disruption_risk"] = calculate_sleep_disruption_risk(
        time_minutes, caffeine_curve,
        bedtime_minutes=bedtime_minutes,
        threshold_mg_l=caffeine_risk_threshold,
    )
    
    return metrics
