FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps first — changes rarely, good for layer caching
RUN apt-get update && apt-get install -y --no-install-recommends \
  htop=3.2.2-2 \
  vim=2:9.0.1378-2+deb12u2 \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps using lockfile — cached separately from source code
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  uv sync --frozen --no-dev --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p /prom_mp

EXPOSE 8000

CMD ["gunicorn", "config.asgi:application", \
  "-k", "uvicorn.workers.UvicornWorker", \
  "--workers", "${GUNICORN_WORKERS:-4}", \
  "--bind", "0.0.0.0:8000"]
