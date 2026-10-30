# navoke_backend/settings.py
import os
from pathlib import Path
import json
import base64
import firebase_admin
from firebase_admin import credentials
import dj_database_url
from django.core.exceptions import ImproperlyConfigured


try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None
    print("WARNING: python-dotenv not installed. Using system environment variables.")

# Загружаем .env (если есть)
try:
    load_dotenv()
except:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


def _required_env(name):
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(f'{name} must be set')
    return value


# Безопасность
DEBUG = os.getenv('DEBUG', 'False') == 'True'
SECRET_KEY = _required_env('DJANGO_SECRET_KEY')

# Firebase: в production обязателен FIREBASE_CREDENTIALS.
firebase_credentials = os.getenv('FIREBASE_CREDENTIALS')
if firebase_credentials:
    firebase_credentials_json = base64.b64decode(firebase_credentials)
    cred = credentials.Certificate(json.loads(firebase_credentials_json))
elif DEBUG and (BASE_DIR / 'serviceAccountKey.json').exists():
    # Удобство локальной разработки; файл в .gitignore.
    cred = credentials.Certificate(str(BASE_DIR / 'serviceAccountKey.json'))
else:
    raise ImproperlyConfigured(
        'FIREBASE_CREDENTIALS must be set when DEBUG=False'
    )

firebase_admin.initialize_app(cred)

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,10.0.2.2,192.168.1.0/24').split(',') + ['.railway.app', '.onrender.com', '.pythonanywhere.com']

# ✅ Убираем дублирование - оставляем только один раз
ROOT_URLCONF = 'navoke_backend.urls'

# Установленные приложения
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Сторонние
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Свои
    'core',
    'users',
    'products',
    'orders',
    'payments',
    'notifications',
]

# Раздел AUTH_USER_MODEL (ОБЯЗАТЕЛЬНО!)
AUTH_USER_MODEL = 'users.User'

# Промежуточные слои
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

APPEND_SLASH = True

# CORS настройки
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
]

DATABASE_URL = _required_env('DATABASE_URL')

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
    )
}

# Redis для кэширования
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# Настройки REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 1000,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT настройки
# navoke_backend/settings.py

# JWT настройки (увеличено время жизни)
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),      # ✅ Было 60 минут, стало 1 день
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # ✅ Было 1 день, стало 7 дней
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend'),
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # ✅ ДОБАВЛЕНО

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ✅ ДОБАВЛЕНО: WhiteNoise для медиа-файлов
WHITENOISE_MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
WHITENOISE_USE_FINDERS = True

# Celery настройки
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'frontend/pages')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Email для уведомлений
ADMIN_EMAIL = 'admin@navoke.ru'
DEFAULT_FROM_EMAIL = 'noreply@navoke.ru'

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Сайт для ссылок
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')

# ✅ Добавляем настройки для ЮKassa
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')
YOOKASSA_RETURN_URL = os.getenv('YOOKASSA_RETURN_URL', 'http://127.0.0.1:8000/order-success/')

# Официальные IP-диапазоны, с которых ЮKassa присылает HTTP-уведомления.
# Сверять при деплое: https://yookassa.ru/developers/using-api/webhooks#ip
YOOKASSA_TRUSTED_NETS = [
    net.strip()
    for net in os.getenv(
        'YOOKASSA_TRUSTED_NETS',
        '185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,'
        '77.75.154.128/25,77.75.156.11/32,77.75.156.35/32',
    ).split(',')
    if net.strip()
]

# True только за доверенным reverse-proxy, который сам перезаписывает
# X-Real-IP / X-Forwarded-For. Иначе заголовки можно подделать.
YOOKASSA_TRUST_PROXY = os.getenv('YOOKASSA_TRUST_PROXY', 'False').lower() == 'true'

# Добавьте в конец settings.py:

# CSRF настройки
CSRF_TRUSTED_ORIGINS = [
    'https://navoke.relaxdev.ru',
    'https://*.relaxdev.ru',
]

# CORS настройки
CORS_ALLOWED_ORIGINS = [
    'https://web-production-b0761.up.railway.app',
    'https://*.railway.app',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')



SPECTACULAR_SETTINGS = {
    'TITLE': 'НаVoke API',
    'DESCRIPTION': 'API для системы доставки еды НаVoke',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,  # не показывать саму схему в списке эндпоинтов
}

