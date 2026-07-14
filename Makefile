.PHONY: help install sync test cov lint format typecheck build clean

help:
	@echo "injector-autowired — development commands"
	@echo ""
	@echo "  make install    Create venv and install in editable mode with dev extras"
	@echo "  make sync        Sync dependencies from pyproject.toml"
	@echo "  make test        Run the test suite"
	@echo "  make cov         Run tests with coverage report"
	@echo "  make lint        Run ruff"
	@echo "  make format      Auto-format with ruff"
	@echo "  make typecheck   Run mypy"
	@echo "  make build       Build wheel + sdist"
	@echo "  make clean       Remove build artifacts and caches"

install:
	uv sync --all-extras

sync:
	uv sync --all-extras

test:
	uv run pytest

cov:
	uv run pytest --cov=src/injector_autowired --cov-report=term-missing --cov-report=xml

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy src

build:
	uv build

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
