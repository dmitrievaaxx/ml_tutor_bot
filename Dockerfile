# Используем официальный образ Python 3.11 slim для минимального размера
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости для оптимизации
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы конфигурации и исходный код
COPY pyproject.toml ./
COPY bot/ ./bot/
COPY llm/ ./llm/

# Устанавливаем uv и зависимости проекта с оптимизацией
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache . && \
    # Удаляем кэш pip для уменьшения размера
    pip cache purge && \
    # Удаляем временные файлы
    find /usr/local -name "*.pyc" -delete && \
    find /usr/local -name "__pycache__" -delete

# Создаем непривилегированного пользователя для безопасности
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Запуск бота
CMD ["python", "-m", "bot.main"]

