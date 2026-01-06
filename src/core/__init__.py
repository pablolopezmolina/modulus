# src/core/__init__.py
# MODULUS Core Module

from .engine import (
    SimulationEngine,
    SimulationConfig,
    ProductComposition,
    PopulationResults,
    IndividualResult,
)

from .population import (
    PopulationGenerator,
    GenerationConfig,
    VirtualPerson,
    create_reference_person,
    create_test_person,
)

from .models import (
    DallaManModel,
    DallaManParams,
    GlucoseInput,
    EliteCaffeineModel,
    CaffeineParams,
    CaffeineInput,
)

from .adapters import (
    GlucoseModelAdapter,
    CaffeineModelAdapter,
    MealEffectConfig,
    create_adapters,
)

__all__ = [
    # Engine
    "SimulationEngine",
    "SimulationConfig",
    "ProductComposition",
    "PopulationResults",
    "IndividualResult",
    # Population
    "PopulationGenerator",
    "GenerationConfig",
    "VirtualPerson",
    "create_reference_person",
    "create_test_person",
    # Models
    "DallaManModel",
    "DallaManParams",
    "GlucoseInput",
    "EliteCaffeineModel",
    "CaffeineParams",
    "CaffeineInput",
    # Adapters
    "GlucoseModelAdapter",
    "CaffeineModelAdapter",
    "MealEffectConfig",
    "create_adapters",
]
