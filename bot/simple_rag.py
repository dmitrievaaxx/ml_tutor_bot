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
            
            # Добавляем документы по одному
            for i, chunk in enumerate(all_splits):
                try:
                    self.vector_store.add_documents([chunk])
                    logger.info(f"Добавлен чанк {i+1}/{len(all_splits)}")
                except Exception as e:
                    logger.error(f"Ошибка добавления чанка {i+1}: {e}")
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
    
    def answer_question(self, question: str) -> str:
        """
        Ответ на вопрос через RAG (как в notebook)
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            Ответ на основе документа
        """
        try:
            if not self.rag_chain:
                return "RAG система не инициализирована. Сначала загрузите документ."
            
            # Используем RAG цепочку (как в notebook)
            answer = self.rag_chain.invoke(question)
            
            logger.info(f"RAG ответ на вопрос: {question[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа: {e}")
            return f"Ошибка при получении ответа: {str(e)}"
    
    def has_document(self) -> bool:
        """Проверка наличия загруженного документа"""
        return self.vector_store is not None and self.rag_chain is not None
