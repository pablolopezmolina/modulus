"""
InteractionGraph - Contract 4.1

Manages the graph of interactions between compounds and applies them
to effects during simulation.

Contract requirements:
- get_applicable_interactions() only returns interactions where both compounds present
- apply_interactions() applies synergies first, then antagonisms
- Result never has negative values for parameters that must be positive
"""
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path

from .interaction import Interaction, ContextInteraction


# Parameters that should never be negative
NON_NEGATIVE_PARAMS = {
    "jitter_risk",
    "sleep_disruption_risk",
    "crash_risk",
    "alertness",
    "focus",
    "energy",
    "absorption_rate",
    "bioavailability",
    "creatine_uptake",
    "glucose_peak",
    "caffeine_concentration",
}


class InteractionGraph:
    """
    Graph of compound interactions with lookup and application methods.
    
    Contract 4.1 specifies:
    - get_applicable_interactions() only returns interactions where both compounds present
    - apply_interactions() applies in order: synergies first, then antagonisms
    - Result never has negative values for positive parameters
    
    The graph is loaded from a JSON file with the following structure:
    {
        "version": "1.0",
        "interactions": [...],
        "context_rules": [...]
    }
    """
    
    def __init__(self, json_path: str):
        """
        Initialize the interaction graph from a JSON file.
        
        Args:
            json_path: Path to interactions.json
        """
        self._interactions: Dict[Tuple[str, str], List[Interaction]] = {}
        self._context_rules: List[ContextInteraction] = []
        self._all_compounds: Set[str] = set()
        
        self._load_from_json(json_path)
    
    def _load_from_json(self, json_path: str) -> None:
        """Load interactions from JSON file."""
        path = Path(json_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Interactions file not found: {json_path}")
        
        with open(path, "r") as f:
            data = json.load(f)
        
        # Load compound-compound interactions
        for i_data in data.get("interactions", []):
            interaction = Interaction.from_dict(i_data)
            key = interaction.key
            
            if key not in self._interactions:
                self._interactions[key] = []
            self._interactions[key].append(interaction)
            
            # Track all compounds
            self._all_compounds.add(interaction.compound_a)
            self._all_compounds.add(interaction.compound_b)
        
        # Load context rules (optional)
        for rule_data in data.get("context_rules", []):
            rule = ContextInteraction.from_dict(rule_data)
            self._context_rules.append(rule)
            self._all_compounds.add(rule.compound_id)
    
    @property
    def interaction_count(self) -> int:
        """Total number of compound-compound interactions."""
        return sum(len(interactions) for interactions in self._interactions.values())
    
    @property
    def context_rule_count(self) -> int:
        """Total number of context rules."""
        return len(self._context_rules)
    
    @property
    def compounds_with_interactions(self) -> Set[str]:
        """Set of all compounds that have at least one interaction."""
        return self._all_compounds.copy()
    
    def get_interaction(
        self, 
        compound_a: str, 
        compound_b: str
    ) -> Optional[List[Interaction]]:
        """
        Get interactions between two specific compounds.
        
        Args:
            compound_a: First compound ID
            compound_b: Second compound ID
            
        Returns:
            List of interactions or None if no interaction exists
        """
        # Normalize order
        if compound_a > compound_b:
            compound_a, compound_b = compound_b, compound_a
        
        return self._interactions.get((compound_a, compound_b))
    
    def get_applicable_interactions(
        self,
        compounds_present: List[Tuple[str, float]]
    ) -> List[Interaction]:
        """
        Get all interactions that apply given the compounds and doses present.
        
        Contract: Only returns interactions where BOTH compounds are present.
        
        Args:
            compounds_present: List of (compound_id, dose) tuples
            
        Returns:
            List of applicable Interaction objects
        """
        applicable = []
        
        # Create lookup for compounds and their doses
        compound_doses: Dict[str, float] = {}
        for compound_id, dose in compounds_present:
            # Aggregate doses if compound appears multiple times
            if compound_id in compound_doses:
                compound_doses[compound_id] += dose
            else:
                compound_doses[compound_id] = dose
        
        compound_ids = set(compound_doses.keys())
        
        # Check each interaction
        for key, interactions in self._interactions.items():
            compound_a, compound_b = key
            
            # Both compounds must be present (Contract requirement)
            if compound_a not in compound_ids or compound_b not in compound_ids:
                continue
            
            dose_a = compound_doses[compound_a]
            dose_b = compound_doses[compound_b]
            
            for interaction in interactions:
                # Check dose thresholds
                if interaction.applies_at_doses(dose_a, dose_b):
                    applicable.append(interaction)
        
        return applicable
    
    def get_context_interactions(
        self,
        compounds_present: List[Tuple[str, float]],
        context: Dict[str, Any]
    ) -> List[ContextInteraction]:
        """
        Get context-based interactions that apply.
        
        These are single-compound rules triggered by context (time, total dose, etc.)
        
        Args:
            compounds_present: List of (compound_id, dose) tuples
            context: Context information (time_of_day_minutes, total_caffeine_mg, etc.)
            
        Returns:
            List of applicable ContextInteraction objects
        """
        applicable = []
        
        # Create lookup for compounds
        compound_ids = {c[0] for c in compounds_present}
        
        for rule in self._context_rules:
            # Compound must be present
            if rule.compound_id not in compound_ids:
                continue
            
            # Check condition
            if rule.check_condition(context):
                applicable.append(rule)
        
        return applicable
    
    def apply_interactions(
        self,
        base_effects: Dict[str, float],
        interactions: List[Interaction]
    ) -> Dict[str, float]:
        """
        Apply interactions to base effects, returning modified effects.
        
        Contract requirements:
        - Apply synergies first, then antagonisms, then absorption, then metabolism
        - Result never has negative values for non-negative parameters
        
        Args:
            base_effects: Dictionary of {param_name: value}
            interactions: List of interactions to apply
            
        Returns:
            Modified effects dictionary
        """
        # Make a copy to avoid mutating input
        modified = base_effects.copy()
        
        # Sort interactions by type priority
        # Order: synergies first, then antagonisms, then others
        priority_order = {"synergy": 0, "antagonism": 1, "absorption": 2, "metabolism": 3}
        sorted_interactions = sorted(
            interactions,
            key=lambda i: priority_order.get(i.interaction_type, 4)
        )
        
        # Apply each interaction
        for interaction in sorted_interactions:
            param = interaction.target_param
            
            # Get current value (default to 0 if not present)
            current_value = modified.get(param, 0.0)
            
            # Apply the modifier
            new_value = interaction.apply_to(current_value)
            
            # Clamp to non-negative if required (Contract requirement)
            if param in NON_NEGATIVE_PARAMS and new_value < 0:
                new_value = 0.0
            
            modified[param] = new_value
        
        return modified
    
    def apply_context_interactions(
        self,
        base_effects: Dict[str, float],
        context_interactions: List[ContextInteraction]
    ) -> Dict[str, float]:
        """
        Apply context-based interactions to base effects.
        
        Args:
            base_effects: Dictionary of {param_name: value}
            context_interactions: List of context interactions to apply
            
        Returns:
            Modified effects dictionary
        """
        modified = base_effects.copy()
        
        for rule in context_interactions:
            param = rule.target_param
            current_value = modified.get(param, 0.0)
            
            if rule.modifier_type == "multiply":
                new_value = current_value * rule.modifier_value
            elif rule.modifier_type == "add":
                new_value = current_value + rule.modifier_value
            elif rule.modifier_type == "replace":
                new_value = rule.modifier_value
            else:
                new_value = current_value
            
            # Clamp to non-negative if required
            if param in NON_NEGATIVE_PARAMS and new_value < 0:
                new_value = 0.0
            
            modified[param] = new_value
        
        return modified
    
    def get_all_interactions_for_compound(
        self, 
        compound_id: str
    ) -> List[Tuple[str, Interaction]]:
        """
        Get all interactions that involve a specific compound.
        
        Args:
            compound_id: The compound to search for
            
        Returns:
            List of (other_compound, interaction) tuples
        """
        results = []
        
        for key, interactions in self._interactions.items():
            compound_a, compound_b = key
            
            if compound_a == compound_id:
                for interaction in interactions:
                    results.append((compound_b, interaction))
            elif compound_b == compound_id:
                for interaction in interactions:
                    results.append((compound_a, interaction))
        
        return results
    
    def list_all_interactions(self) -> List[Interaction]:
        """Get a flat list of all compound-compound interactions."""
        all_interactions = []
        for interactions in self._interactions.values():
            all_interactions.extend(interactions)
        return all_interactions
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the graph to a dictionary.
        
        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "version": "1.0",
            "interactions": [
                i.to_dict() 
                for interactions in self._interactions.values()
                for i in interactions
            ],
            "context_rules": [rule.to_dict() for rule in self._context_rules]
        }
    
    def __repr__(self) -> str:
        return (
            f"InteractionGraph("
            f"{self.interaction_count} interactions, "
            f"{self.context_rule_count} context rules, "
            f"{len(self._all_compounds)} compounds)"
        )
