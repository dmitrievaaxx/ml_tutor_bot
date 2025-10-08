# ML Tutor Bot

Образовательный Telegram-бот для изучения машинного обучения. Бот помогает разобраться в концепциях ML простым языком, используя примеры и аналогии.

## Возможности

**Текущая версия (v0.5.0 - Итерация 5):**
- ✅ Базовый Telegram-бот на aiogram
- ✅ Интеграция с LLM через OpenRouter API
- ✅ Обработка команд /start, /level, /status
- ✅ Логирование запросов и ответов LLM
- ✅ Управление контекстом диалога (история сообщений)
- ✅ Системный промпт для настройки поведения бота
- ✅ Контекстные ответы с сохранением истории диалога
- ✅ Адаптивные объяснения под уровень пользователя (Новичок, Базовый, Продвинутый)
- ✅ Docker контейнеризация для простого деплоя
- ✅ Makefile для автоматизации задач разработки и деплоя

## Технологический стек

- **Python** 3.11+
- **aiogram** - для работы с Telegram Bot API
- **OpenRouter** - для доступа к LLM (бесплатные модели)
- **OpenAI Python Client** - для работы с OpenRouter API
- **uv** - для управления зависимостями
- **Docker** - для деплоя

## Установка и запуск

Есть два способа запуска бота:
1. **Локально** - с использованием Python и uv
2. **Docker** - в контейнере (рекомендуется для продакшена)

### Предварительные требования

**Для локального запуска:**
- Python 3.11 или выше
- [uv](https://docs.astral.sh/uv/) - менеджер пакетов Python

**Для запуска в Docker:**
- [Docker](https://www.docker.com/) установленный на вашей системе

**Для обоих способов:**
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

## Запуск через Docker (рекомендуется)

Docker обеспечивает изолированную и воспроизводимую среду для запуска бота.

### Шаг 1: Подготовка

Убедитесь, что у вас установлен Docker:
```bash
docker --version
```

### Шаг 2: Клонирование репозитория

```bash
git clone <repository-url>
cd ml_tutor_bot
```

### Шаг 3: Настройка окружения

Создайте файл `.env` в корне проекта:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

Отредактируйте `.env` и добавьте ваши ключи:
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather

# OpenRouter API Configuration
OPENROUTER_API_KEY=ваш_ключ_от_openrouter

# LLM Configuration
LLM_MODEL=mistralai/mistral-7b-instruct:free
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Logging Configuration
LOG_LEVEL=INFO
```

### Шаг 4: Сборка Docker образа

```bash
# С использованием Makefile (рекомендуется)
make docker-build

# Или напрямую через Docker
docker build -t ml-tutor-bot:latest .
```

### Шаг 5: Запуск контейнера

```bash
# С использованием Makefile
make docker-run

# Или напрямую через Docker
docker run -d --name ml-tutor-bot --env-file .env ml-tutor-bot:latest
```

### Шаг 6: Проверка работы

Проверьте логи контейнера:
```bash
docker logs ml-tutor-bot
```

Вы должны увидеть:
```
INFO - Бот запущен и готов к работе
```

### Управление контейнером

```bash
# Остановка и удаление контейнера
make docker-stop

# Просмотр логов
docker logs -f ml-tutor-bot

# Перезапуск (после изменения кода)
make docker-stop
make docker-build
make docker-run
```

## Деплой в облако ☁️

Бот можно развернуть на облачных платформах для работы 24/7 без необходимости держать компьютер включенным.

### Рекомендуемая платформа: Railway ⭐

**Railway** - самый простой способ развернуть бота в облаке:
- ✅ **Бесплатный тариф**: $5 кредитов/месяц (достаточно для бота)
- ✅ **Без кредитной карты**: Можно начать сразу
- ✅ **Автодеплой**: При push в GitHub бот обновляется автоматически
- ✅ **3 клика до деплоя**: Максимально просто

**Быстрый старт:**
1. Зарегистрируйтесь на https://railway.app через GitHub
2. Выберите "Deploy from GitHub repo"
3. Добавьте переменные окружения
4. Готово! Бот работает 24/7

**Подробная инструкция:** [doc/guides/railway_deployment.md](doc/guides/railway_deployment.md)

### Альтернатива: Fly.io

**Fly.io** - для более опытных пользователей:
- ✅ **Полностью бесплатно**: В рамках free tier
- ✅ **Больше контроля**: Мощные CLI инструменты
- ⚠️ **Требуется карта**: Даже для бесплатного тарифа

**Подробная инструкция:** [doc/guides/flyio_deployment.md](doc/guides/flyio_deployment.md)

### Сравнение платформ

Полный анализ вариантов облачного деплоя см. в [doc/CLOUD_DEPLOYMENT_OPTIONS.md](doc/CLOUD_DEPLOYMENT_OPTIONS.md)

## Структура проекта

```
ml_tutor_bot/
├── bot/                    # Модуль Telegram бота
│   ├── __init__.py
│   ├── main.py            # Запуск бота
│   ├── handlers.py        # Обработчики команд и сообщений
│   └── dialog.py          # Управление диалогами
├── llm/                   # Модуль работы с LLM
│   ├── __init__.py
│   └── client.py          # Клиент для OpenRouter API
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
├── .dockerignore         # Исключения для Docker сборки
├── .gitignore
├── Dockerfile            # Docker конфигурация
├── Makefile              # Автоматизация задач
├── pyproject.toml        # Конфигурация проекта и зависимости
└── README.md
```

## Разработка

### Автоматизация с Makefile

Проект включает Makefile для упрощения типовых задач:

```bash
# Показать все доступные команды
make help

# Установка зависимостей
make install

# Установка зависимостей для разработки
make install-dev

# Запуск тестов
make test

# Запуск бота локально
make run

# Сборка Docker образа
make docker-build

# Запуск в Docker
make docker-run

# Остановка Docker контейнера
make docker-stop

# Очистка временных файлов
make clean
```

### Установка зависимостей для разработки

```bash
make install-dev
# Или
uv pip install -e ".[dev]"
```

### Запуск тестов

```bash
make test
# Или
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
- [x] **Итерация 3:** Управление диалогом
- [x] **Итерация 4:** Сценарий работы
- [x] **Итерация 5:** Деплой и финализация
- [ ] **Итерация 6:** Облачное развертывание

## Документация

- [Техническое видение](doc/vision.md)
- [План разработки](doc/tasklist.md)
- [Правила разработки](doc/conventions.md)
- [Workflow](doc/workflow.md)

### Руководства:
- [Настройка BotFather](doc/guides/botfather_setup.md)
- [Получение API ключа OpenRouter](doc/guides/openrouter_setup.md)
- [Деплой на Railway](doc/guides/railway_deployment.md) ⭐ Рекомендуется
- [Деплой на Fly.io](doc/guides/flyio_deployment.md) (альтернатива)
- [Сравнение облачных платформ](doc/CLOUD_DEPLOYMENT_OPTIONS.md)

## Лицензия

Этот проект создан в образовательных целях.

