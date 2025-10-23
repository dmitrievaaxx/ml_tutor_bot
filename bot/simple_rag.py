"""Простая RAG система на основе LangChain (как в naive-rag.ipynb)"""

import logging
import tempfile
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.messages import HumanMessage, AIMessage
except ImportError as e:
    logging.warning(f"LangChain не установлен: {e}")
    PyPDFLoader = None
    RecursiveCharacterTextSplitter = None
    InMemoryVectorStore = None
    OpenAIEmbeddings = None
    ChatOpenAI = None
    ChatPromptTemplate = None
    StrOutputParser = None
    RunnablePassthrough = None
    HumanMessage = None
    AIMessage = None

logger = logging.getLogger(__name__)


class SimpleRAG:
    """Простая RAG система на основе LangChain (как в notebook)"""
    
    def __init__(self):
        if not all([PyPDFLoader, RecursiveCharacterTextSplitter, InMemoryVectorStore]):
            raise ImportError("LangChain компоненты не установлены")
        
        self.vector_store = None
        self.retriever = None
        self.llm = None
        self.rag_chain = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Инициализация компонентов RAG"""
        try:
            # Инициализируем LLM (используем OpenRouter вместо OpenAI)
            self.llm = ChatOpenAI(
                model="meta-llama/llama-3.3-70b-instruct:free", 
                temperature=0.9,
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            # Инициализируем эмбеддинги (используем OpenRouter)
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            logger.info("RAG компоненты инициализированы с OpenRouter")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации RAG: {e}")
            raise
    
    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Обработка PDF файла (как в notebook)
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"Обрабатываю PDF: {file_path}")
            
            # 1. Загрузка документа (как в notebook)
            loader = PyPDFLoader(
                file_path=file_path,
                mode="page",
                extraction_mode="plain"
            )
            
            # Загружаем страницы
            pages = []
            for page in loader.load():
                pages.append(page)
            
            logger.info(f"Загружено {len(pages)} страниц")
            
            # 2. Разбиение на чанки (как в notebook)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, 
                chunk_overlap=0
            )
            all_splits = text_splitter.split_documents(pages)
            
            logger.info(f"Создано {len(all_splits)} чанков")
            
            # 3. Создание векторного хранилища (как в notebook)
            logger.info("Создаю векторное хранилище...")
            
            # Создаем пустое векторное хранилище
            self.vector_store = InMemoryVectorStore(embedding=self.embeddings)
            
            # Добавляем документы батчами для лучшей производительности
            batch_size = 10
            for i in range(0, len(all_splits), batch_size):
                batch = all_splits[i:i + batch_size]
                try:
                    # Используем add_texts вместо add_documents для совместимости
                    texts = [doc.page_content for doc in batch]
                    metadatas = [doc.metadata for doc in batch]
                    self.vector_store.add_texts(texts, metadatas)
                    logger.info(f"Добавлен батч чанков {i//batch_size + 1}/{(len(all_splits) + batch_size - 1)//batch_size}")
                except Exception as e:
                    logger.error(f"Ошибка добавления батча {i//batch_size + 1}: {e}")
                    # Пробуем добавить по одному как fallback
                    for j, chunk in enumerate(batch):
                        try:
                            self.vector_store.add_texts([chunk.page_content], [chunk.metadata])
                        except Exception as e2:
                            logger.error(f"Ошибка добавления чанка {i+j+1}: {e2}")
                            continue
            
            # 4. Создание retriever (как в notebook)
            self.retriever = self.vector_store.as_retriever(
                search_kwargs={'k': 3}
            )
            
            # 5. Создание RAG цепочки (как в notebook)
            self._create_rag_chain()
            
            # Создаем превью контента
            content_preview = self._create_content_preview(pages)
            
            # Извлекаем метаданные
            metadata = self._extract_metadata(file_path, pages)
            
            return {
                'success': True,
                'pages': len(pages),
                'chunks_count': len(all_splits),
                'content_preview': content_preview,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки PDF: {e}")
            return {
                'success': False,
                'error': f'Ошибка обработки: {str(e)}'
            }
    
    def _create_rag_chain(self):
        """Создание RAG цепочки (как в notebook)"""
        try:
            # Системный промпт (как в notebook)
            SYSTEM_TEMPLATE = """
You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the user question.
If you don't know the answer, just say 'Я не нашел ответа на ваш вопрос!'.
Use three sentences maximum and keep the answer concise.

Context:
{context}
"""
            
            # Создаем промпт шаблон (как в notebook)
            question_answering_prompt = ChatPromptTemplate([
                ("system", SYSTEM_TEMPLATE),
                ("human", "{question}"),
            ])
            
            # Функция форматирования чанков (как в notebook)
            def format_chunks(chunks):
                return "\n\n".join(chunk.page_content for chunk in chunks)
            
            # Создаем RAG цепочку (как в notebook)
            self.rag_chain = (
                {"context": self.retriever | format_chunks, "question": RunnablePassthrough()}
                | question_answering_prompt
                | self.llm
                | StrOutputParser()
            )
            
            logger.info("RAG цепочка создана")
            
        except Exception as e:
            logger.error(f"Ошибка создания RAG цепочки: {e}")
            raise
    
    def _create_content_preview(self, pages: List, length: int = 500) -> str:
        """Создание превью контента"""
        try:
            if not pages:
                return ""
            
            # Берем текст с первых страниц
            content = ""
            for page in pages[:3]:  # Первые 3 страницы
                content += page.page_content + "\n"
            
            if len(content) <= length:
                return content.strip()
            
            # Обрезаем до нужной длины
            preview = content[:length].strip()
            
            # Пытаемся закончить на полном предложении
            last_period = preview.rfind('.')
            if last_period > length * 0.7:
                preview = preview[:last_period + 1]
            
            return preview + "..."
            
        except Exception as e:
            logger.error(f"Ошибка создания превью: {e}")
            return "Не удалось создать превью"
    
    def _extract_metadata(self, file_path: str, pages: List) -> Dict[str, Any]:
        """Извлечение метаданных"""
        try:
            metadata = {
                'title': Path(file_path).stem,
                'pages': len(pages),
                'authors': '',
                'arxiv_id': ''
            }
            
            # Пытаемся найти ArXiv ID в тексте
            if pages:
                content = pages[0].page_content
                import re
                
                arxiv_patterns = [
                    r'arxiv:(\d+\.\d+)',
                    r'arXiv:(\d+\.\d+)',
                    r'(\d{4}\.\d{4,5})'
                ]
                
                for pattern in arxiv_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        metadata['arxiv_id'] = match.group(1)
                        break
            
            return metadata
            
        except Exception as e:
            logger.error(f"Ошибка извлечения метаданных: {e}")
            return {
                'title': Path(file_path).stem,
                'pages': len(pages) if pages else 0,
                'authors': '',
                'arxiv_id': ''
            }
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Ответ на вопрос через RAG с анализом качества
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            Словарь с ответом и метаданными
        """
        try:
            if not self.rag_chain:
                return {
                    'answer': "RAG система не инициализирована. Сначала загрузите документ.",
                    'source': 'error',
                    'quality': 'low'
                }
            
            # Получаем релевантные чанки для анализа
            relevant_chunks = self.retriever.invoke(question)
            
            # Используем RAG цепочку (как в notebook)
            answer = self.rag_chain.invoke(question)
            
            # Анализируем качество ответа
            quality = self._analyze_answer_quality(question, answer, relevant_chunks)
            
            # Определяем источник ответа
            source = self._determine_answer_source(quality, relevant_chunks)
            
            logger.info(f"RAG ответ на вопрос: {question[:50]}... (качество: {quality})")
            
            return {
                'answer': answer,
                'source': source,
                'quality': quality,
                'chunks_used': len(relevant_chunks)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа: {e}")
            return {
                'answer': f"Ошибка при получении ответа: {str(e)}",
                'source': 'error',
                'quality': 'low'
            }
    
    def _analyze_answer_quality(self, question: str, answer: str, chunks: List) -> str:
        """Анализ качества ответа"""
        try:
            # Простой анализ качества на основе ключевых слов
            question_lower = question.lower()
            answer_lower = answer.lower()
            
            # Проверяем, содержит ли ответ ключевые слова из вопроса
            question_words = set(question_lower.split())
            answer_words = set(answer_lower.split())
            
            # Подсчитываем пересечение слов
            common_words = question_words.intersection(answer_words)
            overlap_ratio = len(common_words) / len(question_words) if question_words else 0
            
            # Проверяем наличие информации в чанках
            chunks_content = " ".join([chunk.page_content.lower() for chunk in chunks])
            chunks_words = set(chunks_content.split())
            chunks_overlap = question_words.intersection(chunks_words)
            chunks_ratio = len(chunks_overlap) / len(question_words) if question_words else 0
            
            # Определяем качество
            if overlap_ratio > 0.3 and chunks_ratio > 0.2:
                return 'high'
            elif overlap_ratio > 0.1 and chunks_ratio > 0.1:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Ошибка анализа качества: {e}")
            return 'low'
    
    def _determine_answer_source(self, quality: str, chunks: List) -> str:
        """Определение источника ответа"""
        if quality == 'high':
            return 'document'
        elif quality == 'medium':
            return 'document_partial'
        else:
            return 'not_found'
    
    def extract_document_topics(self) -> List[str]:
        """Извлечение ключевых тем из документа"""
        try:
            if not self.vector_store:
                return []
            
            # Получаем все документы из хранилища через поиск
            # InMemoryVectorStore не имеет get_all_documents(), используем поиск
            all_docs = self.vector_store.similarity_search("", k=1000)  # Получаем все документы
            
            if not all_docs:
                return []
            
            # Объединяем текст всех документов
            full_text = " ".join([doc.page_content for doc in all_docs])
            
            # Простое извлечение тем на основе ключевых слов
            topics = self._extract_topics_from_text(full_text)
            
            logger.info(f"Извлечено {len(topics)} тем из документа")
            return topics
            
        except Exception as e:
            logger.error(f"Ошибка извлечения тем: {e}")
            return []
    
    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Извлечение тем из текста"""
        try:
            import re
            
            # Ищем заголовки и ключевые фразы
            topics = []
            
            # Паттерны для поиска тем
            patterns = [
                r'## (.+)',  # Markdown заголовки
                r'# (.+)',   # Markdown заголовки
                r'Abstract[:\s]*(.+)',  # Abstract
                r'Introduction[:\s]*(.+)',  # Introduction
                r'Method[:\s]*(.+)',  # Method
                r'Result[:\s]*(.+)',  # Results
                r'Conclusion[:\s]*(.+)',  # Conclusion
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    topic = match.strip()[:100]  # Ограничиваем длину
                    if len(topic) > 10 and topic not in topics:
                        topics.append(topic)
            
            # Если не нашли тем, создаем общие
            if not topics:
                topics = [
                    "Основная идея статьи",
                    "Методы и подходы", 
                    "Результаты и выводы"
                ]
            
            return topics[:3]  # Возвращаем максимум 3 темы
            
        except Exception as e:
            logger.error(f"Ошибка извлечения тем из текста: {e}")
            return ["Основная идея статьи", "Методы и подходы", "Результаты и выводы"]
    
    def has_document(self) -> bool:
        """Проверка наличия загруженного документа"""
        return self.vector_store is not None and self.rag_chain is not None
