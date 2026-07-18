.PHONY: install dev lint type test coverage doctor serve clean

install:
	uv sync

dev:
	uv sync --all-extras

lint:
	uv run ruff check .
	uv run ruff format --check .

lint-fix:
	uv run ruff check --fix .
	uv run ruff format .

type:
	uv run mypy src

test:
	uv run pytest -q

coverage:
	uv run pytest --cov=carpet_designer --cov-report=term-missing

doctor:
	uv run carpet-designer doctor

serve:
	uv run carpet-designer serve

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
	rm -rf htmlcov/

check: lint type test
	@echo "All checks passed."
