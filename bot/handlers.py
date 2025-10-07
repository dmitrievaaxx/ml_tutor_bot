"""Обработчики команд и сообщений Telegram-бота"""

import logging
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from llm.client import get_llm_response
from bot.dialog import (
    get_dialog_history,
    add_user_message,
    add_assistant_message,
    clear_dialog,
    get_dialog_stats,
    clean_response,
    is_first_level_selection,
    get_welcome_message
)


logger = logging.getLogger(__name__)


async def handle_start(message: Message):
    """
    Обработка команды /start
    
    Отправляет приветственное сообщение с кнопками выбора уровня
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /start от пользователя {user_id} (@{username})")
    
    # Очистка истории при старте (начинаем с чистого листа)
    clear_dialog(chat_id)
    
    # Создаем кнопки для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Новичок", callback_data="level_novice")],
        [InlineKeyboardButton(text="🟡 Базовый", callback_data="level_basic")],
        [InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")]
    ])
    
    await message.answer(
        "Привет!👋\n\n"
        "Я помогу тебе разобраться в машинном обучении, нейросетях и NLP — от основ до продвинутых концепций.\n\n"
        "📊 Выбери свой уровень знаний:",
        reply_markup=keyboard
           )


async def handle_level(message: Message):
    """
    Обработка команды /level
    
    Позволяет пользователю изменить свой уровень знаний
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /level от пользователя {user_id} (@{username})")
    
    # Создаем кнопки для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Новичок", callback_data="level_novice")],
        [InlineKeyboardButton(text="🟡 Базовый", callback_data="level_basic")],
        [InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")]
    ])
    
    await message.answer(
        "📊 Выбери новый уровень знаний:",
        reply_markup=keyboard
    )


async def handle_status(message: Message):
    """
    Обработка команды /status
    
    Показывает текущий уровень знаний пользователя
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /status от пользователя {user_id} (@{username})")
    
    # Получаем текущий уровень пользователя
    from bot.dialog import extract_user_level
    current_level = extract_user_level(chat_id)
    
    if current_level:
        level_emojis = {
            'Новичок': '🟢',
            'Базовый': '🟡', 
            'Продвинутый': '🔴'
        }
        emoji = level_emojis.get(current_level, '📊')
        
        status_message = f"{emoji} **Текущий уровень:** {current_level}\n\n"
        
        if current_level == 'Новичок':
            status_message += "Ты изучаешь ML с нуля простыми словами 😊"
        elif current_level == 'Базовый':
            status_message += "Ты изучаешь ML с техническими деталями 📚"
        else:  # Продвинутый
            status_message += "Ты изучаешь продвинутые темы ML 🔬"
        
        status_message += "\n\nИспользуй /level чтобы изменить уровень"
    else:
        status_message = "📊 Уровень знаний не выбран\n\nИспользуй /start чтобы выбрать уровень"
    
    await message.answer(status_message)


async def handle_clear(message: Message):
    """
    Обработка команды /clear
    
    Очищает историю диалога для начала беседы с чистого листа
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /clear от пользователя {user_id}")
    
    # Получение статистики перед очисткой
    stats = get_dialog_stats(chat_id)
    
    # Очистка истории диалога
    clear_dialog(chat_id)
    
    await message.answer(
        f"🗑️ История диалога очищена!\n\n"
        f"Было сообщений: {stats['user']} от вас, {stats['assistant']} от меня.\n\n"
        f"Начнём сначала! Задавай свои вопросы о машинном обучении 😊"
    )


async def handle_message(message: Message):
    """
    Обработка текстовых сообщений через LLM с сохранением контекста
    
    Функция:
    1. Получает сообщение от пользователя
    2. Показывает индикатор "печатает..." пока модель думает
    3. Добавляет сообщение в историю диалога
    4. Отправляет историю в LLM для получения контекстного ответа
    5. Сохраняет ответ в историю
    6. Отправляет ответ пользователю с форматированием Markdown
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {text}")
    
    try:
        # Показываем индикатор "печатает..." пока LLM думает
        await message.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Отправляем сообщение о том, что модель думает
        thinking_msg = await message.answer("🤔 Модель думает над ответом...")
        
        # Добавление сообщения пользователя в историю
        add_user_message(chat_id, text)
        
        # Получение полной истории диалога
        dialog_history = get_dialog_history(chat_id)
        logger.info(f"История диалога получена: {len(dialog_history)} сообщений")
        
        # Получение ответа от LLM с учетом контекста диалога
        logger.info("Начинаем запрос к LLM...")
        response = await get_llm_response(dialog_history)
        logger.info(f"Ответ от LLM получен: {len(response) if response else 0} символов")
        
        # Проверка на пустой ответ
        if not response or response.strip() == "":
            response = "Извините, я не смог сгенерировать ответ на ваш вопрос. Попробуйте переформулировать вопрос или задайте другой."
        
        # Очистка ответа от форматирования и иностранных слов
        cleaned_response = clean_response(response)
        logger.info(f"Ответ очищен: {len(response)} -> {len(cleaned_response)} символов")
        
        # Сохранение ответа ассистента в историю
        add_assistant_message(chat_id, cleaned_response)
        
        # Удаляем сообщение "модель думает"
        await thinking_msg.delete()
        
        # Отправка ответа пользователю как обычный текст без форматирования
        await message.answer(cleaned_response)
        
    except ValueError as e:
        # Ошибка конфигурации (например, отсутствует API ключ)
        logger.error(f"Ошибка конфигурации: {e}")
        try:
            await thinking_msg.delete()
        except:
            pass
        await message.answer(
            "⚠️ Бот не настроен. Обратитесь к администратору."
        )
        
    except Exception as e:
        # Общая ошибка при обработке
        logger.error(f"Ошибка при обработке сообщения: {type(e).__name__}: {e}")
        try:
            await thinking_msg.delete()
        except:
            pass
        await message.answer(
            "😔 Извините, произошла ошибка при обработке вашего сообщения. "
            "Попробуйте еще раз или напишите позже."
        )


async def handle_level_selection(callback_query: CallbackQuery):
    """
    Обработка выбора уровня знаний через кнопки
    
    Args:
        callback_query: Объект callback query от нажатия кнопки
    """
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    
    # Определяем уровень по callback_data
    level_mapping = {
        "level_novice": "Новичок",
        "level_basic": "Базовый", 
        "level_advanced": "Продвинутый"
    }
    
    level = level_mapping.get(callback_query.data)
    
    if level:
        logger.info(f"Выбран уровень {level} пользователем {user_id} (@{username})")
        
        # Добавляем сообщение о выборе уровня в историю
        add_user_message(chat_id, level)
        
        # Получаем историю диалога
        dialog_history = get_dialog_history(chat_id)
        
        try:
            # Определяем, первый ли это выбор уровня
            is_first = is_first_level_selection(chat_id)
            
            # Убираем кнопки после выбора уровня
            await callback_query.message.edit_text(
                f"✅ Выбран уровень: {level}",
                reply_markup=None
            )
            
            if is_first:
                # Первый выбор уровня - показываем приветствие с темами
                welcome_msg = get_welcome_message(level)
                await callback_query.message.answer(welcome_msg)
                add_assistant_message(chat_id, welcome_msg)
            else:
                # Смена уровня - показываем простое сообщение без LLM
                level_change_msg = f"✅ Уровень знаний изменен на '{level}'. Задавайте свои вопросы!"
                await callback_query.message.answer(level_change_msg)
                add_assistant_message(chat_id, level_change_msg)
            
            # Подтверждаем callback (убираем "часики" с кнопки)
            await callback_query.answer()
                
        except ValueError as e:
            logger.error(f"Ошибка конфигурации: {e}")
            await callback_query.message.answer(
                "⚠️ Бот не настроен. Обратитесь к администратору."
            )
            await callback_query.answer()
        except Exception as e:
            logger.error(f"Ошибка при обработке выбора уровня: {type(e).__name__}: {e}")
            await callback_query.message.answer(
                "😔 Извините, произошла ошибка. Попробуйте еще раз."
            )
            await callback_query.answer()
    else:
        await callback_query.answer("Неизвестный уровень")


def register_handlers(dp: Dispatcher):
    """
    Регистрация всех обработчиков сообщений в диспетчере
    
    Порядок регистрации важен: более специфичные обработчики 
    (например, команды) должны регистрироваться раньше общих
    
    Args:
        dp: Диспетчер aiogram для регистрации обработчиков
    """
    # Обработчик команды /start - приветствие и сброс диалога
    dp.message.register(handle_start, Command("start"))
    
    # Обработчик команды /level - смена уровня знаний
    dp.message.register(handle_level, Command("level"))
    
    # Обработчик команды /status - показ текущего уровня
    dp.message.register(handle_status, Command("status"))
    
    # Обработчик команды /clear - очистка истории диалога
    dp.message.register(handle_clear, Command("clear"))
    
    # Обработчик нажатий на кнопки выбора уровня
    dp.callback_query.register(handle_level_selection)
    
    # Обработчик всех остальных текстовых сообщений через LLM с контекстом
    dp.message.register(handle_message)
