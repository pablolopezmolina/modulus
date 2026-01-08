"""
Tests for Evidence Registry - Session 9.1

The Evidence Registry provides scientific traceability for all model parameters.
It supports:
- DOI-based source tracking
- Confidence levels (high/medium/low/theoretical)
- BibTeX export for citations
- Evidence tables for PDF reports
"""

import pytest
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================================
# DOMAIN MODELS TESTS
# ============================================================================

class TestEvidenceSource:
    """Tests for EvidenceSource dataclass."""
    
    def test_create_source_with_doi(self):
        """Source can be created with a DOI."""
        from src.analysis.evidence import EvidenceSource
        
        source = EvidenceSource(
            source_id="blanchard_1983",
            doi="10.1007/BF00542458",
            title="Caffeine pharmacokinetics in man",
            authors=["Blanchard, J.", "Sawers, S.J.A."],
            journal="European Journal of Clinical Pharmacology",
            year=1983,
            source_type="peer_reviewed"
        )
        
        assert source.source_id == "blanchard_1983"
        assert source.doi == "10.1007/BF00542458"
        assert source.year == 1983
        assert source.source_type == "peer_reviewed"
    
    def test_create_source_without_doi(self):
        """Source can be created without DOI (database, textbook)."""
        from src.analysis.evidence import EvidenceSource
        
        source = EvidenceSource(
            source_id="nhanes_2020",
            doi=None,
            title="National Health and Nutrition Examination Survey",
            authors=["CDC"],
            journal=None,
            year=2020,
            source_type="database",
            url="https://www.cdc.gov/nchs/nhanes/"
        )
        
        assert source.source_id == "nhanes_2020"
        assert source.doi is None
        assert source.source_type == "database"
        assert source.url is not None
    
    def test_source_types_validation(self):
        """Source type must be valid."""
        from src.analysis.evidence import EvidenceSource
        
        valid_types = ["peer_reviewed", "database", "textbook", "meta_analysis", "clinical_trial"]
        
        for source_type in valid_types:
            source = EvidenceSource(
                source_id=f"test_{source_type}",
                doi=None,
                title="Test",
                authors=["Test"],
                journal=None,
                year=2020,
                source_type=source_type
            )
            assert source.source_type == source_type
    
    def test_invalid_source_type_raises(self):
        """Invalid source type raises ValueError."""
        from src.analysis.evidence import EvidenceSource
        
        with pytest.raises(ValueError, match="source_type"):
            EvidenceSource(
                source_id="test",
                doi=None,
                title="Test",
                authors=["Test"],
                journal=None,
                year=2020,
                source_type="invalid_type"
            )


class TestParameterEvidence:
    """Tests for ParameterEvidence linking parameters to sources."""
    
    def test_create_parameter_evidence(self):
        """Parameter evidence links a parameter to its source."""
        from src.analysis.evidence import ParameterEvidence
        
        evidence = ParameterEvidence(
            parameter_name="caffeine_half_life_h",
            parameter_value=5.0,
            parameter_unit="hours",
            source_id="blanchard_1983",
            confidence="high",
            notes="Healthy adults, non-smokers"
        )
        
        assert evidence.parameter_name == "caffeine_half_life_h"
        assert evidence.parameter_value == 5.0
        assert evidence.confidence == "high"
    
    def test_confidence_levels_validation(self):
        """Confidence must be valid level."""
        from src.analysis.evidence import ParameterEvidence
        
        valid_levels = ["high", "medium", "low", "theoretical"]
        
        for level in valid_levels:
            evidence = ParameterEvidence(
                parameter_name="test_param",
                parameter_value=1.0,
                parameter_unit="mg",
                source_id="test_source",
                confidence=level
            )
            assert evidence.confidence == level
    
    def test_invalid_confidence_raises(self):
        """Invalid confidence level raises ValueError."""
        from src.analysis.evidence import ParameterEvidence
        
        with pytest.raises(ValueError, match="confidence"):
            ParameterEvidence(
                parameter_name="test_param",
                parameter_value=1.0,
                parameter_unit="mg",
                source_id="test_source",
                confidence="very_high"  # Invalid
            )


# ============================================================================
# EVIDENCE REGISTRY TESTS
# ============================================================================

class TestEvidenceRegistry:
    """Tests for the main EvidenceRegistry class."""
    
    @pytest.fixture
    def empty_registry(self):
        """Create an empty registry."""
        from src.analysis.evidence import EvidenceRegistry
        return EvidenceRegistry()
    
    @pytest.fixture
    def populated_registry(self):
        """Create a registry with some sources and evidence."""
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource, ParameterEvidence
        
        registry = EvidenceRegistry()
        
        # Add sources
        registry.add_source(EvidenceSource(
            source_id="blanchard_1983",
            doi="10.1007/BF00542458",
            title="Caffeine pharmacokinetics in man",
            authors=["Blanchard, J.", "Sawers, S.J.A."],
            journal="European Journal of Clinical Pharmacology",
            year=1983,
            source_type="peer_reviewed"
        ))
        
        registry.add_source(EvidenceSource(
            source_id="dalla_man_2007",
            doi="10.1109/TBME.2006.889180",
            title="Meal Simulation Model of the Glucose-Insulin System",
            authors=["Dalla Man, C.", "Rizza, R.A.", "Cobelli, C."],
            journal="IEEE Transactions on Biomedical Engineering",
            year=2007,
            source_type="peer_reviewed"
        ))
        
        # Add parameter evidence
        registry.add_parameter_evidence(ParameterEvidence(
            parameter_name="caffeine_half_life_h",
            parameter_value=5.0,
            parameter_unit="hours",
            source_id="blanchard_1983",
            confidence="high",
            notes="Healthy adults, non-smokers"
        ))
        
        registry.add_parameter_evidence(ParameterEvidence(
            parameter_name="glucose_effectiveness",
            parameter_value=0.0038,
            parameter_unit="1/min",
            source_id="dalla_man_2007",
            confidence="high",
            notes="SI units"
        ))
        
        return registry
    
    def test_add_source(self, empty_registry):
        """Can add a source to the registry."""
        from src.analysis.evidence import EvidenceSource
        
        source = EvidenceSource(
            source_id="test_source",
            doi="10.1234/test",
            title="Test Paper",
            authors=["Test, A."],
            journal="Test Journal",
            year=2020,
            source_type="peer_reviewed"
        )
        
        empty_registry.add_source(source)
        
        assert empty_registry.get_source("test_source") == source
    
    def test_add_duplicate_source_raises(self, empty_registry):
        """Adding duplicate source_id raises ValueError."""
        from src.analysis.evidence import EvidenceSource
        
        source = EvidenceSource(
            source_id="test_source",
            doi="10.1234/test",
            title="Test Paper",
            authors=["Test, A."],
            journal="Test Journal",
            year=2020,
            source_type="peer_reviewed"
        )
        
        empty_registry.add_source(source)
        
        with pytest.raises(ValueError, match="already exists"):
            empty_registry.add_source(source)
    
    def test_get_nonexistent_source_raises(self, empty_registry):
        """Getting nonexistent source raises KeyError."""
        with pytest.raises(KeyError):
            empty_registry.get_source("nonexistent")
    
    def test_add_parameter_evidence_with_valid_source(self, populated_registry):
        """Can add parameter evidence referencing existing source."""
        from src.analysis.evidence import ParameterEvidence
        
        evidence = ParameterEvidence(
            parameter_name="new_param",
            parameter_value=42.0,
            parameter_unit="units",
            source_id="blanchard_1983",  # Exists
            confidence="medium"
        )
        
        populated_registry.add_parameter_evidence(evidence)
        
        results = populated_registry.get_evidence_for_parameter("new_param")
        assert len(results) == 1
        assert results[0].parameter_value == 42.0
    
    def test_add_parameter_evidence_with_invalid_source_raises(self, empty_registry):
        """Adding evidence with nonexistent source raises ValueError."""
        from src.analysis.evidence import ParameterEvidence
        
        evidence = ParameterEvidence(
            parameter_name="test_param",
            parameter_value=1.0,
            parameter_unit="mg",
            source_id="nonexistent_source",
            confidence="high"
        )
        
        with pytest.raises(ValueError, match="Source .* not found"):
            empty_registry.add_parameter_evidence(evidence)
    
    def test_list_all_sources(self, populated_registry):
        """Can list all sources in registry."""
        sources = populated_registry.list_sources()
        
        assert len(sources) == 2
        assert "blanchard_1983" in sources
        assert "dalla_man_2007" in sources
    
    def test_get_evidence_for_parameter(self, populated_registry):
        """Can get all evidence for a specific parameter."""
        evidence = populated_registry.get_evidence_for_parameter("caffeine_half_life_h")
        
        assert len(evidence) == 1
        assert evidence[0].parameter_value == 5.0
        assert evidence[0].source_id == "blanchard_1983"
    
    def test_get_evidence_for_nonexistent_parameter(self, populated_registry):
        """Getting evidence for nonexistent parameter returns empty list."""
        evidence = populated_registry.get_evidence_for_parameter("nonexistent")
        assert evidence == []
    
    def test_get_all_evidence(self, populated_registry):
        """Can get all parameter evidence."""
        all_evidence = populated_registry.get_all_evidence()
        
        assert len(all_evidence) == 2
        param_names = [e.parameter_name for e in all_evidence]
        assert "caffeine_half_life_h" in param_names
        assert "glucose_effectiveness" in param_names


# ============================================================================
# EXPORT FUNCTIONALITY TESTS
# ============================================================================

class TestBibTeXExport:
    """Tests for BibTeX citation export."""
    
    @pytest.fixture
    def registry_with_sources(self):
        """Create registry with various source types for export testing."""
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource
        
        registry = EvidenceRegistry()
        
        registry.add_source(EvidenceSource(
            source_id="blanchard_1983",
            doi="10.1007/BF00542458",
            title="Caffeine pharmacokinetics in man",
            authors=["Blanchard, J.", "Sawers, S.J.A."],
            journal="European Journal of Clinical Pharmacology",
            year=1983,
            source_type="peer_reviewed"
        ))
        
        registry.add_source(EvidenceSource(
            source_id="nhanes_database",
            doi=None,
            title="National Health and Nutrition Examination Survey",
            authors=["CDC"],
            journal=None,
            year=2020,
            source_type="database",
            url="https://www.cdc.gov/nchs/nhanes/"
        ))
        
        return registry
    
    def test_export_single_source_bibtex(self, registry_with_sources):
        """Export a single source to BibTeX format."""
        bibtex = registry_with_sources.export_bibtex("blanchard_1983")
        
        assert "@article{blanchard_1983," in bibtex
        assert "author = {Blanchard, J. and Sawers, S.J.A.}" in bibtex
        assert "title = {Caffeine pharmacokinetics in man}" in bibtex
        assert "year = {1983}" in bibtex
        assert "doi = {10.1007/BF00542458}" in bibtex
    
    def test_export_all_sources_bibtex(self, registry_with_sources):
        """Export all sources to BibTeX format."""
        bibtex = registry_with_sources.export_all_bibtex()
        
        assert "@article{blanchard_1983," in bibtex
        assert "@misc{nhanes_database," in bibtex
    
    def test_export_database_source_bibtex(self, registry_with_sources):
        """Export database source to BibTeX (uses @misc)."""
        bibtex = registry_with_sources.export_bibtex("nhanes_database")
        
        assert "@misc{nhanes_database," in bibtex
        assert "url = {https://www.cdc.gov/nchs/nhanes/}" in bibtex


class TestEvidenceTableExport:
    """Tests for evidence table generation (for PDF)."""
    
    @pytest.fixture
    def populated_registry(self):
        """Create a registry with sources and evidence for table tests."""
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource, ParameterEvidence
        
        registry = EvidenceRegistry()
        
        registry.add_source(EvidenceSource(
            source_id="blanchard_1983",
            doi="10.1007/BF00542458",
            title="Caffeine pharmacokinetics",
            authors=["Blanchard, J."],
            journal="Eur J Clin Pharmacol",
            year=1983,
            source_type="peer_reviewed"
        ))
        
        registry.add_source(EvidenceSource(
            source_id="yang_2010",
            doi="10.1111/j.1365-2125.2009.03578.x",
            title="Theanine review",
            authors=["Yang, L."],
            journal="Br J Clin Pharmacol",
            year=2010,
            source_type="peer_reviewed"
        ))
        
        registry.add_parameter_evidence(ParameterEvidence(
            parameter_name="caffeine_half_life_h",
            parameter_value=5.0,
            parameter_unit="hours",
            source_id="blanchard_1983",
            confidence="high",
            compound_id="caffeine"
        ))
        
        registry.add_parameter_evidence(ParameterEvidence(
            parameter_name="theanine_tmax_min",
            parameter_value=50.0,
            parameter_unit="minutes",
            source_id="yang_2010",
            confidence="medium",
            compound_id="l_theanine"
        ))
        
        return registry
    
    def test_generate_evidence_table(self, populated_registry):
        """Generate evidence table as list of dicts."""
        table = populated_registry.generate_evidence_table()
        
        assert len(table) == 2
        
        # Check first row has expected columns
        row = table[0]
        assert "parameter_name" in row
        assert "value" in row
        assert "unit" in row
        assert "confidence" in row
        assert "source" in row
        assert "doi" in row
    
    def test_generate_evidence_table_sorted(self, populated_registry):
        """Evidence table is sorted by compound_id, then parameter_name."""
        table = populated_registry.generate_evidence_table()
        
        # Should be sorted alphabetically by compound_id
        compounds = [row.get("compound_id", "") for row in table]
        assert compounds == sorted(compounds)
    
    def test_generate_evidence_table_for_compound(self, populated_registry):
        """Can generate table filtered by compound."""
        table = populated_registry.generate_evidence_table(compound_id="caffeine")
        
        assert len(table) == 1
        assert table[0]["parameter_name"] == "caffeine_half_life_h"
    
    def test_generate_evidence_table_formatted_source(self, populated_registry):
        """Source column is formatted as 'Author et al., Year'."""
        table = populated_registry.generate_evidence_table()
        
        # Find caffeine row
        caffeine_row = next(r for r in table if r["parameter_name"] == "caffeine_half_life_h")
        
        # Should be "Blanchard, 1983" or similar
        assert "Blanchard" in caffeine_row["source"]
        assert "1983" in caffeine_row["source"]


class TestCitationListExport:
    """Tests for formatted citation list export."""
    
    @pytest.fixture
    def registry(self):
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource
        
        registry = EvidenceRegistry()
        
        registry.add_source(EvidenceSource(
            source_id="dalla_man_2007",
            doi="10.1109/TBME.2006.889180",
            title="Meal Simulation Model of the Glucose-Insulin System",
            authors=["Dalla Man, C.", "Rizza, R.A.", "Cobelli, C."],
            journal="IEEE Trans Biomed Eng",
            year=2007,
            source_type="peer_reviewed"
        ))
        
        return registry
    
    def test_export_apa_citation(self, registry):
        """Export citation in APA-like format."""
        citation = registry.format_citation("dalla_man_2007", style="apa")
        
        # APA: Author, A. A., Author, B. B., & Author, C. C. (Year). Title. Journal.
        assert "Dalla Man, C." in citation
        assert "2007" in citation
        assert "Meal Simulation Model" in citation
        assert "IEEE Trans Biomed Eng" in citation
    
    def test_export_short_citation(self, registry):
        """Export short citation (Author et al., Year)."""
        citation = registry.format_citation("dalla_man_2007", style="short")
        
        # Short: "Dalla Man et al., 2007"
        assert "Dalla Man et al." in citation
        assert "2007" in citation


# ============================================================================
# INTEGRATION WITH COMPOUND LIBRARY TESTS
# ============================================================================

class TestCompoundIntegration:
    """Tests for integration with existing compound library."""
    
    def test_load_evidence_from_compound_profile(self):
        """Can extract evidence from a CompoundProfile's primary_sources."""
        from src.analysis.evidence import EvidenceRegistry
        
        # Mock compound profile data (as it would come from ingredients.json)
        compound_data = {
            "compound_id": "caffeine",
            "name": "Caffeine",
            "primary_sources": [
                "10.1007/BF00542458",
                "10.1016/j.pharmthera.2009.03.004"
            ],
            "evidence_level": "high"
        }
        
        registry = EvidenceRegistry()
        
        # Should be able to register DOIs from compound
        for doi in compound_data["primary_sources"]:
            # This just verifies the DOI format, doesn't require network
            assert registry.is_valid_doi(doi)
    
    def test_validate_doi_format(self):
        """DOI format validation works correctly."""
        from src.analysis.evidence import EvidenceRegistry
        
        registry = EvidenceRegistry()
        
        # Valid DOIs
        assert registry.is_valid_doi("10.1007/BF00542458")
        assert registry.is_valid_doi("10.1109/TBME.2006.889180")
        assert registry.is_valid_doi("10.1016/j.pharmthera.2009.03.004")
        
        # Invalid DOIs
        assert not registry.is_valid_doi("not_a_doi")
        assert not registry.is_valid_doi("10.abc/invalid")
        assert not registry.is_valid_doi("")
        assert not registry.is_valid_doi(None)


# ============================================================================
# SUMMARY STATISTICS TESTS
# ============================================================================

class TestEvidenceSummary:
    """Tests for evidence summary statistics."""
    
    @pytest.fixture
    def registry_with_evidence(self):
        """Create registry with multiple evidence levels."""
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource, ParameterEvidence
        
        registry = EvidenceRegistry()
        
        # Add a source
        registry.add_source(EvidenceSource(
            source_id="test_source",
            doi="10.1234/test",
            title="Test",
            authors=["Test"],
            journal="Test",
            year=2020,
            source_type="peer_reviewed"
        ))
        
        # Add evidence with different confidence levels
        for i, conf in enumerate(["high", "high", "medium", "low"]):
            registry.add_parameter_evidence(ParameterEvidence(
                parameter_name=f"param_{i}",
                parameter_value=float(i),
                parameter_unit="units",
                source_id="test_source",
                confidence=conf
            ))
        
        return registry
    
    def test_get_evidence_summary(self, registry_with_evidence):
        """Get summary statistics of evidence."""
        summary = registry_with_evidence.get_summary()
        
        assert summary["total_sources"] == 1
        assert summary["total_parameters"] == 4
        assert summary["confidence_breakdown"]["high"] == 2
        assert summary["confidence_breakdown"]["medium"] == 1
        assert summary["confidence_breakdown"]["low"] == 1
        assert summary["confidence_breakdown"]["theoretical"] == 0
    
    def test_get_evidence_coverage(self, registry_with_evidence):
        """Calculate percentage of high-confidence evidence."""
        summary = registry_with_evidence.get_summary()
        
        # high_confidence_pct = high / total
        assert summary["high_confidence_pct"] == pytest.approx(50.0)  # 2/4


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================

class TestSerialization:
    """Tests for saving/loading registry state."""
    
    def test_registry_to_dict(self):
        """Registry can be serialized to dict."""
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource, ParameterEvidence
        
        registry = EvidenceRegistry()
        
        registry.add_source(EvidenceSource(
            source_id="test_source",
            doi="10.1234/test",
            title="Test Paper",
            authors=["Test, A."],
            journal="Test Journal",
            year=2020,
            source_type="peer_reviewed"
        ))
        
        registry.add_parameter_evidence(ParameterEvidence(
            parameter_name="test_param",
            parameter_value=42.0,
            parameter_unit="units",
            source_id="test_source",
            confidence="high"
        ))
        
        data = registry.to_dict()
        
        assert "sources" in data
        assert "parameter_evidence" in data
        assert len(data["sources"]) == 1
        assert len(data["parameter_evidence"]) == 1
    
    def test_registry_from_dict(self):
        """Registry can be loaded from dict."""
        from src.analysis.evidence import EvidenceRegistry
        
        data = {
            "sources": [{
                "source_id": "test_source",
                "doi": "10.1234/test",
                "title": "Test Paper",
                "authors": ["Test, A."],
                "journal": "Test Journal",
                "year": 2020,
                "source_type": "peer_reviewed"
            }],
            "parameter_evidence": [{
                "parameter_name": "test_param",
                "parameter_value": 42.0,
                "parameter_unit": "units",
                "source_id": "test_source",
                "confidence": "high",
                "compound_id": None,
                "notes": None
            }]
        }
        
        registry = EvidenceRegistry.from_dict(data)
        
        assert len(registry.list_sources()) == 1
        assert len(registry.get_all_evidence()) == 1
    
    def test_roundtrip_serialization(self):
        """to_dict -> from_dict preserves all data."""
        from src.analysis.evidence import EvidenceRegistry, EvidenceSource, ParameterEvidence
        
        registry = EvidenceRegistry()
        
        registry.add_source(EvidenceSource(
            source_id="test",
            doi="10.1234/test",
            title="Test",
            authors=["A"],
            journal="J",
            year=2020,
            source_type="peer_reviewed"
        ))
        
        registry.add_parameter_evidence(ParameterEvidence(
            parameter_name="p1",
            parameter_value=1.0,
            parameter_unit="u",
            source_id="test",
            confidence="high"
        ))
        
        # Roundtrip
        data = registry.to_dict()
        restored = EvidenceRegistry.from_dict(data)
        
        # Verify
        assert registry.list_sources() == restored.list_sources()
        assert len(registry.get_all_evidence()) == len(restored.get_all_evidence())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
