# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GRMS (Guest Room Management System) is a Django-based IoT/smart hotel management platform with real-time WebSocket communication, device management, and multi-tenant architecture. The system integrates with access control devices, handles guest check-ins/check-outs, and provides real-time monitoring through WebRTC and MQTT protocols.

## Technology Stack

- **Backend**: Django 5.0.4 with Django REST Framework
- **Package manager**: uv (`pyproject.toml` + `uv.lock`; `requirements.txt` is a generated mirror)
- **Real-time**: Django Channels (WebSockets), served via Gunicorn/Uvicorn ASGI workers
- **Database**: PostgreSQL 16 with TimescaleDB extension for time-series data, fronted by PgBouncer (transaction pooling)
- **Task Queue**: Celery on a dedicated `redis-broker` instance (separate from the `redis` cache/channel layer)
- **Message Queue**: RabbitMQ for device communication, MQTT broker
- **Auth**: JWT (djangorestframework-simplejwt), django-allauth (Google, Microsoft, Keycloak SSO)
- **Monitoring**: Prometheus metrics (django-prometheus); standalone Prometheus + Grafana + Alertmanager stack under `deploy/monitoring/`
- **Process Management**: Each process runs as its own Docker Compose service (no supervisord); orchestrated via `deploy/Makefile`

## Development Commands

### Backend Development

Run backend commands from `backend/` or via `./manage.py`. Dependencies are uv-managed (`uv sync --frozen` from `uv.lock`); tests run under pytest (`./manage.py test`, or `pytest path/to/test.py::TestClass::test_method`).

### Code Quality

Code style config lives in `backend/pyproject.toml`: Ruff (lint + format + import sorting, line length 120) and `ty` (type check, environment root `./apps`). `pre-commit` runs Ruff on commit (`.pre-commit-config.yaml`). Import-order groups are defined under `[tool.ruff.lint.isort]`.

### Docker Development

Compose stack and orchestration live in `deploy/`. Everything is driven through `deploy/Makefile` (run from `deploy/`), which layers `docker-compose.yml` with `docker-compose.override.yml` (dev, default) or `docker-compose.prod.yml` (`ENV=prod`, resource limits). Services are grouped into `infra`, `app`, `iot`, `front`, `proxy`.

```bash
# Bring services up by level (run from deploy/)
make up-infra       # postgres, pgbouncer, redis, redis-broker, rabbitmq
make up-app         # infra + Django (backend) + Celery workers
make up-all         # everything except Node-RED
make up-all ENV=prod

# Logs / shell / status for a single service
make logs s=backend
make shell s=backend
make ps

# Django helpers
make migrate
make collectstatic

# Deploy (pull images + recreate)
make deploy-backend
make deploy-frontend

# One-off exec (container names: django, celery-critical, celery-default, celery-low, ...)
docker exec -it django python manage.py <command>
```

Node-RED runs as a separate multi-tenant stack (`deploy/docker-compose.nodered.yml`, one project per tenant): `make nodered-up-<tenant>`, `make nodered-up-all`. The monitoring stack has its own compose + Makefile under `deploy/monitoring/`.

### Tenant Management

```bash
# Create a new tenant (multi-tenant system)
docker exec -it django python manage.py create_tenant

# Delete tenant
docker exec -it django python manage.py delete_tenant

# Create relationships
docker exec -it django python manage.py create_relation
```

### Custom Management Commands

Core commands in `backend/apps/core/management/commands/`:
- `mq_async.py` - RabbitMQ async message handler; runs as the `mq-async` service (invoked directly as `python apps/core/management/commands/mq_async.py`, 2 replicas, bypasses PgBouncer)
- `active_attribute_server_scope.py` / `read_write_cpu_ram.py` - now driven by Celery beat (not standalone services)
- `create_tenant.py` - Interactive tenant creation
- `create_admin.py` - Create an admin/superuser
- `delete_tenant.py` - Delete tenant
- `create_relation.py` - Create relationships between entities
- `give_perms.py` / `give_ui_perms.py` - Manage permissions
- `fixtures.py` - Load fixture data
- `reset_ids.py` - Reset/renumber IDs
- `ts_kv_from_csv.py` - Import time-series data from CSV
- `sim_message.py` / `sim_publish.py` - Simulate device messages/telemetry
- `playground.py` - Development testing/experimentation

Mews integration commands in `backend/apps/mews/management/commands/`:
- `mews_websocket.py` - Mews WebSocket client (runs as the `mews-websocket` service)
- `mews_sync.py` - Manual reservation synchronization
- `mews_access_tokens.py` - Manage Mews access tokens
- `get_mews_customers.py` - Fetch customer data from Mews
- `sim_mews_event.py` - Simulate Mews events for testing

Services commands in `backend/apps/services/management/commands/`:
- `pms_handler.py` - PMS message handler (runs as the `pms-handler` service)
- `pms_sync.py` - PMS synchronization
- `migrate_integration_settings.py` - Migrate integration settings

## Architecture

### Multi-Tenant Design

The system uses a multi-tenant architecture where each hotel/property is a separate tenant:
- Tenants have their own data isolation through database filtering
- `TenantProfile` defines tenant capabilities
- `CheckForTenantMiddleware` (core/utils/middleware.py) handles tenant context
- Most models inherit from `BaseModel` which includes tenant relationships

### App Structure

The Django project is organized into specialized apps under `backend/apps/`:

- **core**: Base models (`BaseModel`, `UpdateByModel`), shared utilities, middleware, and pagination
- **users**: Custom user model (email-only, no username), authentication, JWT tokens
- **main**: Core business logic
  - Tenant, Room, RoomType, Guest, Customer models
  - Device management (Device, DeviceProfile, DeviceCredentials)
  - Check-in/check-out workflows and Room History
  - Dashboard metrics
- **shuttle**: Real-time WebSocket communication
  - Time-series data storage (TsKvDictionary, TsKvLatest)
  - WebSocket consumers for device communication
  - Demultiplexer for routing WebSocket messages
- **access_manager**: Physical access control integration, device synchronization
- **services**: External service integrations (PMS systems)
- **hoteza**: Hoteza PMS integration (webhook endpoints for check-in/check-out/DND/guest events, not in INSTALLED_APPS, routes at root level)
- **admin_panel**: Multi-tenant admin operations (tenant management, user management, user impersonation), routes under `/api/v1/admin/`
- **mews**: Mews PMS integration
  - Real-time WebSocket client for Mews events
  - Reservation synchronization
  - Access token management
  - Guest data sync

### Real-Time Communication

The system uses multiple protocols:
- **WebSockets**: Django Channels with Redis channel layer
  - Main router: `backend/apps/shuttle/router.py`
  - Two endpoints:
    - `/api/ws/` - v1 endpoint (no auth middleware, uses ReceiverConsumer)
    - `/api/ws/v2/` - v2 endpoint (JWT auth via JWTAuthMiddlewareStack, uses Demultiplexer)
  - Consumers in `shuttle/consumers/` and `shuttle/v2_consumers/`
  - Demultiplexer pattern for routing WebSocket messages by stream name
  - Channel layer uses custom `uuidjson` serializer (registered in core.apps)
- **MQTT**: External broker for IoT device communication (mqtt-broker service)
- **RabbitMQ**: Internal message queue for device commands and telemetry
  - Handled by the `mq_async` command running as the `mq-async` service (2 replicas)

### Process Architecture (Docker services)

There is no supervisord. Each process is its own Compose service, all built from the same image and defined in `deploy/docker-compose.yml`:

1. **backend** (`django`) - Gunicorn with Uvicorn ASGI workers (port 8000). Startup runs `entrypoint.sh`: `migrate` + `collectstatic`, then Gunicorn with `GUNICORN_WORKERS` (default `2*CPU+1`).
2. **celery-critical** - worker on the `critical` queue (`-c 2`, max 50 tasks/child)
3. **celery-default** - worker on the `default` queue (`-c 8`, max 100 tasks/child)
4. **celery-low** - worker on the `low` queue (`-c 1`, max 50 tasks/child)
5. **celery-beat** - periodic task scheduler
6. **celery-flower** - Celery monitoring UI (port 5555, basic auth via `FLOWER_BASIC_AUTH`)
7. **mq-async** - RabbitMQ async message handler (2 replicas; connects directly to Postgres, bypassing PgBouncer)
8. **mews-websocket** - Mews WebSocket client for real-time events
9. **pms-handler** - PMS message handler for external integrations

Infra services: `postgres` (TimescaleDB), `pgbouncer`, `redis` (cache/channel layer), `redis-broker` (Celery broker/result), `rabbitmq`. Edge: `mqtt` (IoT), `frontend` (Vue), `proxy` (nginx-proxy) + `letsencrypt` (acme-companion). Each service sets its own `PGAPPNAME` (`grms-backend`, `grms-celery-*`, `grms-mq-async`, ...) for Postgres monitoring.

Note: `active_attribute_server_scope` and `read_write_cpu_ram` run via Celery beat, not as standalone services.

### Database Models

Key model patterns defined in `backend/apps/core/models.py`:
- `BaseModel`: UUID primary key, created_at (Unix timestamp in milliseconds), created_by
  - Uses `get_mil_sec()` for timestamps (Unix epoch in milliseconds)
  - All models inherit from this for consistent ID and audit fields
- `UpdateByModel`: updated_at, updated_by tracking
  - Automatically updates `updated_at` on save if object exists
- `BaseModelTs`: Alternative base with `ts` field instead of `created_at`
- `NewUpdateByModel`: DateTimeField variant of UpdateByModel (uses Django DateTimeField instead of millisecond timestamps)
- Time-series models use TimescaleDB hypertables for device telemetry
- Most models use `models.AutoField` as DEFAULT_AUTO_FIELD
- Custom `UnixTimeStampField` stores timestamps as Unix epoch milliseconds

### API Design

- RESTful API under `/api/v1/` (users, main, shuttle, access-manager, services, admin namespaces)
- JWT authentication required by default
- Pagination: 15 items per page (configurable via `page_size` query param)
- Swagger/OpenAPI docs available (drf-yasg)
- URL routing: Each app has its own `urls.py` under app namespace

### Celery Tasks

Queues are defined in `config/celery.py`: `critical`, `default` (default queue), `low`. Task-to-queue routing lives in `app.conf.task_routes` (e.g. `sync_devices_task`, `auto_check_out`, `auto_block` → `critical`; `aggregate_table_ts_kv`, `delete_old_logs`, `flush_expired_tokens` → `low`). Global settings: `task_soft_time_limit=300`, `task_time_limit=360`, `task_acks_late=True`, `worker_prefetch_multiplier=1`.

Scheduled tasks in `config/settings.py` (`CELERY_BEAT_SCHEDULE`):
- `auto-checkout` - every 5 minutes (main.tasks.auto_check_out)
- `auto-block-guest` - 1800s interval (main.tasks.auto_block)
- `sync_device` - 300s interval (access_manager.tasks.sync_device.sync_devices_task)
- `clean_logs` - Daily at midnight (shuttle.tasks.delete_old_logs)
- `update_db_metrics` - 60s interval (core.tasks.update_db_metrics)
- `mews-sync` - 60s interval (mews.tasks.sync_reservations)
- `active-attribute-server-scope` - 10s interval (core.tasks.active_attribute_server_scope_task)
- `aggregate-ts-kv` - Daily at 03:00 (shuttle.tasks.aggregate_table_ts_kv)
- `flush-expired-tokens` - Daily at 03:00 (users.tasks.flush_expired_tokens)

Note: `mews-access-tokens` is currently commented out in the schedule.

Custom tasks can be added to app-specific `tasks.py` files using `@shared_task` decorator.

### Authentication

- Custom user model: `users.User` (email-based, no username field)
- Multiple auth backends: JWT, Django ModelBackend, django-allauth
- Social auth: Google OAuth, Microsoft, Keycloak (OpenID Connect)
- Custom adapters prevent public signup: `NoSignupAccountAdapter`, `NoNewSocialSignupAdapter`
- Frontend redirects configured via `FRONTEND_DOMAIN` env var

### Monitoring

- Prometheus metrics exposed at `/` (django-prometheus), aggregated across processes via `PROMETHEUS_MULTIPROC_DIR=/prom_mp`
- Custom metrics in `main/metrics.py`
- Gateway monitoring via `DJANGO_IS_MONITORING_GATEWAYS` and `DJANGO_MONITOR_DISABLED_GATEWAYS`
- Database metrics updated every 60s via Celery task
- Standalone observability stack under `deploy/monitoring/` (Prometheus + Grafana + Alertmanager + node-exporter + blackbox), with Grafana dashboards and alert rules; alerts route to Telegram. Runs on the shared external `roomio_net` network.
- Celery workers/queues can be inspected via Flower (`celery-flower` service, port 5555)

## Configuration

### Environment Variables

Key variables (see `deploy/env.example` for the compose stack and `backend/.env` for local dev):
- Database: `POSTGRES_*` variables (containers reach Postgres through PgBouncer by default)
- Redis: `REDIS_HOST`, `REDIS_PORT` (cache/channels); Celery uses `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` pointed at `redis-broker`
- RabbitMQ: `RABBITMQ_*` variables
- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- CORS: `DJANGO_CORS_ORIGIN_WHITELIST`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- SSO: `KEYCLOAK_*`, `GOOGLE_CLIENT_*`, `MS_CLIENT_*`
- Email: `EMAIL_*` variables
- Frontend: `FRONTEND_DOMAIN`, `VITE_*` variables
- Proxy/TLS (nginx-proxy + acme-companion): `API_VIRTUAL_HOST`, `FRONTEND_VIRTUAL_HOST`, `LETSENCRYPT_EMAIL`
- Flower: `FLOWER_BASIC_AUTH` (user:password, required by the `celery-flower` service)

### Static & Media Files

- Static files: `/app/static/` (collected via `collectstatic`)
- Media files: `/app/media/` (user uploads)
- Both are shared volumes served by the `proxy` (nginx-proxy) container in production

## Testing

- Test framework: pytest with pytest-django and pytest-asyncio
- Test runner: `config.pytest_runner.PytestTestRunner`
- Test files: `test_*.py` or `*_tests.py` or `tests.py`
- Async mode: auto
- Configuration: `backend/pyproject.toml` (tool.pytest.ini_options)
- Settings: Automatically uses `config.settings` with `TESTING=True`
- Each app has a `tests/` directory with individual test files
- Test structure:
  - `core/tests/base.py` - Base test classes
  - `*/tests/test_*.py` - Individual test modules
  - `shuttle/tests/consumers/` - WebSocket consumer tests
  - `shuttle/tests/rest/` - REST API tests

## CI/CD

GitLab CI pipeline (`.gitlab-ci.yml`) with stages:
1. **test** - `uv sync --frozen` + `uv run python manage.py test` against TimescaleDB (2.21.0) and Redis 7 (uv image, Python 3.12)
2. **build** - Build Docker image, push to GitLab registry (dev/latest tags)
3. **staging** - Manual deployments to leto (dev environment)
4. **production** - Manual deployments to grms (via jump host) and cloud environments

Deploy jobs run the `deploy/Makefile` targets over SSH; the `MAKE_ENV` CI variable is passed through to select the compose profile (e.g. `ENV=prod`).

Branches:
- `dev` - Development branch, builds `dev` tag
- `stable` - Production branch, builds `latest` tag
- `main` - Main integration branch

## Common Patterns

### Adding a New Model

1. Create model in appropriate app's `models.py`, inherit from `BaseModel` or `UpdateByModel`
2. Create queryset in app's `querysets/` directory (if complex queries needed)
3. Create serializer in app's `serializers/` directory
4. Create viewset in app's `views/` directory
5. Register URL in app's `urls.py`
6. Run migrations: `./manage.py makemigrations && ./manage.py migrate`
7. Add tests in app's `tests/` directory

Note: Django will automatically generate migrations. Never write migrations manually.

### Adding a WebSocket Consumer

1. Create consumer class in `shuttle/consumers/` or `shuttle/v2_consumers/`
2. Add route to `shuttle/router.py`
3. Implement `connect`, `disconnect`, and message handlers
4. Use demultiplexer for complex message routing

### Adding a Celery Task

1. Create task in app's `tasks.py` with `@shared_task` decorator
2. For periodic tasks, add to `CELERY_BEAT_SCHEDULE` in `config/settings.py`
3. To run it off the `default` queue, add a route in `app.conf.task_routes` (`config/celery.py`) targeting `critical` or `low`
4. Tasks run in the matching Celery worker service (`celery-critical` / `celery-default` / `celery-low`)

### Adding Permissions

- Use Django's built-in permission system
- Custom permissions defined in model `Meta.permissions`
- Use `give_perms` management command to assign permissions

## Key Architectural Decisions

### Timestamp Handling
- All timestamps are stored as Unix epoch in **milliseconds** (not seconds)
- Use `get_mil_sec()` from `core.utils.get_time` for timestamp generation
- Custom `UnixTimeStampField` handles millisecond timestamps

### Multi-Process Architecture
- Each process is a separate Docker Compose service built from the same image (no supervisord)
- Gunicorn uses Uvicorn workers for ASGI support (WebSockets)
- Celery is split into per-priority workers (`critical`/`default`/`low`) plus beat and flower
- Each process has isolated Prometheus metrics via multiprocess mode (`PROMETHEUS_MULTIPROC_DIR`)

### WebSocket Architecture
- Two separate WebSocket endpoints (v1 without auth, v2 with JWT)
- Demultiplexer routes messages by stream name to specific consumers
- Channel layer uses Redis with custom UUID JSON serializer
- JWT auth implemented as middleware wrapper (JWTAuthMiddlewareStack)

### Database Connection Management
- Pooling is handled by PgBouncer (transaction mode) in front of Postgres, so Django uses `CONN_MAX_AGE=0`
- `mq-async` connects directly to Postgres (`POSTGRES_HOST=postgres`), bypassing PgBouncer — transaction pooling is incompatible with its long-lived async connections
- Each process sets its own `PGAPPNAME` for PostgreSQL monitoring (`grms-backend`, `grms-celery-critical`, `grms-mq-async`, ...)

## Deployment Notes

- The system requires TimescaleDB (PostgreSQL extension) for time-series data
- `proxy` (nginx-proxy) + `letsencrypt` (acme-companion) handle routing and automatic TLS via `*_VIRTUAL_HOST` / `LETSENCRYPT_HOST` env vars
- Processes run as separate Compose services orchestrated by `deploy/Makefile` (no supervisord)
- Update deployments via `make deploy-backend` / `make deploy-frontend` (or the CI production jobs); `entrypoint.sh` runs migrations and collectstatic on backend startup
- Create tenant before first use via `create_tenant` command
- Monitor metrics at the Prometheus endpoint (`/`), Grafana (`deploy/monitoring/`), and Flower (port 5555) for production health
- Never write migrations manually - always use `./manage.py makemigrations`
- Before creating new features, check if similar patterns exist in the codebase
