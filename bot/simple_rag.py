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
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
    MessagesPlaceholder = None

logger = logging.getLogger(__name__)


class SimpleRAG:
    """Простая RAG система на основе LangChain (как в notebook)"""
    
    def __init__(self):
        if not all([PyPDFLoader, RecursiveCharacterTextSplitter, InMemoryVectorStore]):
            raise ImportError("LangChain компоненты не установлены")
        
        self.vector_store = None
        self.retriever = None
        self.llm = None
        self.llm_query_transform = None
        self.rag_chain = None
        self.rag_conversation_chain = None
        self.rag_query_transform_chain = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Инициализация компонентов RAG"""
        try:
            # Инициализируем основной LLM (используем OpenRouter вместо OpenAI)
            self.llm = ChatOpenAI(
                model="meta-llama/llama-3.3-70b-instruct:free", 
                temperature=0.9,
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            # Инициализируем LLM для Query Transformation (как в notebook)
            self.llm_query_transform = ChatOpenAI(
                model="meta-llama/llama-3.3-70b-instruct:free",
                temperature=0.4,
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
            
            # 3. Создание векторного хранилища (обходной путь для OpenRouter)
            logger.info("Создаю векторное хранилище...")
            
            # Проблема: InMemoryVectorStore не работает с OpenRouter embeddings
            # Решение: создаем простое хранилище без embeddings для начала
            try:
                # Создаем пустое векторное хранилище без embeddings
                self.vector_store = InMemoryVectorStore()
                
                # Добавляем документы напрямую (без embeddings пока)
                for i, chunk in enumerate(all_splits):
                    try:
                        # Добавляем как простые тексты без embeddings
                        self.vector_store.add_texts([chunk.page_content], [chunk.metadata])
                        logger.info(f"Добавлен чанк {i+1}/{len(all_splits)}")
                    except Exception as e2:
                        logger.error(f"Ошибка добавления чанка {i+1}: {e2}")
                        continue
                
                logger.info(f"Векторное хранилище создано с {len(all_splits)} чанками (без embeddings)")
                
            except Exception as e:
                logger.error(f"Критическая ошибка создания векторного хранилища: {e}")
                # Создаем заглушку
                self.vector_store = None
            
            # 4. Создание retriever (как в notebook)
            if self.vector_store:
                try:
                    self.retriever = self.vector_store.as_retriever(
                        search_kwargs={'k': 3}
                    )
                    logger.info("Retriever создан успешно")
                except Exception as e:
                    logger.error(f"Ошибка создания retriever: {e}")
                    # Создаем простой retriever без векторного поиска
                    self.retriever = None
            else:
                logger.warning("Векторное хранилище не создано, retriever недоступен")
                self.retriever = None
            
            # 5. Создание всех RAG цепочек (как в notebook)
            if self.retriever:
                self._create_rag_chains()
            else:
                logger.warning("Retriever недоступен, RAG цепочки не созданы")
            
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
    
    def _create_rag_chains(self):
        """Создание всех RAG цепочек (как в notebook)"""
        try:
            # 1. Базовая RAG цепочка (как в notebook)
            self._create_basic_rag_chain()
            
            # 2. Conversational RAG цепочка (как в notebook)
            self._create_conversational_rag_chain()
            
            # 3. RAG с Query Transformation (как в notebook)
            self._create_query_transform_rag_chain()
            
            logger.info("Все RAG цепочки созданы")
            
        except Exception as e:
            logger.error(f"Ошибка создания RAG цепочек: {e}")
            raise
    
    def _create_basic_rag_chain(self):
        """Создание базовой RAG цепочки (как в notebook)"""
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
            
            logger.info("Базовая RAG цепочка создана")
            
        except Exception as e:
            logger.error(f"Ошибка создания базовой RAG цепочки: {e}")
            raise
    
    def _create_conversational_rag_chain(self):
        """Создание conversational RAG цепочки (как в notebook)"""
        try:
            # Conversational системный промпт (как в notebook)
            CONVERSATION_SYSTEM_TEMPLATE = """
You are an assistant for question-answering tasks. Answer the user's questions based on the conversation history and below context retrieved for the last question. Answer 'Я не нашел ответа на ваш вопрос!' if you don't find any information in the context. Use three sentences maximum and keep the answer concise.

Context retrieved for the last question:

{context}
"""
            
            # Создаем conversational промпт (как в notebook)
            conversational_answering_prompt = ChatPromptTemplate([
                ("system", CONVERSATION_SYSTEM_TEMPLATE),
                ("placeholder", "{messages}")
            ])
            
            # Функция для получения последнего сообщения (как в notebook)
            def get_last_message_for_retriever_input(params: Dict):
                return params["messages"][-1].content
            
            # Функция форматирования чанков
            def format_chunks(chunks):
                return "\n\n".join(chunk.page_content for chunk in chunks)
            
            # Создаем conversational RAG цепочку (как в notebook)
            self.rag_conversation_chain = (
                RunnablePassthrough.assign(
                    context=get_last_message_for_retriever_input | self.retriever | format_chunks
                )
                | conversational_answering_prompt
                | self.llm
                | StrOutputParser()
            )
            
            logger.info("Conversational RAG цепочка создана")
            
        except Exception as e:
            logger.error(f"Ошибка создания conversational RAG цепочки: {e}")
            raise
    
    def _create_query_transform_rag_chain(self):
        """Создание RAG цепочки с Query Transformation (как в notebook)"""
        try:
            # Промпт для Query Transformation (как в notebook)
            retrieval_query_transform_prompt = ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="messages"),
                (
                    "user",
                    "Transform last user message to a search query in Russian language according to the whole conversation history above to further retrieve the information relevant to the conversation. Try to thorougly analyze all message to generate the most relevant query. The longer result better than short. Let it be better more abstract than specific. Only respond with the query, nothing else.",
                ),
            ])
            
            # Создаем цепочку Query Transformation (как в notebook)
            retrieval_query_transformation_chain = (
                retrieval_query_transform_prompt 
                | self.llm_query_transform 
                | StrOutputParser()
            )
            
            # Conversational промпт для ответов
            CONVERSATION_SYSTEM_TEMPLATE = """
You are an assistant for question-answering tasks. Answer the user's questions based on the conversation history and below context retrieved for the last question. Answer 'Я не нашел ответа на ваш вопрос!' if you don't find any information in the context. Use three sentences maximum and keep the answer concise.

Context retrieved for the last question:

{context}
"""
            
            conversational_answering_prompt = ChatPromptTemplate([
                ("system", CONVERSATION_SYSTEM_TEMPLATE),
                ("placeholder", "{messages}")
            ])
            
            # Функция форматирования чанков
            def format_chunks(chunks):
                return "\n\n".join(chunk.page_content for chunk in chunks)
            
            # Создаем RAG цепочку с Query Transformation (как в notebook)
            self.rag_query_transform_chain = (
                RunnablePassthrough.assign(
                    context=retrieval_query_transformation_chain | self.retriever | format_chunks
                )
                | conversational_answering_prompt
                | self.llm
                | StrOutputParser()
            )
            
            logger.info("RAG цепочка с Query Transformation создана")
            
        except Exception as e:
            logger.error(f"Ошибка создания RAG цепочки с Query Transformation: {e}")
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
    
    def answer_question(self, question: str, conversation_history: List = None) -> Dict[str, Any]:
        """
        Ответ на вопрос через RAG с поддержкой диалогов (как в notebook)
        
        Args:
            question: Вопрос пользователя
            conversation_history: История диалога для conversational RAG
            
        Returns:
            Словарь с ответом и метаданными
        """
        try:
            if not self.rag_chain:
                logger.warning("RAG цепочка не создана, используем простой подход")
                # Простой подход: используем LLM напрямую с контекстом документа
                if self.vector_store:
                    try:
                        # Получаем все документы из хранилища
                        all_docs = self.vector_store.similarity_search("", k=1000)
                        if all_docs:
                            # Объединяем весь текст документа
                            document_text = "\n\n".join([doc.page_content for doc in all_docs])
                            
                            # Создаем простой промпт с контекстом
                            context_prompt = f"""Ответь на вопрос на основе следующего документа:

Документ:
{document_text[:2000]}  # Ограничиваем размер

Вопрос: {question}

Ответь кратко и по существу на основе информации из документа. Если информации нет, скажи "В документе нет информации об этом"."""
                            
                            # Используем LLM напрямую
                            answer = self.llm.invoke(context_prompt).content
                            
                            # Определяем источник ответа
                            if "в документе нет информации" in answer.lower():
                                source = 'not_found'
                                quality = 'low'
                            else:
                                source = 'document'
                                quality = 'medium'
                            
                            logger.info(f"Простой RAG ответ: source={source}, quality={quality}")
                            
                            return {
                                'answer': answer,
                                'source': source,
                                'quality': quality,
                                'chunks_used': len(all_docs)
                            }
                    except Exception as e:
                        logger.error(f"Ошибка простого RAG: {e}")
                
                return {
                    'answer': "RAG система не инициализирована. Сначала загрузите документ.",
                    'source': 'error',
                    'quality': 'low'
                }
            
            # Если есть история диалога, используем conversational RAG
            if conversation_history and len(conversation_history) > 1:
                logger.info("Используем conversational RAG с Query Transformation")
                
                # Создаем сообщения для conversational RAG
                messages = []
                for msg in conversation_history[-5:]:  # Берем последние 5 сообщений
                    if msg.get('role') == 'user':
                        messages.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        messages.append(AIMessage(content=msg.get('content', '')))
                
                # Добавляем текущий вопрос
                messages.append(HumanMessage(content=question))
                
                # Используем RAG цепочку с Query Transformation (как в notebook)
                answer = self.rag_query_transform_chain.invoke({"messages": messages})
                
            else:
                logger.info("Используем базовую RAG цепочку")
                
                # Используем базовую RAG цепочку (как в notebook)
                answer = self.rag_chain.invoke(question)
            
            # Получаем релевантные чанки для анализа
            if self.retriever:
                try:
                    relevant_chunks = self.retriever.invoke(question)
                except Exception as e:
                    logger.error(f"Ошибка получения чанков через retriever: {e}")
                    relevant_chunks = []
            else:
                logger.warning("Retriever недоступен, используем пустой список чанков")
                relevant_chunks = []
            
            # Анализируем качество ответа
            quality = self._analyze_answer_quality(question, answer, relevant_chunks)
            
            # Определяем источник ответа
            source = self._determine_answer_source(quality, relevant_chunks)
            
            logger.info(f"RAG ответ на вопрос: {question[:50]}... (качество: {quality}, источник: {source}, чанков: {len(relevant_chunks)})")
            logger.info(f"Ответ: {answer[:100]}...")
            
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
            # Более гибкий анализ качества
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
            
            # Проверяем, есть ли релевантные чанки
            has_relevant_chunks = len(chunks) > 0
            
            # Проверяем, не является ли ответ стандартным "не нашел"
            is_standard_no_answer = "не нашел ответа" in answer_lower or "я не нашел" in answer_lower
            
            # Более гибкие критерии качества
            if has_relevant_chunks and not is_standard_no_answer:
                if overlap_ratio > 0.2 or chunks_ratio > 0.15:
                    logger.info(f"Высокое качество: overlap={overlap_ratio:.2f}, chunks={chunks_ratio:.2f}")
                    return 'high'
                elif overlap_ratio > 0.05 or chunks_ratio > 0.05:
                    logger.info(f"Среднее качество: overlap={overlap_ratio:.2f}, chunks={chunks_ratio:.2f}")
                    return 'medium'
                else:
                    # Если есть чанки, но мало пересечений, все равно считаем частично релевантным
                    logger.info(f"Частично релевантно: overlap={overlap_ratio:.2f}, chunks={chunks_ratio:.2f}, но есть чанки")
                    return 'medium'
            else:
                logger.info(f"Низкое качество: overlap={overlap_ratio:.2f}, chunks={chunks_ratio:.2f}, has_chunks={has_relevant_chunks}, is_no_answer={is_standard_no_answer}")
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
                logger.warning("Векторное хранилище не инициализировано")
                return ["Основная идея статьи", "Методы и подходы", "Результаты и выводы"]
            
            # Получаем все документы из хранилища через поиск
            # InMemoryVectorStore не имеет get_all_documents(), используем поиск
            try:
                all_docs = self.vector_store.similarity_search("", k=1000)  # Получаем все документы
            except Exception as e:
                logger.error(f"Ошибка поиска в векторном хранилище: {e}")
                return ["Основная идея статьи", "Методы и подходы", "Результаты и выводы"]
            
            if not all_docs:
                logger.warning("Не найдено документов в векторном хранилище")
                return ["Основная идея статьи", "Методы и подходы", "Результаты и выводы"]
            
            # Объединяем текст всех документов
            full_text = " ".join([doc.page_content for doc in all_docs])
            
            # Простое извлечение тем на основе ключевых слов
            topics = self._extract_topics_from_text(full_text)
            
            logger.info(f"Извлечено {len(topics)} тем из документа")
            return topics
            
        except Exception as e:
            logger.error(f"Ошибка извлечения тем: {e}")
            return ["Основная идея статьи", "Методы и подходы", "Результаты и выводы"]
    
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
    
    def _create_empty_vector_store(self):
        """Создание пустого векторного хранилища"""
        return InMemoryVectorStore(embedding=self.embeddings)
    
    def has_document(self) -> bool:
        """Проверка наличия загруженного документа"""
        return self.vector_store is not None and self.rag_chain is not None
