# =============================================================================
# roomio GRMS — backend Makefile
# =============================================================================
# Использование:
#   make build              # локальная сборка (текущая платформа)
#   make push TAG=dev       # мультиплатформенная сборка + push в registry
#   make push TAG=latest    # то же, для продакшна
# =============================================================================

REGISTRY  = registry.gitlab.com/yroomio/grms
TAG      ?= dev
PLATFORM ?= linux/arm64
PLATFORMS = linux/amd64,linux/arm64
BUILDER   = grms-builder
DOCKERFILE = Dockerfile

.PHONY: help buildx-setup build push push-dev push-prod build-debug

# --- Help ---

help:
	@echo ""
	@echo "  roomio GRMS — сборка Docker-образа"
	@echo ""
	@echo "  Подготовка:"
	@echo "    make buildx-setup          Создать buildx-builder (один раз)"
	@echo ""
	@echo "  Сборка:"
	@echo "    make build                 Локальная сборка (текущая платформа, без push)"
	@echo "    make build TAG=my-feature  Сборка с кастомным тегом"
	@echo "    make build-debug           Сборка с htop/vim для отладки"
	@echo ""
	@echo "  Push в registry:"
	@echo "    make push                  Мультиплатформа + push (TAG=dev по умолчанию)"
	@echo "    make push-dev              Push с тегом dev"
	@echo "    make push-prod             Push с тегом latest"
	@echo ""
	@echo "  Переменные:"
	@echo "    TAG       Тег образа      (default: dev)"
	@echo "    PLATFORM  Платформа       (default: linux/amd64)"
	@echo "    PLATFORMS Для push        (default: linux/amd64,linux/arm64)"
	@echo ""

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

build-debug:
	docker buildx build \
	  --file $(DOCKERFILE) \
	  --platform $(PLATFORM) \
	  --build-arg DEBUG_TOOLS=1 \
	  --tag $(REGISTRY):$(TAG)-debug \
	  --load \
	  .

# --- Push ---

push: buildx-setup
	docker buildx build \
	  --file $(DOCKERFILE) \
	  --platform $(PLATFORMS) \
	  --tag $(REGISTRY):$(TAG) \
	  --push \
	  .
	@echo "Pushed: $(REGISTRY):$(TAG)"

push-dev:
	$(MAKE) push TAG=dev

push-prod:
	$(MAKE) push TAG=latest
