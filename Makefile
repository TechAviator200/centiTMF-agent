.PHONY: up down build logs shell-backend shell-db seed reset

up:
	docker compose up --build

up-detach:
	docker compose up --build -d

down:
	docker compose down

down-volumes:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U centitmf -d centitmf

seed:
	docker compose exec backend python scripts/seed.py

reset:
	docker compose down -v
	docker compose up --build

lint-backend:
	docker compose exec backend ruff check app/

format-backend:
	docker compose exec backend ruff format app/
