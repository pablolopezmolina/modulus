"""
Tests for Tier 2 Ingredients (7 new compounds)
FASE 3, Sesión 8.1

Tests verify:
1. All 15 compounds load correctly
2. Each new compound has valid PK/PD parameters
3. Each new compound has proper evidence (DOIs)
4. Contract 3.1 compliance for all new compounds
"""
import pytest
from pathlib import Path


class TestTier2IngredientsExist:
    """Test that all 15 ingredients exist and load correctly."""
    
    @pytest.fixture
    def library(self):
        """Load the ingredient library."""
        from src.core.compounds.library import IngredientLibrary
        json_path = Path("data/reference/ingredients.json")
        return IngredientLibrary(json_path)
    
    def test_total_compound_count(self, library):
        """Should have 15 total compounds (8 Tier 1 + 7 Tier 2)."""
        compounds = library.list_compounds()
        assert len(compounds) == 15, f"Expected 15 compounds, got {len(compounds)}"
    
    def test_tier1_compounds_still_exist(self, library):
        """Original 8 Tier 1 compounds should still be present."""
        tier1_compounds = [
            "caffeine",
            "carbohydrate_glucose",
            "carbohydrate_maltodextrin",
            "carbohydrate_palatinose",
            "l_theanine",
            "taurine",
            "beta_alanine",
            "creatine_monohydrate"
        ]
        for compound_id in tier1_compounds:
            assert compound_id in library.list_compounds(), f"Missing Tier 1 compound: {compound_id}"
    
    def test_tier2_compounds_exist(self, library):
        """All 7 new Tier 2 compounds should be present."""
        tier2_compounds = [
            "citrulline_malate",
            "tyrosine",
            "alpha_gpc",
            "vitamin_b6",
            "vitamin_b12",
            "magnesium_citrate",
            "ashwagandha"
        ]
        for compound_id in tier2_compounds:
            assert compound_id in library.list_compounds(), f"Missing Tier 2 compound: {compound_id}"


class TestCitrullineMalate:
    """Tests for citrulline_malate compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("citrulline_malate")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "citrulline_malate"
        assert compound.category == "amino"
        assert "Citrulline" in compound.name
    
    def test_pk_params(self, compound):
        """Citrulline has one-compartment kinetics."""
        assert compound.pk_model == "one_compartment"
        assert "ka" in compound.pk_params  # Absorption rate
        assert "ke" in compound.pk_params  # Elimination rate
        assert "vd" in compound.pk_params  # Volume of distribution
        # Typical Tmax ~1h, half-life ~1h
        assert compound.pk_params["ka"] > 0
        assert compound.pk_params["ke"] > 0
    
    def test_pd_params(self, compound):
        """Citrulline affects blood flow via NO pathway."""
        assert compound.pd_model in ["emax", "threshold"]
        assert compound.target_system == "blood_flow"
    
    def test_dose_limits(self, compound):
        """Standard citrulline doses: 3-8g single, up to 15g daily."""
        assert compound.max_single_dose >= 3000  # mg
        assert compound.max_single_dose <= 10000
        assert compound.max_daily_dose >= 6000
        assert compound.max_daily_dose <= 20000
        assert compound.dose_unit == "mg"
    
    def test_evidence(self, compound):
        """Should have scientific evidence."""
        assert len(compound.primary_sources) >= 2
        assert compound.evidence_level in ["high", "medium"]


class TestTyrosine:
    """Tests for tyrosine compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("tyrosine")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "tyrosine"
        assert compound.category == "amino"
        assert "Tyrosine" in compound.name or "tyrosine" in compound.name.lower()
    
    def test_pk_params(self, compound):
        """Tyrosine has moderate absorption."""
        assert compound.pk_model == "one_compartment"
        # Tmax typically 1-2h
        assert compound.pk_params["ka"] > 0
        assert compound.pk_params["ke"] > 0
    
    def test_pd_params(self, compound):
        """Tyrosine is precursor for catecholamines."""
        assert compound.target_system == "cognitive"
        assert compound.pd_model in ["emax", "threshold", "linear"]
    
    def test_dose_limits(self, compound):
        """Standard tyrosine doses: 500-2000mg."""
        assert compound.max_single_dose >= 500
        assert compound.max_single_dose <= 3000
        assert compound.dose_unit == "mg"
    
    def test_evidence(self, compound):
        assert len(compound.primary_sources) >= 2


class TestAlphaGPC:
    """Tests for alpha_gpc compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("alpha_gpc")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "alpha_gpc"
        assert compound.category in ["nootropic", "choline"]
        assert "GPC" in compound.name or "Choline" in compound.name
    
    def test_pk_params(self, compound):
        """Alpha-GPC has good oral bioavailability."""
        assert compound.pk_model == "one_compartment"
        assert compound.bioavailability >= 0.3  # Good absorption
    
    def test_pd_params(self, compound):
        """Alpha-GPC supports acetylcholine synthesis."""
        assert compound.target_system == "cognitive"
    
    def test_dose_limits(self, compound):
        """Standard alpha-GPC doses: 300-1200mg."""
        assert compound.max_single_dose >= 300
        assert compound.max_single_dose <= 1500
        assert compound.dose_unit == "mg"
    
    def test_evidence(self, compound):
        assert len(compound.primary_sources) >= 2
        assert compound.evidence_level in ["high", "medium"]


class TestVitaminB6:
    """Tests for vitamin_b6 compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("vitamin_b6")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "vitamin_b6"
        assert compound.category == "vitamin"
        assert "B6" in compound.name or "Pyridoxine" in compound.name
    
    def test_pk_params(self, compound):
        """B6 is water-soluble with good absorption."""
        assert compound.pk_model == "one_compartment"
        assert compound.bioavailability >= 0.7
    
    def test_dose_limits(self, compound):
        """B6 doses typically 1.3-100mg (UL ~100mg/day for adults)."""
        assert compound.max_single_dose >= 10
        assert compound.max_single_dose <= 200
        assert compound.dose_unit == "mg"
    
    def test_evidence(self, compound):
        assert compound.evidence_level == "high"


class TestVitaminB12:
    """Tests for vitamin_b12 compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("vitamin_b12")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "vitamin_b12"
        assert compound.category == "vitamin"
        assert "B12" in compound.name or "Cobalamin" in compound.name
    
    def test_pk_params(self, compound):
        """B12 has saturable absorption."""
        assert compound.pk_model in ["one_compartment", "saturable"]
        # B12 bioavailability varies with dose (saturable)
    
    def test_dose_limits(self, compound):
        """B12 doses: 2.4mcg RDA to 1000+mcg supplements."""
        # Note: usually measured in mcg
        assert compound.dose_unit == "mcg"
        assert compound.max_single_dose >= 100
    
    def test_evidence(self, compound):
        assert compound.evidence_level == "high"


class TestMagnesiumCitrate:
    """Tests for magnesium_citrate compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("magnesium_citrate")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "magnesium_citrate"
        assert compound.category == "mineral"
        assert "Magnesium" in compound.name
    
    def test_pk_params(self, compound):
        """Magnesium citrate has ~30% bioavailability."""
        assert compound.pk_model == "one_compartment"
        assert 0.2 <= compound.bioavailability <= 0.5
    
    def test_pd_params(self, compound):
        """Magnesium affects multiple systems."""
        assert compound.target_system == "relaxation"
    
    def test_dose_limits(self, compound):
        """Elemental magnesium: 100-400mg typical."""
        assert compound.max_single_dose >= 100
        assert compound.max_single_dose <= 500
        assert compound.dose_unit == "mg"
    
    def test_evidence(self, compound):
        assert compound.evidence_level == "high"


class TestAshwagandha:
    """Tests for ashwagandha compound."""
    
    @pytest.fixture
    def compound(self):
        from src.core.compounds.library import IngredientLibrary
        library = IngredientLibrary(Path("data/reference/ingredients.json"))
        return library.get_compound("ashwagandha")
    
    def test_basic_properties(self, compound):
        assert compound.compound_id == "ashwagandha"
        assert compound.category == "adaptogen"
        assert "Ashwagandha" in compound.name or "Withania" in compound.name
    
    def test_pk_params(self, compound):
        """Ashwagandha withanolides have specific kinetics."""
        assert compound.pk_model == "one_compartment"
        # Tmax typically 2-3 hours
    
    def test_pd_params(self, compound):
        """Ashwagandha modulates cortisol/stress."""
        assert compound.target_system == "cortisol"
        assert compound.pd_model in ["emax", "threshold"]
    
    def test_dose_limits(self, compound):
        """Standard doses: 300-600mg root extract."""
        assert compound.max_single_dose >= 300
        assert compound.max_single_dose <= 1000
        assert compound.dose_unit == "mg"
    
    def test_evidence(self, compound):
        assert len(compound.primary_sources) >= 3
        assert compound.evidence_level in ["high", "medium"]


class TestAllTier2CompoundsHaveDOIs:
    """Verify all Tier 2 compounds have real DOI references."""
    
    @pytest.fixture
    def library(self):
        from src.core.compounds.library import IngredientLibrary
        return IngredientLibrary(Path("data/reference/ingredients.json"))
    
    @pytest.mark.parametrize("compound_id", [
        "citrulline_malate",
        "tyrosine",
        "alpha_gpc",
        "vitamin_b6",
        "vitamin_b12",
        "magnesium_citrate",
        "ashwagandha"
    ])
    def test_compound_has_dois(self, library, compound_id):
        """Each Tier 2 compound should have at least 2 DOI references."""
        compound = library.get_compound(compound_id)
        dois = [s for s in compound.primary_sources if "10." in s]
        assert len(dois) >= 2, f"{compound_id} needs at least 2 DOI references"


class TestAllCompoundsPassValidation:
    """Contract 3.1 compliance for all 15 compounds."""
    
    @pytest.fixture
    def library(self):
        from src.core.compounds.library import IngredientLibrary
        return IngredientLibrary(Path("data/reference/ingredients.json"))
    
    def test_all_compounds_valid(self, library):
        """All compounds should pass CompoundProfile validation."""
        from src.core.compounds.profile import CompoundProfile
        
        for compound_id in library.list_compounds():
            compound = library.get_compound(compound_id)
            # If we got here without exception, it's valid
            assert isinstance(compound, CompoundProfile)
            assert compound.compound_id == compound_id
    
    def test_all_have_required_pk_params(self, library):
        """All compounds should have required PK parameters."""
        required_for_one_compartment = ["ka", "ke", "vd"]
        
        for compound_id in library.list_compounds():
            compound = library.get_compound(compound_id)
            if compound.pk_model == "one_compartment":
                for param in required_for_one_compartment:
                    assert param in compound.pk_params, \
                        f"{compound_id} missing PK param: {param}"
    
    def test_all_have_valid_bioavailability(self, library):
        """Bioavailability must be in [0, 1]."""
        for compound_id in library.list_compounds():
            compound = library.get_compound(compound_id)
            assert 0 <= compound.bioavailability <= 1, \
                f"{compound_id} has invalid bioavailability: {compound.bioavailability}"
    
    def test_all_have_evidence_level(self, library):
        """All compounds must have valid evidence level."""
        valid_levels = ["high", "medium", "low", "theoretical"]
        
        for compound_id in library.list_compounds():
            compound = library.get_compound(compound_id)
            assert compound.evidence_level in valid_levels, \
                f"{compound_id} has invalid evidence_level: {compound.evidence_level}"


class TestCategoryDistribution:
    """Test that we have a good mix of compound categories."""
    
    @pytest.fixture
    def library(self):
        from src.core.compounds.library import IngredientLibrary
        return IngredientLibrary(Path("data/reference/ingredients.json"))
    
    def test_has_multiple_categories(self, library):
        """Should have at least 5 different categories."""
        categories = set()
        for compound_id in library.list_compounds():
            compound = library.get_compound(compound_id)
            categories.add(compound.category)
        
        assert len(categories) >= 5, f"Only {len(categories)} categories: {categories}"
    
    def test_expected_categories_present(self, library):
        """Should have key categories for supplement formulations."""
        compounds = [library.get_compound(cid) for cid in library.list_compounds()]
        categories = {c.category for c in compounds}
        
        expected = {"stimulant", "amino", "vitamin", "mineral", "adaptogen", "carbohydrate"}
        # At least 5 of these 6 should be present
        present = expected & categories
        assert len(present) >= 5, f"Missing categories. Have: {categories}"
