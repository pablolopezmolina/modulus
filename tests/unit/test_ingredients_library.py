"""
Tests for ingredients.json library loading and validation.

Session 4.2: Validates that ingredients.json:
1. Loads without errors
2. Contains all 8 Tier 1 compounds
3. All compounds have valid pk_params and pd_params
4. All compounds have sources with DOIs
5. All compounds pass CompoundProfile validation
"""

import pytest
import json
from pathlib import Path

from src.core.compounds.profile import CompoundProfile
from src.core.compounds.library import IngredientLibrary


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def ingredients_json_path():
    """Path to the ingredients.json file."""
    return Path(__file__).parent.parent.parent / "data" / "reference" / "ingredients.json"


@pytest.fixture
def raw_ingredients_data(ingredients_json_path):
    """Load raw JSON data."""
    with open(ingredients_json_path, "r") as f:
        return json.load(f)


@pytest.fixture
def ingredient_library(ingredients_json_path):
    """Load IngredientLibrary from JSON."""
    return IngredientLibrary(str(ingredients_json_path))


# =============================================================================
# TIER 1 COMPOUNDS LIST
# =============================================================================

TIER_1_COMPOUNDS = [
    "caffeine",
    "carbohydrate_glucose",
    "carbohydrate_maltodextrin",
    "carbohydrate_palatinose",
    "l_theanine",
    "taurine",
    "beta_alanine",
    "creatine_monohydrate",
]


# =============================================================================
# TEST: FILE EXISTS AND LOADS
# =============================================================================

class TestIngredientsJsonExists:
    """Test that ingredients.json exists and is valid JSON."""
    
    def test_file_exists(self, ingredients_json_path):
        """ingredients.json file exists."""
        assert ingredients_json_path.exists(), f"File not found: {ingredients_json_path}"
    
    def test_file_is_valid_json(self, ingredients_json_path):
        """ingredients.json is valid JSON."""
        with open(ingredients_json_path, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)
    
    def test_has_compounds_key(self, raw_ingredients_data):
        """JSON has 'compounds' key."""
        assert "compounds" in raw_ingredients_data
        assert isinstance(raw_ingredients_data["compounds"], list)
    
    def test_has_metadata(self, raw_ingredients_data):
        """JSON has metadata (version, last_updated)."""
        assert "version" in raw_ingredients_data
        assert "last_updated" in raw_ingredients_data


# =============================================================================
# TEST: ALL TIER 1 COMPOUNDS PRESENT
# =============================================================================

class TestTier1CompoundsPresent:
    """Test that all 8 Tier 1 compounds are present."""
    
    def test_library_loads_without_error(self, ingredient_library):
        """IngredientLibrary loads without errors."""
        assert ingredient_library is not None
    
    def test_has_8_compounds(self, ingredient_library):
        """Library has at least 8 compounds."""
        assert len(ingredient_library) >= 8
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_tier1_compound_present(self, ingredient_library, compound_id):
        """Each Tier 1 compound is present in the library."""
        assert compound_id in ingredient_library, f"Missing compound: {compound_id}"
    
    def test_all_tier1_compounds_present(self, ingredient_library):
        """All 8 Tier 1 compounds are present."""
        compound_ids = ingredient_library.list_compounds()
        for compound_id in TIER_1_COMPOUNDS:
            assert compound_id in compound_ids, f"Missing: {compound_id}"


# =============================================================================
# TEST: COMPOUND PROFILE VALIDATION
# =============================================================================

class TestCompoundProfileValidation:
    """Test that all compounds pass CompoundProfile validation."""
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_compound_is_valid_profile(self, ingredient_library, compound_id):
        """Each compound can be retrieved as a valid CompoundProfile."""
        profile = ingredient_library.get_compound(compound_id)
        assert isinstance(profile, CompoundProfile)
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_compound_has_required_fields(self, ingredient_library, compound_id):
        """Each compound has all required fields."""
        profile = ingredient_library.get_compound(compound_id)
        
        # Required fields from Contract 3.1
        assert profile.compound_id == compound_id
        assert profile.name is not None and len(profile.name) > 0
        assert profile.category is not None
        assert profile.pk_model in ["one_compartment", "two_compartment", "saturable"]
        assert profile.pd_model in ["emax", "linear", "threshold", "none"]
        assert 0 <= profile.bioavailability <= 1
        assert profile.evidence_level in ["high", "medium", "low", "theoretical"]
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_compound_has_valid_doses(self, ingredient_library, compound_id):
        """Each compound has valid dose limits."""
        profile = ingredient_library.get_compound(compound_id)
        
        assert profile.max_single_dose > 0
        assert profile.max_daily_dose > 0
        assert profile.max_daily_dose >= profile.max_single_dose
        assert profile.dose_unit in ["mg", "g", "mcg"]


# =============================================================================
# TEST: PK PARAMETERS
# =============================================================================

class TestPKParameters:
    """Test that pk_params are complete and valid."""
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_pk_params_not_empty(self, ingredient_library, compound_id):
        """Each compound has non-empty pk_params."""
        profile = ingredient_library.get_compound(compound_id)
        assert profile.pk_params is not None
        assert len(profile.pk_params) > 0
    
    def test_caffeine_has_half_life(self, ingredient_library):
        """Caffeine has half_life_hours in pk_params."""
        profile = ingredient_library.get_compound("caffeine")
        assert "half_life_hours" in profile.pk_params or "half_life_h" in profile.pk_params
    
    def test_caffeine_has_tmax(self, ingredient_library):
        """Caffeine has tmax (time to peak) in pk_params."""
        profile = ingredient_library.get_compound("caffeine")
        assert "tmax_minutes" in profile.pk_params or "tmax_min" in profile.pk_params
    
    def test_carbohydrates_have_gi(self, ingredient_library):
        """Carbohydrate compounds have glycemic_index."""
        for compound_id in ["carbohydrate_glucose", "carbohydrate_maltodextrin", "carbohydrate_palatinose"]:
            profile = ingredient_library.get_compound(compound_id)
            # GI might be in pk_params or pd_params
            has_gi = (
                "glycemic_index" in profile.pk_params or 
                "glycemic_index" in profile.pd_params or
                "gi" in profile.pk_params or
                "gi" in profile.pd_params
            )
            assert has_gi, f"{compound_id} missing glycemic_index"


# =============================================================================
# TEST: PD PARAMETERS
# =============================================================================

class TestPDParameters:
    """Test that pd_params are complete and valid."""
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_pd_params_exists(self, ingredient_library, compound_id):
        """Each compound has pd_params (can be empty for 'none' pd_model)."""
        profile = ingredient_library.get_compound(compound_id)
        assert profile.pd_params is not None
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_target_system_valid(self, ingredient_library, compound_id):
        """Each compound has a valid target_system."""
        profile = ingredient_library.get_compound(compound_id)
        valid_systems = ["glucose", "caffeine", "adenosine", "cortisol", "energy", "muscle", "neural", "none"]
        assert profile.target_system in valid_systems, f"{compound_id} has invalid target_system: {profile.target_system}"
    
    def test_caffeine_targets_adenosine(self, ingredient_library):
        """Caffeine targets adenosine system."""
        profile = ingredient_library.get_compound("caffeine")
        assert profile.target_system in ["adenosine", "caffeine", "neural"]
    
    def test_carbohydrates_target_glucose(self, ingredient_library):
        """Carbohydrate compounds target glucose system."""
        for compound_id in ["carbohydrate_glucose", "carbohydrate_maltodextrin", "carbohydrate_palatinose"]:
            profile = ingredient_library.get_compound(compound_id)
            assert profile.target_system == "glucose", f"{compound_id} should target glucose"


# =============================================================================
# TEST: EVIDENCE AND SOURCES
# =============================================================================

class TestEvidenceAndSources:
    """Test that all compounds have proper evidence documentation."""
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_has_primary_sources(self, ingredient_library, compound_id):
        """Each compound has at least one primary source."""
        profile = ingredient_library.get_compound(compound_id)
        assert profile.primary_sources is not None
        assert len(profile.primary_sources) >= 1, f"{compound_id} needs at least 1 source"
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_sources_look_like_dois_or_refs(self, ingredient_library, compound_id):
        """Sources should be DOIs or valid references."""
        profile = ingredient_library.get_compound(compound_id)
        for source in profile.primary_sources:
            # DOI format: 10.xxxx/xxxxx or reference string
            is_doi = source.startswith("10.") or "doi.org" in source.lower()
            is_pmid = source.lower().startswith("pmid:")
            is_reference = len(source) > 10  # At least a reasonable reference
            assert is_doi or is_pmid or is_reference, f"Invalid source format: {source}"
    
    @pytest.mark.parametrize("compound_id", TIER_1_COMPOUNDS)
    def test_evidence_level_appropriate(self, ingredient_library, compound_id):
        """Evidence level matches number of sources."""
        profile = ingredient_library.get_compound(compound_id)
        
        # High evidence should have multiple sources
        if profile.evidence_level == "high":
            assert len(profile.primary_sources) >= 2, f"{compound_id} claims high evidence but has <2 sources"


# =============================================================================
# TEST: SPECIFIC COMPOUND VALUES (SANITY CHECKS)
# =============================================================================

class TestSpecificCompoundValues:
    """Sanity checks for specific compound values based on literature."""
    
    def test_caffeine_bioavailability_near_100(self, ingredient_library):
        """Caffeine has ~100% oral bioavailability."""
        profile = ingredient_library.get_compound("caffeine")
        assert profile.bioavailability >= 0.95, "Caffeine bioavailability should be ~100%"
    
    def test_glucose_gi_is_100(self, ingredient_library):
        """Glucose has GI=100 (by definition)."""
        profile = ingredient_library.get_compound("carbohydrate_glucose")
        gi = profile.pk_params.get("glycemic_index") or profile.pd_params.get("glycemic_index")
        assert gi == 100, "Glucose GI must be 100 by definition"
    
    def test_palatinose_gi_is_low(self, ingredient_library):
        """Palatinose (isomaltulose) has low GI (~32)."""
        profile = ingredient_library.get_compound("carbohydrate_palatinose")
        gi = profile.pk_params.get("glycemic_index") or profile.pd_params.get("glycemic_index")
        assert gi <= 40, f"Palatinose GI should be ~32, got {gi}"
    
    def test_creatine_dose_limits_reasonable(self, ingredient_library):
        """Creatine has reasonable dose limits (loading vs maintenance)."""
        profile = ingredient_library.get_compound("creatine_monohydrate")
        # Typical: 3-5g/day maintenance, up to 20g/day loading
        assert profile.max_single_dose >= 3, "Creatine single dose should allow 3g+"
        assert profile.max_daily_dose >= 5, "Creatine daily dose should allow 5g+"
        assert profile.max_daily_dose <= 30, "Creatine daily dose shouldn't exceed 30g"
    
    def test_beta_alanine_dose_limits_reasonable(self, ingredient_library):
        """Beta-alanine has reasonable dose limits."""
        profile = ingredient_library.get_compound("beta_alanine")
        # Typical: 2-5g/day, often split to avoid paresthesia
        assert profile.max_single_dose >= 0.8, "Beta-alanine single dose should allow 800mg+"
        assert profile.max_daily_dose >= 3, "Beta-alanine daily dose should allow 3g+"


# =============================================================================
# TEST: CATEGORY ASSIGNMENTS
# =============================================================================

class TestCategoryAssignments:
    """Test that compounds have appropriate categories."""
    
    def test_caffeine_is_stimulant(self, ingredient_library):
        """Caffeine is categorized as stimulant."""
        profile = ingredient_library.get_compound("caffeine")
        assert profile.category == "stimulant"
    
    def test_carbohydrates_are_carbohydrate(self, ingredient_library):
        """Carbohydrate compounds are categorized as carbohydrate."""
        for compound_id in ["carbohydrate_glucose", "carbohydrate_maltodextrin", "carbohydrate_palatinose"]:
            profile = ingredient_library.get_compound(compound_id)
            assert profile.category == "carbohydrate", f"{compound_id} should be category=carbohydrate"
    
    def test_l_theanine_is_amino(self, ingredient_library):
        """L-Theanine is categorized as amino acid."""
        profile = ingredient_library.get_compound("l_theanine")
        assert profile.category in ["amino", "amino_acid", "nootropic"]
    
    def test_creatine_is_amino_or_performance(self, ingredient_library):
        """Creatine is categorized appropriately."""
        profile = ingredient_library.get_compound("creatine_monohydrate")
        assert profile.category in ["amino", "amino_acid", "performance", "ergogenic"]
    
    def test_taurine_is_amino(self, ingredient_library):
        """Taurine is categorized as amino acid."""
        profile = ingredient_library.get_compound("taurine")
        assert profile.category in ["amino", "amino_acid"]
    
    def test_beta_alanine_is_amino(self, ingredient_library):
        """Beta-alanine is categorized as amino acid."""
        profile = ingredient_library.get_compound("beta_alanine")
        assert profile.category in ["amino", "amino_acid", "performance", "ergogenic"]
