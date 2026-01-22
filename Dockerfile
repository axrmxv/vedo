# Базовый образ Python 3.14
FROM python:3.14-slim

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY backend/ ./backend/
COPY static/ ./static/

# Создание необходимых директорий
RUN mkdir -p storage logs

# Открытие порта
EXPOSE 8035

# Запуск приложения
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8035"]
