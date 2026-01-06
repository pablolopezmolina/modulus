"""
MODULUS - Dependency Rules Tests
Version: 3.0

These tests enforce the architectural rules defined in ARCHITECTURE.md:
- core/ must NOT import from api/ or reporting/
- models/ must NOT import from simulation/

If these tests fail, the code change violates the architecture.
DO NOT modify these tests to make them pass - fix the violating code instead.
"""

import pytest
import ast
import os
from pathlib import Path
from typing import Set, List, Tuple


def get_project_root() -> Path:
    """Get the project root directory."""
    # Start from this test file and go up
    current = Path(__file__).resolve()
    # Go up until we find 'src' directory
    while current.parent != current:
        if (current / "src").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (directory containing 'src')")


def get_imports_from_file(filepath: Path) -> Set[str]:
    """
    Extract all import statements from a Python file.
    
    Returns a set of module names that are imported.
    """
    imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return imports
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Handle relative imports
                if node.level > 0:
                    # Relative import like "from ..api import"
                    # We need to resolve this based on the file location
                    imports.add(f"relative:{node.module}")
                else:
                    imports.add(node.module.split('.')[0])
    
    return imports


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory recursively."""
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


def check_forbidden_imports(
    source_dir: Path,
    forbidden_patterns: List[str]
) -> List[Tuple[Path, str]]:
    """
    Check if any files in source_dir import from forbidden patterns.
    
    Returns list of (filepath, forbidden_import) tuples.
    """
    violations = []
    
    for filepath in find_python_files(source_dir):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue
        
        # Check for import patterns in the raw content
        # This catches both "import api" and "from api import"
        for pattern in forbidden_patterns:
            # Check various import forms
            patterns_to_check = [
                f"import {pattern}",
                f"from {pattern}",
                f"from .{pattern}",
                f"from ..{pattern}",
                f"from ...{pattern}",
            ]
            for p in patterns_to_check:
                if p in content:
                    violations.append((filepath, pattern))
                    break
    
    return violations


class TestDependencyRules:
    """Tests that verify architectural dependency rules are not violated."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return get_project_root()
    
    def test_core_does_not_import_api(self, project_root):
        """
        RULE: core/ must NOT import from api/
        
        Reason: core/ is the business logic layer.
        api/ is the presentation layer that depends on core/, not vice versa.
        """
        core_dir = project_root / "src" / "core"
        if not core_dir.exists():
            pytest.skip("src/core directory not found")
        
        violations = check_forbidden_imports(core_dir, ["api"])
        
        assert len(violations) == 0, (
            f"ARCHITECTURE VIOLATION: core/ imports from api/\n"
            f"Violations found:\n" +
            "\n".join(f"  {filepath}: imports '{imp}'" for filepath, imp in violations)
        )
    
    def test_core_does_not_import_reporting(self, project_root):
        """
        RULE: core/ must NOT import from reporting/
        
        Reason: core/ contains the simulation engine.
        reporting/ is for output generation and depends on core/, not vice versa.
        """
        core_dir = project_root / "src" / "core"
        if not core_dir.exists():
            pytest.skip("src/core directory not found")
        
        violations = check_forbidden_imports(core_dir, ["reporting"])
        
        assert len(violations) == 0, (
            f"ARCHITECTURE VIOLATION: core/ imports from reporting/\n"
            f"Violations found:\n" +
            "\n".join(f"  {filepath}: imports '{imp}'" for filepath, imp in violations)
        )
    
    def test_models_does_not_import_simulation(self, project_root):
        """
        RULE: models/ must NOT import from simulation/
        
        Reason: models/ contains individual physiological models.
        simulation/ orchestrates models but models should be independent.
        """
        models_dir = project_root / "src" / "core" / "models"
        if not models_dir.exists():
            pytest.skip("src/core/models directory not found")
        
        violations = check_forbidden_imports(models_dir, ["simulation"])
        
        assert len(violations) == 0, (
            f"ARCHITECTURE VIOLATION: models/ imports from simulation/\n"
            f"Violations found:\n" +
            "\n".join(f"  {filepath}: imports '{imp}'" for filepath, imp in violations)
        )
    
    def test_contracts_has_no_dependencies_on_implementation(self, project_root):
        """
        RULE: contracts/ should only depend on standard library + pydantic
        
        Reason: Contracts define interfaces and should be independent of implementation.
        """
        contracts_dir = project_root / "src" / "core" / "contracts"
        if not contracts_dir.exists():
            pytest.skip("src/core/contracts directory not found")
        
        # These are implementation modules that contracts should NOT import
        forbidden = ["models", "population", "simulation", "timeline", "compounds"]
        violations = check_forbidden_imports(contracts_dir, forbidden)
        
        assert len(violations) == 0, (
            f"ARCHITECTURE VIOLATION: contracts/ imports implementation modules\n"
            f"Violations found:\n" +
            "\n".join(f"  {filepath}: imports '{imp}'" for filepath, imp in violations)
        )


class TestModuleStructure:
    """Tests that verify the expected module structure exists."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return get_project_root()
    
    def test_core_directory_exists(self, project_root):
        """src/core/ directory should exist."""
        assert (project_root / "src" / "core").exists()
    
    def test_contracts_directory_exists(self, project_root):
        """src/core/contracts/ directory should exist."""
        assert (project_root / "src" / "core" / "contracts").exists()
    
    def test_models_directory_exists(self, project_root):
        """src/core/models/ directory should exist."""
        assert (project_root / "src" / "core" / "models").exists()
    
    def test_api_directory_exists(self, project_root):
        """src/api/ directory should exist."""
        assert (project_root / "src" / "api").exists()


class TestImportSafety:
    """Tests that verify imports don't cause circular dependencies."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return get_project_root()
    
    def test_contracts_can_be_imported(self, project_root):
        """contracts module should be importable without errors."""
        import sys
        src_path = str(project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        # This should not raise any import errors
        from core.contracts import Event, PhysiologicalState, SimulationResult
        
        assert Event is not None
        assert PhysiologicalState is not None
        assert SimulationResult is not None
    
    def test_no_circular_imports_in_core(self, project_root):
        """All core modules should be importable without circular import errors."""
        import sys
        src_path = str(project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        # These should all import without circular dependency issues
        import core
        import core.contracts
        import core.models
        import core.population
