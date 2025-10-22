"""Обработчики команд и сообщений Telegram-бота"""

import logging
import random
import base64
from datetime import datetime
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
from bot.database import Database
from bot.test_prompts import TEST_GENERATION_PROMPT


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


def create_questions_mode_keyboard():
    """
    Создает клавиатуру для режима задавания вопросов
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками управления
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Сменить уровень", callback_data="change_level"),
            InlineKeyboardButton(text="ℹ️ Статус", callback_data="show_status")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="show_profile"),
            InlineKeyboardButton(text="📚 Начать курс", callback_data="start_course")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="show_help")
        ]
    ])


async def handle_start(message: Message):
    """
    Обработка команды /start
    
    Показывает приветствие и основные команды
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    chat_id = message.chat.id
    
    logger.info(f"Команда /start от пользователя {user_id} (@{username})")
    
    # Очистка истории при старте (начинаем с чистого листа)
    clear_dialog(chat_id)
    
    # Создаем кнопки для основных функций
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Сменить уровень", callback_data="change_level"),
            InlineKeyboardButton(text="ℹ️ Статус", callback_data="show_status")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="show_profile"),
            InlineKeyboardButton(text="📚 Начать курс Math", callback_data="start_course")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="show_help")
        ]
    ])
    
    welcome_text = get_welcome_message("Базовый")
    await message.answer(welcome_text, reply_markup=keyboard)




async def handle_level(message: Message):
    """
    Обработка команды /level - смена уровня знаний
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /level от пользователя {user_id}")
    
    # Создаем клавиатуру для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Базовый", callback_data="level_beginner"),
            InlineKeyboardButton(text="🟡 Средний", callback_data="level_intermediate")
        ],
        [
            InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ]
    ])
    
    await message.answer(
        "📊 Выберите ваш уровень знаний:\n\n"
        "🟢 **Базовый** - начинающий, изучаю основы\n"
        "🟡 **Средний** - имею опыт, хочу углубить знания\n"
        "🔴 **Продвинутый** - эксперт, нужны сложные темы",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_status(message: Message):
    """
    Обработка команды /status - показ текущего уровня
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    
    logger.info(f"Команда /status от пользователя {user_id}")
    
    # Получаем статистику диалога
    stats = get_dialog_stats(message.chat.id)
    
    status_text = (
        f"ℹ️ **Ваш статус:**\n\n"
        f"📊 Уровень: Базовый (по умолчанию)\n"
        f"💬 Сообщений в диалоге: {stats['message_count']}\n"
        f"📝 Последнее сообщение: {stats['last_message_time']}\n\n"
        f"Используйте /level для смены уровня знаний"
    )
    
    await message.answer(status_text, parse_mode="Markdown")


async def handle_help(message: Message):
    """
    Обработка команды /help - помощь
    
    Args:
        message: Объект сообщения от пользователя
    """
    help_text = (
        "❓ **Помощь по использованию бота:**\n\n"
        "**Основные команды:**\n"
        "• /start - начать работу с ботом\n"
        "• /level - изменить уровень знаний\n"
        "• /status - показать текущий статус\n"
        "• /profile - показать профиль\n"
        "• /start_course - начать курс Math\n"
        "• /errors - показать ошибки в тестах\n"
        "• /help - эта справка\n\n"
        "**Режимы работы:**\n"
        "• **Вопросы** - задавайте любые вопросы по ML\n"
        "• **Курсы** - изучайте структурированные уроки\n\n"
        "**Возможности:**\n"
        "• Анализ изображений с формулами и схемами\n"
        "• Транскрипция голосовых сообщений\n"
        "• Адаптация ответов под ваш уровень\n"
        "• Интерактивные тесты и прогресс"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


async def handle_main_menu_buttons(callback_query: CallbackQuery):
    """
    Обработка кнопок главного меню
    
    Args:
        callback_query: Объект callback query от пользователя
    """
    data = callback_query.data
    
    if data == "change_level":
        await handle_level(callback_query.message)
        await callback_query.answer()
    
    elif data == "show_status":
        await handle_status(callback_query.message)
        await callback_query.answer()
    
    elif data == "show_profile":
        await handle_profile_command(callback_query.message)
        await callback_query.answer()
    
    elif data == "start_course":
        await handle_start_course(callback_query.message)
        await callback_query.answer()
    
    elif data == "show_help":
        await handle_help(callback_query.message)
        await callback_query.answer()


async def handle_level_selection(callback_query: CallbackQuery):
    """
    Обработка выбора уровня знаний
    
    Args:
        callback_query: Объект callback query от пользователя
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    level_map = {
        "level_beginner": "Базовый",
        "level_intermediate": "Средний", 
        "level_advanced": "Продвинутый"
    }
    
    if data in level_map:
        level = level_map[data]
        
        # Обновляем уровень пользователя (в реальной реализации здесь была бы БД)
        logger.info(f"Пользователь {user_id} изменил уровень на: {level}")
        
        await callback_query.message.edit_text(
            f"✅ Уровень знаний изменен на: **{level}**\n\n"
            "Теперь я буду адаптировать ответы под ваш уровень знаний.",
            parse_mode="Markdown"
        )
        await callback_query.answer()


async def handle_message(message: Message):
    """
    Обработка текстовых сообщений через LLM с контекстом
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {text[:50]}...")
    
    # Проверяем, не является ли это выбором уровня
    if is_first_level_selection(text):
        return
    
    # Добавляем сообщение пользователя в историю
    add_user_message(chat_id, text)
    
    # Получаем историю диалога
    dialog_history = get_dialog_history(chat_id)
    
    # Отправляем индикатор "модель думает"
    thinking_msg = random.choice(THINKING_MESSAGES)
    processing_msg = await message.answer(thinking_msg)
    
    try:
        # Получаем ответ от LLM
        response = await get_llm_response(text, user_id, dialog_history)
        
        # Очищаем ответ от лишних символов
        clean_text = clean_response(response)
        
        # Добавляем ответ ассистента в историю
        add_assistant_message(chat_id, clean_text)
        
        # Удаляем сообщение "обрабатываю"
        await processing_msg.delete()
        
        # Отправляем ответ пользователю
        await message.answer(clean_text)
        
        logger.info(f"Ответ отправлен пользователю {user_id}. Длина ответа: {len(clean_text)} символов")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {type(e).__name__}: {e}")
        await processing_msg.edit_text("😔 Извините, произошла ошибка при обработке сообщения. Попробуйте еще раз.")


async def handle_photo(message: Message):
    """
    Обработка фотографий с использованием Vision API
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Фото от пользователя {user_id}")
    
    # Отправляем индикатор обработки
    processing_msg = await message.answer("📷 Анализирую изображение...")
    
    try:
        # Получаем информацию о фото
        photo = message.photo[-1]  # Берем фото наибольшего размера
        file_id = photo.file_id
        
        # Здесь должна быть логика анализа изображения через Vision API
        # Пока что отправляем заглушку
        await processing_msg.edit_text(
            "📷 Изображение получено!\n\n"
            "Функция анализа изображений временно недоступна. "
            "Отправьте текстовое сообщение для получения ответа."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {type(e).__name__}: {e}")
        await processing_msg.edit_text("😔 Извините, произошла ошибка при обработке изображения. Попробуйте отправить текстовое сообщение.")


async def handle_voice(message: Message):
    """
    Обработка голосовых сообщений
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Голосовое сообщение от пользователя {user_id}")
    
    # Отправляем индикатор обработки
    processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Здесь должна быть логика транскрипции голоса
        # Пока что отправляем заглушку
        await processing_msg.edit_text(
            "🎤 Голосовое сообщение получено!\n\n"
            "Функция транскрипции голоса временно недоступна. "
            "Отправьте текстовое сообщение для получения ответа."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {type(e).__name__}: {e}")
        await processing_msg.edit_text("😔 Извините, произошла ошибка при обработке голосового сообщения. Попробуйте отправить текстовое сообщение.")


# Инициализация базы данных
db = Database()


async def handle_start_course(message: Message):
    """
    Обработка команды /start_course - начало курса Math
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /start_course от пользователя {user_id}")
    
    # Инициализируем прогресс пользователя для курса Math
    course = db.get_course(1)  # Предполагаем, что Math курс имеет ID = 1
    if not course:
        await message.answer("❌ Курс Math не найден. Обратитесь к администратору.")
        return
    
    db.init_user_progress(user_id, course.id)
    
    # Показываем первый урок
    await show_lesson(message, course.id, 1)


async def show_lesson(message: Message, course_id: int, lesson_number: int):
    """
    Показать урок пользователю
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    lesson = db.get_lesson(course_id, lesson_number)
    if not lesson:
        await message.answer("❌ Урок не найден.")
        return
    
    course = db.get_course(course_id)
    progress = db.get_user_progress(user_id, course_id)
    
    # Создаем клавиатуру навигации
    keyboard_buttons = []
    
    # Кнопки навигации
    nav_buttons = []
    if lesson_number > 1:
        nav_buttons.append(InlineKeyboardButton(text="← Предыдущий", callback_data=f"lesson_{course_id}_{lesson_number-1}"))
    
    if lesson_number < course.total_lessons:
        nav_buttons.append(InlineKeyboardButton(text="Следующий →", callback_data=f"lesson_{course_id}_{lesson_number+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    # Кнопки управления
    keyboard_buttons.append([
        InlineKeyboardButton(text="🏠 Назад", callback_data="back_to_menu"),
        InlineKeyboardButton(text="🧪 Тест", callback_data=f"test_{lesson.id}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Формируем сообщение
    lesson_text = f"📘 Урок {lesson_number}/{course.total_lessons}: {lesson.title}\n\n{lesson.content}"
    
    await message.answer(lesson_text, reply_markup=keyboard)


async def handle_lesson_callback(callback_query: CallbackQuery):
    """
    Обработка навигации по урокам
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data.startswith("lesson_"):
        # Навигация по урокам
        parts = data.split("_")
        course_id = int(parts[1])
        lesson_number = int(parts[2])
        
        await callback_query.message.delete()
        await show_lesson(callback_query.message, course_id, lesson_number)
        await callback_query.answer()
    
    elif data.startswith("test_"):
        # Начало тестирования
        lesson_id = int(data.split("_")[1])
        await start_lesson_test(callback_query, lesson_id)
    
    elif data == "back_to_menu":
        # Возврат в главное меню
        await callback_query.message.delete()
        await handle_start(callback_query.message)
        await callback_query.answer()


async def start_lesson_test(callback_query: CallbackQuery, lesson_id: int):
    """
    Начать тестирование по уроку
    """
    user_id = callback_query.from_user.id
    
    # Получаем урок
    lesson = None
    for course_id in range(1, 10):  # Предполагаем максимум 10 курсов
        for lesson_num in range(1, 20):  # Предполагаем максимум 20 уроков
            l = db.get_lesson(course_id, lesson_num)
            if l and l.id == lesson_id:
                lesson = l
                break
        if lesson:
            break
    
    if not lesson:
        await callback_query.answer("❌ Урок не найден.")
        return
    
    # Генерируем тестовый вопрос
    try:
        prompt = TEST_GENERATION_PROMPT.format(
            lesson_title=lesson.title,
            lesson_content=lesson.content
        )
        
        response = await get_llm_response(prompt, user_id)
        
        # Парсим ответ
        lines = response.strip().split('\n')
        question = ""
        options = []
        correct_answer = ""
        
        parsing_mode = "question"
        for line in lines:
            line = line.strip()
            if line.startswith("Вопрос:"):
                question = line.replace("Вопрос:", "").strip()
                parsing_mode = "options"
            elif line.startswith("A)"):
                options.append(line.replace("A)", "").strip())
            elif line.startswith("B)"):
                options.append(line.replace("B)", "").strip())
            elif line.startswith("C)"):
                options.append(line.replace("C)", "").strip())
            elif line.startswith("Правильный ответ:"):
                correct_answer = line.replace("Правильный ответ:", "").strip()
        
        if not question or len(options) != 3 or not correct_answer:
            await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            return
        
        # Создаем клавиатуру с вариантами ответов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"A) {options[0]}", callback_data=f"answer_{lesson_id}_A_{correct_answer}"),
                InlineKeyboardButton(text=f"B) {options[1]}", callback_data=f"answer_{lesson_id}_B_{correct_answer}")
            ],
            [
                InlineKeyboardButton(text=f"C) {options[2]}", callback_data=f"answer_{lesson_id}_C_{correct_answer}")
            ],
            [
                InlineKeyboardButton(text="🔄 Новый вопрос", callback_data=f"test_{lesson_id}")
            ]
        ])
        
        test_text = f"🧪 Тест по уроку: {lesson.title}\n\n{question}\n\nВыберите правильный ответ:"
        
        await callback_query.message.edit_text(test_text, reply_markup=keyboard)
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка генерации теста: {e}")
        await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")


async def handle_test_answer(callback_query: CallbackQuery):
    """
    Обработка ответа на тест
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data.startswith("answer_"):
        parts = data.split("_")
        lesson_id = int(parts[1])
        user_answer = parts[2]
        correct_answer = parts[3]
        
        # Проверяем ответ
        is_correct = user_answer == correct_answer
        
        if is_correct:
            # Отмечаем урок как завершенный
            db.complete_lesson(user_id, lesson_id)
            
            # Обновляем прогресс
            lesson = None
            course_id = None
            for cid in range(1, 10):
                for ln in range(1, 20):
                    l = db.get_lesson(cid, ln)
                    if l and l.id == lesson_id:
                        lesson = l
                        course_id = cid
                        break
                if lesson:
                    break
            
            if lesson and course_id:
                progress = db.get_user_progress(user_id, course_id)
                if progress:
                    completed_lessons = progress.completed_lessons + 1
                    db.update_user_progress(user_id, course_id, lesson.lesson_number, completed_lessons)
            
            await callback_query.message.edit_text(
                "✅ Правильно! Урок завершен.\n\n"
                "Вы можете перейти к следующему уроку или повторить материал.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="➡️ Следующий урок", callback_data=f"lesson_{course_id}_{lesson.lesson_number+1}"),
                        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
                    ]
                ])
            )
        else:
            # Сохраняем ошибку
            db.add_test_error(user_id, lesson_id, "Тестовый вопрос", correct_answer, user_answer)
            
            await callback_query.message.edit_text(
                f"❌ Неправильно! Правильный ответ: {correct_answer}\n\n"
                "Попробуйте еще раз с новым вопросом.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🔄 Новый вопрос", callback_data=f"test_{lesson_id}"),
                        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
                    ]
                ])
            )
        
        await callback_query.answer()


async def handle_profile_command(message: Message):
    """
    Обработка команды /profile - показ прогресса пользователя
    """
    user_id = message.from_user.id
    
    # Получаем статистику по всем курсам
    courses_stats = []
    for course_id in range(1, 10):  # Предполагаем максимум 10 курсов
        course = db.get_course(course_id)
        if course:
            stats = db.get_user_course_stats(user_id, course_id)
            if stats['completed_lessons'] > 0 or stats['current_lesson'] > 1:
                courses_stats.append({
                    'name': course.name,
                    'current': stats['current_lesson'],
                    'total': course.total_lessons,
                    'completed': stats['completed_lessons'],
                    'errors': stats['error_count']
                })
    
    if not courses_stats:
        await message.answer("📊 Вы еще не начали изучать курсы. Используйте /start_course для начала.")
        return
    
    # Формируем сообщение профиля
    profile_text = "👤 Ваш профиль:\n\n"
    
    for stats in courses_stats:
        profile_text += f"📚 {stats['name']}: {stats['completed']}/{stats['total']} уроков завершено\n"
        profile_text += f"📍 Текущий урок: {stats['current']}/{stats['total']}\n"
        profile_text += f"❌ Ошибок в тестах: {stats['errors']}\n\n"
    
    profile_text += "Используйте /errors для просмотра ошибок в тестах."
    
    await message.answer(profile_text)


async def handle_errors_command(message: Message):
    """
    Обработка команды /errors - показ ошибок пользователя
    """
    user_id = message.from_user.id
    
    errors = db.get_user_test_errors(user_id)
    
    if not errors:
        await message.answer("✅ У вас нет ошибок в тестах!")
        return
    
    # Группируем ошибки по урокам
    errors_by_lesson = {}
    for error in errors:
        if error.lesson_id not in errors_by_lesson:
            errors_by_lesson[error.lesson_id] = []
        errors_by_lesson[error.lesson_id].append(error)
    
    errors_text = "❌ Ваши ошибки в тестах:\n\n"
    
    for lesson_id, lesson_errors in errors_by_lesson.items():
        # Получаем информацию об уроке
        lesson = None
        for course_id in range(1, 10):
            for lesson_num in range(1, 20):
                l = db.get_lesson(course_id, lesson_num)
                if l and l.id == lesson_id:
                    lesson = l
                    break
            if lesson:
                break
        
        if lesson:
            errors_text += f"📘 {lesson.title}:\n"
            for error in lesson_errors[:3]:  # Показываем только последние 3 ошибки
                errors_text += f"• Вопрос: {error.question[:50]}...\n"
                errors_text += f"  Правильный ответ: {error.correct_answer}\n"
                errors_text += f"  Ваш ответ: {error.user_answer}\n\n"
    
    errors_text += "Попробуйте пройти тесты заново для улучшения результатов!"
    
    await message.answer(errors_text)


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
    
    # Обработчик команды /help - помощь
    dp.message.register(handle_help, Command("help"))
    
    # Обработчик команды /start_course - начало курса
    dp.message.register(handle_start_course, Command("start_course"))
    
    # Обработчик команды /profile - профиль пользователя
    dp.message.register(handle_profile_command, Command("profile"))
    
    # Обработчик команды /errors - ошибки в тестах
    dp.message.register(handle_errors_command, Command("errors"))
    
    # Обработчик нажатий на кнопки выбора уровня
    dp.callback_query.register(handle_level_selection, F.data.startswith("level_"))
    
    # Обработчик кнопок главного меню
    dp.callback_query.register(handle_main_menu_buttons, F.data.in_([
        "change_level", "show_status", "show_profile", "start_course", "show_help"
    ]))
    
    # Обработчики для курсов
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("lesson_"))
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("test_"))
    dp.callback_query.register(handle_lesson_callback, F.data == "back_to_menu")
    dp.callback_query.register(handle_test_answer, F.data.startswith("answer_"))
    
    # Обработчик голосовых сообщений (должен быть перед общим обработчиком сообщений)
    dp.message.register(handle_voice, F.voice)
    
    # Обработчик фотографий и документов с изображениями (должен быть перед общим обработчиком сообщений)
    # Регистрируем отдельно для каждого типа медиа
    dp.message.register(handle_photo, F.photo)
    dp.message.register(handle_photo, F.document.has(F.mime_type.startswith('image/')))
    
    # Обработчик всех остальных текстовых сообщений через LLM с контекстом
    dp.message.register(handle_message)