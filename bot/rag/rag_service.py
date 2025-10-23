"""Основной RAG сервис для обработки запросов пользователей"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from .document_processor import DocumentProcessor
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGService:
    """Основной сервис для RAG функциональности"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore()
    
    def process_document(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """
        Полная обработка документа: извлечение текста, разбиение на чанки, создание эмбеддингов
        При загрузке нового документа автоматически удаляет старый
        
        Args:
            file_path: Путь к PDF файлу
            user_id: ID пользователя
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            logger.info(f"Начинаю обработку документа для пользователя {user_id}")
            
            # Удаляем старый документ пользователя (KISS принцип)
            self.delete_user_documents(user_id)
            
            # Обрабатываем PDF
            doc_data = self.document_processor.process_pdf(file_path)
            
            # Разбиваем на чанки
            chunks = self.document_processor.chunk_text(doc_data['content'])
            
            if not chunks:
                raise ValueError("Не удалось создать чанки из документа")
            
            # Добавляем в векторное хранилище (используем user_id как document_id)
            self.vector_store.add_document(
                document_id=user_id,  # Используем user_id как document_id
                chunks=chunks,
                metadata=doc_data['metadata'],
                user_id=user_id
            )
            
            # Создаем превью содержимого
            content_preview = self.document_processor.create_content_preview(doc_data['content'])
            
            result = {
                'success': True,
                'content_preview': content_preview,
                'chunks_count': len(chunks),
                'pages': doc_data['pages'],
                'metadata': doc_data['metadata']
            }
            
            logger.info(f"Документ пользователя {user_id} успешно обработан: {len(chunks)} чанков")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки документа для пользователя {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_and_answer(self, query: str, user_id: int, max_results: int = 3) -> Dict[str, Any]:
        """
        Поиск релевантных документов и формирование ответа
        
        Args:
            query: Поисковый запрос пользователя
            user_id: ID пользователя
            max_results: Максимальное количество результатов
            
        Returns:
            Словарь с результатами поиска и рекомендациями
        """
        try:
            logger.info(f"Поиск для пользователя {user_id}: {query[:50]}...")
            
            # Поиск в векторном хранилище
            results = self.vector_store.search(query, user_id, max_results)
            
            if not results:
                return {
                    'found': False,
                    'message': 'В ваших документах не найдена информация по этому вопросу.',
                    'suggestions': self._get_suggestions(query)
                }
            
            # Анализируем качество результатов
            best_result = results[0]
            max_similarity = best_result['similarity']
            
            if max_similarity > 0.7:
                # Высокое качество - полный ответ из документов
                return self._format_high_quality_response(results, query)
            elif max_similarity > 0.4:
                # Среднее качество - гибридный ответ
                return self._format_hybrid_response(results, query)
            else:
                # Низкое качество - fallback
                return self._format_fallback_response(query, results)
                
        except Exception as e:
            logger.error(f"Ошибка поиска для пользователя {user_id}: {e}")
            return {
                'found': False,
                'message': 'Произошла ошибка при поиске в документах.',
                'error': str(e)
            }
    
    def _format_high_quality_response(self, results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Форматирование ответа высокого качества"""
        sources = []
        content_parts = []
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            title = metadata.get('title', 'Неизвестный документ')
            authors = metadata.get('authors', '')
            
            source_info = f"📄 {title}"
            if authors:
                source_info += f" ({authors})"
            
            sources.append(source_info)
            content_parts.append(f"[Источник {i}]\n{result['content']}")
        
        return {
            'found': True,
            'quality': 'high',
            'message': f'📚 На основе ваших документов:\n\n' + '\n\n'.join(content_parts),
            'sources': sources,
            'similarity': results[0]['similarity']
        }
    
    def _format_hybrid_response(self, results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Форматирование гибридного ответа"""
        sources = []
        content_parts = []
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            title = metadata.get('title', 'Неизвестный документ')
            
            sources.append(f"📄 {title}")
            content_parts.append(f"[Частично релевантно {i}]\n{result['content']}")
        
        return {
            'found': True,
            'quality': 'medium',
            'message': f'📚 Частично найдено в ваших документах:\n\n' + '\n\n'.join(content_parts) + 
                      f'\n\n💡 Рекомендую также обратиться к общим знаниям по этой теме.',
            'sources': sources,
            'similarity': results[0]['similarity']
        }
    
    def _format_fallback_response(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Форматирование fallback ответа"""
        return {
            'found': False,
            'quality': 'low',
            'message': f'🤖 В ваших документах не найдена точная информация по вопросу "{query}".\n\n'
                      f'Рекомендую использовать общие знания или загрузить дополнительные статьи по этой теме.',
            'suggestions': self._get_suggestions(query)
        }
    
    def _get_suggestions(self, query: str) -> List[str]:
        """Получение предложений для улучшения поиска"""
        suggestions = [
            "Попробуйте переформулировать вопрос",
            "Используйте ключевые слова из статьи",
            "Загрузите дополнительные статьи по этой теме",
            "Задайте более конкретный вопрос"
        ]
        
        # Специфичные предложения для ML тем
        ml_keywords = ['нейронная сеть', 'машинное обучение', 'алгоритм', 'модель', 'обучение']
        if any(keyword in query.lower() for keyword in ml_keywords):
            suggestions.extend([
                "Спросите об архитектуре модели",
                "Уточните результаты экспериментов",
                "Интересуйтесь математическими формулами"
            ])
        
        return suggestions
    
    def delete_user_documents(self, user_id: int):
        """Удаление всех документов пользователя"""
        try:
            self.vector_store.delete_user_documents(user_id)
            logger.info(f"Удалены все документы пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка удаления документов пользователя {user_id}: {e}")
    
    def delete_document(self, user_id: int, document_id: int):
        """Удаление конкретного документа"""
        try:
            self.vector_store.delete_document(user_id, document_id)
            logger.info(f"Удален документ {document_id} пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка удаления документа {document_id}: {e}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            return self.vector_store.get_user_stats(user_id)
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return {
                'total_chunks': 0,
                'total_documents': 0,
                'documents': []
            }
