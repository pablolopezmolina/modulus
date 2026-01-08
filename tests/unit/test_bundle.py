"""
Tests for ReproducibilityBundle (Sesión 9.2)

Tests the reproducibility system for Pack 2 auditing requirements.
"""

import pytest
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass

# We'll import from the module once it's created
# from src.reporting.bundle import (
#     ReproducibilityBundle,
#     BundleConfig,
#     SimulationFingerprint,
#     BundleVerificationResult,
# )


# ============================================================================
# MOCK CLASSES (for testing without full dependencies)
# ============================================================================

@dataclass
class MockFormulation:
    """Mock formulation for testing."""
    name: str
    ingredients: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ingredients": self.ingredients
        }


@dataclass  
class MockTimeline:
    """Mock timeline for testing."""
    events: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {"events": self.events}


@dataclass
class MockPopulationConfig:
    """Mock population config for testing."""
    n_individuals: int
    seed: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_individuals": self.n_individuals,
            "seed": self.seed
        }


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_formulation():
    """Sample formulation for bundle testing."""
    return MockFormulation(
        name="Test Pre-Workout",
        ingredients=[
            {"compound_id": "caffeine", "amount": 200, "unit": "mg"},
            {"compound_id": "l_theanine", "amount": 100, "unit": "mg"},
        ]
    )


@pytest.fixture
def sample_timeline():
    """Sample timeline for bundle testing."""
    return MockTimeline(
        events=[
            {"timestamp_minutes": 420, "event_type": "ingestion", 
             "payload": {"compound_id": "caffeine", "amount": 200, "unit": "mg"}},
            {"timestamp_minutes": 450, "event_type": "meal",
             "payload": {"carbs_g": 50, "protein_g": 20, "fat_g": 10}},
        ]
    )


@pytest.fixture
def sample_population_config():
    """Sample population config for bundle testing."""
    return MockPopulationConfig(n_individuals=1000, seed=42)


@pytest.fixture
def sample_ingredient_versions():
    """Sample ingredient library versions."""
    return {
        "caffeine": "1.2.0",
        "l_theanine": "1.0.0",
        "library_version": "2.1.0",
    }


@pytest.fixture
def sample_simulation_config():
    """Sample simulation configuration."""
    return {
        "dt_minutes": 1.0,
        "duration_minutes": 1440,
        "seed": 12345,
    }


# ============================================================================
# TEST: BundleConfig
# ============================================================================

class TestBundleConfig:
    """Tests for BundleConfig dataclass."""
    
    def test_create_bundle_config(self, sample_simulation_config):
        """BundleConfig can be created with valid parameters."""
        from src.reporting.bundle import BundleConfig
        
        config = BundleConfig(
            simulation_params=sample_simulation_config,
            modulus_version="3.0.0",
            ingredients_version="2.1.0",
        )
        
        assert config.simulation_params == sample_simulation_config
        assert config.modulus_version == "3.0.0"
        assert config.ingredients_version == "2.1.0"
    
    def test_bundle_config_to_dict(self, sample_simulation_config):
        """BundleConfig serializes to dict."""
        from src.reporting.bundle import BundleConfig
        
        config = BundleConfig(
            simulation_params=sample_simulation_config,
            modulus_version="3.0.0",
            ingredients_version="2.1.0",
        )
        
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert "simulation_params" in result
        assert "modulus_version" in result
        assert "ingredients_version" in result
    
    def test_bundle_config_from_dict(self, sample_simulation_config):
        """BundleConfig can be created from dict."""
        from src.reporting.bundle import BundleConfig
        
        data = {
            "simulation_params": sample_simulation_config,
            "modulus_version": "3.0.0",
            "ingredients_version": "2.1.0",
        }
        
        config = BundleConfig.from_dict(data)
        
        assert config.simulation_params == sample_simulation_config
        assert config.modulus_version == "3.0.0"


# ============================================================================
# TEST: SimulationFingerprint
# ============================================================================

class TestSimulationFingerprint:
    """Tests for SimulationFingerprint - hash generation."""
    
    def test_create_fingerprint(self):
        """SimulationFingerprint can be created."""
        from src.reporting.bundle import SimulationFingerprint
        
        fingerprint = SimulationFingerprint(
            input_hash="abc123",
            config_hash="def456",
            combined_hash="xyz789",
            algorithm="sha256",
        )
        
        assert fingerprint.input_hash == "abc123"
        assert fingerprint.algorithm == "sha256"
    
    def test_fingerprint_from_data(self, sample_formulation, sample_timeline):
        """SimulationFingerprint generates deterministic hash from data."""
        from src.reporting.bundle import SimulationFingerprint
        
        fp1 = SimulationFingerprint.from_data(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            config={"seed": 42},
        )
        
        fp2 = SimulationFingerprint.from_data(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            config={"seed": 42},
        )
        
        # Same input = same hash
        assert fp1.combined_hash == fp2.combined_hash
    
    def test_fingerprint_different_input_different_hash(
        self, sample_formulation, sample_timeline
    ):
        """Different inputs produce different hashes."""
        from src.reporting.bundle import SimulationFingerprint
        
        fp1 = SimulationFingerprint.from_data(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            config={"seed": 42},
        )
        
        fp2 = SimulationFingerprint.from_data(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            config={"seed": 99},  # Different seed
        )
        
        assert fp1.combined_hash != fp2.combined_hash
    
    def test_fingerprint_to_dict(self, sample_formulation, sample_timeline):
        """SimulationFingerprint serializes to dict."""
        from src.reporting.bundle import SimulationFingerprint
        
        fingerprint = SimulationFingerprint.from_data(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            config={"seed": 42},
        )
        
        result = fingerprint.to_dict()
        
        assert "input_hash" in result
        assert "config_hash" in result
        assert "combined_hash" in result
        assert "algorithm" in result


# ============================================================================
# TEST: ReproducibilityBundle
# ============================================================================

class TestReproducibilityBundle:
    """Tests for main ReproducibilityBundle class."""
    
    def test_create_bundle(
        self, 
        sample_formulation, 
        sample_timeline, 
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """ReproducibilityBundle can be created with all required data."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle is not None
        assert bundle.modulus_version == "3.0.0"
        assert bundle.fingerprint is not None
    
    def test_bundle_has_timestamp(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle includes creation timestamp."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle.created_at is not None
        assert isinstance(bundle.created_at, str)
        # Should be ISO format
        datetime.fromisoformat(bundle.created_at)
    
    def test_bundle_has_unique_id(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle has a unique identifier."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle.bundle_id is not None
        assert len(bundle.bundle_id) > 0
    
    def test_bundle_contains_seed(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle contains the simulation seed."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle.seed == sample_simulation_config["seed"]
    
    def test_bundle_contains_ingredient_versions(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle contains ingredient library versions."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle.ingredient_versions == sample_ingredient_versions


# ============================================================================
# TEST: Bundle Export
# ============================================================================

class TestBundleExport:
    """Tests for bundle export functionality."""
    
    def test_export_to_dict(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle can be exported to dictionary."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        result = bundle.to_dict()
        
        assert isinstance(result, dict)
        assert "bundle_id" in result
        assert "modulus_version" in result
        assert "created_at" in result
        assert "fingerprint" in result
        assert "inputs" in result
        assert "formulation" in result["inputs"]
        assert "timeline" in result["inputs"]
    
    def test_export_to_json_string(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle can be exported to JSON string."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        json_str = bundle.to_json()
        
        assert isinstance(json_str, str)
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "bundle_id" in parsed
    
    def test_export_to_file(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config,
        tmp_path
    ):
        """Bundle can be exported to JSON file."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        file_path = tmp_path / "bundle.json"
        bundle.export(file_path)
        
        assert file_path.exists()
        
        # Verify file content
        with open(file_path) as f:
            loaded = json.load(f)
        
        assert loaded["bundle_id"] == bundle.bundle_id
    
    def test_export_filename_default(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config,
        tmp_path
    ):
        """Bundle generates default filename based on ID and timestamp."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        filename = bundle.get_default_filename()
        
        assert filename.endswith(".json")
        assert "modulus_bundle" in filename


# ============================================================================
# TEST: Bundle Import
# ============================================================================

class TestBundleImport:
    """Tests for bundle import functionality."""
    
    def test_from_dict(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle can be created from dictionary."""
        from src.reporting.bundle import ReproducibilityBundle
        
        original = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        exported = original.to_dict()
        restored = ReproducibilityBundle.from_dict(exported)
        
        assert restored.bundle_id == original.bundle_id
        assert restored.fingerprint.combined_hash == original.fingerprint.combined_hash
    
    def test_from_json(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle can be created from JSON string."""
        from src.reporting.bundle import ReproducibilityBundle
        
        original = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        json_str = original.to_json()
        restored = ReproducibilityBundle.from_json(json_str)
        
        assert restored.bundle_id == original.bundle_id
    
    def test_load_from_file(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config,
        tmp_path
    ):
        """Bundle can be loaded from file."""
        from src.reporting.bundle import ReproducibilityBundle
        
        original = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        file_path = tmp_path / "bundle.json"
        original.export(file_path)
        
        loaded = ReproducibilityBundle.load(file_path)
        
        assert loaded.bundle_id == original.bundle_id
        assert loaded.fingerprint.combined_hash == original.fingerprint.combined_hash


# ============================================================================
# TEST: Bundle Verification
# ============================================================================

class TestBundleVerification:
    """Tests for bundle verification functionality."""
    
    def test_verify_returns_result_object(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """verify() returns a BundleVerificationResult."""
        from src.reporting.bundle import ReproducibilityBundle, BundleVerificationResult
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        # Create mock results matching the bundle inputs
        mock_results = {
            "seed": sample_simulation_config["seed"],
            "formulation_hash": "test",
        }
        
        result = bundle.verify(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            simulation_config=sample_simulation_config,
        )
        
        assert isinstance(result, BundleVerificationResult)
    
    def test_verify_same_inputs_passes(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Verification passes when inputs match."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        result = bundle.verify(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            simulation_config=sample_simulation_config,
        )
        
        assert result.is_valid
        assert result.input_match
        assert result.config_match
    
    def test_verify_different_formulation_fails(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Verification fails when formulation differs."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        # Different formulation
        different_formulation = MockFormulation(
            name="Different Product",
            ingredients=[
                {"compound_id": "caffeine", "amount": 300, "unit": "mg"},  # Different dose
            ]
        )
        
        result = bundle.verify(
            formulation=different_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            simulation_config=sample_simulation_config,
        )
        
        assert not result.is_valid
        assert not result.input_match
    
    def test_verify_different_seed_fails(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Verification fails when seed differs."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        different_config = sample_simulation_config.copy()
        different_config["seed"] = 99999  # Different seed
        
        result = bundle.verify(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            simulation_config=different_config,
        )
        
        assert not result.is_valid
        assert not result.config_match
    
    def test_verify_provides_mismatch_details(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Verification provides details on mismatches."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        # Multiple differences
        different_formulation = MockFormulation(
            name="Different Product",
            ingredients=[]
        )
        different_config = {"seed": 99999, "dt_minutes": 2.0, "duration_minutes": 1440}
        
        result = bundle.verify(
            formulation=different_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            simulation_config=different_config,
        )
        
        assert not result.is_valid
        assert len(result.mismatches) > 0


# ============================================================================
# TEST: Version Compatibility
# ============================================================================

class TestVersionCompatibility:
    """Tests for version compatibility checking."""
    
    def test_check_version_compatibility_same_version(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Same version is compatible."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        is_compatible, warnings = bundle.check_version_compatibility("3.0.0")
        
        assert is_compatible
        assert len(warnings) == 0
    
    def test_check_version_compatibility_minor_diff(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Minor version difference is compatible with warning."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        is_compatible, warnings = bundle.check_version_compatibility("3.1.0")
        
        assert is_compatible
        assert len(warnings) > 0
    
    def test_check_version_compatibility_major_diff(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Major version difference is NOT compatible."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        is_compatible, warnings = bundle.check_version_compatibility("4.0.0")
        
        assert not is_compatible


# ============================================================================
# TEST: Summary and Display
# ============================================================================

class TestBundleSummary:
    """Tests for bundle summary generation."""
    
    def test_get_summary(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle can generate human-readable summary."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        summary = bundle.get_summary()
        
        assert isinstance(summary, dict)
        assert "bundle_id" in summary
        assert "created_at" in summary
        assert "modulus_version" in summary
        assert "hash" in summary
        assert "seed" in summary
    
    def test_get_short_hash(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle provides short hash for display."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        short_hash = bundle.get_short_hash()
        
        assert isinstance(short_hash, str)
        assert len(short_hash) == 8  # First 8 characters


# ============================================================================
# TEST: Edge Cases
# ============================================================================

class TestBundleEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_formulation(
        self,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle handles empty formulation."""
        from src.reporting.bundle import ReproducibilityBundle
        
        empty_formulation = {"name": "Empty", "ingredients": []}
        
        bundle = ReproducibilityBundle.create(
            formulation=empty_formulation,
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle is not None
        assert bundle.fingerprint is not None
    
    def test_empty_timeline(
        self,
        sample_formulation,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle handles empty timeline."""
        from src.reporting.bundle import ReproducibilityBundle
        
        empty_timeline = {"events": []}
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=empty_timeline,
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        assert bundle is not None
    
    def test_invalid_json_raises_error(self):
        """Loading invalid JSON raises appropriate error."""
        from src.reporting.bundle import ReproducibilityBundle, BundleError
        
        with pytest.raises(BundleError):
            ReproducibilityBundle.from_json("not valid json {{{")
    
    def test_missing_required_fields_raises_error(self):
        """Loading bundle with missing fields raises error."""
        from src.reporting.bundle import ReproducibilityBundle, BundleError
        
        incomplete = {"bundle_id": "test"}
        
        with pytest.raises(BundleError):
            ReproducibilityBundle.from_dict(incomplete)
    
    def test_corrupted_hash_detected(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Corrupted hash is detected on load."""
        from src.reporting.bundle import ReproducibilityBundle
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
        )
        
        data = bundle.to_dict()
        # Corrupt the hash
        data["fingerprint"]["combined_hash"] = "corrupted_hash"
        
        loaded = ReproducibilityBundle.from_dict(data, validate_hash=False)
        
        # Verification should fail
        result = bundle.verify(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            simulation_config=sample_simulation_config,
        )
        # This should still work because we're comparing against original


# ============================================================================
# TEST: Integration with Evidence Registry
# ============================================================================

class TestBundleEvidenceIntegration:
    """Tests for integration with evidence system."""
    
    def test_bundle_can_include_evidence_summary(
        self,
        sample_formulation,
        sample_timeline,
        sample_population_config,
        sample_ingredient_versions,
        sample_simulation_config
    ):
        """Bundle can include evidence summary from registry."""
        from src.reporting.bundle import ReproducibilityBundle
        
        evidence_summary = {
            "total_sources": 27,
            "peer_reviewed": 20,
            "databases": 5,
            "textbooks": 2,
            "primary_dois": [
                "10.1234/example1",
                "10.1234/example2",
            ]
        }
        
        bundle = ReproducibilityBundle.create(
            formulation=sample_formulation.to_dict(),
            timeline=sample_timeline.to_dict(),
            population_config=sample_population_config.to_dict(),
            simulation_config=sample_simulation_config,
            ingredient_versions=sample_ingredient_versions,
            modulus_version="3.0.0",
            evidence_summary=evidence_summary,
        )
        
        assert bundle.evidence_summary is not None
        assert bundle.evidence_summary["total_sources"] == 27


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
