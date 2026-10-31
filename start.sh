#!/bin/sh

python manage.py migrate orders 0008 --fake || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn navoke_backend.wsgi:application --bind 0.0.0.0:8080
