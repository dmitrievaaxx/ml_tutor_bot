"""Клиент для работы с Vision API через OpenRouter"""

import os
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Глобальный клиент для Vision API
_vision_client = None


def get_vision_client():
    """
    Получение или создание клиента для Vision API
    
    Создает единственный экземпляр клиента (singleton pattern) для 
    эффективного использования ресурсов
    
    Returns:
        AsyncOpenAI: Настроенный клиент для работы с Vision API
        
    Raises:
        ValueError: Если OPENROUTER_API_KEY не найден в переменных окружения
    """
    global _vision_client
    
    if _vision_client is None:
        logger.info("Создаем новый Vision клиент...")
        api_key = os.getenv('OPENROUTER_API_KEY')
        logger.info(f"API ключ получен: {'ДА' if api_key else 'НЕТ'}")
        
        if not api_key:
            logger.error("OPENROUTER_API_KEY не найден в переменных окружения")
            raise ValueError(
                "OPENROUTER_API_KEY не найден в переменных окружения. "
                "Добавьте его в файл .env"
            )
        
        # Создание клиента с базовым URL OpenRouter
        _vision_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        logger.info("Vision клиент для OpenRouter успешно инициализирован")
    
    return _vision_client


async def get_vision_response(messages: list, image_base64: str) -> str:
    """
    Получение ответа от Vision API на основе истории диалога и изображения
    
    Функция выполняет:
    1. Получение клиента Vision API
    2. Формирование запроса с изображением и историей диалога
    3. Логирование запроса и ответа
    4. Обработку ошибок
    
    Args:
        messages: История диалога в формате [{"role": "...", "content": "..."}]
        image_base64: Изображение в формате base64
        
    Returns:
        str: Ответ от Vision модели
        
    Raises:
        Exception: При ошибках обращения к API
    """
    logger.info("get_vision_response вызвана")
    try:
        logger.info("Получаем Vision клиент...")
        client = get_vision_client()
        logger.info("Vision клиент получен успешно")
    except ValueError as e:
        logger.error(f"Ошибка инициализации Vision клиента: {e}")
        return ""
    
    # Получение параметров модели из переменных окружения
    model = os.getenv('VISION_MODEL', 'qwen/qwen2.5-vl-72b-instruct:free')
    temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
    max_tokens = int(os.getenv('LLM_MAX_TOKENS', '1000'))
    
    # Логирование запроса
    logger.info(
        f"Запрос к Vision API | Модель: {model} | "
        f"Сообщений в истории: {len(messages)} | "
        f"Размер изображения: {len(image_base64)} символов base64"
    )
    
    try:
        # Формируем запрос с изображением
        vision_messages = messages.copy()
        last_message = vision_messages[-1]
        
        # Добавляем изображение к последнему сообщению пользователя
        vision_messages[-1] = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": last_message["content"]
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }
        
        # Запрос к Vision API
        response = await client.chat.completions.create(
            model=model,
            messages=vision_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Извлечение текста ответа
        answer = response.choices[0].message.content
        
        # Логирование ответа
        logger.info(
            f"Ответ от Vision API | Модель: {model} | Длина: {len(answer)} символов | "
            f"Начало: {answer[:50]}{'...' if len(answer) > 50 else ''}"
        )
        
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка Vision API с моделью {model}: {type(e).__name__}: {e}")
        return ""
