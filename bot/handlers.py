"""
Обработчики сообщений и команд для Telegram бота ML Tutor

Этот модуль содержит все обработчики для команд, сообщений и callback queries.
"""

import logging
from string import Template
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.dialog import clear_dialog, add_user_message, add_assistant_message, get_dialog_history, extract_user_level, get_user_level_or_default
from bot.prompts import get_system_prompt, get_welcome_message
from bot.progress import get_user_progress, mark_topic_completed
from llm.client import get_llm_response, get_llm_response_for_test
from llm.tavily_client import search_with_tavily
from bot.database import Database
from bot.test_prompts import TEST_GENERATION_PROMPT
from bot.simple_rag import SimpleRAG
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Простой класс-обертка для совместимости с существующим кодом
class LearningProgressTracker:
    def __init__(self):
        pass
    
    def get_user_stats(self, user_id: int) -> dict:
        """Получить статистику пользователя"""
        # Получаем статистику тестов из базы данных
        test_errors = db.get_user_test_errors(user_id)
        successful_tests = 0  # Упрощенная логика
        
        return {
            'topics_studied': 0,  # Упрощенная логика
            'learning_time': '0 мин',  # Заглушка
            'successful_tests': successful_tests,
            'test_errors': len(test_errors)
        }
    
    def update_progress(self, user_id: int, question: str, response: str):
        """Обновить прогресс пользователя"""
        # Простая логика: если в ответе есть ключевые слова, отмечаем тему как изученную
        if any(keyword in question.lower() for keyword in ['вектор', 'матрица', 'собственн']):
            mark_topic_completed(user_id, 'math_vectors_operations')
        elif any(keyword in question.lower() for keyword in ['матриц', 'умножен', 'транспон']):
            mark_topic_completed(user_id, 'math_matrices_operations')
        elif any(keyword in question.lower() for keyword in ['собственн', 'eigen', 'характерист']):
            mark_topic_completed(user_id, 'math_eigenvalues_vectors')

# Инициализация трекера прогресса
progress_tracker = LearningProgressTracker()

# Инициализация базы данных
db = Database()


async def handle_start(message: Message):
    """
    Обработка команды /start
    
    Показывает приветствие и очищает только историю диалога.
    Прогресс курсов сохраняется - для его очистки используйте /clear
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    chat_id = message.chat.id
    
    logger.info(f"Команда /start от пользователя {user_id} (@{username})")
    
    # Сохраняем текущий уровень перед очисткой диалога
    current_level = get_user_level_or_default(chat_id)
    
    # Очистка истории диалога при старте (прогресс курсов сохраняется)
    clear_dialog(chat_id)
    
    # Восстанавливаем уровень после очистки диалога
    if current_level != "Базовый":  # Если уровень не по умолчанию
        add_user_message(chat_id, current_level)
    
    # Формируем приветственное сообщение
    welcome_text = f"""👋 Привет!
Я — твой помощник по машинному обучению 🧠

⚙️ Возможности:
• Адаптивные объяснения тем ML и DL под твой уровень
• Поддержка текста, голоса и изображений
• Образовательные курсы с интерактивными тестами для закрепления
• Изучение и обсуждение PDF-статей

🚀 Как использовать:
• Используй команды или отправь текст/картинку/аудио/PDF-статью
• /learn — начать обучение по курсам
• /status — показать текущий уровень знаний
• /help — список всех возможностей

📊 Выбери свой уровень знаний, чтобы начать:"""
    
    # Создаем клавиатуру для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Новичок", callback_data="level_beginner"),
            InlineKeyboardButton(text="🟡 Базовый", callback_data="level_intermediate")
        ],
        [
            InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")
        ]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)


async def handle_learn(message: Message):
    """
    Обработка команды /learn - выбор курсов
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    
    logger.info(f"Команда /learn от пользователя {user_id}")
    
    # Получаем доступные курсы
    courses = []
    for course_id in range(1, 10):  # Предполагаем максимум 10 курсов
        course = db.get_course(course_id)
        if course:
            courses.append(course)
    
    if not courses:
        await message.answer("❌ Курсы пока не доступны. Обратитесь к администратору.")
        return
    
    # Создаем клавиатуру с курсами
    keyboard_buttons = []
    for course in courses:
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"📚 {course.name}", callback_data=f"course_{course.id}")
        ])
    
    # Добавляем кнопку "Вернуться в главное меню"
    keyboard_buttons.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    courses_text = "📚 Доступные курсы:\n\n"
    for i, course in enumerate(courses, 1):
        courses_text += f"🧠 {course.name}\n"
        courses_text += f"   └─ {course.description}\n"
        courses_text += f"   └─ Уроков: {course.total_lessons}\n\n"
    
    courses_text += "Выберите курс для изучения:"
    
    await message.answer(courses_text, reply_markup=keyboard, parse_mode="Markdown")


async def handle_level(message: Message):
    """
    Обработка команды /level - смена уровня знаний
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /level от пользователя {user_id}")
    
    # Формируем сообщение для выбора уровня
    level_text = """📊 Выбери свой уровень знаний:"""
    
    # Создаем клавиатуру для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Новичок", callback_data="level_beginner"),
            InlineKeyboardButton(text="🟡 Базовый", callback_data="level_intermediate")
        ],
        [
            InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")
        ]
    ])
    
    await message.answer(level_text, reply_markup=keyboard)


async def handle_status(message: Message):
    """
    Обработка команды /status - показ текущего уровня
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /status от пользователя {user_id}")
    
    # Получаем статистику диалога
    dialog_history = get_dialog_history(chat_id)
    current_level = get_user_level_or_default(chat_id)
    
    # Получаем статистику прогресса
    progress_stats = progress_tracker.get_user_stats(user_id)
    
    # Получаем информацию о курсах
    courses = db.get_all_courses()
    courses_info = []
    
    for course in courses:
        progress = db.get_user_progress(user_id, course.id)
        if progress:
            completed = progress.completed_lessons
            total = course.total_lessons
            percentage = int((completed / total) * 100) if total > 0 else 0
            courses_info.append(f"🧠 {course.name} └─ Прогресс: {completed}/{total} ({percentage}%)")
        else:
            courses_info.append(f"🧠 {course.name} └─ Прогресс: 0/{course.total_lessons} (0%)")
    
    # Проверяем, был ли уровень установлен автоматически
    original_level = extract_user_level(chat_id)
    level_note = ""
    if original_level is None:
        level_note = " (установлен автоматически)"
    
    status_text = f"📊 **Ваш профиль:**\n\n"
    level_emoji = "🟢" if current_level == "Новичок" else "🟡" if current_level == "Базовый" else "🔴"
    status_text += f"🎯 **Текущий уровень:** {current_level} {level_emoji}\n"
    status_text += f"💡 Используйте команду /level для смены уровня.\n\n"
    
    if courses_info:
        status_text += f"📚 **Курсы:**\n"
        for course_info in courses_info:
            status_text += f"{course_info}\n"
        status_text += "\n"
    
    # Создаем клавиатуру с кнопкой возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ]
    ])
    
    await message.answer(status_text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_clear(message: Message):
    """
    Обработка команды /clear - очистка прогресса курсов
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /clear от пользователя {user_id}")
    
    # Очищаем весь прогресс пользователя
    db.clear_user_progress(user_id)
    
    # Очищаем диалог
    clear_dialog(chat_id)
    
    clear_text = """🗑️ **Очистка завершена!**

✅ Удалено:
• История диалогов
• Прогресс курсов
• Результаты тестов

🎯 Можете начать обучение заново.

💡 Используйте /learn для выбора курса."""
    
    await message.answer(clear_text, parse_mode="Markdown")


async def handle_help(message: Message):
    """
    Обработка команды /help - показ справки
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    
    logger.info(f"Команда /help от пользователя {user_id}")
    
    help_text = """
🤖 **ML Tutor Bot - Справка**

**Основные команды:**
• /start - Начать работу с ботом
• /learn - Выбрать курс для изучения
• /level - Изменить уровень знаний
• /status - Показать текущий статус
• /exit - Выйти из режима анализа PDF
• /clear - Очистить весь прогресс курсов
• /help - Показать эту справку
"""
    
    # Создаем клавиатуру с кнопкой возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
        ]
    ])
    
    await message.answer(help_text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_exit(message: Message):
    """
    Обработка команды /exit - выход из режима анализа PDF
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Команда /exit от пользователя {user_id}")
    
    # Удаляем документ пользователя из базы данных
    db.clear_user_documents(user_id)
    
    exit_text = """📄 Вы вышли из режима анализа PDF

Продолжайте обучение:
• Задавайте вопросы по ML
• Изучайте курсы: /learn
• Меняйте уровень: /level"""
    
    # Создаем кнопку для возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="back_to_main")
        ]
    ])
    
    await message.answer(exit_text, parse_mode="Markdown", reply_markup=keyboard)


async def handle_unknown_command(message: Message):
    """
    Обработка неизвестных команд
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    command = message.text.split()[0] if message.text else ""
    
    logger.info(f"Неизвестная команда '{command}' от пользователя {user_id}")
    
    unknown_text = f"""❌ Команда `{command}` не найдена.

Используйте доступные команды:
• `/start` - Начать работу с ботом
• `/learn` - Выбрать курс для изучения
• `/level` - Изменить уровень знаний
• `/status` - Показать текущий статус
• `/help` - Показать справку

Или просто задавайте вопросы по машинному обучению!"""
    
    await message.answer(unknown_text, parse_mode="Markdown")


async def handle_course_selection(callback_query: CallbackQuery):
    """
    Обработка выбора курса - показывает план курса с прогрессом
    
    Args:
        callback_query: Объект callback query от пользователя
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data.startswith("course_"):
        course_id = int(data.split("_")[1])
        course = db.get_course(course_id)
        
        if not course:
            await callback_query.answer("❌ Курс не найден.")
            return
            
        # Получаем прогресс пользователя
        progress = db.get_user_progress(user_id, course_id)
        if not progress:
            db.init_user_progress(user_id, course_id)
            progress = db.get_user_progress(user_id, course_id)
        
        # Получаем список завершенных уроков
        completed_lessons = db.get_user_completed_lessons(user_id, course_id)
        
        # Формируем план курса с прогрессом
        plan_text = f"🧠 **МАТЕМАТИЧЕСКИЕ ОСНОВЫ ML**\n\n"
        plan_text += f"📊 Прогресс: {len(completed_lessons)}/{course.total_lessons} уроков завершено\n\n"
        
        # Показываем уроки с галочками по разделам
        plan_text += "📋 План курса:\n"
        
        # ЛИНЕЙНАЯ АЛГЕБРА
        plan_text += "▲ ЛИНЕЙНАЯ АЛГЕБРА\n"
        linear_algebra_lessons = [
            "Векторы и операции",
            "Матрицы и основные операции", 
            "Собственные значения и векторы",
            "Ортогональность и проекции",
            "SVD и PCA"
        ]
        
        for i, lesson_title in enumerate(linear_algebra_lessons, 1):
            lesson = db.get_lesson(course_id, i)
            if lesson:
                is_completed = i in completed_lessons
                status = "✅" if is_completed else ""
                plan_text += f"{status} {i}. {lesson_title}\n"
            else:
                plan_text += f"{i}. {lesson_title}\n"
        
        plan_text += "\n▲ МАТАН И ОПТИМИЗАЦИЯ\n"
        math_optimization_lessons = [
            "Производные и частные производные",
            "Градиенты и цепное правило",
            "Градиенты в матричной форме", 
            "Градиентный спуск (GD, SGD)",
            "Adam и другие оптимизаторы",
            "Выпуклые и невыпуклые функции",
            "Функции потерь (MSE, Cross-Entropy)",
            "Регуляризация (L1, L2)"
        ]
        
        for i, lesson_title in enumerate(math_optimization_lessons, 6):
            lesson = db.get_lesson(course_id, i)
            if lesson:
                is_completed = i in completed_lessons
                status = "✅" if is_completed else ""
                plan_text += f"{status} {i}. {lesson_title}\n"
            else:
                plan_text += f"{i}. {lesson_title}\n"
        
        plan_text += "\n▲ ВЕРОЯТНОСТЬ И СТАТИСТИКА\n"
        probability_stats_lessons = [
            "Случайные величины и распределения",
            "Матожидание, дисперсия, ковариация",
            "Байесовская теорема",
            "Maximum Likelihood Estimation (MLE)",
            "Энтропия и дивергенции"
        ]
        
        for i, lesson_title in enumerate(probability_stats_lessons, 14):
            lesson = db.get_lesson(course_id, i)
            if lesson:
                is_completed = i in completed_lessons
                status = "✅" if is_completed else ""
                plan_text += f"{status} {i}. {lesson_title}\n"
            else:
                plan_text += f"{i}. {lesson_title}\n"
        
        # Создаем клавиатуру
        keyboard_buttons = []
        
        if progress.current_lesson <= course.total_lessons:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🚀 Начать обучение", callback_data=f"start_learning_{course_id}")
            ])
        
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="← Назад к выбору курсов", callback_data="back_to_courses")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(plan_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback_query.answer()
    
    elif data == "back_to_courses":
        # Возврат к выбору курсов
        await callback_query.message.delete()
        await handle_learn(callback_query.message)
        await callback_query.answer()
    
    elif data == "back_to_main":
        # Удаляем текущее сообщение и отправляем новое главное меню
        try:
            await callback_query.message.delete()
        except:
            pass  # Игнорируем ошибки удаления
        
        # Если пользователь был в режиме RAG, выходим из него
        user_id = callback_query.from_user.id
        if db.has_user_documents(user_id):
            db.clear_user_documents(user_id)
            logger.info(f"Пользователь {user_id} вышел из режима RAG через главное меню")
        
        # Создаем новое сообщение с главным меню
        await callback_query.message.answer(
            """👋 Привет!
Я — твой помощник по машинному обучению 🧠

⚙️ Возможности:
• Адаптивные объяснения тем ML и DL под твой уровень
• Поддержка текста, голоса и изображений
• Образовательные курсы с интерактивными тестами для закрепления
• Изучение и обсуждение PDF-статей

🚀 Как использовать:
• Используй команды или отправь текст/картинку/аудио/PDF-статью
• /learn — начать обучение по курсам
• /status — показать текущий уровень знаний
• /help — список всех возможностей

📊 Выбери свой уровень знаний, чтобы начать:""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🟢 Новичок", callback_data="level_beginner"),
                    InlineKeyboardButton(text="🟡 Базовый", callback_data="level_intermediate")
                ],
                [
                    InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")
                ]
            ])
        )
        await callback_query.answer()


async def handle_level_selection(callback_query: CallbackQuery):
    """
    Обработка выбора уровня знаний
    
    Args:
        callback_query: Объект callback query от пользователя
    """
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    # Маппинг callback_data на уровни (используем те же названия, что и в extract_user_level)
    level_map = {
        "level_beginner": "Новичок",
        "level_intermediate": "Базовый", 
        "level_advanced": "Продвинутый"
    }
    
    if data in level_map:
        level = level_map[data]
        
        # Добавляем выбранный уровень в историю диалога
        add_user_message(chat_id, level)
        
        # Обновляем уровень пользователя (в реальной реализации здесь была бы БД)
        logger.info(f"Пользователь {user_id} изменил уровень на: {level}")
        
        # Получаем приветственное сообщение для выбранного уровня
        welcome_message = get_welcome_message(level)
        
        # Создаем клавиатуру с кнопкой возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")
            ]
        ])
        
        # Отправляем сообщение с подтверждением и приветствием
        await callback_query.message.edit_text(
            f"{welcome_message}\n\n"
            "Теперь я буду адаптировать ответы под ваш уровень знаний. Задавайте любые вопросы!\n\n"
            "💡 Используйте команду /level для смены уровня.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback_query.answer()
    
    elif data == "show_courses":
        # Переход к выбору курсов
        await handle_learn(callback_query.message)
        await callback_query.answer()
    

async def handle_message(message: Message):
    """
    Обработка обычных текстовых сообщений через LLM
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {text[:50]}...")
    
    # Проверяем, есть ли у пользователя выбранный уровень
    current_level = extract_user_level(chat_id)
    if current_level is None:
        # Устанавливаем уровень по умолчанию без уведомления
        get_user_level_or_default(chat_id)
    
    # Добавляем сообщение пользователя в историю
    add_user_message(chat_id, text)
    
    # Отправляем индикатор генерации
    processing_msg = await message.answer("🤖 Формулирую понятное объяснение...")
    
    # Получаем историю диалога
    dialog_history = get_dialog_history(chat_id)
    
    # Проверяем режим: RAG (есть документ) или обычный
    try:
        if db.has_user_documents(user_id):
            # Режим RAG - отвечаем по документу
            response = await get_rag_response(text, user_id, dialog_history)
        else:
            # Обычный режим - как раньше
            response = await get_llm_response(dialog_history)
        
        if response:
            # Добавляем ответ в историю
            add_assistant_message(chat_id, response)
            
            # Отправляем ответ пользователю, заменяя индикатор
            await processing_msg.edit_text(response)
            
            # Обновляем статистику прогресса
            progress_tracker.update_progress(user_id, text, response)
        else:
            await processing_msg.edit_text(
                "❌ Не удалось получить ответ. Попробуйте еще раз."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await processing_msg.edit_text(
            "❌ Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз."
        )


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
        InlineKeyboardButton(text="🏠 Назад к курсу", callback_data=f"back_to_course_{course.id}"),
        InlineKeyboardButton(text="🧪 Тест", callback_data=f"test_{lesson.id}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Формируем сообщение
    lesson_text = f"📘 Урок {lesson_number}/{course.total_lessons}: {lesson.title}\n\n{lesson.content}"
    
    await message.answer(lesson_text, reply_markup=keyboard)


async def handle_lesson_callback(callback_query: CallbackQuery):
    """
    Обработка навигации по урокам и начала обучения
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data.startswith("start_learning_"):
        # Начало обучения - показываем текущий урок
        course_id = int(data.split("_")[2])
        progress = db.get_user_progress(user_id, course_id)
        
        # Определяем номер урока для начала
        if progress:
            lesson_number = progress.current_lesson
        else:
            lesson_number = 1  # Начинаем с первого урока
        
        await callback_query.message.delete()
        await show_lesson(callback_query.message, course_id, lesson_number)
        await callback_query.answer()
    
    elif data.startswith("lesson_"):
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
    
    elif data.startswith("back_to_course_"):
        # Возврат к плану курса
        course_id = int(data.split("_")[-1])
        # Прямо вызываем обработку курса без создания нового CallbackQuery
        await callback_query.message.edit_text("🔄 Возвращаемся к курсу...")
        
        # Получаем курс
        course = db.get_course(course_id)
        if not course:
            await callback_query.message.edit_text("❌ Курс не найден.")
            await callback_query.answer()
            return
        
        # Получаем прогресс пользователя
        progress = db.get_user_progress(user_id, course_id)
        
        # Формируем текст плана курса
        plan_text = f"🧠 **{course.name.upper()}**\n\n"
        
        if progress:
            plan_text += f"📊 Прогресс: {progress.completed_lessons}/{course.total_lessons} уроков завершено\n\n"
        else:
            plan_text += f"📊 Прогресс: 0/{course.total_lessons} уроков завершено\n\n"
        
        plan_text += f"📋 **План курса:**\n"
        
        # Получаем список завершенных уроков
        completed_lessons = db.get_user_completed_lessons(user_id, course_id)
        
        # Группируем уроки по разделам
        sections = {
            "ЛИНЕЙНАЯ АЛГЕБРА": list(range(1, 6)),
            "МАТАН И ОПТИМИЗАЦИЯ": list(range(6, 14)),
            "ВЕРОЯТНОСТЬ И СТАТИСТИКА": list(range(14, 19))
        }
        
        for section_name, lesson_range in sections.items():
            plan_text += f"▲ {section_name}\n"
            for i in lesson_range:
                lesson = db.get_lesson(course_id, i)
                if lesson:
                    lesson_title = lesson.title
                    if i in completed_lessons:
                        plan_text += f"✅ {i}. {lesson_title}\n"
                    else:
                        plan_text += f"  {i}. {lesson_title}\n"
            plan_text += "\n"
        
        # Создаем клавиатуру только с кнопкой "Меню курса"
        keyboard_buttons = []
        
        # Кнопка "Назад к курсам"
        keyboard_buttons.append([
            InlineKeyboardButton(text="← Назад к курсам", callback_data="back_to_courses")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(plan_text, reply_markup=keyboard, parse_mode="Markdown")
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
        
    # Показываем индикатор генерации теста
    generating_msg = await callback_query.message.edit_text("🧪 Генерирую тестовый вопрос...")
    
    # Генерируем тестовый вопрос
    try:
        logger.info(f"Генерируем тест для урока: {lesson.title}")
        
        # Безопасно форматируем промпт с рандомизацией
        try:
            # Добавляем случайный элемент для разнообразия
            import random
            random_hint = random.choice([
                "Создай вопрос с простыми числами",
                "Используй разные числа в вопросе", 
                "Сделай вопрос интересным",
                "Используй числа от 1 до 5"
            ])
            
            # Используем Template для безопасного форматирования
            template = Template(TEST_GENERATION_PROMPT)
            prompt = template.safe_substitute(
                lesson_title=lesson.title,
                lesson_content=lesson.content
            )
            
            # Добавляем рандомизацию в конец промпта
            prompt += f"\n\nВАЖНО: {random_hint}. Создай УНИКАЛЬНЫЙ вопрос, отличающийся от предыдущих."
            
        except Exception as format_error:
            logger.error(f"Ошибка форматирования промпта: {format_error}")
            try:
                await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            except Exception:
                await callback_query.message.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            return
        
        logger.info(f"Промпт сформирован, длина: {len(prompt)} символов")
        
        # Используем специальные параметры для генерации тестов
        response = await get_llm_response_for_test(prompt)
        
        logger.info(f"Ответ LLM для генерации теста: {response[:300]}...")
        
        # Очищаем ответ от токенов модели
        clean_response = response.strip()
        if clean_response.startswith('<s>'):
            clean_response = clean_response[3:].strip()
        if clean_response.endswith('</s>'):
            clean_response = clean_response[:-4].strip()
        
        # Проверяем, что ответ не пустой и содержит достаточно информации
        if len(clean_response) < 10 or clean_response in ['<s>', '</s>', '<s></s>']:
            logger.warning(f"LLM вернул слишком короткий ответ: '{clean_response}'")
            try:
                await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            except Exception:
                await callback_query.message.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            return
        
        logger.info(f"Очищенный ответ LLM: {clean_response[:200]}...")
        
        # Парсим ответ
        lines = clean_response.split('\n')
        question = ""
        options = []
        correct_answer = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("Вопрос:"):
                question = line.replace("Вопрос:", "").strip()
            elif line.startswith("A)"):
                options.append(line.replace("A)", "").strip())
            elif line.startswith("B)"):
                options.append(line.replace("B)", "").strip())
            elif line.startswith("C)"):
                options.append(line.replace("C)", "").strip())
            elif line.startswith("Правильный ответ:"):
                correct_answer = line.replace("Правильный ответ:", "").strip()
        
        # Если не удалось распарсить, попробуем альтернативный формат
        if not question or len(options) != 3 or not correct_answer:
            logger.warning(f"Не удалось распарсить ответ LLM: {clean_response[:200]}...")
            # Попробуем найти вопрос и варианты по другим паттернам
            for line in lines:
                line = line.strip()
                if not question and ("?" in line or "равен" in line or "равна" in line):
                    question = line
                elif line.startswith("A)") or line.startswith("A."):
                    if len(options) < 3:  # Предотвращаем дублирование
                        options.append(line[2:].strip())
                elif line.startswith("B)") or line.startswith("B."):
                    if len(options) < 3:
                        options.append(line[2:].strip())
                elif line.startswith("C)") or line.startswith("C."):
                    if len(options) < 3:
                        options.append(line[2:].strip())
                elif "правильный" in line.lower() and ("A" in line or "B" in line or "C" in line):
                    # Ищем букву в строке с правильным ответом
                    for char in ['A', 'B', 'C']:
                        if char in line:
                            correct_answer = char
                            break
        
        # Если все еще нет правильного ответа, попробуем найти его в конце
        if not correct_answer:
            for line in reversed(lines):
                line = line.strip()
                if any(char in line for char in ['A', 'B', 'C']):
                    # Ищем последнюю букву A, B или C в строке
                    for char in ['C', 'B', 'A']:  # Проверяем в обратном порядке
                        if char in line:
                            correct_answer = char
                            break
                    if correct_answer:
                        break
        
        # Нормализуем правильный ответ
        if correct_answer in ['A', 'B', 'C']:
            correct_answer = correct_answer
        elif correct_answer.startswith('A)'):
            correct_answer = 'A'
        elif correct_answer.startswith('B)'):
            correct_answer = 'B'
        elif correct_answer.startswith('C)'):
            correct_answer = 'C'
        
        # Проверяем математическую корректность ответа
        if _is_mathematical_question(question):
            if not _validate_mathematical_answer(question, options, correct_answer):
                logger.warning(f"Математически некорректный ответ, генерируем новый")
                # Попробуем сгенерировать еще раз с новым промптом
                try:
                    # Добавляем еще больше рандомизации для повторной генерации
                    import random
                    retry_hints = [
                        "Используй ДРУГИЕ числа в вопросе",
                        "Создай вопрос с числами 2, 3, 4",
                        "Используй числа 1, 2, 3 для разнообразия",
                        "Сделай вопрос с числами 3, 4, 5"
                    ]
                    retry_hint = random.choice(retry_hints)
                    
                    retry_template = Template(TEST_GENERATION_PROMPT)
                    retry_prompt = retry_template.safe_substitute(
                        lesson_title=lesson.title,
                        lesson_content=lesson.content
                    )
                    
                    # Добавляем рандомизацию для повторной генерации
                    retry_prompt += f"\n\nКРИТИЧЕСКИ ВАЖНО: {retry_hint}. Это ПОВТОРНАЯ генерация - создай СОВСЕМ ДРУГОЙ вопрос!"
                    
                    response = await get_llm_response_for_test(retry_prompt)
                except Exception as retry_error:
                    logger.error(f"Ошибка повторной генерации: {retry_error}")
                    try:
                        await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
                    except Exception:
                        await callback_query.message.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
                    return
                
                clean_response = response.strip()
                if clean_response.startswith('<s>'):
                    clean_response = clean_response[3:].strip()
                if clean_response.startswith('</s>'):
                    clean_response = clean_response[:-4].strip()
                
                # Повторно парсим
                lines = clean_response.split('\n')
                question = ""
                options = []
                correct_answer = ""
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("Вопрос:"):
                        question = line.replace("Вопрос:", "").strip()
                    elif line.startswith("A)"):
                        options.append(line.replace("A)", "").strip())
                    elif line.startswith("B)"):
                        options.append(line.replace("B)", "").strip())
                    elif line.startswith("C)"):
                        options.append(line.replace("C)", "").strip())
                    elif line.startswith("Правильный ответ:"):
                        correct_answer = line.replace("Правильный ответ:", "").strip()
                
                # Нормализуем правильный ответ еще раз
                if correct_answer in ['A', 'B', 'C']:
                    correct_answer = correct_answer
                elif correct_answer.startswith('A)'):
                    correct_answer = 'A'
                elif correct_answer.startswith('B)'):
                    correct_answer = 'B'
                elif correct_answer.startswith('C)'):
                    correct_answer = 'C'
        
        if not question or len(options) != 3 or not correct_answer:
            logger.warning(f"LLM не смог сгенерировать валидный тест, создаем fallback вопрос")
            
            # Создаем простой fallback вопрос на основе темы урока
            if "вектор" in lesson.title.lower():
                question = "Что такое вектор в математике?"
                options = ["Направленный отрезок", "Число", "Точка"]
                correct_answer = "A"
            elif "матрица" in lesson.title.lower():
                question = "Что такое матрица?"
                options = ["Прямоугольная таблица чисел", "Вектор", "Функция"]
                correct_answer = "A"
            elif "собственн" in lesson.title.lower():
                question = "Что такое собственное значение матрицы?"
                options = ["Число λ такое, что Av = λv", "Определитель", "След"]
                correct_answer = "A"
            else:
                question = "Что изучается в этом уроке?"
                options = ["Математические концепции", "История", "Литература"]
                correct_answer = "A"
            
            logger.info(f"Создан fallback вопрос: {question}")
        
        if not question or len(options) != 3 or not correct_answer:
            await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            logger.error(f"Не удалось сгенерировать тест даже с fallback. Вопрос: '{question}', Варианты: {options}, Правильный: '{correct_answer}'")
            logger.error(f"Полный ответ LLM: {clean_response}")
            return
        
        # Создаем клавиатуру с вариантами ответов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"A) {options[0]}", callback_data=f"answer_{lesson_id}_A_{correct_answer}"),
                InlineKeyboardButton(text=f"B) {options[1]}", callback_data=f"answer_{lesson_id}_B_{correct_answer}")
            ],
            [
                InlineKeyboardButton(text=f"C) {options[2]}", callback_data=f"answer_{lesson_id}_C_{correct_answer}")
            ]
        ])
        
        test_text = f"🧪 Тест по уроку: {lesson.title}\n\n{question}\n\nВыберите правильный ответ:"
        
        await callback_query.message.edit_text(test_text, reply_markup=keyboard)
        try:
            await callback_query.answer()
        except Exception:
            # Callback query истек, но тест уже отправлен
            pass
        
    except Exception as e:
        logger.error(f"Ошибка генерации теста: {e}")
        try:
            await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
        except Exception:
            await callback_query.message.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")


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
                if not progress:
                    # Инициализируем прогресс пользователя, если его нет
                    db.init_user_progress(user_id, course_id)
                    progress = db.get_user_progress(user_id, course_id)
                
                if progress:
                    completed_lessons = progress.completed_lessons + 1
                    next_lesson = lesson.lesson_number + 1
                    db.update_user_progress(user_id, course_id, next_lesson, completed_lessons)
                    # Сохраняем информацию о завершенном уроке
                    db.complete_lesson(user_id, lesson.id)
                    logger.info(f"Обновлен прогресс пользователя {user_id}: урок {lesson.lesson_number} завершен, следующий урок {next_lesson}, завершено уроков {completed_lessons}")
            
            await callback_query.message.edit_text(
                "✅ Правильно! Урок завершен.\n\n"
                "Отлично! Вы успешно прошли тест. Можете перейти к следующему уроку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="➡️ Следующий урок", callback_data=f"lesson_{course_id}_{lesson.lesson_number+1}")
                    ],
                    [
                        InlineKeyboardButton(text="📚 Меню курса", callback_data=f"back_to_course_{course_id}")
                    ]
                ])
            )
        else:
            # Сохраняем ошибку
            db.add_test_error(user_id, lesson_id, "Тестовый вопрос", correct_answer, user_answer)
            
            # Получаем информацию об уроке для кнопки "Вернуться к уроку"
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
            
            await callback_query.message.edit_text(
                f"❌ Неправильно! Правильный ответ: {correct_answer}\n\n"
                "Вернитесь к уроку, чтобы повторить материал, а затем попробуйте тест снова.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📖 Вернуться к уроку", callback_data=f"lesson_{course_id}_{lesson.lesson_number}"),
                        InlineKeyboardButton(text="📚 Меню курса", callback_data=f"back_to_course_{course_id}")
                    ]
                ])
            )
        
        await callback_query.answer()
        

async def handle_photo(message: Message):
    """
    Обработка фотографий с использованием Vision API
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Фото от пользователя {user_id}")
    
    # Проверяем, есть ли у пользователя выбранный уровень
    current_level = extract_user_level(chat_id)
    if current_level is None:
        # Устанавливаем уровень по умолчанию без уведомления
        get_user_level_or_default(chat_id)
    
    # Отправляем индикатор обработки
    processing_msg = await message.answer("📷 Анализирую изображение...")
    
    try:
        # Получаем информацию о фото
        photo = message.photo[-1]  # Берем фото наибольшего размера
        file_id = photo.file_id
        
        # Получаем файл от Telegram
        bot = message.bot
        file = await bot.get_file(file_id)
        
        # Скачиваем файл
        file_content = await bot.download_file(file.file_path)
        
        # Конвертируем в base64
        import base64
        image_base64 = base64.b64encode(file_content.read()).decode('utf-8')
        
        # Определяем формат изображения
        image_format = "jpeg"  # По умолчанию
        if file.file_path:
            if file.file_path.lower().endswith('.png'):
                image_format = "png"
            elif file.file_path.lower().endswith('.gif'):
                image_format = "gif"
        
        # Получаем историю диалога
        dialog_history = get_dialog_history(chat_id)
        
        # Добавляем сообщение пользователя в историю
        caption = message.caption or "Проанализируй это изображение"
        add_user_message(chat_id, f"[ИЗОБРАЖЕНИЕ] {caption}")
        
        # Получаем обновленную историю диалога
        dialog_history = get_dialog_history(chat_id)
        
        # Импортируем Vision API клиент
        from llm.vision_client import get_vision_response
        
        # Получаем ответ от Vision API
        response = await get_vision_response(dialog_history, image_base64, image_format)
        
        if response:
            # Добавляем ответ в историю
            add_assistant_message(chat_id, response)
            
            # Отправляем ответ пользователю
            await processing_msg.edit_text(response)
            
            # Обновляем статистику прогресса
            progress_tracker.update_progress(user_id, caption, response)
        else:
            await processing_msg.edit_text(
                "❌ Не удалось проанализировать изображение. Попробуйте отправить другое фото или обратитесь к администратору."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {type(e).__name__}: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке изображения. Попробуйте отправить другое фото."
        )


async def handle_voice(message: Message):
    """
    Обработка голосовых сообщений
    
    Args:
        message: Объект сообщения с голосовым файлом
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Голосовое сообщение от пользователя {user_id}")
    
    # Проверяем, есть ли у пользователя выбранный уровень
    current_level = extract_user_level(chat_id)
    if current_level is None:
        # Устанавливаем уровень по умолчанию без уведомления
        get_user_level_or_default(chat_id)
    
    # Отправляем индикатор обработки
    processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Получаем информацию о голосовом файле
        voice = message.voice
        file_id = voice.file_id
        
        # Получаем файл от Telegram
        bot = message.bot
        file = await bot.get_file(file_id)
        
        # Скачиваем файл
        file_content = await bot.download_file(file.file_path)
        
        # Импортируем Speech API клиент
        from llm.speech_client import HuggingFaceSpeechClient
        
        # Создаем клиент для распознавания речи
        speech_client = HuggingFaceSpeechClient()
        
        # Проверяем, настроен ли клиент
        if not speech_client.api_token:
            await processing_msg.edit_text(
                "❌ Голосовые сообщения временно недоступны. "
                "Для их работы необходимо настроить Hugging Face API токен. "
                "Пожалуйста, используйте текстовые сообщения."
            )
            return
        
        # Конвертируем аудио в текст
        text = await speech_client.transcribe_audio_data(file_content.read(), ".ogg")
        
        if text and text.strip():
            # Добавляем сообщение пользователя в историю
            add_user_message(chat_id, text)
            
            # Получаем историю диалога
            dialog_history = get_dialog_history(chat_id)
            
            # Получаем ответ от LLM
            response = await get_llm_response(dialog_history)
            
            if response:
                # Добавляем ответ в историю
                add_assistant_message(chat_id, response)
                
                # Отправляем ответ пользователю
                await processing_msg.edit_text(response)
                
                # Обновляем статистику прогресса
                progress_tracker.update_progress(user_id, text, response)
            else:
                await processing_msg.edit_text(
                    f"🎤 **Распознанный текст:** {text}\n\n❌ Не удалось получить ответ. Попробуйте еще раз."
                )
        else:
            await processing_msg.edit_text(
                "❌ Не удалось распознать речь. Попробуйте записать сообщение еще раз или используйте текстовые сообщения."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {type(e).__name__}: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке голосового сообщения. Попробуйте записать еще раз или используйте текстовые сообщения."
        )


def _is_mathematical_question(question: str) -> bool:
    """Проверяет, является ли вопрос математическим"""
    math_keywords = ['вектор', 'матрица', 'умножение', 'скалярное произведение', 'детерминант', 'равен', 'равна', 'сумма', 'сложение', 'вычитание', 'деление']
    return any(keyword in question.lower() for keyword in math_keywords)


def _validate_mathematical_answer(question: str, options: list, correct_answer: str) -> bool:
    """Проверяет математическую корректность ответа"""
    try:
        import re
        
        # Проверка для скалярного произведения векторов
        if 'скалярное произведение' in question.lower():
            vectors = re.findall(r'\[([^\]]+)\]', question)
            if len(vectors) >= 2:
                try:
                    v1 = [int(x.strip()) for x in vectors[0].split(',')]
                    v2 = [int(x.strip()) for x in vectors[1].split(',')]
                    
                    if len(v1) == len(v2):
                        correct_result = sum(a * b for a, b in zip(v1, v2))
                        
                        # Проверяем, есть ли правильный ответ в вариантах
                        for option in options:
                            if str(correct_result) in option:
                                logger.info(f"Скалярное произведение: векторы {v1} и {v2}, правильный ответ: {correct_result}")
                                return True
                        
                        logger.warning(f"Скалярное произведение: правильный ответ {correct_result} не найден в вариантах {options}")
                        return False
                except Exception as e:
                    logger.warning(f"Ошибка парсинга векторов: {e}")
                    return False
        
        # Проверка для сложения векторов
        elif 'сумма' in question.lower() and 'вектор' in question.lower():
            vectors = re.findall(r'\[([^\]]+)\]', question)
            if len(vectors) >= 2:
                try:
                    v1 = [int(x.strip()) for x in vectors[0].split(',')]
                    v2 = [int(x.strip()) for x in vectors[1].split(',')]
                    
                    if len(v1) == len(v2):
                        correct_result = [a + b for a, b in zip(v1, v2)]
                        
                        # Проверяем, есть ли правильный ответ в вариантах
                        for option in options:
                            if str(correct_result) in option:
                                logger.info(f"Сложение векторов: векторы {v1} и {v2}, правильный ответ: {correct_result}")
                                return True
                        
                        logger.warning(f"Сложение векторов: правильный ответ {correct_result} не найден в вариантах {options}")
                        return False
                except Exception as e:
                    logger.warning(f"Ошибка парсинга векторов для сложения: {e}")
                    return False
        
        # Проверка для умножения матрицы на вектор
        elif 'матрица' in question.lower() and 'вектор' in question.lower():
            vectors = re.findall(r'\[([^\]]+)\]', question)
            if len(vectors) >= 2:
                try:
                    # Первый вектор - матрица (двумерная)
                    matrix_rows = []
                    vector = []
                    
                    # Парсим матрицу
                    for i, vec in enumerate(vectors[:-1]):
                        row = [int(x.strip()) for x in vec.split(',')]
                        matrix_rows.append(row)
                    
                    # Последний вектор - вектор
                    vector = [int(x.strip()) for x in vectors[-1].split(',')]
                    
                    if len(matrix_rows) > 0 and len(vector) > 0:
                        # Вычисляем произведение матрицы на вектор
                        result = []
                        for row in matrix_rows:
                            if len(row) == len(vector):
                                dot_product = sum(a * b for a, b in zip(row, vector))
                                result.append(dot_product)
                        
                        if result:
                            # Проверяем, есть ли правильный ответ в вариантах
                            for option in options:
                                if str(result) in option or all(str(x) in option for x in result):
                                    logger.info(f"Умножение матрицы на вектор: результат {result}")
                                    return True
                            
                            logger.warning(f"Умножение матрицы на вектор: правильный ответ {result} не найден в вариантах {options}")
                            return False
                except Exception as e:
                    logger.warning(f"Ошибка парсинга матрицы и вектора: {e}")
                    return False
        
        # Проверка для детерминанта
        elif 'детерминант' in question.lower():
            vectors = re.findall(r'\[([^\]]+)\]', question)
            if len(vectors) >= 2:
                try:
                    # Парсим матрицу 2x2
                    row1 = [int(x.strip()) for x in vectors[0].split(',')]
                    row2 = [int(x.strip()) for x in vectors[1].split(',')]
                    
                    if len(row1) == 2 and len(row2) == 2:
                        det = row1[0] * row2[1] - row1[1] * row2[0]
                        
                        # Проверяем, есть ли правильный ответ в вариантах
                        for option in options:
                            if str(det) in option:
                                logger.info(f"Детерминант: матрица {[row1, row2]}, результат: {det}")
                                return True
                        
                        logger.warning(f"Детерминант: правильный ответ {det} не найден в вариантах {options}")
                        return False
                except Exception as e:
                    logger.warning(f"Ошибка парсинга детерминанта: {e}")
                    return False
        
        return True  # Для не-математических вопросов или если не удалось распарсить
    except Exception as e:
        logger.warning(f"Ошибка валидации: {e}")
        return True  # В случае ошибки считаем валидным


# RAG обработчики (KISS принцип)


async def handle_pdf_file(message: Message):
    """Обработка загруженного PDF файла (KISS принцип)"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Загрузка PDF от пользователя {user_id}")
    
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте файл как документ.")
        return
    
    document = message.document
    file_name = document.file_name
    
    if not file_name:
        await message.answer("❌ Не удалось определить имя файла.")
        return
    
    # Проверяем, что это PDF
    if not file_name.lower().endswith('.pdf'):
        await message.answer(
            "❌ Поддерживаются только PDF файлы.\n\n"
            "Пожалуйста, отправьте PDF статью."
        )
        return
    
    # Отправляем индикатор обработки
    processing_msg = await message.answer("📄 Обрабатываю PDF статью...")
    
    try:
        # Скачиваем файл
        bot = message.bot
        file = await bot.get_file(document.file_id)
        file_content = await bot.download_file(file.file_path)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content.read())
            temp_path = temp_file.name
        
        # Обрабатываем документ через простую RAG систему
        rag_system = SimpleRAG()
        result = rag_system.process_pdf(temp_path)
        
        if result['success']:
            # Сохраняем в базу данных
            metadata = result['metadata']
            doc_id = db.add_document(
                title=metadata.get('title', Path(file_name).stem),
                content_preview=result['content_preview'],
                file_type='pdf',
                user_id=user_id,
                file_size=document.file_size,
                metadata=metadata,
                arxiv_id=metadata.get('arxiv_id'),
                authors=metadata.get('authors')
            )
            
            # Извлекаем темы из документа
            topics = rag_system.extract_document_topics()
            
            # Удаляем временный файл
            os.unlink(temp_path)
            
            # Формируем ответ
            title = metadata.get('title', Path(file_name).stem)
            authors = metadata.get('authors', '')
            arxiv_id = metadata.get('arxiv_id', '')
            
            # Экранируем специальные символы Markdown
            safe_title = title.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace('`', '\\`')
            safe_authors = authors.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace('`', '\\`')
            safe_arxiv_id = arxiv_id.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace('`', '\\`')
            
            success_text = f"✅ **Вы вошли в режим анализа документа!**\n\n"
            
            # Добавляем примеры вопросов
            success_text += "❓ **Примеры вопросов:**\n"
            success_text += "• О чем данная статья?\n"
            success_text += "• Какие методы использованы в статье?\n"
            success_text += "• В чём преимущество данных методов?\n\n"
            
            success_text += "💬 **Или задайте свой вопрос!**\n\n"
            success_text += "💡 **Для выхода из режима анализа документа используйте команду /exit**"
            
            await processing_msg.edit_text(success_text, parse_mode="Markdown")
            
        else:
            # Удаляем временный файл
            os.unlink(temp_path)
            
            await processing_msg.edit_text(
                f"❌ **Ошибка обработки PDF:**\n\n{result['error']}\n\n"
                "Попробуйте отправить другой файл или обратитесь к администратору.",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Ошибка обработки PDF: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке PDF файла.\n\n"
            "Попробуйте отправить файл еще раз."
        )
        
        # Удаляем временный файл если он существует
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)


async def get_rag_response(query: str, user_id: int, dialog_history: list) -> str:
    """Получение ответа через полноценную RAG систему (как в notebook)"""
    try:
        # Получаем документ пользователя
        user_doc = db.get_user_document(user_id)
        
        if not user_doc:
            logger.info(f"У пользователя {user_id} нет документа, используем обычный LLM")
            return await get_llm_response(dialog_history)
        
        # Создаем RAG систему и загружаем документ
        rag_system = SimpleRAG()
        
        # Получаем путь к файлу документа (если он сохранен)
        # Пока что используем content_preview для простоты
        document_text = user_doc.get('content_preview', '')
        
        if not document_text:
            logger.info(f"У документа пользователя {user_id} нет текста, используем обычный LLM")
            return await get_llm_response(dialog_history)
        
        # Создаем временный файл с содержимым документа для RAG системы
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(document_text)
            temp_path = temp_file.name
        
        try:
            # Обрабатываем документ через RAG систему
            # Проверяем, что это действительно PDF файл
            if temp_path.endswith('.txt'):
                # Для текстовых файлов используем простой подход
                logger.info("Обрабатываю текстовый файл как документ")
                
                # Создаем простую RAG систему без PDF парсинга
                rag_system = SimpleRAG()
                
                # Создаем временный PDF файл с содержимым
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pdf') as pdf_temp:
                    # Записываем содержимое как простой текст
                    pdf_temp.write(document_text)
                    pdf_temp_path = pdf_temp.name
                
                try:
                    # Используем простой подход - создаем векторное хранилище напрямую
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                    from langchain_core.documents import Document
                    from langchain_core.vectorstores import InMemoryVectorStore
                    
                    # Создаем документ из текста
                    doc = Document(page_content=document_text, metadata={"source": "uploaded_text"})
                    
                    # Разбиваем на чанки с умной логикой
                    chunks = rag_system._smart_chunk_split([doc], chunk_size=400, overlap=100)
                    
                    # Анализируем качество разбиения на чанки
                    logger.info("=" * 60)
                    logger.info("АНАЛИЗ ЧАНКОВ ПРИ ОБРАБОТКЕ ВОПРОСА")
                    logger.info("=" * 60)
                    logger.info(f"Исходный текст: {len(document_text):,} символов")
                    logger.info(f"Создано чанков: {len(chunks)}")
                    for i, chunk in enumerate(chunks):
                        logger.info(f"Чанк {i+1}: {len(chunk.page_content):3d} символов | {chunk.page_content[:80]}...")
                    logger.info("=" * 60)
                    
                    # Создаем векторное хранилище
                    try:
                        # Используем from_documents для создания векторного хранилища
                        rag_system.vector_store = InMemoryVectorStore.from_documents(
                            chunks,
                            embedding=rag_system.embeddings
                        )
                        logger.info(f"Векторное хранилище создано успешно с {len(chunks)} чанками")
                    except Exception as e:
                        logger.error(f"Ошибка создания векторного хранилища через from_documents: {e}")
                        # Fallback: добавляем по одному
                        rag_system.vector_store = InMemoryVectorStore(embedding=rag_system.embeddings)
                        for chunk in chunks:
                            try:
                                rag_system.vector_store.add_texts([chunk.page_content], [chunk.metadata])
                            except Exception as e2:
                                logger.error(f"Ошибка добавления чанка: {e2}")
                                continue
                    
                    # Создаем retriever
                    rag_system.retriever = rag_system.vector_store.as_retriever(search_kwargs={'k': 3})
                    
                    # Создаем RAG цепочки
                    rag_system._create_rag_chains()
                    
                finally:
                    if os.path.exists(pdf_temp_path):
                        os.unlink(pdf_temp_path)
            else:
                # Для PDF файлов используем обычную обработку
                result = rag_system.process_pdf(temp_path)
                
                if not result['success']:
                    logger.error(f"Ошибка обработки документа для RAG: {result['error']}")
                    return await get_llm_response(dialog_history)
            
            # Используем полноценную RAG систему для ответа
            rag_result = rag_system.answer_question(query, dialog_history)
            
            logger.info(f"RAG результат: source={rag_result['source']}, quality={rag_result['quality']}, chunks={rag_result.get('chunks_used', 0)}")
            
            if rag_result['source'] == 'error':
                logger.error(f"Ошибка RAG ответа: {rag_result['answer']}")
                return await get_llm_response(dialog_history)
            
            # Формируем ответ с префиксом в зависимости от источника и качества
            quality = rag_result.get('quality', 'low')
            
            if rag_result['source'] == 'document':
                # RAG нашла полноценный ответ в документе - показываем только его
                response = f"📄 Ответ RAG системы:\n{rag_result['answer']}"
            elif rag_result['source'] == 'document_partial':
                # RAG нашла частичный ответ в документе - показываем только его
                response = f"📄 Ответ RAG системы:\n{rag_result['answer']}"
            else:  # not_found
                # RAG система не нашла информацию в документе
                logger.info(f"RAG система не нашла информацию для вопроса: {query[:50]}...")
                
                # Сначала показываем ответ RAG системы
                response = f"📄 Ответ RAG системы:\n{rag_result['answer']}"
                
                # Если качество ответа низкое, добавляем общий ответ и веб-поиск
                if quality == 'low':
                    # Получаем общий ответ от базового промпта
                    general_response = await get_llm_response(dialog_history)
                    
                    # Убираем фразу "Могу рассказать про..." из ответа
                    import re
                    general_response = re.sub(r'\n\nМогу рассказать про.*?Хочешь\?', '', general_response, flags=re.DOTALL)
                    general_response = re.sub(r'Могу рассказать про.*?Хочешь\?', '', general_response, flags=re.DOTALL)
                    
                    # Убираем префиксы RAG системы из общего ответа
                    general_response = re.sub(r'📄 Ответ RAG системы:\s*', '', general_response)
                    general_response = re.sub(r'^Ответ RAG системы:\s*\n?', '', general_response, flags=re.MULTILINE)  # Удаляем без emoji
                    general_response = re.sub(r'📄 Ответ на основе документа:\s*', '', general_response)
                    general_response = re.sub(r'📄 Ответ на основе документа \(частично\):\s*', '', general_response)
                    
                    # Добавляем общий ответ
                    response += f"\n\n💡 Общий ответ:\n{general_response}"
                    
                    # Попытка веб-поиска через Tavily
                    logger.info(f"🌐 Пытаемся выполнить веб-поиск для вопроса: {query[:50]}...")
                    web_response = await search_with_tavily(query, max_results=2)
                    if web_response:
                        logger.info(f"✅ Веб-поиск вернул результаты (длина: {len(web_response)} символов)")
                        response += f"\n\n🌐 Дополнительная информация:\n{web_response}"
                    else:
                        logger.info("⚠️ Веб-поиск не вернул результатов или недоступен")
            
            # Добавляем напоминание о команде /exit
            response += "\n\n💡 Для выхода из режима анализа документа используйте команду /exit"
            
            logger.info(f"RAG ответ для пользователя {user_id} (источник: {rag_result['source']})")
            return response
            
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"Ошибка RAG для пользователя {user_id}: {e}")
        # При ошибке используем обычный LLM
        return await get_llm_response(dialog_history)


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
    
    # Обработчик команды /exit - выход из режима RAG
    dp.message.register(handle_exit, Command("exit"))
    
    # Обработчик команды /learn - выбор курсов
    dp.message.register(handle_learn, Command("learn"))
    
    # Обработчик команды /clear - очистка прогресса курсов
    dp.message.register(handle_clear, Command("clear"))
    
    # RAG обработчики (KISS принцип)
    dp.message.register(handle_pdf_file, F.document)
    
    # Обработчик неизвестных команд (команды, начинающиеся с /, но не зарегистрированные)
    dp.message.register(handle_unknown_command, F.text.startswith("/"))
    
    # Обработчик нажатий на кнопки выбора уровня
    dp.callback_query.register(handle_level_selection, F.data.startswith("level_"))
    dp.callback_query.register(handle_level_selection, F.data == "show_courses")
    
    # Обработчик выбора курсов
    dp.callback_query.register(handle_course_selection, F.data.startswith("course_"))
    dp.callback_query.register(handle_course_selection, F.data == "back_to_main")
    dp.callback_query.register(handle_course_selection, F.data == "back_to_courses")
    
    # Обработчики для курсов
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("lesson_"))
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("test_"))
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("start_learning_"))
    dp.callback_query.register(handle_lesson_callback, F.data == "back_to_menu")
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("back_to_course_"))
    dp.callback_query.register(handle_test_answer, F.data.startswith("answer_"))
    
    # Обработчик голосовых сообщений (должен быть перед общим обработчиком сообщений)
    dp.message.register(handle_voice, F.voice)
    
    # Обработчик фото сообщений (должен быть перед общим обработчиком сообщений)
    dp.message.register(handle_photo, F.photo)
    
    # Обработчик всех остальных текстовых сообщений через LLM с контекстом
    dp.message.register(handle_message)
