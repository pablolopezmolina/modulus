"""
IngredientLibrary - Database of compound profiles.

Implements Contract 3.2: IngredientLibrary from CONTRACTS.md.

The IngredientLibrary loads compound profiles from a JSON file and provides
methods to query and retrieve them.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator

from .profile import CompoundProfile


class IngredientLibrary:
    """
    Database of compound profiles loaded from JSON.
    
    Implements Contract 3.2 from CONTRACTS.md.
    
    The library loads all compound profiles from a JSON file on initialization
    and provides methods to query them.
    
    Contract 3.2 Requirements:
        - get_compound() raises KeyError if compound doesn't exist
        - list_compounds() returns IDs (strings), not objects
        - get_interaction() returns None if no interaction defined
    
    Example JSON structure:
        {
            "version": "1.0",
            "compounds": {
                "caffeine": {
                    "compound_id": "caffeine",
                    "name": "Caffeine",
                    "category": "stimulant",
                    ...
                },
                ...
            },
            "interactions": {
                ...
            }
        }
    """
    
    def __init__(self, json_path: str) -> None:
        """
        Load ingredient library from JSON file.
        
        Args:
            json_path: Path to JSON file with ingredient data.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValueError: If the JSON structure is invalid.
        """
        path = Path(json_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Ingredients file not found: {json_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._version: str = data.get("version", "unknown")
        self._compounds: Dict[str, CompoundProfile] = {}
        self._interactions: Dict[str, Any] = data.get("interactions", {})
        
        # Load all compounds
        compounds_data = data.get("compounds", {})
        for compound_id, compound_data in compounds_data.items():
            # Ensure compound_id in data matches the key
            if compound_data.get("compound_id") != compound_id:
                compound_data["compound_id"] = compound_id
            
            self._compounds[compound_id] = CompoundProfile.from_dict(compound_data)
    
    def get_compound(self, compound_id: str) -> CompoundProfile:
        """
        Get a compound profile by ID.
        
        Contract 3.2: Raises KeyError if compound doesn't exist.
        
        Args:
            compound_id: The unique compound identifier.
            
        Returns:
            The CompoundProfile for the compound.
            
        Raises:
            KeyError: If compound_id doesn't exist in the library.
        """
        if compound_id not in self._compounds:
            raise KeyError(f"Compound not found: '{compound_id}'")
        return self._compounds[compound_id]
    
    def list_compounds(self, category: Optional[str] = None) -> List[str]:
        """
        List all compound IDs, optionally filtered by category.
        
        Contract 3.2: Returns IDs (strings), not CompoundProfile objects.
        
        Args:
            category: Optional category to filter by (e.g., "stimulant", "amino").
                     If None, returns all compound IDs.
                     
        Returns:
            List of compound IDs matching the filter.
        """
        if category is None:
            return list(self._compounds.keys())
        
        return [
            cid for cid, profile in self._compounds.items()
            if profile.category == category
        ]
    
    def get_interaction(
        self, 
        compound_a: str, 
        compound_b: str
    ) -> Optional[Any]:
        """
        Get interaction between two compounds.
        
        Contract 3.2: Returns None if no interaction is defined.
        
        The order of compounds doesn't matter - the library normalizes
        to alphabetical order internally.
        
        Args:
            compound_a: First compound ID.
            compound_b: Second compound ID.
            
        Returns:
            Interaction data if defined, None otherwise.
            
        Note:
            Full Interaction support will be added in Fase 3 (Sesión 8.2).
            For now, this always returns None as no interactions are defined.
        """
        # Normalize order (Contract 3.3 requires compound_a < compound_b)
        if compound_a > compound_b:
            compound_a, compound_b = compound_b, compound_a
        
        # Create canonical key
        key = f"{compound_a}:{compound_b}"
        
        return self._interactions.get(key)
    
    def list_categories(self) -> List[str]:
        """
        List all unique categories in the library.
        
        Returns:
            Sorted list of unique category names.
        """
        categories = set(profile.category for profile in self._compounds.values())
        return sorted(categories)
    
    @property
    def version(self) -> str:
        """Get library version string."""
        return self._version
    
    def __len__(self) -> int:
        """Return number of compounds in library."""
        return len(self._compounds)
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over compound IDs."""
        return iter(self._compounds.keys())
    
    def __contains__(self, compound_id: str) -> bool:
        """Check if compound ID exists in library."""
        return compound_id in self._compounds
    
    def __repr__(self) -> str:
        return (
            f"IngredientLibrary(version='{self._version}', "
            f"compounds={len(self._compounds)})"
        )
