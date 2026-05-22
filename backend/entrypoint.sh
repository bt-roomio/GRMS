#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

WORKERS="${GUNICORN_WORKERS:-$(python -c 'import os; print(2 * os.cpu_count() + 1)')}"

exec gunicorn config.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WORKERS}" \
  --worker-connections "${GUNICORN_WORKER_CONNECTIONS:-1000}" \
  --timeout "${GUNICORN_TIMEOUT:-30}" \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --bind 0.0.0.0:8000
