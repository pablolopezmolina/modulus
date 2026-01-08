"""
Interaction - Contract 3.3

Represents an interaction between two compounds.

Contract requirements:
- compound_a < compound_b (alphabetical order to avoid duplicates)
- modifier_type: "multiply" | "add" | "replace"
- interaction_type: "synergy" | "antagonism" | "absorption" | "metabolism"
- evidence_level: "high" | "medium" | "low" | "theoretical"
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple


# Valid values for enum-like fields
VALID_INTERACTION_TYPES = {"synergy", "antagonism", "absorption", "metabolism"}
VALID_MODIFIER_TYPES = {"multiply", "add", "replace"}
VALID_EVIDENCE_LEVELS = {"high", "medium", "low", "theoretical"}


@dataclass(frozen=True)
class Interaction:
    """
    Represents an interaction between two compounds.
    
    The interaction modifies a target parameter when both compounds
    are present in a formulation or simulation.
    
    Contract 3.3 specifies:
    - compound_a < compound_b alphabetically (enforced on creation)
    - modifier_type="multiply" implies modifier_value typically in [0.5, 2.0]
    - modifier_type="add" implies modifier_value in units of target_param
    
    Attributes:
        compound_a: First compound (alphabetically lower)
        compound_b: Second compound (alphabetically higher)
        interaction_type: Type of interaction (synergy/antagonism/absorption/metabolism)
        target_param: Parameter that gets modified (e.g., "jitter_risk")
        modifier_type: How to apply the modifier (multiply/add/replace)
        modifier_value: The value to apply
        dose_dependent: Whether the interaction depends on doses
        min_dose_a: Minimum dose of compound_a for interaction (if dose_dependent)
        min_dose_b: Minimum dose of compound_b for interaction (if dose_dependent)
        evidence_level: Quality of evidence (high/medium/low/theoretical)
        source: DOI or reference for the interaction
        description: Human-readable description (optional)
    """
    compound_a: str
    compound_b: str
    interaction_type: str
    target_param: str
    modifier_type: str
    modifier_value: float
    dose_dependent: bool
    evidence_level: str
    source: str
    min_dose_a: Optional[float] = None
    min_dose_b: Optional[float] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize the interaction."""
        # Normalize alphabetical order (Contract 3.3 requirement)
        # We stored originals in __new__, now swap if needed
        original_a = getattr(self, '_original_a', self.compound_a)
        original_b = getattr(self, '_original_b', self.compound_b)
        
        if original_a > original_b:
            # Swap to maintain alphabetical order
            # Since frozen, we use object.__setattr__
            object.__setattr__(self, 'compound_a', original_b)
            object.__setattr__(self, 'compound_b', original_a)
            # Also swap min_doses if both are present
            orig_min_a = self.min_dose_a
            orig_min_b = self.min_dose_b
            object.__setattr__(self, 'min_dose_a', orig_min_b)
            object.__setattr__(self, 'min_dose_b', orig_min_a)
        
        # Validate interaction_type
        if self.interaction_type not in VALID_INTERACTION_TYPES:
            raise ValueError(
                f"Invalid interaction_type: '{self.interaction_type}'. "
                f"Must be one of: {VALID_INTERACTION_TYPES}"
            )
        
        # Validate modifier_type
        if self.modifier_type not in VALID_MODIFIER_TYPES:
            raise ValueError(
                f"Invalid modifier_type: '{self.modifier_type}'. "
                f"Must be one of: {VALID_MODIFIER_TYPES}"
            )
        
        # Validate evidence_level
        if self.evidence_level not in VALID_EVIDENCE_LEVELS:
            raise ValueError(
                f"Invalid evidence_level: '{self.evidence_level}'. "
                f"Must be one of: {VALID_EVIDENCE_LEVELS}"
            )
        
        # Validate dose thresholds if dose_dependent
        if self.dose_dependent:
            if self.min_dose_a is not None and self.min_dose_a < 0:
                raise ValueError("min_dose_a cannot be negative")
            if self.min_dose_b is not None and self.min_dose_b < 0:
                raise ValueError("min_dose_b cannot be negative")
    
    def __new__(cls, compound_a: str, compound_b: str, **kwargs):
        """Store original compounds before potential swap."""
        instance = super().__new__(cls)
        # Store originals for swap detection in __post_init__
        object.__setattr__(instance, '_original_a', compound_a)
        object.__setattr__(instance, '_original_b', compound_b)
        return instance
    
    @property
    def key(self) -> Tuple[str, str]:
        """
        Unique key for this interaction pair.
        
        Always returns (compound_a, compound_b) in alphabetical order.
        """
        return (self.compound_a, self.compound_b)
    
    @property
    def is_synergistic(self) -> bool:
        """True if this is a synergistic interaction."""
        return self.interaction_type == "synergy"
    
    @property
    def is_antagonistic(self) -> bool:
        """True if this is an antagonistic interaction."""
        return self.interaction_type == "antagonism"
    
    def applies_at_doses(self, dose_a: float, dose_b: float) -> bool:
        """
        Check if this interaction applies at the given doses.
        
        For non-dose-dependent interactions, always returns True.
        For dose-dependent interactions, checks min_dose thresholds.
        
        Args:
            dose_a: Dose of compound_a in the same units as min_dose_a
            dose_b: Dose of compound_b in the same units as min_dose_b
            
        Returns:
            True if the interaction applies at these doses
        """
        if not self.dose_dependent:
            return True
        
        # Check min_dose_a threshold
        if self.min_dose_a is not None and dose_a < self.min_dose_a:
            return False
        
        # Check min_dose_b threshold
        if self.min_dose_b is not None and dose_b < self.min_dose_b:
            return False
        
        return True
    
    def apply_to(self, base_value: float) -> float:
        """
        Apply this interaction's modifier to a base value.
        
        Args:
            base_value: The original value to modify
            
        Returns:
            The modified value
        """
        if self.modifier_type == "multiply":
            return base_value * self.modifier_value
        elif self.modifier_type == "add":
            return base_value + self.modifier_value
        elif self.modifier_type == "replace":
            return self.modifier_value
        else:
            # Should not reach here due to validation
            return base_value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary.
        
        Returns:
            Dictionary representation suitable for JSON.
        """
        result = {
            "compound_a": self.compound_a,
            "compound_b": self.compound_b,
            "interaction_type": self.interaction_type,
            "target_param": self.target_param,
            "modifier_type": self.modifier_type,
            "modifier_value": self.modifier_value,
            "dose_dependent": self.dose_dependent,
            "evidence_level": self.evidence_level,
            "source": self.source,
        }
        
        # Include optional fields if present
        if self.min_dose_a is not None:
            result["min_dose_a"] = self.min_dose_a
        if self.min_dose_b is not None:
            result["min_dose_b"] = self.min_dose_b
        if self.description is not None:
            result["description"] = self.description
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Interaction":
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary with interaction data
            
        Returns:
            Interaction instance
        """
        return cls(
            compound_a=data["compound_a"],
            compound_b=data["compound_b"],
            interaction_type=data["interaction_type"],
            target_param=data["target_param"],
            modifier_type=data["modifier_type"],
            modifier_value=float(data["modifier_value"]),
            dose_dependent=data.get("dose_dependent", False),
            min_dose_a=data.get("min_dose_a"),
            min_dose_b=data.get("min_dose_b"),
            evidence_level=data.get("evidence_level", "medium"),
            source=data.get("source", ""),
            description=data.get("description"),
        )
    
    def __repr__(self) -> str:
        return (
            f"Interaction({self.compound_a} + {self.compound_b} → "
            f"{self.modifier_type} {self.target_param} by {self.modifier_value})"
        )


class ContextInteraction:
    """
    Represents a context-based interaction (not compound-compound).
    
    These are triggered by conditions like:
    - Total caffeine dose > 300mg → increased jitter
    - Caffeine after 14:00 → sleep disruption risk
    
    This is a simpler structure for single-compound context rules.
    """
    
    def __init__(
        self,
        compound_id: str,
        condition_type: str,  # "dose_threshold" | "time_window"
        condition_params: Dict[str, Any],
        target_param: str,
        modifier_type: str,
        modifier_value: float,
        evidence_level: str = "medium",
        source: str = "",
        description: Optional[str] = None
    ):
        self.compound_id = compound_id
        self.condition_type = condition_type
        self.condition_params = condition_params
        self.target_param = target_param
        self.modifier_type = modifier_type
        self.modifier_value = modifier_value
        self.evidence_level = evidence_level
        self.source = source
        self.description = description
    
    def check_condition(self, context: Dict[str, Any]) -> bool:
        """
        Check if the context satisfies this interaction's condition.
        
        Args:
            context: Dictionary with context information
                - For dose_threshold: {"total_caffeine_mg": 350}
                - For time_window: {"time_of_day_minutes": 900}
        
        Returns:
            True if condition is met
        """
        if self.condition_type == "dose_threshold":
            param_name = self.condition_params.get("param")
            threshold = self.condition_params.get("threshold", 0)
            operator = self.condition_params.get("operator", ">=")
            
            value = context.get(param_name, 0)
            
            if operator == ">=":
                return value >= threshold
            elif operator == ">":
                return value > threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == "<":
                return value < threshold
            else:
                return False
        
        elif self.condition_type == "time_window":
            start = self.condition_params.get("start_minutes", 0)
            end = self.condition_params.get("end_minutes", 1440)
            time = context.get("time_of_day_minutes", 0)
            return start <= time <= end
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "compound_id": self.compound_id,
            "condition_type": self.condition_type,
            "condition_params": self.condition_params,
            "target_param": self.target_param,
            "modifier_type": self.modifier_type,
            "modifier_value": self.modifier_value,
            "evidence_level": self.evidence_level,
            "source": self.source,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextInteraction":
        """Deserialize from dictionary."""
        return cls(
            compound_id=data["compound_id"],
            condition_type=data["condition_type"],
            condition_params=data["condition_params"],
            target_param=data["target_param"],
            modifier_type=data["modifier_type"],
            modifier_value=float(data["modifier_value"]),
            evidence_level=data.get("evidence_level", "medium"),
            source=data.get("source", ""),
            description=data.get("description"),
        )
