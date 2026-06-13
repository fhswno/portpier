# portpier — common dev commands.
# Run `make` (or `make help`) to see everything available.

.DEFAULT_GOAL := help
.PHONY: help install run version typecheck lint fmt test check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install all deps (runtime + dev)
	uv sync

run: ## Launch portpier
	uv run portpier

version: ## Print the portpier version
	uv run portpier --version

typecheck: ## Run mypy --strict on src/
	uv run mypy --strict src/

lint: ## Run ruff lint on src/
	uv run ruff check src/

fmt: ## Auto-format and auto-fix with ruff
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

test: ## Run the test suite
	@uv run pytest; status=$$?; \
	if [ $$status -eq 5 ]; then echo "→ no tests collected yet (fine at this stage)"; exit 0; fi; \
	exit $$status

check: typecheck lint test ## Run all gates: typecheck + lint + test

clean: ## Remove the venv and all caches
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
