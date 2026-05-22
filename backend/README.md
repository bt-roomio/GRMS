# roomio GRMS — Backend

## Сборка Docker-образа

Все команды выполняются из директории `backend/`.

### Подготовка (один раз)

```bash
make buildx-setup
```

### Локальная сборка (без push)

```bash
make build              # текущая платформа, тег :dev
make build TAG=feature  # кастомный тег
```

### Push в GitLab Registry

```bash
make push-dev           # мультиплатформа → registry:dev
make push-prod          # мультиплатформа → registry:latest
make push TAG=my-tag    # кастомный тег
```

Реестр: `registry.gitlab.com/yroomio/grms`
Платформы: `linux/amd64`, `linux/arm64`

---

## Структура образа

- Базовый образ: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- Пакетный менеджер: `uv` (два слоя — зависимости отдельно от кода)
- Venv: `/app/.venv`
- Рабочая директория: `/app`
- Пользователь: `app` (non-root, home `/home/app`)
- Точка входа: `/app/entrypoint.sh`

Entrypoint выполняет:
1. `manage.py migrate`
2. `manage.py collectstatic`
3. Запуск `gunicorn` с Uvicorn-воркерами (ASGI)

---

## Отладка образа

```bash
# Войти в контейнер из реестра
docker run --rm -it registry.gitlab.com/yroomio/grms:dev bash

# Войти в запущенный контейнер
docker exec -it django bash

# Проверить установленные пакеты
docker run --rm registry.gitlab.com/yroomio/grms:dev uv pip list
```

---

## Устранение неполадок

### Redis replication (role:slave)

```bash
docker exec -it redis redis-cli INFO replication
# Если role:slave:
docker exec -it redis redis-cli REPLICAOF NO ONE
```

### Зависимости не обновились в dev

В dev используется named volume `backend_venv` для `/app/.venv`.
После изменения `uv.lock` или `pyproject.toml` — пересобери образ и удали volume:

```bash
make push-dev
docker volume rm roomio_backend_venv
```
