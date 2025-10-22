# Исправление ошибки "Instance is frozen" для кнопки "Меню курса"

## 🐛 **Проблема:**
```
ValidationError: 1 validation error for CallbackQuery
data
  Instance is frozen [type=frozen_instance, input_value='course_1', input_type=str]
```

## 🔍 **Причина:**
Объект `CallbackQuery` в aiogram является неизменяемым (frozen). Мы пытались изменить `callback_query.data`, что вызывало ошибку валидации Pydantic.

## ✅ **Исправление:**

### **Старый код (неправильный):**
```python
elif data.startswith("back_to_course_"):
    course_id = int(data.split("_")[-1])
    callback_query.data = f"course_{course_id}"  # ❌ Ошибка: объект frozen
    await handle_course_selection(callback_query)
```

### **Новый код (правильный):**
```python
elif data.startswith("back_to_course_"):
    course_id = int(data.split("_")[-1])
    # Создаем новый callback query с правильными данными
    from aiogram.types import CallbackQuery
    new_callback = CallbackQuery(
        id=callback_query.id,
        from_user=callback_query.from_user,
        message=callback_query.message,
        data=f"course_{course_id}",
        chat_instance=callback_query.chat_instance
    )
    await handle_course_selection(new_callback)  # ✅ Используем новый объект
```

## 🎯 **Результат:**
Теперь кнопка "📚 Меню курса" должна работать без ошибок и правильно показывать план курса.

## 🔧 **Технические детали:**
- Создаем новый объект `CallbackQuery` вместо изменения существующего
- Копируем все необходимые поля из оригинального callback
- Устанавливаем правильное значение `data` в новом объекте

## 🚀 **Для применения изменений:**
Перезапустите бота, чтобы исправление вступило в силу.

Исправление вступит в силу сразу после перезапуска! 🎉
