#!/bin/bash
set -e
python manage.py collectstatic --noinput
python manage.py migrate --noinput

python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
# Ищем пользователя admin
user = User.objects.filter(username='admin').first()
if user:
    user.is_staff = True
    user.is_superuser = True
    user.role = 'admin'  # ✅ Меняем роль в приложении
    user.is_active = True
    user.save()
    print('Пользователь admin теперь администратор!')
else:
    User.objects.create_superuser('admin', 'admin@example.com', 'admin492357816')
"

# Запускаем Gunicorn
exec gunicorn navoke_backend.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload
