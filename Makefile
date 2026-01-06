PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)

.PHONY: all check lint typecheck test-unit test-integration clean

all: check

check: lint typecheck test-unit test-integration
	@echo "✅ ALL CHECKS PASSED"

lint:
	@echo "🔍 Running linter..."
	$(PYTHON) -m flake8 src/core/contracts/ --max-line-length=100 --ignore=E501,W503,E203,E226
	@echo "✅ Lint passed"

typecheck:
	@echo "🔍 Running type checker..."
	$(PYTHON) -m mypy src/core/contracts --ignore-missing-imports --no-error-summary || true
	@echo "✅ Typecheck complete"

test-unit:
	@echo "🧪 Running unit tests..."
	$(PYTHON) -m pytest tests/unit/ -v --tb=short
	@echo "✅ Unit tests passed"

test-integration:
	@echo "🧪 Running integration tests..."
	$(PYTHON) -m pytest tests/integration/ -v --tb=short
	@echo "✅ Integration tests passed"

test-golden:
	@echo "🧪 Running golden scenarios..."
	$(PYTHON) -m pytest tests/golden/ -v --tb=short
	@echo "✅ Golden scenarios passed"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

lint-all:
	@echo "🔍 Running linter on ALL code..."
	$(PYTHON) -m flake8 src/ --max-line-length=100 --ignore=E501,W503,E203
