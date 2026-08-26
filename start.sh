#!/bin/bash
python manage.py migrate
gunicorn navoke_backend.wsgi --bind 0.0.0.0:8000 --log-file -