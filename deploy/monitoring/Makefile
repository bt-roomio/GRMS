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
	@echo "  roomio GRMS — стек мониторинга"
	@echo ""
	@echo "  Запуск:"
	@echo "    make up                    Поднять все сервисы (dev)"
	@echo "    make up ENV=prod           Поднять в продакшн-режиме (лимиты ресурсов)"
	@echo "    make down                  Остановить все сервисы"
	@echo "    make down-v                Остановить и удалить volumes (ОСТОРОЖНО!)"
	@echo ""
	@echo "  Деплой:"
	@echo "    make deploy                git pull + docker pull + restart"
	@echo "    make deploy ENV=prod       Деплой в продакшн-режиме"
	@echo ""
	@echo "  Управление:"
	@echo "    make restart s=grafana     Перезапустить сервис"
	@echo "    make logs s=prometheus     Логи сервиса (Ctrl+C для выхода)"
	@echo "    make shell s=grafana       sh в контейнер"
	@echo "    make ps                    Статус всех контейнеров"
	@echo "    make pull                  Обновить все образы"
	@echo ""
	@echo "  Prometheus:"
	@echo "    make reload                Перечитать конфиг без рестарта"
	@echo ""
	@echo "  Первый запуск:"
	@echo "    make init                  Создать .env из env.example"
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
	$(error Укажи сервис: make restart s=grafana)
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
	$(error Укажи сервис: make shell s=prometheus)
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
	@echo "Деплой завершён: $$(git log -1 --oneline)"

# --- First run ---

init:
	@if [ -f .env ]; then \
		echo ".env уже существует, пропускаем"; \
	else \
		cp env.example .env; \
		echo "Создан .env из env.example — заполни переменные перед запуском"; \
	fi
	@if [ ! -f targets/blackbox-https.yml ]; then \
		cp targets/blackbox-https.example.yml targets/blackbox-https.yml; \
		echo "Создан targets/blackbox-https.yml — добавь свои домены"; \
	fi
