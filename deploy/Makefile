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
# Node-RED (multi-tenant):
#   make nodered-up-nines      # поднять тенанта "nines"
#   make nodered-up-all        # поднять всех тенантов из NODERED_TENANTS
#   make nodered-logs-nines    # логи тенанта
# =============================================================================

ENV ?= dev

COMPOSE_BASE = docker compose -f docker-compose.yml
COMPOSE_PROD = $(COMPOSE_BASE) -f docker-compose.prod.yml

ifeq ($(ENV), prod)
  COMPOSE = $(COMPOSE_PROD)
else
	COMPOSE = $(COMPOSE_BASE) -f docker-compose.override.yml
endif

# Все профили для down (нужно перечислить явно)
ALL_PROFILES = --profile infra --profile app --profile iot --profile front --profile proxy --profile nodered

# Node-RED multi-tenant
NODERED         = docker compose -f docker-compose.nodered.yml
NODERED_TENANTS ?= nines map olympic

.PHONY: help up-infra up-app up-iot up-front up-proxy up-nodered up-all \
        down restart logs shell ps pull deploy \
        migrate collectstatic \
        nodered-up-all nodered-down-all nodered-pull-all nodered-restart-all

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
	@echo "    make up-all                Всё вместе"
	@echo "    make up-all ENV=prod       Всё в продакшн-режиме (лимиты ресурсов)"
	@echo ""
	@echo "  Деплой:"
	@echo "    make deploy                git pull + docker pull + restart app"
	@echo "    make deploy-backend        Обновить только backend + celery"
	@echo ""
	@echo "  Управление:"
	@echo "    make down                  Остановить все сервисы"
	@echo "    make restart s=backend     Перезапустить сервис"
	@echo "    make logs s=backend        Логи сервиса (Ctrl+C для выхода)"
	@echo "    make shell s=backend       Bash в контейнер"
	@echo "    make ps                    Статус всех контейнеров"
	@echo "    make pull                  Обновить все образы"
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
	@echo ""

# --- Запуск по уровням ---

up-infra:
	$(COMPOSE) --profile infra up -d

up-app:
	$(COMPOSE) --profile infra --profile app up -d

up-iot:
	$(COMPOSE) --profile infra --profile app --profile iot up -d

up-front:
	$(COMPOSE) --profile infra --profile app --profile front up -d

up-proxy:
	$(COMPOSE) --profile proxy up -d

up-nodered:
	$(COMPOSE) --profile infra --profile app --profile nodered up -d

up-all:
	$(COMPOSE) $(ALL_PROFILES) up -d

# --- Остановка ---

down:
	$(COMPOSE) $(ALL_PROFILES) down

down-v:  ## Остановить и удалить volumes (ОСТОРОЖНО: удалит данные!)
	$(COMPOSE) $(ALL_PROFILES) down -v

# --- Управление сервисами ---

restart:
ifndef s
	$(error Укажи сервис: make restart s=backend)
endif
	$(COMPOSE) $(ALL_PROFILES) restart $(s)

logs:
ifndef s
	$(COMPOSE) $(ALL_PROFILES) logs -f --tail=100
else
	$(COMPOSE) $(ALL_PROFILES) logs -f --tail=100 $(s)
endif

shell:
ifndef s
	$(error Укажи сервис: make shell s=backend)
endif
	$(COMPOSE) $(ALL_PROFILES) exec $(s) bash

ps:
	$(COMPOSE) $(ALL_PROFILES) ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"

pull:
	$(COMPOSE) $(ALL_PROFILES) pull

# --- Django ---

migrate:
	$(COMPOSE) $(ALL_PROFILES) exec backend python manage.py migrate

collectstatic:
	$(COMPOSE) $(ALL_PROFILES) exec backend python manage.py collectstatic --noinput

# --- Деплой ---

deploy:
	git pull
	$(COMPOSE) $(ALL_PROFILES) pull
	$(COMPOSE) --profile infra --profile app up -d --remove-orphans
	@echo "Деплой завершён: $$(git log -1 --oneline)"

deploy-backend:
	git pull
	$(COMPOSE) pull backend
	$(COMPOSE) up -d --no-deps backend celery-critical celery-default celery-low celery-beat mq-async

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

nodered-up-all:      $(addprefix nodered-up-,      $(NODERED_TENANTS))
nodered-down-all:    $(addprefix nodered-down-,    $(NODERED_TENANTS))
nodered-pull-all:    $(addprefix nodered-pull-,    $(NODERED_TENANTS))
nodered-restart-all: $(addprefix nodered-restart-, $(NODERED_TENANTS))

# --- Первый запуск ---

init: up-infra
	@echo "Ожидаем готовности БД..."
	@sleep 5
	$(COMPOSE) $(ALL_PROFILES) exec postgres pg_isready -U $(shell grep POSTGRES_USER .env | cut -d= -f2)
	@echo "Инфраструктура готова. Запусти: make up-app"
