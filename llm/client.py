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
        logger.info("Создаем новый клиент OpenAI...")
        api_key = os.getenv('OPENROUTER_API_KEY')
        logger.info(f"API ключ получен: {'ДА' if api_key else 'НЕТ'}")
        if not api_key:
            logger.error("OPENROUTER_API_KEY не найден в переменных окружения")
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


async def get_llm_response(messages: list) -> str:
    """
    Получение ответа от LLM на основе истории диалога
    
    Функция выполняет:
    1. Получение клиента OpenRouter
    2. Формирование запроса к LLM с историей диалога
    3. Логирование запроса и ответа
    4. Обработку ошибок
    
    Args:
        messages: История диалога в формате [{"role": "...", "content": "..."}]
        
    Returns:
        str: Ответ от LLM
        
    Raises:
        Exception: При ошибках обращения к API
    """
    logger.info("get_llm_response вызвана")
    try:
        logger.info("Получаем клиента OpenAI...")
        client = get_openai_client()
        logger.info("Клиент OpenAI получен успешно")
    except ValueError as e:
        logger.error(f"Ошибка инициализации клиента: {e}")
        return ""
    
    # Получение параметров модели из переменных окружения
    # Список моделей в порядке приоритета (только доступные модели)
    fallback_models = [
        'mistralai/mistral-7b-instruct:free',        # Mistral 7B - хорошо с многоязычностью
        'meta-llama/llama-3.2-3b-instruct:free',     # Llama 3.2 3B - стабильная модель
        'meta-llama/llama-3.1-8b-instruct:free',     # Llama 3.1 8B - больше параметров
        'huggingfaceh4/zephyr-7b-beta:free',         # Zephyr 7B - альтернатива
    ]
    
    model = os.getenv('LLM_MODEL', fallback_models[0])
    temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
    max_tokens = int(os.getenv('LLM_MAX_TOKENS', '500'))
    
    # Логирование запроса
    logger.info(
        f"Запрос к LLM | Модель: {model} | "
        f"Сообщений в истории: {len(messages)}"
    )
    
    # Пробуем разные модели, если основная не работает
    for attempt, current_model in enumerate(fallback_models):
        try:
            logger.info(f"Попытка {attempt + 1}: используем модель {current_model}")
            
            # Запрос к OpenRouter API с полной историей диалога
            response = await client.chat.completions.create(
                model=current_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Извлечение текста ответа
            answer = response.choices[0].message.content
            
            # Логирование ответа
            logger.info(
                f"Ответ от LLM | Модель: {current_model} | Длина: {len(answer)} символов | "
                f"Начало: {answer[:50]}{'...' if len(answer) > 50 else ''}"
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка с моделью {current_model}: {type(e).__name__}: {e}")
            if attempt < len(fallback_models) - 1:
                logger.info(f"Пробуем следующую модель...")
                continue
            else:
                logger.error("Все модели недоступны")
                return ""
