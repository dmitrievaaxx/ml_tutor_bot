"""Обработчики команд и сообщений Telegram-бота"""

import logging
import random
import base64
from aiogram import Dispatcher, F
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

# Сообщения для индикатора "модель думает"
THINKING_MESSAGES = [
    "⏳ Секунду...",
    "💭 Минутку...",
    "🔍 Ищу лучший ответ для тебя...",
    "💭 Думаю над ответом...",
    "💡 Формулирую понятное объяснение...",
    "🎓 Готовлю подробный ответ...",
    "📚 Подбираю лучшие примеры...",
]


async def handle_start(message: Message):
    """
    Обработка команды /start
    
    Автоматически устанавливает базовый уровень и отправляет приветственное сообщение
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /start от пользователя {user_id} (@{username})")
    
    # Очистка истории при старте (начинаем с чистого листа)
    clear_dialog(chat_id)
    
    # Автоматически устанавливаем базовый уровень
    from bot.dialog import add_user_message, add_assistant_message
    add_user_message(chat_id, "Базовый")
    logger.info(f"Автоматически установлен базовый уровень для пользователя {user_id}")
    
    # Отправляем приветственное сообщение с уведомлением об автоматическом выборе уровня
    welcome_msg = get_welcome_message("Базовый")
    level_notification = "📊 Автоматически выбран базовый уровень. Используй /level для смены уровня."
    
    await message.answer(
        "Привет!👋\n\n"
        f"{level_notification}\n\n"
        f"{welcome_msg}"
    )
    
    # Сохраняем приветственное сообщение в историю
    add_assistant_message(chat_id, welcome_msg)


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
    
    # Если уровень не установлен, автоматически устанавливаем базовый
    if not current_level:
        logger.info(f"Уровень не установлен для пользователя {user_id}, устанавливаем базовый")
        add_user_message(chat_id, "Базовый")
        current_level = "Базовый"
    
    level_emojis = {
        'Новичок': '🟢',
        'Базовый': '🟡', 
        'Продвинутый': '🔴'
    }
    emoji = level_emojis.get(current_level, '📊')
    
    status_message = f"{emoji} Текущий уровень: {current_level}\n\n"
    
    if current_level == 'Новичок':
        status_message += "Ты изучаешь ML с нуля простыми словами😊"
    elif current_level == 'Базовый':
        status_message += "Ты изучаешь ML с техническими деталями📚"
    else:  # Продвинутый
        status_message += "Ты изучаешь продвинутые темы ML🔬"
    
    status_message += "\n\nИспользуй /level чтобы изменить уровень"
    
    await message.answer(status_message)


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
    
    # Проверяем, не является ли это сообщением с медиа
    # Проверяем все возможные способы определения медиа
    has_photo = (
        (hasattr(message, 'photo') and message.photo) or
        (hasattr(message, 'document') and message.document and message.document.mime_type and message.document.mime_type.startswith('image/')) or
        (hasattr(message, 'animation') and message.animation) or
        (hasattr(message, 'video') and message.video)
    )
    
    # Дополнительная проверка для документов с изображениями
    if hasattr(message, 'document') and message.document and message.document.mime_type:
        if message.document.mime_type.startswith('image/'):
            has_photo = True
    
    if has_photo:
        logger.info(f"⚠️ ОШИБКА: Сообщение с медиа попало в общий обработчик!")
        logger.info(f"📷 Есть photo: {hasattr(message, 'photo') and message.photo}")
        logger.info(f"📄 Есть document: {hasattr(message, 'document') and message.document}")
        if hasattr(message, 'photo') and message.photo:
            logger.info(f"📷 Количество фото: {len(message.photo)}")
            logger.info(f"📷 Размеры фото: {[f'{p.width}x{p.height}' for p in message.photo]}")
        # Не обрабатываем медиа в общем обработчике
        return
    
    logger.info(f"📝 ОБЩИЙ ОБРАБОТЧИК СООБЩЕНИЙ ВЫЗВАН! Пользователь {user_id}, текст: '{text}'")
    logger.info(f"🔍 Тип сообщения: {type(message).__name__}")
    logger.info(f"📷 Есть ли фото: {hasattr(message, 'photo') and message.photo is not None}")
    
    try:
        # Показываем индикатор "печатает..." пока LLM думает
        await message.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Отправляем случайное сообщение о том, что модель думает
        thinking_msg = await message.answer(random.choice(THINKING_MESSAGES))
        
        # Добавление сообщения пользователя в историю
        add_user_message(chat_id, text)
        
        # Получение полной истории диалога
        dialog_history = get_dialog_history(chat_id)
        logger.info(f"История диалога получена: {len(dialog_history)} сообщений")
        
        # Проверяем и устанавливаем уровень пользователя, если не установлен
        from bot.dialog import extract_user_level
        user_level = extract_user_level(chat_id)
        if not user_level:
            logger.info(f"Уровень не установлен для пользователя {user_id}, устанавливаем базовый")
            add_user_message(chat_id, "Базовый")
            user_level = "Базовый"
        logger.info(f"Уровень пользователя {user_id}: {user_level}")
        
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


async def handle_photo(message: Message):
    """
    Обработка фотографий с использованием Vision API
    
    Функция:
    1. Получает фото от пользователя
    2. Показывает индикатор обработки изображения
    3. Скачивает фото наилучшего качества из Telegram
    4. Конвертирует в base64 для передачи в Vision API
    5. Добавляет подпись к фото в историю диалога
    6. Отправляет запрос в Vision API с контекстом
    7. Возвращает ответ пользователю
    
    Args:
        message: Объект сообщения с фото
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    caption = message.caption or "Что на этом изображении?"
    
    logger.info(f"🎯 ОБРАБОТЧИК ФОТО ВЫЗВАН! Пользователь {user_id}, чат {chat_id}, подпись: {caption}")
    logger.info(f"🔍 Тип сообщения: {type(message).__name__}")
    logger.info(f"🔍 Есть ли текст: {message.text is not None}")
    logger.info(f"🔍 Текст сообщения: '{message.text}'")
    
    # Определяем тип медиа
    if message.photo:
        logger.info(f"📷 Обычное фото - количество: {len(message.photo)}")
        logger.info(f"📷 Размеры фото: {[f'{p.width}x{p.height}' for p in message.photo]}")
        media_type = "photo"
    elif message.document:
        logger.info(f"📄 Документ-изображение: {message.document.file_name}")
        logger.info(f"📄 MIME тип: {message.document.mime_type}")
        media_type = "document"
    else:
        logger.info(f"❓ Неизвестный тип медиа")
        media_type = "unknown"
    
    try:
        # Показываем индикатор обработки изображения
        await message.bot.send_chat_action(chat_id=chat_id, action="typing")
        thinking_msg = await message.answer("🖼️ Анализирую изображение...")
        
        # Получаем файл в зависимости от типа медиа
        if message.photo:
            # Обычное фото - берем наилучшего качества (последний элемент в списке)
            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
        elif message.document:
            # Документ-изображение
            file = await message.bot.get_file(message.document.file_id)
        else:
            raise ValueError("Неизвестный тип медиа")
        
        # Скачиваем изображение
        photo_bytes = await message.bot.download_file(file.file_path)
        
        # Конвертируем в base64
        image_data = photo_bytes.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Определяем формат изображения
        if message.document and message.document.mime_type:
            # Для документов используем MIME тип
            if 'jpeg' in message.document.mime_type or 'jpg' in message.document.mime_type:
                image_format = "jpeg"
            elif 'png' in message.document.mime_type:
                image_format = "png"
            elif 'gif' in message.document.mime_type:
                image_format = "gif"
            elif 'webp' in message.document.mime_type:
                image_format = "webp"
            else:
                image_format = "jpeg"  # fallback
        else:
            # Для обычных фото определяем по первым байтам
            if image_data.startswith(b'\xff\xd8\xff'):
                image_format = "jpeg"
            elif image_data.startswith(b'\x89PNG'):
                image_format = "png"
            elif image_data.startswith(b'GIF'):
                image_format = "gif"
            else:
                image_format = "jpeg"  # fallback
        
        # Проверяем размер изображения (не более 20MB для Vision API)
        image_size_mb = len(image_data) / (1024 * 1024)
        logger.info(f"Изображение конвертировано в base64: {len(image_base64)} символов, размер: {image_size_mb:.2f} MB, формат: {image_format}")
        
        if image_size_mb > 20:
            await thinking_msg.delete()
            await message.answer(
                "Извините, изображение слишком большое (более 20MB). "
                "Пожалуйста, сожмите изображение и попробуйте еще раз."
            )
            return
        
        # Добавляем сообщение пользователя с подписью в историю
        add_user_message(chat_id, caption)
        
        # Получаем историю диалога
        dialog_history = get_dialog_history(chat_id)
        logger.info(f"История диалога получена: {len(dialog_history)} сообщений")
        
        # Проверяем и устанавливаем уровень пользователя, если не установлен
        from bot.dialog import extract_user_level
        user_level = extract_user_level(chat_id)
        if not user_level:
            logger.info(f"Уровень не установлен для пользователя {user_id}, устанавливаем базовый")
            add_user_message(chat_id, "Базовый")
            user_level = "Базовый"
        logger.info(f"Уровень пользователя {user_id}: {user_level}")
        
        # Получаем ответ от Vision API
        from llm.vision_client import get_vision_response
        logger.info("Начинаем запрос к Vision API...")
        response = await get_vision_response(dialog_history, image_base64, image_format)
        logger.info(f"Ответ от Vision API получен: {len(response) if response else 0} символов")
        
        # Проверка на пустой ответ
        if not response or response.strip() == "":
            response = "Извините, я не смог проанализировать изображение. Возможные причины:\n\n• Изображение слишком большое или в неподдерживаемом формате\n• Проблемы с Vision API\n• Превышен лимит запросов\n\nПопробуйте отправить другое фото в формате JPEG или PNG."
        
        # Очистка ответа от форматирования
        cleaned_response = clean_response(response)
        logger.info(f"Ответ очищен: {len(response)} -> {len(cleaned_response)} символов")
        
        # Сохранение ответа ассистента в историю
        add_assistant_message(chat_id, cleaned_response)
        
        # Удаляем сообщение об обработке
        await thinking_msg.delete()
        
        # Отправляем ответ пользователю
        await message.answer(cleaned_response)
        
    except ValueError as e:
        # Ошибка конфигурации (например, отсутствует API ключ)
        logger.error(f"Ошибка конфигурации Vision API: {e}")
        try:
            await thinking_msg.delete()
        except:
            pass
        await message.answer(
            "⚠️ Vision API не настроен. Обратитесь к администратору."
        )
        
    except Exception as e:
        # Общая ошибка при обработке изображения
        logger.error(f"Ошибка при обработке фото: {type(e).__name__}: {e}")
        try:
            await thinking_msg.delete()
        except:
            pass
        await message.answer(
            "😔 Извините, произошла ошибка при обработке изображения. "
            "Попробуйте отправить другое фото или обратитесь позже."
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
            
            if is_first:
                # Первый выбор уровня - показываем "Выбран уровень" + приветствие
                await callback_query.message.edit_text(
                    f"✅ Выбран уровень: {level}",
                    reply_markup=None
                )
                welcome_msg = get_welcome_message(level)
                await callback_query.message.answer(welcome_msg)
                add_assistant_message(chat_id, welcome_msg)
            else:
                # Смена уровня - показываем только финальное сообщение
                await callback_query.message.edit_text(
                    f"🔄 Уровень изменен на '{level}'. Задавайте свои вопросы!",
                    reply_markup=None
                )
                add_assistant_message(chat_id, f"🔄 Уровень изменен на '{level}'. Задавайте свои вопросы!")
            
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
    
    # Обработчик нажатий на кнопки выбора уровня
    dp.callback_query.register(handle_level_selection)
    
    # Обработчик фотографий и документов с изображениями (должен быть перед общим обработчиком сообщений)
    # Регистрируем отдельно для каждого типа медиа
    dp.message.register(handle_photo, F.photo)
    dp.message.register(handle_photo, F.document.has(F.mime_type.startswith('image/')))
    
    # Обработчик всех остальных текстовых сообщений через LLM с контекстом
    dp.message.register(handle_message)
