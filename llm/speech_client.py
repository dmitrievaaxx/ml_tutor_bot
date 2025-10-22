"""
Модуль для работы с транскрипцией аудио через Hugging Face Whisper API
"""

import tempfile
import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class HuggingFaceSpeechClient:
    """
    Клиент для транскрипции аудио с использованием Hugging Face Whisper API
    """
    
    def __init__(self):
        """
        Инициализация клиента Hugging Face
        """
        # Проверяем наличие API токена
        api_token = os.getenv('HUGGINGFACE_API_TOKEN')
        logger.info(f"HUGGINGFACE_API_TOKEN получен: {'ДА' if api_token else 'НЕТ'}")
        if api_token:
            logger.info(f"Длина токена: {len(api_token)} символов")
        
        if not api_token:
            logger.warning("HUGGINGFACE_API_TOKEN не установлен в переменных окружения. Голосовые сообщения будут недоступны.")
            self.api_token = None
            self.api_url = None
            self.headers = None
            return
        
        self.api_token = api_token
        self.api_url = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
        self.headers = {
            "Authorization": f"Bearer {api_token}"
        }
        logger.info("Hugging Face Whisper API клиент инициализирован")
    
    async def transcribe_audio(self, audio_path: str) -> str:
        """
        Транскрибирует аудио-файл в текст через Hugging Face Whisper API
        
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
            
            # Проверяем размер файла (ограничение HF: 25MB)
            file_size = os.path.getsize(audio_path)
            max_size = 25 * 1024 * 1024  # 25MB
            if file_size > max_size:
                raise ValueError(f"Файл слишком большой: {file_size / (1024*1024):.1f}MB (максимум 25MB)")
            
            logger.info(f"Начинаем транскрипцию файла: {audio_path}")
            
            # Транскрибируем аудио через Hugging Face API
            with open(audio_path, 'rb') as audio_file:
                # Определяем правильный Content-Type для файла
                content_type = "audio/ogg"  # По умолчанию для .ogg файлов
                if audio_path.endswith('.wav'):
                    content_type = "audio/wav"
                elif audio_path.endswith('.mp3'):
                    content_type = "audio/mpeg"
                elif audio_path.endswith('.flac'):
                    content_type = "audio/flac"
                
                # Отправляем файл напрямую с правильным Content-Type
                response = requests.post(
                    self.api_url,
                    headers={
                        **self.headers,
                        "Content-Type": content_type
                    },
                    data=audio_file.read()
                )
            
            # Проверяем статус ответа
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and 'text' in result:
                    transcribed_text = result['text'].strip()
                elif isinstance(result, list) and len(result) > 0:
                    transcribed_text = result[0].get('text', '').strip()
                else:
                    raise ValueError(f"Неожиданный формат ответа от API: {result}")
                
                logger.info(f"Транскрипция завершена. Длина текста: {len(transcribed_text)} символов")
                return transcribed_text
            else:
                error_msg = f"Ошибка API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Ошибка при транскрипции аудио: {e}")
            raise
    
    async def transcribe_audio_data(self, audio_data: bytes, file_extension: str = ".ogg") -> str:
        """
        Транскрибирует аудио-данные из памяти через Hugging Face Whisper API
        
        Args:
            audio_data: Байты аудио-файла
            file_extension: Расширение файла
        
        Returns:
            str: Транскрибированный текст
        """
        if not self.api_token:
            raise ValueError("Hugging Face API токен не настроен. Установите HUGGINGFACE_API_TOKEN в переменных окружения.")
        
        try:
            # Проверяем размер данных (ограничение HF: 25MB)
            data_size = len(audio_data)
            max_size = 25 * 1024 * 1024  # 25MB
            if data_size > max_size:
                raise ValueError(f"Аудио-данные слишком большие: {data_size / (1024*1024):.1f}MB (максимум 25MB)")
            
            logger.info(f"Начинаем транскрипцию аудио-данных размером {data_size} байт")
            
            # Определяем правильный Content-Type для файла
            content_type = "audio/ogg"  # По умолчанию для .ogg файлов
            if file_extension.endswith('.wav'):
                content_type = "audio/wav"
            elif file_extension.endswith('.mp3'):
                content_type = "audio/mpeg"
            elif file_extension.endswith('.flac'):
                content_type = "audio/flac"
            
            # Отправляем данные напрямую с правильным Content-Type
            response = requests.post(
                self.api_url,
                headers={
                    **self.headers,
                    "Content-Type": content_type
                },
                data=audio_data
            )
            
            # Проверяем статус ответа
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and 'text' in result:
                    transcribed_text = result['text'].strip()
                elif isinstance(result, list) and len(result) > 0:
                    transcribed_text = result[0].get('text', '').strip()
                else:
                    raise ValueError(f"Неожиданный формат ответа от API: {result}")
                
                logger.info(f"Транскрипция завершена. Длина текста: {len(transcribed_text)} символов")
                return transcribed_text
            else:
                error_msg = f"Ошибка API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Ошибка при транскрипции аудио-данных: {e}")
            raise


# Глобальный экземпляр клиента (ленивая инициализация)
_speech_client: Optional[HuggingFaceSpeechClient] = None


def get_speech_client() -> HuggingFaceSpeechClient:
    """
    Получить экземпляр клиента для транскрипции
    
    Returns:
        HuggingFaceSpeechClient: Экземпляр клиента
    """
    global _speech_client
    if _speech_client is None:
        _speech_client = HuggingFaceSpeechClient()
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