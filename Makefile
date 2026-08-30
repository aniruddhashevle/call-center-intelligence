.PHONY: install test test-unit test-integration test-all lint format check run clean clean-cache reset-db reset db-info db-tables

install:
	uv sync --dev
	pre-commit install

test:
	uv run pytest tests/unit tests/security -v

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-all:
	uv run pytest tests/ -v

lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest tests/ -q

run:
	uv run python app.py

clean-cache:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +

clean:
	$(MAKE) clean-cache

reset-db:
	rm -f data/call_center.db

db-info:
	sqlite3 data/call_center.db ".databases"

db-tables:
	sqlite3 data/call_center.db ".tables"

reset:
	$(MAKE) clean-cache
	$(MAKE) reset-db
