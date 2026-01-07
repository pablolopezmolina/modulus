"""
Tests for CompoundProfile and IngredientLibrary.

Session 4.1 tests updated for Session 4.2 interface changes:
- CompoundProfile now requires: max_single_dose, max_daily_dose, target_system
- target_system must be one of: glucose, caffeine, adenosine, cortisol, energy, muscle, neural, none
- IngredientLibrary loads from JSON with "compounds" array
"""

import pytest
import json
import tempfile
from pathlib import Path

from src.core.compounds.profile import (
    CompoundProfile,
    VALID_PK_MODELS,
    VALID_PD_MODELS,
    VALID_EVIDENCE_LEVELS,
    VALID_DOSE_UNITS,
    VALID_TARGET_SYSTEMS,
)
from src.core.compounds.library import IngredientLibrary


# =============================================================================
# HELPER: Create valid CompoundProfile with defaults
# =============================================================================

def make_valid_profile(**overrides):
    """Create a valid CompoundProfile with sensible defaults."""
    defaults = {
        "compound_id": "test_compound",
        "name": "Test Compound",
        "category": "stimulant",
        "pk_model": "one_compartment",
        "pd_model": "emax",
        "max_single_dose": 100.0,
        "max_daily_dose": 400.0,
        "target_system": "adenosine",
        "pk_params": {"half_life_hours": 5.0},
        "pd_params": {"emax": 100},
        "bioavailability": 0.99,
        "dose_unit": "mg",
        "evidence_level": "high",
        "primary_sources": ["10.1234/test"],
    }
    defaults.update(overrides)
    return CompoundProfile(**defaults)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_profile():
    """A valid CompoundProfile for testing."""
    return make_valid_profile()


@pytest.fixture
def temp_ingredients_file():
    """Create a temporary ingredients.json file for testing."""
    data = {
        "version": "1.0.0",
        "last_updated": "2025-01-07",
        "compounds": [
            {
                "compound_id": "test_caffeine",
                "name": "Test Caffeine",
                "category": "stimulant",
                "pk_model": "one_compartment",
                "pk_params": {"half_life_hours": 5.0, "tmax_minutes": 45},
                "bioavailability": 0.99,
                "pd_model": "emax",
                "pd_params": {"emax": 100, "ec50_mg_l": 2.5},
                "target_system": "adenosine",
                "max_single_dose": 400,
                "max_daily_dose": 600,
                "dose_unit": "mg",
                "evidence_level": "high",
                "primary_sources": ["10.1016/test"]
            },
            {
                "compound_id": "test_glucose",
                "name": "Test Glucose",
                "category": "carbohydrate",
                "pk_model": "one_compartment",
                "pk_params": {"glycemic_index": 100},
                "bioavailability": 1.0,
                "pd_model": "linear",
                "pd_params": {"glucose_rise_per_g": 3.5},
                "target_system": "glucose",
                "max_single_dose": 100,
                "max_daily_dose": 500,
                "dose_unit": "g",
                "evidence_level": "high",
                "primary_sources": ["10.1093/test"]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def empty_ingredients_file():
    """Create a temporary ingredients.json with no compounds."""
    data = {
        "version": "1.0.0",
        "last_updated": "2025-01-07",
        "compounds": []
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    
    yield temp_path
    
    Path(temp_path).unlink(missing_ok=True)


# =============================================================================
# TEST: CompoundProfile Creation
# =============================================================================

class TestCompoundProfileCreation:
    """Test CompoundProfile creation and basic properties."""
    
    def test_create_valid_compound_profile(self):
        """Can create a valid CompoundProfile."""
        profile = make_valid_profile(
            compound_id="caffeine",
            name="Caffeine",
            category="stimulant",
            target_system="adenosine",
        )
        
        assert profile.compound_id == "caffeine"
        assert profile.name == "Caffeine"
        assert profile.category == "stimulant"
        assert profile.target_system == "adenosine"
    
    def test_compound_id_must_be_snake_case(self):
        """compound_id must be snake_case."""
        profile = make_valid_profile(compound_id="valid_snake_case")
        assert profile.compound_id == "valid_snake_case"
    
    def test_compound_id_rejects_invalid_format(self):
        """compound_id rejects CamelCase."""
        with pytest.raises(ValueError, match="snake_case"):
            make_valid_profile(compound_id="InvalidCamelCase")
    
    def test_compound_id_rejects_spaces(self):
        """compound_id rejects spaces."""
        with pytest.raises(ValueError, match="snake_case"):
            make_valid_profile(compound_id="invalid spaces")
    
    def test_compound_id_rejects_starting_with_number(self):
        """compound_id must start with letter."""
        with pytest.raises(ValueError, match="snake_case"):
            make_valid_profile(compound_id="123_invalid")
    
    def test_name_cannot_be_empty(self):
        """name cannot be empty."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            make_valid_profile(name="")
    
    def test_name_cannot_be_whitespace(self):
        """name cannot be just whitespace."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            make_valid_profile(name="   ")


# =============================================================================
# TEST: CompoundProfile Validation
# =============================================================================

class TestCompoundProfileValidation:
    """Test CompoundProfile field validation."""
    
    def test_bioavailability_must_be_between_0_and_1(self):
        """bioavailability must be in [0, 1]."""
        profile = make_valid_profile(bioavailability=0.5)
        assert profile.bioavailability == 0.5
    
    def test_bioavailability_rejects_above_1(self):
        """bioavailability > 1 is rejected."""
        with pytest.raises(ValueError, match="bioavailability"):
            make_valid_profile(bioavailability=1.5)
    
    def test_bioavailability_rejects_below_0(self):
        """bioavailability < 0 is rejected."""
        with pytest.raises(ValueError, match="bioavailability"):
            make_valid_profile(bioavailability=-0.1)
    
    def test_valid_pk_models(self):
        """All valid pk_model values are accepted."""
        for pk_model in VALID_PK_MODELS:
            profile = make_valid_profile(pk_model=pk_model)
            assert profile.pk_model == pk_model
    
    def test_invalid_pk_model_rejected(self):
        """Invalid pk_model is rejected."""
        with pytest.raises(ValueError, match="pk_model"):
            make_valid_profile(pk_model="invalid_model")
    
    def test_valid_pd_models(self):
        """All valid pd_model values are accepted."""
        for pd_model in VALID_PD_MODELS:
            profile = make_valid_profile(pd_model=pd_model)
            assert profile.pd_model == pd_model
    
    def test_invalid_pd_model_rejected(self):
        """Invalid pd_model is rejected."""
        with pytest.raises(ValueError, match="pd_model"):
            make_valid_profile(pd_model="invalid_model")
    
    def test_valid_evidence_levels(self):
        """All valid evidence_level values are accepted."""
        for evidence_level in VALID_EVIDENCE_LEVELS:
            profile = make_valid_profile(evidence_level=evidence_level)
            assert profile.evidence_level == evidence_level
    
    def test_invalid_evidence_level_rejected(self):
        """Invalid evidence_level is rejected."""
        with pytest.raises(ValueError, match="evidence_level"):
            make_valid_profile(evidence_level="invalid")
    
    def test_max_single_dose_must_be_positive(self):
        """max_single_dose must be > 0."""
        with pytest.raises(ValueError, match="max_single_dose"):
            make_valid_profile(max_single_dose=0)
    
    def test_max_single_dose_rejects_negative(self):
        """max_single_dose < 0 is rejected."""
        with pytest.raises(ValueError, match="max_single_dose"):
            make_valid_profile(max_single_dose=-10)
    
    def test_max_daily_dose_must_be_positive(self):
        """max_daily_dose must be > 0."""
        with pytest.raises(ValueError, match="max_daily_dose"):
            make_valid_profile(max_daily_dose=0)
    
    def test_valid_dose_units(self):
        """All valid dose_unit values are accepted."""
        for dose_unit in VALID_DOSE_UNITS:
            profile = make_valid_profile(dose_unit=dose_unit)
            assert profile.dose_unit == dose_unit
    
    def test_invalid_dose_unit_rejected(self):
        """Invalid dose_unit is rejected."""
        with pytest.raises(ValueError, match="dose_unit"):
            make_valid_profile(dose_unit="ml")
    
    def test_valid_target_systems(self):
        """All valid target_system values are accepted."""
        for target_system in VALID_TARGET_SYSTEMS:
            profile = make_valid_profile(target_system=target_system)
            assert profile.target_system == target_system
    
    def test_invalid_target_system_rejected(self):
        """Invalid target_system is rejected."""
        with pytest.raises(ValueError, match="target_system"):
            make_valid_profile(target_system="alertness")  # Not valid


# =============================================================================
# TEST: CompoundProfile Serialization
# =============================================================================

class TestCompoundProfileSerialization:
    """Test CompoundProfile serialization methods."""
    
    def test_to_dict(self, valid_profile):
        """to_dict() returns a dictionary with all fields."""
        d = valid_profile.to_dict()
        
        assert isinstance(d, dict)
        assert d["compound_id"] == valid_profile.compound_id
        assert d["name"] == valid_profile.name
        assert d["category"] == valid_profile.category
        assert d["pk_model"] == valid_profile.pk_model
        assert d["pd_model"] == valid_profile.pd_model
        assert d["bioavailability"] == valid_profile.bioavailability
        assert d["max_single_dose"] == valid_profile.max_single_dose
        assert d["max_daily_dose"] == valid_profile.max_daily_dose
        assert d["target_system"] == valid_profile.target_system
    
    def test_from_dict(self):
        """from_dict() creates a valid CompoundProfile."""
        data = {
            "compound_id": "test_compound",
            "name": "Test Compound",
            "category": "stimulant",
            "pk_model": "one_compartment",
            "pd_model": "emax",
            "max_single_dose": 100.0,
            "max_daily_dose": 400.0,
            "target_system": "adenosine",
            "pk_params": {"half_life_hours": 5.0},
            "pd_params": {"emax": 100},
            "bioavailability": 0.99,
            "dose_unit": "mg",
            "evidence_level": "high",
            "primary_sources": ["10.1234/test"],
        }
        
        profile = CompoundProfile.from_dict(data)
        
        assert profile.compound_id == "test_compound"
        assert profile.max_single_dose == 100.0
        assert profile.target_system == "adenosine"
    
    def test_roundtrip_serialization(self, valid_profile):
        """to_dict() -> from_dict() preserves all data."""
        d = valid_profile.to_dict()
        restored = CompoundProfile.from_dict(d)
        
        assert restored.compound_id == valid_profile.compound_id
        assert restored.name == valid_profile.name
        assert restored.pk_model == valid_profile.pk_model
        assert restored.bioavailability == valid_profile.bioavailability
        assert restored.max_single_dose == valid_profile.max_single_dose


# =============================================================================
# TEST: CompoundProfile Properties
# =============================================================================

class TestCompoundProfileProperties:
    """Test CompoundProfile computed properties."""
    
    def test_has_high_evidence(self):
        """has_high_evidence returns True for high evidence."""
        profile = make_valid_profile(evidence_level="high")
        assert profile.has_high_evidence is True
    
    def test_has_high_evidence_false_for_other(self):
        """has_high_evidence returns False for other levels."""
        for level in ["medium", "low", "theoretical"]:
            profile = make_valid_profile(evidence_level=level)
            assert profile.has_high_evidence is False
    
    def test_source_count(self):
        """source_count returns number of sources."""
        profile = make_valid_profile(primary_sources=["doi1", "doi2", "doi3"])
        assert profile.source_count == 3
    
    def test_get_pk_param(self):
        """get_pk_param returns parameter value."""
        profile = make_valid_profile(pk_params={"half_life_hours": 5.0})
        assert profile.get_pk_param("half_life_hours") == 5.0
    
    def test_get_pk_param_default(self):
        """get_pk_param returns default for missing param."""
        profile = make_valid_profile(pk_params={})
        assert profile.get_pk_param("missing", default=10) == 10
    
    def test_get_pd_param(self):
        """get_pd_param returns parameter value."""
        profile = make_valid_profile(pd_params={"emax": 100})
        assert profile.get_pd_param("emax") == 100


# =============================================================================
# TEST: CompoundProfile Categories
# =============================================================================

class TestCompoundProfileCategories:
    """Test CompoundProfile category handling."""
    
    def test_valid_categories(self):
        """Various valid categories are accepted."""
        valid_categories = ["stimulant", "amino", "carbohydrate", "vitamin", "adaptogen"]
        for category in valid_categories:
            profile = make_valid_profile(category=category)
            assert profile.category == category


# =============================================================================
# TEST: IngredientLibrary Loading
# =============================================================================

class TestIngredientLibraryLoading:
    """Test IngredientLibrary loading from JSON."""
    
    def test_load_from_json(self, temp_ingredients_file):
        """Can load library from JSON file."""
        library = IngredientLibrary(temp_ingredients_file)
        assert len(library) == 2
    
    def test_load_nonexistent_file_raises(self):
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            IngredientLibrary("/nonexistent/path.json")
    
    def test_load_invalid_json_raises(self):
        """Loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {{{")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                IngredientLibrary(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_empty_library(self):
        """Can create empty library without JSON."""
        library = IngredientLibrary(None)
        assert len(library) == 0


# =============================================================================
# TEST: IngredientLibrary Get Compound
# =============================================================================

class TestIngredientLibraryGetCompound:
    """Test IngredientLibrary.get_compound()."""
    
    def test_get_existing_compound(self, temp_ingredients_file):
        """get_compound returns CompoundProfile for existing compound."""
        library = IngredientLibrary(temp_ingredients_file)
        profile = library.get_compound("test_caffeine")
        
        assert isinstance(profile, CompoundProfile)
        assert profile.compound_id == "test_caffeine"
    
    def test_get_nonexistent_compound_raises_keyerror(self, temp_ingredients_file):
        """get_compound raises KeyError for nonexistent compound."""
        library = IngredientLibrary(temp_ingredients_file)
        
        with pytest.raises(KeyError):
            library.get_compound("nonexistent")
    
    def test_get_all_compounds(self, temp_ingredients_file):
        """Can get all compounds from library."""
        library = IngredientLibrary(temp_ingredients_file)
        
        for compound_id in library.list_compounds():
            profile = library.get_compound(compound_id)
            assert isinstance(profile, CompoundProfile)


# =============================================================================
# TEST: IngredientLibrary List Compounds
# =============================================================================

class TestIngredientLibraryListCompounds:
    """Test IngredientLibrary.list_compounds()."""
    
    def test_list_all_compounds(self, temp_ingredients_file):
        """list_compounds() returns all compound IDs."""
        library = IngredientLibrary(temp_ingredients_file)
        compounds = library.list_compounds()
        
        assert len(compounds) == 2
        assert "test_caffeine" in compounds
        assert "test_glucose" in compounds
    
    def test_list_compounds_by_category(self, temp_ingredients_file):
        """list_compounds(category=X) filters by category."""
        library = IngredientLibrary(temp_ingredients_file)
        
        stimulants = library.list_compounds(category="stimulant")
        assert stimulants == ["test_caffeine"]
        
        carbs = library.list_compounds(category="carbohydrate")
        assert carbs == ["test_glucose"]
    
    def test_list_compounds_empty_category(self, temp_ingredients_file):
        """list_compounds returns empty for nonexistent category."""
        library = IngredientLibrary(temp_ingredients_file)
        result = library.list_compounds(category="nonexistent")
        assert result == []
    
    def test_list_compounds_returns_ids_not_objects(self, temp_ingredients_file):
        """list_compounds returns strings, not CompoundProfile objects."""
        library = IngredientLibrary(temp_ingredients_file)
        compounds = library.list_compounds()
        
        for item in compounds:
            assert isinstance(item, str)


# =============================================================================
# TEST: IngredientLibrary Get Interaction
# =============================================================================

class TestIngredientLibraryGetInteraction:
    """Test IngredientLibrary.get_interaction()."""
    
    def test_get_interaction_returns_none_when_no_interactions(self, temp_ingredients_file):
        """get_interaction returns None (interactions not implemented yet)."""
        library = IngredientLibrary(temp_ingredients_file)
        result = library.get_interaction("test_caffeine", "test_glucose")
        assert result is None
    
    def test_get_interaction_order_independent(self, temp_ingredients_file):
        """get_interaction(A, B) == get_interaction(B, A)."""
        library = IngredientLibrary(temp_ingredients_file)
        result1 = library.get_interaction("test_caffeine", "test_glucose")
        result2 = library.get_interaction("test_glucose", "test_caffeine")
        assert result1 == result2


# =============================================================================
# TEST: IngredientLibrary Properties
# =============================================================================

class TestIngredientLibraryProperties:
    """Test IngredientLibrary magic methods and properties."""
    
    def test_library_has_compound_count(self, temp_ingredients_file):
        """len(library) returns compound count."""
        library = IngredientLibrary(temp_ingredients_file)
        assert len(library) == 2
    
    def test_library_iteration(self, temp_ingredients_file):
        """Can iterate over library compound IDs."""
        library = IngredientLibrary(temp_ingredients_file)
        compound_ids = list(library)
        
        assert len(compound_ids) == 2
        assert "test_caffeine" in compound_ids
    
    def test_library_contains(self, temp_ingredients_file):
        """'compound_id' in library works."""
        library = IngredientLibrary(temp_ingredients_file)
        
        assert "test_caffeine" in library
        assert "nonexistent" not in library
    
    def test_list_categories(self, temp_ingredients_file):
        """list_categories() returns unique categories."""
        library = IngredientLibrary(temp_ingredients_file)
        categories = library.list_categories()
        
        assert "stimulant" in categories
        assert "carbohydrate" in categories
    
    def test_library_version(self, temp_ingredients_file):
        """library.version returns version from JSON."""
        library = IngredientLibrary(temp_ingredients_file)
        assert library.version == "1.0.0"
    
    def test_library_last_updated(self, temp_ingredients_file):
        """library.last_updated returns date from JSON."""
        library = IngredientLibrary(temp_ingredients_file)
        assert library.last_updated == "2025-01-07"


# =============================================================================
# TEST: IngredientLibrary Empty
# =============================================================================

class TestIngredientLibraryEmptyFile:
    """Test IngredientLibrary with empty compounds list."""
    
    def test_empty_compounds(self, empty_ingredients_file):
        """Library with no compounds works."""
        library = IngredientLibrary(empty_ingredients_file)
        assert len(library) == 0
        assert library.list_compounds() == []


# =============================================================================
# TEST: Integration
# =============================================================================

class TestCompoundProfileLibraryIntegration:
    """Test CompoundProfile and IngredientLibrary work together."""
    
    def test_library_returns_validated_profiles(self, temp_ingredients_file):
        """Library returns valid CompoundProfile objects."""
        library = IngredientLibrary(temp_ingredients_file)
        
        for compound_id in library.list_compounds():
            profile = library.get_compound(compound_id)
            # If we got here, the profile passed validation
            assert profile.compound_id == compound_id
    
    def test_roundtrip_compound_data(self, temp_ingredients_file):
        """Profile from library can be serialized and restored."""
        library = IngredientLibrary(temp_ingredients_file)
        original = library.get_compound("test_caffeine")
        
        # Roundtrip
        data = original.to_dict()
        restored = CompoundProfile.from_dict(data)
        
        assert restored.compound_id == original.compound_id
        assert restored.name == original.name
        assert restored.bioavailability == original.bioavailability
    
    def test_add_compound_to_library(self):
        """Can add a compound to an empty library."""
        library = IngredientLibrary(None)
        profile = make_valid_profile(compound_id="new_compound")
        
        library.add_compound(profile)
        
        assert "new_compound" in library
        assert library.get_compound("new_compound") == profile
    
    def test_add_duplicate_compound_raises(self):
        """Adding duplicate compound raises ValueError."""
        library = IngredientLibrary(None)
        profile = make_valid_profile(compound_id="duplicate")
        
        library.add_compound(profile)
        
        with pytest.raises(ValueError, match="already exists"):
            library.add_compound(profile)
