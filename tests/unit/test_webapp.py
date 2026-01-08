"""
Tests for MODULUS Consumer Web App - Session 15.x

Tests cover:
- PersonalizationEngine (timing optimization, dosage adjustment, warnings)
- BrandConfig (white label configuration)
- ProductConfig (product-specific settings)
- API endpoints
"""
import pytest
from datetime import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# PERSONALIZATION ENGINE TESTS
# =============================================================================

class TestUserInput:
    """Tests for UserInput dataclass validation."""
    
    def test_valid_user_input(self):
        """UserInput accepts valid data."""
        from src.webapp.personalization import UserInput
        
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        assert user.weight_kg == 75.0
        assert user.wake_time == "07:00"
        assert user.activity_time == "18:00"
        assert user.caffeine_sensitivity == "normal"
    
    def test_user_input_rejects_invalid_weight(self):
        """UserInput rejects weight outside range."""
        from src.webapp.personalization import UserInput
        
        with pytest.raises(ValueError):
            UserInput(
                weight_kg=500.0,  # Too heavy
                wake_time="07:00",
                activity_time="18:00",
                caffeine_sensitivity="normal"
            )
        
        with pytest.raises(ValueError):
            UserInput(
                weight_kg=10.0,  # Too light
                wake_time="07:00",
                activity_time="18:00",
                caffeine_sensitivity="normal"
            )
    
    def test_user_input_rejects_invalid_time_format(self):
        """UserInput rejects invalid time format."""
        from src.webapp.personalization import UserInput
        
        with pytest.raises(ValueError):
            UserInput(
                weight_kg=75.0,
                wake_time="7:00",  # Missing leading zero
                activity_time="18:00",
                caffeine_sensitivity="normal"
            )
    
    def test_user_input_rejects_invalid_caffeine_sensitivity(self):
        """UserInput rejects invalid caffeine sensitivity."""
        from src.webapp.personalization import UserInput
        
        with pytest.raises(ValueError):
            UserInput(
                weight_kg=75.0,
                wake_time="07:00",
                activity_time="18:00",
                caffeine_sensitivity="ultra_fast"  # Invalid
            )
    
    def test_user_input_with_optional_fields(self):
        """UserInput handles optional fields."""
        from src.webapp.personalization import UserInput
        
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal",
            age=35,
            has_eaten=True,
            sleep_target_time="23:00"
        )
        
        assert user.age == 35
        assert user.has_eaten is True
        assert user.sleep_target_time == "23:00"


class TestPersonalizationResult:
    """Tests for PersonalizationResult dataclass."""
    
    def test_result_structure(self):
        """PersonalizationResult has correct structure."""
        from src.webapp.personalization import PersonalizationResult
        
        result = PersonalizationResult(
            optimal_timing="17:15",
            dosage_multiplier=1.0,
            warnings=[],
            expected_effects={
                "alertness_peak": "~45 min after intake",
                "duration": "4-6 hours",
                "sleep_impact": "minimal"
            },
            recommendations=[
                "Take with food for sustained release"
            ]
        )
        
        assert result.optimal_timing == "17:15"
        assert result.dosage_multiplier == 1.0
        assert result.warnings == []
        assert "alertness_peak" in result.expected_effects
        assert len(result.recommendations) == 1
    
    def test_result_to_dict(self):
        """PersonalizationResult serializes to dict."""
        from src.webapp.personalization import PersonalizationResult
        
        result = PersonalizationResult(
            optimal_timing="17:15",
            dosage_multiplier=1.0,
            warnings=["Consider lower dose"],
            expected_effects={"peak": "45 min"},
            recommendations=[]
        )
        
        d = result.to_dict()
        
        assert isinstance(d, dict)
        assert d["optimal_timing"] == "17:15"
        assert d["dosage_multiplier"] == 1.0
        assert "Consider lower dose" in d["warnings"]


class TestTimingCalculator:
    """Tests for timing optimization logic."""
    
    def test_pre_workout_timing_normal_sensitivity(self):
        """Normal caffeine sensitivity: 45-60 min before activity."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        result = engine.calculate_optimal_timing(user, caffeine_mg=200)
        
        # Should be 45-60 min before 18:00 = 17:00-17:15
        timing_parts = result.split(":")
        hour = int(timing_parts[0])
        minute = int(timing_parts[1])
        
        # Activity at 18:00, timing should be 17:00-17:15
        assert hour == 17
        assert 0 <= minute <= 20  # 45-60 min before
    
    def test_pre_workout_timing_slow_metabolizer(self):
        """Slow metabolizer: earlier timing (60-90 min before)."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="slow"
        )
        
        result = engine.calculate_optimal_timing(user, caffeine_mg=200)
        
        # Slow metabolizer: should be earlier, maybe 16:30-17:00
        timing_parts = result.split(":")
        hour = int(timing_parts[0])
        
        # Should be at least 60 min before (17:00 or earlier)
        assert hour <= 17
    
    def test_pre_workout_timing_fast_metabolizer(self):
        """Fast metabolizer: later timing (30-45 min before)."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="fast"
        )
        
        result = engine.calculate_optimal_timing(user, caffeine_mg=200)
        
        # Fast metabolizer: should be later, maybe 17:15-17:30
        timing_parts = result.split(":")
        hour = int(timing_parts[0])
        minute = int(timing_parts[1])
        
        # Should be 30-45 min before (17:15-17:30)
        assert hour == 17
        assert minute >= 10  # Closer to activity time
    
    def test_sleep_protection_warning(self):
        """Late activity triggers sleep warning."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="21:00",  # Late evening
            caffeine_sensitivity="normal",
            sleep_target_time="23:00"
        )
        
        result = engine.personalize("test_product", user)
        
        # Should warn about sleep disruption
        assert any("sleep" in w.lower() for w in result.warnings)
    
    def test_no_sleep_warning_for_morning_activity(self):
        """Morning activity doesn't trigger sleep warning."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="06:00",
            activity_time="08:00",  # Morning
            caffeine_sensitivity="normal"
        )
        
        result = engine.personalize("test_product", user)
        
        # Should NOT have sleep warning
        sleep_warnings = [w for w in result.warnings if "sleep" in w.lower()]
        assert len(sleep_warnings) == 0


class TestDosageAdjustment:
    """Tests for dosage adjustment based on user characteristics."""
    
    def test_weight_based_adjustment_heavy(self):
        """Heavy users may need higher dose."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=120.0,  # Heavy
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        result = engine.personalize("test_product", user)
        
        # Heavier person might get multiplier > 1.0
        assert result.dosage_multiplier >= 1.0
    
    def test_weight_based_adjustment_light(self):
        """Light users may need lower dose."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=50.0,  # Light
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        result = engine.personalize("test_product", user)
        
        # Lighter person might get multiplier < 1.0
        assert result.dosage_multiplier <= 1.0
    
    def test_sensitivity_adjustment_slow(self):
        """Slow metabolizers should get lower dose recommendation."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="slow"
        )
        
        result = engine.personalize("test_product", user)
        
        # Slow metabolizer should have reduced dose OR warning
        assert result.dosage_multiplier <= 1.0 or any("sensitive" in w.lower() or "reduce" in w.lower() for w in result.warnings)
    
    def test_dosage_multiplier_bounds(self):
        """Dosage multiplier stays within safe bounds."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        
        # Test extreme cases
        for weight in [40.0, 150.0]:
            for sensitivity in ["slow", "normal", "fast"]:
                user = UserInput(
                    weight_kg=weight,
                    wake_time="07:00",
                    activity_time="18:00",
                    caffeine_sensitivity=sensitivity
                )
                
                result = engine.personalize("test_product", user)
                
                # Multiplier should be in safe range [0.5, 1.5]
                assert 0.5 <= result.dosage_multiplier <= 1.5


class TestWarningGeneration:
    """Tests for warning generation."""
    
    def test_fasted_state_warning(self):
        """Not eating generates fasted state warning."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal",
            has_eaten=False
        )
        
        result = engine.personalize("test_product", user)
        
        # Should recommend eating or warn about absorption/empty stomach
        all_messages = result.warnings + result.recommendations
        has_fasted_message = any(
            "food" in w.lower() or 
            "eat" in w.lower() or 
            "absorb" in w.lower() or
            "empty stomach" in w.lower() or
            "snack" in w.lower()
            for w in all_messages
        )
        assert has_fasted_message, f"Expected fasted state message in: {all_messages}"
    
    def test_high_dose_warning(self):
        """High caffeine products get appropriate warnings."""
        from src.webapp.personalization import PersonalizationEngine, UserInput, ProductConfig
        
        engine = PersonalizationEngine()
        
        # Register high-caffeine product
        engine.register_product(ProductConfig(
            product_id="high_caff",
            name="Extreme Energy",
            caffeine_mg=400,  # Very high
            has_theanine=False,
            other_stimulants_mg=0,
            serving_instructions="Mix with water"
        ))
        
        user = UserInput(
            weight_kg=60.0,  # Light person
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="slow"  # Sensitive
        )
        
        result = engine.personalize("high_caff", user)
        
        # Should have warning about high dose
        assert any("dose" in w.lower() or "reduce" in w.lower() or "high" in w.lower() 
                   for w in result.warnings)
    
    def test_synergistic_product_benefit(self):
        """Products with L-theanine get noted as smoother."""
        from src.webapp.personalization import PersonalizationEngine, UserInput, ProductConfig
        
        engine = PersonalizationEngine()
        
        # Register balanced product
        engine.register_product(ProductConfig(
            product_id="balanced",
            name="Smooth Energy",
            caffeine_mg=150,
            has_theanine=True,  # Has L-theanine
            other_stimulants_mg=0,
            serving_instructions="Take with water"
        ))
        
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        result = engine.personalize("balanced", user)
        
        # Should mention smooth/balanced energy in effects
        effects_text = str(result.expected_effects).lower()
        assert "smooth" in effects_text or "balanced" in effects_text or "reduced jitter" in effects_text


# =============================================================================
# BRAND CONFIG TESTS
# =============================================================================

class TestBrandConfig:
    """Tests for white-label brand configuration."""
    
    def test_brand_config_creation(self):
        """BrandConfig accepts valid configuration."""
        from src.webapp.config import BrandConfig
        
        config = BrandConfig(
            brand_id="acme_nutrition",
            brand_name="ACME Nutrition",
            primary_color="#FF6B00",
            secondary_color="#1A1A2E",
            logo_url="https://acme.com/logo.png",
            footer_text="© 2025 ACME Nutrition"
        )
        
        assert config.brand_id == "acme_nutrition"
        assert config.primary_color == "#FF6B00"
    
    def test_brand_config_default_colors(self):
        """BrandConfig has sensible defaults."""
        from src.webapp.config import BrandConfig
        
        config = BrandConfig(
            brand_id="minimal",
            brand_name="Minimal Brand"
        )
        
        # Should have default colors
        assert config.primary_color is not None
        assert config.secondary_color is not None
    
    def test_brand_config_color_validation(self):
        """BrandConfig validates hex color format."""
        from src.webapp.config import BrandConfig
        
        # Valid hex colors should work
        config = BrandConfig(
            brand_id="test",
            brand_name="Test",
            primary_color="#FF6B00"
        )
        assert config.primary_color == "#FF6B00"
        
        # 3-char hex should also work
        config = BrandConfig(
            brand_id="test2",
            brand_name="Test",
            primary_color="#F60"
        )
        assert config.primary_color == "#F60"
    
    def test_brand_config_to_css_vars(self):
        """BrandConfig generates CSS variables."""
        from src.webapp.config import BrandConfig
        
        config = BrandConfig(
            brand_id="test",
            brand_name="Test Brand",
            primary_color="#FF6B00",
            secondary_color="#1A1A2E"
        )
        
        css_vars = config.to_css_vars()
        
        assert "--primary-color" in css_vars
        assert "#FF6B00" in css_vars
        assert "--secondary-color" in css_vars


class TestProductConfig:
    """Tests for product configuration."""
    
    def test_product_config_creation(self):
        """ProductConfig accepts valid data."""
        from src.webapp.personalization import ProductConfig
        
        product = ProductConfig(
            product_id="energy_pro",
            name="Energy Pro Max",
            caffeine_mg=200,
            has_theanine=True,
            other_stimulants_mg=50,
            serving_instructions="Mix 1 scoop with 8oz water"
        )
        
        assert product.product_id == "energy_pro"
        assert product.caffeine_mg == 200
        assert product.has_theanine is True
    
    def test_product_config_optional_fields(self):
        """ProductConfig handles optional fields."""
        from src.webapp.personalization import ProductConfig
        
        product = ProductConfig(
            product_id="simple",
            name="Simple Energy",
            caffeine_mg=100,
            has_theanine=False,
            other_stimulants_mg=0,
            serving_instructions="Take 1 capsule",
            description="Basic energy supplement",
            typical_timing_before_min=45,
            max_daily_servings=2
        )
        
        assert product.description == "Basic energy supplement"
        assert product.typical_timing_before_min == 45
        assert product.max_daily_servings == 2


# =============================================================================
# RESPONSE TIME TESTS
# =============================================================================

class TestResponseTime:
    """Tests to ensure <100ms response time."""
    
    def test_personalization_is_fast(self):
        """Personalization completes in <100ms."""
        import time
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        # Warm up
        engine.personalize("test_product", user)
        
        # Time multiple calls
        times = []
        for _ in range(10):
            start = time.time()
            engine.personalize("test_product", user)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should be well under 100ms
        assert max_time < 0.1, f"Max time {max_time*1000:.1f}ms exceeds 100ms"
        assert avg_time < 0.05, f"Avg time {avg_time*1000:.1f}ms is too high"


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================

class TestSerialization:
    """Tests for JSON serialization."""
    
    def test_user_input_from_dict(self):
        """UserInput can be created from dict."""
        from src.webapp.personalization import UserInput
        
        data = {
            "weight_kg": 75.0,
            "wake_time": "07:00",
            "activity_time": "18:00",
            "caffeine_sensitivity": "normal"
        }
        
        user = UserInput.from_dict(data)
        
        assert user.weight_kg == 75.0
        assert user.wake_time == "07:00"
    
    def test_personalization_result_json_safe(self):
        """PersonalizationResult can be JSON serialized."""
        import json
        from src.webapp.personalization import PersonalizationResult
        
        result = PersonalizationResult(
            optimal_timing="17:15",
            dosage_multiplier=1.0,
            warnings=["Take with food"],
            expected_effects={"peak": "45 min"},
            recommendations=["Stay hydrated"]
        )
        
        # Should serialize without error
        json_str = json.dumps(result.to_dict())
        
        # Should deserialize correctly
        data = json.loads(json_str)
        assert data["optimal_timing"] == "17:15"


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_midnight_activity(self):
        """Handle activity at midnight."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="20:00",  # Night shift worker
            activity_time="00:30",  # Just after midnight
            caffeine_sensitivity="normal"
        )
        
        result = engine.personalize("test_product", user)
        
        # Should still produce valid result
        assert result.optimal_timing is not None
        assert ":" in result.optimal_timing
    
    def test_same_time_wake_and_activity(self):
        """Handle wake time same as activity time."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="06:00",
            activity_time="06:00",  # Immediate activity
            caffeine_sensitivity="fast"
        )
        
        result = engine.personalize("test_product", user)
        
        # Should recommend taking before wake (night before) or upon waking
        assert result.optimal_timing is not None
        # Should have recommendation about early timing
        assert len(result.recommendations) > 0 or result.optimal_timing <= "06:00"
    
    def test_very_early_activity(self):
        """Handle very early morning activity."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="04:00",
            activity_time="04:30",  # 30 min after waking
            caffeine_sensitivity="normal"
        )
        
        result = engine.personalize("test_product", user)
        
        # Should handle gracefully
        assert result.optimal_timing is not None
        # Timing should be around or before wake time
        timing_hour = int(result.optimal_timing.split(":")[0])
        assert timing_hour <= 4
    
    def test_unknown_product_raises_error(self):
        """Unknown product ID raises appropriate error."""
        from src.webapp.personalization import PersonalizationEngine, UserInput
        
        engine = PersonalizationEngine()
        user = UserInput(
            weight_kg=75.0,
            wake_time="07:00",
            activity_time="18:00",
            caffeine_sensitivity="normal"
        )
        
        with pytest.raises(KeyError):
            engine.personalize("nonexistent_product_xyz", user)


# =============================================================================
# PRODUCT REGISTRY TESTS
# =============================================================================

class TestProductRegistry:
    """Tests for product registration and lookup."""
    
    def test_register_and_retrieve_product(self):
        """Can register and retrieve product."""
        from src.webapp.personalization import PersonalizationEngine, ProductConfig
        
        engine = PersonalizationEngine()
        
        product = ProductConfig(
            product_id="custom_blend",
            name="Custom Blend",
            caffeine_mg=175,
            has_theanine=True,
            other_stimulants_mg=25,
            serving_instructions="Mix with water"
        )
        
        engine.register_product(product)
        
        # Should be able to retrieve
        retrieved = engine.get_product("custom_blend")
        assert retrieved.name == "Custom Blend"
        assert retrieved.caffeine_mg == 175
    
    def test_list_registered_products(self):
        """Can list all registered products."""
        from src.webapp.personalization import PersonalizationEngine, ProductConfig
        
        engine = PersonalizationEngine()
        
        # Register a few products
        for i in range(3):
            engine.register_product(ProductConfig(
                product_id=f"product_{i}",
                name=f"Product {i}",
                caffeine_mg=100 + i*50,
                has_theanine=i % 2 == 0,
                other_stimulants_mg=0,
                serving_instructions="Take as directed"
            ))
        
        products = engine.list_products()
        
        # Should include all registered plus default test product
        assert len(products) >= 3
        assert "product_0" in products
        assert "product_1" in products
        assert "product_2" in products
    
    def test_update_existing_product(self):
        """Registering same ID updates the product."""
        from src.webapp.personalization import PersonalizationEngine, ProductConfig
        
        engine = PersonalizationEngine()
        
        # Register initial
        engine.register_product(ProductConfig(
            product_id="updatable",
            name="Version 1",
            caffeine_mg=100,
            has_theanine=False,
            other_stimulants_mg=0,
            serving_instructions="V1"
        ))
        
        # Update
        engine.register_product(ProductConfig(
            product_id="updatable",
            name="Version 2",
            caffeine_mg=150,
            has_theanine=True,
            other_stimulants_mg=25,
            serving_instructions="V2"
        ))
        
        retrieved = engine.get_product("updatable")
        assert retrieved.name == "Version 2"
        assert retrieved.caffeine_mg == 150
        assert retrieved.has_theanine is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
