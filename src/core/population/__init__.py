# src/core/population/__init__.py
# MODULUS — Population Module
#
# Este módulo proporciona generación de poblaciones virtuales para
# simulaciones metabólicas a escala.

from .person import VirtualPerson, create_reference_person, create_test_person
from .generator import PopulationGenerator, GenerationConfig
from .distributions import (
    PopulationDistributions,
    LatinHypercubeSampler,
    CorrelationMatrix,
    DistributionSpec,
    sample_distribution,
)

__all__ = [
    # Person
    "VirtualPerson",
    "create_reference_person",
    "create_test_person",
    # Generator
    "PopulationGenerator",
    "GenerationConfig",
    # Distributions
    "PopulationDistributions",
    "LatinHypercubeSampler",
    "CorrelationMatrix",
    "DistributionSpec",
    "sample_distribution",
]
