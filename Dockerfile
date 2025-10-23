# Многоэтапная сборка для уменьшения размера образа
FROM python:3.11-slim as builder

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы конфигурации
COPY pyproject.toml ./

# Устанавливаем зависимости в виртуальное окружение
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

# Финальный образ
FROM python:3.11-slim

# Устанавливаем только необходимые системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем исходный код
COPY bot/ ./bot/
COPY llm/ ./llm/
COPY data/ ./data/

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Запуск бота
CMD ["python", "-m", "bot.main"]

