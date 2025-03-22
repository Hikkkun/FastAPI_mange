FROM python:3.10-slim-bullseye

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код и шаблоны
COPY ./app /app