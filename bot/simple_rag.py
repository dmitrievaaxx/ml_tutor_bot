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
            
            # Инициализируем эмбеддинги (как в notebook)
            logger.info("Используем OpenAI API для embeddings (как в notebook)")
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
            
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
            
            # 2. Разбиение на чанки с улучшенной логикой
            all_splits = self._smart_chunk_split(pages, chunk_size=400, overlap=100)
            
            logger.info(f"Создано {len(all_splits)} чанков")
            
            # Анализируем качество разбиения на чанки
            self._analyze_chunks_quality(pages, all_splits)
            
            # 3. Создание векторного хранилища (как в notebook)
            logger.info("Создаю векторное хранилище...")
            
            # Создаем векторное хранилище (как в notebook)
            self.vector_store = InMemoryVectorStore.from_documents(
                all_splits,
                embedding=self.embeddings
            )
            logger.info(f"Векторное хранилище создано с {len(all_splits)} чанками")
            for i, chunk in enumerate(all_splits):
                logger.info(f"Чанк {i+1} при создании: {chunk.page_content[:150]}...")
            
            # 4. Создание retriever (как в notebook)
            self.retriever = self.vector_store.as_retriever(
                search_kwargs={'k': 3}
            )
            
            # 5. Создание всех RAG цепочек (как в notebook)
            self._create_rag_chains()
            
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
    
    def format_chunks(self, chunks):
        """Объединяем чанки в одну строку (как в notebook)"""
        return "\n\n".join(chunk.page_content for chunk in chunks)
    
    def _create_basic_rag_chain(self):
        """Создание базовой RAG цепочки (как в notebook)"""
        try:
            # Системный промпт (как в notebook)
            SYSTEM_TEMPLATE = """
You are an assistant for question-answering tasks.
Do not use Chinese characters in respond.
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
            
            # Создаем RAG цепочку (как в notebook)
            self.rag_chain = (
                {"context": self.retriever | self.format_chunks, "question": RunnablePassthrough()}
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
You are an assistant for question-answering tasks. Do not use Chinese characters in respond. Answer the user's questions based on the conversation history and below context retrieved for the last question. Answer 'Я не нашел ответа на ваш вопрос!' if you don't find any information in the context. Use three sentences maximum and keep the answer concise.

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
            
            # Создаем conversational RAG цепочку (как в notebook)
            self.rag_conversation_chain = (
                RunnablePassthrough.assign(
                    context=get_last_message_for_retriever_input | self.retriever | self.format_chunks
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
                    "Transform last user message to a search query in Russian language according to the whole conversation history above to further retrieve the information relevant to the conversation. For general questions like 'what is this about?' or 'what is the article about?', search for: article topic, main theme, summary, abstract, main concepts, document content. For specific questions, search for exact information. Try to thoroughly analyze all messages to generate the most relevant query. The longer result better than short. Only respond with the query, nothing else.",
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
You are an assistant for question-answering tasks. Do not use Chinese characters in respond. Answer the user's questions based on the conversation history and below context retrieved for the last question. Answer 'Я не нашел ответа на ваш вопрос!' if you don't find any information in the context. Use three sentences maximum and keep the answer concise.

Context retrieved for the last question:

{context}
"""
            
            conversational_answering_prompt = ChatPromptTemplate([
                ("system", CONVERSATION_SYSTEM_TEMPLATE),
                ("placeholder", "{messages}")
            ])
            
            # Создаем RAG цепочку с Query Transformation (как в notebook)
            self.rag_query_transform_chain = (
                RunnablePassthrough.assign(
                    context=retrieval_query_transformation_chain | self.retriever | self.format_chunks
                )
                | conversational_answering_prompt
                | self.llm
                | StrOutputParser()
            )
            
            logger.info("RAG цепочка с Query Transformation создана")
            
        except Exception as e:
            logger.error(f"Ошибка создания RAG цепочки с Query Transformation: {e}")
            raise
    
    def _analyze_chunks_quality(self, pages: List, chunks: List) -> None:
        """Анализ качества разбиения текста на чанки"""
        try:
            if not pages or not chunks:
                logger.warning("Нет страниц или чанков для анализа")
                return
            
            # Получаем полный текст
            full_text = ""
            for page in pages:
                full_text += page.page_content + "\n"
            
            logger.info("=" * 80)
            logger.info("АНАЛИЗ КАЧЕСТВА РАЗБИЕНИЯ НА ЧАНКИ")
            logger.info("=" * 80)
            
            # Основная статистика
            total_text_length = len(full_text)
            total_chunks = len(chunks)
            total_chunk_length = sum(len(chunk.page_content) for chunk in chunks)
            
            logger.info(f"📊 ОБЩАЯ СТАТИСТИКА:")
            logger.info(f"   • Длина исходного текста: {total_text_length:,} символов")
            logger.info(f"   • Количество чанков: {total_chunks}")
            logger.info(f"   • Общая длина чанков: {total_chunk_length:,} символов")
            logger.info(f"   • Покрытие текста: {(total_chunk_length/total_text_length)*100:.1f}%")
            
            # Анализ размеров чанков
            chunk_sizes = [len(chunk.page_content) for chunk in chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            min_size = min(chunk_sizes)
            max_size = max(chunk_sizes)
            
            logger.info(f"📏 РАЗМЕРЫ ЧАНКОВ:")
            logger.info(f"   • Средний размер: {avg_size:.0f} символов")
            logger.info(f"   • Минимальный размер: {min_size} символов")
            logger.info(f"   • Максимальный размер: {max_size} символов")
            
            # Детальный анализ каждого чанка
            logger.info(f"📝 ДЕТАЛЬНЫЙ АНАЛИЗ ЧАНКОВ:")
            for i, chunk in enumerate(chunks):
                chunk_text = chunk.page_content
                chunk_length = len(chunk_text)
                
                # Находим начало и конец чанка в исходном тексте
                start_pos = full_text.find(chunk_text[:50])  # Ищем по первым 50 символам
                end_pos = start_pos + chunk_length if start_pos != -1 else -1
                
                logger.info(f"   Чанк {i+1:2d}: {chunk_length:3d} символов | Позиция: {start_pos:4d}-{end_pos:4d}")
                logger.info(f"              Начало: {chunk_text[:60]}...")
                logger.info(f"              Конец:   ...{chunk_text[-40:]}")
                
                # Проверяем, не обрывается ли чанк на середине предложения
                if chunk_text and chunk_text[-1] not in '.!?':
                    logger.warning(f"              ⚠️  Чанк {i+1} обрывается на середине предложения!")
                else:
                    logger.info(f"              ✅ Чанк {i+1} заканчивается корректно")
            
            # Проверяем пропуски в тексте
            logger.info(f"🔍 ПРОВЕРКА ПОКРЫТИЯ:")
            covered_positions = set()
            for chunk in chunks:
                chunk_text = chunk.page_content
                start_pos = full_text.find(chunk_text[:50])
                if start_pos != -1:
                    for pos in range(start_pos, start_pos + len(chunk_text)):
                        covered_positions.add(pos)
            
            total_positions = len(full_text)
            covered_count = len(covered_positions)
            coverage_percent = (covered_count / total_positions) * 100
            
            logger.info(f"   • Покрыто позиций: {covered_count:,} из {total_positions:,}")
            logger.info(f"   • Процент покрытия: {coverage_percent:.1f}%")
            
            if coverage_percent < 95:
                logger.warning(f"   ⚠️  Низкое покрытие текста! Возможны пропуски.")
            
            # Общая оценка качества разбиения
            logger.info(f"📈 ОБЩАЯ ОЦЕНКА КАЧЕСТВА:")
            broken_chunks = sum(1 for chunk in chunks if chunk.page_content and chunk.page_content[-1] not in '.!?')
            quality_score = ((len(chunks) - broken_chunks) / len(chunks)) * 100 if chunks else 0
            
            logger.info(f"   • Чанков с корректным окончанием: {len(chunks) - broken_chunks}/{len(chunks)}")
            logger.info(f"   • Оценка качества: {quality_score:.1f}%")
            
            if quality_score >= 80:
                logger.info(f"   ✅ Качество разбиения: ОТЛИЧНО")
            elif quality_score >= 60:
                logger.info(f"   ⚠️  Качество разбиения: УДОВЛЕТВОРИТЕЛЬНО")
            else:
                logger.warning(f"   ❌ Качество разбиения: ПЛОХО - нужна оптимизация")
            
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Ошибка анализа качества чанков: {e}")
    
    def _smart_chunk_split(self, pages: List, chunk_size: int = 400, overlap: int = 100) -> List:
        """Умное разбиение текста на чанки с учетом границ предложений"""
        try:
            from langchain_core.documents import Document
            
            # Объединяем весь текст
            full_text = ""
            for page in pages:
                full_text += page.page_content + "\n"
            
            # Разбиваем на предложения
            import re
            sentences = re.split(r'(?<=[.!?])\s+', full_text)
            
            chunks = []
            current_chunk = ""
            current_size = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Если добавление предложения превысит размер чанка
                if current_size + len(sentence) > chunk_size and current_chunk:
                    # Сохраняем текущий чанк
                    chunks.append(Document(
                        page_content=current_chunk.strip(),
                        metadata={"source": "smart_split"}
                    ))
                    
                    # Начинаем новый чанк с перекрытием
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    current_size = len(current_chunk)
                else:
                    # Добавляем предложение к текущему чанку
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                    current_size = len(current_chunk)
            
            # Добавляем последний чанк
            if current_chunk.strip():
                chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata={"source": "smart_split"}
                ))
            
            logger.info(f"Умное разбиение: создано {len(chunks)} чанков из {len(sentences)} предложений")
            return chunks
            
        except Exception as e:
            logger.error(f"Ошибка умного разбиения: {e}")
            # Fallback к стандартному разбиению
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]
            )
            return text_splitter.split_documents(pages)
    
    def _create_content_preview(self, pages: List, length: int = 20000) -> str:
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
                
                # Для коротких ответов типа "Да", "Нет" используем последний вопрос из истории
                if len(question.strip()) <= 3 and conversation_history:
                    # Берем последний вопрос пользователя из истории
                    last_user_question = None
                    for msg in reversed(conversation_history):
                        if msg.get('role') == 'user' and len(msg.get('content', '').strip()) > 3:
                            last_user_question = msg.get('content', '')
                            break
                    
                    if last_user_question:
                        logger.info(f"Короткий ответ '{question}', используем последний вопрос: '{last_user_question}'")
                        # Обновляем релевантные чанки на основе последнего вопроса
                        relevant_chunks = self.retriever.invoke(last_user_question)
                
            else:
                logger.info("Используем базовую RAG цепочку")
                
                # Используем базовую RAG цепочку (как в notebook)
                answer = self.rag_chain.invoke(question)
                
                # Получаем релевантные чанки для анализа
                relevant_chunks = self.retriever.invoke(question)
            
            # Если релевантные чанки еще не получены (для conversational RAG без коротких ответов)
            if 'relevant_chunks' not in locals():
                relevant_chunks = self.retriever.invoke(question)
            
            # Очищаем ответ от лишних фраз "не нашел" если есть релевантный контент
            answer_cleaned = self._clean_answer(answer)
            
            # Анализируем качество ответа
            quality = self._analyze_answer_quality(question, answer_cleaned, relevant_chunks)
            
            # Определяем источник ответа
            source = self._determine_answer_source(quality, relevant_chunks)
            
            logger.info(f"RAG ответ на вопрос: {question[:50]}... (качество: {quality}, источник: {source}, чанков: {len(relevant_chunks)})")
            logger.info(f"Ответ: {answer_cleaned[:100]}...")
            
            return {
                'answer': answer_cleaned,
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
    
    def _clean_answer(self, answer: str) -> str:
        """
        Очищает ответ от лишних фраз "не нашел" если есть релевантный контент
        
        Args:
            answer: Исходный ответ
            
        Returns:
            str: Очищенный ответ
        """
        if not answer:
            return answer
        
        no_answer_phrases = ["не нашел ответа", "я не нашел"]
        answer_lower = answer.lower()
        
        # Проверяем есть ли фраза "не нашел"
        for phrase in no_answer_phrases:
            if phrase in answer_lower:
                # Находим позицию начала фразы
                phrase_pos = answer_lower.find(phrase)
                # Если ДО фразы есть достаточно контента (>30 символов),
                # убираем фразу "не нашел" и все что после нее
                if len(answer[:phrase_pos].strip()) > 30:
                    # Удаляем все начиная с "не нашел" до конца
                    cleaned = answer[:phrase_pos].strip()
                    logger.info(f"Очищен ответ: удалено '{phrase}' и текст после него (было {len(answer)} символов, стало {len(cleaned)})")
                    return cleaned
        
        return answer
    
    def _analyze_answer_quality(self, question: str, answer: str, chunks: List) -> str:
        """Анализ качества ответа"""
        try:
            # Более гибкий анализ качества
            question_lower = question.lower()
            answer_lower = answer.lower()
            
            # Проверяем, содержит ли ответ ключевые слова из вопроса
            question_words = set(question_lower.split())
            answer_words = set(answer_lower.split())
            
            logger.info(f"Анализ качества: вопрос='{question}', слова вопроса={question_words}")
            logger.info(f"Ответ: {answer[:200]}...")
            logger.info(f"Чанки найдены: {len(chunks)}")
            if chunks:
                logger.info(f"Первый чанк: {chunks[0].page_content[:200]}...")
                for i, chunk in enumerate(chunks):
                    logger.info(f"Чанк {i+1}: {chunk.page_content[:100]}...")
            
            # Подсчитываем пересечение слов
            common_words = question_words.intersection(answer_words)
            overlap_ratio = len(common_words) / len(question_words) if question_words else 0
            
            # Дополнительная проверка: ищем ключевые слова из вопроса в ответе
            key_words_in_answer = False
            for q_word in question_words:
                if len(q_word) > 3 and q_word in answer_lower:
                    key_words_in_answer = True
                    logger.info(f"Найдено ключевое слово '{q_word}' в ответе")
                    break
            
            # Проверяем наличие информации в чанках
            chunks_content = " ".join([chunk.page_content.lower() for chunk in chunks])
            chunks_words = set(chunks_content.split())
            chunks_overlap = question_words.intersection(chunks_words)
            chunks_ratio = len(chunks_overlap) / len(question_words) if question_words else 0
            
            # Дополнительная проверка: ищем похожие слова (для случаев типа "беггинг" vs "бэггинг")
            similar_words_found = False
            
            # Специальные случаи для русских слов с разным написанием
            word_variations = {
                'беггинг': ['бэггинг', 'bagging'],
                'бэггинг': ['беггинг', 'bagging'],
                'bagging': ['беггинг', 'бэггинг'],
                'бустинг': ['бустинг', 'boosting'],
                'boosting': ['бустинг', 'бустинг'],
                'ансамбль': ['ensemble'],
                'ensemble': ['ансамбль']
            }
            
            for q_word in question_words:
                if len(q_word) > 3:  # Только для слов длиннее 3 символов
                    # Проверяем вариации слова
                    variations_to_check = [q_word]
                    if q_word in word_variations:
                        variations_to_check.extend(word_variations[q_word])
                    
                    for chunk in chunks:
                        chunk_text = chunk.page_content.lower()
                        # Проверяем все вариации слова
                        for variation in variations_to_check:
                            if variation in chunk_text:
                                similar_words_found = True
                                logger.info(f"Найдено похожее слово: '{q_word}' -> '{variation}' в чанке")
                                logger.info(f"Содержимое чанка: {chunk_text[:200]}...")
                                break
                        if similar_words_found:
                            break
                    if similar_words_found:
                        break
            
            # Проверяем, есть ли релевантные чанки
            has_relevant_chunks = len(chunks) > 0
            
            # Проверяем, не является ли ответ стандартным "не нашел"
            # Сначала ищем фразу "не нашел" в ответе
            no_answer_phrases = ["не нашел ответа", "я не нашел"]
            has_no_answer_phrase = any(phrase in answer_lower for phrase in no_answer_phrases)
            
            # Если есть фраза "не нашел", проверяем есть ли контент ДО этой фразы
            if has_no_answer_phrase:
                # Находим позицию начала фразы "не нашел"
                no_answer_pos = min([
                    answer_lower.find(phrase) 
                    for phrase in no_answer_phrases 
                    if phrase in answer_lower
                ])
                # Если ДО фразы "не нашел" есть существенный контент (больше 30 символов),
                # считаем что ответ есть, просто LLM добавил лишнее в конце
                content_before_no = answer_lower[:no_answer_pos].strip()
                has_content_before = len(content_before_no) > 30
                is_standard_no_answer = not has_content_before and not key_words_in_answer
            else:
                is_standard_no_answer = False
            
            # Более гибкие критерии качества
            logger.info(f"Критерии: has_chunks={has_relevant_chunks}, is_no_answer={is_standard_no_answer}, key_words={key_words_in_answer}, similar={similar_words_found}")
            
            if has_relevant_chunks and not is_standard_no_answer:
                # Если есть ключевые слова в ответе, похожие слова или хорошее пересечение - высокое качество
                if key_words_in_answer or similar_words_found or overlap_ratio > 0.2 or chunks_ratio > 0.15:
                    logger.info(f"Высокое качество: overlap={overlap_ratio:.2f}, chunks={chunks_ratio:.2f}, similar={similar_words_found}, key_words={key_words_in_answer}")
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
