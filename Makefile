# YomiToku-Client Makefile

.PHONY: help install format test lint build clean pre-commit setup-dev

# Default target
help:
	@echo "YomiToku-Client Development Tools"
	@echo ""
	@echo "Available commands:"
	@echo "  setup-dev     - Set up development environment"
	@echo "  install       - Install package"
	@echo "  format        - Format code"
	@echo "  test          - Run tests"
	@echo "  lint          - Code quality check"
	@echo "  build         - Build package"
	@echo "  clean         - Clean build files"
	@echo "  pre-commit    - Install pre-commit hooks"
	@echo "  check         - Run all checks"
	@echo ""

# Set up development environment
setup-dev:
	@echo "🔧 Setting up development environment..."
	pip install -e .
	pip install -e ".[dev]"
	pip install pre-commit
	pre-commit install
	@echo "✅ Development environment setup complete"

# Install package
install:
	@echo "📦 Installing package..."
	pip install -e .
	@echo "✅ Installation complete"

# Format code
format:
	@echo "🎨 Formatting code..."
	python scripts/format_code.py
	@echo "✅ Formatting complete"

# Run tests
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v --cov=src --cov-report=term-missing
	@echo "✅ Tests complete"

# Code quality check
lint:
	@echo "🔍 Code quality check..."
	python -m black --check src/ tests/ scripts/
	python -m isort --check-only src/ tests/ scripts/
	python -m flake8 src/ tests/ scripts/
	python -m mypy src/
	@echo "✅ Code quality check complete"

# Build package
build:
	@echo "🏗️  Building package..."
	python -m build
	python -m twine check dist/*
	@echo "✅ Build complete"

# Clean build files
clean:
	@echo "🧹 Cleaning build files..."
	rm -rf build/
	rm -rf dist/
	rm -rf src/*.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	@echo "✅ Clean complete"

# Install pre-commit hooks
pre-commit:
	@echo "🪝 Installing pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Pre-commit hooks installation complete"

# Run all checks
check:
	@echo "🔍 Running all checks..."
	python scripts/test_local.py
	@echo "✅ All checks complete"

# Quick development cycle
dev: format test
	@echo "🚀 Development cycle complete"
