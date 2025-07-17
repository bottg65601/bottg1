# Этап сборки зависимостей
FROM python:3.11-slim as builder

WORKDIR /app

# Установка системных зависимостей (если нужны)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

WORKDIR /app

# Копируем только необходимое из builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/requirements.txt .

# Копируем исходный код
COPY . .

# Настройки окружения
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1

# Оптимизация для production
RUN find /usr/local -type d -name '__pycache__' -exec rm -rf {} + && \
    find /usr/local -type f -name '*.pyc' -delete

# Порт приложения (для документации)
EXPOSE 8080

# Команда запуска (выберите одну из вариантов)
# Для long-polling бота:
CMD ["python", "main.py"]

# Для вебхук-бота с Gunicorn:
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--worker-class", "gevent", "--workers", "1", "app:app"]