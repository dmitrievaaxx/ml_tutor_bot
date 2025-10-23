"""Векторное хранилище для RAG системы на основе ChromaDB"""

import logging
import os
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    chromadb = None
    SentenceTransformer = None
    logging.warning("ChromaDB или SentenceTransformers не установлены. RAG недоступен.")

logger = logging.getLogger(__name__)


class VectorStore:
    """Класс для работы с векторным хранилищем ChromaDB"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        if chromadb is None or SentenceTransformer is None:
            raise ImportError(
                "ChromaDB или SentenceTransformers не установлены. "
                "Установите: pip install chromadb sentence-transformers"
            )
        
        self.persist_directory = persist_directory
        self.embeddings_model = None
        self.chroma_client = None
        self.collection = None
        
        self._initialize()
    
    def _initialize(self):
        """Инициализация компонентов"""
        try:
            # Создаем директорию для данных
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Инициализируем модель эмбеддингов
            logger.info("Загружаю модель эмбеддингов...")
            self.embeddings_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            )
            
            # Инициализируем ChromaDB
            logger.info("Инициализирую ChromaDB...")
            self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Создаем или получаем коллекцию
            try:
                self.collection = self.chroma_client.get_collection("ml_documents")
                logger.info("Найдена существующая коллекция ml_documents")
            except:
                self.collection = self.chroma_client.create_collection("ml_documents")
                logger.info("Создана новая коллекция ml_documents")
            
            logger.info("VectorStore инициализирован успешно")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации VectorStore: {e}")
            raise
    
    def add_document(self, document_id: int, chunks: List[str], metadata: Dict[str, Any], user_id: int):
        """
        Добавление документа в векторное хранилище
        
        Args:
            document_id: ID документа из базы данных
            chunks: Список чанков текста
            metadata: Метаданные документа
            user_id: ID пользователя
        """
        try:
            if not chunks:
                logger.warning(f"Нет чанков для документа {document_id}")
                return
            
            # Создаем эмбеддинги для чанков
            logger.info(f"Создаю эмбеддинги для {len(chunks)} чанков...")
            embeddings = self.embeddings_model.encode(chunks)
            
            # Подготавливаем данные для ChromaDB
            ids = [f"{user_id}_{document_id}_{i}" for i in range(len(chunks))]
            
            # Добавляем метаданные к каждому чанку
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    'user_id': user_id,
                    'document_id': document_id,
                    'chunk_index': i,
                    'chunk_count': len(chunks)
                }
                metadatas.append(chunk_metadata)
            
            # Добавляем в коллекцию
            self.collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=chunks,
                metadatas=metadatas
            )
            
            logger.info(f"Добавлен документ {document_id} с {len(chunks)} чанками для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа в векторное хранилище: {e}")
            raise
    
    def search(self, query: str, user_id: int, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Поиск релевантных документов
        
        Args:
            query: Поисковый запрос
            user_id: ID пользователя
            n_results: Количество результатов
            
        Returns:
            Список релевантных документов с метаданными
        """
        try:
            # Создаем эмбеддинг для запроса
            query_embedding = self.embeddings_model.encode([query])
            
            # Поиск в ChromaDB с фильтром по пользователю
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                where={"user_id": user_id}
            )
            
            # Форматируем результаты
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'similarity': 1 - results['distances'][0][i] if results['distances'] else 0
                    })
            
            logger.info(f"Найдено {len(formatted_results)} релевантных документов для пользователя {user_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска в векторном хранилище: {e}")
            return []
    
    def delete_user_documents(self, user_id: int):
        """
        Удаление всех документов пользователя
        
        Args:
            user_id: ID пользователя
        """
        try:
            # Получаем все документы пользователя
            results = self.collection.get(where={"user_id": user_id})
            
            if results['ids']:
                # Удаляем документы
                self.collection.delete(ids=results['ids'])
                logger.info(f"Удалены документы пользователя {user_id}: {len(results['ids'])} чанков")
            else:
                logger.info(f"У пользователя {user_id} нет документов в векторном хранилище")
            
        except Exception as e:
            logger.error(f"Ошибка удаления документов пользователя {user_id}: {e}")
    
    def delete_document(self, user_id: int, document_id: int):
        """
        Удаление конкретного документа
        
        Args:
            user_id: ID пользователя
            document_id: ID документа
        """
        try:
            # Получаем документ пользователя
            results = self.collection.get(where={"user_id": user_id, "document_id": document_id})
            
            if results['ids']:
                # Удаляем документ
                self.collection.delete(ids=results['ids'])
                logger.info(f"Удален документ {document_id} пользователя {user_id}: {len(results['ids'])} чанков")
            else:
                logger.info(f"Документ {document_id} пользователя {user_id} не найден в векторном хранилище")
            
        except Exception as e:
            logger.error(f"Ошибка удаления документа {document_id}: {e}")
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получение статистики пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой
        """
        try:
            results = self.collection.get(where={"user_id": user_id})
            
            if not results['ids']:
                return {
                    'total_chunks': 0,
                    'total_documents': 0,
                    'documents': []
                }
            
            # Подсчитываем уникальные документы
            document_ids = set()
            for metadata in results['metadatas']:
                if 'document_id' in metadata:
                    document_ids.add(metadata['document_id'])
            
            return {
                'total_chunks': len(results['ids']),
                'total_documents': len(document_ids),
                'documents': list(document_ids)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return {
                'total_chunks': 0,
                'total_documents': 0,
                'documents': []
            }
