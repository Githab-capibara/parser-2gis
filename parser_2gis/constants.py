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

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache

from typing import TypeAlias

# Импорты констант из подмодулей для обратной совместимости
from .parser import (
    DEFAULT_SLEEP_TIME,
    MAX_RECORDS_BASE_OFFSET,
    MAX_RECORDS_MEMORY_COEFFICIENT,
    MAX_RECORDS_MEMORY_DIVISOR,
    MAX_VISITED_LINKS_SIZE,
    PROGRESS_UPDATE_INTERVAL,
)
from .security import (
    FORBIDDEN_PATH_CHARS,
    HTTP_STATUS_OK,
    MAX_DICT_RECURSION_DEPTH,
    MAX_PATH_LENGTH_SAFE,
    MAX_UNIQUE_NAME_ATTEMPTS,
    MAX_URL_DECODE_ITERATIONS,
)

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

EnvValidationResult: TypeAlias = tuple[bool, str | None]

# =============================================================================
# DATACLASS ДЛЯ ВАЛИДАЦИИ ENV ПЕРЕМЕННЫХ
# =============================================================================


@dataclass
class EnvConfig:
    """Конфигурация ENV переменных с валидацией.

    Централизованная валидация ENV переменных для устранения дублирования кода.
    Использует валидаторы полей для проверки диапазонов значений.

    Attributes:
        max_workers: Максимальное количество рабочих потоков.
        max_timeout: Максимальный таймаут в секундах.
        default_timeout: Таймаут по умолчанию в секундах.
        max_pool_size: Максимальный размер пула соединений.
        min_pool_size: Минимальный размер пула соединений.
        max_cache_size_mb: Максимальный размер кэша в MB.
        max_temp_files: Максимальное количество временных файлов.
        temp_file_cleanup_interval: Интервал очистки временных файлов в секундах.

    Example:
        >>> config = EnvConfig()
        >>> print(config.max_workers)  # 50 (или значение из PARSER_MAX_WORKERS)

    """

    # Поля инициализируются в __post_init__
    _logger: logging.Logger = field(init=False, repr=False)

    def _validate_env_int(
        self,
        env_name: str,
        default: int,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        """Валидирует ENV переменную как целое число в допустимом диапазоне.

        Args:
            env_name: Имя ENV переменной.
            default: Значение по умолчанию.
            min_value: Минимальное допустимое значение.
            max_value: Максимальное допустимое значение.

        Returns:
            Валидированное целое число.

        """
        value_str = os.getenv(env_name)

        if value_str is None:
            return default

        try:
            value = int(value_str)
        except ValueError as e:
            self._logger.error(
                "ENV переменная %s=%s не является целым числом: %s", env_name, value_str, e
            )
            return default

        if min_value is not None and value < min_value:
            self._logger.warning(
                "ENV переменная %s=%d меньше минимального значения %d. Используется %d",
                env_name,
                value,
                min_value,
                min_value,
            )
            return min_value

        if max_value is not None and value > max_value:
            self._logger.warning(
                "ENV переменная %s=%d больше максимального значения %d. Используется %d",
                env_name,
                value,
                max_value,
                max_value,
            )
            return max_value

        return value

    # Параллельный парсинг
    max_workers: int = field(init=False)
    max_timeout: int = field(init=False)
    default_timeout: int = field(init=False)
    min_workers: int = field(init=False)
    min_timeout: int = field(init=False)

    # Connection Pool
    max_pool_size: int = field(init=False)
    min_pool_size: int = field(init=False)
    connection_max_age: int = field(init=False)
    max_connection_age: int = field(init=False)

    # Кэширование
    max_cache_size_mb: int = field(init=False)

    # Временные файлы
    max_temp_files: int = field(init=False)
    max_temp_files_monitoring: int = field(init=False)
    temp_file_cleanup_interval: int = field(init=False)
    orphaned_temp_file_age: int = field(init=False)

    # Merge операции
    merge_lock_timeout: int = field(init=False)
    max_lock_file_age: int = field(init=False)

    def __post_init__(self) -> None:
        """Инициализация полей после создания объекта."""
        # Инициализация logger
        object.__setattr__(self, "_logger", logging.getLogger("parser_2gis.constants.env_config"))

        # Инициализация полей со значениями по умолчанию
        object.__setattr__(self, "min_workers", 1)
        object.__setattr__(self, "min_timeout", 1)
        object.__setattr__(self, "max_temp_files", 1000)

        # ISSUE-012: Логирование используемых ENV переменных при инициализации
        self._logger.info("Инициализация конфигурации ENV переменных")

        # Параллельный парсинг
        max_workers_val = self._validate_env_int("PARSER_MAX_WORKERS", 50, 1, 100)
        object.__setattr__(self, "max_workers", max_workers_val)
        self._logger.info("PARSER_MAX_WORKERS: %d (по умолчанию: 50)", max_workers_val)

        max_timeout_val = self._validate_env_int("PARSER_MAX_TIMEOUT", 72000, 60, 172800)
        object.__setattr__(self, "max_timeout", max_timeout_val)
        self._logger.info("PARSER_MAX_TIMEOUT: %d сек (по умолчанию: 72000)", max_timeout_val)

        default_timeout_val = self._validate_env_int("PARSER_DEFAULT_TIMEOUT", 7200, 60, 72000)
        object.__setattr__(self, "default_timeout", default_timeout_val)
        self._logger.info(
            "PARSER_DEFAULT_TIMEOUT: %d сек (по умолчанию: 7200)", default_timeout_val
        )

        # Connection Pool
        max_pool_size_val = self._validate_env_int("PARSER_MAX_POOL_SIZE", 20, 5, 50)
        object.__setattr__(self, "max_pool_size", max_pool_size_val)
        self._logger.info("PARSER_MAX_POOL_SIZE: %d (по умолчанию: 20)", max_pool_size_val)

        min_pool_size_val = self._validate_env_int("PARSER_MIN_POOL_SIZE", 5, 1, 10)
        object.__setattr__(self, "min_pool_size", min_pool_size_val)
        self._logger.info("PARSER_MIN_POOL_SIZE: %d (по умолчанию: 5)", min_pool_size_val)

        connection_max_age_val = self._validate_env_int("PARSER_CONNECTION_MAX_AGE", 600, 60, 7200)
        object.__setattr__(self, "connection_max_age", connection_max_age_val)
        self._logger.info(
            "PARSER_CONNECTION_MAX_AGE: %d сек (по умолчанию: 600)", connection_max_age_val
        )

        max_connection_age_val = self._validate_env_int("PARSER_MAX_CONNECTION_AGE", 600, 60, 7200)
        object.__setattr__(self, "max_connection_age", max_connection_age_val)
        self._logger.info(
            "PARSER_MAX_CONNECTION_AGE: %d сек (по умолчанию: 600)", max_connection_age_val
        )

        # Кэширование
        max_cache_size_mb_val = self._validate_env_int("PARSER_MAX_CACHE_SIZE_MB", 500, 100, 2000)
        object.__setattr__(self, "max_cache_size_mb", max_cache_size_mb_val)
        self._logger.info(
            "PARSER_MAX_CACHE_SIZE_MB: %d MB (по умолчанию: 500)", max_cache_size_mb_val
        )

        # Временные файлы
        max_temp_files_monitoring_val = self._validate_env_int(
            "PARSER_MAX_TEMP_FILES_MONITORING", 1000, 100, 10000
        )
        object.__setattr__(self, "max_temp_files_monitoring", max_temp_files_monitoring_val)
        self._logger.info(
            "PARSER_MAX_TEMP_FILES_MONITORING: %d (по умолчанию: 1000)",
            max_temp_files_monitoring_val,
        )

        temp_file_cleanup_interval_val = self._validate_env_int(
            "PARSER_TEMP_FILE_CLEANUP_INTERVAL", 120, 10, 7200
        )
        object.__setattr__(self, "temp_file_cleanup_interval", temp_file_cleanup_interval_val)
        self._logger.info(
            "PARSER_TEMP_FILE_CLEANUP_INTERVAL: %d сек (по умолчанию: 120)",
            temp_file_cleanup_interval_val,
        )

        orphaned_temp_file_age_val = self._validate_env_int(
            "PARSER_ORPHANED_TEMP_FILE_AGE", 600, 60, 172800
        )
        object.__setattr__(self, "orphaned_temp_file_age", orphaned_temp_file_age_val)
        self._logger.info(
            "PARSER_ORPHANED_TEMP_FILE_AGE: %d сек (по умолчанию: 600)", orphaned_temp_file_age_val
        )

        # Merge операции
        merge_lock_timeout_val = self._validate_env_int(
            "PARSER_MERGE_LOCK_TIMEOUT", 7200, 60, 14400
        )
        object.__setattr__(self, "merge_lock_timeout", merge_lock_timeout_val)
        self._logger.info(
            "PARSER_MERGE_LOCK_TIMEOUT: %d сек (по умолчанию: 7200)", merge_lock_timeout_val
        )

        max_lock_file_age_val = self._validate_env_int("PARSER_MAX_LOCK_FILE_AGE", 120, 10, 1200)
        object.__setattr__(self, "max_lock_file_age", max_lock_file_age_val)
        self._logger.info(
            "PARSER_MAX_LOCK_FILE_AGE: %d сек (по умолчанию: 120)", max_lock_file_age_val
        )


# =============================================================================
# LAZY ИНИЦИАЛИЗАЦИЯ ENV CONFIG (SINGLETON PATTERN БЕЗ ГЛОБАЛЬНОГО СОСТОЯНИЯ)
# =============================================================================
# ISSUE-010: Устранено глобальное состояние _env_config_instance
# Используем замыкание для хранения singleton экземпляра


def get_env_config() -> EnvConfig:
    """Получает singleton экземпляр EnvConfig с lazy инициализацией.

    EnvConfig создаётся только при первом вызове функции, а не при импорте модуля.
    Это предотвращает лишние вычисления при импорте и ускоряет запуск модуля.

    ISSUE-010: Устранено глобальное состояние через использование замыкания.

    Returns:
        Singleton экземпляр EnvConfig.

    Example:
        >>> config = get_env_config()
        >>> print(config.max_workers)  # 50 (или значение из PARSER_MAX_WORKERS)

    """
    # ISSUE-010: Singleton через замыкание вместо глобальной переменной
    # Переменная _instance видна только внутри функции, не загрязняя глобальное пространство
    if not hasattr(get_env_config, "_instance"):
        get_env_config._instance = EnvConfig()  # type: ignore[attr-defined]  # pylint: disable=protected-access
    return get_env_config._instance  # type: ignore[attr-defined]  # pylint: disable=protected-access


# Для обратной совместимости используем __getattr__ для ленивой инициализации
# ISSUE-010: Кэширование результатов __getattr__ через lru_cache для оптимизации

# P0-12: Словарь маппинга ENV-зависимых констант для устранения длинной цепи if
_ENV_CONSTANTS_MAPPING: dict[str, str] = {
    # Connection pool
    "MAX_CONNECTION_AGE": "max_connection_age",
    "MAX_CACHE_SIZE_MB": "max_cache_size_mb",
    "MAX_POOL_SIZE": "max_pool_size",
    "MIN_POOL_SIZE": "min_pool_size",
    "CONNECTION_MAX_AGE": "connection_max_age",
    # Параллельный парсинг
    "MIN_WORKERS": "min_workers",
    "MAX_WORKERS": "max_workers",
    "MIN_TIMEOUT": "min_timeout",
    "MAX_TIMEOUT": "max_timeout",
    "DEFAULT_TIMEOUT": "default_timeout",
    "TEMP_FILE_CLEANUP_INTERVAL": "temp_file_cleanup_interval",
    "MAX_TEMP_FILES_MONITORING": "max_temp_files_monitoring",
    "ORPHANED_TEMP_FILE_AGE": "orphaned_temp_file_age",
    "MERGE_LOCK_TIMEOUT": "merge_lock_timeout",
    "MAX_LOCK_FILE_AGE": "max_lock_file_age",
}

# P0-12: Словарь маппинга статических констант для устранения длинной цепи if
_STATIC_CONSTANTS_MAPPING: dict[str, int | float | list[str]] = {
    # Безопасность данных
    "MAX_DATA_DEPTH": 100,
    "MAX_STRING_LENGTH": 10000,
    "MAX_DATA_SIZE": 10 * 1024 * 1024,
    "MAX_COLLECTION_SIZE": 100000,
    "MAX_PATH_LENGTH": 4096,
    # Безопасность initialState
    "MAX_INITIAL_STATE_DEPTH": 10,
    "MAX_INITIAL_STATE_SIZE": 5 * 1024 * 1024,
    "MAX_ITEMS_IN_COLLECTION": 10000,
    # Кэширование
    "DEFAULT_BATCH_SIZE": 100,
    "MAX_BATCH_SIZE": 1000,
    "LRU_EVICT_BATCH": 100,
    "SHA256_HASH_LENGTH": 64,
    "EXTRACTOR_CACHE_MAX_SIZE": 2048,
    "CACHE_EVICTION_PERCENT": 10,
    # Параллельный парсинг
    "MAX_TEMP_FILES": 1000,
    # Буферизация
    "DEFAULT_BUFFER_SIZE": 524288,
    "MERGE_BUFFER_SIZE": 131072,
    "CSV_BATCH_SIZE": 1000,
    "CSV_COLUMNS_PER_ENTITY": 5,
    "MERGE_BATCH_SIZE": 500,
    "LARGE_FILE_THRESHOLD_MB": 100,
    "LARGE_FILE_BUFFER_MULTIPLIER": 4,
    "MAX_BUFFER_SIZE": 1048576,
    "MMAP_THRESHOLD_BYTES": 10 * 1024 * 1024,
    # Валидация городов
    "MAX_CITIES_FILE_SIZE": 10 * 1024 * 1024,
    "MAX_CITIES_COUNT": 1000,
    "MMAP_CITIES_THRESHOLD": 1 * 1024 * 1024,
    # JS безопасность
    "MAX_JS_CODE_LENGTH": 100000,
    "MAX_RESPONSE_SIZE": 10 * 1024 * 1024,
    "MAX_TOTAL_JS_SIZE": 5 * 1024 * 1024,
    "CHROME_STARTUP_DELAY": 5.0,
    # Rate limiting
    "EXTERNAL_RATE_LIMIT_CALLS": 10,
    "EXTERNAL_RATE_LIMIT_PERIOD": 60,
    # HTTP кэширование
    "HTTP_CACHE_TTL_SECONDS": 300,
    "HTTP_CACHE_MAXSIZE": 1024,
    # Polling
    "DEFAULT_POLL_INTERVAL": 0.1,
    "MAX_POLL_INTERVAL": 2.0,
    "EXPONENTIAL_BACKOFF_MULTIPLIER": 2,
    # HTTP статус коды
    "HTTP_STATUS_OK": 200,
    # Безопасность путей
    "MAX_URL_DECODE_ITERATIONS": 5,
    "MAX_DICT_RECURSION_DEPTH": 10,
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL": 3,
    # Уникальные имена файлов
    "MAX_UNIQUE_NAME_ATTEMPTS": 10,
    # Таймауты и задержки
    "DEFAULT_SLEEP_TIME": 0.1,
    # Парсер - лимиты
    "MAX_VISITED_LINKS_SIZE": 10000,
    "MAX_RECORDS_MEMORY_COEFFICIENT": 550,
    "MAX_RECORDS_MEMORY_DIVISOR": 1024,
    "MAX_RECORDS_BASE_OFFSET": 400,
    # Порог памяти для GC
    "GC_MEMORY_THRESHOLD_MB": 100,
    # Безопасность путей
    "MAX_PATH_LENGTH_SAFE": 4096,
    "FORBIDDEN_PATH_CHARS": ["..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"],
}


@lru_cache(maxsize=128)
def _get_constant_value(name: str) -> int | float | list[str] | EnvConfig:
    """Получает значение константы с кэшированием через lru_cache.

    ISSUE-010: Кэширование результатов для устранения повторных вычислений.
    Все константы кэшируются после первого обращения.
    P0-12: Использует словарь-маппинг вместо длинной цепи if-проверок.

    Args:
        name: Имя константы.

    Returns:
        Значение константы.

    """
    # Специальный случай для env_config
    if name == "env_config":
        return get_env_config()

    # P0-12: Проверка ENV-зависимых констант через словарь
    env_attr = _ENV_CONSTANTS_MAPPING.get(name)
    if env_attr is not None:
        config = get_env_config()
        return getattr(config, env_attr)

    # P0-12: Проверка статических констант через словарь
    if name in _STATIC_CONSTANTS_MAPPING:
        return _STATIC_CONSTANTS_MAPPING[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __getattr__(name: str) -> int | float | list[str] | EnvConfig:
    """Ленивая инициализация констант для устранения global singleton (A034).

    ISSUE-010: Устранено глобальное состояние _env_config_instance.
    Константы, зависящие от ENV переменных, создаются только при первом обращении.
    Это предотвращает инициализацию global state при импорте модуля.

    ISSUE-010: Результаты кэшируются через _get_constant_value с lru_cache.
    """
    return _get_constant_value(name)


# =============================================================================
# ФУНКЦИЯ ВАЛИДАЦИИ ENV ПЕРЕМЕННЫХ (для экспорта)
# =============================================================================


def validate_env_int(
    env_name: str, default: int, min_value: int | None = None, max_value: int | None = None
) -> int:
    """Валидирует ENV переменную как целое число в допустимом диапазоне.

    Функция-обёртка для EnvConfig._validate_env_int для использования
    на уровне модуля.

    Args:
        env_name: Имя ENV переменной.
        default: Значение по умолчанию.
        min_value: Минимальное допустимое значение.
        max_value: Максимальное допустимое значение.

    Returns:
        Валидированное целое число.

    """
    return get_env_config()._validate_env_int(env_name, default, min_value, max_value)  # pylint: disable=protected-access


# =============================================================================
# КОНСТАНТЫ (LAZY INIT ЧЕРЕЗ __getattr__)
# =============================================================================
# Все константы теперь инициализируются лениво через __getattr__ при первом обращении.
# Это устраняет global singleton состояние при импорте модуля (A034).
#
# Экспортируемые символы перечислены в __all__ в конце файла.
#
# Для получения константы используйте:
#   from parser_2gis.constants import MAX_WORKERS
# или
#   from parser_2gis import constants
#   value = constants.MAX_WORKERS
# =============================================================================

# =============================================================================
# ЭКСПОРТИРУЕМЫЕ СИМВОЛЫ
# =============================================================================

# noqa: F822 - Константы определяются через __getattr__ для lazy инициализации (A034)
__all__: list[str] = [  # noqa: F822
    # Конфигурация ENV
    "EnvConfig",
    "get_env_config",
    "validate_env_int",
    # Безопасность данных
    "MAX_DATA_DEPTH",
    "MAX_STRING_LENGTH",
    "MAX_DATA_SIZE",
    "MAX_COLLECTION_SIZE",
    "MAX_PATH_LENGTH",
    # Безопасность initialState (firm_parser.py)
    "MAX_INITIAL_STATE_DEPTH",
    "MAX_INITIAL_STATE_SIZE",
    "MAX_ITEMS_IN_COLLECTION",
    # Кэширование
    "DEFAULT_BATCH_SIZE",
    "MAX_CONNECTION_AGE",
    "MAX_BATCH_SIZE",
    "MAX_CACHE_SIZE_MB",
    "LRU_EVICT_BATCH",
    "SHA256_HASH_LENGTH",
    # Connection Pool
    "MAX_POOL_SIZE",
    "MIN_POOL_SIZE",
    "CONNECTION_MAX_AGE",
    # Параллельный парсинг
    "MIN_WORKERS",
    "MAX_WORKERS",
    "MIN_TIMEOUT",
    "MAX_TIMEOUT",
    "DEFAULT_TIMEOUT",
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
    "MAX_TEMP_FILES",
    "MERGE_LOCK_TIMEOUT",
    "MAX_LOCK_FILE_AGE",
    # Буферизация
    "DEFAULT_BUFFER_SIZE",
    "MERGE_BUFFER_SIZE",
    "CSV_BATCH_SIZE",
    "CSV_COLUMNS_PER_ENTITY",
    "MERGE_BATCH_SIZE",
    # Валидация городов
    "MAX_CITIES_FILE_SIZE",
    "MAX_CITIES_COUNT",
    "MMAP_CITIES_THRESHOLD",
    # JS безопасность
    "MAX_JS_CODE_LENGTH",
    "MAX_RESPONSE_SIZE",
    "MAX_TOTAL_JS_SIZE",
    "CHROME_STARTUP_DELAY",
    # Rate limiting
    "EXTERNAL_RATE_LIMIT_CALLS",
    "EXTERNAL_RATE_LIMIT_PERIOD",
    # HTTP кэширование
    "HTTP_CACHE_TTL_SECONDS",
    "HTTP_CACHE_MAXSIZE",
    # Polling
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    # HTTP статус коды
    "HTTP_STATUS_OK",
    # Безопасность путей
    "MAX_URL_DECODE_ITERATIONS",
    "MAX_DICT_RECURSION_DEPTH",
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL",
    # Уникальные имена файлов
    "MAX_UNIQUE_NAME_ATTEMPTS",
    # Таймауты и задержки
    "DEFAULT_SLEEP_TIME",
    # Парсер - лимиты
    "MAX_VISITED_LINKS_SIZE",
    "MAX_RECORDS_MEMORY_COEFFICIENT",
    "MAX_RECORDS_MEMORY_DIVISOR",
    "MAX_RECORDS_BASE_OFFSET",
    # Безопасность путей
    "MAX_PATH_LENGTH_SAFE",
    "FORBIDDEN_PATH_CHARS",
]
