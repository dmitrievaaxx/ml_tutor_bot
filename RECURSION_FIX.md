# Исправление бесконечной рекурсии в get_user_level_or_default

## 🐛 **Проблема:**
Бесконечная рекурсия в функции `get_user_level_or_default`:

```
get_user_level_or_default() 
  → add_user_message() 
    → get_dialog_history() 
      → get_user_level_or_default() 
        → add_user_message() 
          → get_dialog_history() 
            → get_user_level_or_default() 
              → ... (бесконечная рекурсия)
```

## 🔍 **Причина:**
Функция `get_user_level_or_default` вызывала `add_user_message`, которая в свою очередь вызывала `get_dialog_history`, которая снова вызывала `get_user_level_or_default`.

## ✅ **Исправление:**

### **Старый код (неправильный):**
```python
def get_user_level_or_default(chat_id: int) -> str:
    user_level = extract_user_level(chat_id)
    if user_level is None:
        default_level = "Базовый"
        add_user_message(chat_id, default_level)  # ❌ Вызывает рекурсию
        return default_level
    return user_level
```

### **Новый код (правильный):**
```python
def get_user_level_or_default(chat_id: int) -> str:
    user_level = extract_user_level(chat_id)
    if user_level is None:
        default_level = "Базовый"
        # ✅ Просто возвращаем уровень без добавления в историю
        return default_level
    return user_level
```

## 🎯 **Результат:**

1. **Устранена рекурсия**: Функция больше не вызывает сама себя
2. **Сохранена функциональность**: Уровень по умолчанию все еще возвращается
3. **Стабильность**: Бот больше не падает с ошибкой рекурсии

## 🔧 **Логика работы:**

- Если уровень выбран пользователем → возвращаем его
- Если уровень не выбран → возвращаем "Базовый" без добавления в историю
- Добавление уровня в историю происходит только при явном выборе пользователем

## 🚀 **Для применения изменений:**
Перезапустите бота, чтобы исправление вступило в силу.

Исправление вступит в силу сразу после перезапуска! 🎉
