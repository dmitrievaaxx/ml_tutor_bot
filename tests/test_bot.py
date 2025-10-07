"""Тесты логики диалогов и уровней знаний"""

import pytest
from bot.dialog import (
    clear_dialog,
    add_user_message,
    add_assistant_message,
    extract_user_level,
    get_dialog_history,
    is_first_level_selection,
    get_system_prompt
)


class TestDialogLevels:
    """Тесты для работы с уровнями знаний"""
    
    def test_extract_user_level_basic(self):
        """Тест извлечения уровня из истории диалога"""
        chat_id = 12345
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Добавляем сообщение с уровнем
        add_user_message(chat_id, "Базовый")
        
        # Проверяем извлечение уровня
        level = extract_user_level(chat_id)
        assert level == "Базовый"
    
    def test_extract_user_level_multiple_messages(self):
        """Тест извлечения уровня когда есть несколько сообщений"""
        chat_id = 12346
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Добавляем несколько сообщений
        add_user_message(chat_id, "Привет")
        add_user_message(chat_id, "Новичок")
        add_user_message(chat_id, "Как дела?")
        
        # Проверяем извлечение уровня
        level = extract_user_level(chat_id)
        assert level == "Новичок"
    
    def test_extract_user_level_no_level(self):
        """Тест когда уровень не выбран"""
        chat_id = 12347
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Добавляем сообщения без уровня
        add_user_message(chat_id, "Привет")
        add_user_message(chat_id, "Как дела?")
        
        # Проверяем что уровень не найден
        level = extract_user_level(chat_id)
        assert level is None
    
    def test_level_change_preserves_latest(self):
        """Тест что при смене уровня сохраняется последний выбранный"""
        chat_id = 12348
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Выбираем первый уровень
        add_user_message(chat_id, "Новичок")
        level1 = extract_user_level(chat_id)
        assert level1 == "Новичок"
        
        # Меняем на другой уровень
        add_user_message(chat_id, "Продвинутый")
        level2 = extract_user_level(chat_id)
        assert level2 == "Продвинутый"
    
    def test_clear_dialog_preserves_level(self):
        """Тест что clear_dialog сохраняет уровень"""
        chat_id = 12349
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Выбираем уровень
        add_user_message(chat_id, "Базовый")
        assert extract_user_level(chat_id) == "Базовый"
        
        # Очищаем диалог
        clear_dialog(chat_id)
        
        # Проверяем что уровень сохранился
        assert extract_user_level(chat_id) == "Базовый"
        
        # Проверяем что история содержит только системный промпт и уровень
        history = get_dialog_history(chat_id)
        assert len(history) == 2
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "user"
        assert history[1]["content"] == "Базовый"
    
    def test_is_first_level_selection(self):
        """Тест определения первого выбора уровня"""
        chat_id = 12350
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Первый выбор уровня
        add_user_message(chat_id, "Новичок")
        assert is_first_level_selection(chat_id) == True
        
        # Второй выбор уровня (смена)
        add_user_message(chat_id, "Продвинутый")
        assert is_first_level_selection(chat_id) == False
    
    def test_system_prompt_updates_with_level(self):
        """Тест что системный промпт обновляется с уровнем"""
        chat_id = 12351
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Выбираем уровень
        add_user_message(chat_id, "Новичок")
        
        # Получаем историю
        history = get_dialog_history(chat_id)
        
        # Проверяем что системный промпт содержит уровень "Новичок"
        system_prompt = history[0]["content"]
        assert "НОВИЧОК" in system_prompt
        assert "Простые слова" in system_prompt
    
    def test_all_levels_work(self):
        """Тест что все уровни работают корректно"""
        chat_id = 12352
        
        levels = ["Новичок", "Базовый", "Продвинутый"]
        
        for level in levels:
            # Очищаем историю
            clear_dialog(chat_id)
            
            # Выбираем уровень
            add_user_message(chat_id, level)
            
            # Проверяем извлечение
            extracted_level = extract_user_level(chat_id)
            assert extracted_level == level
            
            # Проверяем системный промпт
            history = get_dialog_history(chat_id)
            system_prompt = history[0]["content"]
            assert level.upper() in system_prompt


class TestDialogHistory:
    """Тесты для работы с историей диалогов"""
    
    def test_dialog_history_creation(self):
        """Тест создания истории диалога"""
        chat_id = 12353
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Получаем историю
        history = get_dialog_history(chat_id)
        
        # Проверяем что история создана
        assert len(history) >= 1
        assert history[0]["role"] == "system"
    
    def test_add_messages(self):
        """Тест добавления сообщений в историю"""
        chat_id = 12354
        
        # Очищаем историю
        clear_dialog(chat_id)
        
        # Добавляем сообщения
        add_user_message(chat_id, "Привет")
        add_assistant_message(chat_id, "Привет! Как дела?")
        
        # Получаем историю
        history = get_dialog_history(chat_id)
        
        # Проверяем что сообщения добавлены
        assert len(history) >= 3  # system + user + assistant
        assert history[-2]["role"] == "user"
        assert history[-2]["content"] == "Привет"
        assert history[-1]["role"] == "assistant"
        assert history[-1]["content"] == "Привет! Как дела?"