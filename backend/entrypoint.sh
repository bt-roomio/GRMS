#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate

echo "Running createcachetable..."
python manage.py createcachetable

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Supervisor..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
