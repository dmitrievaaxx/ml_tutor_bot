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
from bot.database import Database
from bot.test_prompts import TEST_GENERATION_PROMPT

logger = logging.getLogger(__name__)

# Простой класс-обертка для совместимости с существующим кодом
class LearningProgressTracker:
    def __init__(self):
        pass
    
    def get_user_stats(self, user_id: int) -> dict:
        """Получить статистику пользователя"""
        progress = get_user_progress(user_id)
        
        # Получаем статистику тестов из базы данных
        test_errors = db.get_user_test_errors(user_id)
        successful_tests = max(0, len(progress) - len(test_errors))  # Примерная оценка
        
        return {
            'topics_studied': len(progress),
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
    
    Показывает приветствие и переводит в режим вопросов
    
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
    
    # Формируем приветственное сообщение
    welcome_text = f"""Привет!👋

Я помогу тебе разобраться в математических основах машинного обучения!

🎓 **Что я умею:**
• Структурированные курсы с 18 уроками по математике для ML
• Интерактивные тесты для проверки знаний после каждого урока
• Анализ изображений с формулами, схемами и диаграммами
• Голосовые вопросы и ответы на русском языке
• Адаптивные объяснения под твой уровень знаний

📚 **Программа курса:**
• Линейная алгебра (векторы, матрицы, собственные значения)
• Математический анализ (производные, градиенты, оптимизация)
• Вероятность и статистика (распределения, байесовская теорема)

🚀 **Как начать:**
1. Выбери свой уровень знаний ниже
2. Нажми "📖 Курсы" для изучения структурированного материала
3. Или просто задавай вопросы текстом, голосом или картинками!

📊 Выбери свой уровень знаний:"""
    
    # Создаем клавиатуру для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Новичок", callback_data="level_beginner"),
            InlineKeyboardButton(text="🟡 Базовый", callback_data="level_intermediate")
        ],
        [
            InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")
        ],
        [
            InlineKeyboardButton(text="📖 Курсы", callback_data="show_courses")
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
    
    status_text += f"📈 **Статистика:**\n"
    status_text += f"• Успешных тестов: {progress_stats.get('successful_tests', 0)}\n"
    status_text += f"• Ошибок в тестах: {progress_stats.get('test_errors', 0)}\n"
    status_text += f"• Время обучения: {progress_stats.get('learning_time', '0 мин')}\n"
    
    await message.answer(status_text, parse_mode="Markdown")


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
• `/start` - Начать работу с ботом
• `/learn` - Выбрать курс для изучения
• `/level` - Изменить уровень знаний
• `/status` - Показать текущий статус
• `/help` - Показать эту справку

**Как пользоваться:**
1. Выберите уровень знаний командой `/level`
2. Задавайте вопросы по машинному обучению
3. Изучайте курсы командой `/learn`
4. Отслеживайте прогресс в профиле

**Возможности:**
• Адаптивные ответы под ваш уровень
• Структурированные курсы с тестами
• Отслеживание прогресса обучения
• Голосовые сообщения (в разработке)

**Поддерживаемые темы:**
• Машинное обучение
• Математика для ML
• Программирование на Python
• Нейронные сети
• Обработка данных

Задавайте любые вопросы! 🚀
"""
    
    await message.answer(help_text, parse_mode="Markdown")


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
        
        # Формируем план курса с прогрессом
        plan_text = f"🧠 **МАТЕМАТИЧЕСКИЕ ОСНОВЫ ML**\n\n"
        plan_text += f"📊 Прогресс: {progress.completed_lessons}/{course.total_lessons} уроков завершено\n"
        plan_text += f"📍 Текущий урок: {progress.current_lesson}/{course.total_lessons}\n\n"
        
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
                is_completed = progress.completed_lessons >= i
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
                is_completed = progress.completed_lessons >= i
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
                is_completed = progress.completed_lessons >= i
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
        await callback_query.message.delete()
        await handle_start(callback_query.message)
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
        
        # Отправляем сообщение с подтверждением и приветствием
        level_emoji = "🟢" if level == "Новичок" else "🟡" if level == "Базовый" else "🔴"
        await callback_query.message.edit_text(
            f"✅ Уровень установлен: {level} {level_emoji}\n\n"
            f"{welcome_message}\n\n"
            "Теперь я буду адаптировать ответы под ваш уровень знаний. Задавайте любые вопросы!\n\n"
            "💡 Используйте команду /level для смены уровня.",
            parse_mode="Markdown"
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
        # Устанавливаем уровень по умолчанию и уведомляем пользователя
        default_level = get_user_level_or_default(chat_id)
        await message.answer(
            f"🟡 Уровень по умолчанию: **{default_level}**\n\n"
            f"Я буду отвечать на базовом уровне. Используйте команду /level для смены уровня.\n\n",
            parse_mode="Markdown"
        )
    
    # Добавляем сообщение пользователя в историю
    add_user_message(chat_id, text)
    
    # Отправляем индикатор генерации
    processing_msg = await message.answer("🤖 Формулирую понятное объяснение...")
    
    # Получаем историю диалога
    dialog_history = get_dialog_history(chat_id)
    
    # Отправляем запрос к LLM
    try:
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
        if progress:
            await callback_query.message.delete()
            await show_lesson(callback_query.message, course_id, progress.current_lesson)
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
        # Создаем новый callback query с правильными данными
        from aiogram.types import CallbackQuery
        new_callback = CallbackQuery(
            id=callback_query.id,
            from_user=callback_query.from_user,
            message=callback_query.message,
            data=f"course_{course_id}",
            chat_instance=callback_query.chat_instance
        )
        await handle_course_selection(new_callback)


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
            ],
            [
                InlineKeyboardButton(text="🔄 Новый вопрос", callback_data=f"test_{lesson_id}")
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
                if progress:
                    completed_lessons = progress.completed_lessons + 1
                    db.update_user_progress(user_id, course_id, lesson.lesson_number, completed_lessons)
            
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
        # Устанавливаем уровень по умолчанию и уведомляем пользователя
        default_level = get_user_level_or_default(chat_id)
        await message.answer(
            f"🟡 Уровень по умолчанию: **{default_level}**\n\n"
            f"Я буду отвечать на базовом уровне. Используйте команду /level для смены уровня.\n\n",
            parse_mode="Markdown"
        )
    
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
        # Устанавливаем уровень по умолчанию и уведомляем пользователя
        default_level = get_user_level_or_default(chat_id)
        await message.answer(
            f"🟡 Уровень по умолчанию: **{default_level}**\n\n"
            f"Я буду отвечать на базовом уровне. Используйте команду /level для смены уровня.\n\n",
            parse_mode="Markdown"
        )
    
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
    
    # Обработчик команды /learn - выбор курсов
    dp.message.register(handle_learn, Command("learn"))
    
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
