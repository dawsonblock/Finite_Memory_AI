.PHONY: help install install-dev test lint format type-check clean all

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package
	pip3 install -e .

install-dev:  ## Install package with development dependencies
	pip3 install -e ".[dev]"

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ -v --cov=finite_memory_llm --cov-report=html --cov-report=term

lint:  ## Run linter (ruff)
	ruff check finite_memory_llm/ examples/ tests/ benchmarks/

lint-fix:  ## Run linter and fix issues
	ruff check --fix finite_memory_llm/ examples/ tests/ benchmarks/

format:  ## Format code with black
	black finite_memory_llm/ examples/ tests/ benchmarks/

format-check:  ## Check formatting without changes
	black --check finite_memory_llm/ examples/ tests/ benchmarks/

type-check:  ## Run type checker (mypy)
	mypy finite_memory_llm/

all-checks: format-check lint type-check test  ## Run all quality checks

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/

build:  ## Build distribution packages
	python3 -m build

publish-test:  ## Publish to TestPyPI
	python3 -m twine upload --repository testpypi dist/*

publish:  ## Publish to PyPI
	python3 -m twine upload dist/*

