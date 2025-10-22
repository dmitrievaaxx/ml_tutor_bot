#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных с курсами
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.database import Database


def main():
    """Инициализация базы данных с курсами"""
    print("Инициализация базы данных ML Tutor Bot...")
    
    # Создаем экземпляр базы данных
    db = Database()
    
    # Проверяем, есть ли уже курс Math
    existing_course = db.get_course(1)
    if existing_course:
        print(f"Курс '{existing_course.name}' уже существует в базе данных")
        return
    
    # Загружаем курс из JSON файла
    json_path = project_root / "data" / "math_course.json"
    if not json_path.exists():
        print(f"Файл курса не найден: {json_path}")
        return
    
    try:
        course_id = db.load_course_from_json(str(json_path))
        print(f"Курс успешно загружен в базу данных с ID: {course_id}")
        
        # Проверяем количество уроков
        course = db.get_course(course_id)
        if course:
            print(f"Курс '{course.name}': {course.total_lessons} уроков")
            
            # Показываем первые несколько уроков
            for i in range(1, min(4, course.total_lessons + 1)):
                lesson = db.get_lesson(course_id, i)
                if lesson:
                    print(f"  Урок {i}: {lesson.title}")
        
    except Exception as e:
        print(f"Ошибка при загрузке курса: {e}")
        return
    
    print("Инициализация завершена успешно!")


if __name__ == "__main__":
    main()
