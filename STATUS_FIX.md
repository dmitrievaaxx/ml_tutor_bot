# Исправление ошибки "Database object has no attribute 'get_all_courses'"

## 🐛 **Проблема:**
Команда `/status` не работала из-за отсутствующего метода `get_all_courses()` в классе `Database`:

```
AttributeError: 'Database' object has no attribute 'get_all_courses'
```

## 🔍 **Причина:**
В функции `handle_status` в `bot/handlers.py` использовался метод `db.get_all_courses()`, который не был реализован в классе `Database`.

## ✅ **Исправление:**

### **Добавлен метод в класс Database:**
```python
def get_all_courses(self) -> List[Course]:
    """Get all courses"""
    conn = self.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, description, total_lessons
        FROM courses ORDER BY id
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        Course(id=row[0], name=row[1], description=row[2], total_lessons=row[3])
        for row in rows
    ]
```

## 🎯 **Результат:**

1. **Команда /status работает** - больше нет ошибки AttributeError
2. **Отображается информация о курсах** - показывается прогресс по всем курсам
3. **Стабильность** - бот не падает при вызове команды /status

## 🔧 **Функциональность:**

Метод `get_all_courses()` возвращает список всех курсов из базы данных, что позволяет:
- Показать прогресс пользователя по всем курсам
- Отобразить статистику обучения
- Предоставить полную информацию о доступных курсах

## 🚀 **Для применения изменений:**
Перезапустите бота, чтобы исправление вступило в силу.

**Команда /status теперь работает корректно!** 🎉
