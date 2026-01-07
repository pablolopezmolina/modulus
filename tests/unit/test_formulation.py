# tests/unit/test_formulation.py
"""
Tests for Formulation System (Sesión 4.3)

Tests the Ingredient, ServingInfo, ValidationResult, and Formulation classes.
Verifies integration with IngredientLibrary and Timeline generation.
"""
import pytest
from dataclasses import FrozenInstanceError
from typing import List

# These imports will work in the real project
# For now, we define the expected interface

# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def mock_library():
    """
    Mock IngredientLibrary for testing.
    In real tests, this would use the actual library with ingredients.json
    """
    from src.core.compounds.library import IngredientLibrary
    import os
    
    # Try to use real library if available
    json_path = "data/reference/ingredients.json"
    if os.path.exists(json_path):
        return IngredientLibrary(json_path)
    
    # Fallback: create mock
    class MockLibrary:
        def __init__(self):
            self._compounds = {
                "caffeine": {"dose_unit": "mg", "max_single_dose": 400, "max_daily_dose": 600},
                "l_theanine": {"dose_unit": "mg", "max_single_dose": 400, "max_daily_dose": 600},
                "creatine_monohydrate": {"dose_unit": "g", "max_single_dose": 10, "max_daily_dose": 20},
                "carbohydrate_glucose": {"dose_unit": "g", "max_single_dose": 100, "max_daily_dose": 500},
            }
        
        def get_compound(self, compound_id: str):
            if compound_id not in self._compounds:
                raise KeyError(f"Compound not found: {compound_id}")
            
            from dataclasses import dataclass
            @dataclass
            class MockCompound:
                compound_id: str = compound_id
                dose_unit: str = self._compounds[compound_id]["dose_unit"]
                max_single_dose: float = self._compounds[compound_id]["max_single_dose"]
                max_daily_dose: float = self._compounds[compound_id]["max_daily_dose"]
            
            return MockCompound()
        
        def list_compounds(self, category=None):
            return list(self._compounds.keys())
        
        def has_compound(self, compound_id: str) -> bool:
            return compound_id in self._compounds
    
    return MockLibrary()


# ==============================================================================
# INGREDIENT TESTS
# ==============================================================================

class TestIngredient:
    """Tests for Ingredient dataclass."""
    
    def test_ingredient_creation_basic(self):
        """Ingredient can be created with basic parameters."""
        from src.core.compounds.formulation import Ingredient
        
        ing = Ingredient(
            compound_id="caffeine",
            amount=200.0,
            unit="mg"
        )
        
        assert ing.compound_id == "caffeine"
        assert ing.amount == 200.0
        assert ing.unit == "mg"
    
    def test_ingredient_is_frozen(self):
        """Ingredient is immutable (frozen dataclass)."""
        from src.core.compounds.formulation import Ingredient
        
        ing = Ingredient(compound_id="caffeine", amount=200.0, unit="mg")
        
        with pytest.raises(FrozenInstanceError):
            ing.amount = 300.0
    
    def test_ingredient_equality(self):
        """Two identical Ingredients are equal."""
        from src.core.compounds.formulation import Ingredient
        
        ing1 = Ingredient(compound_id="caffeine", amount=200.0, unit="mg")
        ing2 = Ingredient(compound_id="caffeine", amount=200.0, unit="mg")
        
        assert ing1 == ing2
    
    def test_ingredient_valid_units(self):
        """Ingredient validates unit is in allowed list."""
        from src.core.compounds.formulation import Ingredient
        
        # Valid units
        for unit in ["mg", "g", "mcg", "ml", "iu"]:
            ing = Ingredient(compound_id="test", amount=100.0, unit=unit)
            assert ing.unit == unit
    
    def test_ingredient_invalid_unit_raises(self):
        """Ingredient with invalid unit raises ValueError."""
        from src.core.compounds.formulation import Ingredient
        
        with pytest.raises(ValueError, match="unit"):
            Ingredient(compound_id="test", amount=100.0, unit="invalid")
    
    def test_ingredient_negative_amount_raises(self):
        """Ingredient with negative amount raises ValueError."""
        from src.core.compounds.formulation import Ingredient
        
        with pytest.raises(ValueError, match="amount"):
            Ingredient(compound_id="test", amount=-50.0, unit="mg")
    
    def test_ingredient_zero_amount_raises(self):
        """Ingredient with zero amount raises ValueError."""
        from src.core.compounds.formulation import Ingredient
        
        with pytest.raises(ValueError, match="amount"):
            Ingredient(compound_id="test", amount=0.0, unit="mg")
    
    def test_ingredient_empty_compound_id_raises(self):
        """Ingredient with empty compound_id raises ValueError."""
        from src.core.compounds.formulation import Ingredient
        
        with pytest.raises(ValueError, match="compound_id"):
            Ingredient(compound_id="", amount=100.0, unit="mg")
    
    def test_ingredient_to_dict(self):
        """Ingredient can be serialized to dict."""
        from src.core.compounds.formulation import Ingredient
        
        ing = Ingredient(compound_id="caffeine", amount=200.0, unit="mg")
        d = ing.to_dict()
        
        assert d == {
            "compound_id": "caffeine",
            "amount": 200.0,
            "unit": "mg"
        }
    
    def test_ingredient_from_dict(self):
        """Ingredient can be created from dict."""
        from src.core.compounds.formulation import Ingredient
        
        d = {"compound_id": "caffeine", "amount": 200.0, "unit": "mg"}
        ing = Ingredient.from_dict(d)
        
        assert ing.compound_id == "caffeine"
        assert ing.amount == 200.0
        assert ing.unit == "mg"


# ==============================================================================
# SERVING INFO TESTS
# ==============================================================================

class TestServingInfo:
    """Tests for ServingInfo dataclass."""
    
    def test_serving_info_creation(self):
        """ServingInfo can be created with parameters."""
        from src.core.compounds.formulation import ServingInfo
        
        info = ServingInfo(
            serving_size=1,
            serving_unit="scoop",
            servings_per_container=30
        )
        
        assert info.serving_size == 1
        assert info.serving_unit == "scoop"
        assert info.servings_per_container == 30
    
    def test_serving_info_is_frozen(self):
        """ServingInfo is immutable."""
        from src.core.compounds.formulation import ServingInfo
        
        info = ServingInfo(serving_size=1, serving_unit="scoop", servings_per_container=30)
        
        with pytest.raises(FrozenInstanceError):
            info.serving_size = 2
    
    def test_serving_info_optional_servings_per_container(self):
        """servings_per_container is optional."""
        from src.core.compounds.formulation import ServingInfo
        
        info = ServingInfo(serving_size=1, serving_unit="capsule")
        
        assert info.servings_per_container is None
    
    def test_serving_info_to_dict(self):
        """ServingInfo can be serialized to dict."""
        from src.core.compounds.formulation import ServingInfo
        
        info = ServingInfo(serving_size=2, serving_unit="capsules", servings_per_container=60)
        d = info.to_dict()
        
        assert d == {
            "serving_size": 2,
            "serving_unit": "capsules",
            "servings_per_container": 60
        }


# ==============================================================================
# VALIDATION RESULT TESTS
# ==============================================================================

class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_validation_result_valid(self):
        """ValidationResult for valid formulation."""
        from src.core.compounds.formulation import ValidationResult
        
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validation_result_with_warnings(self):
        """ValidationResult can have warnings while still valid."""
        from src.core.compounds.formulation import ValidationResult
        
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Caffeine dose is near maximum recommended"]
        )
        
        assert result.is_valid is True
        assert len(result.warnings) == 1
    
    def test_validation_result_with_errors(self):
        """ValidationResult with errors is not valid."""
        from src.core.compounds.formulation import ValidationResult
        
        result = ValidationResult(
            is_valid=False,
            errors=["Unknown compound: fake_compound"],
            warnings=[]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
    
    def test_validation_result_is_frozen(self):
        """ValidationResult is immutable."""
        from src.core.compounds.formulation import ValidationResult
        
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        with pytest.raises(FrozenInstanceError):
            result.is_valid = False


# ==============================================================================
# FORMULATION TESTS
# ==============================================================================

class TestFormulationCreation:
    """Tests for Formulation creation and basic properties."""
    
    def test_formulation_creation_basic(self):
        """Formulation can be created with basic parameters."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        ingredients = [
            Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
            Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
        ]
        
        serving = ServingInfo(serving_size=1, serving_unit="scoop")
        
        formulation = Formulation(
            name="Energy Blend",
            ingredients=tuple(ingredients),
            form="powder",
            serving_info=serving
        )
        
        assert formulation.name == "Energy Blend"
        assert len(formulation.ingredients) == 2
        assert formulation.form == "powder"
    
    def test_formulation_is_frozen(self):
        """Formulation is immutable."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test",
            ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        with pytest.raises(FrozenInstanceError):
            formulation.name = "Changed"
    
    def test_formulation_ingredients_must_be_tuple(self):
        """Formulation requires ingredients as tuple for immutability."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        # Should work with tuple
        formulation = Formulation(
            name="Test",
            ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        assert isinstance(formulation.ingredients, tuple)
    
    def test_formulation_valid_forms(self):
        """Formulation validates form is in allowed list."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        valid_forms = ["powder", "capsule", "tablet", "liquid", "gummy", "bar"]
        
        for form in valid_forms:
            formulation = Formulation(
                name="Test",
                ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
                form=form,
                serving_info=ServingInfo(serving_size=1, serving_unit="unit")
            )
            assert formulation.form == form
    
    def test_formulation_invalid_form_raises(self):
        """Formulation with invalid form raises ValueError."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        with pytest.raises(ValueError, match="form"):
            Formulation(
                name="Test",
                ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
                form="invalid_form",
                serving_info=ServingInfo(serving_size=1, serving_unit="unit")
            )
    
    def test_formulation_empty_name_raises(self):
        """Formulation with empty name raises ValueError."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        with pytest.raises(ValueError, match="name"):
            Formulation(
                name="",
                ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
                form="capsule",
                serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
            )
    
    def test_formulation_empty_ingredients_raises(self):
        """Formulation with no ingredients raises ValueError."""
        from src.core.compounds.formulation import Formulation, ServingInfo
        
        with pytest.raises(ValueError, match="ingredients"):
            Formulation(
                name="Empty Product",
                ingredients=(),
                form="capsule",
                serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
            )
    
    def test_formulation_optional_description(self):
        """Formulation can have optional description."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test",
            ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule"),
            description="A test product"
        )
        
        assert formulation.description == "A test product"
    
    def test_formulation_optional_brand(self):
        """Formulation can have optional brand."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Energy Pro",
            ingredients=(Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule"),
            brand="TestCorp"
        )
        
        assert formulation.brand == "TestCorp"


class TestFormulationValidation:
    """Tests for Formulation.validate() method."""
    
    def test_validate_all_ingredients_exist(self, mock_library):
        """Validation passes when all ingredients exist in library."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Valid Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        result = formulation.validate(mock_library)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_unknown_ingredient_error(self, mock_library):
        """Validation fails when ingredient doesn't exist in library."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Bad Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="fake_compound", amount=100.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        result = formulation.validate(mock_library)
        
        assert result.is_valid is False
        assert any("fake_compound" in err for err in result.errors)
    
    def test_validate_exceeds_max_single_dose_warning(self, mock_library):
        """Validation warns when ingredient exceeds max single dose."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="High Caffeine",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=500.0, unit="mg"),  # Max is 400mg
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        result = formulation.validate(mock_library)
        
        # Still valid but with warning
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("exceeds" in w.lower() or "max" in w.lower() for w in result.warnings)
    
    def test_validate_unit_mismatch_warning(self, mock_library):
        """Validation warns when ingredient unit doesn't match compound's dose_unit."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Wrong Unit",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=0.2, unit="g"),  # Should be mg
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        result = formulation.validate(mock_library)
        
        # Valid but with warning about unit
        assert len(result.warnings) > 0
        assert any("unit" in w.lower() for w in result.warnings)
    
    def test_validate_duplicate_ingredients_warning(self, mock_library):
        """Validation warns when same ingredient appears multiple times."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Duplicate Caffeine",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=50.0, unit="mg"),
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),  # Duplicate!
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        result = formulation.validate(mock_library)
        
        assert len(result.warnings) > 0
        assert any("duplicate" in w.lower() for w in result.warnings)


class TestFormulationToTimeline:
    """Tests for Formulation.to_timeline() method."""
    
    def test_to_timeline_creates_timeline(self, mock_library):
        """to_timeline creates a valid Timeline object."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        from src.core.timeline.timeline import Timeline
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        timeline = formulation.to_timeline(base_time_minutes=420)  # 7:00 AM
        
        assert isinstance(timeline, Timeline)
    
    def test_to_timeline_creates_ingestion_events(self, mock_library):
        """to_timeline creates ingestion events for each ingredient."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        timeline = formulation.to_timeline(base_time_minutes=420)
        events = timeline.events
        
        assert len(events) == 2
        
        # Check event types
        for event in events:
            assert event.event_type == "ingestion"
    
    def test_to_timeline_event_payloads_correct(self, mock_library):
        """to_timeline events have correct payload structure."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        timeline = formulation.to_timeline(base_time_minutes=420)
        event = timeline.events[0]
        
        # Check payload according to Contract 2.1
        assert event.payload["compound_id"] == "caffeine"
        assert event.payload["amount"] == 200.0
        assert event.payload["unit"] == "mg"
        assert event.payload["form"] == "capsule"
    
    def test_to_timeline_respects_base_time(self, mock_library):
        """to_timeline places events at approximately the specified base_time."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        timeline = formulation.to_timeline(base_time_minutes=600)  # 10:00 AM
        
        # First event is exactly at base_time
        assert timeline.events[0].timestamp_minutes == 600
    
    def test_to_timeline_default_base_time_is_zero(self, mock_library):
        """to_timeline defaults to base_time=0 if not specified."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        timeline = formulation.to_timeline()
        
        assert timeline.events[0].timestamp_minutes == 0
    
    def test_to_timeline_events_have_unique_timestamps(self, mock_library):
        """Events have unique timestamps (tiny offset between each)."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
                Ingredient(compound_id="carbohydrate_glucose", amount=30.0, unit="g"),
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop")
        )
        
        timeline = formulation.to_timeline(base_time_minutes=420)
        
        # All events should have unique timestamps
        timestamps = [e.timestamp_minutes for e in timeline.events]
        assert len(timestamps) == len(set(timestamps))  # All unique
        
        # But they should all be very close to the base time (within 1 minute)
        for ts in timestamps:
            assert 420 <= ts < 421  # All within 1 minute of base_time
    
    def test_to_timeline_validates_base_time_range(self, mock_library):
        """to_timeline raises error if base_time is out of 0-1440 range."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test Product",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        with pytest.raises(ValueError, match="base_time"):
            formulation.to_timeline(base_time_minutes=-10)
        
        with pytest.raises(ValueError, match="base_time"):
            formulation.to_timeline(base_time_minutes=1500)


class TestFormulationSerialization:
    """Tests for Formulation serialization."""
    
    def test_formulation_to_dict(self):
        """Formulation can be serialized to dict."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Energy Blend",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop", servings_per_container=30),
            description="Pre-workout energy blend",
            brand="TestCorp"
        )
        
        d = formulation.to_dict()
        
        assert d["name"] == "Energy Blend"
        assert d["form"] == "powder"
        assert len(d["ingredients"]) == 2
        assert d["serving_info"]["serving_unit"] == "scoop"
        assert d["description"] == "Pre-workout energy blend"
        assert d["brand"] == "TestCorp"
    
    def test_formulation_from_dict(self):
        """Formulation can be created from dict."""
        from src.core.compounds.formulation import Formulation
        
        d = {
            "name": "Energy Blend",
            "ingredients": [
                {"compound_id": "caffeine", "amount": 200.0, "unit": "mg"},
                {"compound_id": "l_theanine", "amount": 100.0, "unit": "mg"},
            ],
            "form": "powder",
            "serving_info": {
                "serving_size": 1,
                "serving_unit": "scoop",
                "servings_per_container": 30
            }
        }
        
        formulation = Formulation.from_dict(d)
        
        assert formulation.name == "Energy Blend"
        assert formulation.form == "powder"
        assert len(formulation.ingredients) == 2
        assert formulation.ingredients[0].compound_id == "caffeine"
    
    def test_formulation_roundtrip(self):
        """Formulation survives to_dict/from_dict roundtrip."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        original = Formulation(
            name="Energy Blend",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop", servings_per_container=30),
            description="Test",
            brand="TestCorp"
        )
        
        d = original.to_dict()
        restored = Formulation.from_dict(d)
        
        assert restored.name == original.name
        assert restored.form == original.form
        assert len(restored.ingredients) == len(original.ingredients)
        assert restored.serving_info.serving_unit == original.serving_info.serving_unit


class TestFormulationHelpers:
    """Tests for Formulation helper methods."""
    
    def test_get_total_by_compound(self, mock_library):
        """get_total_by_compound returns sum of amounts for a compound."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=50.0, unit="mg"),
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),  # Duplicate
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop")
        )
        
        total_caffeine = formulation.get_total_by_compound("caffeine")
        total_theanine = formulation.get_total_by_compound("l_theanine")
        
        assert total_caffeine == 200.0
        assert total_theanine == 50.0
    
    def test_get_total_by_compound_not_found(self, mock_library):
        """get_total_by_compound returns 0 for compound not in formula."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop")
        )
        
        total = formulation.get_total_by_compound("l_theanine")
        
        assert total == 0.0
    
    def test_list_compound_ids(self, mock_library):
        """list_compound_ids returns unique compound IDs."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=50.0, unit="mg"),
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),  # Duplicate
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop")
        )
        
        compounds = formulation.list_compound_ids()
        
        assert set(compounds) == {"caffeine", "l_theanine"}
    
    def test_contains_compound(self, mock_library):
        """contains_compound returns True if compound is in formula."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Test",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=50.0, unit="mg"),
            ),
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop")
        )
        
        assert formulation.contains_compound("caffeine") is True
        assert formulation.contains_compound("l_theanine") is True
        assert formulation.contains_compound("creatine") is False


class TestFormulationPreworkoutExample:
    """Integration test with realistic pre-workout formulation."""
    
    def test_realistic_preworkout(self, mock_library):
        """Create and validate a realistic pre-workout product."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        preworkout = Formulation(
            name="Energy Pro Max",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=200.0, unit="mg"),
                Ingredient(compound_id="l_theanine", amount=100.0, unit="mg"),
                Ingredient(compound_id="creatine_monohydrate", amount=5.0, unit="g"),
                Ingredient(compound_id="carbohydrate_glucose", amount=25.0, unit="g"),
            ),
            form="powder",
            serving_info=ServingInfo(
                serving_size=1,
                serving_unit="scoop",
                servings_per_container=30
            ),
            description="High-performance pre-workout blend",
            brand="ClientCorp"
        )
        
        # Validate against library
        result = preworkout.validate(mock_library)
        assert result.is_valid is True
        
        # Convert to timeline at 5:30 PM (17:30 = 1050 min)
        timeline = preworkout.to_timeline(base_time_minutes=1050)
        
        assert len(timeline.events) == 4
        
        # All events should be very close to base_time
        for e in timeline.events:
            assert 1050 <= e.timestamp_minutes < 1051
        
        # Check all events are ingestion type
        assert all(e.event_type == "ingestion" for e in timeline.events)
        
        # Verify caffeine event details
        caffeine_events = [e for e in timeline.events if e.payload["compound_id"] == "caffeine"]
        assert len(caffeine_events) == 1
        assert caffeine_events[0].payload["amount"] == 200.0
        assert caffeine_events[0].payload["form"] == "powder"


# ==============================================================================
# EDGE CASES
# ==============================================================================

class TestFormulationEdgeCases:
    """Edge case tests for Formulation."""
    
    def test_very_small_amount(self, mock_library):
        """Formulation handles very small amounts (mcg)."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Vitamin D",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=0.001, unit="mg"),  # 1 mcg
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        timeline = formulation.to_timeline()
        
        assert timeline.events[0].payload["amount"] == 0.001
    
    def test_large_number_of_ingredients(self, mock_library):
        """Formulation handles many ingredients."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        # Create 20 ingredients with different amounts to avoid any potential issues
        ingredients = tuple(
            Ingredient(compound_id="caffeine", amount=10.0 + i*0.1, unit="mg")
            for i in range(20)
        )
        
        formulation = Formulation(
            name="Mega Blend",
            ingredients=ingredients,
            form="powder",
            serving_info=ServingInfo(serving_size=1, serving_unit="scoop")
        )
        
        timeline = formulation.to_timeline(base_time_minutes=0)
        
        assert len(timeline.events) == 20
        
        # All timestamps should be unique
        timestamps = [e.timestamp_minutes for e in timeline.events]
        assert len(timestamps) == len(set(timestamps))
    
    def test_unicode_in_name(self, mock_library):
        """Formulation handles unicode in name."""
        from src.core.compounds.formulation import Formulation, Ingredient, ServingInfo
        
        formulation = Formulation(
            name="Café Énergy 日本",
            ingredients=(
                Ingredient(compound_id="caffeine", amount=100.0, unit="mg"),
            ),
            form="capsule",
            serving_info=ServingInfo(serving_size=1, serving_unit="capsule")
        )
        
        assert formulation.name == "Café Énergy 日本"
        
        d = formulation.to_dict()
        restored = Formulation.from_dict(d)
        assert restored.name == "Café Énergy 日本"
