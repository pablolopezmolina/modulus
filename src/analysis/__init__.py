# src/analysis/__init__.py
"""
MODULUS Analysis Module.

This module provides metrics calculation, risk analysis, and claim defensibility
tools for evaluating supplement formulations.

Submodules:
- metrics: Basic metabolic and performance metrics
- risk: Risk mapping and segmentation (future)
- claims: Claim defensibility analysis (future)
- decision: Go/Caution/No-Go decision engine (future)
"""

from src.analysis.metrics import (
    # Individual metric functions
    calculate_glucose_peak,
    calculate_glucose_time_to_peak,
    calculate_glucose_auc,
    calculate_time_above_glucose_threshold,
    calculate_caffeine_peak,
    calculate_caffeine_half_life,
    calculate_alertness_peak,
    calculate_alertness_duration_above_threshold,
    calculate_sleep_disruption_risk,
    # Batch calculator
    MetricsCalculator,
    calculate_all_metrics,
)

__all__ = [
    # Glucose metrics
    "calculate_glucose_peak",
    "calculate_glucose_time_to_peak",
    "calculate_glucose_auc",
    "calculate_time_above_glucose_threshold",
    # Caffeine metrics
    "calculate_caffeine_peak",
    "calculate_caffeine_half_life",
    # Alertness metrics
    "calculate_alertness_peak",
    "calculate_alertness_duration_above_threshold",
    # Risk metrics
    "calculate_sleep_disruption_risk",
    # Batch calculator
    "MetricsCalculator",
    "calculate_all_metrics",
]
