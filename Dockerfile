# Используем официальный легкий образ Python [citation:4][citation:9]
FROM python:3.11-slim

# Отключаем запись .pyc файлов и буферизацию вывода (для логов) [citation:2][citation:4]
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию внутри контейнера [citation:7][citation:9]
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости [citation:4]
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем весь остальной код проекта в контейнер [citation:8]
COPY . /app/

# Создаем пользователя без прав root для безопасности [citation:2][citation:5]
RUN adduser --disabled-password --no-create-home appuser
USER appuser

# Указываем порт, который будет слушать приложение [citation:2][citation:4]
EXPOSE 8000

# Запускаем Gunicorn (производственный сервер) [citation:2][citation:3]
CMD ["gunicorn", "navoke_backend.wsgi:application", "--bind", "0.0.0.0:8000"]