.PHONY: up down test lint format typecheck imports migrations schema server

up:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down

test:
	uv run pytest

lint:
	uv run ruff check backend

format:
	uv run ruff format --check backend

typecheck:
	PYTHONPATH=backend uv run mypy backend

imports:
	PYTHONPATH=backend uv run lint-imports

migrations:
	uv run python backend/manage.py makemigrations --check --dry-run

schema:
	uv run python backend/manage.py spectacular --file /tmp/openapi-schema.yml

server:
	uv run python backend/manage.py runserver 127.0.0.1:8000
