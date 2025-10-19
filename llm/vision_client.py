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


async def get_vision_response(messages: list, image_base64: str, image_format: str = "jpeg") -> str:
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
        image_format: Формат изображения (jpeg, png, gif)
        
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
    # Используем Google Gemini Flash для Vision - надежная модель с хорошей поддержкой изображений
    model = os.getenv('VISION_MODEL', 'qwen/qwen-2-vl-7b-instruct:free')
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
        
        # Добавляем специальную инструкцию для Vision API в системный промпт
        if vision_messages and vision_messages[0]["role"] == "system":
            original_prompt = vision_messages[0]["content"]
            vision_messages[0]["content"] = f"""{original_prompt}

ВАЖНАЯ ИНСТРУКЦИЯ ДЛЯ АНАЛИЗА ИЗОБРАЖЕНИЙ:
- Пользователь отправил изображение - ты ДОЛЖЕН сначала проанализировать его содержимое
- Опиши детально, что именно изображено на картинке (формулы, схемы, графики, текст, код и т.д.)
- ТОЛЬКО после детального анализа изображения давай объяснения по теме ML
- НЕ игнорируй изображение! НЕ отвечай общими фразами!

Формат ответа на изображение:
1. Сначала детально опиши, что видишь на изображении
2. Затем объясни это в контексте машинного обучения (с учетом уровня пользователя)
3. Предложи связанные темы для изучения
            """
            logger.info(f"Системный промпт дополнен инструкциями для Vision API")
        
        # Добавляем изображение к последнему сообщению пользователя
        # Формируем текст запроса с явным указанием на необходимость анализа изображения
        user_text = last_message["content"] if last_message["content"] else ""
        
        # Если пользователь не добавил текст, используем явную инструкцию
        if not user_text or user_text == "Что на этом изображении?":
            user_text = "Проанализируй это изображение. Опиши детально, что на нем изображено (формулы, схемы, графики, текст, код), и объясни в контексте машинного обучения."
        else:
            # Если пользователь добавил подпись, дополняем её инструкцией
            user_text = f"[ИЗОБРАЖЕНИЕ] {user_text}"
        
        vision_messages[-1] = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_text
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{image_base64}"
                    }
                }
            ]
        }
        
        # Логируем структуру запроса для отладки
        logger.info(f"Vision запрос содержит {len(vision_messages)} сообщений")
        logger.info(f"Текст запроса к изображению: '{user_text}'")
        logger.info(f"Формат изображения: {image_format}, размер base64: {len(image_base64)} символов")
        
        # Проверяем, что изображение действительно добавлено
        last_msg_content = vision_messages[-1]["content"]
        if isinstance(last_msg_content, list) and len(last_msg_content) >= 2:
            logger.info("✅ Изображение успешно добавлено к сообщению")
        else:
            logger.error("❌ ОШИБКА: Изображение НЕ добавлено к сообщению!")
        
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
        
        # Детальная диагностика ошибок
        if "rate limit" in str(e).lower():
            logger.error("Превышен лимит запросов к Vision API")
            return "Извините, превышен лимит запросов к Vision API. Попробуйте позже."
        elif "invalid" in str(e).lower() and "image" in str(e).lower():
            logger.error("Неподдерживаемый формат изображения")
            return "Извините, формат изображения не поддерживается. Попробуйте отправить изображение в формате JPEG или PNG."
        elif "timeout" in str(e).lower():
            logger.error("Таймаут запроса к Vision API")
            return "Извините, запрос к Vision API занял слишком много времени. Попробуйте еще раз."
        elif "model" in str(e).lower() and "not found" in str(e).lower():
            logger.error("Vision модель недоступна")
            return "Извините, Vision модель временно недоступна. Попробуйте позже."
        else:
            logger.error(f"Неизвестная ошибка Vision API: {e}")
            return f"Извините, произошла ошибка при анализе изображения: {type(e).__name__}. Попробуйте отправить другое фото."
