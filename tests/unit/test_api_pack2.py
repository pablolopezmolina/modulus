# MODULUS - API Unit Tests for Pack 2
# Session 11.2
# Tests for Pack 2 API endpoints
#
# NOTE: Imports use src.api.main to match project structure

"""
Unit tests for MODULUS API Pack 2 endpoints.

These tests verify:
1. Pydantic schema validation
2. Helper functions
3. Storage operations
4. Mock simulation logic
"""

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================

class TestIngredientInputSchema:
    """Tests for IngredientInput Pydantic schema."""
    
    def test_valid_ingredient(self):
        """Valid ingredient passes validation."""
        from src.api.main import IngredientInput
        
        ing = IngredientInput(
            compound_id="caffeine",
            amount=200.0,
            unit="mg"
        )
        
        assert ing.compound_id == "caffeine"
        assert ing.amount == 200.0
        assert ing.unit == "mg"
    
    def test_default_unit(self):
        """Default unit is mg."""
        from src.api.main import IngredientInput
        
        ing = IngredientInput(
            compound_id="l_theanine",
            amount=100.0
        )
        
        assert ing.unit == "mg"
    
    def test_invalid_compound_id_uppercase(self):
        """Uppercase in compound_id fails."""
        from src.api.main import IngredientInput
        
        with pytest.raises(ValueError):
            IngredientInput(
                compound_id="Caffeine",
                amount=100.0,
                unit="mg"
            )
    
    def test_invalid_compound_id_special_chars(self):
        """Special characters in compound_id fail."""
        from src.api.main import IngredientInput
        
        with pytest.raises(ValueError):
            IngredientInput(
                compound_id="caffeine-extra",
                amount=100.0,
                unit="mg"
            )
    
    def test_zero_amount_fails(self):
        """Zero amount fails validation."""
        from src.api.main import IngredientInput
        
        with pytest.raises(ValueError):
            IngredientInput(
                compound_id="caffeine",
                amount=0.0,
                unit="mg"
            )
    
    def test_negative_amount_fails(self):
        """Negative amount fails validation."""
        from src.api.main import IngredientInput
        
        with pytest.raises(ValueError):
            IngredientInput(
                compound_id="caffeine",
                amount=-50.0,
                unit="mg"
            )
    
    def test_invalid_unit_fails(self):
        """Invalid unit fails validation."""
        from src.api.main import IngredientInput
        
        with pytest.raises(ValueError):
            IngredientInput(
                compound_id="caffeine",
                amount=100.0,
                unit="kg"
            )
    
    def test_valid_units(self):
        """All valid units work."""
        from src.api.main import IngredientInput
        
        for unit in ["mg", "g", "mcg"]:
            ing = IngredientInput(
                compound_id="caffeine",
                amount=100.0,
                unit=unit
            )
            assert ing.unit == unit
    
    def test_compound_id_with_numbers(self):
        """Compound ID can contain numbers."""
        from src.api.main import IngredientInput
        
        ing = IngredientInput(
            compound_id="vitamin_b12",
            amount=100.0,
            unit="mcg"
        )
        assert ing.compound_id == "vitamin_b12"
    
    def test_compound_id_with_underscores(self):
        """Compound ID can contain underscores."""
        from src.api.main import IngredientInput
        
        ing = IngredientInput(
            compound_id="creatine_monohydrate",
            amount=5.0,
            unit="g"
        )
        assert ing.compound_id == "creatine_monohydrate"


class TestFormulationRequestSchema:
    """Tests for FormulationRequest Pydantic schema."""
    
    def test_valid_request(self):
        """Valid request passes validation."""
        from src.api.main import FormulationRequest, IngredientInput
        
        req = FormulationRequest(
            name="Energy Pro Max",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=200.0, unit="mg"),
                IngredientInput(compound_id="l_theanine", amount=100.0, unit="mg"),
            ]
        )
        
        assert req.name == "Energy Pro Max"
        assert len(req.ingredients) == 2
    
    def test_default_values(self):
        """Default values are applied correctly."""
        from src.api.main import FormulationRequest, IngredientInput
        
        req = FormulationRequest(
            name="Simple Product",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=100.0, unit="mg"),
            ]
        )
        
        assert req.form == "capsule"
        assert req.population_size == 1000
        assert req.seed is None
        assert req.serving_info == "1 serving"
    
    def test_empty_name_fails(self):
        """Empty name fails validation."""
        from src.api.main import FormulationRequest, IngredientInput
        
        with pytest.raises(ValueError):
            FormulationRequest(
                name="",
                ingredients=[
                    IngredientInput(compound_id="caffeine", amount=100.0, unit="mg"),
                ]
            )
    
    def test_empty_ingredients_fails(self):
        """Empty ingredients list fails validation."""
        from src.api.main import FormulationRequest
        
        with pytest.raises(ValueError):
            FormulationRequest(
                name="Empty Product",
                ingredients=[]
            )
    
    def test_population_size_minimum(self):
        """Population size minimum is 10."""
        from src.api.main import FormulationRequest, IngredientInput
        
        # Valid minimum
        req = FormulationRequest(
            name="Product",
            ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
            population_size=10
        )
        assert req.population_size == 10
        
        # Below minimum
        with pytest.raises(ValueError):
            FormulationRequest(
                name="Product",
                ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
                population_size=5
            )
    
    def test_population_size_maximum(self):
        """Population size maximum is 100000."""
        from src.api.main import FormulationRequest, IngredientInput
        
        # Valid maximum
        req = FormulationRequest(
            name="Product",
            ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
            population_size=100000
        )
        assert req.population_size == 100000
        
        # Above maximum
        with pytest.raises(ValueError):
            FormulationRequest(
                name="Product",
                ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
                population_size=100001
            )
    
    def test_valid_forms(self):
        """All valid forms work."""
        from src.api.main import FormulationRequest, IngredientInput
        
        for form in ["capsule", "powder", "liquid", "tablet", "gummy"]:
            req = FormulationRequest(
                name="Product",
                ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
                form=form
            )
            assert req.form == form
    
    def test_invalid_form_fails(self):
        """Invalid form fails validation."""
        from src.api.main import FormulationRequest, IngredientInput
        
        with pytest.raises(ValueError):
            FormulationRequest(
                name="Product",
                ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
                form="injectable"
            )
    
    def test_with_timeline_events(self):
        """Request with timeline events works."""
        from src.api.main import FormulationRequest, IngredientInput, TimelineEventInput
        
        req = FormulationRequest(
            name="Product with Events",
            ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
            timeline_events=[
                TimelineEventInput(
                    timestamp_minutes=480,
                    event_type="meal",
                    payload={"carbs_g": 50}
                )
            ]
        )
        
        assert len(req.timeline_events) == 1
        assert req.timeline_events[0].timestamp_minutes == 480


class TestDecisionSummarySchema:
    """Tests for DecisionSummary Pydantic schema."""
    
    def test_valid_verdicts(self):
        """Valid verdicts pass validation."""
        from src.api.main import DecisionSummary
        
        for verdict in ["GO", "CAUTION", "NO_GO"]:
            decision = DecisionSummary(
                verdict=verdict,
                confidence=0.8,
                summary="Test summary"
            )
            assert decision.verdict == verdict
    
    def test_invalid_verdict_fails(self):
        """Invalid verdict fails validation."""
        from src.api.main import DecisionSummary
        
        with pytest.raises(ValueError):
            DecisionSummary(
                verdict="MAYBE",
                confidence=0.8,
                summary="Test summary"
            )
    
    def test_confidence_valid_range(self):
        """Confidence in [0, 1] is valid."""
        from src.api.main import DecisionSummary
        
        for conf in [0.0, 0.5, 1.0]:
            decision = DecisionSummary(
                verdict="GO",
                confidence=conf,
                summary="Test"
            )
            assert decision.confidence == conf
    
    def test_confidence_below_zero_fails(self):
        """Confidence below 0 fails."""
        from src.api.main import DecisionSummary
        
        with pytest.raises(ValueError):
            DecisionSummary(
                verdict="GO",
                confidence=-0.1,
                summary="Test"
            )
    
    def test_confidence_above_one_fails(self):
        """Confidence above 1 fails."""
        from src.api.main import DecisionSummary
        
        with pytest.raises(ValueError):
            DecisionSummary(
                verdict="GO",
                confidence=1.5,
                summary="Test"
            )


class TestRiskSummarySchema:
    """Tests for RiskSummary Pydantic schema."""
    
    def test_valid_risk_summary(self):
        """Valid risk summary passes validation."""
        from src.api.main import RiskSummary
        
        risk = RiskSummary(
            risk_name="sleep_disruption",
            percentage=23.5,
            severity="medium",
            affected_segments=["slow_metabolizers", "elderly"]
        )
        
        assert risk.risk_name == "sleep_disruption"
        assert risk.percentage == 23.5
        assert risk.severity == "medium"
    
    def test_valid_severities(self):
        """All valid severities work."""
        from src.api.main import RiskSummary
        
        for severity in ["low", "medium", "high"]:
            risk = RiskSummary(
                risk_name="test_risk",
                percentage=10.0,
                severity=severity
            )
            assert risk.severity == severity
    
    def test_percentage_range(self):
        """Percentage must be in [0, 100]."""
        from src.api.main import RiskSummary
        
        # Valid
        risk = RiskSummary(risk_name="test", percentage=0.0, severity="low")
        assert risk.percentage == 0.0
        
        risk = RiskSummary(risk_name="test", percentage=100.0, severity="high")
        assert risk.percentage == 100.0
        
        # Invalid
        with pytest.raises(ValueError):
            RiskSummary(risk_name="test", percentage=-1.0, severity="low")
        
        with pytest.raises(ValueError):
            RiskSummary(risk_name="test", percentage=101.0, severity="low")


class TestCompareRequestSchema:
    """Tests for CompareRequest Pydantic schema."""
    
    def test_valid_compare_request(self):
        """Valid compare request passes validation."""
        from src.api.main import CompareRequest, FormulationRequest, IngredientInput
        
        req = CompareRequest(
            formulation_a=FormulationRequest(
                name="Product A",
                ingredients=[IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")]
            ),
            formulation_b=FormulationRequest(
                name="Product B",
                ingredients=[IngredientInput(compound_id="caffeine", amount=150.0, unit="mg")]
            )
        )
        
        assert req.formulation_a.name == "Product A"
        assert req.formulation_b.name == "Product B"
    
    def test_custom_names(self):
        """Custom names are preserved."""
        from src.api.main import CompareRequest, FormulationRequest, IngredientInput
        
        req = CompareRequest(
            formulation_a=FormulationRequest(
                name="A",
                ingredients=[IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")]
            ),
            formulation_b=FormulationRequest(
                name="B",
                ingredients=[IngredientInput(compound_id="caffeine", amount=150.0, unit="mg")]
            ),
            name_a="Current Formula",
            name_b="Proposed Formula"
        )
        
        assert req.name_a == "Current Formula"
        assert req.name_b == "Proposed Formula"
    
    def test_default_population_size(self):
        """Default population size is 1000."""
        from src.api.main import CompareRequest, FormulationRequest, IngredientInput
        
        req = CompareRequest(
            formulation_a=FormulationRequest(
                name="A",
                ingredients=[IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")]
            ),
            formulation_b=FormulationRequest(
                name="B",
                ingredients=[IngredientInput(compound_id="caffeine", amount=150.0, unit="mg")]
            )
        )
        
        assert req.population_size == 1000


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Tests for API helper functions."""
    
    def test_generate_simulation_id_format(self):
        """Simulation ID has correct format."""
        from src.api.main import generate_simulation_id
        
        sim_id = generate_simulation_id()
        
        assert sim_id.startswith("sim_")
        assert len(sim_id) == 20
    
    def test_generate_simulation_id_unique(self):
        """Simulation IDs are unique."""
        from src.api.main import generate_simulation_id
        
        ids = [generate_simulation_id() for _ in range(100)]
        
        assert len(set(ids)) == 100
    
    def test_generate_comparison_id_format(self):
        """Comparison ID has correct format."""
        from src.api.main import generate_comparison_id
        
        cmp_id = generate_comparison_id()
        
        assert cmp_id.startswith("cmp_")
        assert len(cmp_id) == 20
    
    def test_compute_input_hash_deterministic(self):
        """Same input produces same hash."""
        from src.api.main import compute_input_hash
        
        request = {"name": "Product", "amount": 100}
        
        hash1 = compute_input_hash(request)
        hash2 = compute_input_hash(request)
        
        assert hash1 == hash2
    
    def test_compute_input_hash_different(self):
        """Different inputs produce different hashes."""
        from src.api.main import compute_input_hash
        
        hash1 = compute_input_hash({"name": "Product A"})
        hash2 = compute_input_hash({"name": "Product B"})
        
        assert hash1 != hash2
    
    def test_compute_input_hash_order_independent(self):
        """Key order doesn't affect hash."""
        from src.api.main import compute_input_hash
        
        hash1 = compute_input_hash({"a": 1, "b": 2})
        hash2 = compute_input_hash({"b": 2, "a": 1})
        
        assert hash1 == hash2
    
    def test_validate_simulation_id_valid_sim(self):
        """Valid simulation IDs are accepted."""
        from src.api.main import validate_simulation_id
        
        assert validate_simulation_id("sim_0123456789abcdef") is True
    
    def test_validate_simulation_id_valid_cmp(self):
        """Valid comparison IDs are accepted."""
        from src.api.main import validate_simulation_id
        
        assert validate_simulation_id("cmp_fedcba9876543210") is True
    
    def test_validate_simulation_id_invalid_prefix(self):
        """Invalid prefix is rejected."""
        from src.api.main import validate_simulation_id
        
        assert validate_simulation_id("xyz_0123456789abcdef") is False
    
    def test_validate_simulation_id_too_short(self):
        """Too short ID is rejected."""
        from src.api.main import validate_simulation_id
        
        assert validate_simulation_id("sim_short") is False
    
    def test_validate_simulation_id_uppercase(self):
        """Uppercase hex is rejected."""
        from src.api.main import validate_simulation_id
        
        assert validate_simulation_id("sim_0123456789ABCDEF") is False
    
    def test_validate_simulation_id_no_prefix(self):
        """No prefix is rejected."""
        from src.api.main import validate_simulation_id
        
        assert validate_simulation_id("0123456789abcdef1234") is False


class TestIngredientValidation:
    """Tests for ingredient validation."""
    
    def test_validate_known_ingredients(self):
        """Known ingredients pass validation."""
        from src.api.main import validate_ingredients, IngredientInput
        
        ingredients = [
            IngredientInput(compound_id="caffeine", amount=200.0, unit="mg"),
            IngredientInput(compound_id="l_theanine", amount=100.0, unit="mg"),
        ]
        
        unknown = validate_ingredients(ingredients)
        
        assert unknown == []
    
    def test_validate_unknown_ingredients(self):
        """Unknown ingredients are reported."""
        from src.api.main import validate_ingredients, IngredientInput
        
        ingredients = [
            IngredientInput(compound_id="caffeine", amount=200.0, unit="mg"),
            IngredientInput(compound_id="unknown_compound", amount=100.0, unit="mg"),
            IngredientInput(compound_id="another_unknown", amount=50.0, unit="mg"),
        ]
        
        unknown = validate_ingredients(ingredients)
        
        assert "unknown_compound" in unknown
        assert "another_unknown" in unknown
        assert "caffeine" not in unknown
    
    def test_all_known_ingredients(self):
        """All 15 known ingredients pass."""
        from src.api.main import validate_ingredients, IngredientInput, KNOWN_INGREDIENTS
        
        ingredients = [
            IngredientInput(compound_id=cid, amount=100.0, unit="mg")
            for cid in KNOWN_INGREDIENTS
        ]
        
        unknown = validate_ingredients(ingredients)
        
        assert unknown == []


# =============================================================================
# STORAGE TESTS
# =============================================================================

class TestSimulationStorage:
    """Tests for in-memory simulation storage."""
    
    def test_store_and_retrieve(self):
        """Can store and retrieve simulation."""
        from src.api.main import SimulationStorage
        
        storage = SimulationStorage()
        
        storage.store_simulation(
            sim_id="sim_test123456789ab",
            result={"verdict": "GO"},
            request={"name": "Test"},
            bundle={"version": "3.0.0"}
        )
        
        retrieved = storage.get_simulation("sim_test123456789ab")
        
        assert retrieved is not None
        assert retrieved["result"]["verdict"] == "GO"
        assert retrieved["request"]["name"] == "Test"
        assert retrieved["bundle"]["version"] == "3.0.0"
    
    def test_retrieve_nonexistent(self):
        """Retrieving nonexistent simulation returns None."""
        from src.api.main import SimulationStorage
        
        storage = SimulationStorage()
        
        retrieved = storage.get_simulation("sim_doesnotexist123")
        
        assert retrieved is None
    
    def test_store_multiple(self):
        """Can store multiple simulations."""
        from src.api.main import SimulationStorage
        
        storage = SimulationStorage()
        
        for i in range(5):
            storage.store_simulation(
                sim_id=f"sim_{i:016x}",
                result={"index": i},
                request={"name": f"Test {i}"},
                bundle={"version": "3.0.0"}
            )
        
        for i in range(5):
            retrieved = storage.get_simulation(f"sim_{i:016x}")
            assert retrieved is not None
            assert retrieved["result"]["index"] == i
    
    def test_store_comparison(self):
        """Can store and retrieve comparison."""
        from src.api.main import SimulationStorage
        
        storage = SimulationStorage()
        
        storage.store_comparison(
            comparison_id="cmp_test123456789ab",
            result={"winner": "A"},
            sim_id_a="sim_a123456789abcde",
            sim_id_b="sim_b123456789abcde"
        )
        
        retrieved = storage.get_comparison("cmp_test123456789ab")
        
        assert retrieved is not None
        assert retrieved["result"]["winner"] == "A"
        assert retrieved["simulation_id_a"] == "sim_a123456789abcde"
        assert retrieved["simulation_id_b"] == "sim_b123456789abcde"
    
    def test_created_at_timestamp(self):
        """Stored items have created_at timestamp."""
        from src.api.main import SimulationStorage
        
        storage = SimulationStorage()
        
        storage.store_simulation(
            sim_id="sim_timestamp1234567",
            result={},
            request={},
            bundle={}
        )
        
        retrieved = storage.get_simulation("sim_timestamp1234567")
        
        assert "created_at" in retrieved
        # Should be valid ISO timestamp
        datetime.fromisoformat(retrieved["created_at"])


# =============================================================================
# MOCK SIMULATION TESTS
# =============================================================================

class TestMockSimulation:
    """Tests for mock simulation function."""
    
    def test_mock_simulation_structure(self):
        """Mock simulation returns expected structure."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Test Product",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")
            ],
            seed=42
        )
        
        result = _mock_simulation(request)
        
        assert result["success"] is True
        assert "decision" in result
        assert "risks" in result
        assert "claims" in result
        assert "metrics" in result
        assert "n_simulated" in result
        assert "n_valid" in result
    
    def test_mock_simulation_deterministic(self):
        """Mock simulation is deterministic with seed."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Test Product",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")
            ],
            seed=42
        )
        
        result1 = _mock_simulation(request)
        result2 = _mock_simulation(request)
        
        # Metrics should be identical with same seed
        assert result1["decision"]["verdict"] == result2["decision"]["verdict"]
    
    def test_mock_simulation_high_caffeine_caution(self):
        """High caffeine without theanine gives CAUTION."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="High Caffeine",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=300.0, unit="mg")
            ],
            seed=42
        )
        
        result = _mock_simulation(request)
        
        assert result["decision"]["verdict"] == "CAUTION"
    
    def test_mock_simulation_caffeine_theanine_go(self):
        """Caffeine with theanine gives GO."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Balanced Formula",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=200.0, unit="mg"),
                IngredientInput(compound_id="l_theanine", amount=100.0, unit="mg"),
            ],
            seed=42
        )
        
        result = _mock_simulation(request)
        
        assert result["decision"]["verdict"] == "GO"
    
    def test_mock_simulation_low_caffeine_go(self):
        """Low caffeine gives GO."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Low Caffeine",
            ingredients=[
                IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")
            ],
            seed=42
        )
        
        result = _mock_simulation(request)
        
        assert result["decision"]["verdict"] == "GO"
    
    def test_mock_simulation_population_size(self):
        """Mock simulation respects population size."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Test",
            ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
            population_size=500,
            seed=42
        )
        
        result = _mock_simulation(request)
        
        assert result["n_simulated"] == 500
        assert result["n_valid"] <= 500
    
    def test_mock_simulation_claims_structure(self):
        """Mock simulation returns expected claims."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Test",
            ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
            seed=42
        )
        
        result = _mock_simulation(request)
        
        for claim_id, claim_data in result["claims"].items():
            assert "is_defensible" in claim_data
            assert "responder_pct" in claim_data
            assert "confidence" in claim_data
    
    def test_mock_simulation_metrics_structure(self):
        """Mock simulation returns expected metrics."""
        from src.api.main import _mock_simulation, FormulationRequest, IngredientInput
        
        request = FormulationRequest(
            name="Test",
            ingredients=[IngredientInput(compound_id="caffeine", amount=100.0, unit="mg")],
            seed=42
        )
        
        result = _mock_simulation(request)
        
        expected_metrics = [
            "glucose_peak_mean",
            "alertness_duration_mean",
            "caffeine_half_life_mean"
        ]
        
        for metric in expected_metrics:
            assert metric in result["metrics"]


class TestMockComparison:
    """Tests for mock comparison function."""
    
    def test_mock_comparison_structure(self):
        """Mock comparison returns expected structure."""
        from src.api.main import _mock_comparison, CompareRequest, FormulationRequest, IngredientInput
        
        request = CompareRequest(
            formulation_a=FormulationRequest(
                name="A",
                ingredients=[IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")]
            ),
            formulation_b=FormulationRequest(
                name="B",
                ingredients=[IngredientInput(compound_id="caffeine", amount=150.0, unit="mg")]
            )
        )
        
        result = _mock_comparison(request)
        
        assert result["success"] is True
        assert "result_a" in result
        assert "result_b" in result
        assert "delta_metrics" in result
        assert "winner_by_metric" in result
        assert "recommendation" in result
    
    def test_mock_comparison_winners(self):
        """Mock comparison determines winners correctly."""
        from src.api.main import _mock_comparison, CompareRequest, FormulationRequest, IngredientInput
        
        request = CompareRequest(
            formulation_a=FormulationRequest(
                name="A",
                ingredients=[IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")],
                seed=42
            ),
            formulation_b=FormulationRequest(
                name="B",
                ingredients=[IngredientInput(compound_id="caffeine", amount=150.0, unit="mg")],
                seed=43
            )
        )
        
        result = _mock_comparison(request)
        
        for metric, winner in result["winner_by_metric"].items():
            assert winner in ["A", "B", "TIE"]
    
    def test_mock_comparison_statistical_significance(self):
        """Mock comparison includes statistical significance."""
        from src.api.main import _mock_comparison, CompareRequest, FormulationRequest, IngredientInput
        
        request = CompareRequest(
            formulation_a=FormulationRequest(
                name="A",
                ingredients=[IngredientInput(compound_id="caffeine", amount=200.0, unit="mg")]
            ),
            formulation_b=FormulationRequest(
                name="B",
                ingredients=[IngredientInput(compound_id="caffeine", amount=150.0, unit="mg")]
            )
        )
        
        result = _mock_comparison(request)
        
        assert "statistical_significance" in result
        for metric, significant in result["statistical_significance"].items():
            assert isinstance(significant, bool)


# =============================================================================
# RESPONSE SCHEMA TESTS
# =============================================================================

class TestSimulationResponseSchema:
    """Tests for SimulationResponse schema."""
    
    def test_valid_simulation_response(self):
        """Valid SimulationResponse passes validation."""
        from src.api.main import (
            SimulationResponse, DecisionSummary,
            RiskSummary, ClaimDefensibility
        )
        
        response = SimulationResponse(
            simulation_id="sim_0123456789abcdef",
            product_name="Test Product",
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision=DecisionSummary(
                verdict="GO",
                confidence=0.85,
                summary="Product is safe"
            ),
            risks=[
                RiskSummary(
                    risk_name="sleep_disruption",
                    percentage=15.5,
                    severity="low",
                    affected_segments=["slow_metabolizers"]
                )
            ],
            claims_defensibility={
                "sustained_energy": ClaimDefensibility(
                    is_defensible=True,
                    responder_pct=75.0,
                    confidence=0.85
                )
            },
            metrics={"glucose_peak_mean": 135.0},
            n_simulated=1000,
            n_valid=987
        )
        
        assert response.simulation_id == "sim_0123456789abcdef"
        assert response.decision.verdict == "GO"


class TestComparisonResponseSchema:
    """Tests for ComparisonResponse schema."""
    
    def test_valid_comparison_response(self):
        """Valid ComparisonResponse passes validation."""
        from src.api.main import ComparisonResponse
        
        response = ComparisonResponse(
            comparison_id="cmp_0123456789abcdef",
            timestamp=datetime.now(timezone.utc).isoformat(),
            name_a="Product A",
            name_b="Product B",
            simulation_id_a="sim_a123456789abcde",
            simulation_id_b="sim_b123456789abcde",
            winner_by_metric={
                "glucose_peak": "A",
                "alertness_duration": "B"
            },
            delta_metrics={
                "glucose_peak": -5.0,
                "alertness_duration": 0.3
            },
            recommendation="Formulation A recommended"
        )
        
        assert response.comparison_id == "cmp_0123456789abcdef"
        assert response.winner_by_metric["glucose_peak"] == "A"


class TestEvidenceResponseSchema:
    """Tests for EvidenceResponse schema."""
    
    def test_valid_evidence_response(self):
        """Valid EvidenceResponse passes validation."""
        from src.api.main import EvidenceResponse
        
        response = EvidenceResponse(
            simulation_id="sim_0123456789abcdef",
            sources=[
                {
                    "compound_id": "caffeine",
                    "doi": "10.1234/caffeine",
                    "title": "Caffeine PK"
                }
            ],
            parameters_evidence={
                "caffeine": {"pk_params": {"source": "literature"}}
            },
            methodology="Monte Carlo simulation",
            confidence_levels={"caffeine": "high"}
        )
        
        assert response.simulation_id == "sim_0123456789abcdef"
        assert len(response.sources) == 1


class TestBundleResponseSchema:
    """Tests for BundleResponse schema."""
    
    def test_valid_bundle_response(self):
        """Valid BundleResponse passes validation."""
        from src.api.main import BundleResponse
        
        response = BundleResponse(
            simulation_id="sim_0123456789abcdef",
            version="3.0.0",
            hash="sha256_hash_here",
            seed=42,
            timestamp=datetime.now(timezone.utc).isoformat(),
            config={"population_size": 1000},
            ingredient_versions={"caffeine": "1.0"}
        )
        
        assert response.simulation_id == "sim_0123456789abcdef"
        assert response.version == "3.0.0"
        assert response.seed == 42


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
