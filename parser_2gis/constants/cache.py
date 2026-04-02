"""Константы кэширования для parser-2gis.

Этот модуль содержит константы связанные с кэшированием:
- Размеры кэша
- Параметры connection pool
- TTL и batch размеры

Пример использования:
    >>> from parser_2gis.constants.cache import MAX_CACHE_SIZE_MB, MAX_POOL_SIZE
    >>> print(f"Максимальный размер кэша: {MAX_CACHE_SIZE_MB} MB")
"""

from __future__ import annotations

# =============================================================================
# РАЗМЕРЫ КЭША
# =============================================================================

# Максимальный размер кэша в MB
MAX_CACHE_SIZE_MB: int = 500

# Размер batch по умолчанию
DEFAULT_BATCH_SIZE: int = 100

# Максимальный размер batch
MAX_BATCH_SIZE: int = 1000

# Размер batch для LRU eviction
LRU_EVICT_BATCH: int = 100

# Длина SHA256 хэша
SHA256_HASH_LENGTH: int = 64


# =============================================================================
# CONNECTION POOL
# =============================================================================

# Максимальный размер пула соединений
MAX_POOL_SIZE: int = 20

# Минимальный размер пула соединений
MIN_POOL_SIZE: int = 5

# Максимальный возраст соединения в секундах
CONNECTION_MAX_AGE: int = 600

# Максимальный возраст соединения (алиас)
MAX_CONNECTION_AGE: int = 600

# ISSUE-067: Имя файла кэша по умолчанию
DEFAULT_CACHE_FILE_NAME: str = "cache.db"

# ISSUE-068: Директория output по умолчанию
DEFAULT_OUTPUT_DIR: str = "output"

# ISSUE-065: TTL кэша по умолчанию (часы)
DEFAULT_TTL_HOURS: int = 24


__all__ = [
    "MAX_CACHE_SIZE_MB",
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE",
    "LRU_EVICT_BATCH",
    "SHA256_HASH_LENGTH",
    "MAX_POOL_SIZE",
    "MIN_POOL_SIZE",
    "CONNECTION_MAX_AGE",
    "MAX_CONNECTION_AGE",
    "DEFAULT_CACHE_FILE_NAME",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_TTL_HOURS",
]
