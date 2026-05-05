DOCKER_DIR := docker
COMPOSE    := docker compose -f $(DOCKER_DIR)/docker-compose.yml
DJANGO     := docker exec -it django

s        ?=
REGISTRY ?= grms
TAG      ?= latest
PLATFORM ?= linux/amd64

.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------

.PHONY: pull
pull: ## Pull latest images
	$(COMPOSE) pull

.PHONY: up
up: ## Start all or specific service (make up s=redis)
	@if [ -z "$(s)" ]; then $(COMPOSE) rm -fsv migrate 2>/dev/null || true; fi
	$(COMPOSE) up -d $(s)

.PHONY: down
down: ## Stop all services
	$(COMPOSE) down

.PHONY: deploy
deploy: ## Full deploy: pull + down + up
	$(COMPOSE) pull
	$(COMPOSE) down
	$(COMPOSE) up -d

.PHONY: restart
restart: ## Restart a service (make restart s=celery)
	$(COMPOSE) restart $(s)

.PHONY: logs
logs: ## Follow service logs (make logs s=backend)
	$(COMPOSE) logs -f $(s)

.PHONY: ps
ps: ## Show container status
	$(COMPOSE) ps

.PHONY: build
build: ## Build multi-arch image (make build REGISTRY=... TAG=...)
	cd backend && docker buildx build --platform $(PLATFORM) -t $(REGISTRY):$(TAG) .

# ---------------------------------------------------------------------------
# Django (inside container)
# ---------------------------------------------------------------------------

.PHONY: migrate
migrate: ## Run migrations
	$(DJANGO) python manage.py migrate

.PHONY: migrations
migrations: ## Create migrations
	$(DJANGO) python manage.py makemigrations

.PHONY: shell
shell: ## Open Django shell
	$(DJANGO) python manage.py shell

.PHONY: bash
bash: ## Open bash inside django container
	$(DJANGO) bash

.PHONY: createsuperuser
createsuperuser: ## Create superuser
	$(DJANGO) python manage.py createsuperuser

.PHONY: create-tenant
create-tenant: ## Create a tenant
	$(DJANGO) python manage.py create_tenant

# ---------------------------------------------------------------------------
# Local backend (without Docker)
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run tests
	cd backend && pytest

.PHONY: test-v
test-v: ## Run tests with verbose output
	cd backend && pytest -v

.PHONY: lint
lint: ## Check code style (ruff)
	cd backend && ruff check .

.PHONY: format
format: ## Format code (black + isort)
	cd backend && black . && isort .

.PHONY: check
check: ## Django system check
	cd backend && ./manage.py check
