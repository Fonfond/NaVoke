#!/bin/bash
python manage.py migrate
gunicorn navoke_backend.wsgi --bind 0.0.0.0:8000 --timeout 120 --workers 2 --preload --log-file -
