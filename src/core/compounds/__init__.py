# src/core/compounds/__init__.py
"""
Compounds module for MODULUS.

This module provides:
- CompoundProfile: Profile of a compound with PK/PD parameters
- IngredientLibrary: Library of compounds loaded from JSON
- Ingredient: A single ingredient with compound_id, amount, and unit
- ServingInfo: Serving size information
- ValidationResult: Result of formulation validation
- Formulation: A complete product formula with multiple ingredients
- create_simple_formulation: Convenience factory function
"""
from src.core.compounds.profile import CompoundProfile
from src.core.compounds.library import IngredientLibrary
from src.core.compounds.formulation import (
    Ingredient,
    ServingInfo,
    ValidationResult,
    Formulation,
    create_simple_formulation,
    VALID_UNITS,
    VALID_FORMS,
)

__all__ = [
    # Profile
    "CompoundProfile",
    # Library
    "IngredientLibrary",
    # Formulation
    "Ingredient",
    "ServingInfo",
    "ValidationResult",
    "Formulation",
    "create_simple_formulation",
    # Constants
    "VALID_UNITS",
    "VALID_FORMS",
]
