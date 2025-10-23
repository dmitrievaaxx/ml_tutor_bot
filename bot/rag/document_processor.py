"""Обработчик PDF документов для RAG системы"""

import logging
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logging.warning("PyPDF2 не установлен. Обработка PDF недоступна.")

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Класс для обработки PDF документов"""
    
    def __init__(self):
        if PyPDF2 is None:
            raise ImportError("PyPDF2 не установлен. Установите: pip install PyPDF2")
    
    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Обработка PDF файла и извлечение текста
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Словарь с содержимым и метаданными
        """
        try:
            logger.info(f"Обрабатываю PDF файл: {file_path}")
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Извлекаем текст со всех страниц
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += f"\n--- Страница {page_num + 1} ---\n"
                    text += page_text
                
                # Очищаем текст
                cleaned_text = self._clean_text(text)
                
                # Извлекаем метаданные
                metadata = self._extract_metadata(cleaned_text, pdf_reader)
                
                logger.info(f"PDF обработан: {len(cleaned_text)} символов, {len(pdf_reader.pages)} страниц")
                
                return {
                    'content': cleaned_text,
                    'pages': len(pdf_reader.pages),
                    'metadata': metadata,
                    'file_type': 'pdf'
                }
                
        except Exception as e:
            logger.error(f"Ошибка обработки PDF {file_path}: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Очистка извлеченного текста"""
        # Удаляем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        
        # Удаляем маркеры страниц
        text = re.sub(r'--- Страница \d+ ---', '', text)
        
        # Удаляем служебные символы
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\"\'\/]', '', text)
        
        return text.strip()
    
    def _extract_metadata(self, text: str, pdf_reader: PyPDF2.PdfReader) -> Dict[str, Any]:
        """Извлечение метаданных из PDF"""
        metadata = {
            'pages': len(pdf_reader.pages),
            'file_type': 'pdf'
        }
        
        # Пытаемся извлечь информацию из первых строк
        lines = text.split('\n')[:20]  # Первые 20 строк
        
        # Ищем ArXiv ID
        arxiv_id = self._find_arxiv_id(lines)
        if arxiv_id:
            metadata['arxiv_id'] = arxiv_id
        
        # Ищем авторов
        authors = self._find_authors(lines)
        if authors:
            metadata['authors'] = authors
        
        # Ищем название статьи
        title = self._find_title(lines)
        if title:
            metadata['title'] = title
        
        return metadata
    
    def _find_arxiv_id(self, lines: List[str]) -> Optional[str]:
        """Поиск ArXiv ID в тексте"""
        for line in lines:
            # Паттерны для ArXiv ID
            patterns = [
                r'arXiv:(\d+\.\d+)',
                r'arxiv\.org/abs/(\d+\.\d+)',
                r'(\d{4}\.\d{4,5})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def _find_authors(self, lines: List[str]) -> Optional[str]:
        """Поиск авторов в тексте"""
        for i, line in enumerate(lines[:10]):  # Ищем в первых 10 строках
            line = line.strip()
            
            # Пропускаем пустые строки и заголовки
            if not line or len(line) < 3:
                continue
            
            # Ищем строки с фамилиями (содержат запятые или "and")
            if ',' in line or ' and ' in line.lower():
                # Проверяем, что это не адрес или другая информация
                if not any(word in line.lower() for word in ['email', '@', 'university', 'department']):
                    return line
        
        return None
    
    def _find_title(self, lines: List[str]) -> Optional[str]:
        """Поиск названия статьи"""
        for i, line in enumerate(lines[:5]):  # Ищем в первых 5 строках
            line = line.strip()
            
            # Пропускаем пустые строки
            if not line:
                continue
            
            # Название обычно длинное и не содержит служебных слов
            if (len(line) > 10 and 
                not any(word in line.lower() for word in ['abstract', 'introduction', 'arxiv', 'doi']) and
                not line.isupper()):  # Не все заглавные
                return line
        
        return None
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Разбиение текста на чанки для лучшего поиска
        
        Args:
            text: Исходный текст
            chunk_size: Размер чанка в символах
            overlap: Перекрытие между чанками
            
        Returns:
            Список чанков текста
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Пытаемся закончить на границе предложения
            if end < len(text):
                # Ищем последнюю точку, восклицательный или вопросительный знак
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk and len(chunk) > 50:  # Минимальный размер чанка
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        logger.info(f"Текст разбит на {len(chunks)} чанков")
        return chunks
    
    def create_content_preview(self, text: str, max_length: int = 500) -> str:
        """Создание краткого превью содержимого"""
        if len(text) <= max_length:
            return text
        
        # Берем первые max_length символов и обрезаем по границе слова
        preview = text[:max_length]
        last_space = preview.rfind(' ')
        
        if last_space > max_length * 0.8:  # Если последний пробел не слишком далеко
            preview = preview[:last_space]
        
        return preview + "..."
