"""Система отслеживания прогресса обучения пользователей"""

import logging
from typing import Dict, Set, List

logger = logging.getLogger(__name__)

# Глобальное хранилище прогресса пользователей
# В реальном приложении это должно быть в базе данных
_user_progress: Dict[int, Set[str]] = {}

# Определяем темы курса Math
MATH_COURSE_TOPICS = [
    # Линейная алгебра
    "math_vectors_operations",
    "math_matrices_operations", 
    "math_eigenvalues_vectors",
    "math_orthogonality_projections",
    "math_svd_pca",
    
    # Матан и оптимизация
    "math_derivatives_partial",
    "math_gradients_chain_rule",
    "math_gradients_matrix_form",
    "math_gradient_descent",
    "math_adam_optimizers",
    "math_convex_functions",
    "math_loss_functions",
    "math_regularization",
    
    # Вероятность и статистика
    "math_random_variables",
    "math_expectation_variance",
    "math_bayes_theorem",
    "math_mle",
    "math_entropy_divergence"
]

# Определяем темы курса ML
ML_COURSE_TOPICS = [
    # Основы ML
    "ml_introduction",
    "ml_task_types",
    "ml_supervised_unsupervised",
    "ml_overfitting_underfitting",
    "ml_validation_testing",
    
    # Алгоритмы
    "ml_linear_regression",
    "ml_logistic_regression",
    "ml_decision_trees",
    "ml_random_forest",
    "ml_svm",
    "ml_kmeans_clustering",
    "ml_neural_networks",
    
    # Практика
    "ml_pandas_numpy",
    "ml_matplotlib_seaborn",
    "ml_scikit_learn",
    "ml_model_evaluation",
    "ml_feature_engineering",
    "ml_real_projects"
]


def get_user_progress(user_id: int) -> Set[str]:
    """
    Получить прогресс пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Set[str]: Множество завершенных тем
    """
    return _user_progress.get(user_id, set())


def mark_topic_completed(user_id: int, topic_id: str) -> None:
    """
    Отметить тему как завершенную
    
    Args:
        user_id: ID пользователя
        topic_id: ID темы
    """
    if user_id not in _user_progress:
        _user_progress[user_id] = set()
    
    _user_progress[user_id].add(topic_id)
    logger.info(f"Пользователь {user_id} завершил тему: {topic_id}")


def is_topic_completed(user_id: int, topic_id: str) -> bool:
    """
    Проверить, завершена ли тема
    
    Args:
        user_id: ID пользователя
        topic_id: ID темы
        
    Returns:
        bool: True если тема завершена
    """
    return topic_id in get_user_progress(user_id)


def get_course_progress(user_id: int, course_type: str) -> Dict[str, bool]:
    """
    Получить прогресс по курсу
    
    Args:
        user_id: ID пользователя
        course_type: Тип курса ('math' или 'ml')
        
    Returns:
        Dict[str, bool]: Словарь {topic_id: is_completed}
    """
    topics = MATH_COURSE_TOPICS if course_type == 'math' else ML_COURSE_TOPICS
    user_progress = get_user_progress(user_id)
    
    return {topic: topic in user_progress for topic in topics}


def get_course_stats(user_id: int, course_type: str) -> Dict[str, int]:
    """
    Получить статистику курса
    
    Args:
        user_id: ID пользователя
        course_type: Тип курса ('math' или 'ml')
        
    Returns:
        Dict[str, int]: Статистика {completed, total, percentage}
    """
    progress = get_course_progress(user_id, course_type)
    completed = sum(1 for is_done in progress.values() if is_done)
    total = len(progress)
    percentage = int((completed / total) * 100) if total > 0 else 0
    
    return {
        'completed': completed,
        'total': total,
        'percentage': percentage
    }


def format_course_progress_text(user_id: int, course_type: str) -> str:
    """
    Форматировать текст прогресса курса для отображения
    
    Args:
        user_id: ID пользователя
        course_type: Тип курса ('math' или 'ml')
        
    Returns:
        str: Отформатированный текст с прогрессом
    """
    stats = get_course_stats(user_id, course_type)
    progress = get_course_progress(user_id, course_type)
    
    if course_type == 'math':
        course_name = "МАТЕМАТИЧЕСКИЕ ОСНОВЫ ML"
        topics = MATH_COURSE_TOPICS
        topic_names = [
            "Векторы и операции",
            "Матрицы и основные операции", 
            "Собственные значения и векторы",
            "Ортогональность и проекции",
            "SVD и PCA",
            "Производные и частные производные",
            "Градиенты и цепное правило",
            "Градиенты в матричной форме",
            "Градиентный спуск (GD, SGD)",
            "Adam и другие оптимизаторы",
            "Выпуклые и невыпуклые функции",
            "Функции потерь (MSE, Cross-Entropy)",
            "Регуляризация (L1, L2)",
            "Случайные величины и распределения",
            "Матожидание, дисперсия, ковариация",
            "Байесовская теорема",
            "Maximum Likelihood Estimation (MLE)",
            "Энтропия и дивергенции"
        ]
    else:
        course_name = "МАШИННОЕ ОБУЧЕНИЕ"
        topics = ML_COURSE_TOPICS
        topic_names = [
            "Что такое машинное обучение",
            "Типы задач ML (классификация, регрессия, кластеризация)",
            "Обучение с учителем vs без учителя",
            "Переобучение и недообучение",
            "Валидация и тестирование",
            "Линейная регрессия",
            "Логистическая регрессия",
            "Деревья решений",
            "Случайный лес",
            "SVM",
            "K-means кластеризация",
            "Нейронные сети",
            "Работа с данными (pandas, numpy)",
            "Визуализация (matplotlib, seaborn)",
            "Scikit-learn",
            "Оценка качества моделей",
            "Feature Engineering",
            "Реальные проекты"
        ]
    
    # Заголовок с прогрессом
    header = f"📚 **{course_name}**\n\n"
    header += f"📊 **Прогресс: {stats['completed']}/{stats['total']} тем ({stats['percentage']}%)**\n\n"
    
    # Группируем темы по разделам
    if course_type == 'math':
        sections = [
            ("▲ **ЛИНЕЙНАЯ АЛГЕБРА**", topics[:5], topic_names[:5]),
            ("▲ **МАТАН И ОПТИМИЗАЦИЯ**", topics[5:13], topic_names[5:13]),
            ("▲ **ВЕРОЯТНОСТЬ И СТАТИСТИКА**", topics[13:], topic_names[13:])
        ]
    else:
        sections = [
            ("▲ **ОСНОВЫ ML**", topics[:5], topic_names[:5]),
            ("▲ **АЛГОРИТМЫ**", topics[5:12], topic_names[5:12]),
            ("▲ **ПРАКТИКА**", topics[12:], topic_names[12:])
        ]
    
    result = header
    
    for section_name, section_topics, section_names in sections:
        result += f"{section_name}\n"
        
        for i, (topic_id, topic_name) in enumerate(zip(section_topics, section_names), 1):
            is_completed = progress[topic_id]
            status_icon = "✅" if is_completed else "❌"
            result += f"{i}. {status_icon} {topic_name}\n"
        
        result += "\n"
    
    return result
