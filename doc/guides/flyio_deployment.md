# Деплой Telegram-бота на Fly.io (Альтернатива Railway)

Fly.io - это платформа для развертывания приложений с отличной поддержкой Docker и глобальной сетью серверов.

## Когда использовать Fly.io вместо Railway?

- ✅ Закончились кредиты на Railway
- ✅ Нужен больший контроль над инфраструктурой
- ✅ Требуется развертывание в разных регионах мира
- ✅ Нужно больше ресурсов бесплатно (до 3 VM)

## Преимущества Fly.io

- ✅ **Бесплатный тариф**: До 3 shared-cpu VM бесплатно
- ✅ **Всегда активен**: Не "засыпает" в отличие от некоторых платформ
- ✅ **Отличная работа с Docker**: Fly.io построен на Docker
- ✅ **Глобальная сеть**: Можно развернуть в разных регионах
- ✅ **Мощные CLI инструменты**: Полный контроль через командную строку

## Недостатки

- ⚠️ **Требуется кредитная карта**: Даже для бесплатного тарифа
- ⚠️ **Сложнее настройка**: Требуется работа с CLI
- ⚠️ **Кривая обучения**: Не так просто как Railway для новичков

---

## Предварительные требования

1. **Кредитная карта** - для активации бесплатного тарифа
2. **Telegram бот токен** - от @BotFather
3. **OpenRouter API ключ** - от https://openrouter.ai/
4. **Git репозиторий** - с вашим кодом

---

## Шаг 1: Установка Fly CLI

### Windows

```powershell
# Установка через PowerShell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### Linux/Mac

```bash
# Установка через curl
curl -L https://fly.io/install.sh | sh
```

### Проверка установки

```bash
fly version
```

**Ожидаемый вывод:**
```
flyctl v0.x.x ...
```

---

## Шаг 2: Регистрация и авторизация

### 2.1. Регистрация на Fly.io

```bash
fly auth signup
```

Откроется браузер для регистрации:
1. Введите email
2. Создайте пароль
3. Подтвердите email
4. **Добавьте кредитную карту** (списаний не будет в пределах free tier)

### 2.2. Авторизация (если уже зарегистрированы)

```bash
fly auth login
```

### 2.3. Проверка авторизации

```bash
fly auth whoami
```

**Должен показать ваш email.**

---

## Шаг 3: Подготовка проекта

### 3.1. Перейдите в директорию проекта

```bash
cd C:\Users\darya\Documents\ML-tutor-bot\ml_tutor_bot
```

### 3.2. Инициализация приложения на Fly.io

```bash
fly launch
```

Fly CLI задаст несколько вопросов:

**1. Choose an app name (leave blank to generate one):**
```
ml-tutor-bot
```
*(или оставьте пустым для автогенерации)*

**2. Choose a region for deployment:**
```
Amsterdam, Netherlands (ams)
```
*(выберите ближайший к вашим пользователям регион)*

**3. Would you like to set up a Postgresql database?**
```
No
```
*(нам не нужна БД)*

**4. Would you like to set up an Upstash Redis database?**
```
No
```

**5. Would you like to deploy now?**
```
No
```
*(сначала настроим переменные окружения)*

### 3.3. Результат

Fly CLI создаст файл `fly.toml` с конфигурацией.

---

## Шаг 4: Настройка fly.toml

Откройте созданный `fly.toml` и убедитесь, что он выглядит примерно так:

```toml
# fly.toml app configuration file generated for ml-tutor-bot
# See https://fly.io/docs/reference/configuration/ for information about how to use this file.

app = "ml-tutor-bot"
primary_region = "ams"

[build]
  # Fly.io автоматически найдет ваш Dockerfile

[env]
  # Публичные переменные окружения (не секреты)
  LOG_LEVEL = "INFO"
  LLM_MODEL = "mistralai/mistral-7b-instruct:free"
  LLM_TEMPERATURE = "0.7"
  LLM_MAX_TOKENS = "500"

[[services]]
  # Telegram бот не требует открытых портов
  # Но Fly.io требует хотя бы один сервис
  # Можно оставить закомментированным

# [http_service]
#   internal_port = 8080
#   force_https = true
#   auto_stop_machines = false
#   auto_start_machines = false
```

### Важно для Telegram ботов

Telegram боты с polling не требуют открытых портов. Удалите или закомментируйте секцию `[[services]]` если она есть.

**Альтернатива:** Можно добавить простой health check endpoint, но для учебного бота это не обязательно.

---

## Шаг 5: Добавление секретов (переменных окружения)

### 5.1. Установка токенов

```bash
# Установка Telegram Bot Token
fly secrets set TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather

# Установка OpenRouter API Key
fly secrets set OPENROUTER_API_KEY=ваш_ключ_от_openrouter
```

### 5.2. Проверка секретов

```bash
fly secrets list
```

**Должны увидеть:**
```
NAME                     DIGEST                  CREATED AT
OPENROUTER_API_KEY       xxxxxxxxxxxx           1m ago
TELEGRAM_BOT_TOKEN       xxxxxxxxxxxx           1m ago
```

⚠️ **Примечание**: Значения секретов не показываются (только digest для безопасности).

---

## Шаг 6: Деплой приложения

### 6.1. Запуск деплоя

```bash
fly deploy
```

Процесс деплоя:
1. 📦 Загрузка контекста сборки
2. 🐳 Сборка Docker образа
3. 🚀 Развертывание на Fly.io
4. ✅ Проверка здоровья приложения

**Время деплоя:** 3-7 минут.

### 6.2. Отслеживание процесса

Вы увидите лог сборки в реальном времени:
```
==> Building image
==> Creating layer from Dockerfile
...
==> Pushing image to fly
...
==> Deploying ml-tutor-bot
```

### 6.3. Ожидаемый результат

```
--> v0 deployed successfully
```

---

## Шаг 7: Проверка работы

### 7.1. Просмотр статуса приложения

```bash
fly status
```

**Ожидаемый вывод:**
```
App
  Name     = ml-tutor-bot
  Owner    = your-email
  Hostname = ml-tutor-bot.fly.dev
  Platform = machines

Machines
ID              PROCESS STATE   REGION  CHECKS  LAST UPDATED
xxxxxxxxxxxxx   app     started ams     1 total 2m ago
```

**STATE должен быть `started`** ✅

### 7.2. Просмотр логов

```bash
fly logs
```

**Должны увидеть:**
```
INFO - Бот запущен и готов к работе
```

**Для постоянного просмотра логов:**
```bash
fly logs -f
```
*(нажмите Ctrl+C чтобы выйти)*

### 7.3. Тестирование бота в Telegram

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Выберите уровень
5. Задайте вопрос

**Если бот отвечает - деплой успешен! 🎉**

---

## Управление приложением на Fly.io

### Просмотр информации о приложении

```bash
# Общая информация
fly info

# Статус машин
fly status

# Детальная информация о ресурсах
fly dashboard
```

*(откроет веб-интерфейс в браузере)*

### Масштабирование

```bash
# Изменить количество машин
fly scale count 1

# Изменить размер VM (если нужно больше ресурсов)
fly scale vm shared-cpu-1x
```

**Для нашего бота достаточно 1 shared-cpu-1x машины.**

### Перезапуск приложения

```bash
# Перезапуск всех машин
fly apps restart ml-tutor-bot
```

### Остановка приложения

```bash
# Приостановить работу (бесплатно)
fly scale count 0

# Возобновить работу
fly scale count 1
```

### Удаление приложения

```bash
# Полное удаление
fly apps destroy ml-tutor-bot
```

---

## Автоматический деплой при изменениях

### Вариант 1: Деплой вручную

После изменений в коде:

```bash
git add .
git commit -m "Улучшил промпты"
git push

# Деплой на Fly.io
fly deploy
```

### Вариант 2: GitHub Actions (автоматически)

Создайте файл `.github/workflows/fly.yml`:

```yaml
name: Fly Deploy

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

**Настройка:**

1. Получите API токен:
   ```bash
   fly auth token
   ```

2. Добавьте токен в GitHub Secrets:
   - Репозиторий → Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `FLY_API_TOKEN`
   - Value: ваш токен

3. Теперь при push в main автоматически будет деплой!

---

## Мониторинг и логирование

### Просмотр метрик

```bash
# Открыть dashboard
fly dashboard
```

В веб-интерфейсе доступны:
- CPU usage
- Memory usage
- Network traffic
- Request metrics (если используются)

### Логирование

```bash
# Последние 100 строк
fly logs

# Живые логи (realtime)
fly logs -f

# Логи с фильтром по уровню
fly logs | grep ERROR
fly logs | grep INFO
```

### Настройка алертов

В веб-dashboard можно настроить:
- Email уведомления при ошибках
- Slack интеграция
- Webhook для мониторинга

---

## Возможные проблемы и решения

### ❌ Проблема: "Error: no such image"

**Решение:**
```bash
# Убедитесь что Dockerfile существует
ls Dockerfile

# Пересоберите
fly deploy --build-only
```

### ❌ Проблема: "Machine failed to start"

**Причины:**
- Ошибка в коде
- Неверные переменные окружения

**Решение:**
```bash
# Проверьте логи
fly logs

# Проверьте секреты
fly secrets list

# Проверьте статус
fly status
```

### ❌ Проблема: "Out of free tier resources"

**Решение:**
```bash
# Проверьте использование ресурсов
fly dashboard

# Уменьшите количество машин
fly scale count 1

# Или перейдите на платный план ($1.94/месяц)
```

### ❌ Проблема: "Region not available"

**Решение:**
```bash
# Список доступных регионов
fly platform regions

# Смените регион
fly regions set ams
```

---

## Стоимость работы на Fly.io

### Бесплатный тариф (Free Tier)

**Включает:**
- До 3 shared-cpu-1x VM (256MB RAM)
- 160 GB traffic/месяц
- Persistent disk: бесплатно до 3GB

**Для нашего бота:**
- 1 VM: ✅ Бесплатно
- ~1-2 GB traffic/месяц: ✅ Бесплатно
- Нет persistent disk: ✅ Бесплатно

**Итого: полностью бесплатно в рамках free tier! 🎉**

### Платный тариф

Если понадобится больше ресурсов:
- **shared-cpu-1x (256MB)**: $1.94/месяц
- **shared-cpu-2x (512MB)**: $3.88/месяц
- **dedicated-cpu-1x (2GB)**: $23.40/месяц

Для учебного бота бесплатного тарифа более чем достаточно.

---

## Сравнение с Railway

| Характеристика | Fly.io | Railway |
|----------------|--------|---------|
| Бесплатный тариф | ✅ 3 VM навсегда | ✅ $5/месяц кредитов |
| Нужна карта | ✅ Да | ❌ Нет |
| Простота | ⭐⭐⭐ Средне | ⭐⭐⭐⭐⭐ Очень просто |
| Интерфейс | CLI + Web | Web (удобнее) |
| Автодеплой | GitHub Actions | Встроенный |
| Логи | CLI + Web | Web (удобнее) |
| Гибкость | ⭐⭐⭐⭐⭐ Высокая | ⭐⭐⭐ Средняя |
| Для новичков | ⚠️ Сложновато | ✅ Идеально |

**Вывод:** Fly.io лучше для опытных пользователей, Railway - для новичков.

---

## Лучшие практики

### 1. Используйте маленькие образы

Оптимизируйте Dockerfile:
```dockerfile
FROM python:3.11-slim  # slim вместо полного образа
```

### 2. Мониторьте логи

```bash
# Регулярно проверяйте логи на ошибки
fly logs | grep ERROR
```

### 3. Настройте автодеплой

Используйте GitHub Actions для автоматизации.

### 4. Бэкапы

- Код в Git
- Секреты задокументированы (но не в коде!)
- fly.toml в репозитории

### 5. Health checks (опционально)

Для продакшена добавьте простой HTTP endpoint для проверки здоровья приложения.

---

## Дополнительные возможности

### Regions (регионы)

Развернуть в нескольких регионах:

```bash
# Добавить регион
fly regions add fra  # Frankfurt

# Список регионов приложения
fly regions list
```

### Autoscaling

Автоматическое масштабирование:

```bash
# Настройка автоскейлинга
fly autoscale set min=1 max=3
```

### Secrets rotation

Обновление секретов:

```bash
# Обновить токен
fly secrets set TELEGRAM_BOT_TOKEN=новый_токен

# Старое значение автоматически перезаписывается
```

---

## Миграция с Railway на Fly.io

Если у вас уже есть бот на Railway:

1. **Подготовка:**
   ```bash
   fly launch --no-deploy
   ```

2. **Перенос секретов:**
   - Скопируйте переменные из Railway
   - Добавьте их в Fly.io через `fly secrets set`

3. **Деплой:**
   ```bash
   fly deploy
   ```

4. **Тестирование:**
   - Убедитесь что бот работает на Fly.io
   
5. **Переключение:**
   - Можно остановить Railway
   - Или держать оба как backup

---

## Итоги

✅ **Что мы сделали:**
- Установили Fly CLI
- Зарегистрировались на Fly.io
- Развернули бота в облаке
- Настроили секреты
- Проверили работу

✅ **Преимущества Fly.io:**
- Полностью бесплатный тариф (в пределах лимитов)
- Не "засыпает"
- Мощные CLI инструменты
- Глобальная сеть серверов

✅ **Когда использовать:**
- Закончились кредиты Railway
- Нужен больший контроль
- Требуется развертывание в разных регионах

---

**Ваш бот работает на Fly.io! 🚀**

Если нужна помощь:
- Документация: https://fly.io/docs/
- Community: https://community.fly.io/
- Поддержка: support@fly.io


