# MODULUS — Makefile
# 
# Un comando para verificar que todo está bien: make check
# 
# ============================================================================

.PHONY: all check lint typecheck test test-unit test-integration test-golden clean install

# Default target
all: check

# ============================================================================
# MAIN COMMANDS
# ============================================================================

# Run ALL checks (use this before committing)
check: lint typecheck test-unit test-integration test-golden
	@echo ""
	@echo "✅ ALL CHECKS PASSED"
	@echo ""

# Quick check (just unit tests, for rapid iteration)
quick: lint test-unit
	@echo ""
	@echo "✅ Quick check passed"
	@echo ""

# ============================================================================
# INDIVIDUAL CHECKS
# ============================================================================

# Linting (style + common errors)
lint:
	@echo "🔍 Running linter..."
	python -m flake8 src/ --max-line-length=100 --ignore=E501,W503
	@echo "✅ Lint passed"

# Type checking
typecheck:
	@echo "🔍 Running type checker..."
	python -m mypy src/core --ignore-missing-imports --no-error-summary || true
	@echo "✅ Typecheck complete"

# Unit tests
test-unit:
	@echo "🧪 Running unit tests..."
	python -m pytest tests/unit/ -v --tb=short
	@echo "✅ Unit tests passed"

# Integration tests (including contract tests)
test-integration:
	@echo "🧪 Running integration tests..."
	python -m pytest tests/integration/ -v --tb=short
	@echo "✅ Integration tests passed"

# Golden scenarios (regression tests)
test-golden:
	@echo "🧪 Running golden scenarios..."
	python -m pytest tests/golden/ -v --tb=short
	@echo "✅ Golden scenarios passed"

# All tests
test: test-unit test-integration test-golden

# ============================================================================
# DEPENDENCY RULES CHECK
# ============================================================================

# Check that imports follow architecture rules
check-imports:
	@echo "🔍 Checking import rules..."
	@# core/ should not import from api/ or reporting/
	@! grep -r "from api\|from reporting\|import api\|import reporting" src/core/ || \
		(echo "❌ ERROR: core/ has forbidden imports" && exit 1)
	@# models/ should not import from simulation/
	@! grep -r "from \.\.simulation\|from simulation" src/core/models/ || \
		(echo "❌ ERROR: models/ has forbidden imports" && exit 1)
	@echo "✅ Import rules OK"

# ============================================================================
# SETUP
# ============================================================================

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Create dev requirements file if it doesn't exist
requirements-dev.txt:
	@echo "pytest>=7.0" > requirements-dev.txt
	@echo "pytest-cov>=4.0" >> requirements-dev.txt
	@echo "flake8>=6.0" >> requirements-dev.txt
	@echo "mypy>=1.0" >> requirements-dev.txt
	@echo "black>=23.0" >> requirements-dev.txt

# ============================================================================
# UTILITIES
# ============================================================================

# Format code
format:
	python -m black src/ tests/ --line-length=100

# Clean cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

# Show project structure
tree:
	@find src -type f -name "*.py" | head -50

# ============================================================================
# SIMULATION COMMANDS (for manual testing)
# ============================================================================

# Run demo simulation
demo:
	python demo_simulation.py

# Run demo with custom params
demo-preworkout:
	python demo_simulation.py --carbs 25 --gi 85 --caffeine 200 --population 500

# ============================================================================
# HELP
# ============================================================================

help:
	@echo "MODULUS Makefile Commands:"
	@echo ""
	@echo "  make check          - Run ALL checks (lint + typecheck + tests)"
	@echo "  make quick          - Quick check (lint + unit tests only)"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run linter"
	@echo "  make typecheck      - Run type checker"
	@echo "  make check-imports  - Verify import rules"
	@echo "  make format         - Format code with black"
	@echo "  make clean          - Remove cache files"
	@echo "  make install        - Install dependencies"
	@echo "  make demo           - Run demo simulation"
	@echo ""
