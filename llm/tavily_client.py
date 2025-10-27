"""Клиент для работы с Tavily веб-поиском"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def search_with_tavily(query: str, max_results: int = 3) -> Optional[str]:
    """
    Поиск информации в интернете через Tavily API
    
    Args:
        query: Поисковый запрос
        max_results: Максимальное количество результатов
        
    Returns:
        str: Отформатированный ответ с источниками или None если ошибка/нет ключа
    """
    try:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            logger.warning("TAVILY_API_KEY не установлен - пропускаем веб-поиск")
            return None
        
        from tavily import AsyncClient
        
        client = AsyncClient(api_key=api_key)
        
        logger.info(f"Поиск через Tavily: {query[:50]}...")
        
        # Выполняем поиск
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth="basic"  # Используем basic для быстроты
        )
        
        # Форматируем результаты
        results = []
        for i, result in enumerate(response.get('results', []), 1):
            title = result.get('title', 'Без названия')
            content = result.get('content', 'Нет контента')
            url = result.get('url', '')
            
            # Ограничиваем длину контента
            content_preview = content[:300].strip()
            if len(content) > 300:
                content_preview += "..."
            
            results.append(f"📄 {title}\n{content_preview}")
            if url:
                results.append(f"🔗 {url}")
            
            # Добавляем разделитель между результатами (кроме последнего)
            if i < min(len(response.get('results', [])), max_results):
                results.append("")
        
        if results:
            formatted_response = "\n".join(results)
            logger.info(f"Tavily вернул {len(response.get('results', []))} результатов")
            return formatted_response
        else:
            logger.info("Tavily не нашел результатов")
            return None
        
    except ImportError:
        logger.warning("Библиотека tavily не установлена. Установите: pip install tavily-python")
        return None
    except Exception as e:
        logger.error(f"Ошибка поиска Tavily: {e}")
        return None