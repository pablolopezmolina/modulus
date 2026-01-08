# MODULUS - A/B Comparison Engine
# Session 10.2: Compare formulations and determine winner
# ==============================================================================

"""
A/B Comparison Engine for MODULUS.

This module provides functionality to compare two or more PopulationSimulationResults
and determine which formulation performs better across various metrics.

Key Features:
- Metric-by-metric comparison with delta calculation
- Risk comparison with absolute improvement
- Statistical significance testing (Welch's t-test approximation)
- Effect size calculation (Cohen's d)
- Overall winner determination with confidence scoring
- PDF/report-ready output formatting
- Multi-product comparison and ranking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import json
import math
from datetime import datetime, timezone


# ==============================================================================
# CONSTANTS: Metric Directions
# ==============================================================================

# Define whether higher or lower is better for each metric
METRIC_DIRECTIONS: Dict[str, str] = {
    # Glucose metrics - lower is generally better (less spikes)
    "glucose_peak": "lower",
    "glucose_auc": "lower",
    "glucose_time_above_140": "lower",
    "glucose_time_above_180": "lower",
    
    # Alertness metrics - higher is generally better
    "alertness_peak": "higher",
    "alertness_duration_above_60": "higher",
    "alertness_duration_above_70": "higher",
    "alertness_mean": "higher",
    
    # Timing metrics - lower (faster) is better
    "time_to_alertness_peak": "lower",
    "time_to_glucose_peak": "lower",
    
    # Caffeine metrics - context dependent, default to neutral
    "caffeine_peak": "neutral",  # Depends on use case
    "caffeine_half_life": "neutral",
    "caffeine_auc": "neutral",
}

# Risk metrics - ALL should be lower (less risk = better)
RISK_DIRECTIONS: Dict[str, str] = {
    "pct_hyperglycemia": "lower",
    "pct_severe_hyperglycemia": "lower",
    "pct_hypoglycemia": "lower",
    "pct_jitter_risk": "lower",
    "pct_sleep_disruption": "lower",
    "pct_crash_risk": "lower",
}


# ==============================================================================
# ENUMS
# ==============================================================================

class Winner(Enum):
    """Winner enumeration for comparisons."""
    A = "A"
    B = "B"
    TIE = "TIE"


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class ComparisonConfig:
    """Configuration for comparison engine."""
    
    # Statistical significance threshold (p-value)
    significance_threshold: float = 0.05
    
    # Percent difference threshold for declaring tie
    tie_threshold_percent: float = 5.0
    
    # Minimum effect size (Cohen's d) to consider meaningful
    min_effect_size: float = 0.2
    
    # Weight for different metric categories in overall winner
    metric_weight: float = 0.6
    risk_weight: float = 0.4
    
    # Custom metric directions (overrides defaults)
    metric_directions: Dict[str, str] = field(default_factory=dict)
    
    def get_direction(self, metric_name: str) -> str:
        """Get the direction for a metric (higher/lower/neutral)."""
        if metric_name in self.metric_directions:
            return self.metric_directions[metric_name]
        if metric_name in METRIC_DIRECTIONS:
            return METRIC_DIRECTIONS[metric_name]
        # Default to "higher" for unknown metrics
        return "higher"


# ==============================================================================
# DATA CLASSES: Comparison Results
# ==============================================================================

@dataclass(frozen=True)
class MetricComparison:
    """Comparison result for a single metric."""
    
    metric_name: str
    value_a: float
    value_b: float
    delta: float  # B - A
    delta_percent: float  # (B - A) / A * 100
    winner: str  # "A", "B", or "TIE"
    is_significant: bool
    p_value: Optional[float]
    effect_size: Optional[float]  # Cohen's d
    better_direction: str  # "higher" or "lower"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "winner": self.winner,
            "is_significant": self.is_significant,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "better_direction": self.better_direction,
        }


@dataclass(frozen=True)
class RiskComparison:
    """Comparison result for a risk metric."""
    
    risk_name: str
    value_a: float
    value_b: float
    delta: float  # B - A
    delta_percent: float  # (B - A) / A * 100
    winner: str  # "A", "B", or "TIE"
    absolute_improvement: float  # Always positive, how much better
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_name": self.risk_name,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "winner": self.winner,
            "absolute_improvement": self.absolute_improvement,
        }


@dataclass
class Comparison:
    """Full comparison result between two formulations."""
    
    # Identification
    formulation_a_name: str
    formulation_b_name: str
    n_individuals_a: int
    n_individuals_b: int
    
    # Detailed comparisons
    metric_comparisons: Dict[str, MetricComparison]
    risk_comparisons: Dict[str, RiskComparison]
    
    # Winner summaries
    winner_by_metric: Dict[str, Winner]
    winner_by_risk: Dict[str, Winner]
    
    # Overall result
    overall_winner: Winner
    overall_confidence: float  # 0-1
    summary: str
    
    # Metadata
    comparison_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "formulation_a_name": self.formulation_a_name,
            "formulation_b_name": self.formulation_b_name,
            "n_individuals_a": self.n_individuals_a,
            "n_individuals_b": self.n_individuals_b,
            "metric_comparisons": {
                k: v.to_dict() for k, v in self.metric_comparisons.items()
            },
            "risk_comparisons": {
                k: v.to_dict() for k, v in self.risk_comparisons.items()
            },
            "winner_by_metric": {k: v.value for k, v in self.winner_by_metric.items()},
            "winner_by_risk": {k: v.value for k, v in self.winner_by_risk.items()},
            "overall_winner": self.overall_winner.value,
            "overall_confidence": self.overall_confidence,
            "summary": self.summary,
            "comparison_timestamp": self.comparison_timestamp,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def get_top_differences(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get top N differences sorted by absolute delta percent."""
        all_diffs = []
        
        # Add metric comparisons
        for mc in self.metric_comparisons.values():
            all_diffs.append({
                "type": "metric",
                "name": mc.metric_name,
                "delta_percent": mc.delta_percent,
                "winner": mc.winner,
                "value_a": mc.value_a,
                "value_b": mc.value_b,
            })
        
        # Add risk comparisons
        for rc in self.risk_comparisons.values():
            all_diffs.append({
                "type": "risk",
                "name": rc.risk_name,
                "delta_percent": rc.delta_percent,
                "winner": rc.winner,
                "value_a": rc.value_a,
                "value_b": rc.value_b,
            })
        
        # Sort by absolute delta percent
        all_diffs.sort(key=lambda x: abs(x["delta_percent"]), reverse=True)
        
        return all_diffs[:n]
    
    def format_for_pdf(self) -> Dict[str, Any]:
        """Format comparison data for PDF generation."""
        # Metric table
        metric_rows = []
        for mc in self.metric_comparisons.values():
            metric_rows.append({
                "metric": _format_metric_name(mc.metric_name),
                "value_a": _format_value(mc.value_a, mc.metric_name),
                "value_b": _format_value(mc.value_b, mc.metric_name),
                "delta": f"{mc.delta:+.1f}",
                "delta_percent": f"{mc.delta_percent:+.1f}%",
                "winner": mc.winner,
                "significant": "✓" if mc.is_significant else "",
            })
        
        # Risk table
        risk_rows = []
        for rc in self.risk_comparisons.values():
            risk_rows.append({
                "risk": _format_metric_name(rc.risk_name),
                "value_a": f"{rc.value_a * 100:.1f}%",
                "value_b": f"{rc.value_b * 100:.1f}%",
                "delta": f"{rc.delta * 100:+.1f}pp",
                "improvement": f"{rc.absolute_improvement * 100:.1f}pp",
                "winner": rc.winner,
            })
        
        # Winner summary
        a_wins = sum(1 for w in self.winner_by_metric.values() if w == Winner.A)
        b_wins = sum(1 for w in self.winner_by_metric.values() if w == Winner.B)
        ties = sum(1 for w in self.winner_by_metric.values() if w == Winner.TIE)
        
        a_risk_wins = sum(1 for w in self.winner_by_risk.values() if w == Winner.A)
        b_risk_wins = sum(1 for w in self.winner_by_risk.values() if w == Winner.B)
        
        return {
            "title": f"Comparison: {self.formulation_a_name} vs {self.formulation_b_name}",
            "executive_summary": self.summary,
            "metric_table": {
                "headers": ["Metric", self.formulation_a_name, self.formulation_b_name, 
                           "Δ", "Δ%", "Winner", "Sig."],
                "rows": metric_rows,
            },
            "risk_table": {
                "headers": ["Risk", self.formulation_a_name, self.formulation_b_name,
                           "Δ", "Improvement", "Winner"],
                "rows": risk_rows,
            },
            "winner_summary": {
                "overall_winner": self.overall_winner.value,
                "confidence": f"{self.overall_confidence * 100:.0f}%",
                "metric_wins": {"A": a_wins, "B": b_wins, "TIE": ties},
                "risk_wins": {"A": a_risk_wins, "B": b_risk_wins},
            },
            "top_differences": self.get_top_differences(5),
        }


# ==============================================================================
# COMPARISON ENGINE
# ==============================================================================

class ComparisonEngine:
    """Engine for comparing PopulationSimulationResults."""
    
    def __init__(self, config: Optional[ComparisonConfig] = None):
        """Initialize comparison engine with optional configuration."""
        self.config = config or ComparisonConfig()
    
    def compare(self, result_a: Any, result_b: Any) -> Comparison:
        """
        Compare two PopulationSimulationResults.
        
        Args:
            result_a: First simulation result (baseline)
            result_b: Second simulation result (comparison)
            
        Returns:
            Comparison object with detailed analysis
        """
        # Extract names
        name_a = getattr(result_a, 'formulation_name', 'Product A')
        name_b = getattr(result_b, 'formulation_name', 'Product B')
        
        # Compare metrics
        metric_comparisons = self._compare_metrics(result_a, result_b)
        
        # Compare risks
        risk_comparisons = self._compare_risks(result_a, result_b)
        
        # Determine winners per metric
        winner_by_metric = {
            name: Winner[mc.winner] if mc.winner != "TIE" else Winner.TIE
            for name, mc in metric_comparisons.items()
        }
        
        # Determine winners per risk
        winner_by_risk = {
            name: Winner[rc.winner] if rc.winner != "TIE" else Winner.TIE
            for name, rc in risk_comparisons.items()
        }
        
        # Determine overall winner
        overall_winner, confidence = self._determine_overall_winner(
            winner_by_metric, winner_by_risk
        )
        
        # Generate summary
        summary = self._generate_summary(
            name_a, name_b,
            metric_comparisons, risk_comparisons,
            overall_winner, confidence
        )
        
        return Comparison(
            formulation_a_name=name_a,
            formulation_b_name=name_b,
            n_individuals_a=result_a.n_individuals,
            n_individuals_b=result_b.n_individuals,
            metric_comparisons=metric_comparisons,
            risk_comparisons=risk_comparisons,
            winner_by_metric=winner_by_metric,
            winner_by_risk=winner_by_risk,
            overall_winner=overall_winner,
            overall_confidence=confidence,
            summary=summary,
        )
    
    def compare_multiple(self, results: List[Any]) -> List[Comparison]:
        """
        Compare multiple products pairwise.
        
        Args:
            results: List of PopulationSimulationResults
            
        Returns:
            List of Comparison objects for each pair
        """
        comparisons = []
        n = len(results)
        
        for i in range(n):
            for j in range(i + 1, n):
                comp = self.compare(results[i], results[j])
                comparisons.append(comp)
        
        return comparisons
    
    def rank_products(self, results: List[Any]) -> List[Dict[str, Any]]:
        """
        Rank multiple products by overall performance.
        
        Args:
            results: List of PopulationSimulationResults
            
        Returns:
            List of products ranked best to worst with scores
        """
        # Get pairwise comparisons
        comparisons = self.compare_multiple(results)
        
        # Calculate win/loss/tie for each product
        names = [getattr(r, 'formulation_name', f'Product {i}') 
                 for i, r in enumerate(results)]
        scores = {name: {"wins": 0, "losses": 0, "ties": 0, "score": 0.0} 
                  for name in names}
        
        for comp in comparisons:
            if comp.overall_winner == Winner.A:
                scores[comp.formulation_a_name]["wins"] += 1
                scores[comp.formulation_a_name]["score"] += 1.0 * comp.overall_confidence
                scores[comp.formulation_b_name]["losses"] += 1
            elif comp.overall_winner == Winner.B:
                scores[comp.formulation_b_name]["wins"] += 1
                scores[comp.formulation_b_name]["score"] += 1.0 * comp.overall_confidence
                scores[comp.formulation_a_name]["losses"] += 1
            else:  # TIE
                scores[comp.formulation_a_name]["ties"] += 1
                scores[comp.formulation_b_name]["ties"] += 1
                scores[comp.formulation_a_name]["score"] += 0.5
                scores[comp.formulation_b_name]["score"] += 0.5
        
        # Create ranking
        ranking = [
            {
                "name": name,
                "rank": 0,  # Will be filled
                "wins": data["wins"],
                "losses": data["losses"],
                "ties": data["ties"],
                "score": data["score"],
            }
            for name, data in scores.items()
        ]
        
        # Sort by score descending
        ranking.sort(key=lambda x: x["score"], reverse=True)
        
        # Assign ranks
        for i, item in enumerate(ranking):
            item["rank"] = i + 1
        
        return ranking
    
    def _compare_metrics(
        self, result_a: Any, result_b: Any
    ) -> Dict[str, MetricComparison]:
        """Compare all metrics between two results."""
        comparisons = {}
        
        metrics_a = result_a.metrics_stats
        metrics_b = result_b.metrics_stats
        
        # Find common metrics
        common_metrics = set(metrics_a.keys()) & set(metrics_b.keys())
        
        for metric_name in common_metrics:
            stats_a = metrics_a[metric_name]
            stats_b = metrics_b[metric_name]
            
            mc = self._compare_single_metric(
                metric_name,
                stats_a,
                stats_b,
                result_a.n_individuals,
                result_b.n_individuals,
            )
            comparisons[metric_name] = mc
        
        return comparisons
    
    def _compare_single_metric(
        self,
        metric_name: str,
        stats_a: Dict[str, float],
        stats_b: Dict[str, float],
        n_a: int,
        n_b: int,
    ) -> MetricComparison:
        """Compare a single metric."""
        mean_a = stats_a["mean"]
        mean_b = stats_b["mean"]
        std_a = stats_a.get("std", 0.0)
        std_b = stats_b.get("std", 0.0)
        
        # Calculate delta
        delta = mean_b - mean_a
        
        # Calculate delta percent (handle zero)
        if abs(mean_a) > 1e-10:
            delta_percent = (delta / mean_a) * 100
        else:
            delta_percent = float('inf') if delta > 0 else (-float('inf') if delta < 0 else 0.0)
        
        # Get direction preference
        direction = self.config.get_direction(metric_name)
        
        # Calculate statistical significance
        p_value = self._calculate_p_value(mean_a, std_a, n_a, mean_b, std_b, n_b)
        is_significant = p_value is not None and p_value < self.config.significance_threshold
        
        # Calculate effect size (Cohen's d)
        effect_size = self._calculate_effect_size(mean_a, std_a, mean_b, std_b)
        
        # Determine winner
        winner = self._determine_metric_winner(
            delta_percent, direction, is_significant, effect_size
        )
        
        return MetricComparison(
            metric_name=metric_name,
            value_a=mean_a,
            value_b=mean_b,
            delta=delta,
            delta_percent=delta_percent if abs(delta_percent) != float('inf') else 
                          (100.0 if delta > 0 else -100.0),
            winner=winner,
            is_significant=is_significant,
            p_value=p_value,
            effect_size=effect_size,
            better_direction=direction,
        )
    
    def _compare_risks(
        self, result_a: Any, result_b: Any
    ) -> Dict[str, RiskComparison]:
        """Compare all risk metrics between two results."""
        comparisons = {}
        
        risks_a = result_a.risk_analysis
        risks_b = result_b.risk_analysis
        
        # Find common risks
        common_risks = set(risks_a.keys()) & set(risks_b.keys())
        
        for risk_name in common_risks:
            value_a = risks_a[risk_name]
            value_b = risks_b[risk_name]
            
            rc = self._compare_single_risk(risk_name, value_a, value_b)
            comparisons[risk_name] = rc
        
        return comparisons
    
    def _compare_single_risk(
        self,
        risk_name: str,
        value_a: float,
        value_b: float,
    ) -> RiskComparison:
        """Compare a single risk metric."""
        delta = value_b - value_a
        
        # Calculate delta percent
        if abs(value_a) > 1e-10:
            delta_percent = (delta / value_a) * 100
        else:
            delta_percent = 0.0
        
        # For risks, lower is ALWAYS better
        # If delta < 0, B is better (lower risk)
        if delta < -self.config.tie_threshold_percent / 100:
            winner = "B"
        elif delta > self.config.tie_threshold_percent / 100:
            winner = "A"
        else:
            winner = "TIE"
        
        # Absolute improvement
        absolute_improvement = abs(delta)
        
        return RiskComparison(
            risk_name=risk_name,
            value_a=value_a,
            value_b=value_b,
            delta=delta,
            delta_percent=delta_percent,
            winner=winner,
            absolute_improvement=absolute_improvement,
        )
    
    def _calculate_p_value(
        self,
        mean_a: float, std_a: float, n_a: int,
        mean_b: float, std_b: float, n_b: int,
    ) -> Optional[float]:
        """
        Calculate approximate p-value using Welch's t-test.
        
        This is an approximation without scipy.
        """
        if std_a <= 0 and std_b <= 0:
            return None
        
        # Standard error
        se_a = std_a / math.sqrt(n_a) if std_a > 0 and n_a > 0 else 0
        se_b = std_b / math.sqrt(n_b) if std_b > 0 and n_b > 0 else 0
        
        se_diff = math.sqrt(se_a**2 + se_b**2)
        
        if se_diff <= 0:
            return None
        
        # t-statistic
        t_stat = abs(mean_b - mean_a) / se_diff
        
        # Approximate degrees of freedom (Welch-Satterthwaite)
        if se_a > 0 and se_b > 0:
            num = (se_a**2 + se_b**2)**2
            denom = (se_a**4 / (n_a - 1)) + (se_b**4 / (n_b - 1))
            df = num / denom if denom > 0 else n_a + n_b - 2
        else:
            df = n_a + n_b - 2
        
        # Approximate p-value using normal approximation for large df
        # For df > 30, t-distribution ≈ normal distribution
        if df > 30:
            # Use approximation: P(|Z| > t) ≈ 2 * (1 - Φ(t))
            # Using error function approximation
            p_value = 2 * (1 - _normal_cdf(t_stat))
        else:
            # For smaller df, use a rougher approximation
            # This is less accurate but works without scipy
            p_value = 2 * (1 - _normal_cdf(t_stat * math.sqrt(df / (df - 2)) if df > 2 else t_stat))
        
        return max(0.0, min(1.0, p_value))
    
    def _calculate_effect_size(
        self,
        mean_a: float, std_a: float,
        mean_b: float, std_b: float,
    ) -> Optional[float]:
        """Calculate Cohen's d effect size."""
        # Pooled standard deviation
        if std_a <= 0 and std_b <= 0:
            return None
        
        pooled_std = math.sqrt((std_a**2 + std_b**2) / 2)
        
        if pooled_std <= 0:
            return None
        
        cohens_d = (mean_b - mean_a) / pooled_std
        
        return cohens_d
    
    def _determine_metric_winner(
        self,
        delta_percent: float,
        direction: str,
        is_significant: bool,
        effect_size: Optional[float],
    ) -> str:
        """Determine winner for a single metric."""
        # Check if difference is within tie threshold
        if abs(delta_percent) <= self.config.tie_threshold_percent:
            return "TIE"
        
        # Check if effect size is meaningful
        if effect_size is not None and abs(effect_size) < self.config.min_effect_size:
            return "TIE"
        
        # Determine winner based on direction
        if direction == "higher":
            # Higher is better: if B > A (delta > 0), B wins
            return "B" if delta_percent > 0 else "A"
        elif direction == "lower":
            # Lower is better: if B < A (delta < 0), B wins
            return "B" if delta_percent < 0 else "A"
        else:  # neutral
            return "TIE"
    
    def _determine_overall_winner(
        self,
        winner_by_metric: Dict[str, Winner],
        winner_by_risk: Dict[str, Winner],
    ) -> Tuple[Winner, float]:
        """Determine overall winner and confidence."""
        # Count wins for metrics
        metric_a_wins = sum(1 for w in winner_by_metric.values() if w == Winner.A)
        metric_b_wins = sum(1 for w in winner_by_metric.values() if w == Winner.B)
        metric_ties = sum(1 for w in winner_by_metric.values() if w == Winner.TIE)
        total_metrics = len(winner_by_metric)
        
        # Count wins for risks
        risk_a_wins = sum(1 for w in winner_by_risk.values() if w == Winner.A)
        risk_b_wins = sum(1 for w in winner_by_risk.values() if w == Winner.B)
        risk_ties = sum(1 for w in winner_by_risk.values() if w == Winner.TIE)
        total_risks = len(winner_by_risk)
        
        # Calculate weighted scores
        metric_score_a = metric_a_wins / max(total_metrics, 1) if total_metrics > 0 else 0
        metric_score_b = metric_b_wins / max(total_metrics, 1) if total_metrics > 0 else 0
        
        risk_score_a = risk_a_wins / max(total_risks, 1) if total_risks > 0 else 0
        risk_score_b = risk_b_wins / max(total_risks, 1) if total_risks > 0 else 0
        
        # Combined score
        total_score_a = (
            self.config.metric_weight * metric_score_a +
            self.config.risk_weight * risk_score_a
        )
        total_score_b = (
            self.config.metric_weight * metric_score_b +
            self.config.risk_weight * risk_score_b
        )
        
        # Determine winner
        score_diff = total_score_b - total_score_a
        
        if abs(score_diff) < 0.1:  # Very close
            winner = Winner.TIE
            confidence = 0.5
        elif score_diff > 0:
            winner = Winner.B
            confidence = min(0.5 + score_diff, 1.0)
        else:
            winner = Winner.A
            confidence = min(0.5 + abs(score_diff), 1.0)
        
        return winner, confidence
    
    def _generate_summary(
        self,
        name_a: str,
        name_b: str,
        metric_comparisons: Dict[str, MetricComparison],
        risk_comparisons: Dict[str, RiskComparison],
        overall_winner: Winner,
        confidence: float,
    ) -> str:
        """Generate human-readable summary."""
        parts = []
        
        # Overall verdict
        if overall_winner == Winner.A:
            parts.append(f"{name_a} shows better overall performance.")
        elif overall_winner == Winner.B:
            parts.append(f"{name_b} shows better overall performance.")
        else:
            parts.append(f"{name_a} and {name_b} show similar overall performance.")
        
        # Key differences
        top_diffs = []
        
        for mc in metric_comparisons.values():
            if mc.winner != "TIE" and abs(mc.delta_percent) > 10:
                top_diffs.append({
                    "name": mc.metric_name,
                    "winner": mc.winner,
                    "delta_percent": mc.delta_percent,
                    "type": "metric",
                })
        
        for rc in risk_comparisons.values():
            if rc.winner != "TIE" and abs(rc.delta_percent) > 15:
                top_diffs.append({
                    "name": rc.risk_name,
                    "winner": rc.winner,
                    "delta_percent": rc.delta_percent,
                    "type": "risk",
                })
        
        # Sort by impact
        top_diffs.sort(key=lambda x: abs(x["delta_percent"]), reverse=True)
        
        if top_diffs:
            improvements = []
            for diff in top_diffs[:3]:
                winner_name = name_b if diff["winner"] == "B" else name_a
                metric_display = _format_metric_name(diff["name"])
                direction = "lower" if diff["delta_percent"] < 0 else "higher"
                
                if diff["type"] == "risk":
                    improvements.append(
                        f"{winner_name} has {abs(diff['delta_percent']):.0f}% lower {metric_display}"
                    )
                else:
                    improvements.append(
                        f"{winner_name} shows {abs(diff['delta_percent']):.0f}% {direction} {metric_display}"
                    )
            
            parts.append("Key differences: " + "; ".join(improvements) + ".")
        
        # Confidence statement
        if confidence > 0.8:
            parts.append("This conclusion has high confidence based on the data.")
        elif confidence > 0.6:
            parts.append("This conclusion has moderate confidence.")
        else:
            parts.append("More data may be needed for a definitive conclusion.")
        
        return " ".join(parts)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _normal_cdf(x: float) -> float:
    """
    Approximate cumulative distribution function for standard normal.
    Uses the error function approximation.
    """
    # Approximation using math.erf
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _format_metric_name(name: str) -> str:
    """Format metric name for display."""
    # Convert snake_case to Title Case
    words = name.replace("_", " ").replace("pct ", "").split()
    formatted = " ".join(word.capitalize() for word in words)
    
    # Special cases
    replacements = {
        "Auc": "AUC",
        "Mg Dl": "mg/dL",
        "Above 60": ">60%",
        "Above 70": ">70%",
        "Above 140": ">140",
        "Above 180": ">180",
    }
    
    for old, new in replacements.items():
        formatted = formatted.replace(old, new)
    
    return formatted


def _format_value(value: float, metric_name: str) -> str:
    """Format value for display based on metric type."""
    if "percent" in metric_name.lower() or metric_name.startswith("pct_"):
        return f"{value * 100:.1f}%"
    elif "time" in metric_name.lower() or "duration" in metric_name.lower():
        return f"{value:.0f} min"
    elif "glucose" in metric_name.lower():
        return f"{value:.0f} mg/dL"
    elif "alertness" in metric_name.lower():
        return f"{value:.0f}%"
    elif "caffeine" in metric_name.lower():
        return f"{value:.2f} mg/L"
    else:
        return f"{value:.2f}"


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def compare_formulations(
    result_a: Any,
    result_b: Any,
    config: Optional[ComparisonConfig] = None,
) -> Comparison:
    """
    Convenience function to compare two formulations.
    
    Args:
        result_a: First PopulationSimulationResult
        result_b: Second PopulationSimulationResult
        config: Optional ComparisonConfig
        
    Returns:
        Comparison object
    """
    engine = ComparisonEngine(config=config)
    return engine.compare(result_a, result_b)


def format_comparison_for_pdf(comparison: Comparison) -> Dict[str, Any]:
    """
    Convenience function to format comparison for PDF.
    
    Args:
        comparison: Comparison object
        
    Returns:
        Dict ready for PDF generation
    """
    return comparison.format_for_pdf()
