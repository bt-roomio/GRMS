#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

WORKERS="${GUNICORN_WORKERS:-$(python -c 'import os; print(2 * os.cpu_count() + 1)')}"

# Gunicorn counts every WebSocket connection as a request, and a worker restart on
# --max-requests drops all of its sockets at once. For an ASGI worker with long-lived
# connections scheduled restarts are disabled (0); enable only to contain memory leaks.
MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-0}"

exec gunicorn config.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WORKERS}" \
  --worker-connections "${GUNICORN_WORKER_CONNECTIONS:-1000}" \
  --timeout "${GUNICORN_TIMEOUT:-30}" \
  --keep-alive 5 \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --max-requests "${MAX_REQUESTS}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
  --bind 0.0.0.0:8000
