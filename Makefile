# portpier — common dev commands.
# Run `make` (or `make help`) to see everything available.

.DEFAULT_GOAL := help
.PHONY: help install run version smoke typecheck lint fmt test check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install all deps (runtime + dev)
	uv sync

run: ## Launch portpier
	uv run portpier

version: ## Print the portpier version
	uv run portpier --version

smoke: ## Live data-layer check: collect real ports and print the first few
	@uv run python -c "from portpier.data.collector import Collector; from portpier.utils.format import bytes_to_human as b, seconds_to_uptime as up; es = Collector().collect_ports(); print(f'{len(es)} sockets collected'); [print(f':{e.port:<6} {str(e.process_name):<16} {(e.process_type or chr(8212)):<14} {b(e.memory_rss_bytes):>9}  {up(e.uptime_seconds):>8}  {e.state}') for e in es[:10]]"

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
