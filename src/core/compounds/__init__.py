"""
Compounds module - Ingredient library and compound profiles.

This module provides:
- CompoundProfile: Data model for supplement ingredients (Contract 3.1)
- IngredientLibrary: Database of compound profiles (Contract 3.2)

Example:
    from src.core.compounds import CompoundProfile, IngredientLibrary
    
    # Load library from JSON
    library = IngredientLibrary("data/reference/ingredients.json")
    
    # Get a specific compound
    caffeine = library.get_compound("caffeine")
    print(caffeine.bioavailability)  # 0.99
    
    # List all compounds
    all_ids = library.list_compounds()
    
    # List compounds by category
    stimulants = library.list_compounds(category="stimulant")
"""
from .profile import (
    CompoundProfile,
    VALID_PK_MODELS,
    VALID_PD_MODELS,
    VALID_EVIDENCE_LEVELS,
    VALID_DOSE_UNITS,
)
from .library import IngredientLibrary

__all__ = [
    # Main classes
    "CompoundProfile",
    "IngredientLibrary",
    # Constants for validation
    "VALID_PK_MODELS",
    "VALID_PD_MODELS",
    "VALID_EVIDENCE_LEVELS",
    "VALID_DOSE_UNITS",
]
