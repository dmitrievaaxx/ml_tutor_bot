"""
Модуль для работы с локальной транскрипцией аудио через Whisper
"""

import whisper
import tempfile
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LocalWhisperClient:
    """
    Клиент для локальной транскрипции аудио с использованием Whisper
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Инициализация клиента Whisper
        
        Args:
            model_size: Размер модели ("tiny", "base", "small", "medium", "large")
        """
        self.model_size = model_size
        self.model = None
        logger.info(f"Инициализация Whisper с моделью {model_size}")
    
    def _load_model(self):
        """
        Загрузка модели Whisper (ленивая загрузка)
        """
        if self.model is None:
            logger.info(f"Загрузка модели Whisper: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info("Модель Whisper загружена успешно")
    
    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Транскрибирует аудио-файл в текст
        
        Args:
            audio_path: Путь к аудио-файлу
        
        Returns:
            str: Транскрибированный текст
        
        Raises:
            Exception: При ошибке транскрипции
        """
        try:
            # Проверяем существование файла
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Аудио-файл не найден: {audio_path}")
            
            # Проверяем размер файла (ограничение: 25MB)
            file_size = os.path.getsize(audio_path)
            max_size = 25 * 1024 * 1024  # 25MB
            if file_size > max_size:
                raise ValueError(f"Файл слишком большой: {file_size / (1024*1024):.1f}MB (максимум 25MB)")
            
            # Загружаем модель при необходимости
            self._load_model()
            
            logger.info(f"Начинаем транскрипцию файла: {audio_path}")
            
            # Транскрибируем аудио
            result = self.model.transcribe(
                audio_path,
                language="ru",  # Указываем русский язык для лучшего качества
                fp16=False  # Отключаем fp16 для совместимости
            )
            
            transcribed_text = result["text"].strip()
            logger.info(f"Транскрипция завершена. Длина текста: {len(transcribed_text)} символов")
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Ошибка при транскрипции аудио: {e}")
            raise
    
    async def transcribe_audio_data(self, audio_data: bytes, file_extension: str = ".ogg") -> str:
        """
        Транскрибирует аудио-данные из памяти
        
        Args:
            audio_data: Байты аудио-файла
            file_extension: Расширение файла (по умолчанию .ogg для Telegram)
        
        Returns:
            str: Транскрибированный текст
        """
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Транскрибируем временный файл
            result = await self.transcribe_audio(temp_file_path)
            return result
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Временный файл удален: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_file_path}: {e}")


# Глобальный экземпляр клиента (ленивая инициализация)
_speech_client: Optional[LocalWhisperClient] = None


def get_speech_client() -> LocalWhisperClient:
    """
    Получить экземпляр клиента для транскрипции
    
    Returns:
        LocalWhisperClient: Экземпляр клиента
    """
    global _speech_client
    if _speech_client is None:
        _speech_client = LocalWhisperClient()
    return _speech_client


async def transcribe_audio_file(audio_path: str) -> str:
    """
    Удобная функция для транскрипции аудио-файла
    
    Args:
        audio_path: Путь к аудио-файлу
    
    Returns:
        str: Транскрибированный текст
    """
    client = get_speech_client()
    return await client.transcribe_audio(audio_path)


async def transcribe_audio_data(audio_data: bytes, file_extension: str = ".ogg") -> str:
    """
    Удобная функция для транскрипции аудио-данных
    
    Args:
        audio_data: Байты аудио-файла
        file_extension: Расширение файла
    
    Returns:
        str: Транскрибированный текст
    """
    client = get_speech_client()
    return await client.transcribe_audio_data(audio_data, file_extension)
