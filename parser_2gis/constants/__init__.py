"""Пакет констант для parser-2gis.

Этот пакет содержит специализированные модули с константами:
- buffer: константы буферизации
- cache: константы кэширования
- parser: константы парсера
- security: константы безопасности
- validation: константы валидации

ISSUE-038: Используются ленивые импорты через __getattr__ для предотвращения
 eager загрузки всех подмодулей при импорте пакета constants.

Пример использования:
    >>> from parser_2gis.constants.buffer import DEFAULT_BUFFER_SIZE
    >>> from parser_2gis.constants.cache import MAX_CACHE_SIZE_MB
"""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    """Ленивый импорт констант из подмодулей.

    ISSUE-038: Загружает подмодули только при реальном обращении к константам.
    """
    # Buffer constants
    _buffer_names = {
        "CSV_BATCH_SIZE",
        "CSV_COLUMNS_PER_ENTITY",
        "DEFAULT_BUFFER_SIZE",
        "LARGE_FILE_BUFFER_MULTIPLIER",
        "LARGE_FILE_THRESHOLD_MB",
        "MAX_BUFFER_SIZE",
        "MERGE_BATCH_SIZE",
        "MERGE_BUFFER_SIZE",
        "MMAP_THRESHOLD_BYTES",
    }
    if name in _buffer_names:
        from parser_2gis.constants import buffer as _buffer_mod

        return getattr(_buffer_mod, name)

    # Cache constants
    _cache_names = {
        "CONNECTION_MAX_AGE",
        "DEFAULT_BATCH_SIZE",
        "DEFAULT_CACHE_FILE_NAME",
        "DEFAULT_OUTPUT_DIR",
        "DEFAULT_TTL_HOURS",
        "LRU_EVICT_BATCH",
        "MAX_BATCH_SIZE",
        "MAX_CACHE_SIZE_MB",
        "MAX_POOL_SIZE",
        "MIN_POOL_SIZE",
        "SHA256_HASH_LENGTH",
    }
    if name in _cache_names:
        from parser_2gis.constants import cache as _cache_mod

        return getattr(_cache_mod, name)

    # Env config
    _env_names = {"EnvConfig", "get_env_config", "validate_env_int"}
    if name in _env_names:
        from parser_2gis.constants import env_config as _env_mod

        return getattr(_env_mod, name)

    # Parser constants
    _parser_names = {
        "DEFAULT_POLL_INTERVAL",
        "DEFAULT_SLEEP_TIME",
        "DEFAULT_TIMEOUT",
        "EXPONENTIAL_BACKOFF_MULTIPLIER",
        "GC_MEMORY_THRESHOLD_MB",
        "MAX_LOCK_FILE_AGE",
        "MAX_POLL_INTERVAL",
        "MAX_RECORDS_BASE_OFFSET",
        "MAX_RECORDS_MEMORY_COEFFICIENT",
        "MAX_RECORDS_MEMORY_DIVISOR",
        "MAX_TEMP_FILES",
        "MAX_TEMP_FILES_MONITORING",
        "MAX_TIMEOUT",
        "MAX_VISITED_LINKS_SIZE",
        "MAX_WORKERS",
        "MERGE_LOCK_TIMEOUT",
        "MIN_TIMEOUT",
        "MIN_WORKERS",
        "ORPHANED_TEMP_FILE_AGE",
        "PROGRESS_UPDATE_INTERVAL",
        "TEMP_FILE_CLEANUP_INTERVAL",
    }
    if name in _parser_names:
        from parser_2gis.constants import parser as _parser_mod

        return getattr(_parser_mod, name)

    # Security constants
    _security_names = {
        "CHROME_STARTUP_DELAY",
        "EXTERNAL_RATE_LIMIT_CALLS",
        "EXTERNAL_RATE_LIMIT_PERIOD",
        "FORBIDDEN_PATH_CHARS",
        "HTTP_CACHE_MAXSIZE",
        "HTTP_CACHE_TTL_SECONDS",
        "HTTP_STATUS_OK",
        "MAX_COLLECTION_SIZE",
        "MAX_DATA_DEPTH",
        "MAX_DATA_SIZE",
        "MAX_DICT_RECURSION_DEPTH",
        "MAX_INITIAL_STATE_DEPTH",
        "MAX_INITIAL_STATE_SIZE",
        "MAX_ITEMS_IN_COLLECTION",
        "MAX_JS_CODE_LENGTH",
        "MAX_PATH_LENGTH",
        "MAX_PATH_LENGTH_SAFE",
        "MAX_RESPONSE_SIZE",
        "MAX_STRING_LENGTH",
        "MAX_TOTAL_JS_SIZE",
        "MAX_UNIQUE_NAME_ATTEMPTS",
        "MAX_URL_DECODE_ITERATIONS",
    }
    if name in _security_names:
        from parser_2gis.constants import security as _security_mod

        return getattr(_security_mod, name)

    # Validation constants
    _validation_names = {"MAX_CITIES_COUNT", "MAX_CITIES_FILE_SIZE", "MMAP_CITIES_THRESHOLD"}
    if name in _validation_names:
        from parser_2gis.constants import validation as _validation_mod

        return getattr(_validation_mod, name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    """Возвращает список всех доступных имён для автодополнения."""
    return [
        # Buffer
        "CSV_BATCH_SIZE",
        "CSV_COLUMNS_PER_ENTITY",
        "DEFAULT_BUFFER_SIZE",
        "LARGE_FILE_BUFFER_MULTIPLIER",
        "LARGE_FILE_THRESHOLD_MB",
        "MAX_BUFFER_SIZE",
        "MERGE_BATCH_SIZE",
        "MERGE_BUFFER_SIZE",
        "MMAP_THRESHOLD_BYTES",
        # Cache
        "CONNECTION_MAX_AGE",
        "DEFAULT_BATCH_SIZE",
        "DEFAULT_CACHE_FILE_NAME",
        "DEFAULT_OUTPUT_DIR",
        "DEFAULT_TTL_HOURS",
        "LRU_EVICT_BATCH",
        "MAX_BATCH_SIZE",
        "MAX_CACHE_SIZE_MB",
        "MAX_POOL_SIZE",
        "MIN_POOL_SIZE",
        "SHA256_HASH_LENGTH",
        # Env config
        "EnvConfig",
        "get_env_config",
        "validate_env_int",
        # Parser
        "DEFAULT_POLL_INTERVAL",
        "DEFAULT_SLEEP_TIME",
        "DEFAULT_TIMEOUT",
        "EXPONENTIAL_BACKOFF_MULTIPLIER",
        "GC_MEMORY_THRESHOLD_MB",
        "MAX_LOCK_FILE_AGE",
        "MAX_POLL_INTERVAL",
        "MAX_RECORDS_BASE_OFFSET",
        "MAX_RECORDS_MEMORY_COEFFICIENT",
        "MAX_RECORDS_MEMORY_DIVISOR",
        "MAX_TEMP_FILES",
        "MAX_TEMP_FILES_MONITORING",
        "MAX_TIMEOUT",
        "MAX_VISITED_LINKS_SIZE",
        "MAX_WORKERS",
        "MERGE_LOCK_TIMEOUT",
        "MIN_TIMEOUT",
        "MIN_WORKERS",
        "ORPHANED_TEMP_FILE_AGE",
        "PROGRESS_UPDATE_INTERVAL",
        "TEMP_FILE_CLEANUP_INTERVAL",
        # Security
        "CHROME_STARTUP_DELAY",
        "EXTERNAL_RATE_LIMIT_CALLS",
        "EXTERNAL_RATE_LIMIT_PERIOD",
        "FORBIDDEN_PATH_CHARS",
        "HTTP_CACHE_MAXSIZE",
        "HTTP_CACHE_TTL_SECONDS",
        "HTTP_STATUS_OK",
        "MAX_COLLECTION_SIZE",
        "MAX_DATA_DEPTH",
        "MAX_DATA_SIZE",
        "MAX_DICT_RECURSION_DEPTH",
        "MAX_INITIAL_STATE_DEPTH",
        "MAX_INITIAL_STATE_SIZE",
        "MAX_ITEMS_IN_COLLECTION",
        "MAX_JS_CODE_LENGTH",
        "MAX_PATH_LENGTH",
        "MAX_PATH_LENGTH_SAFE",
        "MAX_RESPONSE_SIZE",
        "MAX_STRING_LENGTH",
        "MAX_TOTAL_JS_SIZE",
        "MAX_UNIQUE_NAME_ATTEMPTS",
        "MAX_URL_DECODE_ITERATIONS",
        # Validation
        "MAX_CITIES_COUNT",
        "MAX_CITIES_FILE_SIZE",
        "MMAP_CITIES_THRESHOLD",
        # Functions
        "_reset_constant_cache",
    ]


def _reset_constant_cache() -> None:
    """Сбрасывает кэш lru_cache для констант.

    #150: Функция для инвалидации кэша при изменении ENV переменных.
    """
    from parser_2gis.constants import get_env_config

    if hasattr(get_env_config, "_instance"):
        delattr(get_env_config, "_instance")
