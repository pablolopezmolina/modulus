"""
Evidence Registry - Scientific Traceability System

This module provides comprehensive evidence tracking for all model parameters
in MODULUS. It supports:

- Source management (papers, databases, textbooks)
- Parameter-to-source linking with confidence levels
- BibTeX export for academic citations
- Evidence tables for PDF reports
- Summary statistics for audit/compliance

Part of Pack 2 (€150-250k) - Enterprise Risk & Compliance

Session 9.1 - FASE 3
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import re
from datetime import datetime


# ============================================================================
# CONSTANTS
# ============================================================================

VALID_SOURCE_TYPES = frozenset([
    "peer_reviewed",
    "database", 
    "textbook",
    "meta_analysis",
    "clinical_trial"
])

VALID_CONFIDENCE_LEVELS = frozenset([
    "high",      # Well-established, multiple studies
    "medium",    # Single good study or consistent estimates
    "low",       # Limited evidence, extrapolated
    "theoretical"  # Based on mechanism, not direct measurement
])

# DOI regex pattern: 10.xxxx/anything
DOI_PATTERN = re.compile(r"^10\.\d{4,}/[^\s]+$")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class EvidenceSource:
    """
    Represents a scientific source (paper, database, textbook).
    
    Immutable to ensure data integrity.
    
    Attributes:
        source_id: Unique identifier (e.g., "blanchard_1983")
        doi: Digital Object Identifier (optional for databases)
        title: Full title of the source
        authors: List of author names
        journal: Journal/publication name (None for databases)
        year: Publication year
        source_type: Type classification
        url: Optional URL for online resources
        notes: Optional additional notes
    """
    source_id: str
    doi: Optional[str]
    title: str
    authors: List[str]
    journal: Optional[str]
    year: int
    source_type: str
    url: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate source_type."""
        if self.source_type not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"Invalid source_type '{self.source_type}'. "
                f"Must be one of: {sorted(VALID_SOURCE_TYPES)}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_id": self.source_id,
            "doi": self.doi,
            "title": self.title,
            "authors": list(self.authors),
            "journal": self.journal,
            "year": self.year,
            "source_type": self.source_type,
            "url": self.url,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSource":
        """Deserialize from dictionary."""
        return cls(
            source_id=data["source_id"],
            doi=data.get("doi"),
            title=data["title"],
            authors=data["authors"],
            journal=data.get("journal"),
            year=data["year"],
            source_type=data["source_type"],
            url=data.get("url"),
            notes=data.get("notes")
        )


@dataclass(frozen=True)
class ParameterEvidence:
    """
    Links a model parameter to its evidence source.
    
    Immutable to ensure data integrity.
    
    Attributes:
        parameter_name: Name of the parameter (e.g., "caffeine_half_life_h")
        parameter_value: The value used in the model
        parameter_unit: Unit of measurement
        source_id: Reference to EvidenceSource
        confidence: Confidence level in the evidence
        compound_id: Optional compound this parameter belongs to
        notes: Optional additional context
    """
    parameter_name: str
    parameter_value: float
    parameter_unit: str
    source_id: str
    confidence: str
    compound_id: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate confidence level."""
        if self.confidence not in VALID_CONFIDENCE_LEVELS:
            raise ValueError(
                f"Invalid confidence '{self.confidence}'. "
                f"Must be one of: {sorted(VALID_CONFIDENCE_LEVELS)}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "parameter_name": self.parameter_name,
            "parameter_value": self.parameter_value,
            "parameter_unit": self.parameter_unit,
            "source_id": self.source_id,
            "confidence": self.confidence,
            "compound_id": self.compound_id,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterEvidence":
        """Deserialize from dictionary."""
        return cls(
            parameter_name=data["parameter_name"],
            parameter_value=data["parameter_value"],
            parameter_unit=data["parameter_unit"],
            source_id=data["source_id"],
            confidence=data["confidence"],
            compound_id=data.get("compound_id"),
            notes=data.get("notes")
        )


# ============================================================================
# EVIDENCE REGISTRY
# ============================================================================

class EvidenceRegistry:
    """
    Central registry for scientific evidence in MODULUS.
    
    Provides:
    - Source management (add, get, list)
    - Parameter evidence linking
    - Export to BibTeX and tables
    - Summary statistics
    - Serialization/deserialization
    
    Example:
        >>> registry = EvidenceRegistry()
        >>> registry.add_source(EvidenceSource(...))
        >>> registry.add_parameter_evidence(ParameterEvidence(...))
        >>> bibtex = registry.export_all_bibtex()
        >>> table = registry.generate_evidence_table()
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._sources: Dict[str, EvidenceSource] = {}
        self._evidence: List[ParameterEvidence] = []
    
    # ========================================================================
    # SOURCE MANAGEMENT
    # ========================================================================
    
    def add_source(self, source: EvidenceSource) -> None:
        """
        Add a source to the registry.
        
        Args:
            source: The EvidenceSource to add
            
        Raises:
            ValueError: If source_id already exists
        """
        if source.source_id in self._sources:
            raise ValueError(f"Source '{source.source_id}' already exists in registry")
        self._sources[source.source_id] = source
    
    def get_source(self, source_id: str) -> EvidenceSource:
        """
        Get a source by ID.
        
        Args:
            source_id: The source identifier
            
        Returns:
            The EvidenceSource
            
        Raises:
            KeyError: If source not found
        """
        if source_id not in self._sources:
            raise KeyError(f"Source '{source_id}' not found in registry")
        return self._sources[source_id]
    
    def list_sources(self) -> List[str]:
        """
        List all source IDs in the registry.
        
        Returns:
            List of source_id strings
        """
        return list(self._sources.keys())
    
    # ========================================================================
    # PARAMETER EVIDENCE MANAGEMENT
    # ========================================================================
    
    def add_parameter_evidence(self, evidence: ParameterEvidence) -> None:
        """
        Add parameter evidence to the registry.
        
        Args:
            evidence: The ParameterEvidence to add
            
        Raises:
            ValueError: If referenced source doesn't exist
        """
        if evidence.source_id not in self._sources:
            raise ValueError(
                f"Source '{evidence.source_id}' not found in registry. "
                "Add the source first with add_source()."
            )
        self._evidence.append(evidence)
    
    def get_evidence_for_parameter(self, parameter_name: str) -> List[ParameterEvidence]:
        """
        Get all evidence for a specific parameter.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            List of ParameterEvidence (empty if none found)
        """
        return [e for e in self._evidence if e.parameter_name == parameter_name]
    
    def get_all_evidence(self) -> List[ParameterEvidence]:
        """
        Get all parameter evidence in the registry.
        
        Returns:
            List of all ParameterEvidence
        """
        return list(self._evidence)
    
    # ========================================================================
    # BIBTEX EXPORT
    # ========================================================================
    
    def export_bibtex(self, source_id: str) -> str:
        """
        Export a single source to BibTeX format.
        
        Args:
            source_id: The source to export
            
        Returns:
            BibTeX formatted string
        """
        source = self.get_source(source_id)
        return self._format_bibtex_entry(source)
    
    def export_all_bibtex(self) -> str:
        """
        Export all sources to BibTeX format.
        
        Returns:
            BibTeX formatted string with all sources
        """
        entries = []
        for source_id in sorted(self._sources.keys()):
            entries.append(self._format_bibtex_entry(self._sources[source_id]))
        return "\n\n".join(entries)
    
    def _format_bibtex_entry(self, source: EvidenceSource) -> str:
        """Format a single source as BibTeX entry."""
        # Determine entry type
        if source.source_type in ("peer_reviewed", "meta_analysis", "clinical_trial"):
            entry_type = "article"
        elif source.source_type == "textbook":
            entry_type = "book"
        else:
            entry_type = "misc"
        
        # Build entry
        lines = [f"@{entry_type}{{{source.source_id},"]
        
        # Authors (joined with " and ")
        authors_str = " and ".join(source.authors)
        lines.append(f"  author = {{{authors_str}}},")
        
        # Title
        lines.append(f"  title = {{{source.title}}},")
        
        # Journal (if applicable)
        if source.journal:
            lines.append(f"  journal = {{{source.journal}}},")
        
        # Year
        lines.append(f"  year = {{{source.year}}},")
        
        # DOI (if available)
        if source.doi:
            lines.append(f"  doi = {{{source.doi}}},")
        
        # URL (if available)
        if source.url:
            lines.append(f"  url = {{{source.url}}},")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    # ========================================================================
    # EVIDENCE TABLE EXPORT (for PDF)
    # ========================================================================
    
    def generate_evidence_table(
        self, 
        compound_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate evidence table as list of dicts (for PDF/export).
        
        Args:
            compound_id: Optional filter by compound
            
        Returns:
            List of dicts with keys: parameter_name, value, unit, 
            confidence, source, doi, compound_id
        """
        # Filter evidence
        evidence_list = self._evidence
        if compound_id is not None:
            evidence_list = [e for e in evidence_list if e.compound_id == compound_id]
        
        # Sort by compound_id, then parameter_name
        evidence_list = sorted(
            evidence_list,
            key=lambda e: (e.compound_id or "", e.parameter_name)
        )
        
        # Build table rows
        rows = []
        for evidence in evidence_list:
            source = self._sources.get(evidence.source_id)
            
            # Format source citation (short)
            source_citation = self._format_short_citation(source) if source else "Unknown"
            
            rows.append({
                "parameter_name": evidence.parameter_name,
                "value": evidence.parameter_value,
                "unit": evidence.parameter_unit,
                "confidence": evidence.confidence,
                "source": source_citation,
                "doi": source.doi if source else None,
                "compound_id": evidence.compound_id
            })
        
        return rows
    
    # ========================================================================
    # CITATION FORMATTING
    # ========================================================================
    
    def format_citation(self, source_id: str, style: str = "apa") -> str:
        """
        Format a source citation in the specified style.
        
        Args:
            source_id: The source to format
            style: Citation style ("apa" or "short")
            
        Returns:
            Formatted citation string
        """
        source = self.get_source(source_id)
        
        if style == "short":
            return self._format_short_citation(source)
        elif style == "apa":
            return self._format_apa_citation(source)
        else:
            raise ValueError(f"Unknown citation style: {style}")
    
    def _format_short_citation(self, source: EvidenceSource) -> str:
        """Format as 'Author et al., Year' or 'Author, Year'."""
        if not source.authors:
            return f"Unknown, {source.year}"
        
        first_author = source.authors[0].split(",")[0]  # Get surname
        
        if len(source.authors) > 2:
            return f"{first_author} et al., {source.year}"
        elif len(source.authors) == 2:
            second_author = source.authors[1].split(",")[0]
            return f"{first_author} & {second_author}, {source.year}"
        else:
            return f"{first_author}, {source.year}"
    
    def _format_apa_citation(self, source: EvidenceSource) -> str:
        """Format in APA-like style."""
        # Authors
        authors_str = ", ".join(source.authors)
        
        # Year
        year_str = f"({source.year})"
        
        # Title
        title_str = source.title
        
        # Journal (if available)
        journal_str = f" {source.journal}." if source.journal else ""
        
        return f"{authors_str} {year_str}. {title_str}.{journal_str}"
    
    # ========================================================================
    # VALIDATION UTILITIES
    # ========================================================================
    
    def is_valid_doi(self, doi: Optional[str]) -> bool:
        """
        Check if a string is a valid DOI format.
        
        Args:
            doi: The string to check
            
        Returns:
            True if valid DOI format
        """
        if doi is None or doi == "":
            return False
        return bool(DOI_PATTERN.match(doi))
    
    # ========================================================================
    # SUMMARY STATISTICS
    # ========================================================================
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of the evidence registry.
        
        Returns:
            Dict with:
            - total_sources: Number of sources
            - total_parameters: Number of parameter evidence entries
            - confidence_breakdown: Count by confidence level
            - high_confidence_pct: Percentage of high-confidence params
        """
        total_params = len(self._evidence)
        
        # Count by confidence level
        confidence_counts = {level: 0 for level in VALID_CONFIDENCE_LEVELS}
        for evidence in self._evidence:
            confidence_counts[evidence.confidence] += 1
        
        # Calculate high confidence percentage
        high_pct = (confidence_counts["high"] / total_params * 100) if total_params > 0 else 0.0
        
        return {
            "total_sources": len(self._sources),
            "total_parameters": total_params,
            "confidence_breakdown": confidence_counts,
            "high_confidence_pct": high_pct
        }
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the entire registry to a dictionary.
        
        Returns:
            Dict with 'sources' and 'parameter_evidence' keys
        """
        return {
            "sources": [s.to_dict() for s in self._sources.values()],
            "parameter_evidence": [e.to_dict() for e in self._evidence]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceRegistry":
        """
        Create a registry from a dictionary.
        
        Args:
            data: Dict with 'sources' and 'parameter_evidence' keys
            
        Returns:
            New EvidenceRegistry instance
        """
        registry = cls()
        
        # Load sources first
        for source_data in data.get("sources", []):
            registry.add_source(EvidenceSource.from_dict(source_data))
        
        # Load parameter evidence
        for evidence_data in data.get("parameter_evidence", []):
            registry.add_parameter_evidence(ParameterEvidence.from_dict(evidence_data))
        
        return registry


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_source_from_doi(
    source_id: str,
    doi: str,
    title: str,
    authors: List[str],
    year: int,
    journal: Optional[str] = None,
    source_type: str = "peer_reviewed"
) -> EvidenceSource:
    """
    Convenience function to create a peer-reviewed source.
    
    Args:
        source_id: Unique identifier
        doi: DOI string
        title: Paper title
        authors: List of author names
        year: Publication year
        journal: Journal name
        source_type: Source classification
        
    Returns:
        EvidenceSource instance
    """
    return EvidenceSource(
        source_id=source_id,
        doi=doi,
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        source_type=source_type
    )


def create_database_source(
    source_id: str,
    title: str,
    organization: str,
    year: int,
    url: str
) -> EvidenceSource:
    """
    Convenience function to create a database source.
    
    Args:
        source_id: Unique identifier
        title: Database name
        organization: Responsible organization
        year: Year accessed/updated
        url: URL to database
        
    Returns:
        EvidenceSource instance
    """
    return EvidenceSource(
        source_id=source_id,
        doi=None,
        title=title,
        authors=[organization],
        journal=None,
        year=year,
        source_type="database",
        url=url
    )
