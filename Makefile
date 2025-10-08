.PHONY: help install install-dev test run docker-build docker-run docker-stop clean

# Цвета для вывода
GREEN := \033[0;32m
NC := \033[0m

help:
	@echo "$(GREEN)Доступные команды:$(NC)"
	@echo "  make install      - Установка зависимостей"
	@echo "  make install-dev  - Установка зависимостей для разработки"
	@echo "  make test         - Запуск тестов"
	@echo "  make run          - Запуск бота локально"
	@echo "  make docker-build - Сборка Docker образа"
	@echo "  make docker-run   - Запуск бота в Docker"
	@echo "  make docker-stop  - Остановка Docker контейнера"
	@echo "  make clean        - Очистка временных файлов"

install:
	@echo "$(GREEN)Установка зависимостей...$(NC)"
	uv pip install -e .

install-dev:
	@echo "$(GREEN)Установка зависимостей для разработки...$(NC)"
	uv pip install -e ".[dev]"

test:
	@echo "$(GREEN)Запуск тестов...$(NC)"
	pytest tests/ -v

run:
	@echo "$(GREEN)Запуск бота...$(NC)"
	python -m bot.main

docker-build:
	@echo "$(GREEN)Сборка Docker образа...$(NC)"
	docker build -t ml-tutor-bot:latest .

docker-run:
	@echo "$(GREEN)Запуск бота в Docker...$(NC)"
	docker run -d --name ml-tutor-bot --env-file .env ml-tutor-bot:latest

docker-stop:
	@echo "$(GREEN)Остановка Docker контейнера...$(NC)"
	docker stop ml-tutor-bot || true
	docker rm ml-tutor-bot || true

clean:
	@echo "$(GREEN)Очистка временных файлов...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

