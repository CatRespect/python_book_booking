.PHONY: check lint format

# Run ruff check and fix automatically
lint:
	ruff check . --fix
	mypy .

# Run ruff format
format:
	black .