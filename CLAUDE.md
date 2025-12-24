# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GRMS (Guest Room Management System) is a Django-based IoT/smart hotel management platform with real-time WebSocket communication, device management, and multi-tenant architecture. The system integrates with access control devices, handles guest check-ins/check-outs, and provides real-time monitoring through WebRTC and MQTT protocols.

## Technology Stack

- **Backend**: Django 5.0.4 with Django REST Framework
- **Real-time**: Django Channels (WebSockets), Daphne ASGI server
- **Database**: PostgreSQL with TimescaleDB extension for time-series data
- **Task Queue**: Celery with Redis broker
- **Message Queue**: RabbitMQ for device communication, MQTT broker
- **Auth**: JWT (djangorestframework-simplejwt), django-allauth (Google, Microsoft, Keycloak SSO)
- **Monitoring**: Prometheus metrics (django-prometheus)
- **Process Management**: Supervisord (runs Django, Celery, MQ handler, custom services)

## Development Commands

### Backend Development

All backend commands should be run from the `backend/` directory or via `./manage.py`:

```bash
# Install dependencies
pip install -r requirements.txt

# Database migrations
./manage.py makemigrations
./manage.py migrate

# Run tests (uses pytest)
./manage.py test

# Run specific test file
pytest path/to/test_file.py

# Run specific test class or method
pytest path/to/test_file.py::TestClass::test_method

# Run tests with verbose output
pytest -v

# Create superuser
./manage.py createsuperuser

# Run development server (for local dev without Docker)
./manage.py runserver

# Check for issues (no database access)
./manage.py check
```

### Code Quality

Code style configuration is in `backend/pyproject.toml`:

```bash
# Format code (Black, line length 120)
black .

# Check code style (Ruff, line length 120, excludes migrations)
ruff check .

# Type checking (Pyright, standard mode)
pyright

# Sort imports (isort with Black-compatible profile)
isort .
```

Import order (configured in pyproject.toml):
1. Future imports
2. Standard library
3. Third-party packages
4. Django REST Framework packages (drf)
5. Config module
6. First-party packages
7. App packages (main, shuttle, users, core, services)
8. Local folder imports

### Docker Development

```bash
# Build and run all services
docker compose up --build -d

# View logs
docker compose logs -f django
docker compose logs -f celery

# Execute commands in Django container
docker exec -it django bash
docker exec -it django python manage.py migrate

# Restart services after code changes
docker compose down backend nginx
docker compose up backend nginx -d

# Pull latest images and restart
docker compose pull && docker compose down && docker compose up -d
```

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
- `mq.py` - RabbitMQ message handler (runs via supervisord)
- `active_attribute_server_scope.py` - Active attribute server (runs via supervisord)
- `create_tenant.py` - Interactive tenant creation
- `delete_tenant.py` - Delete tenant
- `create_relation.py` - Create relationships between entities
- `fixtures.py` - Load fixture data
- `give_perms.py` - Manage permissions
- `playground.py` - Development testing/experimentation

Mews integration commands in `backend/apps/mews/management/commands/`:
- `mews_websocket.py` - Mews WebSocket client (runs via supervisord)
- `mews_sync.py` - Manual reservation synchronization
- `mews_access_tokens.py` - Manage Mews access tokens
- `get_mews_customers.py` - Fetch customer data from Mews
- `sim_mews_event.py` - Simulate Mews events for testing

Services commands in `backend/apps/services/management/commands/`:
- `pms_handler.py` - PMS message handler (runs via supervisord)
- `pms_sync.py` - PMS synchronization

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
  - Handled by `mq` management command running in supervisord

### Process Architecture (Supervisord)

The Django container runs multiple processes via supervisord (`backend/supervisord.conf`):
1. **django** - Gunicorn with Uvicorn workers (ASGI, 4 workers, port 8000)
2. **celery** - Background task worker (4 concurrency, max 100 tasks per child)
3. **celery-beat** - Periodic task scheduler
4. **mq** - RabbitMQ message handler (custom management command)
5. **active_attribute_server_scope** - Custom service for device attributes
6. **mews_websocket** - Mews WebSocket client for real-time events
7. **pms_handler** - PMS message handler for external integrations

### Database Models

Key model patterns defined in `backend/apps/core/models.py`:
- `BaseModel`: UUID primary key, created_at (Unix timestamp in milliseconds), created_by
  - Uses `get_mil_sec()` for timestamps (Unix epoch in milliseconds)
  - All models inherit from this for consistent ID and audit fields
- `UpdateByModel`: updated_at, updated_by tracking
  - Automatically updates `updated_at` on save if object exists
- `BaseModelTs`: Alternative base with `ts` field instead of `created_at`
- Time-series models use TimescaleDB hypertables for device telemetry
- Most models use `models.AutoField` as DEFAULT_AUTO_FIELD
- Custom `UnixTimeStampField` stores timestamps as Unix epoch milliseconds

### API Design

- RESTful API under `/api/v1/`
- JWT authentication required by default
- Pagination: 15 items per page (configurable via `page_size` query param)
- Swagger/OpenAPI docs available (drf-yasg)
- URL routing: Each app has its own `urls.py` under app namespace

### Celery Tasks

Scheduled tasks in `config/settings.py` (`CELERY_BEAT_SCHEDULE`):
- `auto-checkout` - 30s interval (main.tasks.auto_check_out)
- `sync_device` - 300s interval (access_manager.tasks.sync_device.sync_devices_task)
- `clean_logs` - Daily at midnight (shuttle.tasks.delete_old_logs)
- `update_db_metrics` - 60s interval (core.tasks.update_db_metrics)
- `mews-sync` - 60s interval (mews.tasks.sync_reservations)
- `mews-access-tokens` - 60s interval (mews.tasks.sync_access_tokens)

Custom tasks can be added to app-specific `tasks.py` files using `@shared_task` decorator.

### Authentication

- Custom user model: `users.User` (email-based, no username field)
- Multiple auth backends: JWT, Django ModelBackend, django-allauth
- Social auth: Google OAuth, Microsoft, Keycloak (OpenID Connect)
- Custom adapters prevent public signup: `NoSignupAccountAdapter`, `NoNewSocialSignupAdapter`
- Frontend redirects configured via `FRONTEND_DOMAIN` env var

### Monitoring

- Prometheus metrics exposed at `/` (django-prometheus)
- Custom metrics in `main/metrics.py`
- Gateway monitoring via `DJANGO_IS_MONITORING_GATEWAYS` and `DJANGO_MONITOR_DISABLED_GATEWAYS`
- Database metrics updated every 60s via Celery task

## Configuration

### Environment Variables

Key variables (see `docker/.env.example` and `backend/.env`):
- Database: `POSTGRES_*` variables
- Redis: `REDIS_HOST`, `REDIS_PORT`
- RabbitMQ: `RABBIT_*` variables
- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- CORS: `DJANGO_CORS_ORIGIN_WHITELIST`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- SSO: `KEYCLOAK_*`, `GOOGLE_CLIENT_*`, `MS_CLIENT_*`
- Email: `EMAIL_*` variables
- Frontend: `FRONTEND_DOMAIN`, `VITE_*` variables

### Static & Media Files

- Static files: `/app/static/` (collected via `collectstatic`)
- Media files: `/app/media/` (user uploads)
- Both served through nginx proxy in production

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
1. **test** - Run Django tests with TimescaleDB and Redis
2. **build** - Build Docker image, push to GitLab registry (dev/latest tags)
3. **deploy** - Manual deployments to:
   - vesna (dev environment)
   - leto (dev environment)
   - grms (production via jump host)

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
3. Task runs in separate Celery worker process

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
- Single Django container runs 7 services via supervisord
- Gunicorn uses Uvicorn workers for ASGI support (WebSockets)
- Celery workers have separate database connection pool (`CONN_MAX_AGE=0`)
- Each process has isolated Prometheus metrics via multiprocess mode

### WebSocket Architecture
- Two separate WebSocket endpoints (v1 without auth, v2 with JWT)
- Demultiplexer routes messages by stream name to specific consumers
- Channel layer uses Redis with custom UUID JSON serializer
- JWT auth implemented as middleware wrapper (JWTAuthMiddlewareStack)

### Database Connection Management
- Web workers: 60s connection pooling (`CONN_MAX_AGE=60`)
- Celery workers: No pooling (`CONN_MAX_AGE=0`) to prevent stale connections
- Each process sets `PGAPPNAME` for PostgreSQL monitoring (grms-web, grms-celery)

## Deployment Notes

- The system requires TimescaleDB (PostgreSQL extension) for time-series data
- Nginx proxy handles SSL termination via Let's Encrypt
- Supervisord manages multiple processes in Django container
- Use `docker compose pull && docker compose down && docker compose up -d` to update
- Create tenant before first use via `create_tenant` command
- Monitor metrics at Prometheus endpoint (`/`) for production health
- Never write migrations manually - always use `./manage.py makemigrations`
- Before creating new features, check if similar patterns exist in the codebase