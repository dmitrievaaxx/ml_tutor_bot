"""Клиент для работы с Tavily веб-поиском"""

import os
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_sentences(text: str, max_sentences: int = 3) -> str:
    """
    Извлекает первые N предложений из текста
    
    Args:
        text: Исходный текст
        max_sentences: Максимальное количество предложений
        
    Returns:
        str: Извлеченные предложения с многоточием если текст обрезан
    """
    if not text:
        return "Нет контента..."
    
    # Разбиваем на предложения по знакам конца предложения
    sentences = re.split(r'([.!?]+\s)', text)
    
    # Объединяем предложения с их знаками препинания
    result_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            result_sentences.append(sentences[i] + sentences[i + 1])
        else:
            result_sentences.append(sentences[i])
    
    # Берем первые max_sentences предложений
    preview = ''.join(result_sentences[:max_sentences])
    
    # Если текст обрезан (есть еще предложения), добавляем многоточие
    if len(result_sentences) > max_sentences:
        # Убираем последний пробел и добавляем многоточие
        preview = preview.rstrip() + "..."
    
    return preview.strip()


async def search_with_tavily(query: str, max_results: int = 3) -> Optional[str]:
    """
    Поиск информации в интернете через Tavily API
    
    Args:
        query: Поисковый запрос
        max_results: Максимальное количество результатов
        
    Returns:
        str: Отформатированный ответ с источниками или None если ошибка/нет ключа
    """
    logger.info(f"🔍 Начинаем веб-поиск через Tavily для запроса: {query[:50]}...")
    
    try:
        api_key = os.getenv('TAVILY_API_KEY')
        logger.info(f"🔑 Проверка TAVILY_API_KEY: {'Найден' if api_key else 'НЕ НАЙДЕН'}")
        
        if not api_key:
            logger.warning("⚠️ TAVILY_API_KEY не установлен - пропускаем веб-поиск")
            return None
        
        from tavily import TavilyClient
        
        # В версии 0.7.x ключ берется из переменной окружения TAVILY_API_KEY автоматически
        client = TavilyClient()
        logger.info(f"✅ Клиент Tavily создан успешно (ключ из переменной окружения)")
        
        # Выполняем поиск (синхронный вызов в async функции)
        response = client.search(
            query,
            max_results=max_results,
            search_depth="basic"  # Используем basic для быстроты
        )
        
        logger.info(f"📊 Tavily вернул ответ с {len(response.get('results', []))} результатами")
        
        # Форматируем результаты
        results = []
        for i, result in enumerate(response.get('results', []), 1):
            title = result.get('title', 'Без названия')
            url = result.get('url', '')
            
            logger.info(f"📄 Результат {i}: {title[:50]}...")
            
            # Формируем результат в новом формате (только заголовок и ссылка)
            results.append(f"📄 {title}\n🔗 {url}")
            
            # Добавляем разделитель между результатами (кроме последнего)
            if i < min(len(response.get('results', [])), max_results):
                results.append("")
        
        if results:
            formatted_response = "\n".join(results)
            logger.info(f"✅ Tavily успешно вернул {len(response.get('results', []))} результатов")
            return formatted_response
        else:
            logger.info("⚠️ Tavily не нашел результатов")
            return None
        
    except ImportError as e:
        logger.warning(f"❌ Библиотека tavily не установлена. Ошибка: {e}. Установите: pip install tavily-python")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка поиска Tavily: {type(e).__name__}: {e}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None