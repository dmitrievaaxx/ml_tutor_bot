"""Главный модуль для запуска Telegram-бота"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.handlers import register_handlers
from bot.database import Database


# Загрузка переменных окружения из .env файла
load_dotenv()


def setup_logging():
    """Настройка логирования приложения"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def setup_bot_commands(bot: Bot):
    """
    Настройка команд бота для отображения в меню
    
    Args:
        bot: Объект бота для установки команд
    """
    commands = [
        BotCommand(command="start", description="🚀 Начать обучение ML"),
        BotCommand(command="learn", description="📚 Выбрать курс"),
        BotCommand(command="level", description="📊 Сменить уровень знаний"),
        BotCommand(command="status", description="ℹ️ Показать текущий уровень"),
        BotCommand(command="clear", description="🗑️ Очистить прогресс курсов"),
        BotCommand(command="help", description="❓ Справка по командам"),
    ]
    
    await bot.set_my_commands(commands)
    logger = logging.getLogger(__name__)
    logger.info("Команды бота настроены")


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
    
    # Отладочная информация о переменных окружения
    logger.info("=== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===")
    logger.info(f"TELEGRAM_BOT_TOKEN: {'ДА' if os.getenv('TELEGRAM_BOT_TOKEN') else 'НЕТ'}")
    logger.info(f"OPENROUTER_API_KEY: {'ДА' if os.getenv('OPENROUTER_API_KEY') else 'НЕТ'}")
    logger.info(f"HUGGINGFACE_API_TOKEN: {'ДА' if os.getenv('HUGGINGFACE_API_TOKEN') else 'НЕТ'}")
    logger.info(f"LLM_MODEL: {os.getenv('LLM_MODEL', 'НЕ УСТАНОВЛЕН')}")
    logger.info(f"VISION_MODEL: {os.getenv('VISION_MODEL', 'НЕ УСТАНОВЛЕН')}")
    logger.info("=====================================")
    
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
    
    # Настройка команд бота для отображения в меню
    await setup_bot_commands(bot)
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    db = Database()
    
    # Проверяем, есть ли курс Math, если нет - загружаем
    math_course = db.get_course(1)
    if not math_course:
        logger.info("Загрузка курса Math...")
        try:
            from pathlib import Path
            json_path = Path(__file__).parent.parent / "data" / "math_course.json"
            if json_path.exists():
                course_id = db.load_course_from_json(str(json_path))
                logger.info(f"Курс Math загружен с ID: {course_id}")
            else:
                logger.warning("Файл курса Math не найден")
        except Exception as e:
            logger.error(f"Ошибка загрузки курса: {e}")
    
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

