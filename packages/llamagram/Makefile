.PHONY: test lint format format-check typecheck lint-check

all: test lint format typecheck

test:
	$(info ****************** running tests ******************)
	rm -rf .env && uv run pytest tests/

lint-check:
	$(info ****************** linting ******************)
	uv run pre-commit run -a
	uv run ruff check

lint:
	$(info ****************** linting ******************)
	uv run pre-commit run -a
	uv run ruff check --fix

format:
	$(info ****************** formatting ******************)
	uv run ruff format

format-check:
	$(info ****************** checking formatting ******************)
	uv run ruff format --check

typecheck:
	$(info ****************** type checking ******************)
	uv run ty check src/llamagram/

build:
	$(info ****************** building ******************)
	uv build
