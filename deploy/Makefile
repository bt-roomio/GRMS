# =============================================================================
# roomio GRMS — Makefile
# =============================================================================
# Использование:
#   make up-infra              # поднять только БД, Redis, RabbitMQ
#   make up-app                # инфра + Django + Celery
#   make up-all                # всё, включая proxy и frontend
#   make up-all ENV=prod       # всё в продакшн-режиме (resource limits)
#   make down                  # остановить всё
#   make logs s=backend        # логи конкретного сервиса
#   make shell s=backend       # exec bash в контейнер
#   make deploy                # git pull + docker pull + restart
#
#   На проде можно добавить ENV=prod в .bashrc
#
# Node-RED (multi-tenant):
#   make nodered-up-nines      # поднять тенанта "nines"
#   make nodered-up-all        # поднять всех тенантов из NODERED_TENANTS
#   make nodered-logs-nines    # логи тенанта
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

# Группы сервисов
INFRA_SVCS   = postgres pgbouncer redis redis-broker rabbitmq
APP_SVCS     = backend celery-critical celery-default celery-realtime celery-low celery-beat celery-flower mq-async mews-websocket pms-handler
IOT_SVCS     = mqtt
FRONT_SVCS   = frontend
PROXY_SVCS   = proxy letsencrypt
ALL_SVCS     = $(INFRA_SVCS) $(APP_SVCS) $(IOT_SVCS) $(FRONT_SVCS) $(PROXY_SVCS)

# Node-RED multi-tenant
NODERED         = docker compose -f docker-compose.nodered.yml
NODERED_TENANTS ?= nines map ol fl

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
	@echo "  roomio GRMS — управление сервисами"
	@echo ""
	@echo "  Запуск:"
	@echo "    make up-infra              Инфраструктура (postgres, redis, rabbitmq)"
	@echo "    make up-app                Инфра + Django + Celery"
	@echo "    make up-iot                Добавить MQTT"
	@echo "    make up-front              Добавить Frontend"
	@echo "    make up-proxy              Добавить Proxy + SSL"
	@echo "    make up-all                Всё вместе (без Node-RED)"
	@echo "    make up-all ENV=prod       Всё в продакшн-режиме (лимиты ресурсов)"
	@echo ""
	@echo "  Деплой:"
	@echo "    make deploy                git pull + docker pull + restart app"
	@echo "    make deploy-backend        Обновить только backend + celery"
	@echo "    make deploy-frontend       Обновить только frontend"
	@echo ""
	@echo "  Управление:"
	@echo "    make down                  Остановить все сервисы"
	@echo "    make down-infra            Остановить инфраструктуру"
	@echo "    make down-app              Остановить backend + celery"
	@echo "    make down-iot              Остановить MQTT"
	@echo "    make down-front            Остановить Frontend"
	@echo "    make down-proxy            Остановить Proxy + SSL"
	@echo "    make down-nodered          Остановить Node-RED"
	@echo "    make restart s=backend     Перезапустить сервис"
	@echo "    make logs s=backend        Логи сервиса (Ctrl+C для выхода)"
	@echo "    make shell s=backend       Bash в контейнер"
	@echo "    make ps                    Статус всех контейнеров"
	@echo ""
	@echo "  Django:"
	@echo "    make migrate               Запустить миграции"
	@echo "    make collectstatic         Собрать статику"
	@echo ""
	@echo "  Node-RED (multi-tenant):"
	@echo "    make nodered-up-<name>     Поднять тенанта  (требует .env.nodered.<name>)"
	@echo "    make nodered-down-<name>   Остановить тенанта"
	@echo "    make nodered-restart-<name>  Перезапустить тенанта"
	@echo "    make nodered-logs-<name>   Логи тенанта"
	@echo "    make nodered-pull-<name>   Обновить образ тенанта"
	@echo "    make nodered-up-all        Поднять всех  (NODERED_TENANTS=$(NODERED_TENANTS))"
	@echo "    make nodered-down-all      Остановить всех"
	@echo "    make nodered-pull-all      Обновить образы всех"
	@echo "    make nodered-ps-<name>     Статус тенанта"
	@echo "    make nodered-ps-all        Статус всех тенантов"
	@echo ""

# --- Запуск по уровням ---

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
	$(error Укажи сервис: make restart s=backend)
endif
	$(COMPOSE) up -d --no-deps $(s)


# --- Остановка ---

down:
	$(COMPOSE) down

down-v:  ## Остановить и удалить volumes (ОСТОРОЖНО: удалит данные!)
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

# --- Управление сервисами ---

restart:
ifndef s
	$(error Укажи сервис: make restart s=backend)
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
	$(error Укажи сервис: make shell s=backend)
endif
	$(COMPOSE) exec $(s) bash

ps:
	$(COMPOSE) ps --format "$(PS_FORMAT)"

# --- Django ---

migrate:
	$(COMPOSE) exec backend python manage.py migrate

collectstatic:
	$(COMPOSE) exec backend python manage.py collectstatic --noinput

# --- Деплой ---

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
