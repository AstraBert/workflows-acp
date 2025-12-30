.PHONY: test lint format format-check typecheck

all: test lint format typecheck

test:
	$(info ****************** running tests ******************)
	echo "No tests yet"

lint:
	$(info ****************** linting ******************)
	uv run pre-commit run -a
	uv run ruff check

format:
	$(info ****************** formatting ******************)
	uv run ruff format

format-check:
	$(info ****************** checking formatting ******************)
	uv run ruff format --check

typecheck:
	$(info ****************** type checking ******************)
	uv run ty check src/workflows_acp/

build:
	$(info ****************** building ******************)
	uv build