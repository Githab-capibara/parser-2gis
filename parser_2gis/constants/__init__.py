"""Пакет констант для parser-2gis.

Этот пакет содержит специализированные модули с константами:
- buffer: константы буферизации
- cache: константы кэширования
- parser: константы парсера
- security: константы безопасности
- validation: константы валидации

Пример использования:
    >>> from parser_2gis.constants.buffer import DEFAULT_BUFFER_SIZE
    >>> from parser_2gis.constants.cache import MAX_CACHE_SIZE_MB
"""

from __future__ import annotations

# Импортируем все константы из подмодулей для обратной совместимости
from parser_2gis.constants.buffer import (  # noqa: F401
    CSV_BATCH_SIZE,
    CSV_COLUMNS_PER_ENTITY,
    DEFAULT_BUFFER_SIZE,
    LARGE_FILE_BUFFER_MULTIPLIER,
    LARGE_FILE_THRESHOLD_MB,
    MAX_BUFFER_SIZE,
    MERGE_BATCH_SIZE,
    MERGE_BUFFER_SIZE,
    MMAP_THRESHOLD_BYTES,
)
from parser_2gis.constants.cache import (  # noqa: F401
    CONNECTION_MAX_AGE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CACHE_FILE_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TTL_HOURS,
    LRU_EVICT_BATCH,
    MAX_BATCH_SIZE,
    MAX_CACHE_SIZE_MB,
    MAX_CONNECTION_AGE,
    MAX_POOL_SIZE,
    MIN_POOL_SIZE,
    SHA256_HASH_LENGTH,
)
from parser_2gis.constants.parser import (  # noqa: F401
    CHROME_STARTUP_DELAY,
    DEFAULT_SLEEP_TIME,
    DEFAULT_TIMEOUT,
    EXTERNAL_RATE_LIMIT_CALLS,
    EXTERNAL_RATE_LIMIT_PERIOD,
    GC_MEMORY_THRESHOLD_MB,
    HTTP_CACHE_MAXSIZE,
    HTTP_CACHE_TTL_SECONDS,
    HTTP_STATUS_OK,
    MAX_LOCK_FILE_AGE,
    MAX_RECORDS_BASE_OFFSET,
    MAX_RECORDS_MEMORY_COEFFICIENT,
    MAX_RECORDS_MEMORY_DIVISOR,
    MAX_TEMP_FILES,
    MAX_TEMP_FILES_MONITORING,
    MAX_TIMEOUT,
    MAX_VISITED_LINKS_SIZE,
    MAX_WORKERS,
    MERGE_LOCK_TIMEOUT,
    MIN_TIMEOUT,
    MIN_WORKERS,
    ORPHANED_TEMP_FILE_AGE,
    PROGRESS_UPDATE_INTERVAL,
    TEMP_FILE_CLEANUP_INTERVAL,
)
from parser_2gis.constants.security import (  # noqa: F401
    FORBIDDEN_PATH_CHARS,
    MAX_COLLECTION_SIZE,
    MAX_DATA_DEPTH,
    MAX_DATA_SIZE,
    MAX_DICT_RECURSION_DEPTH,
    MAX_INITIAL_STATE_DEPTH,
    MAX_INITIAL_STATE_SIZE,
    MAX_ITEMS_IN_COLLECTION,
    MAX_JS_CODE_LENGTH,
    MAX_PATH_LENGTH,
    MAX_PATH_LENGTH_SAFE,
    MAX_RESPONSE_SIZE,
    MAX_STRING_LENGTH,
    MAX_TOTAL_JS_SIZE,
    MAX_UNIQUE_NAME_ATTEMPTS,
    MAX_URL_DECODE_ITERATIONS,
)
from parser_2gis.constants.validation import (  # noqa: F401
    MAX_CITIES_COUNT,
    MAX_CITIES_FILE_SIZE,
    MMAP_CITIES_THRESHOLD,
)

# Polling константы уже импортированы из parser.py

# Импортируем EnvConfig для обратной совместимости
from parser_2gis.constants.env_config import EnvConfig, get_env_config, validate_env_int  # noqa: F401

__all__ = [
    # Buffer constants
    "DEFAULT_BUFFER_SIZE",
    "MERGE_BUFFER_SIZE",
    "CSV_BATCH_SIZE",
    "CSV_COLUMNS_PER_ENTITY",
    "MERGE_BATCH_SIZE",
    "LARGE_FILE_THRESHOLD_MB",
    "LARGE_FILE_BUFFER_MULTIPLIER",
    "MAX_BUFFER_SIZE",
    "MMAP_THRESHOLD_BYTES",
    # Cache constants
    "MAX_CONNECTION_AGE",
    "MAX_CACHE_SIZE_MB",
    "LRU_EVICT_BATCH",
    "SHA256_HASH_LENGTH",
    "MAX_POOL_SIZE",
    "MIN_POOL_SIZE",
    "CONNECTION_MAX_AGE",
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE",
    # Parser constants
    "MIN_WORKERS",
    "MAX_WORKERS",
    "MIN_TIMEOUT",
    "MAX_TIMEOUT",
    "DEFAULT_TIMEOUT",
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
    "MERGE_LOCK_TIMEOUT",
    "MAX_LOCK_FILE_AGE",
    "MAX_TEMP_FILES",
    "PROGRESS_UPDATE_INTERVAL",
    "DEFAULT_SLEEP_TIME",
    "MAX_VISITED_LINKS_SIZE",
    "MAX_RECORDS_MEMORY_COEFFICIENT",
    "MAX_RECORDS_MEMORY_DIVISOR",
    "MAX_RECORDS_BASE_OFFSET",
    "GC_MEMORY_THRESHOLD_MB",
    # Security constants
    "MAX_DATA_DEPTH",
    "MAX_STRING_LENGTH",
    "MAX_DATA_SIZE",
    "MAX_COLLECTION_SIZE",
    "MAX_PATH_LENGTH",
    "MAX_INITIAL_STATE_DEPTH",
    "MAX_INITIAL_STATE_SIZE",
    "MAX_ITEMS_IN_COLLECTION",
    "MAX_JS_CODE_LENGTH",
    "MAX_RESPONSE_SIZE",
    "MAX_TOTAL_JS_SIZE",
    "CHROME_STARTUP_DELAY",
    "EXTERNAL_RATE_LIMIT_CALLS",
    "EXTERNAL_RATE_LIMIT_PERIOD",
    "HTTP_CACHE_TTL_SECONDS",
    "HTTP_CACHE_MAXSIZE",
    "HTTP_STATUS_OK",
    "MAX_URL_DECODE_ITERATIONS",
    "MAX_DICT_RECURSION_DEPTH",
    "MAX_UNIQUE_NAME_ATTEMPTS",
    "MAX_PATH_LENGTH_SAFE",
    "FORBIDDEN_PATH_CHARS",
    # Validation constants
    "MAX_CITIES_FILE_SIZE",
    "MAX_CITIES_COUNT",
    "MMAP_CITIES_THRESHOLD",
    # Polling
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    # Env config
    "EnvConfig",
    "get_env_config",
    "validate_env_int",
]
