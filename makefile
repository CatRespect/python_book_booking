.PHONY: check lint format db-up db-down migrations migrate run swagger test

# Run ruff check and fix automatically
lint:
	ruff check . --fix
	mypy .

# Run ruff format
format:
	black .

db-up:
	docker compose up -d db

db-down:
	docker compose down

migrations:
	python src/manage.py makemigrations booking

migrate:
	python src/manage.py migrate

run:
	python src/manage.py runserver

swagger:
	python src/manage.py export_openapi_schema --api app.presentation.api.api --output swagger.json --indent 2

test:
	pytest
