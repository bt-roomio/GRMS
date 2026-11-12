# =============================================================================
# roomio GRMS — monitoring/Makefile
# =============================================================================
# Usage:
#   make up                    # dev (override is applied automatically)
#   make up ENV=prod           # prod (resource limits, no extra ports)
#   make down                  # stop
#   make logs s=grafana        # logs of a specific service
#   make shell s=prometheus    # exec sh into the container
#   make reload                # reload the Prometheus config without a restart
#   make deploy                # git pull + docker pull + restart
# =============================================================================

ENV ?= dev

PLATFORM := $(if $(filter arm64 aarch64,$(shell uname -m)),linux/arm64,linux/amd64)
export DOCKER_DEFAULT_PLATFORM = $(PLATFORM)

COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_PROD = $(COMPOSE_BASE) -f docker-compose.prod.yml

ifeq ($(ENV), prod)
  COMPOSE = $(COMPOSE_PROD)
else
  COMPOSE = $(COMPOSE_BASE) -f docker-compose.override.yml
endif

.PHONY: help up down down-v restart logs shell ps pull deploy reload init

# --- Help ---

help:
	@echo ""
	@echo "  roomio GRMS — monitoring stack"
	@echo ""
	@echo "  Start:"
	@echo "    make up                    Start all services (dev)"
	@echo "    make up ENV=prod           Start in production mode (resource limits)"
	@echo "    make down                  Stop all services"
	@echo "    make down-v                Stop and remove volumes (CAUTION!)"
	@echo ""
	@echo "  Deploy:"
	@echo "    make deploy                git pull + docker pull + restart"
	@echo "    make deploy ENV=prod       Deploy in production mode"
	@echo ""
	@echo "  Manage:"
	@echo "    make restart s=grafana     Restart a service"
	@echo "    make logs s=prometheus     Service logs (Ctrl+C to exit)"
	@echo "    make shell s=grafana       sh into the container"
	@echo "    make ps                    Status of all containers"
	@echo "    make pull                  Update all images"
	@echo ""
	@echo "  Prometheus:"
	@echo "    make reload                Reload the config without a restart"
	@echo ""
	@echo "  First run:"
	@echo "    make init                  Create .env from env.example"
	@echo ""

# --- Start / stop ---

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

down-v:  ## Stop and remove volumes (CAUTION: deletes data!)
	$(COMPOSE) down -v

# --- Service management ---

restart:
ifndef s
	$(error Specify a service: make restart s=grafana)
endif
	$(COMPOSE) restart $(s)

logs:
ifndef s
	$(COMPOSE) logs -f --tail=100
else
	$(COMPOSE) logs -f --tail=100 $(s)
endif

shell:
ifndef s
	$(error Specify a service: make shell s=prometheus)
endif
	$(COMPOSE) exec $(s) sh

ps:
	$(COMPOSE) ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"

pull:
	$(COMPOSE) pull

# --- Prometheus ---

reload:
	curl -s -X POST http://localhost:9090/-/reload && echo "Prometheus config reloaded"

# --- Deploy ---

deploy:
	git pull
	$(COMPOSE) pull
	$(COMPOSE) up -d --remove-orphans
	@echo "Deploy finished: $$(git log -1 --oneline)"

# --- First run ---

init:
	@if [ -f .env ]; then \
		echo ".env already exists, skipping"; \
	else \
		cp env.example .env; \
		echo "Created .env from env.example — fill in the variables before starting"; \
	fi
	@if [ ! -f targets/blackbox-https.yml ]; then \
		cp targets/blackbox-https.example.yml targets/blackbox-https.yml; \
		echo "Created targets/blackbox-https.yml — add your domains"; \
	fi
