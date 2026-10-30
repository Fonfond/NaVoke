#!/bin/sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn navoke_backend.wsgi:application --bind 0.0.0.0:8080
