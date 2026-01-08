"""
MODULUS Consumer Web App

White-label, mobile-first web application for consumer-facing
supplement personalization.

Session 15.x - FASE 5: Pack 3 (€250-500k/year)
"""

from .personalization import (
    UserInput,
    ProductConfig,
    PersonalizationResult,
    PersonalizationEngine,
    CaffeineSensitivity,
    create_engine_with_products,
    quick_personalize
)

from .config import (
    BrandConfig,
    AppConfig,
    PRESET_BRANDS,
    get_brand_config
)

__all__ = [
    # Personalization
    "UserInput",
    "ProductConfig", 
    "PersonalizationResult",
    "PersonalizationEngine",
    "CaffeineSensitivity",
    "create_engine_with_products",
    "quick_personalize",
    # Config
    "BrandConfig",
    "AppConfig",
    "PRESET_BRANDS",
    "get_brand_config"
]

__version__ = "1.0.0"
