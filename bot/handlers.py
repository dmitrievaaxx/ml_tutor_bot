"""Обработчики команд и сообщений Telegram-бота"""

import logging
import random
import base64
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from llm.client import get_llm_response
from llm.speech_client import transcribe_audio_data
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
        "Я помогу тебе разобраться в машинном обучении, нейросетях и NLP — от основ до продвинутых концепций. Задавай вопросы текстом или присылай изображения с формулами, схемами и диаграммами — я всё объясню!\n\n"
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
        
        status_message = f"{emoji} Текущий уровень: {current_level}\n\nИспользуй /level чтобы изменить уровень"
    else:
        status_message = "📊 Уровень знаний не выбран\n\nИспользуй /start чтобы выбрать уровень или /level для смены"
    
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
        
        # Проверяем уровень пользователя и уведомляем, если не выбран
        from bot.dialog import extract_user_level
        user_level = extract_user_level(chat_id)
        if not user_level:
            logger.info(f"Пользователь {user_id} не выбрал уровень - используем базовый по умолчанию")
            # Отправляем уведомление отдельным сообщением (не удаляем)
            level_notification = "📊 Уровень не выбран - использую базовый уровень для объяснения. Используй /level для смены уровня."
            await message.answer(level_notification)
            # Добавляем уведомление в историю диалога
            add_assistant_message(chat_id, level_notification)
            # Устанавливаем базовый уровень
            add_user_message(chat_id, "Базовый")
            user_level = "Базовый"
            # Обновляем сообщение "думаю" без уведомления (только если текст изменился)
            try:
                new_text = random.choice(THINKING_MESSAGES)
                if thinking_msg.text != new_text:
                    await thinking_msg.edit_text(new_text)
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение 'думаю': {e}")
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
        
        # Проверяем уровень пользователя и уведомляем, если не выбран
        from bot.dialog import extract_user_level
        user_level = extract_user_level(chat_id)
        if not user_level:
            logger.info(f"Пользователь {user_id} не выбрал уровень - используем базовый по умолчанию")
            # Отправляем уведомление отдельным сообщением (не удаляем)
            level_notification = "📊 Уровень не выбран - использую базовый уровень для объяснения. Используй /level для смены уровня."
            await message.answer(level_notification)
            # Добавляем уведомление в историю диалога
            add_assistant_message(chat_id, level_notification)
            # Устанавливаем базовый уровень
            add_user_message(chat_id, "Базовый")
            user_level = "Базовый"
            # Обновляем сообщение "думаю" без уведомления (только если текст изменился)
            try:
                if thinking_msg.text != "🖼️ Анализирую изображение...":
                    await thinking_msg.edit_text("🖼️ Анализирую изображение...")
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение 'думаю': {e}")
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


async def handle_voice(message: Message):
    """
    Обработка голосовых сообщений
    
    Скачивает аудио, транскрибирует его в текст и передает в основной диалоговый флоу
    
    Args:
        message: Объект сообщения с голосовым сообщением
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Получено голосовое сообщение от пользователя {user_id} (@{username})")
    
    try:
        # Отправляем сообщение "обрабатываю голосовое сообщение"
        processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
        
        # Получаем историю диалога
        dialog_history = get_dialog_history(chat_id)
        logger.info(f"История диалога получена: {len(dialog_history)} сообщений")
        
        # Проверяем уровень пользователя и уведомляем, если не выбран
        from bot.dialog import extract_user_level
        user_level = extract_user_level(chat_id)
        if not user_level:
            logger.info(f"Пользователь {user_id} не выбрал уровень - используем базовый по умолчанию")
            # Отправляем уведомление отдельным сообщением (не удаляем)
            level_notification = "📊 Уровень не выбран - использую базовый уровень для объяснения. Используй /level для смены уровня."
            await message.answer(level_notification)
            # Добавляем уведомление в историю диалога
            add_assistant_message(chat_id, level_notification)
            # Устанавливаем базовый уровень
            add_user_message(chat_id, "Базовый")
            user_level = "Базовый"
            # Обновляем сообщение "обрабатываю" без уведомления
            try:
                if processing_msg.text != "🎤 Транскрибирую аудио...":
                    await processing_msg.edit_text("🎤 Транскрибирую аудио...")
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение 'обрабатываю': {e}")
        logger.info(f"Уровень пользователя {user_id}: {user_level}")
        
        # Получаем информацию о голосовом сообщении
        voice = message.voice
        file_id = voice.file_id
        
        logger.info(f"Скачиваем голосовое сообщение: file_id={file_id}")
        
        # Скачиваем файл через Telegram Bot API
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        # Скачиваем аудио-данные
        audio_data = await message.bot.download_file(file_path)
        
        # Определяем расширение файла (Telegram обычно использует .ogg для голосовых сообщений)
        file_extension = ".ogg"
        if hasattr(voice, 'mime_type') and voice.mime_type:
            if "mp3" in voice.mime_type:
                file_extension = ".mp3"
            elif "m4a" in voice.mime_type:
                file_extension = ".m4a"
            elif "wav" in voice.mime_type:
                file_extension = ".wav"
        
        logger.info(f"Аудио-файл скачан, размер: {len(audio_data.read())} байт, расширение: {file_extension}")
        
        # Возвращаем указатель в начало файла
        audio_data.seek(0)
        
        # Обновляем сообщение о статусе
        await processing_msg.edit_text("🎤 Транскрибирую аудио...")
        
        # Транскрибируем аудио
        try:
            transcribed_text = await transcribe_audio_data(audio_data.read(), file_extension)
        except ValueError as e:
            logger.error(f"Ошибка конфигурации: {e}")
            await processing_msg.edit_text("❌ Функция транскрипции голосовых сообщений не настроена. Обратитесь к администратору.")
            return
        except Exception as e:
            logger.error(f"Ошибка транскрипции: {e}")
            await processing_msg.edit_text("❌ Не удалось транскрибировать голосовое сообщение. Возможно, проблема с API или сетью. Попробуйте отправить текстовое сообщение.")
            return
        
        logger.info(f"Транскрипция завершена. Текст найден: {len(transcribed_text) > 0}")
        
        if not transcribed_text.strip():
            await processing_msg.edit_text("❌ Не удалось распознать речь в голосовом сообщении. Попробуйте говорить четче или отправьте текстовое сообщение.")
            return
        
        # Обновляем сообщение о статусе
        await processing_msg.edit_text("💭 Обрабатываю ваш вопрос...")
        
        # Добавляем транскрибированный текст в историю диалога
        add_user_message(chat_id, transcribed_text)
        
        # Получаем обновленную историю диалога
        dialog_history = get_dialog_history(chat_id)
        
        # Отправляем запрос к LLM
        response = await get_llm_response(dialog_history)
        
        if not response:
            await processing_msg.edit_text("😔 Извините, не удалось получить ответ. Попробуйте еще раз.")
            return
        
        # Очищаем ответ от лишних символов
        clean_text = clean_response(response)
        
        # Добавляем ответ ассистента в историю
        add_assistant_message(chat_id, clean_text)
        
        # Удаляем сообщение "обрабатываю"
        await processing_msg.delete()
        
        # Отправляем ответ пользователю
        await message.answer(clean_text)
        
        logger.info(f"Ответ отправлен пользователю {user_id}. Длина ответа: {len(clean_text)} символов")
        
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        await processing_msg.edit_text("❌ Не удалось загрузить голосовое сообщение. Попробуйте еще раз.")
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        await processing_msg.edit_text("❌ Голосовое сообщение слишком большое или в неподдерживаемом формате.")
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {type(e).__name__}: {e}")
        await processing_msg.edit_text("😔 Извините, произошла ошибка при обработке голосового сообщения. Попробуйте отправить текстовое сообщение.")


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
    
    # Обработчик голосовых сообщений (должен быть перед общим обработчиком сообщений)
    dp.message.register(handle_voice, F.voice)
    
    # Обработчик фотографий и документов с изображениями (должен быть перед общим обработчиком сообщений)
    # Регистрируем отдельно для каждого типа медиа
    dp.message.register(handle_photo, F.photo)
    dp.message.register(handle_photo, F.document.has(F.mime_type.startswith('image/')))
    
    # Обработчик всех остальных текстовых сообщений через LLM с контекстом
    dp.message.register(handle_message)
