# navoke_backend/settings.py
import os
from pathlib import Path
import json
import base64
import firebase_admin
from firebase_admin import credentials
import dj_database_url


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

# ✅ ИСПРАВЛЕНО: Загрузка Firebase credentials
if os.environ.get('FIREBASE_CREDENTIALS'):
    # Декодируем base64 строку в JSON
    firebase_credentials_json = base64.b64decode(os.environ['FIREBASE_CREDENTIALS'])
    cred = credentials.Certificate(json.loads(firebase_credentials_json))
else:
    # Если переменной нет — используем локальный файл
    cred = credentials.Certificate(os.path.join(BASE_DIR, 'serviceAccountKey.json'))

firebase_admin.initialize_app(cred)

# Безопасность
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
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
    'drf_yasg',
    
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

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
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
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY', '')
YOOKASSA_RETURN_URL = os.getenv('YOOKASSA_RETURN_URL', 'http://127.0.0.1:8000/order-success/')

# Добавьте в конец settings.py:

# CSRF настройки
CSRF_TRUSTED_ORIGINS = [
    'https://web-production-b0761.up.railway.app',
    'https://*.railway.app',
]

# CORS настройки
CORS_ALLOWED_ORIGINS = [
    'https://web-production-b0761.up.railway.app',
    'https://*.railway.app',
]
