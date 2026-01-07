"""
Claim Defensibility Analysis - Session 6.2

Analyzes whether marketing claims are defensible based on population
simulation results. Provides responder percentages, confidence levels,
and suggested wording for claims.

Part of MODULUS Pack 1 (€50k) - Protocol Assessment.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import math


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class ClaimDefinition:
    """
    Definition of a marketing claim and how to evaluate it.
    
    Immutable - represents a static claim definition.
    """
    claim_id: str
    claim_text: str
    description: str
    evaluation_method: str  # Which metric/calculation to use
    threshold: float        # Value that defines "responder"
    threshold_comparator: str  # ">=", "<=", ">", "<", "=="
    required_responder_rate: float  # Minimum % of responders needed (0-1)
    
    # Optional fields
    conservative_wording: str = ""
    aggressive_wording: str = ""
    
    def __post_init__(self):
        """Validate fields."""
        if not (0.0 <= self.required_responder_rate <= 1.0):
            raise ValueError(
                f"required_responder_rate must be in [0, 1], got {self.required_responder_rate}"
            )
        valid_comparators = {">=", "<=", ">", "<", "=="}
        if self.threshold_comparator not in valid_comparators:
            raise ValueError(
                f"threshold_comparator must be one of {valid_comparators}, "
                f"got '{self.threshold_comparator}'"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "description": self.description,
            "evaluation_method": self.evaluation_method,
            "threshold": self.threshold,
            "threshold_comparator": self.threshold_comparator,
            "required_responder_rate": self.required_responder_rate,
            "conservative_wording": self.conservative_wording,
            "aggressive_wording": self.aggressive_wording,
        }


@dataclass(frozen=True)
class ClaimAnalysis:
    """
    Result of analyzing a single claim.
    
    Contract 6.1 compliant.
    """
    claim_id: str
    claim_text: str
    
    # Core result
    responder_percentage: float  # 0-1, fraction of population that meets criteria
    is_defensible: bool          # True if responder_percentage > threshold AND confidence > min
    confidence: float            # 0-1, how confident we are in the result
    
    # Evidence
    supporting_metrics: Dict[str, float]  # Metrics used in evaluation
    methodology: str                       # How the claim was evaluated
    
    # Output
    suggested_wording: str  # Suggested marketing text
    
    # Regulatory (conservative - all False for now)
    efsa_compatible: bool = False
    fda_compatible: bool = False
    
    def __post_init__(self):
        """Validate fields."""
        if not (0.0 <= self.responder_percentage <= 1.0):
            raise ValueError(
                f"responder_percentage must be in [0, 1], got {self.responder_percentage}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "responder_percentage": self.responder_percentage,
            "is_defensible": self.is_defensible,
            "confidence": self.confidence,
            "supporting_metrics": self.supporting_metrics,
            "methodology": self.methodology,
            "suggested_wording": self.suggested_wording,
            "efsa_compatible": self.efsa_compatible,
            "fda_compatible": self.fda_compatible,
        }


@dataclass(frozen=True)
class ClaimAnalyzerConfig:
    """Configuration for ClaimAnalyzer."""
    min_responder_rate: float = 0.5     # Minimum responder rate for defensibility
    min_confidence: float = 0.7          # Minimum confidence for defensibility
    conservative_wording: bool = True    # Use conservative wording
    
    def __post_init__(self):
        """Validate fields."""
        if not (0.0 <= self.min_responder_rate <= 1.0):
            raise ValueError(
                f"min_responder_rate must be in [0, 1], got {self.min_responder_rate}"
            )
        if not (0.0 <= self.min_confidence <= 1.0):
            raise ValueError(
                f"min_confidence must be in [0, 1], got {self.min_confidence}"
            )


@dataclass
class ClaimAnalysisResult:
    """
    Complete result of analyzing multiple claims.
    """
    analyses: Dict[str, ClaimAnalysis]  # claim_id -> analysis
    n_defensible: int                    # Count of defensible claims
    n_total: int                         # Total claims analyzed
    warnings: List[str] = field(default_factory=list)
    
    def get_defensible_claims(self) -> Dict[str, ClaimAnalysis]:
        """Get only defensible claims."""
        return {
            claim_id: analysis
            for claim_id, analysis in self.analyses.items()
            if analysis.is_defensible
        }
    
    def get_non_defensible_claims(self) -> Dict[str, ClaimAnalysis]:
        """Get only non-defensible claims."""
        return {
            claim_id: analysis
            for claim_id, analysis in self.analyses.items()
            if not analysis.is_defensible
        }
    
    def get_summary(self) -> str:
        """Get a text summary of the analysis."""
        defensible_ids = [c.claim_text for c in self.get_defensible_claims().values()]
        non_defensible_ids = [c.claim_text for c in self.get_non_defensible_claims().values()]
        
        lines = [
            f"Claim Analysis Summary: {self.n_defensible}/{self.n_total} claims are defensible."
        ]
        
        if defensible_ids:
            lines.append(f"Defensible: {', '.join(defensible_ids)}")
        if non_defensible_ids:
            lines.append(f"Not defensible: {', '.join(non_defensible_ids)}")
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
        
        return " ".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "analyses": {
                claim_id: analysis.to_dict()
                for claim_id, analysis in self.analyses.items()
            },
            "n_defensible": self.n_defensible,
            "n_total": self.n_total,
            "warnings": self.warnings,
        }


# =============================================================================
# DEFAULT CLAIM DEFINITIONS
# =============================================================================

def get_default_claims() -> Dict[str, ClaimDefinition]:
    """
    Get default claim definitions.
    
    Claims based on ROADMAP specification:
    - sustained_energy: alertness >60% for >4h
    - no_crash: <10% experimenta drop >30%
    - quick_onset: peak alertness <45min
    - glucose_friendly: <15% hyperglycemia
    """
    return {
        "sustained_energy": ClaimDefinition(
            claim_id="sustained_energy",
            claim_text="Sustained Energy",
            description="Provides energy that lasts for at least 4 hours",
            evaluation_method="alertness_duration_above_60",
            threshold=240.0,  # 4 hours = 240 minutes
            threshold_comparator=">=",
            required_responder_rate=0.5,
            conservative_wording="Provides sustained energy for most users",
            aggressive_wording="Long-lasting energy boost",
        ),
        "no_crash": ClaimDefinition(
            claim_id="no_crash",
            claim_text="No Crash",
            description="Avoids the typical energy crash associated with stimulants",
            evaluation_method="pct_crash_risk",
            threshold=10.0,  # <10% crash risk
            threshold_comparator="<=",
            required_responder_rate=0.5,
            conservative_wording="Most users experience smooth energy without crash",
            aggressive_wording="Crash-free energy",
        ),
        "quick_onset": ClaimDefinition(
            claim_id="quick_onset",
            claim_text="Quick Onset",
            description="Effects are felt quickly after consumption",
            evaluation_method="alertness_time_to_peak",
            threshold=45.0,  # ≤45 minutes to peak
            threshold_comparator="<=",
            required_responder_rate=0.5,
            conservative_wording="Most users feel effects within 45 minutes",
            aggressive_wording="Fast-acting formula",
        ),
        "glucose_friendly": ClaimDefinition(
            claim_id="glucose_friendly",
            claim_text="Glucose Friendly",
            description="Minimal impact on blood glucose levels",
            evaluation_method="pct_hyperglycemia",
            threshold=15.0,  # <15% hyperglycemia
            threshold_comparator="<=",
            required_responder_rate=0.5,
            conservative_wording="Suitable for most people concerned about blood sugar",
            aggressive_wording="Blood sugar friendly",
        ),
    }


# =============================================================================
# CLAIM ANALYZER
# =============================================================================

class ClaimAnalyzer:
    """
    Analyzes whether marketing claims are defensible based on population
    simulation results.
    
    Contract 6.1 compliant.
    
    Usage:
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(population_result)
        
        for claim_id, analysis in result.analyses.items():
            print(f"{analysis.claim_text}: {analysis.is_defensible}")
            if analysis.is_defensible:
                print(f"  Suggested: {analysis.suggested_wording}")
    """
    
    def __init__(
        self,
        config: Optional[ClaimAnalyzerConfig] = None,
        claims: Optional[Dict[str, ClaimDefinition]] = None,
    ):
        """
        Initialize ClaimAnalyzer.
        
        Args:
            config: Configuration for analysis. Uses defaults if None.
            claims: Custom claim definitions. Uses defaults if None.
        """
        self.config = config or ClaimAnalyzerConfig()
        self.claims = claims if claims is not None else get_default_claims()
    
    def analyze(
        self,
        population_result: Any,  # PopulationDayResult or similar
        claims: Optional[List[str]] = None,
    ) -> ClaimAnalysisResult:
        """
        Analyze claims based on population simulation results.
        
        Args:
            population_result: Result from PopulationDaySimulator.
            claims: List of claim_ids to analyze. If None or empty, analyzes all.
        
        Returns:
            ClaimAnalysisResult with analysis for each claim.
        """
        warnings: List[str] = []
        analyses: Dict[str, ClaimAnalysis] = {}
        
        # Check if result is valid
        if hasattr(population_result, "is_valid") and not population_result.is_valid:
            warnings.append("Population simulation result is invalid")
        
        # Determine which claims to analyze
        claim_ids = claims if claims else list(self.claims.keys())
        if not claim_ids:
            claim_ids = list(self.claims.keys())
        
        # Analyze each claim
        for claim_id in claim_ids:
            if claim_id not in self.claims:
                warnings.append(f"Unknown claim: {claim_id}")
                continue
            
            claim_def = self.claims[claim_id]
            analysis = self._analyze_claim(claim_def, population_result, warnings)
            analyses[claim_id] = analysis
        
        # Count defensible
        n_defensible = sum(1 for a in analyses.values() if a.is_defensible)
        
        return ClaimAnalysisResult(
            analyses=analyses,
            n_defensible=n_defensible,
            n_total=len(analyses),
            warnings=warnings,
        )
    
    def _analyze_claim(
        self,
        claim_def: ClaimDefinition,
        result: Any,
        warnings: List[str],
    ) -> ClaimAnalysis:
        """
        Analyze a single claim.
        
        Args:
            claim_def: The claim definition.
            result: Population simulation result.
            warnings: List to append warnings to.
        
        Returns:
            ClaimAnalysis for this claim.
        """
        # Get the metric value
        metric_value, supporting_metrics, methodology = self._evaluate_claim(
            claim_def, result, warnings
        )
        
        # Calculate responder percentage based on evaluation method
        responder_percentage = self._calculate_responder_percentage(
            claim_def, metric_value, result, warnings
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            claim_def, responder_percentage, metric_value, result
        )
        
        # Determine defensibility (Contract 6.1 rule)
        is_defensible = (
            responder_percentage > self.config.min_responder_rate
            and confidence > self.config.min_confidence
        )
        
        # Generate suggested wording
        suggested_wording = self._generate_wording(
            claim_def, is_defensible, responder_percentage, confidence
        )
        
        return ClaimAnalysis(
            claim_id=claim_def.claim_id,
            claim_text=claim_def.claim_text,
            responder_percentage=responder_percentage,
            is_defensible=is_defensible,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
            methodology=methodology,
            suggested_wording=suggested_wording,
            efsa_compatible=False,  # Conservative default
            fda_compatible=False,   # Conservative default
        )
    
    def _evaluate_claim(
        self,
        claim_def: ClaimDefinition,
        result: Any,
        warnings: List[str],
    ) -> tuple:
        """
        Evaluate a claim and extract the relevant metric.
        
        Returns:
            (metric_value, supporting_metrics, methodology)
        """
        method = claim_def.evaluation_method
        supporting_metrics: Dict[str, float] = {}
        methodology = ""
        metric_value = None
        
        # Get metrics_stats if available
        metrics_stats = getattr(result, "metrics_stats", {})
        risk_analysis = getattr(result, "risk_analysis", {})
        
        # Handle different evaluation methods
        if method == "alertness_duration_above_60":
            # sustained_energy: alertness >60% for >4h
            if "alertness_duration_above_60" in metrics_stats:
                stats = metrics_stats["alertness_duration_above_60"]
                metric_value = stats.get("mean", 0.0)
                supporting_metrics["alertness_duration_above_60_mean"] = metric_value
                supporting_metrics["alertness_duration_above_60_p10"] = stats.get("p10", 0.0)
                methodology = (
                    f"Measured duration (minutes) where alertness score >60% across "
                    f"population. Mean: {metric_value:.1f} min. Target: ≥{claim_def.threshold:.0f} min."
                )
            else:
                warnings.append(f"Missing metric: alertness_duration_above_60")
                metric_value = 0.0
                methodology = "Metric not available in simulation results."
        
        elif method == "pct_crash_risk":
            # no_crash: <10% crash risk
            if "pct_crash_risk" in risk_analysis:
                metric_value = risk_analysis["pct_crash_risk"]
                supporting_metrics["pct_crash_risk"] = metric_value
                methodology = (
                    f"Measured percentage of population experiencing alertness crash "
                    f"(>30% drop in 2h). Result: {metric_value:.1f}%. Target: ≤{claim_def.threshold:.0f}%."
                )
            else:
                warnings.append(f"Missing metric: pct_crash_risk")
                metric_value = 100.0  # Assume worst case
                methodology = "Metric not available in simulation results."
        
        elif method == "alertness_time_to_peak":
            # quick_onset: <45min to peak
            if "alertness_time_to_peak" in metrics_stats:
                stats = metrics_stats["alertness_time_to_peak"]
                metric_value = stats.get("mean", 999.0)
                supporting_metrics["alertness_time_to_peak_mean"] = metric_value
                supporting_metrics["alertness_time_to_peak_p90"] = stats.get("p90", 999.0)
                methodology = (
                    f"Measured time to peak alertness across population. "
                    f"Mean: {metric_value:.1f} min. Target: ≤{claim_def.threshold:.0f} min."
                )
            else:
                warnings.append(f"Missing metric: alertness_time_to_peak")
                metric_value = 999.0  # Assume worst case
                methodology = "Metric not available in simulation results."
        
        elif method == "pct_hyperglycemia":
            # glucose_friendly: <15% hyperglycemia
            if "pct_hyperglycemia" in risk_analysis:
                metric_value = risk_analysis["pct_hyperglycemia"]
                supporting_metrics["pct_hyperglycemia"] = metric_value
                methodology = (
                    f"Measured percentage of population experiencing hyperglycemia "
                    f"(glucose >140 mg/dL). Result: {metric_value:.1f}%. Target: ≤{claim_def.threshold:.0f}%."
                )
            else:
                warnings.append(f"Missing metric: pct_hyperglycemia")
                metric_value = 100.0  # Assume worst case
                methodology = "Metric not available in simulation results."
        
        else:
            # Unknown method - try to find in metrics_stats or risk_analysis
            if method in metrics_stats:
                stats = metrics_stats[method]
                metric_value = stats.get("mean", 0.0) if isinstance(stats, dict) else stats
                supporting_metrics[method] = metric_value
                methodology = f"Evaluated using {method}. Value: {metric_value}."
            elif method in risk_analysis:
                metric_value = risk_analysis[method]
                supporting_metrics[method] = metric_value
                methodology = f"Evaluated using {method}. Value: {metric_value}."
            else:
                warnings.append(f"Unknown evaluation method: {method}")
                metric_value = 0.0
                methodology = f"Unknown evaluation method: {method}."
        
        return metric_value, supporting_metrics, methodology
    
    def _calculate_responder_percentage(
        self,
        claim_def: ClaimDefinition,
        metric_value: float,
        result: Any,
        warnings: List[str],
    ) -> float:
        """
        Calculate the percentage of responders based on the claim criteria.
        
        For percentage-based risk metrics (pct_*):
        - These represent population-level risk percentages
        - For "no_crash" claim with threshold <=10%: if crash_risk=25%, claim FAILS
        - The responder_percentage reflects how well the population criterion is met
        - If metric exceeds threshold, responder_pct scales down based on excess
        
        For individual metrics (duration, time_to_peak):
        - We estimate what fraction of individuals meet the criterion
        """
        method = claim_def.evaluation_method
        threshold = claim_def.threshold
        comparator = claim_def.threshold_comparator
        
        # For percentage-based metrics (risks) - these are POPULATION metrics
        if method.startswith("pct_"):
            # The metric tells us what % of population has the risk/outcome
            # For claims like "no_crash" (threshold <=10%):
            # - If risk=5%, we're well under threshold → high responder %
            # - If risk=10%, we're at threshold → responder % = 50%
            # - If risk=25%, we exceed threshold → low responder %
            
            if comparator == "<=":
                if metric_value <= threshold:
                    # Claim criterion met - scale responder % based on margin
                    # At 0% risk → 100% responder
                    # At threshold → 50% responder (borderline)
                    if threshold > 0:
                        margin = (threshold - metric_value) / threshold
                        responder_pct = 0.5 + 0.5 * margin
                    else:
                        responder_pct = 1.0 if metric_value == 0 else 0.0
                else:
                    # Claim criterion NOT met - scale down based on excess
                    # At threshold → 50% responder
                    # At 100% risk → 0% responder
                    excess = metric_value - threshold
                    max_excess = 100.0 - threshold
                    if max_excess > 0:
                        excess_ratio = excess / max_excess
                        responder_pct = 0.5 * (1.0 - excess_ratio)
                    else:
                        responder_pct = 0.0
            elif comparator == ">=":
                if metric_value >= threshold:
                    # Claim met
                    margin = (metric_value - threshold) / (100.0 - threshold) if threshold < 100 else 1.0
                    responder_pct = 0.5 + 0.5 * margin
                else:
                    # Claim not met
                    shortfall_ratio = (threshold - metric_value) / threshold if threshold > 0 else 1.0
                    responder_pct = 0.5 * (1.0 - shortfall_ratio)
            else:
                # Simple comparison
                if self._compare(metric_value, threshold, comparator):
                    responder_pct = 0.75
                else:
                    responder_pct = 0.25
            
            return max(0.0, min(1.0, responder_pct))
        
        # For duration/time metrics, estimate from distribution
        metrics_stats = getattr(result, "metrics_stats", {})
        
        if method in metrics_stats:
            stats = metrics_stats[method]
            mean = stats.get("mean", metric_value)
            std = stats.get("std", mean * 0.2)  # Assume 20% CV if not available
            p10 = stats.get("p10", mean - 1.28 * std)
            p90 = stats.get("p90", mean + 1.28 * std)
            
            # Estimate responder percentage using normal approximation
            if std > 0:
                if comparator == ">=":
                    # What fraction is >= threshold?
                    z = (threshold - mean) / std
                    responder_pct = 1.0 - self._normal_cdf(z)
                elif comparator == "<=":
                    # What fraction is <= threshold?
                    z = (threshold - mean) / std
                    responder_pct = self._normal_cdf(z)
                elif comparator == ">":
                    z = (threshold - mean) / std
                    responder_pct = 1.0 - self._normal_cdf(z)
                elif comparator == "<":
                    z = (threshold - mean) / std
                    responder_pct = self._normal_cdf(z)
                else:
                    # For "==" use narrow band
                    responder_pct = 0.5 if abs(mean - threshold) < std * 0.5 else 0.2
            else:
                # No variance - all same value
                if self._compare(mean, threshold, comparator):
                    responder_pct = 1.0
                else:
                    responder_pct = 0.0
        else:
            # No distribution info - use binary (meets threshold or not)
            if self._compare(metric_value, threshold, comparator):
                responder_pct = 0.7  # Assume 70% if mean passes
            else:
                responder_pct = 0.3  # Assume 30% if mean fails
        
        return max(0.0, min(1.0, responder_pct))
    
    def _calculate_confidence(
        self,
        claim_def: ClaimDefinition,
        responder_pct: float,
        metric_value: float,
        result: Any,
    ) -> float:
        """
        Calculate confidence in the analysis.
        
        Confidence is based on:
        - How far the responder percentage is from the threshold
        - Sample size (n_valid)
        - Data availability
        """
        # Base confidence from responder rate distance to threshold
        threshold = claim_def.required_responder_rate
        distance = abs(responder_pct - threshold)
        
        # Higher confidence when clearly above or below threshold
        if distance > 0.3:
            confidence = 0.95
        elif distance > 0.2:
            confidence = 0.85
        elif distance > 0.1:
            confidence = 0.75
        elif distance > 0.05:
            confidence = 0.65
        else:
            # Very close to threshold - lower confidence
            confidence = 0.55
        
        # Adjust for sample size
        n_valid = getattr(result, "n_valid", 100)
        if n_valid >= 1000:
            confidence *= 1.0
        elif n_valid >= 500:
            confidence *= 0.95
        elif n_valid >= 100:
            confidence *= 0.9
        else:
            confidence *= 0.8
        
        # Adjust if data was missing
        if metric_value == 0.0 or metric_value == 100.0 or metric_value == 999.0:
            # Likely default/missing value
            confidence *= 0.5
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_wording(
        self,
        claim_def: ClaimDefinition,
        is_defensible: bool,
        responder_pct: float,
        confidence: float,
    ) -> str:
        """Generate suggested marketing wording."""
        if is_defensible:
            if self.config.conservative_wording:
                if claim_def.conservative_wording:
                    return claim_def.conservative_wording
                # Generate conservative wording
                return self._generate_conservative_wording(claim_def, responder_pct)
            else:
                if claim_def.aggressive_wording:
                    return claim_def.aggressive_wording
                return claim_def.claim_text
        else:
            # Not defensible - suggest cautious wording or disclaimer
            return self._generate_cautious_wording(claim_def, responder_pct)
    
    def _generate_conservative_wording(
        self,
        claim_def: ClaimDefinition,
        responder_pct: float,
    ) -> str:
        """Generate conservative wording for defensible claim."""
        pct_str = f"{responder_pct * 100:.0f}%"
        
        if responder_pct >= 0.9:
            qualifier = "most"
        elif responder_pct >= 0.7:
            qualifier = "many"
        else:
            qualifier = "some"
        
        templates = {
            "sustained_energy": f"Provides sustained energy for {qualifier} users",
            "no_crash": f"Smooth energy experience for {qualifier} users",
            "quick_onset": f"Fast-acting for {qualifier} users",
            "glucose_friendly": f"Suitable for {qualifier} people monitoring blood sugar",
        }
        
        return templates.get(
            claim_def.claim_id,
            f"{claim_def.claim_text} for {qualifier} users"
        )
    
    def _generate_cautious_wording(
        self,
        claim_def: ClaimDefinition,
        responder_pct: float,
    ) -> str:
        """Generate cautious wording for non-defensible claim."""
        templates = {
            "sustained_energy": "Energy duration may vary by individual",
            "no_crash": "Some users may experience energy fluctuations",
            "quick_onset": "Onset time varies by individual",
            "glucose_friendly": "May affect blood glucose; not recommended for diabetics without medical advice",
        }
        
        return templates.get(
            claim_def.claim_id,
            f"{claim_def.claim_text} - results may vary"
        )
    
    @staticmethod
    def _compare(value: float, threshold: float, comparator: str) -> bool:
        """Compare value to threshold using comparator."""
        if comparator == ">=":
            return value >= threshold
        elif comparator == "<=":
            return value <= threshold
        elif comparator == ">":
            return value > threshold
        elif comparator == "<":
            return value < threshold
        elif comparator == "==":
            return abs(value - threshold) < 0.001
        return False
    
    @staticmethod
    def _normal_cdf(z: float) -> float:
        """
        Standard normal cumulative distribution function.
        
        Uses error function approximation.
        """
        # Clip to avoid overflow
        z = max(-10, min(10, z))
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "ClaimDefinition",
    "ClaimAnalysis",
    "ClaimAnalyzerConfig",
    "ClaimAnalysisResult",
    "ClaimAnalyzer",
    "get_default_claims",
]
