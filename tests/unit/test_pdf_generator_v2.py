"""
Tests for PDF Generator v2 Enterprise
Session 11.1 - Pack 2 (€150-250k)
"""
import pytest
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import tempfile
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from reporting.pdf_generator_v2 import PDFGeneratorV2, PDFv2Config, PDFv2Result


# =============================================================================
# MOCK DATA STRUCTURES
# =============================================================================

@dataclass
class MockPopulationResult:
    """Mock PopulationSimulationResult for testing."""
    n_individuals: int = 1000
    n_valid: int = 985
    time_minutes: List[float] = field(default_factory=lambda: list(range(0, 1441, 10)))
    glucose_percentiles: Dict[str, List[float]] = field(default_factory=dict)
    caffeine_percentiles: Dict[str, List[float]] = field(default_factory=dict)
    alertness_percentiles: Dict[str, List[float]] = field(default_factory=dict)
    metrics_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    risk_analysis: Dict[str, float] = field(default_factory=dict)
    subgroup_analysis: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        n_points = len(self.time_minutes)
        if not self.glucose_percentiles:
            self.glucose_percentiles = {
                "p5": [85.0] * n_points, "p25": [90.0] * n_points, "p50": [95.0] * n_points,
                "p75": [105.0] * n_points, "p95": [120.0] * n_points
            }
        if not self.caffeine_percentiles:
            self.caffeine_percentiles = {
                "p5": [0.5] * n_points, "p25": [1.0] * n_points, "p50": [1.5] * n_points,
                "p75": [2.0] * n_points, "p95": [3.0] * n_points
            }
        if not self.alertness_percentiles:
            self.alertness_percentiles = {
                "p5": [40.0] * n_points, "p25": [55.0] * n_points, "p50": [70.0] * n_points,
                "p75": [80.0] * n_points, "p95": [90.0] * n_points
            }
        if not self.metrics_stats:
            self.metrics_stats = {
                "glucose_peak": {"mean": 145.0, "std": 15.0, "p10": 125.0, "p50": 145.0, "p90": 165.0},
            }
        if not self.risk_analysis:
            self.risk_analysis = {"pct_hyperglycemia": 12.5, "pct_sleep_disruption": 18.0}
        if not self.subgroup_analysis:
            self.subgroup_analysis = {
                "by_bmi": {"normal": {"n": 400, "pct_hyperglycemia": 8.0}, "obese": {"n": 250, "pct_hyperglycemia": 20.0}}
            }


@dataclass
class MockDecision:
    """Mock Decision for testing."""
    verdict: str = "CAUTION"
    confidence: float = 0.75
    summary: str = "Product shows promise but has elevated sleep disruption risk."
    top_risks: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.top_risks:
            self.top_risks = [
                {"risk_id": "sleep_disruption", "percentage": 18.0, "severity": "moderate"},
                {"risk_id": "hyperglycemia", "percentage": 12.5, "severity": "low"}
            ]


@dataclass
class MockClaimAnalysis:
    """Mock ClaimAnalysis for testing."""
    claim_id: str
    claim_text: str
    is_defensible: bool
    confidence: float
    responder_percentage: float
    methodology: str = "Population simulation N=1000"
    suggested_wording: str = ""


@dataclass
class MockFormulation:
    """Mock Formulation for testing."""
    name: str = "Energy Pro Max"
    product_id: str = "EPM-001"
    form: str = "capsule"
    serving_size: str = "2 capsules"
    ingredients: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.ingredients:
            self.ingredients = [
                {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
                {"compound_id": "l_theanine", "amount": 100, "unit": "mg"},
            ]


@dataclass
class MockFullRiskMap:
    """Mock FullRiskMap for testing."""
    segments: List[str] = field(default_factory=lambda: [
        "by_bmi", "by_age", "by_caffeine_sensitivity",
        "by_insulin_sensitivity", "by_activity_level", "by_habitual_caffeine"
    ])
    risk_types: List[str] = field(default_factory=lambda: ["hyperglycemia", "sleep_disruption", "jitter", "crash"])
    danger_zones: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.danger_zones:
            self.danger_zones = [
                {"segment": "by_caffeine_sensitivity:slow", "risk": "sleep_disruption", "percentage": 45.0},
                {"segment": "by_bmi:obese", "risk": "hyperglycemia", "percentage": 25.0}
            ]


@dataclass
class MockComparison:
    """Mock Comparison for testing."""
    product_a_name: str = "Energy Pro Max"
    product_b_name: str = "Energy Lite"
    overall_winner: str = "A"
    metric_comparisons: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.metric_comparisons:
            self.metric_comparisons = [
                {"metric": "alertness_peak", "a_value": 75.0, "b_value": 65.0, "delta": 10.0, "winner": "A"},
            ]


@dataclass
class MockEvidenceEntry:
    """Mock evidence entry."""
    param_name: str
    value: float
    source: str
    doi: Optional[str]
    confidence: str


@dataclass
class MockEvidenceRegistry:
    """Mock EvidenceRegistry for testing."""
    entries: List[MockEvidenceEntry] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.entries:
            self.entries = [
                MockEvidenceEntry("caffeine_half_life", 5.0, "Blanchard 1983", "10.1111/j.1365-2125.1983.tb01514.x", "high"),
                MockEvidenceEntry("theanine_effect", 0.5, "Owen 2008", "10.1080/09637480802228016", "medium"),
                MockEvidenceEntry("glucose_SI", 5.0e-4, "Dalla Man 2007", "10.1152/ajpendo.00319.2006", "high"),
            ]


@dataclass
class MockReproducibilityBundle:
    """Mock ReproducibilityBundle for testing."""
    bundle_id: str = "MODULUS-2025-ABC123"
    version: str = "3.0.0"
    timestamp: str = "2025-01-08T14:30:00Z"
    config_hash: str = "sha256:abc123def456"
    seed: int = 42


@dataclass
class MockCertificateInfo:
    """Mock CertificateInfo for testing."""
    certificate_id: str = "MODULUS-2025-001234"
    product_name: str = "Energy Pro Max"
    verdict: str = "CAUTION"
    issue_date: str = "2025-01-08"
    population_size: int = 1000


# =============================================================================
# TESTS
# =============================================================================

class TestPDFv2Config:
    """Tests for PDFv2Config."""
    
    def test_default_config(self):
        config = PDFv2Config(output_path="/tmp/test.pdf")
        assert config.include_toc is True
        assert config.include_evidence_appendix is True
        assert config.page_size == "letter"
    
    def test_custom_config(self):
        config = PDFv2Config(
            output_path="/tmp/test.pdf",
            product_name="Custom Product",
            include_evidence_appendix=False,
            page_size="A4"
        )
        assert config.product_name == "Custom Product"
        assert config.include_evidence_appendix is False
        assert config.page_size == "A4"
    
    def test_config_validation(self):
        with pytest.raises(ValueError):
            PDFv2Config(output_path="")


class TestPDFv2Structure:
    """Tests for PDF v2 document structure."""
    
    def test_pdf_v2_generates_without_error(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, product_name="Energy Pro Max")
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            assert result is not None
            assert result.page_count >= 20
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_pdf_v2_has_table_of_contents(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_toc=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            assert result.has_toc is True
            assert "Table of Contents" in result.sections
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_pdf_v2_required_sections(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            required = ["Cover Page", "Executive Summary", "Decision Page", "Risk Analysis"]
            for section in required:
                assert section in result.sections, f"Missing: {section}"
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_pdf_v2_with_all_optional_sections(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(
                output_path=output_path,
                include_comparison=True,
                include_evidence_appendix=True,
                include_certificate=True
            )
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                claims_analysis=[MockClaimAnalysis("energy", "Energy", True, 0.8, 73.0)],
                comparison=MockComparison(),
                evidence_registry=MockEvidenceRegistry(),
                reproducibility_bundle=MockReproducibilityBundle(),
                certificate_info=MockCertificateInfo()
            )
            assert result.page_count >= 40
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestRiskMapSection:
    """Tests for Full Risk Map section."""
    
    def test_risk_map_section_included(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                full_risk_map=MockFullRiskMap()
            )
            assert "Risk Analysis" in result.sections
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_danger_zones_highlighted(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                full_risk_map=MockFullRiskMap()
            )
            assert result.danger_zones_count >= 1
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestEvidenceAppendix:
    """Tests for Evidence Appendix section."""
    
    def test_evidence_appendix_included_when_enabled(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_evidence_appendix=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                evidence_registry=MockEvidenceRegistry()
            )
            assert "Evidence Appendix" in result.sections
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_evidence_appendix_lists_dois(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_evidence_appendix=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                evidence_registry=MockEvidenceRegistry()
            )
            assert result.doi_count >= 2
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestComparisonSection:
    """Tests for A/B Comparison section."""
    
    def test_comparison_included_when_provided(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_comparison=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                comparison=MockComparison()
            )
            assert "Product Comparison" in result.sections
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_comparison_shows_winner(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_comparison=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                comparison=MockComparison()
            )
            assert result.comparison_winner in ["A", "B", "TIE"]
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestCertificatePage:
    """Tests for Certificate page integration."""
    
    def test_certificate_included_when_enabled(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_certificate=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                certificate_info=MockCertificateInfo()
            )
            assert "Certificate" in result.sections
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_certificate_shows_verdict(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_certificate=True)
            generator = PDFGeneratorV2(config)
            cert_info = MockCertificateInfo()
            cert_info.verdict = "GO"
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                certificate_info=cert_info
            )
            assert result.certificate_verdict == "GO"
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestReproducibilityInfo:
    """Tests for Reproducibility Info section."""
    
    def test_reproducibility_included_when_enabled(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_reproducibility=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                reproducibility_bundle=MockReproducibilityBundle()
            )
            assert "Reproducibility" in result.sections
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_reproducibility_shows_hash(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, include_reproducibility=True)
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation(),
                reproducibility_bundle=MockReproducibilityBundle()
            )
            assert result.reproducibility_hash is not None
            assert len(result.reproducibility_hash) > 10
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestDesignAndStyling:
    """Tests for professional design elements."""
    
    def test_corporate_colors_applied(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path, primary_color="#1E3A5F")
            generator = PDFGeneratorV2(config)
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            assert result.styling.primary_color == "#1E3A5F"
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_verdict_color_coding(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            decision = MockDecision()
            decision.verdict = "GO"
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=decision,
                formulation=MockFormulation()
            )
            assert result.verdict_color == "green"
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestPDFOutput:
    """Tests for actual PDF file output."""
    
    def test_pdf_file_created(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_pdf_file_valid(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            generator.generate(
                population_result=MockPopulationResult(),
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            with open(output_path, "rb") as f:
                header = f.read(4)
            assert header == b"%PDF"
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_population_result(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            empty_result = MockPopulationResult()
            empty_result.n_valid = 0
            result = generator.generate(
                population_result=empty_result,
                decision=MockDecision(),
                formulation=MockFormulation()
            )
            assert result.has_warning is True
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_no_go_verdict_styling(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name
        
        try:
            config = PDFv2Config(output_path=output_path)
            generator = PDFGeneratorV2(config)
            decision = MockDecision()
            decision.verdict = "NO_GO"
            result = generator.generate(
                population_result=MockPopulationResult(),
                decision=decision,
                formulation=MockFormulation()
            )
            assert result.verdict_color == "red"
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
