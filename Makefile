# Makefile — the project's single entry point.
# A target exists only once it does something: the backlog commands
# (make up, make fixture, make bench…) land with the story that delivers them.

.DEFAULT_GOAL := help

UV                := uv
RUN               := uv run
COMPOSE           := docker compose
# sql/ is mounted at /sql inside the container: a repo path becomes a
# container path by prefixing it with a slash.
CLICKHOUSE_CLIENT := $(COMPOSE) exec -T clickhouse clickhouse-client

.PHONY: help
help: ## List the available targets
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install dependencies and the pre-commit hooks
	$(UV) sync --all-groups
	$(RUN) pre-commit install --install-hooks

.PHONY: lint
lint: ## Run every linter read-only (changes nothing)
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	$(RUN) mypy
	# no-commit-to-branch guards the commit, not the lint: it would fail on main.
	SKIP=no-commit-to-branch $(RUN) pre-commit run --all-files --show-diff-on-failure

.PHONY: format
format: ## Apply the automatic fixes
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

.PHONY: test
test: ## Run the test suite
	$(RUN) pytest

.env:
	cp .env.example .env

.PHONY: up
up: | .env ## Start ClickHouse + MinIO and apply the DDL (re-runnable without drift)
	$(COMPOSE) up -d --wait
	@$(MAKE) --no-print-directory ddl

.PHONY: ddl
ddl: ## Apply sql/ddl/*.sql idempotently
	@for f in sql/ddl/*.sql; do \
		echo "  ddl   $$f"; \
		$(CLICKHOUSE_CLIENT) --queries-file "/$$f" || exit 1; \
	done

.PHONY: seed
seed: ## Load the deterministic baseline rows into bronze.ads_raw
	@for f in sql/seed/*.sql; do \
		echo "  seed  $$f"; \
		$(CLICKHOUSE_CLIENT) --queries-file "/$$f" || exit 1; \
	done

.PHONY: query
query: ## Run one SQL query against ClickHouse (make query Q="SELECT 1")
	@$(CLICKHOUSE_CLIENT) --query "$(Q)"

.PHONY: down
down: ## Destroy the stack and its volumes; make up rebuilds it identically
	$(COMPOSE) down --volumes --remove-orphans

.PHONY: scenarios
scenarios: ## Replay the executable scenarios in scenarios/
	@scripts/replay-scenarios.sh

.PHONY: issues
issues: ## Publish the backlog to GitHub Issues (APPLY=1 to actually create them)
	$(RUN) python scripts/backlog_to_issues.py $(if $(APPLY),--apply,)

.PHONY: ci
ci: lint test ## What CI runs
