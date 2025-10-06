"""Главный модуль для запуска Telegram-бота"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from bot.handlers import register_handlers


# Загрузка переменных окружения из .env файла
load_dotenv()


def setup_logging():
    """Настройка логирования приложения"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def main():
    """
    Основная функция запуска бота
    
    Функция выполняет:
    1. Загрузку конфигурации из переменных окружения
    2. Инициализацию бота и диспетчера
    3. Регистрацию обработчиков сообщений
    4. Запуск polling для получения обновлений
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Получение токена из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN не найден в переменных окружения. "
            "Проверьте файл .env или установите переменную окружения."
        )
    
    # Инициализация бота и диспетчера
    bot = Bot(token=token)
    dp = Dispatcher()
    
    # Регистрация обработчиков команд и сообщений
    register_handlers(dp)
    
    logger.info("Бот запущен и готов к работе")
    
    try:
        # Запуск polling - бот начинает получать обновления от Telegram
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
        raise
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == '__main__':
    asyncio.run(main())

