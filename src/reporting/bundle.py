"""
Reproducibility Bundle for MODULUS (Sesión 9.2)

This module provides the ReproducibilityBundle system for Pack 2 auditing.
It allows clients to recreate any simulation exactly as it was run originally.

Key features:
- Complete input capture (formulation, timeline, config, versions)
- SHA-256 fingerprinting for verification
- Export/import to JSON
- Version compatibility checking
- Integration with Evidence Registry

Example usage:
    bundle = ReproducibilityBundle.create(
        formulation=formulation.to_dict(),
        timeline=timeline.to_dict(),
        population_config=pop_config.to_dict(),
        simulation_config={"seed": 42, "dt_minutes": 1.0},
        ingredient_versions={"caffeine": "1.2.0"},
        modulus_version="3.0.0",
    )
    
    # Export
    bundle.export("simulation_bundle.json")
    
    # Later, verify
    result = bundle.verify(
        formulation=new_formulation.to_dict(),
        timeline=new_timeline.to_dict(),
        simulation_config=new_config,
    )
    assert result.is_valid
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
# EXCEPTIONS
# ============================================================================

class BundleError(Exception):
    """Base exception for bundle operations."""
    pass


class BundleValidationError(BundleError):
    """Raised when bundle validation fails."""
    pass


class BundleVersionError(BundleError):
    """Raised when version compatibility check fails."""
    pass


# ============================================================================
# BUNDLE CONFIG
# ============================================================================

@dataclass
class BundleConfig:
    """
    Configuration parameters for a simulation bundle.
    
    Contains simulation parameters and version information
    that affect reproducibility.
    """
    simulation_params: Dict[str, Any]
    modulus_version: str
    ingredients_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "simulation_params": self.simulation_params,
            "modulus_version": self.modulus_version,
            "ingredients_version": self.ingredients_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BundleConfig":
        """Create from dictionary."""
        return cls(
            simulation_params=data["simulation_params"],
            modulus_version=data["modulus_version"],
            ingredients_version=data["ingredients_version"],
        )


# ============================================================================
# SIMULATION FINGERPRINT
# ============================================================================

@dataclass
class SimulationFingerprint:
    """
    Cryptographic fingerprint of simulation inputs.
    
    Uses SHA-256 to create deterministic hashes of:
    - Input data (formulation + timeline)
    - Configuration (seed, dt, etc.)
    - Combined hash for quick verification
    """
    input_hash: str
    config_hash: str
    combined_hash: str
    algorithm: str = "sha256"
    
    @classmethod
    def from_data(
        cls,
        formulation: Dict[str, Any],
        timeline: Dict[str, Any],
        config: Dict[str, Any],
    ) -> "SimulationFingerprint":
        """
        Create fingerprint from simulation data.
        
        Args:
            formulation: Formulation dictionary
            timeline: Timeline dictionary
            config: Simulation config dictionary
            
        Returns:
            SimulationFingerprint with computed hashes
        """
        # Create deterministic JSON representations
        input_data = {
            "formulation": formulation,
            "timeline": timeline,
        }
        input_json = json.dumps(input_data, sort_keys=True, separators=(',', ':'))
        config_json = json.dumps(config, sort_keys=True, separators=(',', ':'))
        
        # Compute hashes
        input_hash = hashlib.sha256(input_json.encode('utf-8')).hexdigest()
        config_hash = hashlib.sha256(config_json.encode('utf-8')).hexdigest()
        
        # Combined hash
        combined_data = f"{input_hash}:{config_hash}"
        combined_hash = hashlib.sha256(combined_data.encode('utf-8')).hexdigest()
        
        return cls(
            input_hash=input_hash,
            config_hash=config_hash,
            combined_hash=combined_hash,
            algorithm="sha256",
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "input_hash": self.input_hash,
            "config_hash": self.config_hash,
            "combined_hash": self.combined_hash,
            "algorithm": self.algorithm,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationFingerprint":
        """Create from dictionary."""
        return cls(
            input_hash=data["input_hash"],
            config_hash=data["config_hash"],
            combined_hash=data["combined_hash"],
            algorithm=data.get("algorithm", "sha256"),
        )


# ============================================================================
# VERIFICATION RESULT
# ============================================================================

@dataclass
class BundleVerificationResult:
    """
    Result of verifying inputs against a bundle.
    
    Provides detailed information about what matched and what didn't.
    """
    is_valid: bool
    input_match: bool
    config_match: bool
    mismatches: List[str] = field(default_factory=list)
    expected_hash: str = ""
    actual_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "input_match": self.input_match,
            "config_match": self.config_match,
            "mismatches": self.mismatches,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
        }


# ============================================================================
# REPRODUCIBILITY BUNDLE
# ============================================================================

@dataclass
class ReproducibilityBundle:
    """
    Complete reproducibility package for a MODULUS simulation.
    
    Contains all information needed to reproduce a simulation exactly:
    - All input data (formulation, timeline, population config)
    - Configuration (seed, dt, duration)
    - Version information (MODULUS, ingredients)
    - Cryptographic fingerprint for verification
    - Optional evidence summary
    
    This is the core deliverable for Pack 2 auditing requirements.
    """
    bundle_id: str
    created_at: str
    modulus_version: str
    seed: int
    fingerprint: SimulationFingerprint
    inputs: Dict[str, Any]
    simulation_config: Dict[str, Any]
    ingredient_versions: Dict[str, str]
    population_config: Dict[str, Any]
    evidence_summary: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create(
        cls,
        formulation: Dict[str, Any],
        timeline: Dict[str, Any],
        population_config: Dict[str, Any],
        simulation_config: Dict[str, Any],
        ingredient_versions: Dict[str, str],
        modulus_version: str,
        evidence_summary: Optional[Dict[str, Any]] = None,
    ) -> "ReproducibilityBundle":
        """
        Create a new reproducibility bundle.
        
        Args:
            formulation: Complete formulation data
            timeline: Complete timeline data
            population_config: Population generation config
            simulation_config: Simulation parameters (must include 'seed')
            ingredient_versions: Version map for ingredients
            modulus_version: MODULUS engine version
            evidence_summary: Optional evidence registry summary
            
        Returns:
            New ReproducibilityBundle instance
        """
        # Generate unique ID
        bundle_id = f"MODB-{uuid.uuid4().hex[:12].upper()}"
        
        # Timestamp in ISO format
        created_at = datetime.now(timezone.utc).isoformat()
        
        # Create fingerprint
        fingerprint = SimulationFingerprint.from_data(
            formulation=formulation,
            timeline=timeline,
            config=simulation_config,
        )
        
        # Extract seed
        seed = simulation_config.get("seed", 0)
        
        # Package inputs
        inputs = {
            "formulation": formulation,
            "timeline": timeline,
        }
        
        return cls(
            bundle_id=bundle_id,
            created_at=created_at,
            modulus_version=modulus_version,
            seed=seed,
            fingerprint=fingerprint,
            inputs=inputs,
            simulation_config=simulation_config,
            ingredient_versions=ingredient_versions,
            population_config=population_config,
            evidence_summary=evidence_summary,
        )
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize bundle to dictionary.
        
        Returns:
            Complete bundle as dictionary
        """
        return {
            "bundle_id": self.bundle_id,
            "created_at": self.created_at,
            "modulus_version": self.modulus_version,
            "seed": self.seed,
            "fingerprint": self.fingerprint.to_dict(),
            "inputs": self.inputs,
            "simulation_config": self.simulation_config,
            "ingredient_versions": self.ingredient_versions,
            "population_config": self.population_config,
            "evidence_summary": self.evidence_summary,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Serialize bundle to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(
        cls, 
        data: Dict[str, Any],
        validate_hash: bool = True,
    ) -> "ReproducibilityBundle":
        """
        Create bundle from dictionary.
        
        Args:
            data: Bundle dictionary
            validate_hash: Whether to validate hash integrity
            
        Returns:
            ReproducibilityBundle instance
            
        Raises:
            BundleError: If required fields are missing
        """
        required_fields = [
            "bundle_id", "created_at", "modulus_version", "seed",
            "fingerprint", "inputs", "simulation_config", "ingredient_versions",
        ]
        
        for field_name in required_fields:
            if field_name not in data:
                raise BundleError(f"Missing required field: {field_name}")
        
        fingerprint = SimulationFingerprint.from_dict(data["fingerprint"])
        
        return cls(
            bundle_id=data["bundle_id"],
            created_at=data["created_at"],
            modulus_version=data["modulus_version"],
            seed=data["seed"],
            fingerprint=fingerprint,
            inputs=data["inputs"],
            simulation_config=data["simulation_config"],
            ingredient_versions=data["ingredient_versions"],
            population_config=data.get("population_config", {}),
            evidence_summary=data.get("evidence_summary"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "ReproducibilityBundle":
        """
        Create bundle from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            ReproducibilityBundle instance
            
        Raises:
            BundleError: If JSON is invalid
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise BundleError(f"Invalid JSON: {e}")
        
        return cls.from_dict(data)
    
    # ========================================================================
    # FILE I/O
    # ========================================================================
    
    def export(self, path: Union[str, Path]) -> Path:
        """
        Export bundle to JSON file.
        
        Args:
            path: Output file path
            
        Returns:
            Path to created file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        
        return path
    
    @classmethod
    def load(cls, path: Union[str, Path]) -> "ReproducibilityBundle":
        """
        Load bundle from JSON file.
        
        Args:
            path: Input file path
            
        Returns:
            ReproducibilityBundle instance
            
        Raises:
            BundleError: If file cannot be read or parsed
        """
        path = Path(path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                json_str = f.read()
        except IOError as e:
            raise BundleError(f"Cannot read file: {e}")
        
        return cls.from_json(json_str)
    
    def get_default_filename(self) -> str:
        """
        Generate default filename for export.
        
        Returns:
            Filename string like 'modulus_bundle_MODB-ABC123_20250108.json'
        """
        # Parse date from created_at
        try:
            dt = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y%m%d')
        except ValueError:
            date_str = datetime.now().strftime('%Y%m%d')
        
        return f"modulus_bundle_{self.bundle_id}_{date_str}.json"
    
    # ========================================================================
    # VERIFICATION
    # ========================================================================
    
    def verify(
        self,
        formulation: Dict[str, Any],
        timeline: Dict[str, Any],
        simulation_config: Dict[str, Any],
    ) -> BundleVerificationResult:
        """
        Verify that given inputs match this bundle.
        
        Args:
            formulation: Formulation to verify
            timeline: Timeline to verify
            simulation_config: Config to verify
            
        Returns:
            BundleVerificationResult with match details
        """
        # Compute fingerprint of provided inputs
        new_fingerprint = SimulationFingerprint.from_data(
            formulation=formulation,
            timeline=timeline,
            config=simulation_config,
        )
        
        # Compare
        input_match = new_fingerprint.input_hash == self.fingerprint.input_hash
        config_match = new_fingerprint.config_hash == self.fingerprint.config_hash
        is_valid = input_match and config_match
        
        # Collect mismatches
        mismatches = []
        
        if not input_match:
            # Determine what's different
            if formulation != self.inputs.get("formulation"):
                mismatches.append("formulation")
            if timeline != self.inputs.get("timeline"):
                mismatches.append("timeline")
        
        if not config_match:
            # Check specific config differences
            original_config = self.simulation_config
            for key in set(list(simulation_config.keys()) + list(original_config.keys())):
                if simulation_config.get(key) != original_config.get(key):
                    mismatches.append(f"config.{key}")
        
        return BundleVerificationResult(
            is_valid=is_valid,
            input_match=input_match,
            config_match=config_match,
            mismatches=mismatches,
            expected_hash=self.fingerprint.combined_hash,
            actual_hash=new_fingerprint.combined_hash,
        )
    
    # ========================================================================
    # VERSION COMPATIBILITY
    # ========================================================================
    
    def check_version_compatibility(
        self, 
        current_version: str,
    ) -> Tuple[bool, List[str]]:
        """
        Check if bundle is compatible with current MODULUS version.
        
        Compatibility rules:
        - Same major.minor.patch: Fully compatible
        - Same major.minor, different patch: Compatible with warning
        - Same major, different minor: Compatible with warning
        - Different major: NOT compatible
        
        Args:
            current_version: Current MODULUS version string
            
        Returns:
            Tuple of (is_compatible, list of warnings)
        """
        def parse_version(v: str) -> Tuple[int, int, int]:
            parts = v.split('.')
            return (
                int(parts[0]) if len(parts) > 0 else 0,
                int(parts[1]) if len(parts) > 1 else 0,
                int(parts[2]) if len(parts) > 2 else 0,
            )
        
        bundle_ver = parse_version(self.modulus_version)
        current_ver = parse_version(current_version)
        
        warnings = []
        
        # Major version must match
        if bundle_ver[0] != current_ver[0]:
            return False, [
                f"Major version mismatch: bundle={self.modulus_version}, "
                f"current={current_version}. Results may differ significantly."
            ]
        
        # Minor version difference
        if bundle_ver[1] != current_ver[1]:
            warnings.append(
                f"Minor version differs: bundle={self.modulus_version}, "
                f"current={current_version}. Some behaviors may differ."
            )
        
        # Patch version difference
        if bundle_ver[2] != current_ver[2]:
            warnings.append(
                f"Patch version differs: bundle={self.modulus_version}, "
                f"current={current_version}. Minor differences possible."
            )
        
        return True, warnings
    
    # ========================================================================
    # SUMMARY AND DISPLAY
    # ========================================================================
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get human-readable summary of bundle.
        
        Returns:
            Summary dictionary for display
        """
        return {
            "bundle_id": self.bundle_id,
            "created_at": self.created_at,
            "modulus_version": self.modulus_version,
            "seed": self.seed,
            "hash": self.get_short_hash(),
            "full_hash": self.fingerprint.combined_hash,
            "n_ingredients": len(self.ingredient_versions),
            "has_evidence": self.evidence_summary is not None,
        }
    
    def get_short_hash(self, length: int = 8) -> str:
        """
        Get truncated hash for display.
        
        Args:
            length: Number of characters to return
            
        Returns:
            First N characters of combined hash
        """
        return self.fingerprint.combined_hash[:length]
    
    def __repr__(self) -> str:
        return (
            f"ReproducibilityBundle("
            f"id={self.bundle_id}, "
            f"version={self.modulus_version}, "
            f"hash={self.get_short_hash()})"
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_bundle_from_simulation(
    formulation: Any,
    timeline: Any,
    population_config: Any,
    simulation_config: Dict[str, Any],
    ingredient_library: Any = None,
    evidence_registry: Any = None,
    modulus_version: str = "3.0.0",
) -> ReproducibilityBundle:
    """
    Convenience function to create bundle from simulation objects.
    
    Handles conversion from domain objects to dictionaries.
    
    Args:
        formulation: Formulation object or dict
        timeline: Timeline object or dict
        population_config: PopulationConfig object or dict
        simulation_config: Simulation config dict
        ingredient_library: Optional IngredientLibrary for versions
        evidence_registry: Optional EvidenceRegistry for summary
        modulus_version: MODULUS version string
        
    Returns:
        ReproducibilityBundle instance
    """
    # Convert objects to dicts if needed
    formulation_dict = (
        formulation.to_dict() 
        if hasattr(formulation, 'to_dict') 
        else formulation
    )
    
    timeline_dict = (
        timeline.to_dict() 
        if hasattr(timeline, 'to_dict') 
        else timeline
    )
    
    pop_config_dict = (
        population_config.to_dict() 
        if hasattr(population_config, 'to_dict') 
        else population_config
    )
    
    # Get ingredient versions
    ingredient_versions = {}
    if ingredient_library is not None:
        if hasattr(ingredient_library, 'get_versions'):
            ingredient_versions = ingredient_library.get_versions()
        elif hasattr(ingredient_library, 'version'):
            ingredient_versions = {"library_version": ingredient_library.version}
    
    # Get evidence summary
    evidence_summary = None
    if evidence_registry is not None:
        if hasattr(evidence_registry, 'get_summary'):
            evidence_summary = evidence_registry.get_summary()
    
    return ReproducibilityBundle.create(
        formulation=formulation_dict,
        timeline=timeline_dict,
        population_config=pop_config_dict,
        simulation_config=simulation_config,
        ingredient_versions=ingredient_versions,
        modulus_version=modulus_version,
        evidence_summary=evidence_summary,
    )


def verify_bundle_file(
    bundle_path: Union[str, Path],
    formulation: Any,
    timeline: Any,
    simulation_config: Dict[str, Any],
) -> BundleVerificationResult:
    """
    Convenience function to verify inputs against a bundle file.
    
    Args:
        bundle_path: Path to bundle JSON file
        formulation: Formulation to verify
        timeline: Timeline to verify
        simulation_config: Config to verify
        
    Returns:
        BundleVerificationResult
    """
    bundle = ReproducibilityBundle.load(bundle_path)
    
    formulation_dict = (
        formulation.to_dict() 
        if hasattr(formulation, 'to_dict') 
        else formulation
    )
    
    timeline_dict = (
        timeline.to_dict() 
        if hasattr(timeline, 'to_dict') 
        else timeline
    )
    
    return bundle.verify(
        formulation=formulation_dict,
        timeline=timeline_dict,
        simulation_config=simulation_config,
    )
