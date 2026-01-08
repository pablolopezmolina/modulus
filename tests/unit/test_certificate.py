"""
Tests for Modulus Protocol Certificate Generator.

Session 10.3: Generate professional 1-page PDF certificates with
"MODULUS PROTOCOL VERIFIED" branding, decision verdicts, and key metrics.
"""

import pytest
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
import tempfile
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from reporting.certificate import (
    CertificateGenerator,
    CertificateConfig,
    CertificateInfo,
    CertificateResult,
    generate_certificate,
    generate_certificate_id,
    format_certificate_for_pdf,
)


# ============================================================================
# MOCK CLASSES (for testing without dependencies on other modules)
# ============================================================================

@dataclass
class MockDecision:
    """Mock Decision from DecisionEngine."""
    verdict: str  # "GO" | "CAUTION" | "NO_GO"
    confidence: float
    top_risks: List[Dict[str, Any]]
    summary: str


@dataclass
class MockFormulation:
    """Mock Formulation."""
    name: str
    version: str = "1.0"


@dataclass  
class MockPopulationResult:
    """Mock PopulationSimulationResult."""
    n_individuals: int
    n_valid: int
    metrics_stats: Dict[str, Dict[str, float]]
    risk_analysis: Dict[str, float]
    formulation: Optional[MockFormulation] = None


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_decision_go():
    """A GO decision."""
    return MockDecision(
        verdict="GO",
        confidence=0.92,
        top_risks=[
            {"risk_id": "sleep_disruption", "percentage": 8.5},
            {"risk_id": "jitter", "percentage": 5.2},
        ],
        summary="Product shows excellent safety profile across all segments."
    )


@pytest.fixture
def sample_decision_caution():
    """A CAUTION decision."""
    return MockDecision(
        verdict="CAUTION",
        confidence=0.78,
        top_risks=[
            {"risk_id": "sleep_disruption", "percentage": 18.5},
            {"risk_id": "jitter", "percentage": 12.3},
            {"risk_id": "hyperglycemia", "percentage": 9.1},
        ],
        summary="Some segments show elevated risk. Consider reformulation."
    )


@pytest.fixture
def sample_decision_nogo():
    """A NO_GO decision."""
    return MockDecision(
        verdict="NO_GO",
        confidence=0.85,
        top_risks=[
            {"risk_id": "sleep_disruption", "percentage": 35.2},
            {"risk_id": "jitter", "percentage": 28.7},
        ],
        summary="Product fails safety thresholds. Reformulation required."
    )


@pytest.fixture
def sample_population_result():
    """Sample population simulation result."""
    return MockPopulationResult(
        n_individuals=1000,
        n_valid=985,
        metrics_stats={
            "glucose_peak": {"mean": 142.5, "std": 18.3, "p10": 118.2, "p90": 168.4},
            "alertness_peak": {"mean": 78.5, "std": 12.1, "p10": 62.0, "p90": 92.0},
            "alertness_duration_above_60": {"mean": 285.0, "std": 45.0, "p10": 220.0, "p90": 350.0},
            "caffeine_half_life": {"mean": 5.2, "std": 1.8, "p10": 3.2, "p90": 7.8},
        },
        risk_analysis={
            "hyperglycemia": 12.5,
            "severe_hyperglycemia": 2.1,
            "jitter": 8.3,
            "sleep_disruption": 15.2,
            "crash": 5.8,
        },
        formulation=MockFormulation(name="Energy Pro Max", version="2.1")
    )


@pytest.fixture
def sample_population_result_no_formulation():
    """Sample result without formulation."""
    return MockPopulationResult(
        n_individuals=500,
        n_valid=495,
        metrics_stats={
            "glucose_peak": {"mean": 135.0, "std": 15.0},
            "alertness_peak": {"mean": 72.0, "std": 10.0},
        },
        risk_analysis={
            "hyperglycemia": 8.5,
            "jitter": 6.2,
        },
        formulation=None
    )


# ============================================================================
# CERTIFICATE INFO TESTS
# ============================================================================

class TestCertificateInfo:
    """Tests for CertificateInfo dataclass."""
    
    def test_create_certificate_info(self):
        """CertificateInfo can be created with required fields."""
        
        
        info = CertificateInfo(
            certificate_id="MODULUS-2025-001234",
            product_name="Energy Pro Max",
            verdict="GO",
            confidence=0.92,
            issue_date=datetime(2025, 1, 8, 10, 30, 0),
            n_individuals=1000,
            n_valid=985,
            key_metrics={"alertness_peak": 78.5, "glucose_peak": 142.5},
            top_risks=[("sleep_disruption", 15.2)],
            summary="Product approved."
        )
        
        assert info.certificate_id == "MODULUS-2025-001234"
        assert info.product_name == "Energy Pro Max"
        assert info.verdict == "GO"
        assert info.confidence == 0.92
        assert info.n_individuals == 1000
    
    def test_certificate_info_immutable(self):
        """CertificateInfo is frozen (immutable)."""
        
        
        info = CertificateInfo(
            certificate_id="TEST-001",
            product_name="Test Product",
            verdict="GO",
            confidence=0.9,
            issue_date=datetime.now(),
            n_individuals=100,
            n_valid=100,
            key_metrics={},
            top_risks=[],
            summary="Test"
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            info.verdict = "NO_GO"
    
    def test_certificate_info_verdict_validation(self):
        """CertificateInfo validates verdict values."""
        
        
        # Valid verdicts should work
        for verdict in ["GO", "CAUTION", "NO_GO"]:
            info = CertificateInfo(
                certificate_id="TEST",
                product_name="Test",
                verdict=verdict,
                confidence=0.8,
                issue_date=datetime.now(),
                n_individuals=100,
                n_valid=100,
                key_metrics={},
                top_risks=[],
                summary="Test"
            )
            assert info.verdict == verdict
    
    def test_certificate_info_confidence_range(self):
        """CertificateInfo confidence must be in [0, 1]."""
        
        
        # Valid confidence
        info = CertificateInfo(
            certificate_id="TEST",
            product_name="Test",
            verdict="GO",
            confidence=0.85,
            issue_date=datetime.now(),
            n_individuals=100,
            n_valid=100,
            key_metrics={},
            top_risks=[],
            summary="Test"
        )
        assert info.confidence == 0.85
        
        # Boundary values should work
        info_zero = CertificateInfo(
            certificate_id="TEST",
            product_name="Test",
            verdict="GO",
            confidence=0.0,
            issue_date=datetime.now(),
            n_individuals=100,
            n_valid=100,
            key_metrics={},
            top_risks=[],
            summary="Test"
        )
        assert info_zero.confidence == 0.0
        
        info_one = CertificateInfo(
            certificate_id="TEST",
            product_name="Test",
            verdict="GO",
            confidence=1.0,
            issue_date=datetime.now(),
            n_individuals=100,
            n_valid=100,
            key_metrics={},
            top_risks=[],
            summary="Test"
        )
        assert info_one.confidence == 1.0


# ============================================================================
# CERTIFICATE ID GENERATOR TESTS
# ============================================================================

class TestCertificateIdGenerator:
    """Tests for certificate ID generation."""
    
    def test_generate_certificate_id_format(self):
        """Certificate IDs follow MODULUS-YYYY-XXXXXX format."""
        
        
        cert_id = generate_certificate_id()
        
        assert cert_id.startswith("MODULUS-")
        parts = cert_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 4  # Year
        assert len(parts[2]) == 6  # Random hex
    
    def test_generate_certificate_id_unique(self):
        """Each call generates a unique ID."""
        
        
        ids = [generate_certificate_id() for _ in range(100)]
        
        assert len(set(ids)) == 100  # All unique
    
    def test_generate_certificate_id_with_seed(self):
        """Certificate ID with seed is deterministic."""
        
        
        id1 = generate_certificate_id(seed=42)
        id2 = generate_certificate_id(seed=42)
        
        assert id1 == id2
    
    def test_generate_certificate_id_different_seeds(self):
        """Different seeds produce different IDs."""
        
        
        id1 = generate_certificate_id(seed=42)
        id2 = generate_certificate_id(seed=43)
        
        assert id1 != id2


# ============================================================================
# CERTIFICATE GENERATOR TESTS
# ============================================================================

class TestCertificateGenerator:
    """Tests for CertificateGenerator class."""
    
    def test_create_generator(self):
        """CertificateGenerator can be instantiated."""
        
        
        gen = CertificateGenerator()
        assert gen is not None
    
    def test_create_generator_with_config(self):
        """CertificateGenerator accepts configuration."""
        
        
        config = CertificateConfig(
            company_name="MODULUS",
            include_qr_code=True,
            qr_base_url="https://verify.modulus.bio/cert/"
        )
        gen = CertificateGenerator(config=config)
        
        assert gen.config.company_name == "MODULUS"
        assert gen.config.include_qr_code is True
    
    def test_prepare_certificate_info(
        self, sample_population_result, sample_decision_go
    ):
        """prepare() extracts CertificateInfo from results and decision."""
        
        
        gen = CertificateGenerator()
        info = gen.prepare(
            results=sample_population_result,
            decision=sample_decision_go,
            product_name="Energy Pro Max"
        )
        
        assert info.product_name == "Energy Pro Max"
        assert info.verdict == "GO"
        assert info.confidence == 0.92
        assert info.n_individuals == 1000
        assert info.n_valid == 985
        assert "alertness_peak" in info.key_metrics or "glucose_peak" in info.key_metrics
    
    def test_prepare_extracts_product_name_from_formulation(
        self, sample_population_result, sample_decision_go
    ):
        """prepare() can extract product name from formulation."""
        
        
        gen = CertificateGenerator()
        info = gen.prepare(
            results=sample_population_result,
            decision=sample_decision_go,
            # product_name not provided, should use formulation.name
        )
        
        assert info.product_name == "Energy Pro Max"
    
    def test_prepare_with_explicit_product_name(
        self, sample_population_result, sample_decision_go
    ):
        """Explicit product_name overrides formulation.name."""
        
        
        gen = CertificateGenerator()
        info = gen.prepare(
            results=sample_population_result,
            decision=sample_decision_go,
            product_name="Custom Name"
        )
        
        assert info.product_name == "Custom Name"
    
    def test_prepare_without_product_name_or_formulation(
        self, sample_population_result_no_formulation, sample_decision_go
    ):
        """prepare() uses 'Unknown Product' if no name available."""
        
        
        gen = CertificateGenerator()
        info = gen.prepare(
            results=sample_population_result_no_formulation,
            decision=sample_decision_go
        )
        
        assert info.product_name == "Unknown Product"
    
    def test_prepare_extracts_top_risks(
        self, sample_population_result, sample_decision_caution
    ):
        """prepare() extracts top risks correctly."""
        
        
        gen = CertificateGenerator()
        info = gen.prepare(
            results=sample_population_result,
            decision=sample_decision_caution,
            product_name="Test"
        )
        
        assert len(info.top_risks) >= 1
        # Risks are tuples of (risk_id, percentage)
        risk_ids = [r[0] for r in info.top_risks]
        assert "sleep_disruption" in risk_ids or len(info.top_risks) > 0


# ============================================================================
# PDF GENERATION TESTS
# ============================================================================

class TestCertificatePDFGeneration:
    """Tests for actual PDF generation."""
    
    def test_generate_pdf_creates_file(
        self, sample_population_result, sample_decision_go
    ):
        """generate() creates a PDF file."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "certificate.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                product_name="Energy Pro Max",
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            assert result.output_path == str(output_path)
    
    def test_generate_pdf_returns_certificate_result(
        self, sample_population_result, sample_decision_go
    ):
        """generate() returns CertificateResult with all info."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "certificate.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                product_name="Energy Pro Max",
                output_path=str(output_path)
            )
            
            assert result.certificate_id.startswith("MODULUS-")
            assert result.output_path == str(output_path)
            assert result.info is not None
            assert result.info.verdict == "GO"
    
    def test_generate_pdf_go_verdict(
        self, sample_population_result, sample_decision_go
    ):
        """PDF generates successfully for GO verdict."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cert_go.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            assert result.info.verdict == "GO"
    
    def test_generate_pdf_caution_verdict(
        self, sample_population_result, sample_decision_caution
    ):
        """PDF generates successfully for CAUTION verdict."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cert_caution.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_caution,
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            assert result.info.verdict == "CAUTION"
    
    def test_generate_pdf_nogo_verdict(
        self, sample_population_result, sample_decision_nogo
    ):
        """PDF generates successfully for NO_GO verdict."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cert_nogo.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_nogo,
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            assert result.info.verdict == "NO_GO"
    
    def test_generate_pdf_with_seed(
        self, sample_population_result, sample_decision_go
    ):
        """generate() with seed produces deterministic certificate_id."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result1 = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                output_path=str(Path(tmpdir) / "cert1.pdf"),
                seed=12345
            )
            result2 = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                output_path=str(Path(tmpdir) / "cert2.pdf"),
                seed=12345
            )
            
            assert result1.certificate_id == result2.certificate_id
    
    def test_generate_pdf_auto_output_path(
        self, sample_population_result, sample_decision_go
    ):
        """generate() auto-generates output path if not provided."""
        
        
        gen = CertificateGenerator()
        
        # Should create file in current dir or temp
        result = gen.generate(
            results=sample_population_result,
            decision=sample_decision_go,
            product_name="Test Product"
        )
        
        assert result.output_path is not None
        assert Path(result.output_path).exists()
        
        # Cleanup
        Path(result.output_path).unlink(missing_ok=True)


# ============================================================================
# QR CODE TESTS
# ============================================================================

class TestCertificateQRCode:
    """Tests for QR code functionality."""
    
    def test_config_qr_enabled_by_default(self):
        """QR code is enabled by default in config."""
        
        
        config = CertificateConfig()
        assert config.include_qr_code is True
    
    def test_config_qr_can_be_disabled(self):
        """QR code can be disabled."""
        
        
        config = CertificateConfig(include_qr_code=False)
        assert config.include_qr_code is False
    
    def test_generate_verification_url(self):
        """Verification URL is generated correctly."""
        
        
        config = CertificateConfig(
            qr_base_url="https://verify.modulus.bio/cert/"
        )
        gen = CertificateGenerator(config=config)
        
        cert_id = "MODULUS-2025-ABC123"
        url = gen._get_verification_url(cert_id)
        
        assert url == "https://verify.modulus.bio/cert/MODULUS-2025-ABC123"
    
    def test_pdf_generates_without_qr(
        self, sample_population_result, sample_decision_go
    ):
        """PDF generates successfully without QR code."""
        
        
        config = CertificateConfig(include_qr_code=False)
        gen = CertificateGenerator(config=config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cert_no_qr.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                output_path=str(output_path)
            )
            
            assert output_path.exists()


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================

class TestCertificateSerialization:
    """Tests for certificate data serialization."""
    
    def test_certificate_info_to_dict(self):
        """CertificateInfo can be serialized to dict."""
        
        
        info = CertificateInfo(
            certificate_id="TEST-001",
            product_name="Test Product",
            verdict="GO",
            confidence=0.92,
            issue_date=datetime(2025, 1, 8, 10, 0, 0),
            n_individuals=1000,
            n_valid=985,
            key_metrics={"peak": 78.5},
            top_risks=[("sleep", 15.0)],
            summary="Approved"
        )
        
        d = info.to_dict()
        
        assert d["certificate_id"] == "TEST-001"
        assert d["product_name"] == "Test Product"
        assert d["verdict"] == "GO"
        assert d["confidence"] == 0.92
        assert d["issue_date"] == "2025-01-08T10:00:00"
    
    def test_certificate_info_to_json(self):
        """CertificateInfo can be serialized to JSON."""
        
        import json
        
        info = CertificateInfo(
            certificate_id="TEST-001",
            product_name="Test",
            verdict="CAUTION",
            confidence=0.75,
            issue_date=datetime(2025, 1, 8),
            n_individuals=500,
            n_valid=490,
            key_metrics={},
            top_risks=[],
            summary="Test"
        )
        
        json_str = info.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["certificate_id"] == "TEST-001"
        assert parsed["verdict"] == "CAUTION"
    
    def test_certificate_result_to_dict(
        self, sample_population_result, sample_decision_go
    ):
        """CertificateResult can be serialized."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                output_path=str(Path(tmpdir) / "cert.pdf")
            )
            
            d = result.to_dict()
            
            assert "certificate_id" in d
            assert "output_path" in d
            assert "info" in d


# ============================================================================
# EDGE CASES
# ============================================================================

class TestCertificateEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_generate_with_minimal_metrics(self, sample_decision_go):
        """Certificate generates with minimal metrics."""
        
        
        minimal_result = MockPopulationResult(
            n_individuals=100,
            n_valid=100,
            metrics_stats={},  # No metrics
            risk_analysis={},  # No risks
            formulation=None
        )
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(
                results=minimal_result,
                decision=sample_decision_go,
                product_name="Minimal Product",
                output_path=str(Path(tmpdir) / "cert.pdf")
            )
            
            assert Path(result.output_path).exists()
    
    def test_generate_with_long_product_name(
        self, sample_population_result, sample_decision_go
    ):
        """Certificate handles long product names."""
        
        
        gen = CertificateGenerator()
        
        long_name = "Super Ultra Mega Energy Pro Max Extreme Performance Formula v2.0 Extended Release"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                product_name=long_name,
                output_path=str(Path(tmpdir) / "cert.pdf")
            )
            
            assert Path(result.output_path).exists()
    
    def test_generate_with_special_characters_in_name(
        self, sample_population_result, sample_decision_go
    ):
        """Certificate handles special characters in product name."""
        
        
        gen = CertificateGenerator()
        
        special_name = "Energy+ Pro™ (Café Edition) — v2.0"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                product_name=special_name,
                output_path=str(Path(tmpdir) / "cert.pdf")
            )
            
            assert Path(result.output_path).exists()
    
    def test_generate_creates_parent_directories(
        self, sample_population_result, sample_decision_go
    ):
        """Certificate creates parent directories if needed."""
        
        
        gen = CertificateGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dirs" / "cert.pdf"
            
            result = gen.generate(
                results=sample_population_result,
                decision=sample_decision_go,
                output_path=str(output_path)
            )
            
            assert output_path.exists()


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_generate_certificate_function(
        self, sample_population_result, sample_decision_go
    ):
        """generate_certificate() convenience function works."""
        
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_certificate(
                results=sample_population_result,
                decision=sample_decision_go,
                product_name="Test",
                output_path=str(Path(tmpdir) / "cert.pdf")
            )
            
            assert Path(result.output_path).exists()
    
    def test_format_certificate_for_pdf_function(
        self, sample_population_result, sample_decision_go
    ):
        """format_certificate_for_pdf() returns dict for PDF v2 integration."""
        
        
        gen = CertificateGenerator()
        info = gen.prepare(
            results=sample_population_result,
            decision=sample_decision_go,
            product_name="Test"
        )
        
        formatted = format_certificate_for_pdf(info)
        
        assert "title" in formatted
        assert "verdict" in formatted
        assert "metrics_table" in formatted
        assert "risks_table" in formatted


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestCertificateIntegration:
    """Integration tests with other modules."""
    
    def test_certificate_info_compatible_with_bundle(self):
        """CertificateInfo can be included in ReproducibilityBundle."""
        
        import json
        
        info = CertificateInfo(
            certificate_id="TEST-001",
            product_name="Test",
            verdict="GO",
            confidence=0.9,
            issue_date=datetime.now(),
            n_individuals=1000,
            n_valid=995,
            key_metrics={"peak": 80.0},
            top_risks=[],
            summary="OK"
        )
        
        # Should be JSON-serializable for bundle
        bundle_data = {
            "certificate": info.to_dict()
        }
        json_str = json.dumps(bundle_data)
        
        assert "TEST-001" in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
