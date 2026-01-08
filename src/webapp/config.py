"""
MODULUS Consumer Web App - Brand Configuration

White-label configuration for customizing the web app appearance
for different brand partners.

Session 15.1 - FASE 5: Pack 3
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import re


# =============================================================================
# BRAND CONFIG
# =============================================================================

@dataclass
class BrandConfig:
    """
    White-label brand configuration.
    
    Allows customization of colors, logos, and text for each brand partner.
    """
    brand_id: str
    brand_name: str
    
    # Colors (hex format)
    primary_color: str = "#6366F1"      # Indigo
    secondary_color: str = "#1E1B4B"    # Dark indigo
    accent_color: str = "#22D3EE"       # Cyan
    background_color: str = "#0F0E1A"   # Near black
    text_color: str = "#FFFFFF"         # White
    
    # Optional branding
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    footer_text: Optional[str] = None
    privacy_url: Optional[str] = None
    terms_url: Optional[str] = None
    
    # Custom messages
    welcome_message: Optional[str] = None
    tagline: Optional[str] = None
    
    def __post_init__(self):
        """Validate color formats."""
        color_pattern = r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$"
        
        for attr in ["primary_color", "secondary_color", "accent_color", 
                     "background_color", "text_color"]:
            color = getattr(self, attr)
            if not re.match(color_pattern, color):
                raise ValueError(f"Invalid hex color format for {attr}: {color}")
    
    def to_css_vars(self) -> str:
        """Generate CSS custom properties for theming."""
        return f"""
:root {{
    --primary-color: {self.primary_color};
    --secondary-color: {self.secondary_color};
    --accent-color: {self.accent_color};
    --background-color: {self.background_color};
    --text-color: {self.text_color};
    --primary-rgb: {self._hex_to_rgb(self.primary_color)};
    --accent-rgb: {self._hex_to_rgb(self.accent_color)};
}}
"""
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB values for CSS."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "logo_url": self.logo_url,
            "favicon_url": self.favicon_url,
            "footer_text": self.footer_text or f"© 2025 {self.brand_name}",
            "privacy_url": self.privacy_url,
            "terms_url": self.terms_url,
            "welcome_message": self.welcome_message or f"Welcome to {self.brand_name}",
            "tagline": self.tagline or "Personalized for you"
        }


# =============================================================================
# APP CONFIG
# =============================================================================

@dataclass
class AppConfig:
    """
    Global application configuration.
    """
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    
    # Default brand (used when no brand specified)
    default_brand: BrandConfig = field(
        default_factory=lambda: BrandConfig(
            brand_id="modulus",
            brand_name="MODULUS",
            tagline="Personalized Supplement Timing"
        )
    )
    
    # Feature flags
    enable_analytics: bool = True
    enable_feedback: bool = True
    require_consent: bool = True
    
    # Cache settings
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # Rate limiting
    max_requests_per_minute: int = 60


# =============================================================================
# PRESET BRANDS
# =============================================================================

# Example brand configurations for demo purposes
PRESET_BRANDS = {
    "modulus": BrandConfig(
        brand_id="modulus",
        brand_name="MODULUS",
        primary_color="#6366F1",
        secondary_color="#1E1B4B",
        accent_color="#22D3EE",
        tagline="The Science of Supplements"
    ),
    "energyx": BrandConfig(
        brand_id="energyx",
        brand_name="EnergyX",
        primary_color="#FF6B00",
        secondary_color="#1A1A2E",
        accent_color="#FFD700",
        tagline="Fuel Your Performance"
    ),
    "vitaboost": BrandConfig(
        brand_id="vitaboost",
        brand_name="VitaBoost",
        primary_color="#10B981",
        secondary_color="#064E3B",
        accent_color="#34D399",
        tagline="Natural Energy, Optimized"
    ),
    "peakform": BrandConfig(
        brand_id="peakform",
        brand_name="Peak Form",
        primary_color="#EF4444",
        secondary_color="#7F1D1D",
        accent_color="#FCA5A5",
        tagline="Achieve Your Peak"
    )
}


def get_brand_config(brand_id: str) -> BrandConfig:
    """Get brand configuration by ID, or return default."""
    return PRESET_BRANDS.get(brand_id, PRESET_BRANDS["modulus"])
