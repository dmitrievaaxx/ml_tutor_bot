# Быстрый старт: Деплой бота в облако

Это краткая инструкция для быстрого развертывания ML Tutor Bot в облаке.

## Выбор платформы

### Railway (рекомендуется) ⭐

**Преимущества:**
- ✅ Проще всего - деплой за 5 минут
- ✅ Без кредитной карты
- ✅ Бесплатный тариф ($5 кредитов/месяц)

**Недостатки:**
- ⚠️ Кредиты могут закончиться через месяц

### Fly.io (альтернатива)

**Преимущества:**
- ✅ Полностью бесплатно (free tier навсегда)
- ✅ Больше контроля

**Недостатки:**
- ⚠️ Требуется кредитная карта
- ⚠️ Сложнее настройка (CLI)

---

## Вариант 1: Railway (5 минут)

### Шаг 1: Подготовка GitHub

```bash
# Инициализируйте git (если не сделано)
git init
git add .
git commit -m "Ready for Railway deployment"

# Создайте репозиторий на GitHub и загрузите код
git remote add origin https://github.com/ваш-username/ml-tutor-bot.git
git push -u origin main
```

### Шаг 2: Railway

1. Откройте https://railway.app
2. Нажмите **"Login with GitHub"**
3. Нажмите **"New Project"**
4. Выберите **"Deploy from GitHub repo"**
5. Выберите ваш репозиторий `ml-tutor-bot`

### Шаг 3: Переменные окружения

В Railway → Variables → New Variable:

```
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
OPENROUTER_API_KEY=ваш_ключ_от_openrouter
LLM_MODEL=mistralai/mistral-7b-instruct:free
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
LOG_LEVEL=INFO
```

### Шаг 4: Готово!

Railway автоматически:
- Найдет ваш Dockerfile
- Соберет образ
- Развернет бота

**Проверьте логи:**
- Deployments → Active deployment
- Должно быть: "Бот запущен и готов к работе"

**Проверьте бота в Telegram:**
- Найдите бота
- `/start`
- Если отвечает - всё работает! 🎉

---

## Вариант 2: Fly.io (10 минут)

### Шаг 1: Установка CLI

**Windows:**
```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

**Linux/Mac:**
```bash
curl -L https://fly.io/install.sh | sh
```

### Шаг 2: Регистрация

```bash
fly auth signup
```

- Откроется браузер
- Зарегистрируйтесь
- **Добавьте кредитную карту** (бесплатно в пределах free tier)

### Шаг 3: Деплой

```bash
# Перейдите в директорию проекта
cd C:\Users\darya\Documents\ML-tutor-bot\ml_tutor_bot

# Инициализация
fly launch

# Ответьте на вопросы:
# - App name: ml-tutor-bot
# - Region: Amsterdam (ams)
# - Database: No
# - Redis: No
# - Deploy now: No

# Добавьте секреты
fly secrets set TELEGRAM_BOT_TOKEN=ваш_токен
fly secrets set OPENROUTER_API_KEY=ваш_ключ

# Деплой
fly deploy
```

### Шаг 4: Проверка

```bash
# Проверьте статус
fly status

# Проверьте логи
fly logs

# Должно быть: "Бот запущен и готов к работе"
```

**Проверьте бота в Telegram** - он должен отвечать!

---

## Что дальше?

### Автоматический деплой

**Railway:**
- Уже настроен! Просто делайте `git push`

**Fly.io:**
- Настройте GitHub Actions (см. полную инструкцию)

### Мониторинг

**Railway:**
- Web UI → Deployments → Логи
- Settings → Usage (проверка кредитов)

**Fly.io:**
- `fly logs -f` (realtime логи)
- `fly dashboard` (веб интерфейс)

### Если что-то не работает

1. **Проверьте логи** - там будет описание ошибки
2. **Проверьте токены** - они должны быть корректными
3. **См. полные инструкции:**
   - Railway: [doc/guides/railway_deployment.md](guides/railway_deployment.md)
   - Fly.io: [doc/guides/flyio_deployment.md](guides/flyio_deployment.md)

---

## Стоимость

### Railway
- **Бесплатно:** $5 кредитов/месяц (~25-50 дней работы)
- **Платно:** $5/месяц за дополнительные кредиты

### Fly.io
- **Бесплатно:** Полностью free tier (∞ при умеренной нагрузке)
- **Платно:** $1.94/месяц за больше ресурсов

---

## Сравнение

| Критерий | Railway | Fly.io |
|----------|---------|--------|
| Простота | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Время деплоя | 5 мин | 10 мин |
| Нужна карта | ❌ | ✅ |
| Стоимость | $5/мес кредиты | Бесплатно |
| Интерфейс | Web | CLI |

**Рекомендация:** Начните с Railway. Если закончатся кредиты - переходите на Fly.io.

---

**Поздравляем! Ваш бот в облаке! 🚀**

Подробные инструкции:
- [Полная инструкция Railway](guides/railway_deployment.md)
- [Полная инструкция Fly.io](guides/flyio_deployment.md)
- [Сравнение платформ](CLOUD_DEPLOYMENT_OPTIONS.md)


