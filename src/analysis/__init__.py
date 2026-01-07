"""
Analysis Module - MODULUS

Contains analysis tools for evaluating simulation results:
- metrics: Calculation of business metrics from simulation curves
- risk: Risk analysis and risk maps
- decision: Decision engine (Go/Caution/No-Go)
- claims: Claim defensibility analysis
"""

# Metrics
from src.analysis.metrics import (
    MetricsCalculator,
    calculate_all_metrics,
    calculate_glucose_peak,
    calculate_glucose_time_to_peak,
    calculate_glucose_auc,
    calculate_time_above_glucose_threshold,
    calculate_caffeine_peak,
    calculate_caffeine_half_life,
    calculate_alertness_peak,
    calculate_alertness_duration_above_threshold,
    calculate_sleep_disruption_risk,
)

# Risk Analysis
from src.analysis.risk import (
    RiskLevel,
    RiskThresholds,
    RiskMetric,
    SegmentRisk,
    RiskMap,
    DangerZone,
    RiskAnalyzer,
    RiskAnalysisResult,
)

# Decision Engine
from src.analysis.decision import (
    Verdict,
    RiskSummary,
    SegmentAtRisk,
    DecisionConfig,
    Decision,
    DecisionEngine,
)

# Claims Analysis
from src.analysis.claims import (
    ClaimDefinition,
    ClaimAnalysis,
    ClaimAnalyzerConfig,
    ClaimAnalysisResult,
    ClaimAnalyzer,
    get_default_claims,
)

__all__ = [
    # Metrics
    "MetricsCalculator",
    "calculate_all_metrics",
    "calculate_glucose_peak",
    "calculate_glucose_time_to_peak",
    "calculate_glucose_auc",
    "calculate_time_above_glucose_threshold",
    "calculate_caffeine_peak",
    "calculate_caffeine_half_life",
    "calculate_alertness_peak",
    "calculate_alertness_duration_above_threshold",
    "calculate_sleep_disruption_risk",
    # Risk
    "RiskLevel",
    "RiskThresholds",
    "RiskMetric",
    "SegmentRisk",
    "RiskMap",
    "DangerZone",
    "RiskAnalyzer",
    "RiskAnalysisResult",
    # Decision
    "Verdict",
    "RiskSummary",
    "SegmentAtRisk",
    "DecisionConfig",
    "Decision",
    "DecisionEngine",
    # Claims
    "ClaimDefinition",
    "ClaimAnalysis",
    "ClaimAnalyzerConfig",
    "ClaimAnalysisResult",
    "ClaimAnalyzer",
    "get_default_claims",
]
