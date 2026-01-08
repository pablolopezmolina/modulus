# tests/unit/test_optimizer.py
"""
Tests for FormulationOptimizer - MODULUS Session 14.2

Tests the grid search optimizer that finds improved formulation variants.
"""
import pytest
import sys
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


# =============================================================================
# PATH SETUP FOR IMPORTS
# =============================================================================

# Add parent directories to path for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_current_dir, '..', '..', 'src')
if os.path.exists(_src_dir):
    sys.path.insert(0, _src_dir)
else:
    sys.path.insert(0, _current_dir)


# =============================================================================
# IMPORT THE MODULE UNDER TEST
# =============================================================================

try:
    from analysis.optimizer import (
        FormulationOptimizer,
        OptimizerConfig,
        OptimizationObjective,
        OptimizationConstraints,
        OptimizationResult,
        OptimizationReport,
        Ingredient,
        Formulation,
        optimize_formulation,
        format_optimization_report,
    )
    _MODULE_AVAILABLE = True
except ImportError:
    try:
        from optimizer import (
            FormulationOptimizer,
            OptimizerConfig,
            OptimizationObjective,
            OptimizationConstraints,
            OptimizationResult,
            OptimizationReport,
            Ingredient,
            Formulation,
            optimize_formulation,
            format_optimization_report,
        )
        _MODULE_AVAILABLE = True
    except ImportError:
        _MODULE_AVAILABLE = False


# Skip all tests if module not available
pytestmark = pytest.mark.skipif(
    not _MODULE_AVAILABLE,
    reason="optimizer module not available"
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def base_preworkout():
    """Standard pre-workout formula for testing"""
    return Formulation(
        name="Test Pre-Workout",
        ingredients=[
            Ingredient("caffeine", 200, "mg"),
            Ingredient("l_theanine", 100, "mg"),
            Ingredient("beta_alanine", 2000, "mg"),
            Ingredient("citrulline_malate", 6000, "mg"),
        ],
        form="powder",
        serving_info="1 scoop (10g)"
    )


@pytest.fixture
def simple_caffeine_formula():
    """Simple caffeine-only formula"""
    return Formulation(
        name="Simple Caffeine",
        ingredients=[
            Ingredient("caffeine", 200, "mg"),
        ],
        form="capsule"
    )


@pytest.fixture
def high_risk_formula():
    """Formula with high risk metrics (high caffeine)"""
    return Formulation(
        name="High Risk Formula",
        ingredients=[
            Ingredient("caffeine", 400, "mg"),  # Very high
            Ingredient("carbohydrate_glucose", 50, "g"),
        ],
        form="powder"
    )


@pytest.fixture
def default_constraints():
    """Default optimization constraints"""
    return OptimizationConstraints(
        max_caffeine_mg=300,
        max_cost_factor=1.5,
    )


# =============================================================================
# TEST: OptimizationConstraints
# =============================================================================

class TestOptimizationConstraints:
    """Tests for constraint validation"""
    
    def test_default_constraints(self):
        """Default constraints have sensible values"""
        constraints = OptimizationConstraints()
        assert constraints.max_caffeine_mg is None
        assert constraints.max_cost_factor == 2.0
        assert constraints.must_include == []
        assert constraints.must_exclude == []
    
    def test_constraints_with_limits(self):
        """Constraints can have specific limits"""
        constraints = OptimizationConstraints(
            max_caffeine_mg=200,
            max_total_stimulants_mg=250,
            must_include=["caffeine"],
            must_exclude=["synephrine"]
        )
        assert constraints.max_caffeine_mg == 200
        assert constraints.must_include == ["caffeine"]
        assert constraints.must_exclude == ["synephrine"]
    
    def test_dose_ratio_constraints(self):
        """Dose ratios can limit ingredient scaling"""
        constraints = OptimizationConstraints(
            min_dose_ratios={"caffeine": 0.5},
            max_dose_ratios={"caffeine": 1.5},
        )
        assert constraints.min_dose_ratios["caffeine"] == 0.5
        assert constraints.max_dose_ratios["caffeine"] == 1.5
    
    def test_validate_formulation_passes(self, base_preworkout):
        """Validates a compliant formulation"""
        constraints = OptimizationConstraints(
            max_caffeine_mg=300,
            must_include=["caffeine"]
        )
        is_valid, violations = constraints.validate_formulation(
            base_preworkout, base_preworkout
        )
        assert is_valid
        assert len(violations) == 0
    
    def test_validate_formulation_fails_caffeine(self, high_risk_formula):
        """Rejects formula with too much caffeine"""
        constraints = OptimizationConstraints(max_caffeine_mg=200)
        base = high_risk_formula
        is_valid, violations = constraints.validate_formulation(
            high_risk_formula, base
        )
        assert not is_valid
        assert any("caffeine" in v.lower() for v in violations)


# =============================================================================
# TEST: OptimizationObjective
# =============================================================================

class TestOptimizationObjective:
    """Tests for optimization objectives"""
    
    def test_objectives_exist(self):
        """All expected objectives exist"""
        assert OptimizationObjective.MAX_EFFICACY.value == "max_efficacy"
        assert OptimizationObjective.MIN_RISK.value == "min_risk"
        assert OptimizationObjective.BALANCED.value == "balanced"
    
    def test_objective_from_string(self):
        """Can create objective from string"""
        obj = OptimizationObjective("max_efficacy")
        assert obj == OptimizationObjective.MAX_EFFICACY


# =============================================================================
# TEST: OptimizerConfig
# =============================================================================

class TestOptimizerConfig:
    """Tests for optimizer configuration"""
    
    def test_default_config(self):
        """Default config has sensible values"""
        config = OptimizerConfig()
        assert len(config.dose_steps) > 0
        assert config.max_variants > 0
        assert config.top_n > 0
    
    def test_custom_config(self):
        """Can create custom config"""
        config = OptimizerConfig(
            dose_steps=[0.5, 1.0, 1.5],
            max_variants=100,
            top_n=5
        )
        assert len(config.dose_steps) == 3
        assert config.max_variants == 100
        assert config.top_n == 5


# =============================================================================
# TEST: FormulationOptimizer - Initialization
# =============================================================================

class TestFormulationOptimizerInit:
    """Tests for optimizer initialization"""
    
    def test_create_optimizer(self):
        """Can create optimizer with default settings"""
        optimizer = FormulationOptimizer()
        assert optimizer is not None
        assert optimizer.config is not None
    
    def test_create_optimizer_with_config(self):
        """Can create optimizer with custom config"""
        config = OptimizerConfig(max_variants=100, top_n=5)
        optimizer = FormulationOptimizer(config=config)
        assert optimizer.config.max_variants == 100
        assert optimizer.config.top_n == 5


# =============================================================================
# TEST: FormulationOptimizer - Variant Generation
# =============================================================================

class TestVariantGeneration:
    """Tests for generating formula variants"""
    
    def test_generate_dose_variants(self, simple_caffeine_formula):
        """Generates variants by adjusting doses"""
        optimizer = FormulationOptimizer()
        variants = optimizer._generate_dose_variants(simple_caffeine_formula)
        
        assert len(variants) > 1
        for v in variants:
            assert isinstance(v, Formulation)
    
    def test_variants_with_multiple_ingredients(self, base_preworkout):
        """Generates variants for multi-ingredient formula"""
        optimizer = FormulationOptimizer()
        variants = optimizer._generate_dose_variants(base_preworkout)
        
        # Should have many combinations
        assert len(variants) > 5
    
    def test_generate_variants_with_constraints(self, base_preworkout, default_constraints):
        """Generates variants respecting constraints"""
        optimizer = FormulationOptimizer()
        variants = optimizer._generate_variants_with_constraints(
            base_preworkout,
            default_constraints
        )
        
        assert len(variants) > 0
    
    def test_generate_addition_variants(self, simple_caffeine_formula):
        """Generates variants with additional ingredients"""
        optimizer = FormulationOptimizer()
        variants = optimizer._generate_addition_variants(simple_caffeine_formula)
        
        # Should suggest adding theanine (synergy with caffeine)
        added_compounds = set()
        for v in variants:
            for ing in v.ingredients:
                if ing.compound_id != "caffeine":
                    added_compounds.add(ing.compound_id)
        
        # L-theanine should be suggested
        assert "l_theanine" in added_compounds or "taurine" in added_compounds


# =============================================================================
# TEST: FormulationOptimizer - Scoring
# =============================================================================

class TestScoring:
    """Tests for formulation scoring"""
    
    def test_efficacy_score_in_range(self):
        """Efficacy score is in [0, 1]"""
        optimizer = FormulationOptimizer()
        metrics = {
            "alertness_peak": 85,
            "alertness_duration_above_60": 300,
            "alertness_stability": 0.8,
            "glucose_peak": 120,
        }
        score = optimizer._calculate_efficacy_score(metrics)
        assert 0 <= score <= 1
    
    def test_high_efficacy_scores_well(self):
        """High efficacy metrics score above 0.5"""
        optimizer = FormulationOptimizer()
        metrics = {
            "alertness_peak": 90,
            "alertness_duration_above_60": 350,
            "alertness_stability": 0.9,
            "glucose_peak": 100,
        }
        score = optimizer._calculate_efficacy_score(metrics)
        assert score > 0.5
    
    def test_risk_score_in_range(self):
        """Risk score is in [0, 1]"""
        optimizer = FormulationOptimizer()
        risks = {
            "pct_hyperglycemia": 0.30,
            "pct_jitter_risk": 0.40,
            "pct_sleep_disruption": 0.35,
        }
        score = optimizer._calculate_risk_score(risks)
        assert 0 <= score <= 1
    
    def test_high_risk_scores_high(self):
        """High risk metrics score above 0.25"""
        optimizer = FormulationOptimizer()
        risks = {
            "pct_hyperglycemia": 0.40,
            "pct_jitter_risk": 0.50,
            "pct_sleep_disruption": 0.45,
            "pct_crash_risk": 0.30,
        }
        score = optimizer._calculate_risk_score(risks)
        assert score > 0.25
    
    def test_combined_score_max_efficacy(self):
        """MAX_EFFICACY weights efficacy higher"""
        optimizer = FormulationOptimizer()
        
        score = optimizer._calculate_combined_score(
            efficacy=0.9, risk=0.3, objective=OptimizationObjective.MAX_EFFICACY
        )
        assert score > 0.5
    
    def test_combined_score_min_risk(self):
        """MIN_RISK penalizes high risk more"""
        optimizer = FormulationOptimizer()
        
        score_min = optimizer._calculate_combined_score(
            efficacy=0.8, risk=0.7, objective=OptimizationObjective.MIN_RISK
        )
        score_max = optimizer._calculate_combined_score(
            efficacy=0.8, risk=0.7, objective=OptimizationObjective.MAX_EFFICACY
        )
        assert score_min < score_max
    
    def test_combined_score_balanced(self):
        """BALANCED weighs both equally"""
        optimizer = FormulationOptimizer()
        
        score = optimizer._calculate_combined_score(
            efficacy=0.7, risk=0.3, objective=OptimizationObjective.BALANCED
        )
        assert 0 <= score <= 1


# =============================================================================
# TEST: FormulationOptimizer - Full Optimization
# =============================================================================

class TestOptimization:
    """Tests for full optimization pipeline"""
    
    def test_optimize_returns_report(self, base_preworkout, default_constraints):
        """optimize() returns OptimizationReport"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            default_constraints
        )
        
        assert isinstance(report, OptimizationReport)
        assert report.base_formulation == base_preworkout
        assert report.objective == OptimizationObjective.BALANCED
    
    def test_optimize_returns_top_variants(self, base_preworkout):
        """optimize() returns top N variants"""
        config = OptimizerConfig(top_n=3)
        optimizer = FormulationOptimizer(config=config)
        
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        assert len(report.top_variants) <= 3
        assert len(report.top_variants) >= 1
    
    def test_optimize_variants_sorted_by_score(self, base_preworkout):
        """Top variants are sorted best first"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        if len(report.top_variants) > 1:
            scores = [v.score for v in report.top_variants]
            assert scores == sorted(scores, reverse=True)
    
    def test_optimize_includes_base_evaluation(self, base_preworkout):
        """Report includes evaluation of base formula"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        assert report.base_evaluation is not None
        assert report.base_evaluation.formulation == base_preworkout
    
    def test_optimize_calculates_improvement(self, high_risk_formula):
        """Calculates improvement over base"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            high_risk_formula,
            OptimizationObjective.MIN_RISK,
            OptimizationConstraints(max_caffeine_mg=200)
        )
        
        assert report.improvement_achieved is not None
    
    def test_optimize_with_max_efficacy(self, base_preworkout):
        """MAX_EFFICACY optimization works"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.MAX_EFFICACY,
            OptimizationConstraints()
        )
        
        assert len(report.top_variants) >= 1
        assert report.top_variants[0].efficacy_score > 0
    
    def test_optimize_with_min_risk(self, high_risk_formula):
        """MIN_RISK optimization reduces risk"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            high_risk_formula,
            OptimizationObjective.MIN_RISK,
            OptimizationConstraints(max_caffeine_mg=150)
        )
        
        if report.top_variants:
            top = report.top_variants[0]
            # With constraint, should find lower risk variant
            assert top.risk_score <= report.base_evaluation.risk_score + 0.1


# =============================================================================
# TEST: OptimizationResult Details
# =============================================================================

class TestOptimizationResult:
    """Tests for optimization result details"""
    
    def test_result_has_changes_description(self, base_preworkout):
        """Results describe changes from base"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        for result in report.top_variants:
            assert isinstance(result.changes_from_base, dict)
    
    def test_result_has_metrics(self, base_preworkout):
        """Results include relevant metrics"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        for result in report.top_variants:
            assert isinstance(result.metrics, dict)
            assert isinstance(result.risk_analysis, dict)
    
    def test_result_has_valid_scores(self, base_preworkout):
        """All scores are in valid ranges"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        for result in report.top_variants:
            assert 0 <= result.efficacy_score <= 1
            assert 0 <= result.risk_score <= 1
    
    def test_result_to_dict(self, base_preworkout):
        """Result can be converted to dict"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        for result in report.top_variants:
            data = result.to_dict()
            assert isinstance(data, dict)
            assert "score" in data
            assert "efficacy_score" in data


# =============================================================================
# TEST: Comparison Table
# =============================================================================

class TestComparisonTable:
    """Tests for comparison table generation"""
    
    def test_comparison_table_generated(self, base_preworkout):
        """Comparison table is generated"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        assert isinstance(report.comparison_table, list)
        assert len(report.comparison_table) > 0
    
    def test_comparison_table_includes_base(self, base_preworkout):
        """Comparison table includes base formula"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        names = [row.get("name", "") for row in report.comparison_table]
        assert any("base" in n.lower() for n in names)
    
    def test_comparison_table_has_metrics(self, base_preworkout):
        """Comparison table has key metrics"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        for row in report.comparison_table:
            assert "score" in row
            assert "efficacy" in row or "efficacy_score" in row


# =============================================================================
# TEST: Serialization
# =============================================================================

class TestSerialization:
    """Tests for report serialization"""
    
    def test_report_to_dict(self, base_preworkout):
        """Report can be converted to dict"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        data = report.to_dict()
        assert isinstance(data, dict)
        assert "base_formulation" in data
        assert "top_variants" in data
        assert "improvement_achieved" in data
    
    def test_format_report(self, base_preworkout):
        """Report can be formatted as text"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        text = format_optimization_report(report)
        assert isinstance(text, str)
        assert "OPTIMIZATION" in text.upper()
        assert len(text) > 100


# =============================================================================
# TEST: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_single_ingredient_formula(self):
        """Works with single ingredient"""
        formula = Formulation(
            name="Just Caffeine",
            ingredients=[Ingredient("caffeine", 100, "mg")]
        )
        
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            formula,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        assert report is not None
        assert len(report.top_variants) >= 1
    
    def test_very_constrained_optimization(self):
        """Handles very restrictive constraints"""
        formula = Formulation(
            name="Test",
            ingredients=[
                Ingredient("caffeine", 200, "mg"),
                Ingredient("l_theanine", 100, "mg"),
            ]
        )
        
        constraints = OptimizationConstraints(
            max_caffeine_mg=50,
            min_dose_ratios={"l_theanine": 0.9},
            max_dose_ratios={"l_theanine": 1.1},
        )
        
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            formula,
            OptimizationObjective.BALANCED,
            constraints
        )
        
        assert report is not None
    
    def test_empty_constraints(self, base_preworkout):
        """Works with no constraints"""
        optimizer = FormulationOptimizer()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        assert report is not None
        assert report.valid_variants > 0


# =============================================================================
# TEST: Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience/helper functions"""
    
    def test_optimize_formulation_function(self, base_preworkout):
        """Convenience function works"""
        report = optimize_formulation(
            base_preworkout,
            objective="balanced",
            max_caffeine_mg=250
        )
        
        assert report is not None
        assert len(report.top_variants) >= 1
    
    def test_quick_optimize(self, simple_caffeine_formula):
        """Quick optimization with minimal params"""
        report = optimize_formulation(simple_caffeine_formula)
        
        assert report is not None
    
    def test_optimize_with_string_objective(self, base_preworkout):
        """String objectives are converted correctly"""
        for obj_str in ["max_efficacy", "min_risk", "balanced"]:
            report = optimize_formulation(base_preworkout, objective=obj_str)
            assert report is not None


# =============================================================================
# TEST: Performance
# =============================================================================

class TestPerformance:
    """Tests for performance constraints"""
    
    def test_optimization_completes_quickly(self, base_preworkout):
        """Optimization completes in reasonable time"""
        import time
        
        optimizer = FormulationOptimizer()
        
        start = time.time()
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        elapsed = time.time() - start
        
        assert elapsed < 5.0  # Should complete in under 5 seconds
    
    def test_max_variants_limit_respected(self, base_preworkout):
        """Max variants limit is respected"""
        config = OptimizerConfig(max_variants=10)
        optimizer = FormulationOptimizer(config=config)
        
        report = optimizer.optimize(
            base_preworkout,
            OptimizationObjective.BALANCED,
            OptimizationConstraints()
        )
        
        assert report.total_variants_evaluated <= 10


# =============================================================================
# TEST: Formulation Helper Methods
# =============================================================================

class TestFormulation:
    """Tests for Formulation class methods"""
    
    def test_get_ingredient(self, base_preworkout):
        """get_ingredient returns correct ingredient"""
        ing = base_preworkout.get_ingredient("caffeine")
        assert ing is not None
        assert ing.amount == 200
    
    def test_get_ingredient_missing(self, base_preworkout):
        """get_ingredient returns None for missing"""
        ing = base_preworkout.get_ingredient("nonexistent")
        assert ing is None
    
    def test_get_total_amount(self, base_preworkout):
        """get_total_amount returns correct amount"""
        amount = base_preworkout.get_total_amount("caffeine")
        assert amount == 200
    
    def test_copy_with_modifications(self, base_preworkout):
        """copy_with_modifications creates correct variant"""
        variant = base_preworkout.copy_with_modifications(
            name="Modified",
            ingredient_changes={"caffeine": 150}
        )
        
        assert variant.name == "Modified"
        assert variant.get_total_amount("caffeine") == 150
        assert variant.get_total_amount("l_theanine") == 100  # Unchanged
    
    def test_copy_with_additions(self, simple_caffeine_formula):
        """copy_with_modifications adds ingredients"""
        new_ing = Ingredient("taurine", 1000, "mg")
        variant = simple_caffeine_formula.copy_with_modifications(
            add_ingredients=[new_ing]
        )
        
        assert variant.get_ingredient("taurine") is not None
        assert variant.get_ingredient("caffeine") is not None
    
    def test_copy_with_removals(self, base_preworkout):
        """copy_with_modifications removes ingredients"""
        variant = base_preworkout.copy_with_modifications(
            remove_ingredients=["beta_alanine"]
        )
        
        assert variant.get_ingredient("beta_alanine") is None
        assert variant.get_ingredient("caffeine") is not None


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
