"""Модуль глобальных констант проекта parser-2gis.

Этот модуль содержит все магические числа и константы используемые в проекте.
Константы вынесены для централизованного управления и упрощения тестирования.

Пример использования:
    >>> from parser_2gis.constants import MAX_DATA_DEPTH, MAX_STRING_LENGTH
    >>> print(f"Максимальная глубина: {MAX_DATA_DEPTH}")
    Максимальная глубина: 15
"""
# pylint: disable=undefined-all-variable,import-error,no-name-in-module

from __future__ import annotations

import threading
from typing import NamedTuple

# Реэкспорты из подмодулей пакета constants для обратной совместимости.
# Все эти имена также доступны через parser_2gis.constants.<submodule>
# Buffer constants
from parser_2gis.constants.buffer import (
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

# Cache constants
from parser_2gis.constants.cache import (
    CONNECTION_MAX_AGE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CACHE_FILE_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TTL_HOURS,
    LRU_EVICT_BATCH,
    MAX_BATCH_SIZE,
    MAX_CACHE_SIZE_MB,
    MAX_POOL_SIZE,
    MIN_POOL_SIZE,
    SHA256_HASH_LENGTH,
)

# Env config
from parser_2gis.constants.env_config import (
    EnvConfig,
    EnvConfigManager,
    get_env_config,
    get_env_config_manager,
    invalidate_env_config,
    validate_env_int,
)

# Parser constants
from parser_2gis.constants.parser import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SLEEP_TIME,
    DEFAULT_TIMEOUT,
    EXPONENTIAL_BACKOFF_MULTIPLIER,
    GC_MEMORY_THRESHOLD_MB,
    MAX_LOCK_FILE_AGE,
    MAX_POLL_INTERVAL,
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

# Security constants
from parser_2gis.constants.security import (
    CHROME_STARTUP_DELAY,
    EXTERNAL_RATE_LIMIT_CALLS,
    EXTERNAL_RATE_LIMIT_PERIOD,
    FORBIDDEN_PATH_CHARS,
    HTTP_CACHE_MAXSIZE,
    HTTP_CACHE_TTL_SECONDS,
    HTTP_STATUS_OK,
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

# Validation constants
from parser_2gis.constants.validation import (
    MAX_CITIES_COUNT,
    MAX_CITIES_FILE_SIZE,
    MMAP_CITIES_THRESHOLD,
)

# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

type EnvValidationResult = tuple[bool, str | None]


class _EnvValidationEntry(NamedTuple):
    """Запись конфигурации ENV валидации.

    P0-91: Замена tuple[str, int, int | None, int | None, str, str] на именованный кортеж.
    """

    env_name: str
    default: int
    min_value: int | None
    max_value: int | None
    attr_name: str
    log_template: str


# =============================================================================
# THREAD-SAFE LOCK (оставлен для обратной совместимости)
# =============================================================================

# Блокировка для thread-safe инициализации singleton (устарело, оставлено для совместимости)
_env_config_lock = threading.Lock()


# =============================================================================
# УСТАРЕВШИЕ ФУНКЦИИ (обёртки для обратной совместимости)
# =============================================================================


def _reset_constant_cache() -> None:
    """Сбрасывает кэш lru_cache для констант.

    #150: Функция для инвалидации кэша при изменении ENV переменных.
    Необходима для тестирования и динамического изменения конфигурации.

    Example:
        >>> from parser_2gis.constants import _reset_constant_cache
        >>> import os
        >>> os.environ['PARSER_MAX_WORKERS'] = '10'
        >>> _reset_constant_cache()  # Сбросить кэш

    """
    invalidate_env_config()


# =============================================================================
# ЭКСПОРТИРУЕМЫЕ СИМВОЛЫ
# =============================================================================

__all__: list[str] = [
    # Security
    "CHROME_STARTUP_DELAY",
    # Cache
    "CONNECTION_MAX_AGE",
    # Buffer
    "CSV_BATCH_SIZE",
    "CSV_COLUMNS_PER_ENTITY",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_BUFFER_SIZE",
    "DEFAULT_CACHE_FILE_NAME",
    "DEFAULT_OUTPUT_DIR",
    # Parser
    "DEFAULT_POLL_INTERVAL",
    "DEFAULT_SLEEP_TIME",
    "DEFAULT_TIMEOUT",
    "DEFAULT_TTL_HOURS",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    "EXTERNAL_RATE_LIMIT_CALLS",
    "EXTERNAL_RATE_LIMIT_PERIOD",
    "FORBIDDEN_PATH_CHARS",
    "GC_MEMORY_THRESHOLD_MB",
    "HTTP_CACHE_MAXSIZE",
    "HTTP_CACHE_TTL_SECONDS",
    "HTTP_STATUS_OK",
    "LARGE_FILE_BUFFER_MULTIPLIER",
    "LARGE_FILE_THRESHOLD_MB",
    "LRU_EVICT_BATCH",
    "MAX_BATCH_SIZE",
    "MAX_BUFFER_SIZE",
    "MAX_CACHE_SIZE_MB",
    # Validation
    "MAX_CITIES_COUNT",
    "MAX_CITIES_FILE_SIZE",
    "MAX_COLLECTION_SIZE",
    "MAX_DATA_DEPTH",
    "MAX_DATA_SIZE",
    "MAX_DICT_RECURSION_DEPTH",
    "MAX_INITIAL_STATE_DEPTH",
    "MAX_INITIAL_STATE_SIZE",
    "MAX_ITEMS_IN_COLLECTION",
    "MAX_JS_CODE_LENGTH",
    "MAX_LOCK_FILE_AGE",
    "MAX_PATH_LENGTH",
    "MAX_PATH_LENGTH_SAFE",
    "MAX_POLL_INTERVAL",
    "MAX_POOL_SIZE",
    "MAX_RECORDS_BASE_OFFSET",
    "MAX_RECORDS_MEMORY_COEFFICIENT",
    "MAX_RECORDS_MEMORY_DIVISOR",
    "MAX_RESPONSE_SIZE",
    "MAX_STRING_LENGTH",
    "MAX_TEMP_FILES",
    "MAX_TEMP_FILES_MONITORING",
    "MAX_TIMEOUT",
    "MAX_TOTAL_JS_SIZE",
    "MAX_UNIQUE_NAME_ATTEMPTS",
    "MAX_URL_DECODE_ITERATIONS",
    "MAX_VISITED_LINKS_SIZE",
    "MAX_WORKERS",
    "MERGE_BATCH_SIZE",
    "MERGE_BUFFER_SIZE",
    "MERGE_LOCK_TIMEOUT",
    "MIN_POOL_SIZE",
    "MIN_TIMEOUT",
    "MIN_WORKERS",
    "MMAP_CITIES_THRESHOLD",
    "MMAP_THRESHOLD_BYTES",
    "ORPHANED_TEMP_FILE_AGE",
    "PROGRESS_UPDATE_INTERVAL",
    "SHA256_HASH_LENGTH",
    "TEMP_FILE_CLEANUP_INTERVAL",
    # Env config
    "EnvConfig",
    "EnvConfigManager",
    # Type aliases and helpers
    "_EnvValidationEntry",
    "EnvValidationResult",
    "_reset_constant_cache",
    "get_env_config",
    "get_env_config_manager",
    "invalidate_env_config",
    "validate_env_int",
]
