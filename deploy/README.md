# roomio GRMS — Deploy

Инструкция по развёртыванию и управлению сервисами.

## Структура

```
deploy/
├── docker-compose.yml          # Базовая конфигурация (prod)
├── docker-compose.override.yml # Локальная разработка (применяется автоматически)
├── docker-compose.prod.yml     # Prod-специфика: resource limits, закрытые порты
├── docker-compose.nodered.yml  # Node-RED multi-tenant
├── Makefile                    # Команды управления
├── env.example                 # Шаблон переменных окружения
├── .env.nodered.example        # Шаблон для Node-RED тенанта
├── nginx/
│   ├── frontend.conf           # Конфиг nginx для фронтенда
│   └── vhost.d/                # Конфиги nginx-proxy (per-vhost)
└── monitoring/                 # Prometheus + Grafana + Alertmanager
```

## Профили

| Профиль   | Сервисы                                                            |
| --------- | ------------------------------------------------------------------ |
| `infra`   | postgres, pgbouncer, redis, redis-broker, rabbitmq                 |
| `app`     | backend (django), celery-\*, mq-async, mews-websocket, pms-handler |
| `iot`     | mqtt                                                               |
| `front`   | frontend, frontend-nginx                                           |
| `proxy`   | nginx-proxy, letsencrypt                                           |
| `nodered` | nodered (single-tenant, через основной compose)                    |

---

## Первый запуск (production)

### 1. Переменные окружения

```bash
cp env.example .env
# Заполни .env — обязательные поля помечены "change_me"
```

Ключевые переменные:

- `POSTGRES_PASSWORD`, `RABBITMQ_DEFAULT_PASS`, `DJANGO_SECRET_KEY` — сменить на случайные строки
- `API_VIRTUAL_HOST`, `FRONTEND_VIRTUAL_HOST` — домены сервера
- `LETSENCRYPT_EMAIL` — email для SSL-сертификатов
- `BACKEND_IMAGE_TAG` — тег образа (`dev` или `latest`)

### 2. Запуск инфраструктуры

```bash
make up-infra
```

Дождись, пока все сервисы станут `healthy`:

```bash
make ps
```

### 3. Первичная настройка Django

```bash
make migrate
make shell s=backend
# Внутри контейнера:
python manage.py createsuperuser
python manage.py create_tenant
```

### 4. Запуск приложения

```bash
make up-app         # инфра + Django + Celery
make up-iot         # + MQTT
make up-front       # + Frontend
make up-proxy       # + nginx-proxy + SSL
```

Или всё сразу:

```bash
make up-all
```

---

## Локальная разработка

`docker-compose.override.yml` применяется **автоматически** при запуске без `-f`.

Отличия от prod:

- Bind-mount кода (`../backend:/app`) — hot-reload без пересборки образа
- Открытые порты: postgres `5433`, pgbouncer `6432`, redis `6379/6380`, rabbit `15672`
- Django запускается через `runserver` (не gunicorn)
- Frontend запускается через `yarn dev` (Vite dev-сервер на порту `5173`)
- `nginx-proxy` и `letsencrypt` не запускаются

### Запуск backend в dev

```bash
make up-app
# Backend доступен на http://localhost:8000
```

### Запуск frontend в dev

```bash
dc --profile infra --profile app --profile front up -d
# Frontend доступен на http://localhost:5173
```

---

## Деплой обновлений

### Обновить всё приложение

```bash
make deploy
# git pull + docker pull + перезапуск app-сервисов
```

### Обновить только backend и воркеры

```bash
make deploy-backend
```

### Обновить образы без перезапуска

```bash
make pull
```

---

## Управление сервисами

```bash
make ps                    # статус всех контейнеров
make logs s=backend        # логи сервиса (Ctrl+C для выхода)
make logs                  # логи всех сервисов
make restart s=backend     # перезапустить сервис
make shell s=backend       # bash внутри контейнера
make down                  # остановить все сервисы
make down-v                # остановить и удалить volumes (ОСТОРОЖНО: удалит данные!)
```

### Django-команды

```bash
make migrate               # применить миграции
make collectstatic         # собрать статику
make shell s=backend       # войти в контейнер и выполнять команды вручную
```

---

## Node-RED (multi-tenant)

Каждый тенант — отдельный контейнер с изолированным volume и доменом.

### Подготовка тенанта

```bash
cp .env.nodered.example .env.nodered.nines
# Заполни TENANT_NAME, NODERED_TENANT_ID, NODERED_VIRTUAL_HOST
```

### Управление тенантами

```bash
make nodered-up-nines          # поднять тенанта
make nodered-down-nines        # остановить
make nodered-restart-nines     # перезапустить
make nodered-logs-nines        # логи
make nodered-pull-nines        # обновить образ

make nodered-up-all            # поднять всех (NODERED_TENANTS=nines map olympic)
make nodered-down-all          # остановить всех
```

Список тенантов по умолчанию задан в Makefile:

```makefile
NODERED_TENANTS ?= nines map olympic
```

---

## Мониторинг

Стек: Prometheus + Grafana + Alertmanager + Blackbox Exporter + Node Exporter.

```bash
cd monitoring/
cp .env.example .env          # заполни GRAFANA_ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN и др.
docker compose up -d
```

Grafana доступна на `GRAFANA_VIRTUAL_HOST` (через nginx-proxy) или напрямую на порту `3000`.

### Цели для Blackbox (HTTPS мониторинг)

Файл `monitoring/targets/blackbox-https.yml` — **не в git** (server-specific).
Создай по шаблону:

```bash
cp monitoring/targets/blackbox-https.example.yml monitoring/targets/blackbox-https.yml
# Заполни своими доменами
```

### Alertmanager (Telegram)

Секреты `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` задаются в `monitoring/.env`.
Файл `monitoring/alertmanager/alertmanager.yml` использует `${...}` — подстановка происходит при старте контейнера через `envsubst`.

---

## Prod-режим (resource limits)

```bash
make up-all ENV=prod
# Применяет docker-compose.prod.yml поверх базового
```

Prod-файл добавляет CPU/memory limits для всех сервисов и закрывает внешние порты.

---

## Устранение неполадок

### PostgreSQL не стартует (WAL corruption)

Если postgres убит `signal 9` во время recovery и не может запуститься:

```bash
make down
docker compose --profile infra up postgres -d   # поднять только postgres и ждать

# Если signal 9 повторяется — сбросить WAL (dev-только, потеря данных):
docker compose --profile infra stop postgres
docker run --rm \
  -v roomio_pg_data:/var/lib/postgresql/data \
  timescale/timescaledb:2.21.0-pg16 \
  pg_resetwal -f /var/lib/postgresql/data
docker compose --profile infra up postgres -d
```

### Django не видит Django (No module named 'django')

В dev: bind mount `../backend:/app` перекрывает `.venv`. Решение — named volume `backend_venv` уже настроен в `docker-compose.override.yml`. При смене зависимостей удали volume:

```bash
docker volume rm roomio_backend_venv
```

и пересобери образ: `make build` (из `backend/`).

### pgbouncer unhealthy

pgbouncer слушает на порту `5432` внутри контейнера (не `6432`). Healthcheck проверяет именно `5432`.

### Сервис не находит зависимость (no such service)

При явном `-f` нужно указывать все профили. Используй `make`-команды — они уже включают нужные профили.
