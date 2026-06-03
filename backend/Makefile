# =============================================================================
# roomio GRMS — backend Makefile
# =============================================================================
# Использование:
#   make build                         # локальная сборка (текущая платформа)
#   make push                          # сборка + push (TAG=dev)
#   make push TAG=latest PLATFORM=...  # с кастомными параметрами
# =============================================================================

REGISTRY   = registry.gitlab.com/yroomio/grms
TAG       ?= dev
PLATFORM := $(if $(filter arm64 aarch64,$(shell uname -m)),linux/arm64,linux/amd64)
BUILDER    = grms-builder
DOCKERFILE = Dockerfile

export DOCKER_DEFAULT_PLATFORM = $(PLATFORM)

.PHONY: help login buildx-setup build push push-dev push-prod

# --- Help ---

help:
	@echo ""
	@echo "  roomio GRMS — сборка Docker-образа"
	@echo ""
	@echo "  Подготовка:"
	@echo "    make login                 Войти в GitLab Container Registry"
	@echo "    make buildx-setup          Создать buildx-builder (один раз)"
	@echo ""
	@echo "  Сборка:"
	@echo "    make build                 Локальная сборка (текущая платформа, без push)"
	@echo "    make build TAG=my-feature  Сборка с кастомным тегом"
	@echo ""
	@echo "  Push в registry:"
	@echo "    make push                          Push (TAG=dev, PLATFORM=linux/amd64)"
	@echo "    make push PLATFORM=linux/amd64     Push под amd64"
	@echo "    make push-dev                      Push с тегом dev"
	@echo "    make push-prod                     Push с тегом latest"
	@echo ""
	@echo "  Переменные:"
	@echo "    TAG       Тег образа  (default: dev)"
	@echo "    PLATFORM  Платформа   (default: linux/amd64)"
	@echo ""

# --- Auth ---

login:
	docker login registry.gitlab.com

# --- Buildx ---

buildx-setup:
	docker buildx inspect $(BUILDER) > /dev/null 2>&1 || \
	  docker buildx create --name $(BUILDER) --driver docker-container --bootstrap
	docker buildx use $(BUILDER)
	@echo "Builder '$(BUILDER)' готов"

# --- Сборка ---

build:
	docker buildx build \
	  --file $(DOCKERFILE) \
	  --platform $(PLATFORM) \
	  --tag $(REGISTRY):$(TAG) \
	  --load \
	  .

# --- Push ---

push:
	docker buildx build \
	  --file $(DOCKERFILE) \
	  --platform $(PLATFORM) \
	  --tag $(REGISTRY):$(TAG) \
	  --push \
	  .
	@echo "Pushed: $(REGISTRY):$(TAG)"

push-dev:
	$(MAKE) push TAG=dev

push-prod:
	$(MAKE) push TAG=latest
