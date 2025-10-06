"""Клиент для работы с LLM API через OpenRouter"""

import os
import logging
from openai import AsyncOpenAI


logger = logging.getLogger(__name__)


# Глобальный клиент OpenAI для работы с OpenRouter
_openai_client = None


def get_openai_client():
    """
    Получение или создание клиента OpenAI для работы с OpenRouter
    
    Создает единственный экземпляр клиента (singleton pattern) для 
    эффективного использования ресурсов
    
    Returns:
        AsyncOpenAI: Настроенный клиент для работы с OpenRouter API
        
    Raises:
        ValueError: Если OPENROUTER_API_KEY не найден в переменных окружения
    """
    global _openai_client
    
    if _openai_client is None:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY не найден в переменных окружения. "
                "Добавьте его в файл .env"
            )
        
        # Создание клиента с базовым URL OpenRouter
        _openai_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        logger.info("OpenAI клиент для OpenRouter успешно инициализирован")
    
    return _openai_client


async def get_llm_response(message: str) -> str:
    """
    Получение ответа от LLM на основе сообщения пользователя
    
    Функция выполняет:
    1. Получение клиента OpenRouter
    2. Формирование запроса к LLM
    3. Логирование запроса и ответа
    4. Обработку ошибок
    
    Args:
        message: Текст сообщения от пользователя
        
    Returns:
        str: Ответ от LLM
        
    Raises:
        Exception: При ошибках обращения к API
    """
    client = get_openai_client()
    
    # Получение параметров модели из переменных окружения
    # Используем бесплатную модель Qwen, хорошо работающую с русским языком
    model = os.getenv('LLM_MODEL', 'qwen/qwen-2-7b-instruct:free')
    temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
    max_tokens = int(os.getenv('LLM_MAX_TOKENS', '500'))
    
    # Логирование запроса
    logger.info(
        f"Запрос к LLM | Модель: {model} | "
        f"Сообщение: {message[:50]}{'...' if len(message) > 50 else ''}"
    )
    
    try:
        # Запрос к OpenRouter API
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": message}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Извлечение текста ответа
        answer = response.choices[0].message.content
        
        # Логирование ответа
        logger.info(
            f"Ответ от LLM | Длина: {len(answer)} символов | "
            f"Начало: {answer[:50]}{'...' if len(answer) > 50 else ''}"
        )
        
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка при обращении к LLM: {type(e).__name__}: {e}")
        raise
