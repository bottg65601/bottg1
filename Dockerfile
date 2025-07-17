FROM python:3.11-slim as builder

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

WORKDIR /app

# Копируем установленные зависимости из builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Убедимся, что скрипты в .local доступны
ENV PATH=/root/.local/bin:$PATH

# Рекомендуемые настройки для Python в контейнере
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Указываем порт, который будет использовать приложение
EXPOSE 8080

CMD ["python", "main.py"]