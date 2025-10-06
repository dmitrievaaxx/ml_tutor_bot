# ML Tutor Bot

Образовательный Telegram-бот для изучения машинного обучения. Бот помогает разобраться в концепциях ML простым языком, используя примеры и аналогии.

## Возможности

**Текущая версия (v0.2.0 - Итерация 2):**
- ✅ Базовый Telegram-бот на aiogram
- ✅ Интеграция с LLM через OpenRouter API
- ✅ Использование бесплатных моделей (работают в РФ без VPN)
- ✅ Обработка команды /start
- ✅ Логирование запросов и ответов LLM

**В разработке:**
- 🔄 Управление контекстом диалога
- 🔄 Адаптивные объяснения под уровень пользователя

## Технологический стек

- **Python** 3.11+
- **aiogram** - для работы с Telegram Bot API
- **OpenRouter** - для доступа к LLM (бесплатные модели)
- **OpenAI Python Client** - для работы с OpenRouter API
- **uv** - для управления зависимостями
- **Docker** - для деплоя

## Установка и запуск

### Предварительные требования

- Python 3.11 или выше
- [uv](https://docs.astral.sh/uv/) - менеджер пакетов Python
- Telegram аккаунт для создания бота
- OpenRouter аккаунт для доступа к LLM

### Шаг 1: Создание Telegram-бота

Следуйте инструкции в [doc/guides/botfather_setup.md](doc/guides/botfather_setup.md) для создания бота через BotFather и получения токена.

### Шаг 1.5: Получение API ключа OpenRouter

Следуйте инструкции в [doc/guides/openrouter_setup.md](doc/guides/openrouter_setup.md) для регистрации на OpenRouter и получения бесплатного API ключа.

### Шаг 2: Клонирование репозитория

```bash
git clone <repository-url>
cd ml_tutor_bot
```

### Шаг 3: Установка зависимостей

```bash
# Установка uv (если еще не установлен)
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Создание виртуального окружения и установка зависимостей
uv venv
uv pip install -e .
```

### Шаг 4: Настройка окружения

Создайте файл `.env` в корне проекта:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Затем отредактируйте .env и добавьте ваш токен
```

Содержимое `.env`:
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather

# OpenRouter API Configuration
OPENROUTER_API_KEY=ваш_ключ_от_openrouter

# LLM Configuration (бесплатная модель для РФ без VPN)
LLM_MODEL=qwen/qwen-2-7b-instruct:free
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Logging Configuration
LOG_LEVEL=INFO
```

### Шаг 5: Запуск бота

```bash
# Активация виртуального окружения
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Запуск бота
python -m bot.main
```

Вы должны увидеть сообщение:
```
INFO - Бот запущен и готов к работе
```

### Шаг 6: Тестирование

1. Откройте Telegram
2. Найдите вашего бота по username
3. Отправьте команду `/start`
4. Отправьте любой вопрос - бот ответит используя LLM

**Примеры вопросов:**
- "Объясни что такое машинное обучение"
- "Что такое нейронная сеть?"
- "Расскажи про градиентный спуск"

## Структура проекта

```
ml_tutor_bot/
├── bot/                    # Модуль Telegram бота
│   ├── __init__.py
│   ├── main.py            # Запуск бота
│   └── handlers.py        # Обработчики команд и сообщений
├── llm/                   # Модуль работы с LLM (в разработке)
│   ├── __init__.py
│   └── client.py
├── tests/                 # Тесты
│   ├── __init__.py
│   └── test_bot.py
├── doc/                   # Документация
│   ├── guides/           # Руководства
│   ├── conventions.md    # Правила разработки
│   ├── vision.md         # Техническое видение
│   ├── workflow.md       # Workflow разработки
│   └── tasklist.md       # План разработки
├── .env                   # Переменные окружения (не в Git)
├── .env.example          # Пример переменных окружения
├── .gitignore
├── pyproject.toml        # Конфигурация проекта и зависимости
└── README.md
```

## Разработка

### Установка зависимостей для разработки

```bash
uv pip install -e ".[dev]"
```

### Запуск тестов

```bash
pytest
```

### Логирование

Бот использует стандартный модуль `logging` Python. Уровень логирования настраивается через переменную окружения `LOG_LEVEL` в `.env` файле:

- `DEBUG` - подробная отладочная информация
- `INFO` - стандартные информационные сообщения (по умолчанию)
- `ERROR` - только ошибки

## Дорожная карта

См. [doc/tasklist.md](doc/tasklist.md) для подробного плана разработки.

- [x] **Итерация 1:** Базовый Telegram-бот
- [x] **Итерация 2:** Интеграция с LLM
- [ ] **Итерация 3:** Управление диалогом
- [ ] **Итерация 4:** Сценарий работы
- [ ] **Итерация 5:** Деплой и финализация

## Документация

- [Техническое видение](doc/vision.md)
- [План разработки](doc/tasklist.md)
- [Правила разработки](doc/conventions.md)
- [Workflow](doc/workflow.md)

### Руководства:
- [Настройка BotFather](doc/guides/botfather_setup.md)
- [Получение API ключа OpenRouter](doc/guides/openrouter_setup.md)

## Лицензия

Этот проект создан в образовательных целях.

