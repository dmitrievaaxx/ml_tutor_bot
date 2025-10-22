"""
Обработчики сообщений и команд для Telegram бота ML Tutor

Этот модуль содержит все обработчики для команд, сообщений и callback queries.
"""

import logging
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.dialog import clear_dialog, add_user_message, add_assistant_message, get_dialog_history, extract_user_level
from bot.prompts import get_system_prompt, get_welcome_message
from bot.progress import get_user_progress, mark_topic_completed
from llm.client import get_llm_response
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
        return {
            'topics_studied': len(progress),
            'learning_time': '0 мин'  # Заглушка
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
    
    welcome_text = get_welcome_message("Базовый")
    await message.answer(welcome_text)


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
    for course in courses:
        courses_text += f"📚 **{course.name}**\n"
        courses_text += f"   {course.description}\n"
        courses_text += f"   Уроков: {course.total_lessons}\n\n"
    
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
    
    # Создаем клавиатуру для выбора уровня
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Базовый", callback_data="level_beginner"),
            InlineKeyboardButton(text="🟡 Средний", callback_data="level_intermediate")
        ],
        [
            InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")
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
    chat_id = message.chat.id
    
    logger.info(f"Команда /status от пользователя {user_id}")
    
    # Получаем статистику диалога
    dialog_history = get_dialog_history(chat_id)
    current_level = extract_user_level(chat_id)
    
    # Получаем статистику прогресса
    progress_stats = progress_tracker.get_user_stats(user_id)
    
    status_text = f"📊 **Ваш текущий статус:**\n\n"
    status_text += f"🎯 **Уровень знаний:** {current_level}\n"
    status_text += f"💬 **Сообщений в диалоге:** {len(dialog_history)}\n"
    status_text += f"📈 **Изученных тем:** {progress_stats.get('topics_studied', 0)}\n"
    status_text += f"⏱️ **Время обучения:** {progress_stats.get('learning_time', '0 мин')}\n\n"
    status_text += "Используйте /level для смены уровня знаний."
    
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
• `/profile` - Мой профиль
• `/errors` - Мои ошибки в тестах
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
        plan_text = f"📚 **{course.name}**\n\n"
        plan_text += f"{course.description}\n\n"
        plan_text += f"📊 Прогресс: {progress.completed_lessons}/{course.total_lessons} уроков завершено\n"
        plan_text += f"📍 Текущий урок: {progress.current_lesson}/{course.total_lessons}\n\n"
        
        # Показываем уроки с галочками
        plan_text += "📋 План курса:\n"
        for i in range(1, course.total_lessons + 1):
            lesson = db.get_lesson(course_id, i)
            if lesson:
                # Проверяем, завершен ли урок
                is_completed = progress.completed_lessons >= i
                status = "✅" if is_completed else "⭕"
                plan_text += f"{status} Урок {i}: {lesson.title}\n"
        
        # Создаем клавиатуру
        keyboard_buttons = []
        
        if progress.current_lesson <= course.total_lessons:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🚀 Начать обучение", callback_data=f"start_learning_{course_id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="show_profile"),
            InlineKeyboardButton(text="❌ Мои ошибки", callback_data="show_errors")
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


async def handle_main_menu_buttons(callback_query: CallbackQuery):
    """
    Обработка кнопок главного меню
    
    Args:
        callback_query: Объект callback query от пользователя
    """
    data = callback_query.data
    
    if data == "show_profile":
        await handle_profile_command(callback_query.message)
        await callback_query.answer()
    
    elif data == "show_errors":
        await handle_errors_command(callback_query.message)
        await callback_query.answer()


async def handle_level_selection(callback_query: CallbackQuery):
    """
    Обработка выбора уровня знаний
    
    Args:
        callback_query: Объект callback query от пользователя
    """
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Маппинг callback_data на уровни
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
    Обработка обычных текстовых сообщений через LLM
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    logger.info(f"Сообщение от пользователя {user_id}: {text[:50]}...")
    
    # Добавляем сообщение пользователя в историю
    add_user_message(chat_id, text)
    
    # Получаем историю диалога
    dialog_history = get_dialog_history(chat_id)
    
    # Определяем уровень пользователя
    user_level = extract_user_level(chat_id)
    
    # Формируем системный промпт с учетом уровня
    system_prompt = get_system_prompt(user_level)
    
    # Отправляем запрос к LLM
    try:
        response = await get_llm_response(dialog_history)
        
        # Добавляем ответ в историю
        add_assistant_message(chat_id, response)
        
        # Отправляем ответ пользователю
        await message.answer(response)
        
        # Обновляем статистику прогресса
        progress_tracker.update_progress(user_id, text, response)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз.")


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
        
        response = await get_llm_response([{"role": "user", "content": prompt}])
        
        logger.info(f"Ответ LLM для генерации теста: {response[:300]}...")
        
        # Очищаем ответ от токенов модели
        clean_response = response.strip()
        if clean_response.startswith('<s>'):
            clean_response = clean_response[3:].strip()
        if clean_response.startswith('</s>'):
            clean_response = clean_response[:-4].strip()
        
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
                    correct_answer = line.split()[-1].strip()
        
        # Нормализуем правильный ответ
        if correct_answer in ['A', 'B', 'C']:
            correct_answer = correct_answer
        elif correct_answer.startswith('A)'):
            correct_answer = 'A'
        elif correct_answer.startswith('B)'):
            correct_answer = 'B'
        elif correct_answer.startswith('C)'):
            correct_answer = 'C'
        
        if not question or len(options) != 3 or not correct_answer:
            await callback_query.answer("❌ Ошибка генерации теста. Попробуйте еще раз.")
            logger.error(f"Не удалось сгенерировать тест. Вопрос: '{question}', Варианты: {options}, Правильный: '{correct_answer}'")
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
        await message.answer("📊 Вы еще не начали изучать курсы. Используйте /learn для начала.")
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


async def handle_voice(message: Message):
    """
    Обработка голосовых сообщений
    
    Args:
        message: Объект сообщения с голосовым файлом
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"Голосовое сообщение от пользователя {user_id}")
    
    # Пока что просто отвечаем, что функция в разработке
    await message.answer("🎤 Голосовые сообщения пока в разработке. Используйте текстовые сообщения.")


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
    
    # Обработчик команды /profile - профиль пользователя
    dp.message.register(handle_profile_command, Command("profile"))
    
    # Обработчик команды /errors - ошибки в тестах
    dp.message.register(handle_errors_command, Command("errors"))
    
    # Обработчик нажатий на кнопки выбора уровня
    dp.callback_query.register(handle_level_selection, F.data.startswith("level_"))
    
    # Обработчик выбора курсов
    dp.callback_query.register(handle_course_selection, F.data.startswith("course_"))
    dp.callback_query.register(handle_course_selection, F.data == "back_to_main")
    dp.callback_query.register(handle_course_selection, F.data == "back_to_courses")
    
    # Обработчик кнопок главного меню
    dp.callback_query.register(handle_main_menu_buttons, F.data.in_([
        "show_profile", "show_errors"
    ]))
    
    # Обработчики для курсов
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("lesson_"))
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("test_"))
    dp.callback_query.register(handle_lesson_callback, F.data.startswith("start_learning_"))
    dp.callback_query.register(handle_lesson_callback, F.data == "back_to_menu")
    dp.callback_query.register(handle_test_answer, F.data.startswith("answer_"))
    
    # Обработчик голосовых сообщений (должен быть перед общим обработчиком сообщений)
    dp.message.register(handle_voice, F.voice)
    
    # Обработчик всех остальных текстовых сообщений через LLM с контекстом
    dp.message.register(handle_message)
