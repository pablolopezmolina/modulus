# src/core/compounds/formulation.py
"""
Formulation System (Sesión 4.3)

This module provides classes for representing product formulations:
- Ingredient: A single ingredient with compound_id, amount, and unit
- ServingInfo: Serving size and container information
- ValidationResult: Result of formulation validation
- Formulation: A complete product formula with multiple ingredients

Formulations can be validated against an IngredientLibrary and converted
to Timeline objects for simulation.

Contracts implemented:
- Produces Events according to Contract 2.1 (ingestion type)
- Produces Timeline according to Contract 2.2
- Uses IngredientLibrary according to Contract 3.2
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Set, TYPE_CHECKING

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from src.core.timeline import Timeline


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Valid units for ingredients
VALID_UNITS = frozenset(["mg", "g", "mcg", "ml", "iu"])

# Valid product forms
VALID_FORMS = frozenset(["powder", "capsule", "tablet", "liquid", "gummy", "bar"])

# Small offset between events in the same formulation (in minutes)
# 0.001 minutes = 0.06 seconds, negligible for simulation but avoids timestamp collision
EVENT_TIMESTAMP_OFFSET = 0.001


# ==============================================================================
# INGREDIENT
# ==============================================================================

@dataclass(frozen=True)
class Ingredient:
    """
    A single ingredient in a formulation.
    
    Immutable dataclass representing one ingredient with:
    - compound_id: Reference to a compound in the IngredientLibrary
    - amount: Quantity of the ingredient
    - unit: Unit of measurement (mg, g, mcg, ml, iu)
    
    Validates that amount is positive and unit is in the allowed list.
    """
    compound_id: str
    amount: float
    unit: str
    
    def __post_init__(self):
        """Validate ingredient on creation."""
        # Validate compound_id
        if not self.compound_id or not self.compound_id.strip():
            raise ValueError("compound_id cannot be empty")
        
        # Validate amount
        if self.amount <= 0:
            raise ValueError(f"amount must be positive, got {self.amount}")
        
        # Validate unit
        if self.unit not in VALID_UNITS:
            raise ValueError(f"unit must be one of {VALID_UNITS}, got '{self.unit}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "compound_id": self.compound_id,
            "amount": self.amount,
            "unit": self.unit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ingredient":
        """Create Ingredient from dictionary."""
        return cls(
            compound_id=data["compound_id"],
            amount=float(data["amount"]),
            unit=data["unit"]
        )


# ==============================================================================
# SERVING INFO
# ==============================================================================

@dataclass(frozen=True)
class ServingInfo:
    """
    Information about serving size and container.
    
    Immutable dataclass with:
    - serving_size: Number of units per serving (e.g., 1, 2)
    - serving_unit: Type of serving (e.g., "scoop", "capsule", "tablet")
    - servings_per_container: Optional number of servings in the container
    """
    serving_size: int
    serving_unit: str
    servings_per_container: Optional[int] = None
    
    def __post_init__(self):
        """Validate serving info on creation."""
        if self.serving_size <= 0:
            raise ValueError(f"serving_size must be positive, got {self.serving_size}")
        
        if not self.serving_unit or not self.serving_unit.strip():
            raise ValueError("serving_unit cannot be empty")
        
        if self.servings_per_container is not None and self.servings_per_container <= 0:
            raise ValueError(f"servings_per_container must be positive, got {self.servings_per_container}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = {
            "serving_size": self.serving_size,
            "serving_unit": self.serving_unit
        }
        if self.servings_per_container is not None:
            d["servings_per_container"] = self.servings_per_container
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServingInfo":
        """Create ServingInfo from dictionary."""
        return cls(
            serving_size=int(data["serving_size"]),
            serving_unit=data["serving_unit"],
            servings_per_container=data.get("servings_per_container")
        )


# ==============================================================================
# VALIDATION RESULT
# ==============================================================================

@dataclass(frozen=True)
class ValidationResult:
    """
    Result of validating a formulation against an IngredientLibrary.
    
    Immutable dataclass with:
    - is_valid: True if no errors (warnings are allowed)
    - errors: List of critical errors that make the formulation invalid
    - warnings: List of non-critical warnings
    """
    is_valid: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    
    def __init__(
        self,
        is_valid: bool,
        errors: List[str],
        warnings: List[str]
    ):
        """Initialize with lists, convert to tuples for immutability."""
        object.__setattr__(self, "is_valid", is_valid)
        object.__setattr__(self, "errors", tuple(errors))
        object.__setattr__(self, "warnings", tuple(warnings))


# ==============================================================================
# FORMULATION
# ==============================================================================

@dataclass(frozen=True)
class Formulation:
    """
    A complete product formulation.
    
    Immutable dataclass representing a supplement/food product with:
    - name: Product name
    - ingredients: Tuple of Ingredient objects
    - form: Product form (powder, capsule, tablet, liquid, gummy, bar)
    - serving_info: Serving size information
    - description: Optional product description
    - brand: Optional brand name
    
    Can be validated against an IngredientLibrary and converted to a Timeline
    for simulation.
    """
    name: str
    ingredients: Tuple[Ingredient, ...]
    form: str
    serving_info: ServingInfo
    description: Optional[str] = None
    brand: Optional[str] = None
    
    def __post_init__(self):
        """Validate formulation on creation."""
        # Validate name
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        
        # Validate ingredients
        if not self.ingredients or len(self.ingredients) == 0:
            raise ValueError("ingredients cannot be empty")
        
        # Validate form
        if self.form not in VALID_FORMS:
            raise ValueError(f"form must be one of {VALID_FORMS}, got '{self.form}'")
    
    def validate(self, library: Any) -> ValidationResult:
        """
        Validate formulation against an IngredientLibrary.
        
        Checks:
        1. All ingredients exist in the library
        2. Amounts don't exceed max_single_dose (warning)
        3. Units match the compound's dose_unit (warning)
        4. No duplicate ingredients (warning)
        
        Args:
            library: IngredientLibrary instance to validate against
            
        Returns:
            ValidationResult with is_valid, errors, and warnings
        """
        errors: List[str] = []
        warnings: List[str] = []
        seen_compounds: Set[str] = set()
        
        for ingredient in self.ingredients:
            compound_id = ingredient.compound_id
            
            # Check if compound exists
            try:
                compound = library.get_compound(compound_id)
            except KeyError:
                errors.append(f"Unknown compound: {compound_id}")
                continue
            
            # Check for duplicates
            if compound_id in seen_compounds:
                warnings.append(f"Duplicate ingredient: {compound_id}")
            seen_compounds.add(compound_id)
            
            # Check unit matches (if library provides dose_unit)
            if hasattr(compound, 'dose_unit'):
                if ingredient.unit != compound.dose_unit:
                    warnings.append(
                        f"Unit mismatch for {compound_id}: "
                        f"using '{ingredient.unit}', expected '{compound.dose_unit}'"
                    )
            
            # Check amount vs max_single_dose (if library provides it)
            if hasattr(compound, 'max_single_dose'):
                # Convert to same unit if possible for comparison
                amount_in_base = self._convert_to_base_unit(ingredient.amount, ingredient.unit)
                max_in_base = self._convert_to_base_unit(
                    compound.max_single_dose, 
                    getattr(compound, 'dose_unit', ingredient.unit)
                )
                
                if amount_in_base > max_in_base:
                    warnings.append(
                        f"{compound_id} amount ({ingredient.amount} {ingredient.unit}) "
                        f"exceeds max single dose ({compound.max_single_dose} {getattr(compound, 'dose_unit', '')})"
                    )
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
    
    def _convert_to_base_unit(self, amount: float, unit: str) -> float:
        """Convert amount to milligrams for comparison."""
        conversions = {
            "g": 1000.0,
            "mg": 1.0,
            "mcg": 0.001,
            "ml": 1.0,  # Assume 1ml = 1mg for liquids (rough)
            "iu": 1.0,  # Can't convert IU, keep as-is
        }
        return amount * conversions.get(unit, 1.0)
    
    def to_timeline(self, base_time_minutes: float = 0.0) -> "Timeline":
        """
        Convert formulation to a Timeline with ingestion events.
        
        Creates one ingestion event per ingredient. Since Timeline doesn't allow
        two events at exactly the same timestamp, each ingredient gets a tiny
        offset (0.001 min = 0.06 sec) to ensure unique timestamps while being
        essentially simultaneous for simulation purposes.
        
        Args:
            base_time_minutes: When the formulation is consumed (0-1440)
            
        Returns:
            Timeline with ingestion events for each ingredient
            
        Raises:
            ValueError: If base_time_minutes is outside 0-1440 range
        """
        # Validate base_time
        if base_time_minutes < 0 or base_time_minutes > 1440:
            raise ValueError(
                f"base_time_minutes must be in range [0, 1440], got {base_time_minutes}"
            )
        
        # Import from timeline module (Event is re-exported from contracts there)
        from src.core.timeline import Event, Timeline
        
        # Create Timeline and add events with tiny offsets to avoid timestamp collision
        timeline = Timeline()
        
        for i, ingredient in enumerate(self.ingredients):
            # Add tiny offset (0.001 min = 0.06 sec) per ingredient
            # This ensures unique timestamps while being essentially simultaneous
            timestamp = base_time_minutes + (i * EVENT_TIMESTAMP_OFFSET)
            
            # Create ingestion event according to Contract 2.1
            event = Event(
                timestamp_minutes=timestamp,
                event_type="ingestion",
                payload={
                    "compound_id": ingredient.compound_id,
                    "amount": ingredient.amount,
                    "unit": ingredient.unit,
                    "form": self.form
                }
            )
            timeline = timeline.add_event(event)
        
        return timeline
    
    def get_total_by_compound(self, compound_id: str) -> float:
        """
        Get total amount of a compound in the formulation.
        
        If a compound appears multiple times, sums the amounts.
        
        Args:
            compound_id: The compound to look for
            
        Returns:
            Total amount (in the ingredient's unit), or 0.0 if not found
        """
        total = 0.0
        for ingredient in self.ingredients:
            if ingredient.compound_id == compound_id:
                total += ingredient.amount
        return total
    
    def list_compound_ids(self) -> List[str]:
        """
        Get list of unique compound IDs in the formulation.
        
        Returns:
            List of unique compound_id strings
        """
        return list(set(ing.compound_id for ing in self.ingredients))
    
    def contains_compound(self, compound_id: str) -> bool:
        """
        Check if formulation contains a specific compound.
        
        Args:
            compound_id: The compound to check for
            
        Returns:
            True if the compound is in the formulation
        """
        return any(ing.compound_id == compound_id for ing in self.ingredients)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize formulation to dictionary."""
        d = {
            "name": self.name,
            "ingredients": [ing.to_dict() for ing in self.ingredients],
            "form": self.form,
            "serving_info": self.serving_info.to_dict()
        }
        if self.description is not None:
            d["description"] = self.description
        if self.brand is not None:
            d["brand"] = self.brand
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Formulation":
        """Create Formulation from dictionary."""
        ingredients = tuple(
            Ingredient.from_dict(ing) for ing in data["ingredients"]
        )
        serving_info = ServingInfo.from_dict(data["serving_info"])
        
        return cls(
            name=data["name"],
            ingredients=ingredients,
            form=data["form"],
            serving_info=serving_info,
            description=data.get("description"),
            brand=data.get("brand")
        )


# ==============================================================================
# CONVENIENCE FACTORY FUNCTIONS
# ==============================================================================

def create_simple_formulation(
    name: str,
    ingredients: List[Tuple[str, float, str]],
    form: str = "capsule"
) -> Formulation:
    """
    Create a formulation with simplified syntax.
    
    Args:
        name: Product name
        ingredients: List of (compound_id, amount, unit) tuples
        form: Product form (default: "capsule")
        
    Returns:
        Formulation object
        
    Example:
        >>> formulation = create_simple_formulation(
        ...     "Pre-Workout",
        ...     [("caffeine", 200, "mg"), ("l_theanine", 100, "mg")]
        ... )
    """
    ingredient_objects = tuple(
        Ingredient(compound_id=cid, amount=float(amt), unit=unit)
        for cid, amt, unit in ingredients
    )
    
    serving_info = ServingInfo(serving_size=1, serving_unit=form)
    
    return Formulation(
        name=name,
        ingredients=ingredient_objects,
        form=form,
        serving_info=serving_info
    )
