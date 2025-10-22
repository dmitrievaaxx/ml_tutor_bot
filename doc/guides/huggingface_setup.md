# Настройка Hugging Face API для голосовых сообщений

## Проблема
В логах видна ошибка при обработке голосовых сообщений:
```
2025-10-22 20:51:51,756 - llm.speech_client - ERROR - Ошибка при транскрипции аудио: Аудио-файл не найден: b'OggS\x00\x02...'
```

## Причина
1. **Отсутствует токен Hugging Face API** - для работы с голосовыми сообщениями нужен токен
2. **Неправильная обработка аудио-данных** - код пытался передать байты в метод, ожидающий путь к файлу

## Решение

### 1. Получите токен Hugging Face API
1. Зайдите на [huggingface.co](https://huggingface.co)
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в [Settings > Access Tokens](https://huggingface.co/settings/tokens)
4. Создайте новый токен с правами "Read"
5. Скопируйте токен

### 2. Создайте файл .env
Создайте файл `.env` в корне проекта со следующим содержимым:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather

# OpenRouter API Configuration  
OPENROUTER_API_KEY=ваш_ключ_от_openrouter
LLM_MODEL=mistralai/mistral-7b-instruct:free
VISION_MODEL=google/gemini-flash-1.5
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Hugging Face API Configuration (для распознавания речи)
HUGGINGFACE_API_TOKEN=ваш_токен_от_huggingface

# Logging Configuration
LOG_LEVEL=INFO
```

### 3. Перезапустите бота
После добавления токена перезапустите бота:

```bash
# Если используете Docker
make docker-stop
make docker-build  
make docker-run

# Если запускаете локально
python -m bot.main
```

## Что исправлено в коде

1. **Исправлен вызов метода транскрипции** - теперь используется `transcribe_audio_data()` вместо `transcribe_audio()`
2. **Улучшена обработка аудио-данных** - данные отправляются напрямую в API без создания временных файлов
3. **Добавлена проверка токена** - если токен не настроен, пользователь получает понятное сообщение
4. **Улучшена обработка ошибок** - более информативные сообщения об ошибках

## Альтернатива
Если не хотите настраивать Hugging Face API, голосовые сообщения будут недоступны, но бот будет работать с текстовыми сообщениями и изображениями.
