"""
Tests for CompoundProfile and IngredientLibrary.

Tests Contract 3.1 (CompoundProfile) and Contract 3.2 (IngredientLibrary).
"""
import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any


# =============================================================================
# CONTRACT 3.1: CompoundProfile Tests
# =============================================================================

class TestCompoundProfileCreation:
    """Test CompoundProfile instantiation and validation."""

    def test_create_valid_compound_profile(self):
        """Valid CompoundProfile can be created."""
        from src.core.compounds.profile import CompoundProfile
        
        profile = CompoundProfile(
            compound_id="caffeine",
            name="Caffeine",
            category="stimulant",
            pk_model="one_compartment",
            pd_model="emax",
            pk_params={"ka": 0.1, "ke": 0.05, "vd": 0.5},
            bioavailability=0.99,
            pd_params={"emax": 100, "ec50": 2.0},
            target_system="alertness",
            max_single_dose=400.0,
            max_daily_dose=600.0,
            dose_unit="mg",
            evidence_level="high",
            primary_sources=["10.1016/j.pharmthera.2010.10.007"]
        )
        
        assert profile.compound_id == "caffeine"
        assert profile.name == "Caffeine"
        assert profile.category == "stimulant"
        assert profile.bioavailability == 0.99

    def test_compound_id_must_be_snake_case(self):
        """compound_id must be snake_case."""
        from src.core.compounds.profile import CompoundProfile
        
        # Valid snake_case
        profile = CompoundProfile(
            compound_id="l_theanine",
            name="L-Theanine",
            category="amino",
            pk_model="one_compartment",
            pd_model="linear",
        )
        assert profile.compound_id == "l_theanine"

    def test_compound_id_rejects_invalid_format(self):
        """compound_id rejects non-snake_case formats."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="snake_case"):
            CompoundProfile(
                compound_id="L-Theanine",  # Invalid: has dash and uppercase
                name="L-Theanine",
                category="amino",
                pk_model="one_compartment",
                pd_model="linear",
            )

    def test_compound_id_rejects_spaces(self):
        """compound_id rejects spaces."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="snake_case"):
            CompoundProfile(
                compound_id="beta alanine",  # Invalid: has space
                name="Beta-Alanine",
                category="amino",
                pk_model="one_compartment",
                pd_model="linear",
            )


class TestCompoundProfileValidation:
    """Test CompoundProfile field validation."""

    def test_bioavailability_must_be_between_0_and_1(self):
        """bioavailability must be in [0, 1]."""
        from src.core.compounds.profile import CompoundProfile
        
        profile = CompoundProfile(
            compound_id="caffeine",
            name="Caffeine",
            category="stimulant",
            pk_model="one_compartment",
            pd_model="emax",
            bioavailability=0.99,
        )
        assert profile.bioavailability == 0.99

    def test_bioavailability_rejects_above_1(self):
        """bioavailability rejects values > 1."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="bioavailability"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                bioavailability=1.5,
            )

    def test_bioavailability_rejects_below_0(self):
        """bioavailability rejects values < 0."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="bioavailability"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                bioavailability=-0.1,
            )

    def test_valid_pk_models(self):
        """pk_model must be a valid model type."""
        from src.core.compounds.profile import CompoundProfile
        
        for model in ["one_compartment", "two_compartment", "saturable"]:
            profile = CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model=model,
                pd_model="emax",
            )
            assert profile.pk_model == model

    def test_invalid_pk_model_rejected(self):
        """Invalid pk_model is rejected."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="pk_model"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="invalid_model",
                pd_model="emax",
            )

    def test_valid_pd_models(self):
        """pd_model must be a valid model type."""
        from src.core.compounds.profile import CompoundProfile
        
        for model in ["emax", "linear", "threshold", "none"]:
            profile = CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model=model,
            )
            assert profile.pd_model == model

    def test_invalid_pd_model_rejected(self):
        """Invalid pd_model is rejected."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="pd_model"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="invalid_model",
            )

    def test_valid_evidence_levels(self):
        """evidence_level must be valid."""
        from src.core.compounds.profile import CompoundProfile
        
        for level in ["high", "medium", "low", "theoretical"]:
            profile = CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                evidence_level=level,
            )
            assert profile.evidence_level == level

    def test_invalid_evidence_level_rejected(self):
        """Invalid evidence_level is rejected."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="evidence_level"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                evidence_level="very_high",
            )

    def test_max_single_dose_must_be_positive(self):
        """max_single_dose must be > 0."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="max_single_dose"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                max_single_dose=-100.0,
            )

    def test_max_daily_dose_must_be_positive(self):
        """max_daily_dose must be > 0."""
        from src.core.compounds.profile import CompoundProfile
        
        with pytest.raises(ValueError, match="max_daily_dose"):
            CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                max_daily_dose=0.0,
            )

    def test_valid_dose_units(self):
        """dose_unit must be valid."""
        from src.core.compounds.profile import CompoundProfile
        
        for unit in ["mg", "g", "mcg"]:
            profile = CompoundProfile(
                compound_id="test",
                name="Test",
                category="stimulant",
                pk_model="one_compartment",
                pd_model="emax",
                dose_unit=unit,
            )
            assert profile.dose_unit == unit


class TestCompoundProfileSerialization:
    """Test CompoundProfile serialization."""

    def test_to_dict(self):
        """CompoundProfile can be serialized to dict."""
        from src.core.compounds.profile import CompoundProfile
        
        profile = CompoundProfile(
            compound_id="caffeine",
            name="Caffeine",
            category="stimulant",
            pk_model="one_compartment",
            pd_model="emax",
            pk_params={"ka": 0.1, "ke": 0.05},
            bioavailability=0.99,
            pd_params={"emax": 100, "ec50": 2.0},
            evidence_level="high",
            primary_sources=["doi:123"]
        )
        
        d = profile.to_dict()
        
        assert d["compound_id"] == "caffeine"
        assert d["pk_params"]["ka"] == 0.1
        assert d["primary_sources"] == ["doi:123"]

    def test_from_dict(self):
        """CompoundProfile can be created from dict."""
        from src.core.compounds.profile import CompoundProfile
        
        data = {
            "compound_id": "caffeine",
            "name": "Caffeine",
            "category": "stimulant",
            "pk_model": "one_compartment",
            "pd_model": "emax",
            "pk_params": {"ka": 0.1, "ke": 0.05},
            "bioavailability": 0.99,
            "pd_params": {"emax": 100, "ec50": 2.0},
            "evidence_level": "high",
            "primary_sources": ["doi:123"]
        }
        
        profile = CompoundProfile.from_dict(data)
        
        assert profile.compound_id == "caffeine"
        assert profile.pk_params["ka"] == 0.1

    def test_roundtrip_serialization(self):
        """to_dict → from_dict preserves all data."""
        from src.core.compounds.profile import CompoundProfile
        
        original = CompoundProfile(
            compound_id="caffeine",
            name="Caffeine",
            category="stimulant",
            pk_model="one_compartment",
            pd_model="emax",
            pk_params={"ka": 0.1, "ke": 0.05},
            bioavailability=0.99,
            pd_params={"emax": 100, "ec50": 2.0},
            evidence_level="high",
            primary_sources=["doi:123"]
        )
        
        restored = CompoundProfile.from_dict(original.to_dict())
        
        assert restored.compound_id == original.compound_id
        assert restored.bioavailability == original.bioavailability
        assert restored.pk_params == original.pk_params


class TestCompoundProfileCategories:
    """Test CompoundProfile category handling."""

    def test_valid_categories(self):
        """Common categories are accepted."""
        from src.core.compounds.profile import CompoundProfile
        
        categories = ["stimulant", "amino", "vitamin", "adaptogen", "carbohydrate", "mineral"]
        
        for cat in categories:
            profile = CompoundProfile(
                compound_id="test",
                name="Test",
                category=cat,
                pk_model="one_compartment",
                pd_model="none",
            )
            assert profile.category == cat


# =============================================================================
# CONTRACT 3.2: IngredientLibrary Tests
# =============================================================================

@pytest.fixture
def sample_ingredients_data() -> Dict[str, Any]:
    """Create sample ingredients data for testing."""
    return {
        "version": "1.0",
        "compounds": {
            "caffeine": {
                "compound_id": "caffeine",
                "name": "Caffeine",
                "category": "stimulant",
                "pk_model": "one_compartment",
                "pk_params": {"ka": 0.1, "ke": 0.05, "vd": 0.5},
                "bioavailability": 0.99,
                "pd_model": "emax",
                "pd_params": {"emax": 100, "ec50": 2.0},
                "target_system": "alertness",
                "max_single_dose": 400.0,
                "max_daily_dose": 600.0,
                "dose_unit": "mg",
                "evidence_level": "high",
                "primary_sources": ["10.1016/j.pharmthera.2010.10.007"]
            },
            "l_theanine": {
                "compound_id": "l_theanine",
                "name": "L-Theanine",
                "category": "amino",
                "pk_model": "one_compartment",
                "pk_params": {"ka": 0.05, "ke": 0.02, "vd": 0.4},
                "bioavailability": 0.9,
                "pd_model": "linear",
                "pd_params": {"slope": 0.5},
                "target_system": "alertness",
                "max_single_dose": 400.0,
                "max_daily_dose": 1200.0,
                "dose_unit": "mg",
                "evidence_level": "medium",
                "primary_sources": []
            },
            "creatine_monohydrate": {
                "compound_id": "creatine_monohydrate",
                "name": "Creatine Monohydrate",
                "category": "amino",
                "pk_model": "saturable",
                "pk_params": {"km": 50, "vmax": 100},
                "bioavailability": 0.95,
                "pd_model": "threshold",
                "pd_params": {"threshold": 20, "effect": 1.0},
                "target_system": "energy",
                "max_single_dose": 10000.0,
                "max_daily_dose": 20000.0,
                "dose_unit": "mg",
                "evidence_level": "high",
                "primary_sources": ["10.1186/s12970-017-0173-z"]
            }
        }
    }


@pytest.fixture
def temp_ingredients_file(sample_ingredients_data) -> Path:
    """Create a temporary ingredients JSON file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_ingredients_data, f)
        return Path(f.name)


class TestIngredientLibraryLoading:
    """Test IngredientLibrary file loading."""

    def test_load_from_json(self, temp_ingredients_file):
        """Library can be loaded from JSON file."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        assert library is not None
        assert len(library) == 3

    def test_load_nonexistent_file_raises(self):
        """Loading nonexistent file raises FileNotFoundError."""
        from src.core.compounds.library import IngredientLibrary
        
        with pytest.raises(FileNotFoundError):
            IngredientLibrary("/nonexistent/path/ingredients.json")

    def test_load_invalid_json_raises(self):
        """Loading invalid JSON raises appropriate error."""
        from src.core.compounds.library import IngredientLibrary
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json ")
            path = f.name
        
        with pytest.raises(json.JSONDecodeError):
            IngredientLibrary(path)


class TestIngredientLibraryGetCompound:
    """Test IngredientLibrary.get_compound() - Contract 3.2."""

    def test_get_existing_compound(self, temp_ingredients_file):
        """get_compound returns CompoundProfile for existing compound."""
        from src.core.compounds.library import IngredientLibrary
        from src.core.compounds.profile import CompoundProfile
        
        library = IngredientLibrary(str(temp_ingredients_file))
        profile = library.get_compound("caffeine")
        
        assert isinstance(profile, CompoundProfile)
        assert profile.compound_id == "caffeine"
        assert profile.name == "Caffeine"

    def test_get_nonexistent_compound_raises_keyerror(self, temp_ingredients_file):
        """get_compound raises KeyError for nonexistent compound - Contract 3.2."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        with pytest.raises(KeyError):
            library.get_compound("nonexistent_compound")

    def test_get_all_compounds(self, temp_ingredients_file):
        """All compounds in file can be retrieved."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        caffeine = library.get_compound("caffeine")
        theanine = library.get_compound("l_theanine")
        creatine = library.get_compound("creatine_monohydrate")
        
        assert caffeine.category == "stimulant"
        assert theanine.category == "amino"
        assert creatine.category == "amino"


class TestIngredientLibraryListCompounds:
    """Test IngredientLibrary.list_compounds() - Contract 3.2."""

    def test_list_all_compounds(self, temp_ingredients_file):
        """list_compounds returns all compound IDs."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        compound_ids = library.list_compounds()
        
        assert isinstance(compound_ids, list)
        assert len(compound_ids) == 3
        assert "caffeine" in compound_ids
        assert "l_theanine" in compound_ids
        assert "creatine_monohydrate" in compound_ids

    def test_list_compounds_by_category(self, temp_ingredients_file):
        """list_compounds can filter by category."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        stimulants = library.list_compounds(category="stimulant")
        aminos = library.list_compounds(category="amino")
        
        assert stimulants == ["caffeine"]
        assert set(aminos) == {"l_theanine", "creatine_monohydrate"}

    def test_list_compounds_empty_category(self, temp_ingredients_file):
        """list_compounds returns empty list for category with no compounds."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        vitamins = library.list_compounds(category="vitamin")
        assert vitamins == []

    def test_list_compounds_returns_ids_not_objects(self, temp_ingredients_file):
        """list_compounds returns strings, not CompoundProfile objects - Contract 3.2."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        compound_ids = library.list_compounds()
        
        for item in compound_ids:
            assert isinstance(item, str)


class TestIngredientLibraryGetInteraction:
    """Test IngredientLibrary.get_interaction() - Contract 3.2."""

    def test_get_interaction_returns_none_when_no_interactions(self, temp_ingredients_file):
        """get_interaction returns None when no interactions defined - Contract 3.2."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        interaction = library.get_interaction("caffeine", "l_theanine")
        assert interaction is None

    def test_get_interaction_order_independent(self, temp_ingredients_file):
        """get_interaction should work regardless of compound order."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        result1 = library.get_interaction("caffeine", "l_theanine")
        result2 = library.get_interaction("l_theanine", "caffeine")
        
        assert result1 == result2


class TestIngredientLibraryProperties:
    """Test IngredientLibrary additional properties."""

    def test_library_has_compound_count(self, temp_ingredients_file):
        """Library exposes compound count via len()."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        assert len(library) == 3

    def test_library_iteration(self, temp_ingredients_file):
        """Library supports iteration over compound IDs."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        compound_ids = list(library)
        assert len(compound_ids) == 3
        assert "caffeine" in compound_ids

    def test_library_contains(self, temp_ingredients_file):
        """Library supports 'in' operator."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        assert "caffeine" in library
        assert "nonexistent" not in library

    def test_list_categories(self, temp_ingredients_file):
        """Library can list all unique categories."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        categories = library.list_categories()
        
        assert isinstance(categories, list)
        assert set(categories) == {"stimulant", "amino"}


class TestIngredientLibraryEmptyFile:
    """Test IngredientLibrary with empty or minimal data."""

    def test_empty_compounds(self):
        """Library handles empty compounds dict."""
        from src.core.compounds.library import IngredientLibrary
        
        data = {"version": "1.0", "compounds": {}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        
        library = IngredientLibrary(path)
        
        assert len(library) == 0
        assert library.list_compounds() == []


# =============================================================================
# Integration Tests
# =============================================================================

class TestCompoundProfileLibraryIntegration:
    """Integration tests for CompoundProfile and IngredientLibrary."""

    def test_library_returns_validated_profiles(self, temp_ingredients_file):
        """Library returns properly validated CompoundProfile instances."""
        from src.core.compounds.library import IngredientLibrary
        from src.core.compounds.profile import CompoundProfile
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        for compound_id in library:
            profile = library.get_compound(compound_id)
            assert isinstance(profile, CompoundProfile)
            # Validation happens in CompoundProfile.__post_init__
            assert 0 <= profile.bioavailability <= 1
            assert profile.max_single_dose > 0
            assert profile.max_daily_dose > 0

    def test_roundtrip_compound_data(self, temp_ingredients_file, sample_ingredients_data):
        """Data loaded from file matches original."""
        from src.core.compounds.library import IngredientLibrary
        
        library = IngredientLibrary(str(temp_ingredients_file))
        
        caffeine = library.get_compound("caffeine")
        original = sample_ingredients_data["compounds"]["caffeine"]
        
        assert caffeine.compound_id == original["compound_id"]
        assert caffeine.bioavailability == original["bioavailability"]
        assert caffeine.pk_params == original["pk_params"]
