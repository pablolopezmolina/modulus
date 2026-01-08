"""
MODULUS Recommendation Engine
Session 14.1 - FASE 4

Intelligent recommendation system that analyzes simulation results
and generates actionable suggestions to improve formulations.

This module generates four types of recommendations:
1. Ingredient adjustments: "Reduce caffeine 200→150mg"
2. Timing optimization: "Take before 16:00"
3. Addition suggestions: "Add L-Theanine 100mg"
4. Label warnings: "Not for caffeine-sensitive individuals"

Each recommendation includes:
- expected_impact: Dict[metric, Δvalue]
- confidence: float (0-1)
- evidence_summary: str
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class RecommendationType(Enum):
    """Types of recommendations the engine can generate."""
    INGREDIENT_ADJUSTMENT = "ingredient_adjustment"
    TIMING_OPTIMIZATION = "timing_optimization"
    ADDITION_SUGGESTION = "addition_suggestion"
    LABEL_WARNING = "label_warning"
    REMOVAL_SUGGESTION = "removal_suggestion"


# Risk thresholds (percentage of population)
DEFAULT_JITTER_THRESHOLD = 0.15
DEFAULT_SLEEP_THRESHOLD = 0.15
DEFAULT_HYPERGLYCEMIA_THRESHOLD = 0.15
DEFAULT_CRASH_THRESHOLD = 0.15

# Caffeine-specific constants
CAFFEINE_SAFE_DOSE = 200  # mg, generally safe for most people
CAFFEINE_MAX_AFTERNOON = 14 * 60  # 14:00 (2 PM) - latest recommended intake
CAFFEINE_HALF_LIFE_SLOW = 8.0  # hours for slow metabolizers

# L-Theanine recommendation
THEANINE_CAFFEINE_RATIO = 1.0  # 1:1 ratio is common
THEANINE_MIN_DOSE = 100  # mg
THEANINE_MAX_DOSE = 400  # mg

# Evidence confidence levels
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.75
CONFIDENCE_LOW = 0.60


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RecommendationConfig:
    """Configuration for recommendation thresholds."""
    jitter_risk_threshold: float = DEFAULT_JITTER_THRESHOLD
    sleep_risk_threshold: float = DEFAULT_SLEEP_THRESHOLD
    hyperglycemia_threshold: float = DEFAULT_HYPERGLYCEMIA_THRESHOLD
    crash_risk_threshold: float = DEFAULT_CRASH_THRESHOLD
    min_confidence: float = 0.5
    max_recommendations: int = 10


@dataclass
class Recommendation:
    """A single recommendation with expected impact."""
    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    expected_impact: Dict[str, float]  # metric -> delta value
    confidence: float  # 0-1
    evidence_summary: str
    priority: int  # 1=highest, 5=lowest
    
    # Optional fields for specific recommendation types
    target_ingredient: Optional[str] = None
    current_value: Optional[float] = None
    suggested_value: Optional[float] = None
    suggested_timing: Optional[str] = None
    warning_text: Optional[str] = None


@dataclass
class RecommendationReport:
    """Full recommendation analysis report."""
    formulation_name: str
    total_recommendations: int
    recommendations: List[Recommendation]
    overall_improvement_potential: float  # 0-1
    key_issues_identified: List[str]
    
    def get_by_type(self, rec_type: RecommendationType) -> List[Recommendation]:
        """Filter recommendations by type."""
        return [r for r in self.recommendations if r.recommendation_type == rec_type]
    
    def get_high_priority(self, max_priority: int = 2) -> List[Recommendation]:
        """Get high priority recommendations."""
        return [r for r in self.recommendations if r.priority <= max_priority]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "formulation_name": self.formulation_name,
            "total_recommendations": self.total_recommendations,
            "recommendations": [
                {
                    "id": r.recommendation_id,
                    "type": r.recommendation_type.value,
                    "title": r.title,
                    "description": r.description,
                    "expected_impact": r.expected_impact,
                    "confidence": r.confidence,
                    "evidence_summary": r.evidence_summary,
                    "priority": r.priority,
                    "target_ingredient": r.target_ingredient,
                    "current_value": r.current_value,
                    "suggested_value": r.suggested_value,
                    "suggested_timing": r.suggested_timing,
                    "warning_text": r.warning_text,
                }
                for r in self.recommendations
            ],
            "overall_improvement_potential": self.overall_improvement_potential,
            "key_issues_identified": self.key_issues_identified,
        }


# =============================================================================
# RECOMMENDATION ENGINE
# =============================================================================

class RecommendationEngine:
    """
    Analyzes simulation results and generates actionable recommendations.
    
    The engine examines risk analysis results and formulation composition
    to suggest improvements across four categories:
    - Ingredient adjustments (dose changes)
    - Timing optimizations
    - Addition suggestions (synergistic compounds)
    - Label warnings (for at-risk populations)
    
    Example:
        engine = RecommendationEngine()
        report = engine.analyze(simulation_results, formulation)
        print(f"Found {report.total_recommendations} recommendations")
        for rec in report.get_high_priority():
            print(f"- {rec.title}: {rec.description}")
    """
    
    def __init__(self, config: Optional[RecommendationConfig] = None):
        """
        Initialize the recommendation engine.
        
        Args:
            config: Optional configuration for thresholds and limits
        """
        self.config = config or RecommendationConfig()
        self._recommendation_counter = 0
    
    def _generate_id(self) -> str:
        """Generate unique recommendation ID."""
        self._recommendation_counter += 1
        return f"rec_{self._recommendation_counter:04d}"
    
    def analyze(
        self,
        results: Any,  # PopulationSimulationResult or compatible
        formulation: Any,  # Formulation or compatible
    ) -> RecommendationReport:
        """
        Analyze simulation results and generate recommendations.
        
        Args:
            results: Population simulation results with risk_analysis
            formulation: The formulation being analyzed
            
        Returns:
            RecommendationReport with all recommendations
        """
        recommendations: List[Recommendation] = []
        key_issues: List[str] = []
        
        # Extract data from results
        risk_analysis = getattr(results, 'risk_analysis', {}) or {}
        intake_time = getattr(results, 'intake_time_minutes', 420)  # Default 7:00
        
        # Get formulation info
        formulation_name = getattr(formulation, 'name', 'Unknown')
        ingredients = getattr(formulation, 'ingredients', [])
        
        # Get caffeine amount if present
        caffeine_amount = self._get_ingredient_amount(formulation, 'caffeine')
        has_theanine = self._has_ingredient(formulation, 'l_theanine')
        
        # Extract risk percentages
        jitter_risk = risk_analysis.get('pct_jitter_risk', 0.0)
        sleep_risk = risk_analysis.get('pct_sleep_disruption', 0.0)
        hyperglycemia_risk = risk_analysis.get('pct_hyperglycemia', 0.0)
        crash_risk = risk_analysis.get('pct_crash_risk', 0.0)
        
        # =================================================================
        # ANALYSIS 1: Caffeine Dose Adjustments
        # =================================================================
        if caffeine_amount and caffeine_amount > 0:
            if jitter_risk > self.config.jitter_risk_threshold:
                key_issues.append(f"High jitter risk ({jitter_risk:.0%})")
                
                rec = self._recommend_caffeine_reduction(
                    caffeine_amount, jitter_risk
                )
                if rec:
                    recommendations.append(rec)
            
            # Sleep disruption from caffeine
            if sleep_risk > self.config.sleep_risk_threshold:
                key_issues.append(f"High sleep disruption risk ({sleep_risk:.0%})")
        
        # =================================================================
        # ANALYSIS 2: Timing Optimization
        # =================================================================
        if caffeine_amount and sleep_risk > self.config.sleep_risk_threshold:
            if intake_time >= CAFFEINE_MAX_AFTERNOON:
                rec = self._recommend_earlier_timing(intake_time, sleep_risk)
                if rec:
                    recommendations.append(rec)
        
        # =================================================================
        # ANALYSIS 3: Addition Suggestions (L-Theanine)
        # =================================================================
        if caffeine_amount and caffeine_amount > 100 and not has_theanine:
            if jitter_risk > self.config.jitter_risk_threshold * 0.8:  # Slightly lower threshold
                rec = self._recommend_theanine_addition(caffeine_amount, jitter_risk)
                if rec:
                    recommendations.append(rec)
        
        # =================================================================
        # ANALYSIS 4: Label Warnings
        # =================================================================
        # Caffeine sensitivity warning
        if jitter_risk > self.config.jitter_risk_threshold * 1.5:
            rec = self._recommend_caffeine_sensitivity_warning(jitter_risk)
            if rec:
                recommendations.append(rec)
        
        # Sleep timing warning
        if sleep_risk > self.config.sleep_risk_threshold * 1.2:
            rec = self._recommend_sleep_timing_warning(sleep_risk)
            if rec:
                recommendations.append(rec)
        
        # =================================================================
        # ANALYSIS 5: Hyperglycemia Warnings
        # =================================================================
        if hyperglycemia_risk > self.config.hyperglycemia_threshold:
            key_issues.append(f"Elevated hyperglycemia risk ({hyperglycemia_risk:.0%})")
            rec = self._recommend_glucose_warning(hyperglycemia_risk)
            if rec:
                recommendations.append(rec)
        
        # =================================================================
        # ANALYSIS 6: Crash Risk
        # =================================================================
        if crash_risk > self.config.crash_risk_threshold:
            key_issues.append(f"Energy crash risk ({crash_risk:.0%})")
        
        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)
        
        # Limit recommendations
        recommendations = recommendations[:self.config.max_recommendations]
        
        # Calculate improvement potential
        improvement_potential = self._calculate_improvement_potential(
            risk_analysis, recommendations
        )
        
        return RecommendationReport(
            formulation_name=formulation_name,
            total_recommendations=len(recommendations),
            recommendations=recommendations,
            overall_improvement_potential=improvement_potential,
            key_issues_identified=key_issues,
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_ingredient_amount(
        self, formulation: Any, compound_id: str
    ) -> Optional[float]:
        """Get amount of specific ingredient from formulation."""
        if hasattr(formulation, 'get_ingredient_amount'):
            return formulation.get_ingredient_amount(compound_id)
        
        ingredients = getattr(formulation, 'ingredients', [])
        for ing in ingredients:
            if isinstance(ing, dict) and ing.get('compound_id') == compound_id:
                return ing.get('amount')
            elif hasattr(ing, 'compound_id') and ing.compound_id == compound_id:
                return getattr(ing, 'amount', None)
        return None
    
    def _has_ingredient(self, formulation: Any, compound_id: str) -> bool:
        """Check if formulation has specific ingredient."""
        if hasattr(formulation, 'has_ingredient'):
            return formulation.has_ingredient(compound_id)
        return self._get_ingredient_amount(formulation, compound_id) is not None
    
    def _calculate_improvement_potential(
        self,
        risk_analysis: Dict[str, float],
        recommendations: List[Recommendation]
    ) -> float:
        """
        Calculate overall improvement potential (0-1).
        
        Based on:
        - Current risk levels
        - Number and impact of recommendations
        """
        if not recommendations:
            return 0.0
        
        # Sum of excess risks above thresholds
        excess_risk = 0.0
        threshold_map = {
            'pct_jitter_risk': self.config.jitter_risk_threshold,
            'pct_sleep_disruption': self.config.sleep_risk_threshold,
            'pct_hyperglycemia': self.config.hyperglycemia_threshold,
            'pct_crash_risk': self.config.crash_risk_threshold,
        }
        
        for metric, threshold in threshold_map.items():
            current = risk_analysis.get(metric, 0.0)
            if current > threshold:
                excess_risk += (current - threshold)
        
        # Calculate total expected improvement from recommendations
        total_improvement = 0.0
        for rec in recommendations:
            for metric, delta in rec.expected_impact.items():
                if delta < 0:  # Negative delta = improvement
                    total_improvement += abs(delta)
        
        # Normalize to 0-1
        # High excess risk + high improvement potential = high overall potential
        raw_potential = (excess_risk * 0.5) + (total_improvement * 0.5)
        
        # Clamp to [0, 1]
        return min(1.0, max(0.0, raw_potential))
    
    # =========================================================================
    # RECOMMENDATION GENERATORS
    # =========================================================================
    
    def _recommend_caffeine_reduction(
        self, current_dose: float, jitter_risk: float
    ) -> Optional[Recommendation]:
        """Generate caffeine dose reduction recommendation."""
        
        # Calculate suggested dose based on risk level
        if jitter_risk > 0.40:
            # Very high risk - significant reduction
            suggested_dose = min(CAFFEINE_SAFE_DOSE, current_dose * 0.5)
            priority = 1
            confidence = CONFIDENCE_HIGH
        elif jitter_risk > 0.30:
            # High risk - moderate reduction
            suggested_dose = min(CAFFEINE_SAFE_DOSE, current_dose * 0.65)
            priority = 1
            confidence = CONFIDENCE_HIGH
        elif jitter_risk > 0.20:
            # Moderate risk - slight reduction
            suggested_dose = min(CAFFEINE_SAFE_DOSE, current_dose * 0.75)
            priority = 2
            confidence = CONFIDENCE_MEDIUM
        else:
            # Low risk - minimal reduction
            suggested_dose = current_dose * 0.85
            priority = 3
            confidence = CONFIDENCE_MEDIUM
        
        # Round to nice number
        suggested_dose = round(suggested_dose / 25) * 25  # Round to nearest 25mg
        suggested_dose = max(50, suggested_dose)  # Minimum 50mg
        
        if suggested_dose >= current_dose:
            return None  # No meaningful reduction
        
        # Calculate expected impact
        reduction_ratio = (current_dose - suggested_dose) / current_dose
        expected_jitter_reduction = -jitter_risk * reduction_ratio * 0.7  # ~70% effectiveness
        expected_alertness_reduction = -0.05 * reduction_ratio  # Small reduction in effect
        
        return Recommendation(
            recommendation_id=self._generate_id(),
            recommendation_type=RecommendationType.INGREDIENT_ADJUSTMENT,
            title="Reduce caffeine dose",
            description=(
                f"Reduce caffeine from {current_dose:.0f}mg to {suggested_dose:.0f}mg "
                f"to lower jitter risk from {jitter_risk:.0%} to approximately "
                f"{jitter_risk + expected_jitter_reduction:.0%}."
            ),
            expected_impact={
                "pct_jitter_risk": expected_jitter_reduction,
                "alertness_duration": expected_alertness_reduction,
            },
            confidence=confidence,
            evidence_summary=(
                "Caffeine dose-response relationship is well-established. "
                "Doses above 200mg increase jitter risk significantly in "
                "sensitive individuals (Nawrot et al., 2003)."
            ),
            priority=priority,
            target_ingredient="caffeine",
            current_value=current_dose,
            suggested_value=suggested_dose,
        )
    
    def _recommend_earlier_timing(
        self, current_time: float, sleep_risk: float
    ) -> Optional[Recommendation]:
        """Generate timing optimization recommendation."""
        
        # Convert to hours for readability
        current_hour = current_time / 60
        
        # Suggest taking before 2 PM (14:00)
        suggested_hour = min(14.0, current_hour - 2)
        suggested_time = max(6 * 60, suggested_hour * 60)  # Not before 6 AM
        
        # Format times for display
        current_time_str = f"{int(current_time // 60):02d}:{int(current_time % 60):02d}"
        suggested_time_str = f"{int(suggested_time // 60):02d}:{int(suggested_time % 60):02d}"
        
        # Calculate expected impact
        time_improvement = (current_time - suggested_time) / 60  # hours earlier
        expected_sleep_improvement = -sleep_risk * min(1.0, time_improvement / 4) * 0.6
        
        priority = 2 if sleep_risk > 0.25 else 3
        
        return Recommendation(
            recommendation_id=self._generate_id(),
            recommendation_type=RecommendationType.TIMING_OPTIMIZATION,
            title="Take earlier in the day",
            description=(
                f"Recommend taking before {suggested_time_str} instead of {current_time_str}. "
                f"Caffeine's ~5-hour half-life means late intake affects sleep quality. "
                f"This could reduce sleep disruption risk by approximately "
                f"{abs(expected_sleep_improvement):.0%}."
            ),
            expected_impact={
                "pct_sleep_disruption": expected_sleep_improvement,
            },
            confidence=CONFIDENCE_HIGH,
            evidence_summary=(
                "Caffeine has a half-life of 4-6 hours in normal metabolizers. "
                "Intake after 14:00 is associated with increased sleep latency "
                "and reduced sleep quality (Drake et al., 2013)."
            ),
            priority=priority,
            suggested_timing=suggested_time_str,
        )
    
    def _recommend_theanine_addition(
        self, caffeine_amount: float, jitter_risk: float
    ) -> Optional[Recommendation]:
        """Generate L-Theanine addition recommendation."""
        
        # Calculate suggested dose (1:1 to 2:1 ratio with caffeine)
        suggested_dose = min(
            THEANINE_MAX_DOSE,
            max(THEANINE_MIN_DOSE, caffeine_amount * THEANINE_CAFFEINE_RATIO)
        )
        
        # Round to nice number
        suggested_dose = round(suggested_dose / 50) * 50
        
        # Expected impact
        expected_jitter_reduction = -jitter_risk * 0.5  # L-theanine reduces jitter by ~50%
        
        priority = 2 if jitter_risk > 0.20 else 3
        
        return Recommendation(
            recommendation_id=self._generate_id(),
            recommendation_type=RecommendationType.ADDITION_SUGGESTION,
            title="Add L-Theanine for smoother energy",
            description=(
                f"Add L-Theanine {suggested_dose:.0f}mg to smooth out caffeine's "
                f"stimulant effect. L-Theanine promotes alpha brain waves and "
                f"reduces caffeine-induced jitters while maintaining alertness."
            ),
            expected_impact={
                "pct_jitter_risk": expected_jitter_reduction,
            },
            confidence=CONFIDENCE_HIGH,
            evidence_summary=(
                "L-Theanine + caffeine synergy is well-documented. "
                "The combination improves attention and reduces anxiety "
                "compared to caffeine alone (Haskell et al., 2008; "
                "Owen et al., 2008)."
            ),
            priority=priority,
            target_ingredient="l_theanine",
            suggested_value=suggested_dose,
        )
    
    def _recommend_caffeine_sensitivity_warning(
        self, jitter_risk: float
    ) -> Optional[Recommendation]:
        """Generate caffeine sensitivity label warning."""
        
        priority = 1 if jitter_risk > 0.35 else 2
        
        warning_text = (
            "Not recommended for individuals sensitive to caffeine. "
            "Consult a healthcare professional before use if you have "
            "any medical conditions or are taking medications."
        )
        
        return Recommendation(
            recommendation_id=self._generate_id(),
            recommendation_type=RecommendationType.LABEL_WARNING,
            title="Add caffeine sensitivity warning",
            description=(
                f"With {jitter_risk:.0%} of the population showing jitter risk, "
                f"a warning label is recommended to inform caffeine-sensitive "
                f"individuals. This is standard practice for products with "
                f"significant stimulant content."
            ),
            expected_impact={
                "pct_adverse_reports": -0.10,  # Expected reduction in complaints
            },
            confidence=CONFIDENCE_HIGH,
            evidence_summary=(
                "Approximately 10-15% of the population are slow caffeine "
                "metabolizers (CYP1A2 polymorphism). Warning labels reduce "
                "adverse event reports and improve customer satisfaction."
            ),
            priority=priority,
            warning_text=warning_text,
        )
    
    def _recommend_sleep_timing_warning(
        self, sleep_risk: float
    ) -> Optional[Recommendation]:
        """Generate sleep timing label warning."""
        
        priority = 2 if sleep_risk > 0.30 else 3
        
        warning_text = (
            "Do not consume within 6 hours of bedtime. "
            "May cause difficulty falling asleep or staying asleep."
        )
        
        return Recommendation(
            recommendation_id=self._generate_id(),
            recommendation_type=RecommendationType.LABEL_WARNING,
            title="Add timing warning for sleep",
            description=(
                f"With {sleep_risk:.0%} sleep disruption risk, adding a timing "
                f"warning helps consumers avoid evening/nighttime use. "
                f"This is particularly important for slow caffeine metabolizers."
            ),
            expected_impact={
                "pct_sleep_disruption": -0.05,  # Reduction through awareness
            },
            confidence=CONFIDENCE_MEDIUM,
            evidence_summary=(
                "Consumer education on caffeine timing reduces self-reported "
                "sleep issues. Warning labels are required in several "
                "jurisdictions for caffeinated products."
            ),
            priority=priority,
            warning_text=warning_text,
        )
    
    def _recommend_glucose_warning(
        self, hyperglycemia_risk: float
    ) -> Optional[Recommendation]:
        """Generate glucose/diabetes warning."""
        
        priority = 2 if hyperglycemia_risk > 0.20 else 3
        
        warning_text = (
            "Contains carbohydrates that may affect blood sugar levels. "
            "Not recommended for individuals with diabetes without "
            "consulting a healthcare professional."
        )
        
        return Recommendation(
            recommendation_id=self._generate_id(),
            recommendation_type=RecommendationType.LABEL_WARNING,
            title="Add glucose warning for diabetics",
            description=(
                f"With {hyperglycemia_risk:.0%} showing elevated glucose response, "
                f"a warning for diabetic/pre-diabetic consumers is recommended. "
                f"This is standard practice for products containing carbohydrates."
            ),
            expected_impact={
                "pct_adverse_reports": -0.05,
            },
            confidence=CONFIDENCE_HIGH,
            evidence_summary=(
                "Carbohydrate-containing supplements can cause significant "
                "glucose excursions in insulin-resistant individuals. "
                "Proper labeling helps at-risk consumers make informed choices."
            ),
            priority=priority,
            warning_text=warning_text,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_recommendations(
    results: Any,
    formulation: Any,
    config: Optional[RecommendationConfig] = None,
) -> RecommendationReport:
    """
    Convenience function to generate recommendations.
    
    Args:
        results: Population simulation results
        formulation: The formulation being analyzed
        config: Optional configuration
        
    Returns:
        RecommendationReport with all recommendations
    """
    engine = RecommendationEngine(config=config)
    return engine.analyze(results, formulation)


def format_recommendations_text(report: RecommendationReport) -> str:
    """
    Format recommendations as human-readable text.
    
    Args:
        report: RecommendationReport to format
        
    Returns:
        Formatted text string
    """
    lines = [
        f"RECOMMENDATIONS FOR: {report.formulation_name}",
        "=" * 60,
        "",
        f"Total recommendations: {report.total_recommendations}",
        f"Improvement potential: {report.overall_improvement_potential:.0%}",
        "",
    ]
    
    if report.key_issues_identified:
        lines.append("KEY ISSUES IDENTIFIED:")
        for issue in report.key_issues_identified:
            lines.append(f"  • {issue}")
        lines.append("")
    
    if report.recommendations:
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 40)
        
        for rec in report.recommendations:
            lines.extend([
                f"",
                f"[Priority {rec.priority}] {rec.title}",
                f"Type: {rec.recommendation_type.value}",
                f"Description: {rec.description}",
                f"Confidence: {rec.confidence:.0%}",
                f"Evidence: {rec.evidence_summary}",
            ])
            
            if rec.expected_impact:
                impacts = ", ".join(
                    f"{k}: {v:+.0%}" for k, v in rec.expected_impact.items()
                )
                lines.append(f"Expected impact: {impacts}")
            
            if rec.warning_text:
                lines.append(f"Suggested warning: \"{rec.warning_text}\"")
    else:
        lines.append("No recommendations - formulation looks good!")
    
    return "\n".join(lines)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "RecommendationType",
    "Recommendation",
    "RecommendationReport",
    "RecommendationConfig",
    "RecommendationEngine",
    "generate_recommendations",
    "format_recommendations_text",
]
