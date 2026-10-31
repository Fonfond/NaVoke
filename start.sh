#!/bin/bash
set -e
python manage.py collectstatic --noinput

# Repair django_migrations if orders.0009/0010 already exist in the schema.
python manage.py repair_order_migrations

# Apply all remaining migrations (products.0009, users.0004, ...).
python manage.py migrate --noinput

# Show SMTP configuration and connectivity in the startup logs.
python manage.py check_email || echo "WARNING: SMTP check failed"

# Запускаем Gunicorn
exec gunicorn navoke_backend.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload
