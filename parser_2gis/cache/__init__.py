"""Пакет кэширования для parser-2gis.

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
    MAX_DATA_DEPTH,
    MAX_POOL_SIZE,
    MAX_STRING_LENGTH,
    MIN_POOL_SIZE,
    SHA256_HASH_LENGTH,
    validate_env_int,
)
from .manager import Cache, CacheManager
from .pool import PSUTIL_AVAILABLE, ConnectionPool, _calculate_dynamic_pool_size
from .serializer import JsonSerializer, _deserialize_json, _serialize_json
from .validator import CacheDataValidator
from .config_cache import ConfigCache, get_config_cache, CategoryDict

# Для обратной совместимости с тестами
_ConnectionPool = ConnectionPool

# Алиас для обратной совместимости
_validate_pool_env_int = validate_env_int

# Экспортируем psutil для тестов (если доступен)
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

__all__ = [
    "CONNECTION_MAX_AGE",
    "DEFAULT_BATCH_SIZE",
    "LRU_EVICT_BATCH",
    "MAX_BATCH_SIZE",
    "MAX_CACHE_SIZE_MB",
    "MAX_CONNECTION_AGE",
    "MAX_DATA_DEPTH",  # Для обратной совместимости с тестами
    "MAX_POOL_SIZE",
    "MAX_STRING_LENGTH",  # Для обратной совместимости с тестами
    "MIN_POOL_SIZE",
    "SHA256_HASH_LENGTH",
    "PSUTIL_AVAILABLE",
    "Cache",
    "CacheDataValidator",
    "CacheManager",
    "CategoryDict",
    "ConfigCache",
    "ConnectionPool",
    "JsonSerializer",
    "_ConnectionPool",  # Для обратной совместимости с тестами
    "_calculate_dynamic_pool_size",
    "_deserialize_json",  # Для обратной совместимости с тестами
    "_serialize_json",  # Для обратной совместимости с тестами
    "_validate_pool_env_int",  # Алиас для обратной совместимости
    "get_config_cache",
    "psutil",  # Для тестов
    "validate_env_int",
]
