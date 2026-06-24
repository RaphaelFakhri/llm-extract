.PHONY: install lint format typecheck test cov run docker clean

install:
	pip install -e ".[dev]"
	pre-commit install || true

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

typecheck:
	mypy

test:
	pytest

cov:
	pytest --cov=llm_extract --cov-report=term-missing

run:
	llm-extract run --dry-run

docker:
	docker build -t llm-extract:latest .

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov out
	find . -type d -name __pycache__ -exec rm -rf {} +
