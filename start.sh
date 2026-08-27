#!/bin/bash
python manage.py migrate
RUN python manage.py collectstatic --no-input
gunicorn navoke_backend.wsgi --bind 0.0.0.0:8000 --timeout 120 --workers 2 --preload --log-file -
