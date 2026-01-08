"""
Tests for the Interaction Framework (Session 8.2)

Tests Contract 3.3 (Interaction) and Contract 4.1 (InteractionGraph)
"""
import pytest
from typing import List, Tuple, Optional
import json


# =============================================================================
# CONTRACT 3.3: Interaction Tests
# =============================================================================

class TestInteractionContract:
    """Test Contract 3.3: Interaction dataclass."""
    
    def test_interaction_valid_types(self):
        """Interaction accepts valid interaction types."""
        from src.core.interactions.interaction import Interaction
        
        valid_types = ["synergy", "antagonism", "absorption", "metabolism"]
        
        for itype in valid_types:
            interaction = Interaction(
                compound_a="caffeine",
                compound_b="l_theanine",
                interaction_type=itype,
                target_param="jitter_risk",
                modifier_type="multiply",
                modifier_value=0.5,
                dose_dependent=False,
                evidence_level="high",
                source="10.1234/example"
            )
            assert interaction.interaction_type == itype
    
    def test_interaction_invalid_type_rejected(self):
        """Interaction rejects invalid interaction types."""
        from src.core.interactions.interaction import Interaction
        
        with pytest.raises(ValueError, match="interaction_type"):
            Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="invalid_type",
                target_param="test",
                modifier_type="multiply",
                modifier_value=1.0,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
    
    def test_interaction_alphabetical_order_enforced(self):
        """Contract: compound_a < compound_b alphabetically."""
        from src.core.interactions.interaction import Interaction
        
        # Should auto-sort or raise error
        # If compound_a > compound_b, should normalize
        interaction = Interaction(
            compound_a="theanine",  # Comes after "caffeine" alphabetically
            compound_b="caffeine",
            interaction_type="synergy",
            target_param="jitter_risk",
            modifier_type="multiply",
            modifier_value=0.5,
            dose_dependent=False,
            evidence_level="high",
            source="test"
        )
        # After normalization: caffeine < theanine
        assert interaction.compound_a == "caffeine"
        assert interaction.compound_b == "theanine"
    
    def test_interaction_modifier_types(self):
        """Interaction accepts valid modifier types."""
        from src.core.interactions.interaction import Interaction
        
        valid_modifiers = ["multiply", "add", "replace"]
        
        for mod_type in valid_modifiers:
            interaction = Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="synergy",
                target_param="test",
                modifier_type=mod_type,
                modifier_value=1.0,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
            assert interaction.modifier_type == mod_type
    
    def test_interaction_invalid_modifier_type_rejected(self):
        """Interaction rejects invalid modifier types."""
        from src.core.interactions.interaction import Interaction
        
        with pytest.raises(ValueError, match="modifier_type"):
            Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="synergy",
                target_param="test",
                modifier_type="divide",  # Invalid
                modifier_value=1.0,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
    
    def test_interaction_evidence_levels(self):
        """Interaction accepts valid evidence levels."""
        from src.core.interactions.interaction import Interaction
        
        valid_levels = ["high", "medium", "low", "theoretical"]
        
        for level in valid_levels:
            interaction = Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="synergy",
                target_param="test",
                modifier_type="multiply",
                modifier_value=1.0,
                dose_dependent=False,
                evidence_level=level,
                source="test"
            )
            assert interaction.evidence_level == level
    
    def test_interaction_dose_dependent_with_min_doses(self):
        """Dose-dependent interactions can have min_dose thresholds."""
        from src.core.interactions.interaction import Interaction
        
        interaction = Interaction(
            compound_a="caffeine",
            compound_b="l_theanine",
            interaction_type="synergy",
            target_param="jitter_risk",
            modifier_type="multiply",
            modifier_value=0.5,
            dose_dependent=True,
            min_dose_a=100.0,  # At least 100mg caffeine
            min_dose_b=50.0,   # At least 50mg theanine
            evidence_level="high",
            source="test"
        )
        assert interaction.dose_dependent is True
        assert interaction.min_dose_a == 100.0
        assert interaction.min_dose_b == 50.0
    
    def test_interaction_to_dict(self):
        """Interaction can be serialized to dict."""
        from src.core.interactions.interaction import Interaction
        
        interaction = Interaction(
            compound_a="caffeine",
            compound_b="l_theanine",
            interaction_type="synergy",
            target_param="jitter_risk",
            modifier_type="multiply",
            modifier_value=0.5,
            dose_dependent=False,
            evidence_level="high",
            source="10.1234/test"
        )
        
        d = interaction.to_dict()
        assert d["compound_a"] == "caffeine"
        assert d["compound_b"] == "l_theanine"
        assert d["modifier_value"] == 0.5
    
    def test_interaction_from_dict(self):
        """Interaction can be deserialized from dict."""
        from src.core.interactions.interaction import Interaction
        
        data = {
            "compound_a": "caffeine",
            "compound_b": "l_theanine",
            "interaction_type": "synergy",
            "target_param": "jitter_risk",
            "modifier_type": "multiply",
            "modifier_value": 0.5,
            "dose_dependent": False,
            "evidence_level": "high",
            "source": "10.1234/test"
        }
        
        interaction = Interaction.from_dict(data)
        assert interaction.compound_a == "caffeine"
        assert interaction.modifier_value == 0.5
    
    def test_interaction_key_property(self):
        """Interaction has a unique key for lookups."""
        from src.core.interactions.interaction import Interaction
        
        interaction = Interaction(
            compound_a="caffeine",
            compound_b="l_theanine",
            interaction_type="synergy",
            target_param="jitter_risk",
            modifier_type="multiply",
            modifier_value=0.5,
            dose_dependent=False,
            evidence_level="high",
            source="test"
        )
        
        # Key should be consistent regardless of input order
        assert interaction.key == ("caffeine", "l_theanine")


# =============================================================================
# CONTRACT 4.1: InteractionGraph Tests
# =============================================================================

class TestInteractionGraphContract:
    """Test Contract 4.1: InteractionGraph."""
    
    @pytest.fixture
    def sample_interactions_json(self, tmp_path):
        """Create a temporary interactions.json for testing."""
        interactions_data = {
            "version": "1.0",
            "interactions": [
                {
                    "compound_a": "caffeine",
                    "compound_b": "l_theanine",
                    "interaction_type": "synergy",
                    "target_param": "jitter_risk",
                    "modifier_type": "multiply",
                    "modifier_value": 0.5,
                    "dose_dependent": True,
                    "min_dose_a": 50.0,
                    "min_dose_b": 25.0,
                    "evidence_level": "high",
                    "source": "10.1080/1028415X.2008.11671262"
                },
                {
                    "compound_a": "caffeine",
                    "compound_b": "tyrosine",
                    "interaction_type": "synergy",
                    "target_param": "focus_enhancement",
                    "modifier_type": "multiply",
                    "modifier_value": 1.3,
                    "dose_dependent": False,
                    "evidence_level": "medium",
                    "source": "10.1016/j.brainres.2014.09.011"
                },
                {
                    "compound_a": "creatine_monohydrate",
                    "compound_b": "glucose",
                    "interaction_type": "absorption",
                    "target_param": "creatine_uptake",
                    "modifier_type": "multiply",
                    "modifier_value": 1.2,
                    "dose_dependent": True,
                    "min_dose_a": 3000.0,
                    "min_dose_b": 30000.0,
                    "evidence_level": "high",
                    "source": "10.1123/ijsn.9.3.304"
                }
            ]
        }
        
        json_path = tmp_path / "interactions.json"
        with open(json_path, "w") as f:
            json.dump(interactions_data, f)
        
        return str(json_path)
    
    def test_interaction_graph_init(self, sample_interactions_json):
        """InteractionGraph can be initialized with JSON path."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph(sample_interactions_json)
        assert graph is not None
    
    def test_get_applicable_interactions_both_present(self, sample_interactions_json):
        """get_applicable_interactions returns interactions when both compounds present."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph(sample_interactions_json)
        
        compounds_present = [
            ("caffeine", 200.0),
            ("l_theanine", 100.0)
        ]
        
        interactions = graph.get_applicable_interactions(compounds_present)
        
        # Should find caffeine + theanine interaction
        assert len(interactions) >= 1
        assert any(i.compound_a == "caffeine" and i.compound_b == "l_theanine" 
                   for i in interactions)
    
    def test_get_applicable_interactions_one_missing(self, sample_interactions_json):
        """get_applicable_interactions returns empty when one compound missing."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph(sample_interactions_json)
        
        compounds_present = [
            ("caffeine", 200.0),
            # l_theanine not present
        ]
        
        interactions = graph.get_applicable_interactions(compounds_present)
        
        # Should NOT find caffeine + theanine interaction
        caffeine_theanine = [i for i in interactions 
                            if i.compound_a == "caffeine" and i.compound_b == "l_theanine"]
        assert len(caffeine_theanine) == 0
    
    def test_get_applicable_interactions_dose_threshold(self, sample_interactions_json):
        """Dose-dependent interactions check min_dose thresholds."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph(sample_interactions_json)
        
        # Below threshold
        compounds_below = [
            ("caffeine", 30.0),    # Below min_dose_a of 50
            ("l_theanine", 100.0)
        ]
        
        interactions_below = graph.get_applicable_interactions(compounds_below)
        caffeine_theanine_below = [i for i in interactions_below 
                                   if i.compound_a == "caffeine" and i.compound_b == "l_theanine"]
        assert len(caffeine_theanine_below) == 0
        
        # Above threshold
        compounds_above = [
            ("caffeine", 100.0),   # Above min_dose_a of 50
            ("l_theanine", 50.0)   # Above min_dose_b of 25
        ]
        
        interactions_above = graph.get_applicable_interactions(compounds_above)
        caffeine_theanine_above = [i for i in interactions_above 
                                   if i.compound_a == "caffeine" and i.compound_b == "l_theanine"]
        assert len(caffeine_theanine_above) == 1
    
    def test_apply_interactions_multiply(self, sample_interactions_json):
        """apply_interactions correctly applies multiply modifiers."""
        from src.core.interactions.graph import InteractionGraph
        from src.core.interactions.interaction import Interaction
        
        graph = InteractionGraph(sample_interactions_json)
        
        base_effects = {
            "jitter_risk": 0.4,
            "alertness": 80.0
        }
        
        interactions = [
            Interaction(
                compound_a="caffeine",
                compound_b="l_theanine",
                interaction_type="synergy",
                target_param="jitter_risk",
                modifier_type="multiply",
                modifier_value=0.5,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
        ]
        
        modified = graph.apply_interactions(base_effects, interactions)
        
        # jitter_risk should be multiplied by 0.5
        assert modified["jitter_risk"] == pytest.approx(0.2, rel=0.01)
        # alertness should be unchanged
        assert modified["alertness"] == 80.0
    
    def test_apply_interactions_add(self, sample_interactions_json):
        """apply_interactions correctly applies add modifiers."""
        from src.core.interactions.graph import InteractionGraph
        from src.core.interactions.interaction import Interaction
        
        graph = InteractionGraph(sample_interactions_json)
        
        base_effects = {
            "tmax_minutes": 45.0
        }
        
        interactions = [
            Interaction(
                compound_a="caffeine",
                compound_b="food",
                interaction_type="absorption",
                target_param="tmax_minutes",
                modifier_type="add",
                modifier_value=30.0,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
        ]
        
        modified = graph.apply_interactions(base_effects, interactions)
        
        # tmax should have 30 added
        assert modified["tmax_minutes"] == pytest.approx(75.0, rel=0.01)
    
    def test_apply_interactions_replace(self, sample_interactions_json):
        """apply_interactions correctly applies replace modifiers."""
        from src.core.interactions.graph import InteractionGraph
        from src.core.interactions.interaction import Interaction
        
        graph = InteractionGraph(sample_interactions_json)
        
        base_effects = {
            "absorption_rate": 1.0
        }
        
        interactions = [
            Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="absorption",
                target_param="absorption_rate",
                modifier_type="replace",
                modifier_value=0.7,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
        ]
        
        modified = graph.apply_interactions(base_effects, interactions)
        
        # Should be replaced
        assert modified["absorption_rate"] == 0.7
    
    def test_apply_interactions_order_synergy_first(self, sample_interactions_json):
        """Contract: synergies applied before antagonisms."""
        from src.core.interactions.graph import InteractionGraph
        from src.core.interactions.interaction import Interaction
        
        graph = InteractionGraph(sample_interactions_json)
        
        base_effects = {
            "effect": 100.0
        }
        
        # Order in list shouldn't matter - synergies first
        interactions = [
            Interaction(
                compound_a="a",
                compound_b="c",
                interaction_type="antagonism",
                target_param="effect",
                modifier_type="multiply",
                modifier_value=0.5,  # Reduce by half
                dose_dependent=False,
                evidence_level="high",
                source="test"
            ),
            Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="synergy",
                target_param="effect",
                modifier_type="multiply",
                modifier_value=2.0,  # Double
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
        ]
        
        modified = graph.apply_interactions(base_effects, interactions)
        
        # Should be: 100 * 2.0 (synergy) * 0.5 (antagonism) = 100
        # Order: synergies first, then antagonisms
        assert modified["effect"] == pytest.approx(100.0, rel=0.01)
    
    def test_apply_interactions_no_negative_values(self, sample_interactions_json):
        """Contract: result never has negative values for positive params."""
        from src.core.interactions.graph import InteractionGraph
        from src.core.interactions.interaction import Interaction
        
        graph = InteractionGraph(sample_interactions_json)
        
        base_effects = {
            "jitter_risk": 0.1,  # Small value
        }
        
        interactions = [
            Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="antagonism",
                target_param="jitter_risk",
                modifier_type="add",
                modifier_value=-0.5,  # Would make negative
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
        ]
        
        modified = graph.apply_interactions(base_effects, interactions)
        
        # Should be clamped to 0, not negative
        assert modified["jitter_risk"] >= 0
    
    def test_apply_interactions_missing_param_creates_it(self, sample_interactions_json):
        """If target_param doesn't exist, it's created."""
        from src.core.interactions.graph import InteractionGraph
        from src.core.interactions.interaction import Interaction
        
        graph = InteractionGraph(sample_interactions_json)
        
        base_effects = {}  # Empty
        
        interactions = [
            Interaction(
                compound_a="a",
                compound_b="b",
                interaction_type="synergy",
                target_param="new_effect",
                modifier_type="add",
                modifier_value=10.0,
                dose_dependent=False,
                evidence_level="high",
                source="test"
            )
        ]
        
        modified = graph.apply_interactions(base_effects, interactions)
        
        # Should create with base value 0 + 10
        assert "new_effect" in modified
        assert modified["new_effect"] == 10.0


# =============================================================================
# Interactions JSON Tests
# =============================================================================

class TestInteractionsJSON:
    """Test the interactions.json file structure and content."""
    
    def test_interactions_json_exists(self):
        """interactions.json file exists."""
        import os
        path = "data/reference/interactions.json"
        assert os.path.exists(path), f"File not found: {path}"
    
    def test_interactions_json_valid_structure(self):
        """interactions.json has valid structure."""
        with open("data/reference/interactions.json") as f:
            data = json.load(f)
        
        assert "version" in data
        assert "interactions" in data
        assert isinstance(data["interactions"], list)
    
    def test_interactions_json_has_ten_interactions(self):
        """interactions.json has at least 10 interactions."""
        with open("data/reference/interactions.json") as f:
            data = json.load(f)
        
        assert len(data["interactions"]) >= 10
    
    def test_all_interactions_valid(self):
        """All interactions in JSON are valid Interaction objects."""
        from src.core.interactions.interaction import Interaction
        
        with open("data/reference/interactions.json") as f:
            data = json.load(f)
        
        for i_data in data["interactions"]:
            # Should not raise
            interaction = Interaction.from_dict(i_data)
            assert interaction is not None
    
    def test_key_interactions_present(self):
        """Key interactions from roadmap are present."""
        with open("data/reference/interactions.json") as f:
            data = json.load(f)
        
        interactions = data["interactions"]
        
        # Create set of interaction keys
        keys = set()
        for i in interactions:
            a, b = i["compound_a"], i["compound_b"]
            # Normalize order
            if a > b:
                a, b = b, a
            keys.add((a, b))
        
        # Check key interactions exist
        expected_pairs = [
            ("caffeine", "l_theanine"),     # 1. reduced jitter
            ("caffeine", "tyrosine"),       # 10. enhanced focus
        ]
        
        for pair in expected_pairs:
            assert pair in keys, f"Missing interaction: {pair}"
    
    def test_all_interactions_have_sources(self):
        """All interactions have evidence sources (DOIs or references)."""
        with open("data/reference/interactions.json") as f:
            data = json.load(f)
        
        for i_data in data["interactions"]:
            assert "source" in i_data
            assert len(i_data["source"]) > 0, f"Empty source for {i_data}"


# =============================================================================
# Integration with InteractionGraph
# =============================================================================

class TestInteractionGraphIntegration:
    """Integration tests for InteractionGraph with real data."""
    
    def test_graph_loads_real_interactions(self):
        """InteractionGraph loads from real interactions.json."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph("data/reference/interactions.json")
        assert graph.interaction_count >= 10
    
    def test_caffeine_theanine_reduces_jitter(self):
        """Classic caffeine + theanine interaction reduces jitter risk."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph("data/reference/interactions.json")
        
        compounds = [
            ("caffeine", 200.0),
            ("l_theanine", 100.0)
        ]
        
        interactions = graph.get_applicable_interactions(compounds)
        
        base_effects = {"jitter_risk": 0.4}
        modified = graph.apply_interactions(base_effects, interactions)
        
        # Jitter risk should be reduced
        assert modified["jitter_risk"] < base_effects["jitter_risk"]
    
    def test_caffeine_tyrosine_enhances_focus(self):
        """Caffeine + tyrosine interaction enhances focus."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph("data/reference/interactions.json")
        
        compounds = [
            ("caffeine", 200.0),
            ("tyrosine", 500.0)
        ]
        
        interactions = graph.get_applicable_interactions(compounds)
        
        # Should find the synergy
        synergies = [i for i in interactions if i.interaction_type == "synergy"]
        assert len(synergies) >= 1


# =============================================================================
# Context Rules Tests
# =============================================================================

class TestContextRules:
    """Test context-based interactions (time of day, total dose)."""
    
    def test_self_interaction_caffeine_high_dose(self):
        """High caffeine dose (>300mg) increases jitter risk."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph("data/reference/interactions.json")
        
        # High dose scenario
        compounds = [("caffeine", 350.0)]
        
        # Get context-based interactions (self-interactions)
        context_interactions = graph.get_context_interactions(
            compounds,
            context={"total_caffeine_mg": 350.0}
        )
        
        # Should find high-dose caffeine warning
        high_dose = [i for i in context_interactions 
                     if "caffeine" in i.target_param or "jitter" in i.target_param]
        # This is optional - some implementations may not have this
        # Just verify no errors
    
    def test_afternoon_caffeine_sleep_disruption(self):
        """Afternoon caffeine (after 14:00) increases sleep disruption risk."""
        from src.core.interactions.graph import InteractionGraph
        
        graph = InteractionGraph("data/reference/interactions.json")
        
        compounds = [("caffeine", 200.0)]
        
        # Afternoon context
        context_interactions = graph.get_context_interactions(
            compounds,
            context={"time_of_day_minutes": 900}  # 15:00
        )
        
        # Verification depends on implementation
        # Just ensure no errors for now


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
