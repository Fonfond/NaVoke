#!/bin/bash
set -e
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Создаём суперпользователя ПЕРЕД запуском Gunicorn
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin492357816')
print('Суперпользователь создан!')
"

# Запускаем Gunicorn
exec gunicorn navoke_backend.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload
