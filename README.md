# ML Tutor Bot 🤖

> 💬 Интерактивный Telegram-ассистент для изучения машинного обучения.  
> Объясняет сложные концепции простыми словами, адаптируясь под уровень знаний пользователя — от новичка до продвинутого специалиста.

[🔗 Попробовать бота](https://t.me/ml_tutor_bot)

---

## ⚙️ Возможности

- **Адаптация под уровень пользователя** — три уровня сложности объяснений: *Новичок*, *Базовый*, *Продвинутый*
- **Контекстная память** — хранение истории диалога для формирования логически связанных и последовательных ответов
- **Тематические рекомендации** — после каждого объяснения бот предлагает 3 связанных темы для углублённого изучения  
- **Управление уровнем сложности** — возможность изменить уровень в любой момент с помощью команды `/level`

## 🧠 Технические особенности

- **Асинхронная архитектура** — `Python 3.11+`, `aiogram 3.x`, поддержка `async/await` для высокой производительности  
- **Интеграция с LLM** — работа через **OpenRouter API** с поддержкой моделей *Llama 3.1/3.2*, *Mistral*, *Zephyr* и fallback-механизмом  
- **Инженерия промптов** — структурированные шаблоны с примерами и адаптацией под три уровня сложности  
- **Хранение состояния** — in-memory структура `{chat_id: [messages]}` с контекстом и управлением системными промптами  
- **Логирование** — детальные логи запросов и ответов LLM с контекстом (`chat_id`, `длина сообщений`)  
- **Контейнеризация** — **Docker** с multi-stage сборкой и деплоем через **Railway (CI/CD)**  
- **Тестирование** — `pytest` и `pytest-asyncio` для критических сценариев  
- **Автоматизация разработки** — `Makefile` и **uv** для установки, тестов и запуска  

---

## 🚀 Установка и запуск

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/dmitrievaaxx/ml_tutor_bot
cd ml_tutor_bot
```

### Шаг 2: Получение токенов

#### 2.1. Создание Telegram-бота
Следуйте инструкции в [doc/guides/botfather_setup.md](doc/guides/botfather_setup.md) для создания бота через BotFather и получения токена.

#### 2.2. Получение API ключа OpenRouter
Следуйте инструкции в [doc/guides/openrouter_setup.md](doc/guides/openrouter_setup.md) для регистрации на OpenRouter и получения бесплатного API ключа.

#### 2.3. Получение API ключа Hugging Face (опционально)
Для работы с голосовыми сообщениями следуйте инструкции в [doc/guides/huggingface_setup.md](doc/guides/huggingface_setup.md) для получения токена Hugging Face API.

### Шаг 3: Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Откройте `.env` и добавьте ваши токены:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
OPENROUTER_API_KEY=ваш_ключ_от_openrouter
LLM_MODEL=mistralai/mistral-7b-instruct:free
VISION_MODEL=google/gemini-flash-1.5
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
HUGGINGFACE_API_TOKEN=ваш_токен_от_huggingface
LOG_LEVEL=INFO
```

---

### Вариант A: Локальный запуск

**Требования:** Python **3.11+**, менеджер пакетов **uv**

#### 1. Установка зависимостей

```bash
# Создание виртуального окружения
uv venv

# Установка зависимостей проекта
uv pip install -e .
```

#### 2. Активация окружения

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

#### 3. Запуск бота

```bash
python -m bot.main
```

**Ожидаемый вывод:**
```
INFO - Бот запущен и готов к работе
```

---

### Вариант B: Запуск через Docker

**Требования:** **Docker 20.10+** установлен и запущен на системе

#### 1. Запустите Docker Desktop

Убедитесь, что Docker Desktop запущен:
```bash
docker --version
# Должно вывести: Docker version 20.10.x или выше
```

#### 2. Сборка образа

```bash
make docker-build
```

Или напрямую:
```bash
docker build -t ml-tutor-bot:latest .
```

#### 3. Запуск контейнера

```bash
make docker-run
```

Или напрямую:
```bash
docker run -d --name ml-tutor-bot --env-file .env ml-tutor-bot:latest
```

#### 4. Проверка логов

```bash
docker logs ml-tutor-bot
```

**Ожидаемый вывод:**
```
INFO - Бот запущен и готов к работе
```

#### 5. Управление контейнером

```bash
# Остановка и удаление
make docker-stop

# Просмотр логов в реальном времени
docker logs -f ml-tutor-bot

# Перезапуск после изменений
make docker-stop
make docker-build
make docker-run
```

---

## 🧪 Тестирование

```bash
# Установка dev зависимостей
uv pip install -e ".[dev]"

# Запуск тестов
pytest tests/

# Или через Makefile
make test
```

---

## 📚 Документация

### Техническая документация
- [Техническое видение](doc/vision.md) — архитектура, принципы и технологический стек
- [План разработки](doc/tasklist.md) — этапы разработки и прогресс (6 итераций)
- [Правила кодирования](doc/conventions.md) — code style и best practices
- [Workflow разработки](doc/workflow.md) — процесс разработки и согласования

### Руководства по настройке
- [Создание Telegram-бота](doc/guides/botfather_setup.md) — пошаговая инструкция BotFather
- [Получение OpenRouter API ключа](doc/guides/openrouter_setup.md) — регистрация и настройка LLM

---

## 🛠️ Команды Makefile

```bash
make help          # Показать все доступные команды
make install       # Установить зависимости
make install-dev   # Установить зависимости для разработки
make run           # Запустить бота локально
make test          # Запустить тесты
make docker-build  # Собрать Docker образ
make docker-run    # Запустить в Docker
make docker-stop   # Остановить Docker контейнер
make clean         # Очистить временные файлы
```

---

## 📂 Структура проекта

```
ml_tutor_bot/
├── bot/
│   ├── main.py         # Точка входа
│   ├── handlers.py     # Обработчики команд
│   ├── dialog.py       # Управление диалогами
│   └── prompts.py      # Промпты для LLM
├── llm/
│   └── client.py       # OpenRouter клиент
├── tests/
│   └── test_bot.py     # Тесты
├── doc/                # Документация
│   ├── guides/         # Руководства по настройке
│   ├── vision.md
│   ├── tasklist.md
│   ├── conventions.md
│   └── workflow.md
├── .env                # Переменные окружения (создайте сами)
├── .env.example        # Шаблон .env
├── Dockerfile          # Docker конфигурация
├── Makefile            # Автоматизация задач
└── pyproject.toml      # Зависимости
```

---

## 📄 Лицензия

Проект создан в образовательных целях.

---

**Технологии:** Python • aiogram • OpenRouter API • Docker • Railway • pytest • uv
