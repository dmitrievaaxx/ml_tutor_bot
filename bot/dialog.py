"""Управление историей диалогов"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Глобальное хранилище диалогов в оперативной памяти
# Структура: {chat_id: [{"role": "...", "content": "..."}, ...]}
_dialogs = {}


def clean_response(text: str) -> str:
    """
    Очистка ответа от форматирования и иностранных символов
    
    Args:
        text: Исходный текст ответа
        
    Returns:
        str: Очищенный текст только на русском языке
    """
    # Убираем форматирование Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **жирный** -> жирный
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *курсив* -> курсив
    text = re.sub(r'#+\s*(.*)', r'\1', text)      # # заголовок -> заголовок
    text = re.sub(r'^\s*[-*]\s*', '', text, flags=re.MULTILINE)  # Убираем списки
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)  # Убираем нумерованные списки
    
    # КРИТИЧНО: Удаляем все символы кроме русских букв, цифр, пробелов и пунктуации
    # Разрешенные символы: русские буквы, цифры, пробелы, знаки препинания
    allowed_pattern = r'[а-яА-ЯёЁ0-9\s\.,!?;:—–\-\(\)\"\'\n]'
    # Оставляем только разрешенные символы
    text = ''.join(char if re.match(allowed_pattern, char) else '' for char in text)
    
    # Заменяем английские слова на русские (если остались после фильтрации)
    english_replacements = {
        'basics': 'основы',
        'learning': 'обучение', 
        'data': 'данные',
        'model': 'модель',
        'algorithm': 'алгоритм',
        'training': 'обучение',
        'testing': 'тестирование',
        'accuracy': 'точность',
        'prediction': 'прогноз',
        'feature': 'признак',
        'dataset': 'набор данных',
        'machine learning': 'машинное обучение',
        'neural network': 'нейронная сеть',
        'deep learning': 'глубокое обучение',
        'supervised': 'с учителем',
        'unsupervised': 'без учителя',
        'reinforcement': 'с подкреплением',
        'welcome': 'добро пожаловать',
        'hello': 'привет'
    }
    
    for eng, rus in english_replacements.items():
        text = re.sub(r'\b' + eng + r'\b', rus, text, flags=re.IGNORECASE)
    
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Множественные переносы -> двойные
    text = re.sub(r' +', ' ', text)  # Множественные пробелы -> одинарные
    text = text.strip()
    
    return text


def get_system_prompt(level: str = None) -> str:
    """
    Получение системного промпта в зависимости от уровня пользователя
    
    Args:
        level: Уровень знаний пользователя ('Новичок', 'Базовый', 'Продвинутый')
        
    Returns:
        str: Системный промпт для LLM на русском языке
    """
    
    # Базовая часть промпта (общая для всех уровней)
    base_prompt = """Ты помощник по машинному обучению. Отвечай только на русском языке.

ПРАВИЛА:
- Максимум 2-3 предложения
- Только русские буквы
- Без форматирования
- Заканчивай точкой

СТРУКТУРА:
1. Ответ на вопрос
2. Простая аналогия
3. "Могу рассказать про [тема1], [тема2], [тема3]. Хочешь?"
"""
    
    # Промпты для каждого уровня
    level_prompts = {
        'Новичок': """
НОВИЧОК: Простые слова, аналогии из жизни, без терминов.
""",
        
        'Базовый': """
БАЗОВЫЙ: Баланс простоты и терминов, можно упомянуть математику.
""",
        
        'Продвинутый': """
ПРОДВИНУТЫЙ: Технические детали, формулы, глубокие объяснения.
"""
    }
    
    # Если уровень не указан, используем базовый промпт
    if level not in level_prompts:
        return base_prompt + level_prompts['Базовый']
    
    return base_prompt + level_prompts[level]


def extract_user_level(chat_id: int) -> str:
    """
    Извлекает уровень знаний пользователя из истории диалога
    
    Args:
        chat_id: ID чата в Telegram
        
    Returns:
        str: Уровень пользователя ('Новичок', 'Базовый', 'Продвинутый') или None
    """
    if chat_id not in _dialogs:
        return None
    
    # Ищем уровень в сообщениях пользователя
    for message in _dialogs[chat_id]:
        if message["role"] == "user":
            content = message["content"]
            if content in ['Новичок', 'Базовый', 'Продвинутый']:
                return content
    
    return None


def is_first_level_selection(chat_id: int) -> bool:
    """
    Определяет, является ли текущий выбор уровня первым
    
    Args:
        chat_id: ID чата в Telegram
        
    Returns:
        bool: True если это первый выбор уровня, False если смена уровня
    """
    if chat_id not in _dialogs:
        return True
    
    # Считаем количество сообщений с уровнями
    level_count = 0
    for message in _dialogs[chat_id]:
        if message["role"] == "user":
            content = message["content"]
            if content in ['Новичок', 'Базовый', 'Продвинутый']:
                level_count += 1
    
    return level_count <= 1


def get_welcome_message(level: str) -> str:
    """
    Получает приветственное сообщение с темами для уровня
    
    Args:
        level: Уровень знаний пользователя
        
    Returns:
        str: Приветственное сообщение с темами
    """
    welcome_messages = {
        'Новичок': """Отличный выбор — начинаем с основ!
Разберёмся, что такое машинное обучение, нейросети и обработка естественного языка — просто и на примерах из жизни😄

Ты узнаешь:
🤖 что такое ML и зачем оно нужно,
📊 как данные превращаются в предсказания,
🧠 как учатся нейронные сети,
💬 и как машины понимают человеческий язык

Хочешь начать? Напиши:
👉 «Что такое машинное обучение?» или «Как работают нейросети?»""",
        
        'Базовый': """Отлично! Переходим к более глубоким темам.
Разберёмся, как работают основные алгоритмы, нейросетевые модели и методы анализа данных.

Ты узнаешь:
📈 как устроены линейная и логистическая регрессия,
🌲 что делают деревья решений и бустинг,
🧠 как работают CNN, RNN и трансформеры,
💬 и как оценивать модели с помощью метрик — Accuracy, F1, ROC AUC.

Готов попробовать?
Напиши: «Покажи пример градиентного бустинга» или «Объясни трансформер»""",
        
        'Продвинутый': """Ты на продвинутом уровне — отлично! 
Я помогу тебе разбирать архитектуры, подходы и оптимизацию моделей.

Ты узнаешь:
🧠 архитектуры DL (U-Net, ResNet, Transformer, LLM),
📊 методы обучения (self-supervised, fine-tuning, distillation),
⚙️ оптимизаторы (AdamW, SAM, Lion),
🔬 и современные тренды — Diffusion Models, Consistency Models, LCM.

Можем обсуждать тонкости реализации, метрики, data pipeline и выбор гиперпараметров.

Напиши, например:
👉 «Разбери LCM», «Как работает attention?» или «Как стабилизировать обучение диффузионной модели?»"""
    }
    
    return welcome_messages.get(level, welcome_messages['Базовый'])


def get_dialog_history(chat_id: int) -> list:
    """
    Получение истории диалога для чата
    
    Если диалог не существует, создаёт новый с системным промптом.
    Автоматически обновляет системный промпт при смене уровня.
    
    Args:
        chat_id: ID чата в Telegram
        
    Returns:
        list: История сообщений в формате OpenAI [{"role": "...", "content": "..."}]
    """
    if chat_id not in _dialogs:
        # Инициализация нового диалога с системным промптом
        _dialogs[chat_id] = [
            {"role": "system", "content": get_system_prompt()}
        ]
        logger.info(f"Создан новый диалог для chat_id={chat_id}")
    else:
        # Проверяем, нужно ли обновить системный промпт на основе уровня
        user_level = extract_user_level(chat_id)
        if user_level:
            # Обновляем системный промпт (всегда первый элемент)
            new_prompt = get_system_prompt(user_level)
            if _dialogs[chat_id][0]["content"] != new_prompt:
                _dialogs[chat_id][0]["content"] = new_prompt
                logger.info(f"Обновлен системный промпт для уровня '{user_level}' в chat_id={chat_id}")
    
    return _dialogs[chat_id]


def add_user_message(chat_id: int, message: str):
    """
    Добавление сообщения пользователя в историю диалога
    
    Args:
        chat_id: ID чата в Telegram
        message: Текст сообщения от пользователя
    """
    history = get_dialog_history(chat_id)
    history.append({"role": "user", "content": message})
    logger.info(
        f"Добавлено сообщение пользователя в chat_id={chat_id}, "
        f"всего сообщений: {len(history)}"
    )


def add_assistant_message(chat_id: int, message: str):
    """
    Добавление ответа ассистента в историю диалога
    
    Args:
        chat_id: ID чата в Telegram
        message: Ответ от LLM
    """
    history = get_dialog_history(chat_id)
    history.append({"role": "assistant", "content": message})
    logger.info(
        f"Добавлен ответ ассистента в chat_id={chat_id}, "
        f"всего сообщений: {len(history)}"
    )


def clear_dialog(chat_id: int):
    """
    Очистка истории диалога для начала с чистого листа
    
    Args:
        chat_id: ID чата в Telegram
    """
    if chat_id in _dialogs:
        del _dialogs[chat_id]
        logger.info(f"Очищена история для chat_id={chat_id}")


def get_dialog_stats(chat_id: int) -> dict:
    """
    Получение статистики диалога
    
    Args:
        chat_id: ID чата в Telegram
        
    Returns:
        dict: Статистика диалога (количество сообщений, пользователь/ассистент)
    """
    history = get_dialog_history(chat_id)
    
    user_messages = sum(1 for msg in history if msg['role'] == 'user')
    assistant_messages = sum(1 for msg in history if msg['role'] == 'assistant')
    
    return {
        'total': len(history),
        'user': user_messages,
        'assistant': assistant_messages
    }


