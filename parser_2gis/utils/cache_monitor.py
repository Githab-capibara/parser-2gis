"""
Модуль мониторинга кэшей.

Содержит функции для получения статистики по lru_cache кэшам.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# МОНИТОРИНГ КЭШЕЙ
# =============================================================================


def get_cache_stats() -> Dict[str, Any]:
    """Возвращает статистику по всем кэшам lru_cache.

    - Мониторинг hit/miss ratio для оптимизации размеров кэшей
    - Помогает выявить узкие места производительности
    - Возвращает информацию о размере, попаданиях и промахах

    Returns:
        Словарь со статистикой по каждому кэшу:
        {
            '_validate_city_cached': CacheInfo(hits=..., misses=..., maxsize=..., currsize=...),
            '_validate_category_cached': CacheInfo(...),
            'url_query_encode': CacheInfo(...),
        }

    Example:
        >>> stats = get_cache_stats()
        >>> print(stats['_validate_city_cached'])
        CacheInfo(hits=100, misses=5, maxsize=256, currsize=5)
    """
    from .url_utils import _url_query_encode
    from .validation_utils import _validate_category_cached, _validate_city_cached

    return {
        "_validate_city_cached": _validate_city_cached.cache_info(),
        "_validate_category_cached": _validate_category_cached.cache_info(),
        "url_query_encode": _url_query_encode.cache_info(),
    }


def log_cache_stats() -> None:
    """Выводит статистику кэшей в лог.

    - Автоматический вывод статистики кэшей при завершении парсинга
    - Помогает оптимизировать размеры кэшей на основе реальных данных

    Example:
        >>> log_cache_stats()
        # В лог будет записано:
        # Статистика кэша %s: %s
    """
    stats = get_cache_stats()
    for cache_name, info in stats.items():
        logger.info("Статистика кэша %s: %s", cache_name, info)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = ["get_cache_stats", "log_cache_stats"]
