"""
Пакет кэширования для parser-2gis.

Предоставляет функциональность для кэширования результатов парсинга
в локальной базе данных SQLite.

Пример использования:
    >>> from parser_2gis.cache import CacheManager
    >>> cache = CacheManager(Path("cache"))
    >>> cache.get("some_key")
    >>> cache.set("key", {"data": "value"})
    >>> cache.close()
"""

from ..constants import (
    CONNECTION_MAX_AGE,
    DEFAULT_BATCH_SIZE,
    LRU_EVICT_BATCH,
    MAX_BATCH_SIZE,
    MAX_CACHE_SIZE_MB,
    MAX_CONNECTION_AGE,
    MAX_POOL_SIZE,
    MIN_POOL_SIZE,
    SHA256_HASH_LENGTH,
)
from .manager import Cache, CacheManager
from .pool import (
    _PSUTIL_AVAILABLE,
    ConnectionPool,
    _calculate_dynamic_pool_size,
    _validate_pool_env_int,
)
from .serializer import JsonSerializer
from .validator import CacheDataValidator, _validate_cached_data

# Для обратной совместимости с тестами
_ConnectionPool = ConnectionPool

# Экспортируем psutil для тестов (если доступен)
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

__all__ = [
    "CacheManager",
    "Cache",
    "ConnectionPool",
    "_ConnectionPool",  # Для обратной совместимости с тестами
    "JsonSerializer",
    "CacheDataValidator",
    # Функции
    "_calculate_dynamic_pool_size",
    "_validate_pool_env_int",
    "_validate_cached_data",  # Для обратной совместимости с тестами
    # Переменные
    "_PSUTIL_AVAILABLE",
    "psutil",  # Для тестов
    # Константы
    "DEFAULT_BATCH_SIZE",
    "MAX_CONNECTION_AGE",
    "MAX_BATCH_SIZE",
    "MAX_CACHE_SIZE_MB",
    "LRU_EVICT_BATCH",
    "SHA256_HASH_LENGTH",
    "MAX_POOL_SIZE",
    "MIN_POOL_SIZE",
    "CONNECTION_MAX_AGE",
]
