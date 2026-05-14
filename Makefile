PROJECT_NAME = analyse_an
pr = poetry run

.DEFAULT_GOAL := help

##@ Setup project
init: ## Initialize the project
	poetry config virtualenvs.in-project true
	poetry install --no-root
	$(pr) pre-commit install --install-hooks

##@ Local development
run: ## Run the application without Docker
	$(pr) poetry src/__main__.py

lint: ## Run the linter
	$(pr) ruff check --config=pyproject.toml --fix ./src/

format: ## Format the code
	$(pr) ruff format --config=pyproject.toml ./src/

typecheck: ## Run the type checker
	$(pr) mypy --config-file=pyproject.toml --explicit-package-bases ./src/


clean: ## Clean up the project (cache)
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache .pytest_cache


##@ Git
commit: ## Do commit with conventional commit message
	$(pr) cz commit

bump: ## Bump the version and update CHANGELOG.md
	$(pr) cz bump

##@ Documentation
serve: ## Serve the documentation using MkDocs
	$(pr) mkdocs serve

##@ Help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: help run test lint format typecheck dev-logs dev-exec dev-bash dev-build dev-up dev-stop dev-down clean prod-build prod-run