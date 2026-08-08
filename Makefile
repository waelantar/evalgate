.PHONY: bootstrap check db-up db-down api web

bootstrap:
	./scripts/bootstrap.sh

check:
	./scripts/check.sh

db-up:
	docker compose up -d db

db-down:
	docker compose down

api:
	uv run --python 3.13.15 --project apps/api --locked evalgate-api

web:
	npm --prefix apps/web run dev
