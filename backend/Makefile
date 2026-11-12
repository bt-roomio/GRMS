# =============================================================================
# roomio GRMS — backend Makefile
# =============================================================================
# Usage:
#   make build                         # local build (current platform)
#   make push                          # build + push (TAG=dev)
#   make push TAG=latest PLATFORM=...  # with custom parameters
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
	@echo "  roomio GRMS — Docker image build"
	@echo ""
	@echo "  Setup:"
	@echo "    make login                 Log in to GitLab Container Registry"
	@echo "    make buildx-setup          Create the buildx builder (once)"
	@echo ""
	@echo "  Build:"
	@echo "    make build                 Local build (current platform, no push)"
	@echo "    make build TAG=my-feature  Build with a custom tag"
	@echo ""
	@echo "  Push to registry:"
	@echo "    make push                          Push (TAG=dev, PLATFORM=linux/amd64)"
	@echo "    make push PLATFORM=linux/amd64     Push for amd64"
	@echo "    make push-dev                      Push with the dev tag"
	@echo "    make push-prod                     Push with the latest tag"
	@echo ""
	@echo "  Variables:"
	@echo "    TAG       Image tag  (default: dev)"
	@echo "    PLATFORM  Platform    (default: linux/amd64)"
	@echo ""

# --- Auth ---

login:
	docker login registry.gitlab.com

# --- Buildx ---

buildx-setup:
	docker buildx inspect $(BUILDER) > /dev/null 2>&1 || \
	  docker buildx create --name $(BUILDER) --driver docker-container --bootstrap
	docker buildx use $(BUILDER)
	@echo "Builder '$(BUILDER)' is ready"

# --- Build ---

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
