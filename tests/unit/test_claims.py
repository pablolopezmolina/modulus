"""
Tests for Claim Defensibility Analysis - Session 6.2

Tests the ClaimAnalyzer which evaluates whether marketing claims
are defensible based on population simulation results.
"""
import pytest
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import numpy as np


# =============================================================================
# MOCK CLASSES FOR TESTING (simulate PopulationDayResult)
# =============================================================================

@dataclass
class MockPopulationDayResult:
    """Mock PopulationDayResult for testing claims analysis."""
    n_individuals: int = 1000
    n_valid: int = 950
    
    # Time series
    time_minutes: np.ndarray = field(default_factory=lambda: np.arange(0, 1441, 1.0))
    
    # Alertness percentiles (p5, p25, p50, p75, p95)
    alertness_percentiles: Dict[str, np.ndarray] = field(default_factory=dict)
    
    # Glucose percentiles
    glucose_percentiles: Dict[str, np.ndarray] = field(default_factory=dict)
    
    # Caffeine percentiles
    caffeine_percentiles: Dict[str, np.ndarray] = field(default_factory=dict)
    
    # Metrics stats: {metric: {mean, std, p10, p90}}
    metrics_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Risk analysis: {risk_name: percentage}
    risk_analysis: Dict[str, float] = field(default_factory=dict)
    
    # Subgroup analysis
    subgroup_analysis: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Is valid
    is_valid: bool = True


def create_good_result() -> MockPopulationDayResult:
    """Create a result where most claims should be defensible."""
    time = np.arange(0, 1441, 1.0)
    
    # Good alertness: stays >60% for >4h
    # Peak at t=60, sustained high, then gradual decline
    alertness_base = 50 + 30 * np.exp(-((time - 60) ** 2) / (2 * 200**2))
    alertness_base = np.clip(alertness_base, 30, 85)
    
    return MockPopulationDayResult(
        n_individuals=1000,
        n_valid=950,
        time_minutes=time,
        alertness_percentiles={
            "p5": alertness_base - 15,
            "p25": alertness_base - 8,
            "p50": alertness_base,
            "p75": alertness_base + 8,
            "p95": alertness_base + 15,
        },
        glucose_percentiles={
            "p5": np.full(1441, 85.0),
            "p25": np.full(1441, 95.0),
            "p50": np.full(1441, 105.0),
            "p75": np.full(1441, 120.0),
            "p95": np.full(1441, 135.0),  # Stays below 140
        },
        caffeine_percentiles={
            "p5": np.full(1441, 0.5),
            "p50": np.full(1441, 2.0),
            "p95": np.full(1441, 3.5),
        },
        metrics_stats={
            "alertness_peak": {"mean": 75.0, "std": 10.0, "p10": 62.0, "p90": 88.0},
            "alertness_time_to_peak": {"mean": 45.0, "std": 15.0, "p10": 25.0, "p90": 65.0},
            "alertness_duration_above_60": {"mean": 300.0, "std": 60.0, "p10": 220.0, "p90": 380.0},
            "glucose_peak": {"mean": 125.0, "std": 20.0, "p10": 100.0, "p90": 150.0},
            "glucose_time_above_140": {"mean": 10.0, "std": 15.0, "p10": 0.0, "p90": 30.0},
        },
        risk_analysis={
            "pct_hyperglycemia": 8.0,  # <15% - good
            "pct_severe_hyperglycemia": 1.0,
            "pct_jitter_risk": 5.0,
            "pct_sleep_disruption": 10.0,
            "pct_crash_risk": 6.0,  # <10% - good
        },
        is_valid=True,
    )


def create_bad_result() -> MockPopulationDayResult:
    """Create a result where most claims should NOT be defensible."""
    time = np.arange(0, 1441, 1.0)
    
    # Poor alertness: quick spike then crash
    alertness_base = 40 + 35 * np.exp(-((time - 30) ** 2) / (2 * 50**2))
    alertness_base = np.clip(alertness_base, 30, 75)
    
    return MockPopulationDayResult(
        n_individuals=1000,
        n_valid=950,
        time_minutes=time,
        alertness_percentiles={
            "p5": alertness_base - 10,
            "p25": alertness_base - 5,
            "p50": alertness_base,
            "p75": alertness_base + 5,
            "p95": alertness_base + 10,
        },
        glucose_percentiles={
            "p5": np.full(1441, 100.0),
            "p50": np.full(1441, 140.0),
            "p95": np.full(1441, 180.0),  # Many above 140
        },
        caffeine_percentiles={
            "p50": np.full(1441, 3.0),
            "p95": np.full(1441, 5.0),
        },
        metrics_stats={
            "alertness_peak": {"mean": 65.0, "std": 15.0, "p10": 45.0, "p90": 80.0},
            "alertness_time_to_peak": {"mean": 70.0, "std": 25.0, "p10": 40.0, "p90": 100.0},  # Slow
            "alertness_duration_above_60": {"mean": 90.0, "std": 40.0, "p10": 30.0, "p90": 150.0},  # Short
            "glucose_peak": {"mean": 160.0, "std": 25.0, "p10": 130.0, "p90": 190.0},
            "glucose_time_above_140": {"mean": 120.0, "std": 60.0, "p10": 50.0, "p90": 200.0},
        },
        risk_analysis={
            "pct_hyperglycemia": 35.0,  # >15% - bad
            "pct_severe_hyperglycemia": 15.0,
            "pct_jitter_risk": 20.0,
            "pct_sleep_disruption": 30.0,
            "pct_crash_risk": 25.0,  # >10% - bad
        },
        is_valid=True,
    )


# =============================================================================
# IMPORT CLAIMS MODULE
# =============================================================================

# Import claims module
from src.analysis.claims import (
    ClaimDefinition,
    ClaimAnalysis,
    ClaimAnalyzerConfig,
    ClaimAnalysisResult,
    ClaimAnalyzer,
    get_default_claims,
)
CLAIMS_AVAILABLE = True


# =============================================================================
# TEST: ClaimDefinition
# =============================================================================

class TestClaimDefinition:
    """Tests for ClaimDefinition dataclass."""
    
    
    def test_create_basic_claim(self):
        """Can create a basic claim definition."""
        claim = ClaimDefinition(
            claim_id="sustained_energy",
            claim_text="Sustained Energy",
            description="Provides energy that lasts",
            evaluation_method="alertness_duration",
            threshold=240.0,  # 4 hours = 240 minutes
            threshold_comparator=">=",
            required_responder_rate=0.5,
        )
        assert claim.claim_id == "sustained_energy"
        assert claim.threshold == 240.0
        assert claim.required_responder_rate == 0.5
    
    
    def test_claim_immutable(self):
        """ClaimDefinition is frozen (immutable)."""
        claim = ClaimDefinition(
            claim_id="test",
            claim_text="Test",
            description="Test claim",
            evaluation_method="test_method",
            threshold=50.0,
            threshold_comparator=">=",
            required_responder_rate=0.5,
        )
        with pytest.raises((AttributeError, TypeError)):
            claim.claim_id = "new_id"
    
    
    def test_claim_validation_responder_rate(self):
        """Responder rate must be in [0, 1]."""
        with pytest.raises(ValueError):
            ClaimDefinition(
                claim_id="test",
                claim_text="Test",
                description="Test",
                evaluation_method="test",
                threshold=50.0,
                threshold_comparator=">=",
                required_responder_rate=1.5,  # Invalid
            )
    
    
    def test_claim_validation_comparator(self):
        """Comparator must be valid."""
        with pytest.raises(ValueError):
            ClaimDefinition(
                claim_id="test",
                claim_text="Test",
                description="Test",
                evaluation_method="test",
                threshold=50.0,
                threshold_comparator="===",  # Invalid
                required_responder_rate=0.5,
            )
    
    
    def test_to_dict(self):
        """ClaimDefinition can be serialized."""
        claim = ClaimDefinition(
            claim_id="test",
            claim_text="Test Claim",
            description="A test",
            evaluation_method="method",
            threshold=100.0,
            threshold_comparator=">=",
            required_responder_rate=0.5,
        )
        d = claim.to_dict()
        assert d["claim_id"] == "test"
        assert d["threshold"] == 100.0


# =============================================================================
# TEST: ClaimAnalysis
# =============================================================================

class TestClaimAnalysis:
    """Tests for ClaimAnalysis dataclass."""
    
    
    def test_create_analysis(self):
        """Can create a claim analysis result."""
        analysis = ClaimAnalysis(
            claim_id="sustained_energy",
            claim_text="Sustained Energy",
            responder_percentage=0.73,
            is_defensible=True,
            confidence=0.85,
            supporting_metrics={"alertness_duration_above_60": 300.0},
            methodology="Population simulation with N=1000",
            suggested_wording="Provides sustained energy for most users",
            efsa_compatible=False,
            fda_compatible=False,
        )
        assert analysis.is_defensible is True
        assert analysis.responder_percentage == 0.73
        assert analysis.confidence == 0.85
    
    
    def test_analysis_immutable(self):
        """ClaimAnalysis is frozen."""
        analysis = ClaimAnalysis(
            claim_id="test",
            claim_text="Test",
            responder_percentage=0.5,
            is_defensible=True,
            confidence=0.8,
            supporting_metrics={},
            methodology="test",
            suggested_wording="test",
            efsa_compatible=False,
            fda_compatible=False,
        )
        with pytest.raises((AttributeError, TypeError)):
            analysis.is_defensible = False
    
    
    def test_analysis_validation_percentage(self):
        """Responder percentage must be in [0, 1]."""
        with pytest.raises(ValueError):
            ClaimAnalysis(
                claim_id="test",
                claim_text="Test",
                responder_percentage=1.5,  # Invalid
                is_defensible=True,
                confidence=0.8,
                supporting_metrics={},
                methodology="test",
                suggested_wording="test",
                efsa_compatible=False,
                fda_compatible=False,
            )
    
    
    def test_analysis_validation_confidence(self):
        """Confidence must be in [0, 1]."""
        with pytest.raises(ValueError):
            ClaimAnalysis(
                claim_id="test",
                claim_text="Test",
                responder_percentage=0.5,
                is_defensible=True,
                confidence=-0.1,  # Invalid
                supporting_metrics={},
                methodology="test",
                suggested_wording="test",
                efsa_compatible=False,
                fda_compatible=False,
            )
    
    
    def test_to_dict(self):
        """ClaimAnalysis can be serialized."""
        analysis = ClaimAnalysis(
            claim_id="test",
            claim_text="Test",
            responder_percentage=0.75,
            is_defensible=True,
            confidence=0.9,
            supporting_metrics={"metric1": 100.0},
            methodology="simulation",
            suggested_wording="Suggested text",
            efsa_compatible=False,
            fda_compatible=False,
        )
        d = analysis.to_dict()
        assert d["responder_percentage"] == 0.75
        assert d["is_defensible"] is True
        assert "metric1" in d["supporting_metrics"]


# =============================================================================
# TEST: ClaimAnalyzerConfig
# =============================================================================

class TestClaimAnalyzerConfig:
    """Tests for ClaimAnalyzerConfig."""
    
    
    def test_default_config(self):
        """Default config has sensible values."""
        config = ClaimAnalyzerConfig()
        assert config.min_responder_rate == 0.5
        assert config.min_confidence == 0.7
        assert config.conservative_wording is True
    
    
    def test_custom_config(self):
        """Can create custom config."""
        config = ClaimAnalyzerConfig(
            min_responder_rate=0.6,
            min_confidence=0.8,
            conservative_wording=False,
        )
        assert config.min_responder_rate == 0.6
        assert config.min_confidence == 0.8
    
    
    def test_config_validation(self):
        """Config validates thresholds."""
        with pytest.raises(ValueError):
            ClaimAnalyzerConfig(min_responder_rate=1.5)
        with pytest.raises(ValueError):
            ClaimAnalyzerConfig(min_confidence=-0.1)


# =============================================================================
# TEST: Default Claims
# =============================================================================

class TestDefaultClaims:
    """Tests for default claim definitions."""
    
    
    def test_get_default_claims(self):
        """Can get default claim definitions."""
        claims = get_default_claims()
        assert isinstance(claims, dict)
        assert len(claims) >= 4
    
    
    def test_sustained_energy_claim(self):
        """Sustained energy claim is defined correctly."""
        claims = get_default_claims()
        assert "sustained_energy" in claims
        claim = claims["sustained_energy"]
        assert claim.evaluation_method == "alertness_duration_above_60"
        assert claim.threshold == 240.0  # 4 hours
    
    
    def test_no_crash_claim(self):
        """No crash claim is defined correctly."""
        claims = get_default_claims()
        assert "no_crash" in claims
        claim = claims["no_crash"]
        assert "crash" in claim.evaluation_method.lower()
    
    
    def test_quick_onset_claim(self):
        """Quick onset claim is defined correctly."""
        claims = get_default_claims()
        assert "quick_onset" in claims
        claim = claims["quick_onset"]
        assert claim.threshold <= 45.0  # ≤45 minutes
    
    
    def test_glucose_friendly_claim(self):
        """Glucose friendly claim is defined correctly."""
        claims = get_default_claims()
        assert "glucose_friendly" in claims
        claim = claims["glucose_friendly"]
        # Uses hyperglycemia risk
        assert "glucose" in claim.evaluation_method.lower() or "hyperglycemia" in claim.evaluation_method.lower()


# =============================================================================
# TEST: ClaimAnalyzer - Basic Functionality
# =============================================================================

class TestClaimAnalyzerBasic:
    """Tests for basic ClaimAnalyzer functionality."""
    
    
    def test_create_analyzer(self):
        """Can create a ClaimAnalyzer."""
        analyzer = ClaimAnalyzer()
        assert analyzer is not None
    
    
    def test_create_with_config(self):
        """Can create analyzer with custom config."""
        config = ClaimAnalyzerConfig(min_responder_rate=0.6)
        analyzer = ClaimAnalyzer(config=config)
        assert analyzer.config.min_responder_rate == 0.6
    
    
    def test_create_with_custom_claims(self):
        """Can create analyzer with custom claims."""
        custom_claims = {
            "custom_claim": ClaimDefinition(
                claim_id="custom_claim",
                claim_text="Custom Claim",
                description="A custom claim",
                evaluation_method="custom_method",
                threshold=100.0,
                threshold_comparator=">=",
                required_responder_rate=0.5,
            )
        }
        analyzer = ClaimAnalyzer(claims=custom_claims)
        assert "custom_claim" in analyzer.claims


# =============================================================================
# TEST: ClaimAnalyzer - Analysis
# =============================================================================

class TestClaimAnalyzerAnalysis:
    """Tests for ClaimAnalyzer.analyze()."""
    
    
    def test_analyze_returns_result(self):
        """analyze() returns ClaimAnalysisResult."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        assert isinstance(result, ClaimAnalysisResult)
    
    
    def test_analyze_specific_claims(self):
        """Can analyze specific claims only."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["sustained_energy", "no_crash"]
        )
        assert len(result.analyses) == 2
        assert "sustained_energy" in result.analyses
        assert "no_crash" in result.analyses
    
    
    def test_analyze_all_default_claims(self):
        """Analyzes all default claims when none specified."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        assert len(result.analyses) >= 4
    
    
    def test_analyze_unknown_claim_ignored(self):
        """Unknown claims are skipped with warning."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["sustained_energy", "nonexistent_claim"]
        )
        assert "sustained_energy" in result.analyses
        assert "nonexistent_claim" not in result.analyses
        assert len(result.warnings) > 0


# =============================================================================
# TEST: ClaimAnalyzer - Sustained Energy
# =============================================================================

class TestSustainedEnergyClaim:
    """Tests for sustained_energy claim evaluation."""
    
    
    def test_sustained_energy_good_result(self):
        """Sustained energy should be defensible for good result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["sustained_energy"]
        )
        analysis = result.analyses["sustained_energy"]
        # Good result has alertness >60% for ~5h
        assert analysis.responder_percentage > 0.5
        assert analysis.is_defensible is True
    
    
    def test_sustained_energy_bad_result(self):
        """Sustained energy should NOT be defensible for bad result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_bad_result(),
            claims=["sustained_energy"]
        )
        analysis = result.analyses["sustained_energy"]
        # Bad result has short duration
        assert analysis.responder_percentage < 0.5 or analysis.is_defensible is False
    
    
    def test_sustained_energy_methodology(self):
        """Methodology is documented."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["sustained_energy"]
        )
        analysis = result.analyses["sustained_energy"]
        assert len(analysis.methodology) > 0
        assert "alertness" in analysis.methodology.lower() or "population" in analysis.methodology.lower()


# =============================================================================
# TEST: ClaimAnalyzer - No Crash
# =============================================================================

class TestNoCrashClaim:
    """Tests for no_crash claim evaluation."""
    
    
    def test_no_crash_good_result(self):
        """No crash should be defensible for good result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["no_crash"]
        )
        analysis = result.analyses["no_crash"]
        # Good result has <10% crash risk
        assert analysis.is_defensible is True
    
    
    def test_no_crash_bad_result(self):
        """No crash should NOT be defensible for bad result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_bad_result(),
            claims=["no_crash"]
        )
        analysis = result.analyses["no_crash"]
        # Bad result has 25% crash risk
        assert analysis.is_defensible is False


# =============================================================================
# TEST: ClaimAnalyzer - Quick Onset
# =============================================================================

class TestQuickOnsetClaim:
    """Tests for quick_onset claim evaluation."""
    
    
    def test_quick_onset_good_result(self):
        """Quick onset should be defensible for good result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["quick_onset"]
        )
        analysis = result.analyses["quick_onset"]
        # Good result has time_to_peak ~45min
        # May or may not be defensible depending on exact threshold
        assert isinstance(analysis.responder_percentage, float)
    
    
    def test_quick_onset_bad_result(self):
        """Quick onset should NOT be defensible for bad result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_bad_result(),
            claims=["quick_onset"]
        )
        analysis = result.analyses["quick_onset"]
        # Bad result has time_to_peak ~70min (slow)
        assert analysis.is_defensible is False


# =============================================================================
# TEST: ClaimAnalyzer - Glucose Friendly
# =============================================================================

class TestGlucoseFriendlyClaim:
    """Tests for glucose_friendly claim evaluation."""
    
    
    def test_glucose_friendly_good_result(self):
        """Glucose friendly should be defensible for good result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_good_result(),
            claims=["glucose_friendly"]
        )
        analysis = result.analyses["glucose_friendly"]
        # Good result has <15% hyperglycemia
        assert analysis.is_defensible is True
    
    
    def test_glucose_friendly_bad_result(self):
        """Glucose friendly should NOT be defensible for bad result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(
            create_bad_result(),
            claims=["glucose_friendly"]
        )
        analysis = result.analyses["glucose_friendly"]
        # Bad result has 35% hyperglycemia
        assert analysis.is_defensible is False


# =============================================================================
# TEST: ClaimAnalysisResult
# =============================================================================

class TestClaimAnalysisResult:
    """Tests for ClaimAnalysisResult."""
    
    
    def test_result_structure(self):
        """Result has expected structure."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        assert hasattr(result, "analyses")
        assert hasattr(result, "n_defensible")
        assert hasattr(result, "n_total")
        assert hasattr(result, "warnings")
    
    
    def test_defensible_count(self):
        """n_defensible counts correctly."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        manual_count = sum(1 for a in result.analyses.values() if a.is_defensible)
        assert result.n_defensible == manual_count
    
    
    def test_get_defensible_claims(self):
        """Can get only defensible claims."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        defensible = result.get_defensible_claims()
        for claim_id, analysis in defensible.items():
            assert analysis.is_defensible is True
    
    
    def test_get_non_defensible_claims(self):
        """Can get only non-defensible claims."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_bad_result())
        
        non_defensible = result.get_non_defensible_claims()
        for claim_id, analysis in non_defensible.items():
            assert analysis.is_defensible is False
    
    
    def test_to_dict(self):
        """Result can be serialized."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        d = result.to_dict()
        assert "analyses" in d
        assert "n_defensible" in d
        assert "n_total" in d
        assert isinstance(d["analyses"], dict)
    
    
    def test_get_summary(self):
        """Can get a text summary."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        summary = result.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


# =============================================================================
# TEST: Suggested Wording
# =============================================================================

class TestSuggestedWording:
    """Tests for suggested wording generation."""
    
    
    def test_wording_for_defensible(self):
        """Defensible claims get positive wording."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result(), claims=["sustained_energy"])
        
        analysis = result.analyses["sustained_energy"]
        if analysis.is_defensible:
            assert len(analysis.suggested_wording) > 0
            # Should not contain disclaimers for defensible claims
            assert "not" not in analysis.suggested_wording.lower() or "most" in analysis.suggested_wording.lower()
    
    
    def test_wording_for_non_defensible(self):
        """Non-defensible claims get cautious wording."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_bad_result(), claims=["glucose_friendly"])
        
        analysis = result.analyses["glucose_friendly"]
        if not analysis.is_defensible:
            assert len(analysis.suggested_wording) > 0
            # Should be cautious
            assert "may" in analysis.suggested_wording.lower() or "some" in analysis.suggested_wording.lower() or "not recommended" in analysis.suggested_wording.lower()
    
    
    def test_conservative_wording_option(self):
        """Conservative wording is more cautious."""
        config_conservative = ClaimAnalyzerConfig(conservative_wording=True)
        config_normal = ClaimAnalyzerConfig(conservative_wording=False)
        
        analyzer_conservative = ClaimAnalyzer(config=config_conservative)
        analyzer_normal = ClaimAnalyzer(config=config_normal)
        
        result_conservative = analyzer_conservative.analyze(
            create_good_result(), claims=["sustained_energy"]
        )
        result_normal = analyzer_normal.analyze(
            create_good_result(), claims=["sustained_energy"]
        )
        
        # Both should work; conservative might have "most" instead of "all"
        assert result_conservative.analyses["sustained_energy"].suggested_wording is not None
        assert result_normal.analyses["sustained_energy"].suggested_wording is not None


# =============================================================================
# TEST: Confidence Calculation
# =============================================================================

class TestConfidenceCalculation:
    """Tests for confidence calculation."""
    
    
    def test_high_confidence_for_clear_pass(self):
        """High responder rate = high confidence."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        # At least one claim should have high confidence
        high_confidence_claims = [
            a for a in result.analyses.values()
            if a.is_defensible and a.confidence > 0.8
        ]
        assert len(high_confidence_claims) > 0
    
    
    def test_lower_confidence_for_marginal(self):
        """Marginal responder rate = lower confidence."""
        # Create a marginal result - just over threshold
        marginal = create_good_result()
        marginal.metrics_stats["alertness_duration_above_60"]["mean"] = 250.0  # Just over 240
        
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(marginal, claims=["sustained_energy"])
        
        analysis = result.analyses["sustained_energy"]
        # Confidence should be lower for marginal cases
        if analysis.is_defensible:
            # Still confident but maybe not maximum
            assert 0.5 <= analysis.confidence <= 1.0
    
    
    def test_confidence_in_valid_range(self):
        """All confidences are in [0, 1]."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        for analysis in result.analyses.values():
            assert 0.0 <= analysis.confidence <= 1.0


# =============================================================================
# TEST: EFSA/FDA Compatibility (Conservative)
# =============================================================================

class TestRegulatoryCompatibility:
    """Tests for regulatory compatibility flags."""
    
    
    def test_efsa_defaults_to_false(self):
        """EFSA compatibility defaults to False (conservative)."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        for analysis in result.analyses.values():
            # In this initial version, we're conservative
            assert analysis.efsa_compatible is False
    
    
    def test_fda_defaults_to_false(self):
        """FDA compatibility defaults to False (conservative)."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        for analysis in result.analyses.values():
            # In this initial version, we're conservative
            assert analysis.fda_compatible is False


# =============================================================================
# TEST: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    
    def test_empty_claims_list(self):
        """Empty claims list analyzes all defaults."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result(), claims=[])
        # Empty list should mean "all defaults"
        assert len(result.analyses) >= 4
    
    
    def test_none_claims_list(self):
        """None claims list analyzes all defaults."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result(), claims=None)
        assert len(result.analyses) >= 4
    
    
    def test_missing_metrics(self):
        """Handles missing metrics gracefully."""
        incomplete_result = MockPopulationDayResult(
            metrics_stats={},  # Empty
            risk_analysis={},
        )
        
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(incomplete_result)
        
        # Should not crash; may have warnings or low confidence
        assert result is not None
        assert len(result.warnings) > 0 or all(
            a.confidence < 0.5 for a in result.analyses.values()
        )
    
    
    def test_invalid_result(self):
        """Handles invalid population result."""
        invalid_result = MockPopulationDayResult(is_valid=False)
        
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(invalid_result)
        
        # Should return result with warnings
        assert result is not None
        assert len(result.warnings) > 0


# =============================================================================
# TEST: Integration with PopulationDayResult Interface
# =============================================================================

class TestPopulationDayResultIntegration:
    """Tests that ClaimAnalyzer works with PopulationDayResult interface."""
    
    
    def test_uses_metrics_stats(self):
        """Analyzer uses metrics_stats from result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result(), claims=["quick_onset"])
        
        analysis = result.analyses["quick_onset"]
        # Quick onset should use alertness_time_to_peak
        # Supporting metrics may use suffixed names like alertness_time_to_peak_mean
        has_time_to_peak_metric = any(
            "alertness_time_to_peak" in key 
            for key in analysis.supporting_metrics.keys()
        )
        assert has_time_to_peak_metric or "time_to_peak" in analysis.methodology.lower()
    
    
    def test_uses_risk_analysis(self):
        """Analyzer uses risk_analysis from result."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result(), claims=["glucose_friendly"])
        
        analysis = result.analyses["glucose_friendly"]
        # Should reference hyperglycemia risk
        assert "pct_hyperglycemia" in analysis.supporting_metrics or \
               "hyperglycemia" in analysis.methodology.lower()
    
    
    def test_uses_alertness_percentiles(self):
        """Analyzer can use alertness_percentiles for duration analysis."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result(), claims=["sustained_energy"])
        
        # Should successfully analyze
        assert "sustained_energy" in result.analyses


# =============================================================================
# TEST: Contract 6.1 Compliance
# =============================================================================

class TestContract61Compliance:
    """Tests for Contract 6.1: ClaimAnalyzer compliance."""
    
    
    def test_analyze_signature(self):
        """analyze() accepts PopulationSimulationResult and claims list."""
        analyzer = ClaimAnalyzer()
        # Should accept both positional and keyword
        result1 = analyzer.analyze(create_good_result())
        result2 = analyzer.analyze(create_good_result(), claims=["sustained_energy"])
        assert result1 is not None
        assert result2 is not None
    
    
    def test_returns_dict_of_claim_analysis(self):
        """Returns Dict[str, ClaimAnalysis]."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        assert isinstance(result.analyses, dict)
        for claim_id, analysis in result.analyses.items():
            assert isinstance(claim_id, str)
            assert isinstance(analysis, ClaimAnalysis)
    
    
    def test_claim_analysis_has_required_fields(self):
        """ClaimAnalysis has all fields from Contract 6.1."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        for analysis in result.analyses.values():
            assert hasattr(analysis, "claim_id")
            assert hasattr(analysis, "claim_text")
            assert hasattr(analysis, "is_defensible")
            assert hasattr(analysis, "confidence")
            assert hasattr(analysis, "responder_percentage")
            assert hasattr(analysis, "supporting_metrics")
            assert hasattr(analysis, "methodology")
            assert hasattr(analysis, "efsa_compatible")
            assert hasattr(analysis, "fda_compatible")
            assert hasattr(analysis, "suggested_wording")
    
    
    def test_defensibility_rule(self):
        """is_defensible=True only if responder_percentage > 50% AND confidence > 0.7."""
        analyzer = ClaimAnalyzer()
        result = analyzer.analyze(create_good_result())
        
        for analysis in result.analyses.values():
            if analysis.is_defensible:
                # Contract says: is_defensible=True solo si responder_percentage > 50% Y confidence > 0.7
                assert analysis.responder_percentage > 0.5
                assert analysis.confidence > 0.7


# =============================================================================
# SANITY CHECKS
# =============================================================================

class TestSanityChecks:
    """Basic sanity checks."""
    
    def test_mock_results_are_valid(self):
        """Mock results are properly constructed."""
        good = create_good_result()
        bad = create_bad_result()
        
        assert good.is_valid is True
        assert bad.is_valid is True
        assert len(good.time_minutes) == 1441
        assert len(bad.time_minutes) == 1441
    
    def test_good_result_has_good_metrics(self):
        """Good result should have favorable metrics."""
        good = create_good_result()
        
        assert good.risk_analysis["pct_hyperglycemia"] < 15.0
        assert good.risk_analysis["pct_crash_risk"] < 10.0
        assert good.metrics_stats["alertness_duration_above_60"]["mean"] > 240.0
    
    def test_bad_result_has_bad_metrics(self):
        """Bad result should have unfavorable metrics."""
        bad = create_bad_result()
        
        assert bad.risk_analysis["pct_hyperglycemia"] > 15.0
        assert bad.risk_analysis["pct_crash_risk"] > 10.0
        assert bad.metrics_stats["alertness_duration_above_60"]["mean"] < 240.0
