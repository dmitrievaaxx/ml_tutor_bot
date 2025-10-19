"""
Модуль для работы с транскрипцией аудио через OpenAI Whisper API
"""

import tempfile
import os
import logging
from typing import Optional
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAISpeechClient:
    """
    Клиент для транскрипции аудио с использованием OpenAI Whisper API
    """
    
    def __init__(self):
        """
        Инициализация клиента OpenAI
        """
        # Проверяем наличие API ключа (используем тот же ключ что и для OpenRouter)
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY или OPENROUTER_API_KEY не установлен в переменных окружения")
        
        self.client = OpenAI(api_key=api_key)
        logger.info("OpenAI Whisper API клиент инициализирован")
    
    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Транскрибирует аудио-файл в текст через OpenAI Whisper API
        
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
            
            # Проверяем размер файла (ограничение OpenAI: 25MB)
            file_size = os.path.getsize(audio_path)
            max_size = 25 * 1024 * 1024  # 25MB
            if file_size > max_size:
                raise ValueError(f"Файл слишком большой: {file_size / (1024*1024):.1f}MB (максимум 25MB)")
            
            logger.info(f"Начинаем транскрипцию файла: {audio_path}")
            
            # Транскрибируем аудио через OpenAI API
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"  # Указываем русский язык для лучшего качества
                )
            
            transcribed_text = transcript.text.strip()
            logger.info(f"Транскрипция завершена. Длина текста: {len(transcribed_text)} символов")
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Ошибка при транскрипции аудио: {e}")
            raise
    
    async def transcribe_audio_data(self, audio_data: bytes, file_extension: str = ".ogg") -> str:
        """
        Транскрибирует аудио-данные из памяти через OpenAI Whisper API
        
        Args:
            audio_data: Байты аудио-файла
            file_extension: Расширение файла
        
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
_speech_client: Optional[OpenAISpeechClient] = None


def get_speech_client() -> OpenAISpeechClient:
    """
    Получить экземпляр клиента для транскрипции
    
    Returns:
        OpenAISpeechClient: Экземпляр клиента
    """
    global _speech_client
    if _speech_client is None:
        _speech_client = OpenAISpeechClient()
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