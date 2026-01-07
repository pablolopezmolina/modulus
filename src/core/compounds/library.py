"""
Ingredient Library - manages collection of compound profiles.

Contract 3.2 Compliance:
- get_compound(compound_id) → CompoundProfile, raises KeyError if not found
- list_compounds(category=None) → List[str] (IDs, not objects)
- get_interaction(compound_a, compound_b) → Optional[Interaction] (returns None for now)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Any

from .profile import CompoundProfile


class IngredientLibrary:
    """
    Library of compound profiles loaded from JSON.
    
    Contract 3.2:
    - get_compound() raises KeyError if not found
    - list_compounds() returns IDs, not full objects
    - get_interaction() returns None (no interactions yet)
    
    Example:
        >>> library = IngredientLibrary("data/reference/ingredients.json")
        >>> caffeine = library.get_compound("caffeine")
        >>> library.list_compounds(category="stimulant")
        ['caffeine']
    """
    
    def __init__(self, json_path: Optional[str] = None):
        """
        Initialize library from JSON file.
        
        Args:
            json_path: Path to ingredients.json file.
                      If None, creates empty library.
        """
        self._compounds: Dict[str, CompoundProfile] = {}
        self._metadata: Dict[str, Any] = {}
        
        if json_path is not None:
            self._load_from_json(json_path)
    
    def _load_from_json(self, json_path: str) -> None:
        """Load compounds from JSON file."""
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Ingredients file not found: {json_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Store metadata
        self._metadata = {
            "version": data.get("version", "unknown"),
            "last_updated": data.get("last_updated", "unknown"),
            "description": data.get("description", ""),
        }
        
        # Load compounds
        compounds_data = data.get("compounds", [])
        for compound_data in compounds_data:
            profile = self._parse_compound(compound_data)
            self._compounds[profile.compound_id] = profile
    
    def _parse_compound(self, data: Dict[str, Any]) -> CompoundProfile:
        """Parse compound data from JSON to CompoundProfile."""
        return CompoundProfile(
            compound_id=data["compound_id"],
            name=data["name"],
            category=data["category"],
            pk_model=data["pk_model"],
            pk_params=data.get("pk_params", {}),
            bioavailability=data["bioavailability"],
            pd_model=data["pd_model"],
            pd_params=data.get("pd_params", {}),
            target_system=data["target_system"],
            max_single_dose=data["max_single_dose"],
            max_daily_dose=data["max_daily_dose"],
            dose_unit=data["dose_unit"],
            evidence_level=data["evidence_level"],
            primary_sources=data.get("primary_sources", []),
        )
    
    # =========================================================================
    # Contract 3.2: Core Methods
    # =========================================================================
    
    def get_compound(self, compound_id: str) -> CompoundProfile:
        """
        Get compound by ID.
        
        Contract 3.2: Raises KeyError if compound not found.
        
        Args:
            compound_id: Unique compound identifier (snake_case)
        
        Returns:
            CompoundProfile for the compound
        
        Raises:
            KeyError: If compound_id not in library
        """
        if compound_id not in self._compounds:
            raise KeyError(f"Compound not found: {compound_id}")
        return self._compounds[compound_id]
    
    def list_compounds(self, category: Optional[str] = None) -> List[str]:
        """
        List compound IDs, optionally filtered by category.
        
        Contract 3.2: Returns IDs (strings), not full CompoundProfile objects.
        
        Args:
            category: If provided, only return compounds in this category
        
        Returns:
            List of compound_id strings
        """
        if category is None:
            return list(self._compounds.keys())
        
        return [
            compound_id 
            for compound_id, profile in self._compounds.items()
            if profile.category == category
        ]
    
    def get_interaction(
        self, 
        compound_a: str, 
        compound_b: str
    ) -> Optional[Any]:  # Will be Optional[Interaction] when implemented
        """
        Get interaction between two compounds.
        
        Contract 3.2: Returns None if no interaction defined.
        
        Note: Interactions will be implemented in Phase 3 (Sesión 8.2).
        
        Args:
            compound_a: First compound ID
            compound_b: Second compound ID
        
        Returns:
            None (interactions not yet implemented)
        """
        # Interactions will be loaded from interactions.json in Phase 3
        return None
    
    # =========================================================================
    # Additional Utility Methods
    # =========================================================================
    
    def list_categories(self) -> List[str]:
        """
        List all unique categories in the library.
        
        Returns:
            List of category strings
        """
        categories = set(profile.category for profile in self._compounds.values())
        return sorted(categories)
    
    def add_compound(self, profile: CompoundProfile) -> None:
        """
        Add a compound to the library.
        
        Args:
            profile: CompoundProfile to add
        
        Raises:
            ValueError: If compound_id already exists
        """
        if profile.compound_id in self._compounds:
            raise ValueError(f"Compound already exists: {profile.compound_id}")
        self._compounds[profile.compound_id] = profile
    
    @property
    def version(self) -> str:
        """Library version from JSON metadata."""
        return self._metadata.get("version", "unknown")
    
    @property
    def last_updated(self) -> str:
        """Last update date from JSON metadata."""
        return self._metadata.get("last_updated", "unknown")
    
    # =========================================================================
    # Python Magic Methods
    # =========================================================================
    
    def __len__(self) -> int:
        """Number of compounds in library."""
        return len(self._compounds)
    
    def __contains__(self, compound_id: str) -> bool:
        """Check if compound exists in library."""
        return compound_id in self._compounds
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over compound IDs."""
        return iter(self._compounds)
    
    def __repr__(self) -> str:
        return f"IngredientLibrary(compounds={len(self)}, version={self.version})"
