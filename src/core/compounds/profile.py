"""
CompoundProfile - Ingredient/compound data model.

Implements Contract 3.1: CompoundProfile from CONTRACTS.md.

A CompoundProfile contains all pharmacokinetic and pharmacodynamic 
parameters for a supplement ingredient.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any
import re


# Valid values for enum-like fields
VALID_PK_MODELS = frozenset(["one_compartment", "two_compartment", "saturable"])
VALID_PD_MODELS = frozenset(["emax", "linear", "threshold", "none"])
VALID_EVIDENCE_LEVELS = frozenset(["high", "medium", "low", "theoretical"])
VALID_DOSE_UNITS = frozenset(["mg", "g", "mcg"])

# Snake case pattern: lowercase letters, numbers, and underscores only
SNAKE_CASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')


def _validate_snake_case(value: str, field_name: str) -> None:
    """Validate that a string is in snake_case format."""
    if not SNAKE_CASE_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must be in snake_case format (lowercase letters, "
            f"numbers, and underscores only, starting with a letter). Got: '{value}'"
        )


def _validate_range(value: float, min_val: float, max_val: float, field_name: str) -> None:
    """Validate that a value is within a range [min_val, max_val]."""
    if value < min_val or value > max_val:
        raise ValueError(
            f"{field_name} must be between {min_val} and {max_val}. Got: {value}"
        )


def _validate_positive(value: float, field_name: str) -> None:
    """Validate that a value is positive (> 0)."""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive (> 0). Got: {value}")


def _validate_enum(value: str, valid_values: frozenset, field_name: str) -> None:
    """Validate that a value is in a set of valid values."""
    if value not in valid_values:
        raise ValueError(
            f"{field_name} must be one of {sorted(valid_values)}. Got: '{value}'"
        )


@dataclass
class CompoundProfile:
    """
    Profile for a supplement compound with PK/PD parameters.
    
    Implements Contract 3.1 from CONTRACTS.md.
    
    Attributes:
        compound_id: Unique identifier in snake_case (e.g., "caffeine", "l_theanine")
        name: Human-readable name (e.g., "Caffeine", "L-Theanine")
        category: Compound category (e.g., "stimulant", "amino", "vitamin")
        
        pk_model: Pharmacokinetic model type
        pk_params: Parameters for the PK model
        bioavailability: Fraction absorbed (0-1)
        
        pd_model: Pharmacodynamic model type
        pd_params: Parameters for the PD model
        target_system: Physiological system affected (e.g., "alertness", "glucose")
        
        max_single_dose: Maximum safe single dose
        max_daily_dose: Maximum safe daily dose
        dose_unit: Unit for doses ("mg", "g", "mcg")
        
        evidence_level: Quality of evidence ("high", "medium", "low", "theoretical")
        primary_sources: List of DOIs or references
    
    Contract 3.1 Requirements:
        - compound_id MUST be unique in the library (enforced by IngredientLibrary)
        - pk_params MUST contain parameters required for pk_model
        - pd_params MUST contain parameters required for pd_model
        - bioavailability MUST be in [0, 1]
    """
    # Required fields (no defaults) - must come first
    compound_id: str
    name: str
    category: str
    pk_model: str
    pd_model: str
    
    # Optional fields with defaults
    pk_params: Dict[str, float] = field(default_factory=dict)
    bioavailability: float = 1.0
    pd_params: Dict[str, float] = field(default_factory=dict)
    target_system: str = "none"
    max_single_dose: float = 1000.0
    max_daily_dose: float = 2000.0
    dose_unit: str = "mg"
    evidence_level: str = "low"
    primary_sources: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate all fields after initialization."""
        # Validate compound_id is snake_case
        _validate_snake_case(self.compound_id, "compound_id")
        
        # Validate bioavailability is in [0, 1]
        _validate_range(self.bioavailability, 0.0, 1.0, "bioavailability")
        
        # Validate model types
        _validate_enum(self.pk_model, VALID_PK_MODELS, "pk_model")
        _validate_enum(self.pd_model, VALID_PD_MODELS, "pd_model")
        
        # Validate dose limits
        _validate_positive(self.max_single_dose, "max_single_dose")
        _validate_positive(self.max_daily_dose, "max_daily_dose")
        
        # Validate dose unit
        _validate_enum(self.dose_unit, VALID_DOSE_UNITS, "dose_unit")
        
        # Validate evidence level
        _validate_enum(self.evidence_level, VALID_EVIDENCE_LEVELS, "evidence_level")
        
        # Ensure primary_sources is a list
        if not isinstance(self.primary_sources, list):
            object.__setattr__(self, 'primary_sources', list(self.primary_sources))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary.
        
        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "compound_id": self.compound_id,
            "name": self.name,
            "category": self.category,
            "pk_model": self.pk_model,
            "pk_params": dict(self.pk_params),
            "bioavailability": self.bioavailability,
            "pd_model": self.pd_model,
            "pd_params": dict(self.pd_params),
            "target_system": self.target_system,
            "max_single_dose": self.max_single_dose,
            "max_daily_dose": self.max_daily_dose,
            "dose_unit": self.dose_unit,
            "evidence_level": self.evidence_level,
            "primary_sources": list(self.primary_sources),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompoundProfile":
        """
        Create CompoundProfile from dictionary.
        
        Args:
            data: Dictionary with compound profile data.
            
        Returns:
            New CompoundProfile instance.
            
        Raises:
            ValueError: If data is invalid.
        """
        return cls(
            compound_id=data["compound_id"],
            name=data["name"],
            category=data["category"],
            pk_model=data["pk_model"],
            pk_params=dict(data.get("pk_params", {})),
            bioavailability=float(data.get("bioavailability", 1.0)),
            pd_model=data["pd_model"],
            pd_params=dict(data.get("pd_params", {})),
            target_system=data.get("target_system", "none"),
            max_single_dose=float(data.get("max_single_dose", 1000.0)),
            max_daily_dose=float(data.get("max_daily_dose", 2000.0)),
            dose_unit=data.get("dose_unit", "mg"),
            evidence_level=data.get("evidence_level", "low"),
            primary_sources=list(data.get("primary_sources", [])),
        )
    
    def __repr__(self) -> str:
        return (
            f"CompoundProfile(compound_id='{self.compound_id}', "
            f"name='{self.name}', category='{self.category}')"
        )
