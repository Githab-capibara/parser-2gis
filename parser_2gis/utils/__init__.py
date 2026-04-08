"""Пакет утилит для parser-2gis.

Содержит вспомогательные модули:
- decorators: Декораторы ожидания завершения операций
- url_utils: Генерация URL для парсинга
- sanitizers: Санитаризация чувствительных данных
- validation_utils: Валидация городов и категорий, обработка ошибок
- data_utils: Преобразование структур данных
- math_utils: Математические операции
- cache_monitor: Мониторинг статистики кэшей
- path_utils: Валидация безопасности путей
- retry: Повторные попытки с экспоненциальной задержкой
"""

# NOTE: Циклический импорт: constants -> parser -> parser.options -> utils -> constants
# Данный пакет импортируется из parser.options, замыкая цикл зависимостей.
from .cache_monitor import get_cache_stats, log_cache_stats
from .data_utils import unwrap_dot_dict
from .decorators import (
    DEFAULT_POLL_INTERVAL,
    EXPONENTIAL_BACKOFF_MULTIPLIER,
    MAX_POLL_INTERVAL,
    async_wait_until_finished,
    wait_until_finished,
)
from .math_utils import floor_to_hundreds
from .path_utils import FORBIDDEN_PATH_CHARS, validate_path_safety, validate_path_traversal
from .retry import (
    RetryError,
    is_tenacity_available,
    retry_with_backoff,
    retry_with_fixed_delay,
    retry_with_jitter,
    retry_with_tenacity,
)
from .sanitizers import _check_value_type_and_sensitivity, _is_sensitive_key, _sanitize_value
from .url_utils import (
    _generate_category_url_cached,
    generate_category_url,
    generate_city_urls,
    url_query_encode,
)
from .validation_utils import (
    _validate_category,
    _validate_category_cached,
    _validate_city,
    _validate_city_cached,
    report_from_validation_error,
)

# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    # Декораторы
    "wait_until_finished",
    "async_wait_until_finished",
    # Константы polling
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    # URL утилиты
    "generate_category_url",
    "generate_city_urls",
    "url_query_encode",
    "_generate_category_url_cached",
    # Санитаризация
    "_sanitize_value",
    "_is_sensitive_key",
    "_check_value_type_and_sensitivity",
    # Валидация
    "_validate_city",
    "_validate_category",
    "_validate_city_cached",
    "_validate_category_cached",
    "report_from_validation_error",
    # Преобразование данных
    "unwrap_dot_dict",
    # Математические утилиты
    "floor_to_hundreds",
    # Мониторинг кэшей
    "get_cache_stats",
    "log_cache_stats",
    # Валидация путей
    "validate_path_safety",
    "validate_path_traversal",
    "FORBIDDEN_PATH_CHARS",
    # Повторные попытки
    "retry_with_backoff",
    "retry_with_fixed_delay",
    "retry_with_jitter",
    "retry_with_tenacity",
    "is_tenacity_available",
    "RetryError",
]
