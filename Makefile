# Makefile — point d'entree unique du projet.
# Une cible n'existe que si elle fait quelque chose : les commandes du backlog
# (make up, make fixture, make bench…) arrivent avec la carte qui les livre.

.DEFAULT_GOAL := help

UV  := uv
RUN := uv run

.PHONY: help
help: ## Liste les cibles disponibles
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Installe les dependances et les hooks de pre-commit
	$(UV) sync --all-groups
	$(RUN) pre-commit install --install-hooks

.PHONY: lint
lint: ## Passe tous les linters en lecture seule (ne modifie rien)
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	$(RUN) mypy
	# no-commit-to-branch garde le commit, pas le lint : il echouerait sur main.
	SKIP=no-commit-to-branch $(RUN) pre-commit run --all-files --show-diff-on-failure

.PHONY: format
format: ## Applique les corrections automatiques
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

.PHONY: test
test: ## Joue la suite de tests
	$(RUN) pytest

.PHONY: issues
issues: ## Publie le backlog sur GitHub Issues (APPLY=1 pour creer reellement)
	$(RUN) python scripts/backlog_to_issues.py $(if $(APPLY),--apply,)

.PHONY: ci
ci: lint test ## Ce que la CI execute
