# Оптимизация размера Docker образа

## Проблема
Образ Docker превысил лимит в 4GB из-за тяжелых зависимостей RAG.

## Решения

### 1. Оптимизированные зависимости (текущий подход)
- ✅ Убрали LangChain (не используется)
- ✅ Используем легкую модель `all-MiniLM-L6-v2` (22MB вместо 420MB)
- ✅ Многоэтапная сборка Docker
- ✅ Добавили .dockerignore

### 2. Альтернативный легкий вариант
Если размер все еще критичен, используйте `pyproject-light.toml`:
- Только PyPDF2 + scikit-learn
- Без ChromaDB и SentenceTransformers
- Размер образа: ~500MB

### 3. Дополнительные оптимизации

#### Уменьшить размер модели:
```python
# В vector_store.py заменить на еще более легкую модель
self.embeddings_model = SentenceTransformer(
    'sentence-transformers/all-MiniLM-L6-v2'  # 22MB
)
```

#### Использовать CPU-only версии:
```dockerfile
# В Dockerfile добавить переменную окружения
ENV SENTENCE_TRANSFORMERS_HOME=/tmp
ENV HF_HOME=/tmp
```

#### Очистить кэш после установки:
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    rm -rf /root/.cache/pip
```

## Ожидаемый размер образа
- **С оптимизацией**: ~2-3GB
- **Легкий вариант**: ~500MB
- **Без RAG**: ~200MB

## Рекомендации
1. Сначала попробуйте оптимизированную версию
2. Если не помещается - используйте легкий вариант
3. Для продакшена рассмотрите отдельные сервисы для RAG
