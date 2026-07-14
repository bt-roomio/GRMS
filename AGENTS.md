# Project Handover Document

## GRMS Overview
GRMS (Guest Room Management System) is a Django-based IoT/smart hotel management platform designed for efficient guest service and property management. It leverages real-time communications and integrates various technologies for optimal performance.

### Key Features:
- Real-time WebSocket communication for device management.
- Multi-tenant architecture for handling multiple properties.
- Integration with IoT devices for smart hotel functionalities (e.g., access control).
- Guest check-in/check-out workflows and real-time monitoring.

## Technology Stack
- **Backend**: Django 5.0.4 with Django REST Framework.
- **Real-time Communication**: Django Channels (WebSockets), Daphne ASGI server.
- **Database**: PostgreSQL with TimescaleDB extension for time-series data.
- **Task Queue**: Celery with Redis as the broker.
- **Message Queue**: RabbitMQ for device communication and MQTT broker.
- **Authentication**: JWT (using djangorestframework-simplejwt), django-allauth for SSO integrations.
- **Monitoring**: Prometheus metrics through django-prometheus.

## Project Structure
### Apps Overview:
- **core**: Contains base models, shared utilities, and pagination functionalities.
- **users**: Implements custom user models and handles authentication.
- **main**: Central business logic, including tenant, room, and device management.
- **shuttle**: Handles real-time WebSocket communication and time-series data storage.
- **access_manager**: Integrates physical access control systems.
- **services**: Manages external service integrations.

### Multi-Tenant Design
The application supports a multi-tenant design, allowing isolation of data between different hotels. Each hotel operates as a separate tenant, and tenant-specific data is managed through a middleware.

## Development Setup
### Prerequisites:
- Ensure you have Docker and Docker Compose installed.
- Required environment variables should be defined in a `.env` file.

### Setting Up the Project:
1. Clone the repository.
2. Navigate to the back end and run:
   ```bash
   docker compose up --build -d
   ```
3. Run database migrations:
   ```bash
   docker exec -it django python manage.py migrate
   ```
4. Create a superuser if needed:
   ```bash
   docker exec -it django python manage.py createsuperuser
   ```

## Development Commands
- Run tests:
   ```bash
   docker exec -it django python manage.py test
   ```
- Format code:
   ```bash
   black .
   ```
- Check code style:
   ```bash
   ruff check .
   ```

## Key Considerations
- Ensure to follow existing coding standards and best practices.
- Regularly update documentation and keep dependencies up to date.
- Monitor system performance and address any bottlenecks promptly.

## Contact Information
For any inquiries or further information, please contact the development team lead at [email@example.com].
