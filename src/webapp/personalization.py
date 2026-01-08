"""
MODULUS Consumer Web App - Personalization Engine

Fast (<100ms) personalization logic for consumer-facing recommendations.
Does NOT run full 24h simulation - uses heuristic-based calculations.

Session 15.1 - FASE 5: Pack 3
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import re


# =============================================================================
# ENUMS
# =============================================================================

class CaffeineSensitivity(str, Enum):
    """Caffeine metabolism speed based on CYP1A2 genotype."""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UserInput:
    """
    User input for personalization.
    
    Validated to ensure safe ranges and proper formats.
    """
    weight_kg: float
    wake_time: str  # Format: "HH:MM" (24h)
    activity_time: str  # Format: "HH:MM" (24h)
    caffeine_sensitivity: str  # "slow" | "normal" | "fast"
    
    # Optional fields
    age: Optional[int] = None
    has_eaten: Optional[bool] = None
    sleep_target_time: Optional[str] = None  # Format: "HH:MM"
    
    def __post_init__(self):
        """Validate all fields."""
        # Weight validation (30-250 kg is reasonable human range)
        if not 30.0 <= self.weight_kg <= 250.0:
            raise ValueError(f"Weight must be between 30-250 kg, got {self.weight_kg}")
        
        # Time format validation (HH:MM)
        time_pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
        
        if not re.match(time_pattern, self.wake_time):
            raise ValueError(f"wake_time must be in HH:MM format, got '{self.wake_time}'")
        
        if not re.match(time_pattern, self.activity_time):
            raise ValueError(f"activity_time must be in HH:MM format, got '{self.activity_time}'")
        
        if self.sleep_target_time and not re.match(time_pattern, self.sleep_target_time):
            raise ValueError(f"sleep_target_time must be in HH:MM format, got '{self.sleep_target_time}'")
        
        # Caffeine sensitivity validation
        valid_sensitivities = ["slow", "normal", "fast"]
        if self.caffeine_sensitivity not in valid_sensitivities:
            raise ValueError(
                f"caffeine_sensitivity must be one of {valid_sensitivities}, "
                f"got '{self.caffeine_sensitivity}'"
            )
        
        # Age validation (if provided)
        if self.age is not None and not 13 <= self.age <= 120:
            raise ValueError(f"Age must be between 13-120, got {self.age}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserInput":
        """Create UserInput from dictionary."""
        return cls(
            weight_kg=float(data["weight_kg"]),
            wake_time=data["wake_time"],
            activity_time=data["activity_time"],
            caffeine_sensitivity=data["caffeine_sensitivity"],
            age=data.get("age"),
            has_eaten=data.get("has_eaten"),
            sleep_target_time=data.get("sleep_target_time")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "weight_kg": self.weight_kg,
            "wake_time": self.wake_time,
            "activity_time": self.activity_time,
            "caffeine_sensitivity": self.caffeine_sensitivity
        }
        if self.age is not None:
            result["age"] = self.age
        if self.has_eaten is not None:
            result["has_eaten"] = self.has_eaten
        if self.sleep_target_time is not None:
            result["sleep_target_time"] = self.sleep_target_time
        return result


@dataclass
class ProductConfig:
    """
    Product configuration for personalization.
    
    Defines the characteristics of a supplement product.
    """
    product_id: str
    name: str
    caffeine_mg: float
    has_theanine: bool
    other_stimulants_mg: float
    serving_instructions: str
    
    # Optional fields
    description: Optional[str] = None
    typical_timing_before_min: int = 45  # Default: 45 min before activity
    max_daily_servings: int = 2
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate product config."""
        if self.caffeine_mg < 0:
            raise ValueError("caffeine_mg cannot be negative")
        if self.other_stimulants_mg < 0:
            raise ValueError("other_stimulants_mg cannot be negative")
        if self.typical_timing_before_min < 0:
            raise ValueError("typical_timing_before_min cannot be negative")


@dataclass
class PersonalizationResult:
    """
    Result of personalization calculation.
    
    Contains timing, dosage adjustments, warnings, and expected effects.
    """
    optimal_timing: str  # Format: "HH:MM"
    dosage_multiplier: float  # 1.0 = standard serving
    warnings: List[str]
    expected_effects: Dict[str, str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "optimal_timing": self.optimal_timing,
            "dosage_multiplier": self.dosage_multiplier,
            "warnings": self.warnings,
            "expected_effects": self.expected_effects,
            "recommendations": self.recommendations
        }


# =============================================================================
# PERSONALIZATION ENGINE
# =============================================================================

class PersonalizationEngine:
    """
    Fast personalization engine for consumer recommendations.
    
    Uses heuristic-based calculations instead of full simulation
    to achieve <100ms response times.
    """
    
    # Reference weight for dosage calculations
    REFERENCE_WEIGHT_KG = 70.0
    
    # Timing offsets by caffeine sensitivity (minutes before activity)
    TIMING_OFFSETS = {
        "slow": 75,    # Slower metabolism = take earlier
        "normal": 50,  # Standard timing
        "fast": 35     # Fast metabolism = take closer to activity
    }
    
    # Half-life estimates by sensitivity (hours)
    HALF_LIFE_ESTIMATES = {
        "slow": 8.0,
        "normal": 5.0,
        "fast": 3.0
    }
    
    # Dosage multiplier bounds
    MIN_MULTIPLIER = 0.5
    MAX_MULTIPLIER = 1.5
    
    def __init__(self):
        """Initialize engine with default test product."""
        self._products: Dict[str, ProductConfig] = {}
        
        # Register default test product
        self.register_product(ProductConfig(
            product_id="test_product",
            name="Test Energy",
            caffeine_mg=200,
            has_theanine=False,
            other_stimulants_mg=0,
            serving_instructions="Mix with water"
        ))
    
    def register_product(self, product: ProductConfig) -> None:
        """Register or update a product configuration."""
        self._products[product.product_id] = product
    
    def get_product(self, product_id: str) -> ProductConfig:
        """Get product configuration by ID."""
        if product_id not in self._products:
            raise KeyError(f"Product not found: {product_id}")
        return self._products[product_id]
    
    def list_products(self) -> List[str]:
        """List all registered product IDs."""
        return list(self._products.keys())
    
    def calculate_optimal_timing(
        self, 
        user: UserInput, 
        caffeine_mg: float = 200
    ) -> str:
        """
        Calculate optimal intake timing based on user characteristics.
        
        Returns time in "HH:MM" format.
        """
        # Parse activity time
        activity_hour, activity_min = map(int, user.activity_time.split(":"))
        activity_total_min = activity_hour * 60 + activity_min
        
        # Get base offset based on caffeine sensitivity
        base_offset = self.TIMING_OFFSETS.get(user.caffeine_sensitivity, 50)
        
        # Adjust for caffeine dose (higher dose = take slightly earlier)
        dose_factor = caffeine_mg / 200.0  # Normalize to 200mg
        dose_adjustment = int((dose_factor - 1.0) * 10)  # +/- 10 min per 200mg diff
        
        # Calculate optimal time
        optimal_min = activity_total_min - base_offset - dose_adjustment
        
        # Handle wrap-around (negative times = previous day)
        if optimal_min < 0:
            optimal_min += 1440  # Add 24 hours
        
        # Handle midnight wrap-around
        optimal_min = optimal_min % 1440
        
        # Convert back to HH:MM
        optimal_hour = optimal_min // 60
        optimal_minute = optimal_min % 60
        
        return f"{optimal_hour:02d}:{optimal_minute:02d}"
    
    def calculate_dosage_multiplier(
        self, 
        user: UserInput, 
        product: ProductConfig
    ) -> float:
        """
        Calculate dosage adjustment based on user characteristics.
        
        Returns multiplier (1.0 = standard serving).
        """
        multiplier = 1.0
        
        # Weight-based adjustment
        weight_ratio = user.weight_kg / self.REFERENCE_WEIGHT_KG
        
        # Apply gentle weight scaling (not linear)
        # Lighter people: slightly reduce
        # Heavier people: slightly increase
        if weight_ratio < 0.8:  # < 56 kg
            multiplier *= 0.75 + (weight_ratio * 0.25)
        elif weight_ratio > 1.3:  # > 91 kg
            multiplier *= 1.0 + ((weight_ratio - 1.0) * 0.15)
        
        # Sensitivity adjustment
        if user.caffeine_sensitivity == "slow":
            multiplier *= 0.85  # Reduce for slow metabolizers
        elif user.caffeine_sensitivity == "fast":
            multiplier *= 1.1   # Can handle slightly more
        
        # Age adjustment (if provided)
        if user.age is not None:
            if user.age > 60:
                multiplier *= 0.85  # Reduce for older users
            elif user.age < 25:
                multiplier *= 1.05  # Young adults can handle more
        
        # Clamp to safe range
        multiplier = max(self.MIN_MULTIPLIER, min(self.MAX_MULTIPLIER, multiplier))
        
        return round(multiplier, 2)
    
    def generate_warnings(
        self, 
        user: UserInput, 
        product: ProductConfig,
        optimal_timing: str
    ) -> List[str]:
        """Generate relevant warnings for the user."""
        warnings = []
        
        # Parse times for calculations
        activity_hour, activity_min = map(int, user.activity_time.split(":"))
        activity_total_min = activity_hour * 60 + activity_min
        
        timing_hour, timing_min = map(int, optimal_timing.split(":"))
        timing_total_min = timing_hour * 60 + timing_min
        
        # Sleep warning for late caffeine intake
        sleep_target_min = None
        if user.sleep_target_time:
            sleep_hour, sleep_min = map(int, user.sleep_target_time.split(":"))
            sleep_target_min = sleep_hour * 60 + sleep_min
            if sleep_target_min < 360:  # Midnight or later, assume next day
                sleep_target_min += 1440
        else:
            # Assume 23:00 as default sleep target
            sleep_target_min = 23 * 60
        
        # Calculate hours before sleep
        hours_before_sleep = (sleep_target_min - timing_total_min) / 60
        if timing_total_min > sleep_target_min:
            hours_before_sleep = (sleep_target_min + 1440 - timing_total_min) / 60
        
        # Half-life based sleep impact
        half_life = self.HALF_LIFE_ESTIMATES.get(user.caffeine_sensitivity, 5.0)
        
        # If timing is within 2 half-lives of sleep, warn
        if hours_before_sleep < half_life * 2:
            if user.caffeine_sensitivity == "slow":
                warnings.append(
                    "⚠️ Sleep Warning: As a slow caffeine metabolizer, this timing may "
                    "affect your sleep. Consider reducing the dose or taking earlier."
                )
            else:
                warnings.append(
                    "⚠️ Late intake may affect sleep quality. Consider taking earlier "
                    "or reducing the dose."
                )
        
        # High caffeine warning
        total_stimulants = product.caffeine_mg + product.other_stimulants_mg
        if total_stimulants > 300:
            warnings.append(
                f"⚠️ High stimulant content ({total_stimulants}mg total). "
                "Consider starting with half a serving."
            )
        
        # Slow metabolizer with high dose
        if user.caffeine_sensitivity == "slow" and product.caffeine_mg > 150:
            warnings.append(
                "⚠️ As a caffeine-sensitive individual, consider reducing "
                "the dose to avoid overstimulation."
            )
        
        # Add product-specific warnings
        warnings.extend(product.warnings)
        
        return warnings
    
    def generate_recommendations(
        self, 
        user: UserInput, 
        product: ProductConfig
    ) -> List[str]:
        """Generate helpful recommendations."""
        recommendations = []
        
        # Fasted state recommendation
        if user.has_eaten is False:
            recommendations.append(
                "💡 Taking on an empty stomach may cause faster absorption but "
                "also potential stomach discomfort. Consider having a light snack."
            )
        elif user.has_eaten is None:
            recommendations.append(
                "💡 For sustained energy, consider taking with food."
            )
        
        # Hydration reminder
        recommendations.append("💧 Stay well hydrated throughout your activity.")
        
        # L-theanine benefit note
        if product.has_theanine:
            recommendations.append(
                "✨ This product contains L-theanine for smoother, focused energy "
                "with reduced jitters."
            )
        
        # First-time user tip
        if product.caffeine_mg > 200:
            recommendations.append(
                "🆕 If this is your first time, consider starting with half a serving "
                "to assess your tolerance."
            )
        
        return recommendations
    
    def generate_expected_effects(
        self, 
        user: UserInput, 
        product: ProductConfig
    ) -> Dict[str, str]:
        """Generate expected effects description."""
        effects = {}
        
        # Peak effect timing
        if user.caffeine_sensitivity == "fast":
            effects["alertness_peak"] = "~30-45 minutes after intake"
        elif user.caffeine_sensitivity == "slow":
            effects["alertness_peak"] = "~60-90 minutes after intake"
        else:
            effects["alertness_peak"] = "~45-60 minutes after intake"
        
        # Duration
        half_life = self.HALF_LIFE_ESTIMATES.get(user.caffeine_sensitivity, 5.0)
        if half_life > 6:
            effects["duration"] = "6-8 hours (you metabolize caffeine slowly)"
        elif half_life < 4:
            effects["duration"] = "3-4 hours (you metabolize caffeine quickly)"
        else:
            effects["duration"] = "4-6 hours"
        
        # Energy profile
        if product.has_theanine:
            effects["energy_profile"] = "Smooth, focused energy with reduced jitters"
        elif product.caffeine_mg > 200:
            effects["energy_profile"] = "Strong energy boost - may feel intense initially"
        else:
            effects["energy_profile"] = "Moderate energy boost"
        
        # Sleep impact
        sleep_target_min = 23 * 60  # Default 23:00
        if user.sleep_target_time:
            h, m = map(int, user.sleep_target_time.split(":"))
            sleep_target_min = h * 60 + m
        
        activity_h, activity_m = map(int, user.activity_time.split(":"))
        activity_min = activity_h * 60 + activity_m
        
        hours_to_sleep = (sleep_target_min - activity_min) / 60
        if hours_to_sleep < 0:
            hours_to_sleep += 24
        
        if hours_to_sleep > half_life * 2.5:
            effects["sleep_impact"] = "Minimal - caffeine should clear well before bedtime"
        elif hours_to_sleep > half_life * 1.5:
            effects["sleep_impact"] = "Low - some caffeine may remain but unlikely to affect sleep"
        else:
            effects["sleep_impact"] = "Moderate to High - may affect sleep quality"
        
        return effects
    
    def personalize(
        self, 
        product_id: str, 
        user: UserInput
    ) -> PersonalizationResult:
        """
        Generate personalized recommendations for a user and product.
        
        This is the main entry point for personalization.
        """
        # Get product config
        product = self.get_product(product_id)
        
        # Calculate optimal timing
        optimal_timing = self.calculate_optimal_timing(user, product.caffeine_mg)
        
        # Calculate dosage multiplier
        dosage_multiplier = self.calculate_dosage_multiplier(user, product)
        
        # Generate warnings
        warnings = self.generate_warnings(user, product, optimal_timing)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(user, product)
        
        # Generate expected effects
        expected_effects = self.generate_expected_effects(user, product)
        
        return PersonalizationResult(
            optimal_timing=optimal_timing,
            dosage_multiplier=dosage_multiplier,
            warnings=warnings,
            expected_effects=expected_effects,
            recommendations=recommendations
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_engine_with_products(products: List[ProductConfig]) -> PersonalizationEngine:
    """Create an engine pre-loaded with products."""
    engine = PersonalizationEngine()
    for product in products:
        engine.register_product(product)
    return engine


def quick_personalize(
    product_id: str,
    weight_kg: float,
    wake_time: str,
    activity_time: str,
    caffeine_sensitivity: str = "normal",
    **kwargs
) -> Dict[str, Any]:
    """
    Quick personalization with minimal setup.
    
    Returns dict ready for JSON response.
    """
    engine = PersonalizationEngine()
    
    user = UserInput(
        weight_kg=weight_kg,
        wake_time=wake_time,
        activity_time=activity_time,
        caffeine_sensitivity=caffeine_sensitivity,
        **kwargs
    )
    
    result = engine.personalize(product_id, user)
    return result.to_dict()
