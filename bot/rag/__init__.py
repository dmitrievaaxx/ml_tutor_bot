"""
RAG модуль для работы с PDF документами ArXiv

Этот модуль предоставляет функциональность для:
- Обработки PDF файлов
- Создания векторных представлений
- Поиска релевантных фрагментов
- Генерации ответов на основе документов
"""

from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .rag_service import RAGService

__all__ = ['DocumentProcessor', 'VectorStore', 'RAGService']
