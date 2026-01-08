"""
Compound Profile - defines PK/PD properties of an ingredient.

Contract 3.1 Compliance:
- compound_id must be unique snake_case
- pk_model: one_compartment | two_compartment | saturable
- pd_model: emax | linear | threshold | none
- bioavailability: [0, 1]
- evidence_level: high | medium | low | theoretical
- dose_unit: mg | g | mcg
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any
import re


# Valid values for enum-like fields
VALID_PK_MODELS = {"one_compartment", "two_compartment", "saturable"}
VALID_PD_MODELS = {"emax", "linear", "threshold", "none"}
VALID_EVIDENCE_LEVELS = {"high", "medium", "low", "theoretical"}
VALID_DOSE_UNITS = {"mg", "g", "mcg"}

# Expanded target systems for 15 compounds (Tier 1 + Tier 2)
# - Original: glucose, caffeine, adenosine, cortisol, energy, muscle, neural, none
# - Added for Tier 2: focus (theanine, tyrosine, alpha-gpc), blood_flow (citrulline),
#                     cognitive (tyrosine, alpha-gpc), relaxation (magnesium),
#                     general (taurine, vitamins), performance (beta-alanine, creatine)
VALID_TARGET_SYSTEMS = {
    # Core physiological systems
    "glucose",      # Carbohydrates, affects blood glucose
    "caffeine",     # Caffeine/adenosine system
    "adenosine",    # Adenosine receptor system
    "cortisol",     # HPA axis, stress response (ashwagandha)
    
    # Performance & energy
    "energy",       # General energy metabolism
    "performance",  # Exercise performance (creatine, beta-alanine)
    "muscle",       # Muscle-specific effects
    
    # Cognitive & neural
    "neural",       # General neural effects
    "cognitive",    # Cognitive performance (tyrosine, alpha-gpc)
    "focus",        # Focus/attention (theanine)
    
    # Other systems
    "blood_flow",   # Vascular/NO system (citrulline)
    "relaxation",   # Relaxation/GABA (magnesium)
    "general",      # Non-specific/cofactor (vitamins, taurine)
    
    # Placeholder
    "none",         # No specific target system
}


def _validate_snake_case(value: str, field_name: str) -> None:
    """Validate that a string is snake_case."""
    pattern = r'^[a-z][a-z0-9_]*$'
    if not re.match(pattern, value):
        raise ValueError(
            f"{field_name} must be snake_case (lowercase, underscores), got: {value}"
        )


@dataclass(frozen=True)
class CompoundProfile:
    """
    Profile of a compound/ingredient with PK/PD parameters.
    
    Contract 3.1:
    - compound_id: unique snake_case identifier
    - pk_model: one_compartment, two_compartment, or saturable
    - pd_model: emax, linear, threshold, or none
    - bioavailability: [0, 1]
    - evidence_level: high, medium, low, or theoretical
    - dose_unit: mg, g, or mcg
    
    Example:
        >>> caffeine = CompoundProfile(
        ...     compound_id="caffeine",
        ...     name="Caffeine",
        ...     category="stimulant",
        ...     pk_model="one_compartment",
        ...     pk_params={"half_life_hours": 5.0},
        ...     bioavailability=0.99,
        ...     pd_model="emax",
        ...     pd_params={"emax": 100, "ec50_mg_l": 2.5},
        ...     target_system="adenosine",
        ...     max_single_dose=400,
        ...     max_daily_dose=600,
        ...     dose_unit="mg",
        ...     evidence_level="high",
        ...     primary_sources=["10.1016/0024-3205(83)90546-3"],
        ... )
    """
    
    # === Required fields (no defaults) ===
    
    # Identification
    compound_id: str
    name: str
    category: str
    
    # Pharmacokinetics
    pk_model: str
    
    # Pharmacodynamics
    pd_model: str
    
    # Dose limits
    max_single_dose: float
    max_daily_dose: float
    
    # Target system
    target_system: str
    
    # === Optional fields (with defaults) ===
    
    # PK/PD parameters
    pk_params: Dict[str, Any] = field(default_factory=dict)
    pd_params: Dict[str, Any] = field(default_factory=dict)
    
    # Other optional
    bioavailability: float = 1.0
    dose_unit: str = "mg"
    evidence_level: str = "theoretical"
    primary_sources: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate all fields after initialization."""
        # Validate compound_id is snake_case
        _validate_snake_case(self.compound_id, "compound_id")
        
        # Validate name is not empty
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        
        # Validate pk_model
        if self.pk_model not in VALID_PK_MODELS:
            raise ValueError(
                f"pk_model must be one of {VALID_PK_MODELS}, got: {self.pk_model}"
            )
        
        # Validate pd_model
        if self.pd_model not in VALID_PD_MODELS:
            raise ValueError(
                f"pd_model must be one of {VALID_PD_MODELS}, got: {self.pd_model}"
            )
        
        # Validate bioavailability
        if not 0 <= self.bioavailability <= 1:
            raise ValueError(
                f"bioavailability must be in [0, 1], got: {self.bioavailability}"
            )
        
        # Validate target_system
        if self.target_system not in VALID_TARGET_SYSTEMS:
            raise ValueError(
                f"target_system must be one of {VALID_TARGET_SYSTEMS}, got: {self.target_system}"
            )
        
        # Validate dose limits
        if self.max_single_dose <= 0:
            raise ValueError(
                f"max_single_dose must be > 0, got: {self.max_single_dose}"
            )
        if self.max_daily_dose <= 0:
            raise ValueError(
                f"max_daily_dose must be > 0, got: {self.max_daily_dose}"
            )
        
        # Validate dose_unit
        if self.dose_unit not in VALID_DOSE_UNITS:
            raise ValueError(
                f"dose_unit must be one of {VALID_DOSE_UNITS}, got: {self.dose_unit}"
            )
        
        # Validate evidence_level
        if self.evidence_level not in VALID_EVIDENCE_LEVELS:
            raise ValueError(
                f"evidence_level must be one of {VALID_EVIDENCE_LEVELS}, "
                f"got: {self.evidence_level}"
            )
    
    # =========================================================================
    # Serialization
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
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
        """Create from dictionary."""
        return cls(
            compound_id=data["compound_id"],
            name=data["name"],
            category=data["category"],
            pk_model=data["pk_model"],
            pk_params=data.get("pk_params", {}),
            bioavailability=data.get("bioavailability", 1.0),
            pd_model=data["pd_model"],
            pd_params=data.get("pd_params", {}),
            target_system=data.get("target_system", "none"),
            max_single_dose=data["max_single_dose"],
            max_daily_dose=data["max_daily_dose"],
            dose_unit=data.get("dose_unit", "mg"),
            evidence_level=data.get("evidence_level", "theoretical"),
            primary_sources=data.get("primary_sources", []),
        )
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_pk_param(self, param_name: str, default: Any = None) -> Any:
        """Get a PK parameter with optional default."""
        return self.pk_params.get(param_name, default)
    
    def get_pd_param(self, param_name: str, default: Any = None) -> Any:
        """Get a PD parameter with optional default."""
        return self.pd_params.get(param_name, default)
    
    @property
    def has_high_evidence(self) -> bool:
        """Check if compound has high evidence level."""
        return self.evidence_level == "high"
    
    @property
    def source_count(self) -> int:
        """Number of primary sources."""
        return len(self.primary_sources)
    
    def __repr__(self) -> str:
        return (
            f"CompoundProfile(id={self.compound_id!r}, "
            f"name={self.name!r}, "
            f"evidence={self.evidence_level})"
        )
