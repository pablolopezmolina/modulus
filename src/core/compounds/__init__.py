"""
Compounds module - ingredient library and profiles.

Provides:
- CompoundProfile: Dataclass for compound PK/PD properties
- IngredientLibrary: Collection of compounds loaded from JSON

Contract 3.1: CompoundProfile validation
Contract 3.2: IngredientLibrary interface
"""

from .profile import (
    CompoundProfile,
    VALID_PK_MODELS,
    VALID_PD_MODELS,
    VALID_EVIDENCE_LEVELS,
    VALID_DOSE_UNITS,
    VALID_TARGET_SYSTEMS,
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
    "VALID_TARGET_SYSTEMS",
]
