"""Управление историей диалогов"""

import logging
import os
import re

from bot.prompts import get_system_prompt, get_welcome_message

logger = logging.getLogger(__name__)

# Глобальное хранилище диалогов в оперативной памяти
# Структура: {chat_id: [{"role": "...", "content": "..."}, ...]}
_dialogs = {}


def clean_response(text: str) -> str:
    """
    Очистка ответа от форматирования Markdown
    
    Args:
        text: Исходный текст ответа
        
    Returns:
        str: Очищенный текст без markdown форматирования
    """
    # Убираем форматирование Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **жирный** -> жирный
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # *курсив* -> курсив
    text = re.sub(r'#+\s*(.*)', r'\1', text)      # # заголовок -> заголовок
    text = re.sub(r'^\s*[-*]\s*', '', text, flags=re.MULTILINE)  # Убираем маркеры списков
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)  # Убираем нумерацию списков
    
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Множественные переносы -> двойные
    text = re.sub(r' +', ' ', text)  # Множественные пробелы -> одинарные
    text = text.strip()
    
    return text


# Функция get_system_prompt() перенесена в bot/prompts.py


def extract_user_level(chat_id: int) -> str:
    """
    Извлекает уровень знаний пользователя из истории диалога
    Возвращает последний выбранный уровень
    
    Args:
        chat_id: ID чата в Telegram
        
    Returns:
        str: Уровень пользователя ('Новичок', 'Базовый', 'Продвинутый') или None
    """
    if chat_id not in _dialogs:
        return None
    
    # Ищем уровень в сообщениях пользователя (с конца истории)
    # Это гарантирует, что мы получим последний выбранный уровень
    for message in reversed(_dialogs[chat_id]):
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


# Функция get_welcome_message() перенесена в bot/prompts.py


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
        # Инициализация нового диа
        # лога с системным промптом
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
        # Полностью очищаем историю
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


