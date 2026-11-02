#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# An async worker serves many connections at once, so one per core is enough
# (the 2*CPU+1 rule is for sync workers). nproc ignores the cgroup CPU quota:
# set GUNICORN_WORKERS explicitly in production.
WORKERS="${GUNICORN_WORKERS:-$(nproc)}"

# Gunicorn counts every WebSocket connection as a request, and a worker restart on
# --max-requests drops all of its sockets at once. For an ASGI worker with long-lived
# connections scheduled restarts are disabled (0); enable only to contain memory leaks.
MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-0}"
if [ "${MAX_REQUESTS}" -gt 0 ]; then
  JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-$((MAX_REQUESTS / 10))}"
else
  JITTER=0
fi

# Keep below stop_grace_period of the backend service, or Docker sends SIGKILL first.
exec gunicorn config.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WORKERS}" \
  --timeout "${GUNICORN_TIMEOUT:-30}" \
  --keep-alive 5 \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --max-requests "${MAX_REQUESTS}" \
  --max-requests-jitter "${JITTER}" \
  --bind 0.0.0.0:8000
