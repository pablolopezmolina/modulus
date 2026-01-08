# src/analysis/optimizer.py
"""
FormulationOptimizer - MODULUS Session 14.2

Grid search optimizer for finding improved formulation variants.
Supports multiple objectives: MAX_EFFICACY, MIN_RISK, BALANCED.

Usage:
    from analysis.optimizer import FormulationOptimizer, optimize_formulation
    
    # Full control
    optimizer = FormulationOptimizer()
    report = optimizer.optimize(
        base_formula,
        OptimizationObjective.BALANCED,
        OptimizationConstraints(max_caffeine_mg=200)
    )
    
    # Quick optimization
    report = optimize_formulation(formula, objective="balanced", max_caffeine_mg=200)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import itertools
import copy


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class OptimizationObjective(Enum):
    """Optimization objectives"""
    MAX_EFFICACY = "max_efficacy"
    MIN_RISK = "min_risk"
    BALANCED = "balanced"


# Weight configurations for different objectives
OBJECTIVE_WEIGHTS = {
    OptimizationObjective.MAX_EFFICACY: {"efficacy": 0.8, "risk": 0.2},
    OptimizationObjective.MIN_RISK: {"efficacy": 0.2, "risk": 0.8},
    OptimizationObjective.BALANCED: {"efficacy": 0.5, "risk": 0.5},
}

# Known synergies and improvements (from research)
KNOWN_IMPROVEMENTS = {
    "caffeine_theanine_ratio": {
        "description": "L-Theanine at 1:1 to 2:1 ratio with caffeine reduces jitter",
        "applies_when": lambda f: _has_caffeine_without_adequate_theanine(f),
        "suggestion": "add_theanine",
    },
    "high_caffeine": {
        "description": "Caffeine >300mg increases jitter risk significantly",
        "applies_when": lambda f: _get_caffeine_amount(f) > 300,
        "suggestion": "reduce_caffeine",
    },
}

# Default dose adjustment steps (multipliers)
DEFAULT_DOSE_STEPS = [0.5, 0.75, 1.0, 1.25, 1.5]

# Ingredients that can be added for optimization
ADDABLE_INGREDIENTS = {
    "l_theanine": {"default_dose": 100, "unit": "mg", "synergy_with": ["caffeine"]},
    "taurine": {"default_dose": 1000, "unit": "mg", "synergy_with": ["caffeine"]},
}

# Stimulant compound IDs for total stimulant calculation
STIMULANT_COMPOUNDS = {"caffeine", "synephrine", "yohimbine", "tyramine"}


# =============================================================================
# HELPER FUNCTIONS (Module-level)
# =============================================================================

def _has_caffeine_without_adequate_theanine(formulation) -> bool:
    """Check if formula has caffeine but inadequate theanine."""
    caffeine = _get_amount(formulation, "caffeine")
    theanine = _get_amount(formulation, "l_theanine")
    
    if caffeine == 0:
        return False
    if theanine == 0:
        return True
    
    # Theanine should be at least 50% of caffeine dose
    return theanine < caffeine * 0.5


def _get_caffeine_amount(formulation) -> float:
    """Get caffeine amount from formulation."""
    return _get_amount(formulation, "caffeine")


def _get_amount(formulation, compound_id: str) -> float:
    """Get amount of a compound from formulation."""
    if hasattr(formulation, 'get_total_amount'):
        return formulation.get_total_amount(compound_id)
    if hasattr(formulation, 'get_ingredient'):
        ing = formulation.get_ingredient(compound_id)
        return ing.amount if ing else 0.0
    return 0.0


def _get_ingredient(formulation, compound_id: str):
    """Get ingredient from formulation."""
    if hasattr(formulation, 'get_ingredient'):
        return formulation.get_ingredient(compound_id)
    for ing in formulation.ingredients:
        if ing.compound_id == compound_id:
            return ing
    return None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Ingredient:
    """
    Represents an ingredient in a formulation.
    This is a local copy to avoid import issues in testing.
    In production, use: from core.compounds.formulation import Ingredient
    """
    compound_id: str
    amount: float
    unit: str


@dataclass
class Formulation:
    """
    Represents a supplement formulation.
    This is a local copy to avoid import issues in testing.
    In production, use: from core.compounds.formulation import Formulation
    """
    name: str
    ingredients: List[Ingredient]
    form: str = "capsule"
    serving_info: str = "1 serving"
    
    def get_ingredient(self, compound_id: str) -> Optional[Ingredient]:
        """Get ingredient by compound_id."""
        for ing in self.ingredients:
            if ing.compound_id == compound_id:
                return ing
        return None
    
    def get_total_amount(self, compound_id: str) -> float:
        """Get total amount of a compound."""
        ing = self.get_ingredient(compound_id)
        return ing.amount if ing else 0.0
    
    def copy_with_modifications(
        self,
        name: Optional[str] = None,
        ingredient_changes: Optional[Dict[str, float]] = None,
        add_ingredients: Optional[List[Ingredient]] = None,
        remove_ingredients: Optional[List[str]] = None
    ) -> "Formulation":
        """Create a modified copy of this formulation."""
        new_name = name or f"{self.name} (variant)"
        
        # Start with copy of ingredients
        new_ingredients = []
        removed = set(remove_ingredients or [])
        
        for ing in self.ingredients:
            if ing.compound_id in removed:
                continue
            
            if ingredient_changes and ing.compound_id in ingredient_changes:
                new_amount = ingredient_changes[ing.compound_id]
                if new_amount > 0:
                    new_ingredients.append(Ingredient(
                        compound_id=ing.compound_id,
                        amount=new_amount,
                        unit=ing.unit
                    ))
            else:
                new_ingredients.append(Ingredient(
                    compound_id=ing.compound_id,
                    amount=ing.amount,
                    unit=ing.unit
                ))
        
        # Add new ingredients
        if add_ingredients:
            for ing in add_ingredients:
                if ing.compound_id not in removed:
                    new_ingredients.append(ing)
        
        return Formulation(
            name=new_name,
            ingredients=new_ingredients,
            form=self.form,
            serving_info=self.serving_info
        )


@dataclass
class OptimizationConstraints:
    """Constraints for optimization."""
    max_caffeine_mg: Optional[float] = None
    max_total_stimulants_mg: Optional[float] = None
    max_cost_factor: float = 2.0  # Max 2x base cost
    must_include: List[str] = field(default_factory=list)
    must_exclude: List[str] = field(default_factory=list)
    min_dose_ratios: Dict[str, float] = field(default_factory=dict)
    max_dose_ratios: Dict[str, float] = field(default_factory=dict)
    
    def validate_formulation(self, formulation: Formulation, base: Formulation) -> Tuple[bool, List[str]]:
        """
        Check if a formulation satisfies all constraints.
        Returns (is_valid, list_of_violations).
        """
        violations = []
        
        # Check caffeine limit
        if self.max_caffeine_mg is not None:
            caffeine = _get_amount(formulation, "caffeine")
            if caffeine > self.max_caffeine_mg:
                violations.append(f"Caffeine {caffeine}mg exceeds limit {self.max_caffeine_mg}mg")
        
        # Check total stimulants
        if self.max_total_stimulants_mg is not None:
            total_stim = sum(
                _get_amount(formulation, cid) 
                for cid in STIMULANT_COMPOUNDS
            )
            if total_stim > self.max_total_stimulants_mg:
                violations.append(f"Total stimulants {total_stim}mg exceeds limit")
        
        # Check must_include
        for compound_id in self.must_include:
            if _get_ingredient(formulation, compound_id) is None:
                violations.append(f"Missing required ingredient: {compound_id}")
        
        # Check must_exclude
        for compound_id in self.must_exclude:
            if _get_ingredient(formulation, compound_id) is not None:
                violations.append(f"Contains excluded ingredient: {compound_id}")
        
        # Check dose ratios
        for compound_id, min_ratio in self.min_dose_ratios.items():
            base_amount = _get_amount(base, compound_id)
            new_amount = _get_amount(formulation, compound_id)
            if base_amount > 0:
                actual_ratio = new_amount / base_amount
                if actual_ratio < min_ratio:
                    violations.append(f"{compound_id} ratio {actual_ratio:.2f} below min {min_ratio}")
        
        for compound_id, max_ratio in self.max_dose_ratios.items():
            base_amount = _get_amount(base, compound_id)
            new_amount = _get_amount(formulation, compound_id)
            if base_amount > 0:
                actual_ratio = new_amount / base_amount
                if actual_ratio > max_ratio:
                    violations.append(f"{compound_id} ratio {actual_ratio:.2f} above max {max_ratio}")
        
        return len(violations) == 0, violations


@dataclass
class OptimizerConfig:
    """Configuration for the optimizer."""
    dose_steps: List[float] = field(default_factory=lambda: DEFAULT_DOSE_STEPS.copy())
    max_variants: int = 500
    top_n: int = 3
    include_additions: bool = True
    include_removals: bool = True
    use_known_improvements: bool = True


@dataclass
class OptimizationResult:
    """Result of a single formulation evaluation."""
    formulation: Formulation
    score: float  # Overall optimization score (higher = better)
    efficacy_score: float  # 0-1
    risk_score: float  # 0-1 (higher = more risk = worse)
    metrics: Dict[str, float]
    risk_analysis: Dict[str, float]
    changes_from_base: Dict[str, str]
    
    def __lt__(self, other):
        return self.score < other.score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "formulation_name": self.formulation.name,
            "ingredients": [
                {"compound_id": ing.compound_id, "amount": ing.amount, "unit": ing.unit}
                for ing in self.formulation.ingredients
            ],
            "score": round(self.score, 4),
            "efficacy_score": round(self.efficacy_score, 4),
            "risk_score": round(self.risk_score, 4),
            "metrics": {k: round(v, 4) if isinstance(v, float) else v for k, v in self.metrics.items()},
            "risk_analysis": {k: round(v, 4) for k, v in self.risk_analysis.items()},
            "changes_from_base": self.changes_from_base,
        }


@dataclass
class OptimizationReport:
    """Full optimization report."""
    base_formulation: Formulation
    objective: OptimizationObjective
    constraints: OptimizationConstraints
    
    # Results
    top_variants: List[OptimizationResult]
    base_evaluation: OptimizationResult
    
    # Summary
    total_variants_evaluated: int
    valid_variants: int
    improvement_achieved: float  # % improvement over base
    
    # Comparison
    comparison_table: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization."""
        return {
            "base_formulation": {
                "name": self.base_formulation.name,
                "ingredients": [
                    {"compound_id": ing.compound_id, "amount": ing.amount, "unit": ing.unit}
                    for ing in self.base_formulation.ingredients
                ]
            },
            "objective": self.objective.value,
            "constraints": {
                "max_caffeine_mg": self.constraints.max_caffeine_mg,
                "max_total_stimulants_mg": self.constraints.max_total_stimulants_mg,
                "must_include": self.constraints.must_include,
                "must_exclude": self.constraints.must_exclude,
            },
            "top_variants": [v.to_dict() for v in self.top_variants],
            "base_evaluation": self.base_evaluation.to_dict(),
            "total_variants_evaluated": self.total_variants_evaluated,
            "valid_variants": self.valid_variants,
            "improvement_achieved": round(self.improvement_achieved, 4),
            "comparison_table": self.comparison_table,
        }


# =============================================================================
# MOCK EVALUATOR (For when simulation isn't available)
# =============================================================================

class MockFormulationEvaluator:
    """
    Mock evaluator for testing optimizer without full simulation.
    In production, this would use DaySimulator + PopulationSimulator.
    """
    
    def evaluate(self, formulation: Formulation) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Evaluate a formulation, returning (metrics, risk_analysis).
        
        This mock uses heuristics based on ingredient composition.
        """
        # Extract key amounts
        caffeine = _get_amount(formulation, "caffeine")
        theanine = _get_amount(formulation, "l_theanine")
        beta_alanine = _get_amount(formulation, "beta_alanine")
        citrulline = _get_amount(formulation, "citrulline_malate")
        glucose = _get_amount(formulation, "carbohydrate_glucose")
        
        # Calculate metrics
        base_alertness = 50
        if caffeine > 0:
            # Caffeine effect (diminishing returns after 200mg)
            caffeine_effect = min(40, caffeine / 5)
            base_alertness += caffeine_effect
        
        # Theanine smooths the effect
        theanine_ratio = theanine / caffeine if caffeine > 0 else 0
        alertness_stability = 0.7 + min(0.3, theanine_ratio * 0.3)
        
        # Duration based on caffeine dose
        alertness_duration = 180 + caffeine * 0.5  # minutes
        
        # Glucose effect
        glucose_peak = 90  # Fasting baseline
        if glucose > 0:
            glucose_peak = 90 + glucose * 1.5  # ~1.5 mg/dL per gram
        
        metrics = {
            "alertness_peak": min(100, base_alertness),
            "alertness_duration_above_60": alertness_duration if base_alertness > 60 else 0,
            "alertness_stability": alertness_stability,
            "glucose_peak": glucose_peak,
            "glucose_auc": glucose_peak * 2,  # Simplified
        }
        
        # Calculate risks
        risk_analysis = {}
        
        # Jitter risk increases with caffeine, decreases with theanine
        base_jitter = 0
        if caffeine > 100:
            base_jitter = (caffeine - 100) / 500  # Linear increase
        theanine_reduction = min(0.5, theanine / 400)  # Up to 50% reduction
        risk_analysis["pct_jitter_risk"] = max(0, base_jitter - theanine_reduction)
        
        # Sleep disruption from caffeine
        if caffeine > 0:
            # Higher doses = more sleep risk
            risk_analysis["pct_sleep_disruption"] = min(0.5, caffeine / 600)
        else:
            risk_analysis["pct_sleep_disruption"] = 0
        
        # Hyperglycemia from glucose
        if glucose_peak > 140:
            risk_analysis["pct_hyperglycemia"] = min(0.4, (glucose_peak - 140) / 100)
        else:
            risk_analysis["pct_hyperglycemia"] = 0
        
        # Crash risk (inverse of stability)
        risk_analysis["pct_crash_risk"] = max(0, 0.3 - alertness_stability * 0.3)
        
        return metrics, risk_analysis


# =============================================================================
# FORMULATION OPTIMIZER
# =============================================================================

class FormulationOptimizer:
    """
    Grid search optimizer for supplement formulations.
    
    Generates variants by adjusting ingredient doses, adding synergistic
    ingredients, and removing problematic ones. Evaluates each variant
    and returns the top performers based on the specified objective.
    """
    
    def __init__(
        self,
        config: Optional[OptimizerConfig] = None,
        evaluator: Optional[Any] = None
    ):
        """
        Initialize optimizer.
        
        Args:
            config: Optimizer configuration
            evaluator: Formulation evaluator (uses mock if None)
        """
        self.config = config or OptimizerConfig()
        self.evaluator = evaluator or MockFormulationEvaluator()
    
    def optimize(
        self,
        base_formulation: Formulation,
        objective: OptimizationObjective,
        constraints: OptimizationConstraints
    ) -> OptimizationReport:
        """
        Optimize a formulation.
        
        Args:
            base_formulation: Starting formulation
            objective: What to optimize for
            constraints: Constraints to respect
            
        Returns:
            OptimizationReport with top variants and analysis
        """
        # 1. Evaluate base formulation
        base_metrics, base_risks = self.evaluator.evaluate(base_formulation)
        base_efficacy = self._calculate_efficacy_score(base_metrics)
        base_risk = self._calculate_risk_score(base_risks)
        base_score = self._calculate_combined_score(base_efficacy, base_risk, objective)
        
        base_result = OptimizationResult(
            formulation=base_formulation,
            score=base_score,
            efficacy_score=base_efficacy,
            risk_score=base_risk,
            metrics=base_metrics,
            risk_analysis=base_risks,
            changes_from_base={"status": "BASE"}
        )
        
        # 2. Generate variants
        variants = self._generate_variants_with_constraints(
            base_formulation,
            constraints
        )
        
        # 3. Evaluate variants
        results = []
        valid_count = 0
        
        for variant in variants[:self.config.max_variants]:
            # Check constraints
            is_valid, violations = constraints.validate_formulation(variant, base_formulation)
            if not is_valid:
                continue
            
            valid_count += 1
            
            # Evaluate
            metrics, risks = self.evaluator.evaluate(variant)
            efficacy = self._calculate_efficacy_score(metrics)
            risk = self._calculate_risk_score(risks)
            score = self._calculate_combined_score(efficacy, risk, objective)
            
            # Calculate changes
            changes = self._describe_changes(base_formulation, variant)
            
            results.append(OptimizationResult(
                formulation=variant,
                score=score,
                efficacy_score=efficacy,
                risk_score=risk,
                metrics=metrics,
                risk_analysis=risks,
                changes_from_base=changes
            ))
        
        # 4. Sort and select top N
        results.sort(reverse=True, key=lambda r: r.score)
        top_variants = results[:self.config.top_n]
        
        # 5. Calculate improvement
        improvement = 0.0
        if top_variants and base_score > 0:
            best_score = top_variants[0].score
            improvement = (best_score - base_score) / base_score * 100
        
        # 6. Build comparison table
        comparison_table = self._build_comparison_table(base_result, top_variants)
        
        return OptimizationReport(
            base_formulation=base_formulation,
            objective=objective,
            constraints=constraints,
            top_variants=top_variants,
            base_evaluation=base_result,
            total_variants_evaluated=len(variants[:self.config.max_variants]),
            valid_variants=valid_count,
            improvement_achieved=improvement,
            comparison_table=comparison_table
        )
    
    def _generate_dose_variants(self, formulation: Formulation) -> List[Formulation]:
        """Generate variants by adjusting doses."""
        variants = []
        ingredients = formulation.ingredients
        
        if not ingredients:
            return [formulation]
        
        # Generate all combinations of dose adjustments
        dose_combos = list(itertools.product(
            self.config.dose_steps,
            repeat=len(ingredients)
        ))
        
        for combo in dose_combos:
            if all(m == 1.0 for m in combo):
                continue  # Skip base (no changes)
            
            # Create new ingredient list with adjusted doses
            new_ingredients = []
            changes = {}
            
            for ing, multiplier in zip(ingredients, combo):
                new_amount = ing.amount * multiplier
                if new_amount > 0:
                    new_ingredients.append(Ingredient(
                        compound_id=ing.compound_id,
                        amount=new_amount,
                        unit=ing.unit
                    ))
                    if multiplier != 1.0:
                        changes[ing.compound_id] = f"{multiplier}x"
            
            if new_ingredients:
                variant_name = f"{formulation.name} (variant)"
                variants.append(Formulation(
                    name=variant_name,
                    ingredients=new_ingredients,
                    form=formulation.form,
                    serving_info=formulation.serving_info
                ))
        
        return variants
    
    def _generate_variants_with_constraints(
        self,
        formulation: Formulation,
        constraints: OptimizationConstraints
    ) -> List[Formulation]:
        """Generate variants respecting constraints."""
        all_variants = []
        
        # 1. Dose variants
        dose_variants = self._generate_dose_variants(formulation)
        all_variants.extend(dose_variants)
        
        # 2. Addition variants (if enabled)
        if self.config.include_additions:
            addition_variants = self._generate_addition_variants(formulation)
            all_variants.extend(addition_variants)
        
        # 3. Removal variants (if enabled and must_exclude)
        if self.config.include_removals and constraints.must_exclude:
            for compound_id in constraints.must_exclude:
                removal_variant = self._create_removal_variant(formulation, compound_id)
                if removal_variant:
                    all_variants.append(removal_variant)
        
        # 4. Apply known improvements
        if self.config.use_known_improvements:
            improvement_variants = self._generate_improvement_variants(formulation)
            all_variants.extend(improvement_variants)
        
        return all_variants
    
    def _generate_addition_variants(self, formulation: Formulation) -> List[Formulation]:
        """Generate variants by adding synergistic ingredients."""
        variants = []
        
        for compound_id, info in ADDABLE_INGREDIENTS.items():
            # Check if already present
            if _get_ingredient(formulation, compound_id) is not None:
                continue
            
            # Check if synergy applies
            has_synergy = any(
                _get_ingredient(formulation, syn_id) is not None
                for syn_id in info.get("synergy_with", [])
            )
            
            if has_synergy:
                new_ing = Ingredient(
                    compound_id=compound_id,
                    amount=info["default_dose"],
                    unit=info["unit"]
                )
                variant = formulation.copy_with_modifications(
                    name=f"{formulation.name} +{compound_id}",
                    add_ingredients=[new_ing]
                )
                variants.append(variant)
        
        return variants
    
    def _create_removal_variant(
        self,
        formulation: Formulation,
        compound_id: str
    ) -> Optional[Formulation]:
        """Create a variant with an ingredient removed."""
        if _get_ingredient(formulation, compound_id) is None:
            return None
        
        return formulation.copy_with_modifications(
            name=f"{formulation.name} -{compound_id}",
            remove_ingredients=[compound_id]
        )
    
    def _generate_improvement_variants(self, formulation: Formulation) -> List[Formulation]:
        """Generate variants based on known improvements."""
        variants = []
        
        # Caffeine-theanine synergy
        if _has_caffeine_without_adequate_theanine(formulation):
            caffeine = _get_amount(formulation, "caffeine")
            optimal_theanine = caffeine  # 1:1 ratio
            
            theanine_ing = Ingredient(
                compound_id="l_theanine",
                amount=optimal_theanine,
                unit="mg"
            )
            
            existing_theanine = _get_ingredient(formulation, "l_theanine")
            if existing_theanine:
                # Modify existing
                variant = formulation.copy_with_modifications(
                    name=f"{formulation.name} (theanine balanced)",
                    ingredient_changes={"l_theanine": optimal_theanine}
                )
            else:
                # Add new
                variant = formulation.copy_with_modifications(
                    name=f"{formulation.name} +theanine",
                    add_ingredients=[theanine_ing]
                )
            variants.append(variant)
        
        # Reduce high caffeine
        caffeine = _get_amount(formulation, "caffeine")
        if caffeine > 300:
            for target in [200, 250, 300]:
                if target < caffeine:
                    variant = formulation.copy_with_modifications(
                        name=f"{formulation.name} (caffeine={target}mg)",
                        ingredient_changes={"caffeine": target}
                    )
                    variants.append(variant)
        
        return variants
    
    def _calculate_efficacy_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate efficacy score (0-1).
        Higher is better.
        """
        scores = []
        
        # Alertness peak (target: 70-90)
        alertness = metrics.get("alertness_peak", 50)
        alertness_score = min(1.0, max(0, (alertness - 40) / 50))
        scores.append(alertness_score)
        
        # Duration above threshold (target: 240+ minutes)
        duration = metrics.get("alertness_duration_above_60", 0)
        duration_score = min(1.0, duration / 300)
        scores.append(duration_score)
        
        # Stability (higher is better)
        stability = metrics.get("alertness_stability", 0.5)
        scores.append(stability)
        
        # Glucose in range (lower peak is better for efficacy)
        glucose = metrics.get("glucose_peak", 100)
        glucose_score = max(0, 1.0 - (glucose - 90) / 60)
        scores.append(glucose_score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _calculate_risk_score(self, risk_analysis: Dict[str, float]) -> float:
        """
        Calculate risk score (0-1).
        Higher = more risk = worse.
        """
        risks = []
        
        # Weighted average of risk percentages
        weights = {
            "pct_hyperglycemia": 1.0,
            "pct_jitter_risk": 1.5,  # Slightly more important
            "pct_sleep_disruption": 1.5,
            "pct_crash_risk": 1.0,
        }
        
        total_weight = 0
        weighted_sum = 0
        
        for risk_name, weight in weights.items():
            if risk_name in risk_analysis:
                weighted_sum += risk_analysis[risk_name] * weight
                total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        return 0.0
    
    def _calculate_combined_score(
        self,
        efficacy: float,
        risk: float,
        objective: OptimizationObjective
    ) -> float:
        """
        Calculate combined optimization score.
        
        Higher is always better.
        Risk is inverted (low risk = high score contribution).
        """
        weights = OBJECTIVE_WEIGHTS[objective]
        
        # Invert risk so lower risk = higher score
        risk_contribution = 1.0 - risk
        
        return (
            efficacy * weights["efficacy"] +
            risk_contribution * weights["risk"]
        )
    
    def _describe_changes(
        self,
        base: Formulation,
        variant: Formulation
    ) -> Dict[str, str]:
        """Describe what changed from base to variant."""
        changes = {}
        
        base_ids = {ing.compound_id for ing in base.ingredients}
        variant_ids = {ing.compound_id for ing in variant.ingredients}
        
        # Removals
        removed = base_ids - variant_ids
        for compound_id in removed:
            changes[compound_id] = "REMOVED"
        
        # Additions
        added = variant_ids - base_ids
        for compound_id in added:
            ing = _get_ingredient(variant, compound_id)
            if ing:
                changes[compound_id] = f"ADDED ({ing.amount}{ing.unit})"
        
        # Modifications
        for compound_id in base_ids & variant_ids:
            base_amount = _get_amount(base, compound_id)
            new_amount = _get_amount(variant, compound_id)
            
            if base_amount != new_amount:
                ratio = new_amount / base_amount if base_amount > 0 else 0
                direction = "↑" if ratio > 1 else "↓"
                changes[compound_id] = f"{base_amount}→{new_amount} ({direction}{abs(ratio-1)*100:.0f}%)"
        
        if not changes:
            changes["status"] = "NO_CHANGES"
        
        return changes
    
    def _build_comparison_table(
        self,
        base: OptimizationResult,
        top_variants: List[OptimizationResult]
    ) -> List[Dict[str, Any]]:
        """Build a comparison table for the report."""
        table = []
        
        # Add base
        table.append({
            "name": f"{base.formulation.name} (BASE)",
            "score": round(base.score, 3),
            "efficacy": round(base.efficacy_score, 3),
            "risk": round(base.risk_score, 3),
            "jitter_risk": round(base.risk_analysis.get("pct_jitter_risk", 0) * 100, 1),
            "sleep_risk": round(base.risk_analysis.get("pct_sleep_disruption", 0) * 100, 1),
            "alertness_peak": round(base.metrics.get("alertness_peak", 0), 1),
            "changes": "—",
        })
        
        # Add variants
        for i, v in enumerate(top_variants, 1):
            change_summary = ", ".join(
                f"{k}: {val}" for k, val in v.changes_from_base.items()
                if k != "status"
            )[:50]  # Truncate
            
            table.append({
                "name": f"Variant {i}",
                "score": round(v.score, 3),
                "efficacy": round(v.efficacy_score, 3),
                "risk": round(v.risk_score, 3),
                "jitter_risk": round(v.risk_analysis.get("pct_jitter_risk", 0) * 100, 1),
                "sleep_risk": round(v.risk_analysis.get("pct_sleep_disruption", 0) * 100, 1),
                "alertness_peak": round(v.metrics.get("alertness_peak", 0), 1),
                "changes": change_summary or "—",
            })
        
        return table


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def optimize_formulation(
    formulation: Formulation,
    objective: str = "balanced",
    max_caffeine_mg: Optional[float] = None,
    max_total_stimulants_mg: Optional[float] = None,
    must_include: Optional[List[str]] = None,
    must_exclude: Optional[List[str]] = None,
    top_n: int = 3
) -> OptimizationReport:
    """
    Convenience function for quick optimization.
    
    Args:
        formulation: Formula to optimize
        objective: "max_efficacy", "min_risk", or "balanced"
        max_caffeine_mg: Max caffeine limit
        max_total_stimulants_mg: Max total stimulants
        must_include: Required ingredients
        must_exclude: Forbidden ingredients
        top_n: Number of top variants to return
        
    Returns:
        OptimizationReport
    """
    # Parse objective
    try:
        obj = OptimizationObjective(objective)
    except ValueError:
        obj = OptimizationObjective.BALANCED
    
    # Build constraints
    constraints = OptimizationConstraints(
        max_caffeine_mg=max_caffeine_mg,
        max_total_stimulants_mg=max_total_stimulants_mg,
        must_include=must_include or [],
        must_exclude=must_exclude or [],
    )
    
    # Create optimizer with config
    config = OptimizerConfig(top_n=top_n)
    optimizer = FormulationOptimizer(config=config)
    
    return optimizer.optimize(formulation, obj, constraints)


def format_optimization_report(report: OptimizationReport) -> str:
    """
    Format optimization report as readable text.
    
    Args:
        report: The optimization report
        
    Returns:
        Formatted string
    """
    lines = []
    
    lines.append("=" * 60)
    lines.append("FORMULATION OPTIMIZATION REPORT")
    lines.append("=" * 60)
    lines.append("")
    
    lines.append(f"Base Formula: {report.base_formulation.name}")
    lines.append(f"Objective: {report.objective.value}")
    lines.append(f"Variants Evaluated: {report.total_variants_evaluated}")
    lines.append(f"Valid Variants: {report.valid_variants}")
    lines.append(f"Improvement Achieved: {report.improvement_achieved:+.1f}%")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("BASE FORMULA EVALUATION")
    lines.append("-" * 60)
    base = report.base_evaluation
    lines.append(f"  Score: {base.score:.3f}")
    lines.append(f"  Efficacy: {base.efficacy_score:.3f}")
    lines.append(f"  Risk: {base.risk_score:.3f}")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("TOP VARIANTS")
    lines.append("-" * 60)
    
    for i, v in enumerate(report.top_variants, 1):
        lines.append(f"\n{i}. {v.formulation.name}")
        lines.append(f"   Score: {v.score:.3f} (Efficacy: {v.efficacy_score:.3f}, Risk: {v.risk_score:.3f})")
        lines.append("   Changes:")
        for compound, change in v.changes_from_base.items():
            if compound != "status":
                lines.append(f"     - {compound}: {change}")
        
        lines.append("   Key Metrics:")
        lines.append(f"     - Alertness Peak: {v.metrics.get('alertness_peak', 0):.1f}")
        lines.append(f"     - Jitter Risk: {v.risk_analysis.get('pct_jitter_risk', 0)*100:.1f}%")
        lines.append(f"     - Sleep Risk: {v.risk_analysis.get('pct_sleep_disruption', 0)*100:.1f}%")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Enums
    "OptimizationObjective",
    
    # Data classes
    "OptimizationConstraints",
    "OptimizerConfig",
    "OptimizationResult",
    "OptimizationReport",
    "Ingredient",
    "Formulation",
    
    # Main class
    "FormulationOptimizer",
    
    # Convenience functions
    "optimize_formulation",
    "format_optimization_report",
]
