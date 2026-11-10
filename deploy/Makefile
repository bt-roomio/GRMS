# =============================================================================
# roomio GRMS — Makefile
# =============================================================================
# Usage:
#   make up-infra              # bring up only DB, Redis, RabbitMQ
#   make up-app                # infra + Django + Celery
#   make up-all                # everything, including proxy and frontend
#   make up-all ENV=prod       # everything in production mode (resource limits)
#   make down                  # stop everything
#   make logs s=backend        # logs of a specific service
#   make shell s=backend       # exec bash into the container
#   make deploy                # git pull + docker pull + restart
#
#   In production you can add ENV=prod to .bashrc
#
# Node-RED (multi-tenant):
#   make nodered-up-nines      # bring up tenant "nines"
#   make nodered-up-all        # bring up all tenants from NODERED_TENANTS
#   make nodered-logs-nines    # tenant logs
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

# Service groups
INFRA_SVCS   = postgres pgbouncer redis redis-broker rabbitmq
APP_SVCS     = backend celery-critical celery-default celery-realtime celery-low celery-beat celery-flower mq-async mews-websocket pms-handler
IOT_SVCS     = mqtt
FRONT_SVCS   = frontend
PROXY_SVCS   = proxy letsencrypt
ALL_SVCS     = $(INFRA_SVCS) $(APP_SVCS) $(IOT_SVCS) $(FRONT_SVCS) $(PROXY_SVCS)

# Node-RED multi-tenant
NODERED         = docker compose -f docker-compose.nodered.yml
# By default: every .env.nodered.<name> alongside (including ones created automatically on tenant creation)
NODERED_TENANTS ?= $(patsubst .env.nodered.%,%,$(filter-out .env.nodered.example %.removed,$(wildcard .env.nodered.*)))

PS_FORMAT = table {{.Image}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}

.PHONY: help up-infra up-app up-iot up-front up-proxy up-all \
        down down-v down-infra down-app down-iot down-front down-proxy down-nodered \
        restart logs shell ps deploy deploy-backend deploy-frontend \
        down down-v restart logs shell ps deploy deploy-backend deploy-frontend \
        migrate collectstatic \
        nodered-up-all nodered-down-all nodered-pull-all nodered-restart-all nodered-ps-all

# --- Help ---

help:
	@echo ""
	@echo "  roomio GRMS — service management"
	@echo ""
	@echo "  Start:"
	@echo "    make up-infra              Infrastructure (postgres, redis, rabbitmq)"
	@echo "    make up-app                Infra + Django + Celery"
	@echo "    make up-iot                Add MQTT"
	@echo "    make up-front              Add Frontend"
	@echo "    make up-proxy              Add Proxy + SSL"
	@echo "    make up-all                Everything (without Node-RED)"
	@echo "    make up-all ENV=prod       Everything in production mode (resource limits)"
	@echo ""
	@echo "  Deploy:"
	@echo "    make deploy                git pull + docker pull + restart app"
	@echo "    make deploy-backend        Update backend + celery only"
	@echo "    make deploy-frontend       Update frontend only"
	@echo ""
	@echo "  Manage:"
	@echo "    make down                  Stop all services"
	@echo "    make down-infra            Stop infrastructure"
	@echo "    make down-app              Stop backend + celery"
	@echo "    make down-iot              Stop MQTT"
	@echo "    make down-front            Stop Frontend"
	@echo "    make down-proxy            Stop Proxy + SSL"
	@echo "    make down-nodered          Stop Node-RED"
	@echo "    make restart s=backend     Restart a service"
	@echo "    make logs s=backend        Service logs (Ctrl+C to exit)"
	@echo "    make shell s=backend       Bash into the container"
	@echo "    make ps                    Status of all containers"
	@echo ""
	@echo "  Django:"
	@echo "    make migrate               Run migrations"
	@echo "    make collectstatic         Collect static files"
	@echo ""
	@echo "  Node-RED (multi-tenant):"
	@echo "    make nodered-up-<name>     Start a tenant  (needs .env.nodered.<name>)"
	@echo "    make nodered-down-<name>   Stop a tenant"
	@echo "    make nodered-restart-<name>  Restart a tenant"
	@echo "    make nodered-logs-<name>   Tenant logs"
	@echo "    make nodered-pull-<name>   Update a tenant's image"
	@echo "    make nodered-up-all        Start all  (NODERED_TENANTS=$(NODERED_TENANTS))"
	@echo "    make nodered-down-all      Stop all"
	@echo "    make nodered-pull-all      Update all images"
	@echo "    make nodered-ps-<name>     Tenant status"
	@echo "    make nodered-ps-all        Status of all tenants"
	@echo ""

# --- Start by level ---

up-infra:
	$(COMPOSE) up -d  $(INFRA_SVCS)

up-app:
	$(COMPOSE) up -d  $(INFRA_SVCS) $(APP_SVCS)

up-iot:
	$(COMPOSE) up -d  $(INFRA_SVCS) $(APP_SVCS) $(IOT_SVCS)

up-front:
	$(COMPOSE) up -d  $(INFRA_SVCS) $(APP_SVCS) $(FRONT_SVCS)

up-proxy:
	$(COMPOSE) up -d  $(PROXY_SVCS)

up-all:
	$(COMPOSE) up -d $(ALL_SVCS)

up:
ifndef s
	$(error Specify a service: make restart s=backend)
endif
	$(COMPOSE) up -d --no-deps $(s)


# --- Stop ---

down:
	$(COMPOSE) down

down-v:  ## Stop and remove volumes (CAUTION: deletes data!)
	$(COMPOSE) down -v

down-infra:
	$(COMPOSE) down $(INFRA_SVCS)

down-app:
	$(COMPOSE) down $(APP_SVCS)

down-iot:
	$(COMPOSE) down $(IOT_SVCS)

down-front:
	$(COMPOSE) down $(FRONT_SVCS)

down-proxy:
	$(COMPOSE) down $(PROXY_SVCS)

down-nodered:
	$(COMPOSE) down $(NODERED_SVCS)

# --- Service management ---

restart:
ifndef s
	$(error Specify a service: make restart s=backend)
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
	$(error Specify a service: make shell s=backend)
endif
	$(COMPOSE) exec $(s) bash

ps:
	$(COMPOSE) ps --format "$(PS_FORMAT)"

# --- Django ---

migrate:
	$(COMPOSE) exec backend python manage.py migrate

collectstatic:
	$(COMPOSE) exec backend python manage.py collectstatic --noinput

# --- Deploy ---

update-backend:
	$(COMPOSE) up -d --no-deps $(APP_SVCS)

deploy-backend:
	$(COMPOSE) pull $(APP_SVCS)
	$(COMPOSE) up -d --no-deps $(APP_SVCS)

deploy-frontend:
	$(COMPOSE) pull $(FRONT_SVCS)
	$(COMPOSE) up -d --no-deps $(FRONT_SVCS)

# --- Node-RED (multi-tenant) ---

nodered-up-%:
	$(NODERED) --project-name nodered-$* --env-file .env.nodered.$* up -d

nodered-down-%:
	$(NODERED) --project-name nodered-$* --env-file .env.nodered.$* down

nodered-restart-%:
	$(NODERED) --project-name nodered-$* --env-file .env.nodered.$* restart

nodered-logs-%:
	$(NODERED) --project-name nodered-$* --env-file .env.nodered.$* logs -f --tail=100

nodered-pull-%:
	$(NODERED) --project-name nodered-$* --env-file .env.nodered.$* pull

nodered-ps-%:
	$(NODERED) --project-name nodered-$* --env-file .env.nodered.$* ps --format "$(PS_FORMAT)"

nodered-up-all:      $(addprefix nodered-up-,      $(NODERED_TENANTS))
nodered-down-all:    $(addprefix nodered-down-,    $(NODERED_TENANTS))
nodered-pull-all:    $(addprefix nodered-pull-,    $(NODERED_TENANTS))
nodered-restart-all: $(addprefix nodered-restart-, $(NODERED_TENANTS))
nodered-ps-all:      $(addprefix nodered-ps-,      $(NODERED_TENANTS))
