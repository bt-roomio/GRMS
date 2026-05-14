#!/bin/sh
set -e

python manage.py migrate
python manage.py collectstatic --noinput

exec gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers "${GUNICORN_WORKERS:-4}" --worker-connections "${GUNICORN_WORKER_CONNECTIONS:-1000}" --timeout "${GUNICORN_TIMEOUT:-30}" --keepalive 5 --max-requests 1000 --max-requests-jitter 100 --bind 0.0.0.0:8000
