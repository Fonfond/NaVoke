FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Даём права на запись в папку staticfiles
RUN mkdir -p /app/staticfiles && chmod 777 /app/staticfiles

RUN chmod +x /app/start.sh

# Создаём пользователя (но оставляем root для записи)
# RUN adduser --disabled-password --no-create-home appuser
# USER appuser

EXPOSE 8000

CMD ["bash", "/app/start.sh"]
