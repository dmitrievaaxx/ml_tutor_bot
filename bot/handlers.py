"""Обработчики команд и сообщений Telegram-бота"""

import logging
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message


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


async def handle_echo(message: Message):
    """
    Эхо-обработчик всех текстовых сообщений
    
    Повторяет текст сообщения, отправленного пользователем
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    text = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {text}")
    
    # Отправка эхо-ответа
    await message.answer(text)


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
    
    # Обработчик всех остальных текстовых сообщений
    dp.message.register(handle_echo)

