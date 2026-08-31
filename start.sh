#!/bin/bash
set -e
python manage.py collectstatic --noinput
python manage.py migrate --noinput



# Запускаем Gunicorn
exec gunicorn navoke_backend.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload
