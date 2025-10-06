"""Обработчики команд и сообщений Telegram-бота"""

import logging
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from llm.client import get_llm_response


logger = logging.getLogger(__name__)


async def handle_start(message: Message):
    """
    Обработка команды /start
    
    Отправляет приветственное сообщение пользователю при первом запуске бота
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    
    logger.info(f"Команда /start от пользователя {user_id} (@{username})")
    
    await message.answer(
        "Привет! 👋\n\n"
        "Я простой эхо-бот. Отправьте мне любое сообщение, и я повторю его.\n\n"
        "Это базовая версия, скоро я научусь большему!"
    )


async def handle_message(message: Message):
    """
    Обработка текстовых сообщений через LLM
    
    Функция:
    1. Получает сообщение от пользователя
    2. Отправляет его в LLM для обработки
    3. Возвращает ответ пользователю
    4. Обрабатывает ошибки и логирует события
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {text}")
    
    try:
        # Получение ответа от LLM
        response = await get_llm_response(text)
        
        # Отправка ответа пользователю
        await message.answer(response)
        
    except ValueError as e:
        # Ошибка конфигурации (например, отсутствует API ключ)
        logger.error(f"Ошибка конфигурации: {e}")
        await message.answer(
            "⚠️ Бот не настроен. Обратитесь к администратору."
        )
        
    except Exception as e:
        # Общая ошибка при обработке
        logger.error(f"Ошибка при обработке сообщения: {type(e).__name__}: {e}")
        await message.answer(
            "😔 Извините, произошла ошибка при обработке вашего сообщения. "
            "Попробуйте еще раз или напишите позже."
        )


def register_handlers(dp: Dispatcher):
    """
    Регистрация всех обработчиков сообщений в диспетчере
    
    Порядок регистрации важен: более специфичные обработчики 
    (например, команды) должны регистрироваться раньше общих
    
    Args:
        dp: Диспетчер aiogram для регистрации обработчиков
    """
    # Обработчик команды /start
    dp.message.register(handle_start, Command("start"))
    
    # Обработчик всех остальных текстовых сообщений через LLM
    dp.message.register(handle_message)

