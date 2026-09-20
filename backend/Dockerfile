FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# docker CLI + compose (статические сборки): celery-low поднимает Node-RED тенантов через docker.sock.
# 28, а не 29: CLI 29 требует Engine API >= 1.44 на хосте.
COPY --from=docker:28-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:28-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose

# Зависимости — отдельный слой, инвалидируется только при изменении lock-файла
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --frozen --no-dev --no-install-project

COPY . .

# Установка проекта + создание пользователя + права
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev && \
  mkdir -p /prom_mp && \
  chmod +x /app/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
