FROM python:3.11-slim

WORKDIR /app

# Сначала копируем зависимости для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем копируем остальные файлы
COPY . .

# Запуск с логированием
CMD ["python", "-u", "main.py"]