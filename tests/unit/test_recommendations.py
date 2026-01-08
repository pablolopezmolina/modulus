"""
Tests for MODULUS Recommendation Engine
Session 14.1 - FASE 4

Tests the intelligent recommendation system that analyzes simulation results
and generates actionable suggestions to improve formulations.
"""

import pytest
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum
import math

# Import from the correct project location
from src.analysis.recommendations import (
    RecommendationType,
    Recommendation,
    RecommendationReport,
    RecommendationConfig,
    RecommendationEngine,
    generate_recommendations,
    format_recommendations_text,
)


# =============================================================================
# MOCK CLASSES FOR TESTING (matching existing contracts)
# =============================================================================

@dataclass
class MockFormulation:
    """Mock Formulation for testing."""
    name: str
    ingredients: List[Dict[str, Any]]
    
    def get_ingredient_amount(self, compound_id: str) -> Optional[float]:
        """Get amount of specific ingredient."""
        for ing in self.ingredients:
            if ing.get("compound_id") == compound_id:
                return ing.get("amount", 0.0)
        return None
    
    def has_ingredient(self, compound_id: str) -> bool:
        """Check if formulation has specific ingredient."""
        return self.get_ingredient_amount(compound_id) is not None


@dataclass
class MockRiskAnalysis:
    """Mock risk analysis results."""
    pct_hyperglycemia: float = 0.0
    pct_severe_hyperglycemia: float = 0.0
    pct_jitter_risk: float = 0.0
    pct_sleep_disruption: float = 0.0
    pct_crash_risk: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "pct_hyperglycemia": self.pct_hyperglycemia,
            "pct_severe_hyperglycemia": self.pct_severe_hyperglycemia,
            "pct_jitter_risk": self.pct_jitter_risk,
            "pct_sleep_disruption": self.pct_sleep_disruption,
            "pct_crash_risk": self.pct_crash_risk,
        }


@dataclass
class MockMetricsStats:
    """Mock metrics statistics."""
    caffeine_peak_mean: float = 0.0
    caffeine_peak_std: float = 0.0
    glucose_peak_mean: float = 0.0
    glucose_peak_std: float = 0.0
    alertness_duration_mean: float = 0.0
    
    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return {
            "caffeine_peak": {"mean": self.caffeine_peak_mean, "std": self.caffeine_peak_std},
            "glucose_peak": {"mean": self.glucose_peak_mean, "std": self.glucose_peak_std},
            "alertness_duration_above_60": {"mean": self.alertness_duration_mean},
        }


@dataclass
class MockPopulationResult:
    """Mock PopulationSimulationResult for testing."""
    n_individuals: int = 1000
    n_valid: int = 980
    risk_analysis: Dict[str, float] = None
    metrics_stats: Dict[str, Dict[str, float]] = None
    formulation: MockFormulation = None
    intake_time_minutes: float = 420  # 7:00 AM default
    
    def __post_init__(self):
        if self.risk_analysis is None:
            self.risk_analysis = MockRiskAnalysis().to_dict()
        if self.metrics_stats is None:
            self.metrics_stats = MockMetricsStats().to_dict()


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestRecommendationDataClasses:
    """Test the recommendation data structures."""
    
    def test_recommendation_type_enum(self):
        """RecommendationType has all expected values."""
        assert RecommendationType.INGREDIENT_ADJUSTMENT.value == "ingredient_adjustment"
        assert RecommendationType.TIMING_OPTIMIZATION.value == "timing_optimization"
        assert RecommendationType.ADDITION_SUGGESTION.value == "addition_suggestion"
        assert RecommendationType.LABEL_WARNING.value == "label_warning"
        assert RecommendationType.REMOVAL_SUGGESTION.value == "removal_suggestion"
    
    def test_recommendation_creation(self):
        """Recommendation dataclass works correctly."""
        rec = Recommendation(
            recommendation_id="rec_001",
            recommendation_type=RecommendationType.INGREDIENT_ADJUSTMENT,
            title="Reduce caffeine dose",
            description="Reduce caffeine from 200mg to 150mg to lower jitter risk",
            expected_impact={"pct_jitter_risk": -0.15, "alertness_duration": -0.05},
            confidence=0.85,
            evidence_summary="Based on caffeine PK model and population response",
            priority=1,
            target_ingredient="caffeine",
            current_value=200.0,
            suggested_value=150.0
        )
        
        assert rec.recommendation_id == "rec_001"
        assert rec.recommendation_type == RecommendationType.INGREDIENT_ADJUSTMENT
        assert rec.confidence == 0.85
        assert rec.target_ingredient == "caffeine"
        assert rec.expected_impact["pct_jitter_risk"] == -0.15
    
    def test_recommendation_report_creation(self):
        """RecommendationReport dataclass works correctly."""
        rec1 = Recommendation(
            recommendation_id="rec_001",
            recommendation_type=RecommendationType.INGREDIENT_ADJUSTMENT,
            title="Test 1",
            description="Test desc",
            expected_impact={},
            confidence=0.8,
            evidence_summary="Test",
            priority=1
        )
        rec2 = Recommendation(
            recommendation_id="rec_002",
            recommendation_type=RecommendationType.LABEL_WARNING,
            title="Test 2",
            description="Test desc 2",
            expected_impact={},
            confidence=0.7,
            evidence_summary="Test",
            priority=3
        )
        
        report = RecommendationReport(
            formulation_name="Test Product",
            total_recommendations=2,
            recommendations=[rec1, rec2],
            overall_improvement_potential=0.25,
            key_issues_identified=["High jitter risk"]
        )
        
        assert report.total_recommendations == 2
        assert len(report.recommendations) == 2
        assert report.overall_improvement_potential == 0.25
    
    def test_report_get_by_type(self):
        """RecommendationReport.get_by_type filters correctly."""
        rec1 = Recommendation(
            recommendation_id="rec_001",
            recommendation_type=RecommendationType.INGREDIENT_ADJUSTMENT,
            title="Adjust", description="", expected_impact={},
            confidence=0.8, evidence_summary="", priority=1
        )
        rec2 = Recommendation(
            recommendation_id="rec_002",
            recommendation_type=RecommendationType.LABEL_WARNING,
            title="Warning", description="", expected_impact={},
            confidence=0.7, evidence_summary="", priority=2
        )
        rec3 = Recommendation(
            recommendation_id="rec_003",
            recommendation_type=RecommendationType.INGREDIENT_ADJUSTMENT,
            title="Adjust 2", description="", expected_impact={},
            confidence=0.6, evidence_summary="", priority=3
        )
        
        report = RecommendationReport(
            formulation_name="Test",
            total_recommendations=3,
            recommendations=[rec1, rec2, rec3],
            overall_improvement_potential=0.3,
            key_issues_identified=[]
        )
        
        adjustments = report.get_by_type(RecommendationType.INGREDIENT_ADJUSTMENT)
        assert len(adjustments) == 2
        
        warnings = report.get_by_type(RecommendationType.LABEL_WARNING)
        assert len(warnings) == 1
    
    def test_report_get_high_priority(self):
        """RecommendationReport.get_high_priority filters correctly."""
        recs = [
            Recommendation(
                recommendation_id=f"rec_{i}",
                recommendation_type=RecommendationType.INGREDIENT_ADJUSTMENT,
                title=f"Rec {i}", description="", expected_impact={},
                confidence=0.8, evidence_summary="", priority=i
            )
            for i in range(1, 6)
        ]
        
        report = RecommendationReport(
            formulation_name="Test",
            total_recommendations=5,
            recommendations=recs,
            overall_improvement_potential=0.2,
            key_issues_identified=[]
        )
        
        high_priority = report.get_high_priority(2)
        assert len(high_priority) == 2
        assert all(r.priority <= 2 for r in high_priority)


class TestRecommendationEngine:
    """Test the RecommendationEngine class."""
    
    def test_engine_initialization(self):
        """RecommendationEngine initializes correctly."""
        engine = RecommendationEngine()
        assert engine is not None
    
    def test_engine_initialization_with_config(self):
        """RecommendationEngine accepts configuration."""
        config = RecommendationConfig(
            jitter_risk_threshold=0.20,
            sleep_risk_threshold=0.15,
            hyperglycemia_threshold=0.10,
            min_confidence=0.6
        )
        engine = RecommendationEngine(config=config)
        
        assert engine.config.jitter_risk_threshold == 0.20
    
    def test_analyze_returns_report(self):
        """analyze() returns a RecommendationReport."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Pre-Workout",
            ingredients=[
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
                {"compound_id": "beta_alanine", "amount": 3200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.30,
                "pct_sleep_disruption": 0.25,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.08,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        assert isinstance(report, RecommendationReport)
        assert report.formulation_name == "Test Pre-Workout"
    
    def test_high_jitter_risk_generates_recommendation(self):
        """High jitter risk triggers caffeine reduction recommendation."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="High Caffeine Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 300, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.35,  # High jitter risk
                "pct_sleep_disruption": 0.10,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should have caffeine reduction recommendation
        adjustments = report.get_by_type(RecommendationType.INGREDIENT_ADJUSTMENT)
        caffeine_recs = [r for r in adjustments if r.target_ingredient == "caffeine"]
        
        assert len(caffeine_recs) > 0
        rec = caffeine_recs[0]
        assert rec.suggested_value < rec.current_value
    
    def test_high_sleep_risk_generates_timing_recommendation(self):
        """High sleep disruption risk triggers timing recommendation."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Afternoon Energy",
            ingredients=[
                {"compound_id": "caffeine", "amount": 150, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            intake_time_minutes=900,  # 15:00 (3 PM)
            risk_analysis={
                "pct_jitter_risk": 0.10,
                "pct_sleep_disruption": 0.28,  # High sleep risk
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should have timing recommendation
        timing_recs = report.get_by_type(RecommendationType.TIMING_OPTIMIZATION)
        assert len(timing_recs) > 0
    
    def test_caffeine_without_theanine_suggests_addition(self):
        """Caffeine product without L-theanine suggests adding it."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Pure Caffeine",
            ingredients=[
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.22,  # Moderate jitter
                "pct_sleep_disruption": 0.10,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should suggest adding L-theanine
        additions = report.get_by_type(RecommendationType.ADDITION_SUGGESTION)
        theanine_recs = [r for r in additions if "theanine" in r.target_ingredient.lower()]
        
        assert len(theanine_recs) > 0
    
    def test_high_risk_generates_label_warning(self):
        """High risk in any segment generates label warning."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Strong Pre-Workout",
            ingredients=[
                {"compound_id": "caffeine", "amount": 350, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.40,  # Very high
                "pct_sleep_disruption": 0.35,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.08,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should have label warning
        warnings = report.get_by_type(RecommendationType.LABEL_WARNING)
        assert len(warnings) > 0
        
        # Warning should mention caffeine sensitivity
        warning_texts = [w.warning_text for w in warnings if w.warning_text]
        combined = " ".join(warning_texts).lower()
        assert "caffeine" in combined or "sensitive" in combined
    
    def test_low_risk_product_minimal_recommendations(self):
        """Low risk product generates minimal or no recommendations."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Well Balanced Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 100, "unit": "mg"},
                {"compound_id": "l_theanine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            intake_time_minutes=420,  # 7:00 AM
            risk_analysis={
                "pct_jitter_risk": 0.05,
                "pct_sleep_disruption": 0.08,
                "pct_hyperglycemia": 0.03,
                "pct_crash_risk": 0.04,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should have few or no high priority recommendations
        high_priority = report.get_high_priority(2)
        assert len(high_priority) <= 1
    
    def test_confidence_based_on_evidence(self):
        """Recommendation confidence reflects evidence strength."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 250, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.30,
                "pct_sleep_disruption": 0.20,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # All recommendations should have valid confidence
        for rec in report.recommendations:
            assert 0.0 <= rec.confidence <= 1.0
            assert rec.evidence_summary  # Should have evidence
    
    def test_expected_impact_has_reasonable_values(self):
        """Expected impact values are reasonable."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 300, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.35,
                "pct_sleep_disruption": 0.25,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        for rec in report.recommendations:
            for metric, delta in rec.expected_impact.items():
                # Delta should be reasonable (not >100% change)
                assert -1.0 <= delta <= 1.0


class TestCaffeineRecommendations:
    """Specific tests for caffeine-related recommendations."""
    
    def test_caffeine_dose_reduction_calculation(self):
        """Caffeine dose reduction is calculated appropriately."""
        engine = RecommendationEngine()
        
        # Test various caffeine doses
        test_cases = [
            (400, 200),  # Very high -> reduce significantly
            (300, 200),  # High -> reduce to moderate
            (250, 200),  # Moderate-high -> reduce slightly
        ]
        
        for initial_dose, max_expected in test_cases:
            formulation = MockFormulation(
                name=f"Caffeine {initial_dose}mg",
                ingredients=[
                    {"compound_id": "caffeine", "amount": initial_dose, "unit": "mg"},
                ]
            )
            
            results = MockPopulationResult(
                formulation=formulation,
                risk_analysis={
                    "pct_jitter_risk": 0.35,
                    "pct_sleep_disruption": 0.25,
                    "pct_hyperglycemia": 0.05,
                    "pct_crash_risk": 0.05,
                }
            )
            
            report = engine.analyze(results, formulation)
            
            adjustments = report.get_by_type(RecommendationType.INGREDIENT_ADJUSTMENT)
            caffeine_recs = [r for r in adjustments if r.target_ingredient == "caffeine"]
            
            if caffeine_recs:
                rec = caffeine_recs[0]
                assert rec.suggested_value <= max_expected
    
    def test_theanine_ratio_recommendation(self):
        """L-theanine recommendation maintains proper caffeine ratio."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Caffeine Only",
            ingredients=[
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.25,
                "pct_sleep_disruption": 0.15,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        additions = report.get_by_type(RecommendationType.ADDITION_SUGGESTION)
        theanine_recs = [r for r in additions if "theanine" in r.target_ingredient.lower()]
        
        if theanine_recs:
            rec = theanine_recs[0]
            # Common ratios: 1:1 to 1:2 caffeine:theanine
            assert 100 <= rec.suggested_value <= 400


class TestTimingRecommendations:
    """Tests for timing optimization recommendations."""
    
    def test_late_intake_triggers_earlier_timing(self):
        """Late caffeine intake triggers earlier timing recommendation."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Afternoon Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 150, "unit": "mg"},
            ]
        )
        
        # Test late afternoon intake (4 PM)
        results = MockPopulationResult(
            formulation=formulation,
            intake_time_minutes=960,  # 16:00
            risk_analysis={
                "pct_jitter_risk": 0.10,
                "pct_sleep_disruption": 0.30,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        timing_recs = report.get_by_type(RecommendationType.TIMING_OPTIMIZATION)
        assert len(timing_recs) > 0
        
        # Should recommend earlier time
        rec = timing_recs[0]
        assert "before" in rec.description.lower() or "earlier" in rec.description.lower()
    
    def test_morning_intake_no_timing_change(self):
        """Morning intake doesn't trigger timing change for sleep."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Morning Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 150, "unit": "mg"},
            ]
        )
        
        # Morning intake (7 AM)
        results = MockPopulationResult(
            formulation=formulation,
            intake_time_minutes=420,
            risk_analysis={
                "pct_jitter_risk": 0.10,
                "pct_sleep_disruption": 0.08,  # Low sleep risk
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should not have sleep-related timing recommendations
        timing_recs = report.get_by_type(RecommendationType.TIMING_OPTIMIZATION)
        sleep_timing = [r for r in timing_recs if "sleep" in r.description.lower()]
        assert len(sleep_timing) == 0


class TestLabelWarnings:
    """Tests for label warning recommendations."""
    
    def test_caffeine_sensitivity_warning(self):
        """High jitter generates caffeine sensitivity warning."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="High Stimulant",
            ingredients=[
                {"compound_id": "caffeine", "amount": 350, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.40,
                "pct_sleep_disruption": 0.30,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        warnings = report.get_by_type(RecommendationType.LABEL_WARNING)
        assert len(warnings) > 0
        
        # Should include specific warning text
        has_sensitivity_warning = any(
            "sensitive" in (w.warning_text or "").lower() or
            "caffeine" in (w.warning_text or "").lower()
            for w in warnings
        )
        assert has_sensitivity_warning
    
    def test_timing_warning_for_sleep(self):
        """High sleep risk generates timing warning for label."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Pre-Workout",
            ingredients=[
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.15,
                "pct_sleep_disruption": 0.35,  # High
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        warnings = report.get_by_type(RecommendationType.LABEL_WARNING)
        
        has_timing_warning = any(
            "evening" in (w.warning_text or "").lower() or
            "bedtime" in (w.warning_text or "").lower() or
            "sleep" in (w.warning_text or "").lower()
            for w in warnings
        )
        assert has_timing_warning


class TestPriorityScoring:
    """Tests for recommendation priority calculation."""
    
    def test_higher_risk_higher_priority(self):
        """Higher risk issues get higher priority (lower number)."""
        engine = RecommendationEngine()
        
        # High risk product
        formulation = MockFormulation(
            name="High Risk Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 400, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.50,  # Very high
                "pct_sleep_disruption": 0.40,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should have priority 1 recommendations
        has_priority_1 = any(r.priority == 1 for r in report.recommendations)
        assert has_priority_1
    
    def test_priority_ordering(self):
        """Recommendations are ordered by priority."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Mixed Risk Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 300, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.35,
                "pct_sleep_disruption": 0.25,
                "pct_hyperglycemia": 0.08,
                "pct_crash_risk": 0.10,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Verify recommendations have valid priorities
        for rec in report.recommendations:
            assert 1 <= rec.priority <= 5


class TestImprovementPotential:
    """Tests for overall improvement potential calculation."""
    
    def test_improvement_potential_range(self):
        """Improvement potential is between 0 and 1."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 250, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.30,
                "pct_sleep_disruption": 0.20,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        assert 0.0 <= report.overall_improvement_potential <= 1.0
    
    def test_low_risk_low_improvement_potential(self):
        """Low risk products have low improvement potential."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Well Optimized",
            ingredients=[
                {"compound_id": "caffeine", "amount": 100, "unit": "mg"},
                {"compound_id": "l_theanine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.05,
                "pct_sleep_disruption": 0.05,
                "pct_hyperglycemia": 0.03,
                "pct_crash_risk": 0.03,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Low improvement potential for already good product
        assert report.overall_improvement_potential < 0.3


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_formulation(self):
        """Engine handles empty formulation gracefully."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Empty Product",
            ingredients=[]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.0,
                "pct_sleep_disruption": 0.0,
                "pct_hyperglycemia": 0.0,
                "pct_crash_risk": 0.0,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        assert isinstance(report, RecommendationReport)
        assert report.total_recommendations >= 0
    
    def test_missing_risk_metrics(self):
        """Engine handles missing risk metrics gracefully."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.25,
                # Missing some metrics
            }
        )
        
        report = engine.analyze(results, formulation)
        
        assert isinstance(report, RecommendationReport)
    
    def test_extreme_caffeine_dose(self):
        """Engine handles extreme caffeine doses."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Extreme Caffeine",
            ingredients=[
                {"compound_id": "caffeine", "amount": 600, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.70,
                "pct_sleep_disruption": 0.60,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.15,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        # Should strongly recommend reduction
        adjustments = report.get_by_type(RecommendationType.INGREDIENT_ADJUSTMENT)
        caffeine_recs = [r for r in adjustments if r.target_ingredient == "caffeine"]
        
        assert len(caffeine_recs) > 0
        rec = caffeine_recs[0]
        assert rec.priority == 1  # Highest priority
        assert rec.suggested_value < 400  # Significant reduction


class TestRecommendationConfig:
    """Tests for RecommendationConfig customization."""
    
    def test_custom_thresholds(self):
        """Custom thresholds affect recommendation generation."""
        # Strict config - lower thresholds trigger more recommendations
        strict_config = RecommendationConfig(
            jitter_risk_threshold=0.10,  # Very strict
            sleep_risk_threshold=0.10,
            hyperglycemia_threshold=0.05,
            min_confidence=0.5
        )
        
        # Lenient config - higher thresholds
        lenient_config = RecommendationConfig(
            jitter_risk_threshold=0.40,
            sleep_risk_threshold=0.40,
            hyperglycemia_threshold=0.25,
            min_confidence=0.9
        )
        
        strict_engine = RecommendationEngine(config=strict_config)
        lenient_engine = RecommendationEngine(config=lenient_config)
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.20,  # Between strict and lenient thresholds
                "pct_sleep_disruption": 0.20,
                "pct_hyperglycemia": 0.10,
                "pct_crash_risk": 0.08,
            }
        )
        
        strict_report = strict_engine.analyze(results, formulation)
        lenient_report = lenient_engine.analyze(results, formulation)
        
        # Strict config should generate more recommendations
        assert strict_report.total_recommendations >= lenient_report.total_recommendations


class TestKeyIssuesIdentification:
    """Tests for key issues identification."""
    
    def test_key_issues_reflect_high_risks(self):
        """Key issues list reflects the highest risk areas."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="High Jitter Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 350, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.45,  # Primary issue
                "pct_sleep_disruption": 0.30,  # Secondary issue
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        
        assert len(report.key_issues_identified) > 0
        
        # Should mention jitter or caffeine
        issues_text = " ".join(report.key_issues_identified).lower()
        assert "jitter" in issues_text or "caffeine" in issues_text


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_generate_recommendations_function(self):
        """generate_recommendations() convenience function works."""
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 250, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.30,
                "pct_sleep_disruption": 0.20,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = generate_recommendations(results, formulation)
        
        assert isinstance(report, RecommendationReport)
    
    def test_format_recommendations_text(self):
        """format_recommendations_text() produces readable output."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 300, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.35,
                "pct_sleep_disruption": 0.25,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        text = format_recommendations_text(report)
        
        assert "Test Product" in text
        assert "RECOMMENDATIONS" in text


class TestReportSerialization:
    """Tests for report serialization."""
    
    def test_to_dict_method(self):
        """RecommendationReport.to_dict() works correctly."""
        engine = RecommendationEngine()
        
        formulation = MockFormulation(
            name="Test Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 300, "unit": "mg"},
            ]
        )
        
        results = MockPopulationResult(
            formulation=formulation,
            risk_analysis={
                "pct_jitter_risk": 0.35,
                "pct_sleep_disruption": 0.25,
                "pct_hyperglycemia": 0.05,
                "pct_crash_risk": 0.05,
            }
        )
        
        report = engine.analyze(results, formulation)
        data = report.to_dict()
        
        assert "formulation_name" in data
        assert "recommendations" in data
        assert "overall_improvement_potential" in data
        assert "key_issues_identified" in data
        assert data["formulation_name"] == "Test Product"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
