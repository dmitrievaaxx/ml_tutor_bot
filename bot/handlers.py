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
from db.services import UserService, LearningProgressService, UserQuestionService, EducationService
from learning.topic_analyzer import topic_analyzer
from learning.learning_mode import learning_mode_manager
from learning.education_plans import education_plans_manager, EducationDirection
from learning.test_question_generator import TestQuestionGenerator
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
            InlineKeyboardButton(text="🎓 Режим обучения", callback_data="enter_learn_mode")
        ],
        [
            InlineKeyboardButton(text="📚 Сменить режим обучения", callback_data="switch_to_education")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="show_help")
        ]
    ])


async def handle_start(message: Message):
    """
    Обработка команды /start
    
    Показывает выбор режима работы (вопросы или обучение)
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    chat_id = message.chat.id
    
    logger.info(f"Команда /start от пользователя {user_id} (@{username})")
    
    # Создаем или обновляем пользователя в БД
    UserService.get_or_create_user(
        telegram_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    
    # Очистка истории при старте (начинаем с чистого листа)
    clear_dialog(chat_id)
    
    # Создаем кнопки для выбора режима
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❓ Режим вопросов", callback_data="mode_questions"),
            InlineKeyboardButton(text="🎓 Режим обучения", callback_data="mode_learning")
        ]
    ])
    
    await message.answer(
        "Привет!👋\n\n"
        "Я помогу тебе разобраться в машинном обучении, нейросетях и NLP — от основ до продвинутых концепций.\n\n"
        "Выберите режим работы:\n\n"
        "❓ **Режим вопросов** - задавайте вопросы по темам ML, DL, NLP, CV, Math. Я отвечу с учетом вашего уровня знаний!\n\n"
        "🎓 **Режим обучения** - структурированное обучение по темам с вопросами для закрепления знаний.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_mode_selection(callback_query: CallbackQuery):
    """
    Обработка выбора режима работы (вопросы или обучение)
    
    Args:
        callback_query: Callback query от кнопки
    """
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    logger.info(f"Выбор режима от пользователя {user_id} (@{username}): {data}")
    
    try:
        if data == "mode_questions":
            # Режим вопросов - показываем выбор уровня
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Новичок", callback_data="level_novice")],
                [InlineKeyboardButton(text="🟡 Базовый", callback_data="level_basic")],
                [InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")]
            ])
            
            await callback_query.message.edit_text(
                "❓ **Режим вопросов**\n\n"
                "Отлично! Теперь выберите свой уровень знаний, чтобы я мог адаптировать ответы под ваш уровень:\n\n"
                "🟢 **Новичок** - объяснения простыми словами с примерами из жизни\n"
                "🟡 **Базовый** - технические детали с объяснениями\n"
                "🔴 **Продвинутый** - глубокие концепции и современные подходы\n\n"
                "После выбора уровня вы сможете задавать вопросы по темам ML, DL, NLP, CV, Math!",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        elif data == "mode_learning":
            # Режим обучения - показываем только Math
            logger.info(f"Показываем режим обучения для пользователя {user_id}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔢 Math", callback_data="learn_topic_Math")
                ]
            ])
            
            await callback_query.message.edit_text(
                "🎓 **Режим обучения**\n\n"
                "Доступен курс по математическим основам машинного обучения:\n\n"
                "🔢 **Math** - Математические основы ML\n\n"
                "Курс включает 18 уроков по линейной алгебре, математическому анализу и теории вероятностей.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            logger.info(f"Клавиатура режима обучения отправлена пользователю {user_id}")
        
        # Подтверждаем callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора режима для пользователя {user_id}: {e}")
        await callback_query.message.edit_text(
            "😔 Произошла ошибка при выборе режима. Попробуйте позже."
        )


async def handle_switch_to_education(callback_query: CallbackQuery):
    """
    Обработка переключения в режим education
    
    Args:
        callback_query: Callback query от кнопки
    """
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    chat_id = callback_query.message.chat.id
    
    logger.info(f"Переключение в режим education от пользователя {user_id} (@{username})")
    
    try:
        # Создаем клавиатуру для выбора направления обучения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 ML", callback_data="edu_direction_ML"),
                InlineKeyboardButton(text="🧠 DL", callback_data="edu_direction_DL")
            ],
            [
                InlineKeyboardButton(text="💬 NLP", callback_data="edu_direction_NLP"),
                InlineKeyboardButton(text="👁️ CV", callback_data="edu_direction_CV")
            ],
            [
                InlineKeyboardButton(text="🔢 Math", callback_data="edu_direction_Math")
            ],
            [
                InlineKeyboardButton(text="🚀 Вернуться к вопросам", callback_data="back_to_questions")
            ]
        ])
        
        await callback_query.message.edit_text(
            "📚 **Режим структурированного обучения**\n\n"
            "Выберите направление для изучения:\n\n"
            "📚 **ML** - Машинное обучение\n"
            "🧠 **DL** - Глубокое обучение\n"
            "💬 **NLP** - Обработка естественного языка\n"
            "👁️ **CV** - Компьютерное зрение\n"
            "🔢 **Math** - Математические основы\n\n"
            "Каждое направление содержит структурированные уроки с тестами для закрепления знаний.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Подтверждаем callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при переключении в режим education для пользователя {user_id}: {e}")
        await callback_query.message.edit_text(
            "😔 Произошла ошибка при переключении в режим обучения. Попробуйте позже."
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


async def handle_profile(message: Message):
    """
    Обработка команды /profile
    
    Показывает детальный профиль пользователя
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /profile от пользователя {user_id} (@{username})")
    
    try:
        # Получаем информацию о пользователе
        user = UserService.get_user_by_telegram_id(user_id)
        if not user:
            await message.answer("Пользователь не найден. Используйте /start для регистрации.")
            return
        
        # Получаем статистику обучения
        learning_stats = LearningProgressService.get_learning_statistics(user_id)
        
        # Формируем сообщение профиля
        profile_message = f"👤 Профиль пользователя\n\n"
        
        # Основная информация
        profile_message += f"📊 Уровень знаний: {user.current_level or 'Не выбран'}\n"
        
        # Проверяем активную сессию обучения
        active_session = learning_mode_manager.get_active_session(user_id)
        if active_session:
            profile_message += f"🎓 Режим обучения: Активен (тема: {active_session.topic})\n"
        else:
            profile_message += f"🎓 Режим обучения: Неактивен\n"
        
        profile_message += "\n"
        
        # Статистика обучения
        profile_message += f"📚 Статистика обучения:\n"
        profile_message += f"• Изучено тем: {learning_stats.get('topics_studied', 0)}\n"
        profile_message += f"• Время изучения: {learning_stats.get('total_study_time_minutes', 0)} мин\n"
        profile_message += f"• Задано вопросов: {learning_stats.get('total_questions', 0)}\n"
        profile_message += f"• Средний прогресс: {learning_stats.get('average_progress', 0)}%\n\n"
        
        # Информация о сессии обучения
        if active_session:
            profile_message += f"🎯 Активная сессия обучения:\n"
            profile_message += f"• Тема: {active_session.topic}\n"
            profile_message += f"• Вопросов задано: {active_session.questions_asked}\n"
            profile_message += f"• Правильных ответов: {active_session.correct_answers}\n"
            profile_message += f"• Время сессии: {int((datetime.now() - active_session.start_time).total_seconds() / 60)} мин\n\n"
        
        profile_message += f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}\n"
        
        await message.answer(profile_message)
        
    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при получении профиля. "
            "Попробуйте позже."
        )


async def handle_question(message: Message):
    """
    Обработка команды /question
    
    Показывает неотвеченный вопрос на понимание
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /question от пользователя {user_id} (@{username})")
    
    try:
        # Получаем неотвеченный вопрос
        active_session = learning_mode_manager.get_active_session(user_id)
        
        if not active_session:
            await message.answer(
                "❓ У вас нет активной сессии обучения.\n\n"
                "Вопросы на понимание доступны только в режиме обучения. "
                "Используйте /learn чтобы включить режим обучения."
            )
            return
        
        # Генерируем вопрос на понимание
        question = learning_mode_manager.generate_comprehension_question(user_id)
        
        if question:
            await message.answer(f"🤔 Вопрос на понимание:\n\n{question}")
        else:
            await message.answer(
                "❓ Не удалось сгенерировать вопрос на понимание.\n\n"
                "Попробуйте задать несколько вопросов по теме, а затем используйте эту команду снова."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при получении вопроса для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при получении вопроса. "
            "Попробуйте позже."
        )


async def handle_education(message: Message):
    """
    Обработка команды /education
    
    Показывает интерфейс выбора направления обучения
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /education от пользователя {user_id} (@{username})")
    
    try:
        # Получаем текущий прогресс обучения
        education_progress = EducationService.get_user_education_progress(user_id)
        
        # Создаем клавиатуру с направлениями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 ML", callback_data="edu_direction_ML"),
                InlineKeyboardButton(text="🧠 DL", callback_data="edu_direction_DL")
            ],
            [
                InlineKeyboardButton(text="💬 NLP", callback_data="edu_direction_NLP"),
                InlineKeyboardButton(text="👁️ CV", callback_data="edu_direction_CV")
            ],
            [
                InlineKeyboardButton(text="🔢 Math", callback_data="edu_direction_Math")
            ]
        ])
        
        # Формируем сообщение
        education_message = "🎓 **Система образования**\n\n"
        education_message += "Выберите направление обучения:\n\n"
        education_message += "📚 **ML** - Машинное обучение\n"
        education_message += "🧠 **DL** - Глубокое обучение\n"
        education_message += "💬 **NLP** - Обработка естественного языка\n"
        education_message += "👁️ **CV** - Компьютерное зрение\n"
        education_message += "🔢 **Math** - Математические основы\n\n"
        
        if education_progress:
            education_message += "📊 **Ваши активные курсы:**\n"
            for progress in education_progress[:3]:  # Показываем максимум 3
                education_message += f"• {progress['title']} ({progress['progress_percentage']:.1f}%)\n"
        
        await message.answer(education_message, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка при показе системы образования для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при показе системы образования. "
            "Попробуйте позже."
        )


async def handle_learn(message: Message):
    """
    Обработка команды /learn
    
    Показывает интерфейс выбора режима обучения
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /learn от пользователя {user_id} (@{username})")
    
    try:
        # Проверяем, есть ли уже активная сессия
        active_session = learning_mode_manager.get_active_session(user_id)
        
        if active_session:
            await message.answer(
                f"🎓 Режим обучения уже активен!\n\n"
                f"Текущая тема: {active_session.topic}\n"
                f"Вопросов задано: {active_session.questions_asked}\n"
                f"Правильных ответов: {active_session.correct_answers}\n\n"
                f"Используйте /stop_learn чтобы завершить сессию."
            )
            return
        
        # Получаем темы, по которым пользователь задавал вопросы
        user_topics = UserQuestionService.get_user_topics_with_questions(user_id)
        
        # Создаем клавиатуру только с Math
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔢 Math", callback_data="learn_topic_Math")
            ],
            [
                InlineKeyboardButton(text="🚀 Вернуться к вопросам", callback_data="back_to_questions")
            ]
        ])
        
        # Формируем сообщение
        learn_message = "🎓 **Режим обучения**\n\n"
        learn_message += "Доступен курс по математическим основам машинного обучения:\n\n"
        learn_message += "🔢 **Math** - Математические основы ML\n\n"
        learn_message += "Курс включает 18 уроков по линейной алгебре, математическому анализу и теории вероятностей."
        
        await message.answer(learn_message, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка при показе режима обучения для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при показе режима обучения. "
            "Попробуйте позже."
        )


async def handle_education_direction_selection(callback_query: CallbackQuery):
    """
    Обработка выбора направления обучения
    
    Args:
        callback_query: Callback query от кнопки
    """
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    logger.info(f"Выбор направления обучения от пользователя {user_id} (@{username}): {data}")
    
    try:
        # Маппинг направлений (используется во всех блоках)
        direction_mapping = {
            "ML": EducationDirection.ML,
            "DL": EducationDirection.DL,
            "NLP": EducationDirection.NLP,
            "CV": EducationDirection.CV,
            "Math": EducationDirection.MATH
        }
        
        if data.startswith("edu_direction_"):
            direction_str = data.replace("edu_direction_", "")
            
            direction = direction_mapping.get(direction_str)
            if not direction:
                await callback_query.message.edit_text("❌ Неизвестное направление")
                return
            
            # Проверяем, есть ли план для этого направления
            plan = education_plans_manager.get_plan(direction)
            if not plan:
                await callback_query.message.edit_text(
                    f"❌ Учебный план для направления {direction.value} не найден.\n\n"
                    f"Доступные планы будут добавлены в следующих версиях."
                )
                return
            
            # Создаем клавиатуру для начала обучения
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🚀 Начать обучение", callback_data=f"edu_start_{direction.value}")
                ],
                [
                    InlineKeyboardButton(text="📊 Посмотреть план", callback_data=f"edu_plan_{direction.value}")
                ],
                [
                    InlineKeyboardButton(text="❓ Вернуться к вопросам", callback_data="back_to_questions")
                ],
                [
                    InlineKeyboardButton(text="⬅️ Назад", callback_data="edu_back")
                ]
            ])
            
            await callback_query.message.edit_text(
                f"📚 **{plan.title}**\n\n"
                f"{plan.description}\n\n"
                f"📖 **Уроков в курсе:** {len(plan.lessons)}\n"
                f"⏱️ **Примерное время:** {len(plan.lessons) * 15} минут\n\n"
                f"Выберите действие:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif data.startswith("edu_start_"):
            # Начать обучение
            direction_str = data.replace("edu_start_", "")
            direction = direction_mapping.get(direction_str)
            
            if direction:
                # Начинаем учебный план
                success = EducationService.start_education_plan(user_id, direction)
                
                if success:
                    # Получаем первый урок
                    lesson_info = EducationService.get_current_lesson(user_id, direction.value)
                    
                    if lesson_info:
                        # Создаем клавиатуру для навигации по урокам
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="⬅️ Предыдущая тема", callback_data=f"edu_prev_{direction.value}_{lesson_info['lesson_id']}"),
                                InlineKeyboardButton(text="Следующая тема ➡️", callback_data=f"edu_next_{direction.value}_{lesson_info['lesson_id']}")
                            ],
                            [
                                InlineKeyboardButton(text="📝 Тест", callback_data=f"edu_test_{direction.value}_{lesson_info['lesson_id']}")
                            ],
                            [
                                InlineKeyboardButton(text="📊 Прогресс", callback_data=f"edu_progress_{direction.value}"),
                                InlineKeyboardButton(text="⬅️ Назад к курсу", callback_data=f"edu_direction_{direction.value}")
                            ]
                        ])
                        
                        await callback_query.message.edit_text(
                            f"📘 Урок {lesson_info['lesson_number']}. {lesson_info['title']}\n\n"
                            f"{lesson_info['content']}",
                            reply_markup=keyboard,
                            parse_mode=None
                        )
                    else:
                        await callback_query.message.edit_text(
                            f"✅ Учебный план '{direction.value}' начат!\n\n"
                            f"Используйте команду /education чтобы продолжить обучение."
                        )
                else:
                    await callback_query.message.edit_text(
                        "❌ Не удалось начать учебный план. Попробуйте позже."
                    )
        
        elif data.startswith("edu_plan_"):
            # Показать план курса
            direction_str = data.replace("edu_plan_", "")
            direction = direction_mapping.get(direction_str)
            
            if direction:
                plan = education_plans_manager.get_plan(direction)
                if plan:
                    # Формируем план согласно новому формату
                    plan_text = f"📚 **{plan.title.replace('📚 ', '')}**\n\n"
                    
                    if direction.value == "Math":
                        plan_text += "▲ **ЛИНЕЙНАЯ АЛГЕБРА**\n"
                        for i in range(1, 6):  # уроки 1-5
                            if i <= len(plan.lessons):
                                lesson = plan.lessons[i-1]
                                plan_text += f"{i}. {lesson.title}\n"
                        
                        plan_text += "\n▲ **МАТАН И ОПТИМИЗАЦИЯ**\n"
                        # Уроки 6-7: Производные и градиенты
                        for i in range(6, 8):
                            if i <= len(plan.lessons):
                                lesson = plan.lessons[i-1]
                                plan_text += f"{i}. {lesson.title}\n"
                        # Урок 8: Градиенты в матричной форме (был урок 13)
                        if len(plan.lessons) >= 13:
                            lesson = plan.lessons[12]  # индекс 12 = урок 13
                            plan_text += f"8. {lesson.title}\n"
                        # Уроки 9-13: Остальные уроки оптимизации
                        for i in range(9, 14):
                            if i <= len(plan.lessons):
                                lesson = plan.lessons[i-1]
                                plan_text += f"{i}. {lesson.title}\n"
                        
                        plan_text += "\n▲ **ВЕРОЯТНОСТЬ И СТАТИСТИКА**\n"
                        for i in range(14, 19):  # уроки 14-18
                            if i <= len(plan.lessons):
                                lesson = plan.lessons[i-1]
                                plan_text += f"{i}. {lesson.title}\n"
                    else:
                        # Для других курсов используем старый формат
                        for i, lesson in enumerate(plan.lessons, 1):
                            plan_text += f"{i}. **{lesson.title}**\n   {lesson.description}\n\n"
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="🚀 Начать обучение", callback_data=f"edu_start_{direction.value}")
                        ],
                        [
                            InlineKeyboardButton(text="❓ Вернуться к вопросам", callback_data="back_to_questions")
                        ],
                        [
                            InlineKeyboardButton(text="⬅️ Назад", callback_data="edu_back")
                        ]
                    ])
                    
                    await callback_query.message.edit_text(
                        plan_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
        
        elif data.startswith("edu_prev_"):
            # Переход к предыдущему уроку
            # Парсим: edu_prev_Math_math_linear_1 -> direction=Math, lesson_id=math_linear_1
            data_parts = data.split("_", 3)  # Разбиваем только на 4 части
            if len(data_parts) >= 4:
                direction_str = data_parts[2]
                current_lesson_id = data_parts[3]
                direction = direction_mapping.get(direction_str)
                
                if direction:
                    # Получаем план и находим предыдущий урок
                    plan = education_plans_manager.get_plan(direction)
                    if plan:
                        current_index = None
                        for i, lesson in enumerate(plan.lessons):
                            if lesson.id == current_lesson_id:
                                current_index = i
                                break
                        
                        if current_index is not None and current_index > 0:
                            prev_lesson = plan.lessons[current_index - 1]
                            
                            # Создаем клавиатуру для навигации
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="⬅️ Предыдущая тема", callback_data=f"edu_prev_{direction.value}_{prev_lesson.id}"),
                                    InlineKeyboardButton(text="Следующая тема ➡️", callback_data=f"edu_next_{direction.value}_{prev_lesson.id}")
                                ],
                                [
                                    InlineKeyboardButton(text="📝 Тест", callback_data=f"edu_test_{direction.value}_{prev_lesson.id}")
                                ],
                                [
                                    InlineKeyboardButton(text="⬅️ Назад к курсу", callback_data=f"edu_direction_{direction.value}")
                                ]
                            ])
                            
                            await callback_query.message.edit_text(
                                f"📘 Урок {current_index + 1}. {prev_lesson.title}\n\n"
                                f"{prev_lesson.content}",
                                reply_markup=keyboard,
                                parse_mode=None
                            )
                        else:
                            await callback_query.answer("Это первый урок курса", show_alert=True)
        
        elif data.startswith("edu_next_"):
            # Переход к следующему уроку
            # Парсим: edu_next_Math_math_linear_1 -> direction=Math, lesson_id=math_linear_1
            data_parts = data.split("_", 3)  # Разбиваем только на 4 части
            if len(data_parts) >= 4:
                direction_str = data_parts[2]
                current_lesson_id = data_parts[3]
                direction = direction_mapping.get(direction_str)
                
                logger.info(f"Переход к следующему уроку: direction={direction_str}, current_lesson_id={current_lesson_id}")
                
                if direction:
                    # Получаем план и находим следующий урок
                    plan = education_plans_manager.get_plan(direction)
                    if plan:
                        current_index = None
                        for i, lesson in enumerate(plan.lessons):
                            if lesson.id == current_lesson_id:
                                current_index = i
                                break
                        
                        logger.info(f"Текущий индекс урока: {current_index}, всего уроков: {len(plan.lessons)}")
                        
                        if current_index is not None and current_index < len(plan.lessons) - 1:
                            next_lesson = plan.lessons[current_index + 1]
                            
                            # Создаем клавиатуру для навигации
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="⬅️ Предыдущая тема", callback_data=f"edu_prev_{direction.value}_{next_lesson.id}"),
                                    InlineKeyboardButton(text="Следующая тема ➡️", callback_data=f"edu_next_{direction.value}_{next_lesson.id}")
                                ],
                                [
                                    InlineKeyboardButton(text="📝 Тест", callback_data=f"edu_test_{direction.value}_{next_lesson.id}")
                                ],
                                [
                                    InlineKeyboardButton(text="⬅️ Назад к курсу", callback_data=f"edu_direction_{direction.value}")
                                ]
                            ])
                            
                            await callback_query.message.edit_text(
                                f"📘 Урок {current_index + 2}. {next_lesson.title}\n\n"
                                f"{next_lesson.content}",
                                reply_markup=keyboard,
                                parse_mode=None
                            )
                        else:
                            await callback_query.answer("Это последний урок курса", show_alert=True)
        
        elif data.startswith("edu_test_"):
            # Начать тест по уроку
            # Парсим: edu_test_Math_math_linear_1 -> direction=Math, lesson_id=math_linear_1
            data_parts = data.split("_", 3)  # Разбиваем только на 4 части
            if len(data_parts) >= 4:
                direction_str = data_parts[2]
                lesson_id = data_parts[3]
                direction = direction_mapping.get(direction_str)
                
                if direction:
                    # Получаем информацию об уроке
                    lesson_info = EducationService.get_lesson_by_id(lesson_id)
                    
                    if lesson_info:
                        # Показываем индикатор загрузки
                        await callback_query.message.edit_text(
                            "🔄 Генерирую тестовый вопрос...",
                            parse_mode=None
                        )
                        
                        # Генерируем тестовый вопрос через OpenRouter API
                        test_generator = TestQuestionGenerator()
                        test_data = await test_generator.generate_test_question(
                            lesson_info['title'],
                            lesson_info['content']
                        )
                        
                        if test_data:
                            # Создаем клавиатуру с вариантами ответов
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text=f"1️⃣ {test_data['options'][0]}", callback_data=f"test_answer_{direction.value}_{lesson_id}_0")
                                ],
                                [
                                    InlineKeyboardButton(text=f"2️⃣ {test_data['options'][1]}", callback_data=f"test_answer_{direction.value}_{lesson_id}_1")
                                ],
                                [
                                    InlineKeyboardButton(text=f"3️⃣ {test_data['options'][2]}", callback_data=f"test_answer_{direction.value}_{lesson_id}_2")
                                ],
                                [
                                    InlineKeyboardButton(text="⬅️ Назад к уроку", callback_data=f"edu_lesson_{direction.value}_{lesson_id}")
                                ]
                            ])
                            
                            await callback_query.message.edit_text(
                                f"📝 **Тест по уроку:** {lesson_info['title']}\n\n"
                                f"**Вопрос:**\n{test_data['question']}\n\n"
                                f"Выберите правильный ответ:",
                                reply_markup=keyboard,
                                parse_mode=None
                            )
                            
                            # Сохраняем данные теста в сессии (временно)
                            # В реальном приложении лучше использовать Redis или базу данных
                            if not hasattr(callback_query.from_user, 'test_data'):
                                callback_query.from_user.test_data = {}
                            callback_query.from_user.test_data[f"{direction.value}_{lesson_id}"] = test_data
                        else:
                            await callback_query.message.edit_text(
                                "❌ Не удалось сгенерировать тестовый вопрос. Попробуйте позже.",
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="⬅️ Назад к уроку", callback_data=f"edu_lesson_{direction.value}_{lesson_id}")]
                                ]),
                                parse_mode=None
                            )
                    else:
                        await callback_query.answer("Урок не найден", show_alert=True)
        
        elif data.startswith("test_answer_"):
            # Обработка ответа на тест
            parts = data.split("_")
            if len(parts) >= 5:
                direction_str = parts[2]
                lesson_id = parts[3]
                answer_index = int(parts[4])
                direction = direction_mapping.get(direction_str)
                
                if direction:
                    # Получаем данные теста из сессии
                    test_key = f"{direction.value}_{lesson_id}"
                    if hasattr(callback_query.from_user, 'test_data') and test_key in callback_query.from_user.test_data:
                        test_data = callback_query.from_user.test_data[test_key]
                        
                        is_correct = answer_index == test_data['correct_answer']
                        
                        # Получаем информацию об уроке
                        lesson_info = EducationService.get_lesson_by_id(lesson_id)
                        
                        if is_correct:
                            # Правильный ответ - отмечаем урок как пройденный
                            user_service = UserService(callback_query.bot.get('db'))
                            user = user_service.get_user_by_telegram_id(callback_query.from_user.id)
                            
                            if user:
                                progress_service = LearningProgressService(callback_query.bot.get('db'))
                                progress_service.mark_lesson_completed(user.id, lesson_id)
                            
                            result_text = "✅ Правильно! Урок пройден!"
                            explanation_text = f"\n\n**Объяснение:** {test_data['explanation']}"
                            
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="⬅️ Назад к уроку", callback_data=f"edu_lesson_{direction.value}_{lesson_id}")],
                                [InlineKeyboardButton(text="📊 Прогресс", callback_data=f"edu_progress_{direction.value}")]
                            ])
                        else:
                            # Неправильный ответ - объясняем ошибку
                            result_text = "❌ Неправильно!"
                            explanation_text = f"\n\n**Объяснение:** {test_data['explanation']}\n\nЕсли хотите попробовать снова, нажмите кнопку 'Тест' еще раз - будет другой вопрос."
                            
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="📝 Попробовать снова", callback_data=f"edu_test_{direction.value}_{lesson_id}")],
                                [InlineKeyboardButton(text="⬅️ Назад к уроку", callback_data=f"edu_lesson_{direction.value}_{lesson_id}")]
                            ])
                        
                        await callback_query.message.edit_text(
                            f"{result_text}{explanation_text}",
                            reply_markup=keyboard,
                            parse_mode=None
                        )
                        
                        # Очищаем данные теста из сессии
                        if hasattr(callback_query.from_user, 'test_data'):
                            del callback_query.from_user.test_data[test_key]
                    else:
                        await callback_query.answer("Данные теста не найдены. Попробуйте начать тест заново.", show_alert=True)
        
        elif data.startswith("edu_progress_"):
            # Показать прогресс обучения
            direction_str = data.split("_")[2]
            direction = direction_mapping.get(direction_str)
            
            if direction:
                user_service = UserService(callback_query.bot.get('db'))
                user = user_service.get_user_by_telegram_id(callback_query.from_user.id)
                
                if user:
                    progress_service = LearningProgressService(callback_query.bot.get('db'))
                    progress_info = progress_service.get_user_progress(user.id, direction.value)
                    
                    if "error" not in progress_info:
                        # Формируем текст прогресса
                        progress_text = f"📊 **Прогресс по курсу {direction.value}**\n\n"
                        progress_text += f"✅ Пройдено уроков: {progress_info['completed_lessons']}/{progress_info['total_lessons']}\n"
                        progress_text += f"📈 Процент завершения: {progress_info['completion_percentage']:.1f}%\n\n"
                        
                        # Добавляем список уроков с галочками
                        progress_text += "**Уроки:**\n"
                        for lesson in progress_info['lessons']:
                            status = "✅" if lesson['is_completed'] else "⏳"
                            progress_text += f"{status} {lesson['lesson_number']}. {lesson['title']}\n"
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⬅️ Назад к курсу", callback_data=f"edu_start_{direction.value}")]
                        ])
                        
                        await callback_query.message.edit_text(
                            progress_text,
                            reply_markup=keyboard,
                            parse_mode=None
                        )
                    else:
                        await callback_query.answer("Ошибка при получении прогресса", show_alert=True)
        
        elif data.startswith("edu_lesson_"):
            # Вернуться к уроку
            # Парсим: edu_lesson_Math_math_linear_1 -> direction=Math, lesson_id=math_linear_1
            data_parts = data.split("_", 3)  # Разбиваем только на 4 части
            if len(data_parts) >= 4:
                direction_str = data_parts[2]
                lesson_id = data_parts[3]
                direction = direction_mapping.get(direction_str)
                
                if direction:
                    # Получаем информацию об уроке
                    lesson_info = EducationService.get_lesson_by_id(lesson_id)
                    
                    if lesson_info:
                        # Получаем план для определения номера урока
                        plan = education_plans_manager.get_plan(direction)
                        lesson_number = 1
                        if plan:
                            for i, lesson in enumerate(plan.lessons):
                                if lesson.id == lesson_id:
                                    lesson_number = i + 1
                                    break
                        
                        # Создаем клавиатуру для навигации
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="⬅️ Предыдущая тема", callback_data=f"edu_prev_{direction.value}_{lesson_id}"),
                                InlineKeyboardButton(text="Следующая тема ➡️", callback_data=f"edu_next_{direction.value}_{lesson_id}")
                            ],
                            [
                                InlineKeyboardButton(text="📝 Тест", callback_data=f"edu_test_{direction.value}_{lesson_id}")
                            ],
                            [
                                InlineKeyboardButton(text="⬅️ Назад к курсу", callback_data=f"edu_direction_{direction.value}")
                            ]
                        ])
                        
                        await callback_query.message.edit_text(
                            f"📘 Урок {lesson_number}. {lesson_info['title']}\n\n"
                            f"{lesson_info['content']}",
                            reply_markup=keyboard,
                            parse_mode=None
                        )
        
        elif data == "back_to_questions":
            # Вернуться к режиму вопросов
            keyboard = create_questions_mode_keyboard()
            
            await callback_query.message.edit_text(
                "❓ **Режим задавания вопросов**\n\n"
                "Теперь вы можете задавать любые вопросы по машинному обучению, "
                "и я буду отвечать на них с учетом вашего уровня подготовки.\n\n"
                "Просто напишите ваш вопрос, и я постараюсь дать максимально "
                "понятный и полезный ответ!",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        elif data == "edu_back":
            # Вернуться к выбору направления
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📚 ML", callback_data="edu_direction_ML"),
                    InlineKeyboardButton(text="🧠 DL", callback_data="edu_direction_DL")
                ],
                [
                    InlineKeyboardButton(text="💬 NLP", callback_data="edu_direction_NLP"),
                    InlineKeyboardButton(text="👁️ CV", callback_data="edu_direction_CV")
                ],
                [
                    InlineKeyboardButton(text="🔢 Math", callback_data="edu_direction_Math")
                ]
            ])
            
            await callback_query.message.edit_text(
                "🎓 **Система образования**\n\n"
                "Выберите направление обучения:\n\n"
                "📚 **ML** - Машинное обучение\n"
                "🧠 **DL** - Глубокое обучение\n"
                "💬 **NLP** - Обработка естественного языка\n"
                "👁️ **CV** - Компьютерное зрение\n"
                "🔢 **Math** - Математические основы",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        # Подтверждаем callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора направления обучения для пользователя {user_id}: {e}")
        await callback_query.message.edit_text(
            "😔 Произошла ошибка при выборе направления обучения. "
            "Попробуйте позже."
        )


async def handle_test_answer(callback_query: CallbackQuery):
    """
    Обработка ответа на тестовый вопрос
    
    Args:
        callback_query: Callback query от кнопки ответа
    """
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    logger.info(f"=== handle_test_answer ВЫЗВАНА ===")
    logger.info(f"Ответ на тестовый вопрос от пользователя {user_id} (@{username}): {data}")
    
    try:
        # Парсим callback data: test_answer_{lesson_id}_{question_index}_{answer_index}
        # Формат: test_answer_math_linear_1_0_0
        # lesson_id может содержать подчеркивания, поэтому парсим с конца
        parts = data.split("_")
        logger.info(f"Разделенные части: {parts}")
        logger.info(f"Количество частей: {len(parts)}")
        
        if len(parts) < 5:
            logger.error(f"Ошибка: ожидалось минимум 5 частей, получено {len(parts)}")
            await callback_query.message.edit_text("❌ Ошибка в данных теста")
            return
        
        # Извлекаем данные с конца
        answer_index = int(parts[-1])  # Последняя часть
        question_index = int(parts[-2])  # Предпоследняя часть
        lesson_id = "_".join(parts[2:-2])  # Все части между test_answer и question_index
        
        logger.info(f"Извлеченные значения:")
        logger.info(f"  lesson_id: {lesson_id}")
        logger.info(f"  question_index: {question_index}")
        logger.info(f"  answer_index: {answer_index}")
        
        # Получаем информацию об уроке
        lesson_info = EducationService.get_lesson_by_id(lesson_id)
        if not lesson_info:
            await callback_query.message.edit_text("❌ Урок не найден")
            return
        
        question = lesson_info['test_questions'][question_index]
        is_correct = answer_index == question['correct_answer']
        
        logger.info(f"Вопрос: {question['question']}")
        logger.info(f"Выбранный ответ: {answer_index} - {question['options'][answer_index]}")
        logger.info(f"Правильный ответ: {question['correct_answer']} - {question['options'][question['correct_answer']]}")
        logger.info(f"Результат: {'Правильно' if is_correct else 'Неправильно'}")
        
        # Сохраняем результат ответа
        EducationService.submit_test_answer(
            user_id, lesson_id, question_index, 
            question['options'][answer_index], 
            question['options'][question['correct_answer']], 
            is_correct, question['explanation']
        )
        
        # Показываем результат
        if is_correct:
            result_text = "✅ **Правильно!**"
        else:
            result_text = f"❌ **Неправильно!**\n\nПравильный ответ: {question['options'][question['correct_answer']]}"
        
        result_text += f"\n\n💡 **Объяснение:**\n{question['explanation']}"
        
        logger.info(f"Отображаем результат: {result_text[:100]}...")
        
        # Проверяем, есть ли еще вопросы
        if question_index < 2:  # Есть еще вопросы (0, 1, 2)
            next_question = lesson_info['test_questions'][question_index + 1]
            
            # Создаем клавиатуру для следующего вопроса
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"1️⃣ {next_question['options'][0]}", callback_data=f"test_answer_{lesson_id}_{question_index + 1}_0")
                ],
                [
                    InlineKeyboardButton(text=f"2️⃣ {next_question['options'][1]}", callback_data=f"test_answer_{lesson_id}_{question_index + 1}_1")
                ],
                [
                    InlineKeyboardButton(text=f"3️⃣ {next_question['options'][2]}", callback_data=f"test_answer_{lesson_id}_{question_index + 1}_2")
                ]
            ])
            
            await callback_query.message.edit_text(
                f"{result_text}\n\n"
                f"📖 **Вопрос {question_index + 2} из 3:**\n{next_question['question']}\n\n"
                f"Выберите правильный ответ:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # Тест завершен, показываем итоговые результаты
            test_results = EducationService.get_lesson_test_results(user_id, lesson_id)
            correct_count = sum(1 for result in test_results if result['is_correct'])
            
            if correct_count == 3:
                # Урок пройден успешно
                EducationService.complete_lesson(user_id, lesson_id)
                await callback_query.message.edit_text(
                    f"{result_text}\n\n"
                    f"🎉 **Поздравляем! Урок пройден успешно!**\n\n"
                    f"✅ Правильных ответов: {correct_count}/3\n"
                    f"📚 Урок: {lesson_info['title']}\n\n"
                    f"Вы можете перейти к следующему уроку или повторить этот урок.",
                    parse_mode="Markdown"
                )
            else:
                # Урок не пройден
                await callback_query.message.edit_text(
                    f"{result_text}\n\n"
                    f"📊 **Результаты тестирования:**\n\n"
                    f"✅ Правильных ответов: {correct_count}/3\n"
                    f"📚 Урок: {lesson_info['title']}\n\n"
                    f"Для прохождения урока нужно ответить правильно на все 3 вопроса.\n"
                    f"Вы можете повторить тест, написав 'тест'.",
                    parse_mode="Markdown"
                )
        
        # Подтверждаем callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на тест для пользователя {user_id}: {e}")
        await callback_query.message.edit_text(
            "😔 Произошла ошибка при обработке ответа. "
            "Попробуйте позже."
        )


async def handle_lesson_test_start(message: Message):
    """
    Обработка начала тестирования по уроку
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Начало тестирования от пользователя {user_id} (@{username})")
    
    try:
        # Получаем активные учебные планы пользователя
        education_progress = EducationService.get_user_education_progress(user_id)
        
        if not education_progress:
            await message.answer(
                "❌ У вас нет активных учебных планов.\n\n"
                "Используйте команду /education чтобы начать обучение."
            )
            return
        
        # Находим план с текущим уроком
        current_plan = None
        for progress in education_progress:
            if progress['current_lesson_id']:
                current_plan = progress
                break
        
        if not current_plan:
            await message.answer(
                "❌ У вас нет активных уроков для тестирования.\n\n"
                "Используйте команду /education чтобы продолжить обучение."
            )
            return
        
        # Получаем информацию о текущем уроке
        lesson_info = EducationService.get_current_lesson(user_id, current_plan['plan_key'])
        
        if not lesson_info:
            await message.answer(
                "❌ Не удалось получить информацию о текущем уроке.\n\n"
                "Попробуйте позже или используйте /education."
            )
            return
        
        # Проверяем, есть ли уже результаты тестирования для этого урока
        test_results = EducationService.get_lesson_test_results(user_id, lesson_info['lesson_id'])
        
        if test_results:
            # Показываем результаты предыдущего тестирования
            correct_count = sum(1 for result in test_results if result['is_correct'])
            total_questions = len(test_results)
            
            await message.answer(
                f"📊 **Результаты предыдущего тестирования:**\n\n"
                f"✅ Правильных ответов: {correct_count}/{total_questions}\n"
                f"📚 Урок: {lesson_info['title']}\n\n"
                f"Хотите пройти тест заново? Напишите 'да' для повторного тестирования."
            )
            return
        
        # Начинаем новое тестирование
        first_question = lesson_info['test_questions'][0]
        
        # Создаем клавиатуру с вариантами ответов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"1️⃣ {first_question['options'][0]}", callback_data=f"test_answer_{lesson_info['lesson_id']}_0_0")
            ],
            [
                InlineKeyboardButton(text=f"2️⃣ {first_question['options'][1]}", callback_data=f"test_answer_{lesson_info['lesson_id']}_0_1")
            ],
            [
                InlineKeyboardButton(text=f"3️⃣ {first_question['options'][2]}", callback_data=f"test_answer_{lesson_info['lesson_id']}_0_2")
            ]
        ])
        
        await message.answer(
            f"📝 **Тестирование по уроку: {lesson_info['title']}**\n\n"
            f"📖 **Вопрос 1 из 3:**\n{first_question['question']}\n\n"
            f"Выберите правильный ответ:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Сохраняем состояние тестирования в сессии (можно использовать Redis или базу данных)
        # Пока используем простой подход с сохранением в базе данных
        
    except Exception as e:
        logger.error(f"Ошибка при начале тестирования для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при начале тестирования. "
            "Попробуйте позже."
        )


async def handle_lesson_test_answer(message: Message) -> bool:
    """
    Обработка ответа на тестовый вопрос
    
    Args:
        message: Объект сообщения от пользователя
        
    Returns:
        bool: True если сообщение было обработано как ответ на тест
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    user_text = message.text
    
    try:
        # Получаем активные учебные планы пользователя
        education_progress = EducationService.get_user_education_progress(user_id)
        
        if not education_progress:
            return False
        
        # Находим план с текущим уроком
        current_plan = None
        for progress in education_progress:
            if progress['current_lesson_id']:
                current_plan = progress
                break
        
        if not current_plan:
            return False
        
        # Получаем информацию о текущем уроке
        lesson_info = EducationService.get_current_lesson(user_id, current_plan['plan_key'])
        
        if not lesson_info:
            return False
        
        # Проверяем, есть ли результаты тестирования для этого урока
        test_results = EducationService.get_lesson_test_results(user_id, lesson_info['lesson_id'])
        
        # Определяем номер следующего вопроса
        next_question_number = len(test_results) + 1
        
        if next_question_number > 3:
            # Все вопросы уже отвечены
            return False
        
        # Проверяем, является ли это ответом на тестовый вопрос
        # Простая эвристика: если пользователь недавно начал тест и написал короткий ответ
        if len(user_text) < 200 and next_question_number <= 3:
            # Обрабатываем как ответ на тестовый вопрос
            logger.info(f"Обрабатываем ответ на тестовый вопрос {next_question_number} от пользователя {user_id}")
            
            # Отправляем ответ на проверку
            is_correct, correct_answer, explanation = EducationService.submit_test_answer(
                user_id, 
                current_plan['plan_key'], 
                lesson_info['lesson_id'], 
                next_question_number, 
                user_text
            )
            
            if is_correct:
                await message.answer(
                    f"✅ **Правильно!**\n\n"
                    f"📝 **Правильный ответ:** {correct_answer}\n\n"
                    f"💡 **Объяснение:** {explanation}",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"❌ **Не совсем правильно.**\n\n"
                    f"📝 **Правильный ответ:** {correct_answer}\n\n"
                    f"💡 **Объяснение:** {explanation}",
                    parse_mode="Markdown"
                )
            
            # Проверяем, все ли вопросы отвечены
            updated_test_results = EducationService.get_lesson_test_results(user_id, lesson_info['lesson_id'])
            correct_count = sum(1 for result in updated_test_results if result['is_correct'])
            
            if len(updated_test_results) >= 3:
                # Все вопросы отвечены
                if correct_count == 3:
                    # Все ответы правильные - урок завершен
                    EducationService.complete_lesson(user_id, current_plan['plan_key'], lesson_info['lesson_id'])
                    
                    # Получаем следующий урок
                    next_lesson = EducationService.get_current_lesson(user_id, current_plan['plan_key'])
                    
                    if next_lesson:
                        await message.answer(
                            f"🎉 **Поздравляем! Урок завершен!**\n\n"
                            f"✅ Все 3 вопроса отвечены правильно!\n\n"
                            f"📚 **Следующий урок:** {next_lesson['title']}\n"
                            f"📖 Урок {next_lesson['lesson_number']}/{next_lesson['total_lessons']}\n\n"
                            f"Напишите 'тест' чтобы начать тестирование по следующему уроку.",
                            parse_mode=None
                        )
                    else:
                        await message.answer(
                            f"🎉 **Поздравляем! Курс завершен!**\n\n"
                            f"✅ Все уроки курса '{current_plan['title']}' пройдены!\n\n"
                            f"Используйте /education чтобы выбрать новый курс.",
                            parse_mode=None
                        )
                else:
                    # Не все ответы правильные
                    await message.answer(
                        f"📊 **Тестирование завершено!**\n\n"
                        f"✅ Правильных ответов: {correct_count}/3\n\n"
                        f"Урок не засчитан как пройденный. Вы можете:\n"
                        f"• Перейти к следующему уроку (напишите 'дальше')\n"
                        f"• Повторить тест позже (напишите 'тест')\n\n"
                        f"Что выберете?",
                        parse_mode="Markdown"
                    )
            else:
                # Есть еще вопросы
                await message.answer(
                    f"📝 **Вопрос {next_question_number + 1} из 3:**\n{lesson_info['test_questions'][next_question_number]}\n\n"
                    f"Напишите ваш ответ:",
                    parse_mode="Markdown"
                )
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на тест для пользователя {user_id}: {e}")
        return False


async def handle_next_lesson(message: Message):
    """
    Обработка перехода к следующему уроку
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Переход к следующему уроку от пользователя {user_id} (@{username})")
    
    try:
        # Получаем активные учебные планы пользователя
        education_progress = EducationService.get_user_education_progress(user_id)
        
        if not education_progress:
            await message.answer(
                "❌ У вас нет активных учебных планов.\n\n"
                "Используйте команду /education чтобы начать обучение."
            )
            return
        
        # Находим план с текущим уроком
        current_plan = None
        for progress in education_progress:
            if progress['current_lesson_id']:
                current_plan = progress
                break
        
        if not current_plan:
            await message.answer(
                "❌ У вас нет активных уроков.\n\n"
                "Используйте команду /education чтобы продолжить обучение."
            )
            return
        
        # Получаем информацию о текущем уроке
        lesson_info = EducationService.get_current_lesson(user_id, current_plan['plan_key'])
        
        if not lesson_info:
            await message.answer(
                "❌ Не удалось получить информацию о текущем уроке.\n\n"
                "Попробуйте позже или используйте /education."
            )
            return
        
        # Переходим к следующему уроку
        success = EducationService.move_to_next_lesson(user_id, current_plan['plan_key'], lesson_info['lesson_id'])
        
        if success:
            # Получаем информацию о следующем уроке
            next_lesson = EducationService.get_current_lesson(user_id, current_plan['plan_key'])
            
            if next_lesson:
                await message.answer(
                    f"➡️ **Переход к следующему уроку!**\n\n"
                    f"📚 **Урок {next_lesson['lesson_number']}/{next_lesson['total_lessons']}:** {next_lesson['title']}\n\n"
                    f"{next_lesson['content']}\n\n"
                    f"Готовы к тестированию? Напишите 'тест' чтобы начать тест по этому уроку.",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"🎉 **Поздравляем! Курс завершен!**\n\n"
                    f"✅ Все уроки курса '{current_plan['title']}' пройдены!\n\n"
                    f"Используйте /education чтобы выбрать новый курс.",
                    parse_mode="Markdown"
                )
        else:
            await message.answer(
                "❌ Не удалось перейти к следующему уроку.\n\n"
                "Попробуйте позже или используйте /education."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при переходе к следующему уроку для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при переходе к следующему уроку. "
            "Попробуйте позже."
        )


async def handle_retry_test(message: Message):
    """
    Обработка повторного тестирования
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Повторное тестирование от пользователя {user_id} (@{username})")
    
    try:
        # Получаем активные учебные планы пользователя
        education_progress = EducationService.get_user_education_progress(user_id)
        
        if not education_progress:
            await message.answer(
                "❌ У вас нет активных учебных планов.\n\n"
                "Используйте команду /education чтобы начать обучение."
            )
            return
        
        # Находим план с текущим уроком
        current_plan = None
        for progress in education_progress:
            if progress['current_lesson_id']:
                current_plan = progress
                break
        
        if not current_plan:
            await message.answer(
                "❌ У вас нет активных уроков для тестирования.\n\n"
                "Используйте команду /education чтобы продолжить обучение."
            )
            return
        
        # Получаем информацию о текущем уроке
        lesson_info = EducationService.get_current_lesson(user_id, current_plan['plan_key'])
        
        if not lesson_info:
            await message.answer(
                "❌ Не удалось получить информацию о текущем уроке.\n\n"
                "Попробуйте позже или используйте /education."
            )
            return
        
        # Проверяем, есть ли результаты тестирования для этого урока
        test_results = EducationService.get_lesson_test_results(user_id, lesson_info['lesson_id'])
        
        if not test_results:
            # Нет результатов тестирования - начинаем новое тестирование
            await message.answer(
                f"📝 **Тестирование по уроку: {lesson_info['title']}**\n\n"
                f"📖 **Вопрос 1 из 3:**\n{lesson_info['test_questions'][0]}\n\n"
                f"Напишите ваш ответ:",
                parse_mode="Markdown"
            )
        else:
            # Есть результаты - показываем их и предлагаем повторить
            correct_count = sum(1 for result in test_results if result['is_correct'])
            total_questions = len(test_results)
            
            await message.answer(
                f"🔄 **Повторное тестирование по уроку: {lesson_info['title']}**\n\n"
                f"📊 **Предыдущий результат:** {correct_count}/{total_questions} правильных ответов\n\n"
                f"📝 **Вопрос 1 из 3:**\n{lesson_info['test_questions'][0]}\n\n"
                f"Напишите ваш ответ:",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Ошибка при повторном тестировании для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при повторном тестировании. "
            "Попробуйте позже."
        )


async def handle_mode(message: Message):
    """
    Обработка команды /mode
    
    Позволяет переключиться между режимом вопросов и режимом обучения
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /mode от пользователя {user_id} (@{username})")
    
    # Создаем кнопки для выбора режима
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❓ Режим вопросов", callback_data="mode_questions"),
            InlineKeyboardButton(text="🎓 Режим обучения", callback_data="mode_learning")
        ]
    ])
    
    await message.answer(
        "🔄 **Смена режима работы**\n\n"
        "Выберите режим работы:\n\n"
        "❓ **Режим вопросов** - задавайте вопросы по темам ML, DL, NLP, CV, Math. Я отвечу с учетом вашего уровня знаний!\n\n"
        "🎓 **Режим обучения** - структурированное обучение по темам с вопросами для закрепления знаний.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_help(message: Message):
    """
    Обработка команды /help
    
    Показывает справку и инструкции
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /help от пользователя {user_id} (@{username})")
    
    help_message = """❓ **Помощь и инструкции**
        
        🚀 **Режим задавания вопросов** (основной):
        • Задавайте вопросы по темам ML, DL, NLP, CV, Math
        • Присылайте изображения с формулами, схемами, диаграммами
        • Записывайте голосовые сообщения с вопросами
        
        🎓 **Режим обучения**:
        • Задайте вопрос - получите объяснение + вопрос для закрепления
        • Выберите тему для аттестации знаний
        • Правильные ответы добавляют прогресс
        
        📚 **Режим структурированного обучения**:
        • Выберите направление (ML, DL, NLP, CV, Math)
        • Проходите уроки с тестами для закрепления
        • Отслеживайте прогресс по темам
        
        📊 **Команды**:
        • /start - начать работу с выбором режима
        • /mode - сменить режим работы
        • /level - сменить уровень знаний
        • /status - показать текущий статус
        • /profile - детальный профиль
        • /learn - режим обучения
        • /help - эта справка
        
        💡 **Советы**:
        • Выберите подходящий уровень знаний для лучших ответов
        • Используйте режим обучения для закрепления материала
        • Присылайте изображения для анализа формул и схем
        
        🔧 **Поддержка**:
        • Изображения: формулы, схемы, диаграммы
        • Голосовые сообщения: вопросы и объяснения
        • Текстовые сообщения: любые вопросы по темам"""
    
    await message.answer(help_message, parse_mode="Markdown")


async def handle_main_menu_buttons(callback_query: CallbackQuery):
    """
    Обработка кнопок главного меню (из режима вопросов)
    
    Args:
        callback_query: Callback query от кнопки
    """
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    logger.info(f"Нажатие кнопки главного меню от пользователя {user_id} (@{username}): {data}")
    
    try:
        if data == "change_level":
            # Показать выбор уровня
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Новичок", callback_data="level_novice")],
                [InlineKeyboardButton(text="🟡 Базовый", callback_data="level_basic")],
                [InlineKeyboardButton(text="🔴 Продвинутый", callback_data="level_advanced")]
            ])
            
            await callback_query.message.edit_text(
                "📊 **Смена уровня знаний**\n\n"
                "Выберите новый уровень знаний:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        elif data == "show_status":
            # Показать статус
            current_level = UserService.get_user_level(user_id)
            if current_level:
                status_message = f"📊 **Текущий статус**\n\n"
                status_message += f"Уровень знаний: {current_level}\n"
                status_message += f"Режим: Задавание вопросов\n\n"
                status_message += f"Используйте /learn для перехода в режим обучения."
            else:
                status_message = "📊 Уровень знаний не выбран\n\nИспользуй /start чтобы выбрать уровень или /level для смены"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Главное меню", callback_data="back_to_main")]
            ])
            
            await callback_query.message.edit_text(
                status_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        elif data == "show_profile":
            # Показать профиль
            user = UserService.get_user_by_telegram_id(user_id)
            if not user:
                await callback_query.message.edit_text("Пользователь не найден.")
                return
            
            learning_stats = LearningProgressService.get_learning_statistics(user_id)
            
            profile_message = f"👤 **Профиль пользователя**\n\n"
            profile_message += f"📊 Уровень знаний: {user.current_level or 'Не выбран'}\n"
            profile_message += f"📚 Изучено тем: {learning_stats.get('topics_studied', 0)}\n"
            profile_message += f"⏱️ Время изучения: {learning_stats.get('total_study_time_minutes', 0)} мин\n"
            profile_message += f"❓ Задано вопросов: {learning_stats.get('total_questions', 0)}\n"
            profile_message += f"📈 Средний прогресс: {learning_stats.get('average_progress', 0)}%\n"
            profile_message += f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Главное меню", callback_data="back_to_main")]
            ])
            
            await callback_query.message.edit_text(
                profile_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        elif data == "enter_learn_mode":
            # Перейти в режим обучения
            await callback_query.message.edit_text(
                "🎓 Переходим в режим обучения...",
                reply_markup=None
            )
            
            # Вызываем функцию handle_learn
            await handle_learn(callback_query.message)
            
        elif data == "switch_to_education":
            # Переключиться в режим education
            await handle_switch_to_education(callback_query)
            
        elif data == "show_help":
            # Показать помощь
            help_message = """❓ **Помощь и инструкции**
        
        🚀 **Режим задавания вопросов** (текущий):
        • Задавайте вопросы по темам ML, DL, NLP, CV, Math
        • Присылайте изображения с формулами, схемами, диаграммами
        • Записывайте голосовые сообщения с вопросами
        
        🎓 **Режим обучения**:
        • Задайте вопрос - получите объяснение + вопрос для закрепления
        • Выберите тему для аттестации знаний
        • Правильные ответы добавляют прогресс
        
        📚 **Режим структурированного обучения**:
        • Выберите направление (ML, DL, NLP, CV, Math)
        • Проходите уроки с тестами для закрепления
        • Отслеживайте прогресс по темам
        
        📊 **Команды**:
        • /start - вернуться в режим вопросов
        • /level - сменить уровень знаний
        • /status - показать текущий статус
        • /profile - детальный профиль
        • /learn - режим обучения
        • /help - эта справка
        
        💡 **Советы**:
        • Выберите подходящий уровень знаний для лучших ответов
        • Используйте режим обучения для закрепления материала
        • Присылайте изображения для анализа формул и схем"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Главное меню", callback_data="back_to_main")]
            ])
            
            await callback_query.message.edit_text(
                help_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        elif data == "back_to_main":
            # Вернуться в главное меню
            current_level = UserService.get_user_level(user_id)
            if current_level:
                keyboard = create_questions_mode_keyboard()
                
                await callback_query.message.edit_text(
                    f"🚀 **Режим задавания вопросов**\n\n"
                    f"📊 Уровень: {current_level}\n\n"
                    f"Задавайте вопросы по темам ML, DL, NLP, CV или Math. "
                    f"Я отвечу с учетом вашего уровня знаний!\n\n"
                    f"Также можете присылать изображения с формулами, схемами или диаграммами, "
                    f"или записывать голосовые сообщения.",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        
        # Подтверждаем callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки главного меню для пользователя {user_id}: {e}")
        await callback_query.message.edit_text(
            "😔 Произошла ошибка. Попробуйте позже."
        )


async def handle_learn_mode_selection(callback_query: CallbackQuery):
    """
    Обработка выбора режима обучения
    
    Args:
        callback_query: Callback query от кнопки
    """
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or "пользователь"
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    logger.info(f"=== handle_learn_mode_selection вызвана ===")
    logger.info(f"Обработка режима обучения: {data} от пользователя {user_id} (@{username})")
    logger.info(f"Callback data: '{data}'")
    logger.info(f"Data starts with learn_: {data.startswith('learn_')}")
    logger.info(f"Data equals back_to_questions: {data == 'back_to_questions'}")
    
    try:
        if data.startswith("learn_topic_"):
            # Режим выбора темы для аттестации
            topic_category = data.replace("learn_topic_", "")
            logger.info(f"Обработка темы обучения: {topic_category} для пользователя {user_id}")
            logger.info(f"Callback data: {data}")
            
            # Маппинг категорий на названия тем
            topic_mapping = {
                "ML": "Машинное обучение",
                "DL": "Нейронные сети", 
                "NLP": "Обработка естественного языка",
                "CV": "Компьютерное зрение",
                "Math": "Математические основы"
            }
            
            logger.info(f"Topic mapping keys: {list(topic_mapping.keys())}")
            logger.info(f"Looking for: '{topic_category}'")
            
            topic_name = topic_mapping.get(topic_category)
            if not topic_name:
                logger.error(f"Неизвестная тема: {topic_category}")
                await callback_query.message.edit_text("❌ Неизвестная тема")
                return
            
            # Специальная обработка для Math - переход в структурированное обучение
            if topic_category == "Math":
                logger.info(f"Переход в структурированное обучение Math для пользователя {user_id}")
                # Переходим в режим структурированного обучения для Math
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📚 Начать обучение", callback_data="edu_direction_Math"),
                        InlineKeyboardButton(text="📋 Посмотреть план", callback_data="edu_plan_Math")
                    ],
                    [
                        InlineKeyboardButton(text="🚀 Вернуться к вопросам", callback_data="back_to_questions")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    "🔢 **Математические основы ML**\n\n"
                    "Выберите действие:\n\n"
                    "📚 **Начать обучение** - пройти структурированный курс по математике для ML\n"
                    "📋 **Посмотреть план** - ознакомиться с содержанием курса\n\n"
                    "Курс включает 18 уроков по линейной алгебре, математическому анализу и теории вероятностей.",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                # Для других тем используем старую логику с LLM
                # Создаем сессию обучения для конкретной темы
                session = learning_mode_manager.start_learning_session(user_id, topic=topic_name)
                
                # Генерируем первый вопрос по теме
                question = learning_mode_manager.generate_comprehension_question(user_id)
                
                if question:
                    await callback_query.message.edit_text(
                        f"📚 **Аттестация по теме: {topic_name}**\n\n"
                        f"🤔 **Вопрос:**\n{question}\n\n"
                        f"Отвечайте на вопросы, и я буду оценивать ваши знания!",
                        parse_mode="Markdown"
                    )
                else:
                    await callback_query.message.edit_text(
                        f"📚 **Аттестация по теме: {topic_name}**\n\n"
                        f"К сожалению, не удалось сгенерировать вопрос. "
                        f"Попробуйте задать вопрос по теме самостоятельно.",
                        parse_mode="Markdown"
                    )
        
        elif data == "back_to_questions":
            # Вернуться в режим вопросов
            current_level = UserService.get_user_level(user_id)
            if current_level:
                keyboard = create_questions_mode_keyboard()
                
                await callback_query.message.edit_text(
                    f"🚀 **Режим задавания вопросов**\n\n"
                    f"📊 Уровень: {current_level}\n\n"
                    f"Задавайте вопросы по темам ML, DL, NLP, CV или Math. "
                    f"Я отвечу с учетом вашего уровня знаний!\n\n"
                    f"Также можете присылать изображения с формулами, схемами или диаграммами, "
                    f"или записывать голосовые сообщения.",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await callback_query.message.edit_text(
                    "❌ Уровень знаний не выбран. Используйте /start для выбора уровня."
                )
        
        # Подтверждаем callback
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора режима обучения для пользователя {user_id}: {e}")
        await callback_query.message.edit_text(
            "😔 Произошла ошибка при выборе режима обучения. "
            "Попробуйте позже."
        )


async def handle_stop_learn(message: Message):
    """
    Обработка команды /stop_learn
    
    Завершает режим обучения
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /stop_learn от пользователя {user_id} (@{username})")
    
    try:
        # Завершаем сессию обучения
        session_stats = learning_mode_manager.end_learning_session(user_id)
        
        if session_stats:
            await message.answer(
                f"🎓 Сессия обучения завершена!\n\n"
                f"📊 Результаты сессии:\n"
                f"• Тема: {session_stats['topic']}\n"
                f"• Время изучения: {session_stats['duration_minutes']} мин\n"
                f"• Вопросов задано: {session_stats['questions_asked']}\n"
                f"• Правильных ответов: {session_stats['correct_answers']}\n"
                f"• Точность: {session_stats['accuracy']:.1f}%\n"
                f"• Получено прогресса: +{session_stats['progress_gained']:.1f}%\n\n"
                f"Отличная работа! Используйте /learn чтобы начать новую сессию."
            )
        else:
            await message.answer(
                "❌ У вас нет активной сессии обучения.\n\n"
                "Используйте /learn чтобы начать обучение."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при завершении режима обучения для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при завершении режима обучения. "
            "Попробуйте позже."
        )
    """
    Обработка команды /history
    
    Показывает историю изученных тем и прогресс обучения
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /history от пользователя {user_id} (@{username})")
    
    try:
        # Получаем статистику обучения
        stats = LearningProgressService.get_learning_statistics(user_id)
        
        if not stats or stats.get('topics_studied', 0) == 0:
            await message.answer(
                "📚 История обучения пуста\n\n"
                "Начни изучать темы, задавая вопросы боту! "
                "Я буду отслеживать твой прогресс по каждой теме."
            )
            return
        
        # Получаем недавние темы
        recent_topics = LearningProgressService.get_recent_topics(user_id, limit=5)
        
        # Формируем сообщение со статистикой
        stats_message = f"📊 Статистика обучения:\n\n"
        stats_message += f"📚 Изучено тем: {stats['topics_studied']}\n"
        stats_message += f"⏱️ Время изучения: {stats['total_study_time_minutes']} мин\n"
        stats_message += f"❓ Задано вопросов: {stats['total_questions']}\n"
        stats_message += f"📈 Средний прогресс: {stats['average_progress']}%\n\n"
        
        if recent_topics:
            stats_message += "🕒 Недавно изученные темы:\n"
            for i, topic in enumerate(recent_topics, 1):
                stats_message += f"{i}. {topic}\n"
        
        await message.answer(stats_message)
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории обучения для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при получении истории обучения. "
            "Попробуйте позже."
        )


async def handle_history(message: Message):
    """
    Обработка команды /history
    
    Показывает историю изученных тем и прогресс обучения
    
    Args:
        message: Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    chat_id = message.chat.id
    
    logger.info(f"Команда /history от пользователя {user_id} (@{username})")
    
    try:
        # Получаем историю обучения
        learning_stats = LearningProgressService.get_learning_statistics(user_id)
        
        if not learning_stats or learning_stats.get('topics_studied', 0) == 0:
            await message.answer(
                "📚 История обучения пуста.\n\n"
                "Начните задавать вопросы по темам машинного обучения, "
                "и здесь появится информация о вашем прогрессе!"
            )
            return
        
        # Формируем сообщение с историей
        history_message = f"📚 История обучения\n\n"
        history_message += f"📊 Общая статистика:\n"
        history_message += f"• Изучено тем: {learning_stats.get('topics_studied', 0)}\n"
        history_message += f"• Время изучения: {learning_stats.get('total_study_time_minutes', 0)} мин\n"
        history_message += f"• Задано вопросов: {learning_stats.get('total_questions', 0)}\n"
        history_message += f"• Средний прогресс: {learning_stats.get('average_progress', 0)}%\n\n"
        
        # Получаем детальную информацию по темам
        user_progress = LearningProgressService.get_user_progress(user_id)
        
        if user_progress:
            history_message += f"📖 Детальный прогресс по темам:\n"
            for progress in user_progress[:10]:  # Показываем максимум 10 тем
                topic_name = progress['topic_name']
                progress_pct = progress['progress_percentage']
                last_studied = progress['last_studied_at']
                
                # Определяем эмодзи по прогрессу
                if progress_pct >= 80:
                    emoji = "🌟"
                elif progress_pct >= 60:
                    emoji = "✅"
                elif progress_pct >= 40:
                    emoji = "🔄"
                else:
                    emoji = "📚"
                
                history_message += f"{emoji} {topic_name}: {progress_pct:.1f}%\n"
            
            if len(user_progress) > 10:
                history_message += f"... и еще {len(user_progress) - 10} тем\n"
        
        history_message += f"\n💡 Используйте /learn чтобы включить режим обучения с вопросами на понимание!"
        
        await message.answer(history_message)
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории обучения для пользователя {user_id}: {e}")
        await message.answer(
            "😔 Произошла ошибка при получении истории обучения. "
            "Попробуйте позже."
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
    
    # Проверяем, выбран ли уровень знаний у пользователя
    current_level = UserService.get_user_level(user_id)
    if current_level is None:
        # Если уровень не выбран, устанавливаем "Базовый" по умолчанию
        UserService.update_user_level(user_id, "Базовый")
        await message.answer("✅ Выбран уровень: Базовый")
        logger.info(f"Автоматически установлен уровень 'Базовый' для пользователя {user_id}")
    
    # Проверяем, находится ли пользователь в процессе тестирования по уроку
    if text.lower().strip() == "тест":
        await handle_lesson_test_start(message)
        return
    
    # Проверяем, является ли сообщение ответом на тестовый вопрос
    if await handle_lesson_test_answer(message):
        return
    
    # Проверяем команду "дальше" для перехода к следующему уроку
    if text.lower().strip() in ["дальше", "далее", "следующий урок"]:
        await handle_next_lesson(message)
        return
    
    # Проверяем команду "да" для повторного тестирования
    if text.lower().strip() in ["да", "yes", "повторить", "заново"]:
        await handle_retry_test(message)
        return
    
    # Проверяем активную сессию обучения
    active_session = learning_mode_manager.get_active_session(user_id)
    if active_session:
        # Если это режим "Вопросы пользователя" - обрабатываем как обычный вопрос
        if active_session.topic == "Вопросы пользователя":
            # Обрабатываем как обычный вопрос, но в режиме обучения
            # Логика будет в основном блоке обработки
            pass
        else:
            # Если это аттестация по теме - проверяем ответ
            if active_session.questions_asked > 0:
                # Проверяем, является ли это ответом на вопрос на понимание
                # Простая эвристика: если сообщение короткое и содержит ключевые слова
                if len(text) < 100 and any(word in text.lower() for word in ['да', 'нет', 'правильно', 'неправильно', 'верно', 'неверно']):
                    is_correct, explanation = learning_mode_manager.check_answer(user_id, text)
                    await message.answer(f"{explanation}\n\nПродолжайте отвечать на вопросы или используйте /stop_learn чтобы завершить сессию.")
                    return
    
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
        
        # Обновляем прогресс обучения и сохраняем вопрос
        try:
            topic_name, confidence = topic_analyzer.extract_topic_from_question(text)
            if confidence > 20:  # Только если уверенность больше 20%
                # Сохраняем вопрос пользователя
                topic_info = topic_analyzer.get_topic_info(topic_name)
                if topic_info:
                    UserQuestionService.save_user_question(
                        telegram_id=user_id,
                        question_text=text,
                        topic_name=topic_name,
                        topic_category=topic_info.category,
                        confidence_score=confidence
                    )
                    logger.info(f"Сохранен вопрос пользователя {user_id} по теме '{topic_name}'")
                
                LearningProgressService.update_progress(
                    telegram_id=user_id,
                    topic_name=topic_name,
                    progress_delta=3.0,  # +3% за вопрос
                    study_duration_minutes=2,  # Примерно 2 минуты на вопрос
                    questions_asked=1
                )
                logger.info(f"Обновлен прогресс по теме '{topic_name}' для пользователя {user_id}")
                
                # Если включен режим обучения, создаем вопрос на понимание
                active_session = learning_mode_manager.get_active_session(user_id)
                if active_session:
                    if active_session.topic == "Вопросы пользователя":
                        # В режиме "Вопросы пользователя" генерируем вопрос на закрепление
                        question = learning_mode_manager.generate_comprehension_question(user_id)
                        if question:
                            await message.answer(f"🤔 **Вопрос для закрепления:**\n\n{question}\n\nОтвечайте на вопрос, и я оценю ваши знания!", parse_mode="Markdown")
                            logger.info(f"Создан вопрос на закрепление по теме '{topic_name}' для пользователя {user_id}")
                    else:
                        # В режиме аттестации генерируем обычный вопрос на понимание
                        question = learning_mode_manager.generate_comprehension_question(user_id)
                        if question:
                            await message.answer(f"🤔 Вопрос на понимание:\n\n{question}")
                            logger.info(f"Создан вопрос на понимание по теме '{topic_name}' для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресса обучения: {e}")
        
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
        
        # Сначала определяем, первый ли это выбор уровня
        is_first = is_first_level_selection(user_id)
        
        # Обновляем уровень пользователя в БД
        UserService.update_user_level(user_id, level)
        
        # Добавляем сообщение о выборе уровня в историю
        add_user_message(chat_id, level)
        
        # Получаем историю диалога
        dialog_history = get_dialog_history(chat_id)
        
        try:
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
                new_text = "🎤 Транскрибирую аудио..."
                if processing_msg.text != new_text:
                    await processing_msg.edit_text(new_text)
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
        try:
            new_text = "🎤 Транскрибирую аудио..."
            if processing_msg.text != new_text:
                await processing_msg.edit_text(new_text)
        except Exception as e:
            logger.warning(f"Не удалось обновить сообщение о статусе: {e}")
        
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
        try:
            new_text = "💭 Обрабатываю ваш вопрос..."
            if processing_msg.text != new_text:
                await processing_msg.edit_text(new_text)
        except Exception as e:
            logger.warning(f"Не удалось обновить сообщение о статусе: {e}")
        
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
    
    # Обработчик команды /profile - детальный профиль
    dp.message.register(handle_profile, Command("profile"))
    
    # Обработчик команды /learn - режим обучения
    dp.message.register(handle_learn, Command("learn"))
    
    # Обработчик команды /mode - смена режима работы
    dp.message.register(handle_mode, Command("mode"))
    
    # Обработчик команды /help - помощь
    dp.message.register(handle_help, Command("help"))
    
    # Обработчик команды /start_course - начало курса
    dp.message.register(handle_start_course, Command("start_course"))
    
    # Обработчик команды /profile - профиль пользователя
    dp.message.register(handle_profile_command, Command("profile"))
    
    # Обработчик команды /errors - ошибки в тестах
    dp.message.register(handle_errors_command, Command("errors"))
    
    # Обработчик выбора режима работы (вопросы или обучение)
    dp.callback_query.register(handle_mode_selection, F.data.in_(["mode_questions", "mode_learning"]))
    
    # Обработчик нажатий на кнопки выбора уровня
    dp.callback_query.register(handle_level_selection, F.data.startswith("level_"))
    
    # Обработчик кнопок главного меню (из режима вопросов)
    dp.callback_query.register(handle_main_menu_buttons, F.data.in_([
        "change_level", "show_status", "show_profile", "enter_learn_mode", 
        "show_help", "back_to_main", "switch_to_education"
    ]))
    
    # Обработчик выбора режима обучения
    dp.callback_query.register(handle_learn_mode_selection, F.data.startswith("learn_"))
    dp.callback_query.register(handle_learn_mode_selection, F.data == "back_to_questions")
    
    # Обработчик переключения в режим education
    dp.callback_query.register(handle_switch_to_education, F.data == "switch_to_education")
    
    # Обработчик выбора направления обучения
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_direction_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_plan_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_start_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_prev_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_next_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_test_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_progress_"))
    dp.callback_query.register(handle_education_direction_selection, F.data.startswith("edu_lesson_"))
    dp.callback_query.register(handle_education_direction_selection, F.data == "edu_back")
    dp.callback_query.register(handle_education_direction_selection, F.data == "back_to_questions")
    
    # Обработчик ответов на тестовые вопросы
    dp.callback_query.register(handle_test_answer, F.data.startswith("test_answer_"))
    
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
