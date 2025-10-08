# Используем официальный образ Python 3.11 slim для минимального размера
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы конфигурации и исходный код
COPY pyproject.toml ./
COPY bot/ ./bot/
COPY llm/ ./llm/

# Устанавливаем uv и зависимости проекта
# --no-cache-dir уменьшает размер образа
RUN pip install --no-cache-dir uv && \
    uv pip install --system .

# Создаем непривилегированного пользователя для безопасности
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Запуск бота
CMD ["python", "-m", "bot.main"]

