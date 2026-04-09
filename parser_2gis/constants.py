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
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import NamedTuple, cast

# Импорты констант из подмодулей для обратной совместимости
# NOTE: Циклический импорт: constants -> parser -> parser.options -> utils -> constants
# Данный импорт необходим для обратной совместимости, но создаёт цикл зависимостей.
# constants.py импортирует из .parser, а .parser.options импортирует из constants.
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
# КОНСТАНТЫ ДЛЯ PARSE_MAX_WORKERS (DEFAULT/MIN/MAX)
# =============================================================================

DEFAULT_MAX_WORKERS: int = 50
"""Значение по умолчанию для максимального количества рабочих потоков."""

MIN_MAX_WORKERS: int = 1
"""Минимальное допустимое значение для максимального количества рабочих потоков."""

MAX_MAX_WORKERS: int = 100
"""Максимальное допустимое значение для максимального количества рабочих потоков."""

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

type EnvValidationResult = tuple[bool, str | None]


class EnvValidationEntry(NamedTuple):
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

    def validate_env_int(
        self,
        env_name: str,
        default: int,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        """Публичная обёртка для валидации ENV переменной как целого числа.

        Делегирует _validate_env_int для использования вне класса.

        Args:
            env_name: Имя ENV переменной.
            default: Значение по умолчанию.
            min_value: Минимальное допустимое значение.
            max_value: Максимальное допустимое значение.

        Returns:
            Валидированное целое число.

        """
        return self._validate_env_int(env_name, default, min_value, max_value)

    # Параллельный парсинг
    max_workers: int = field(init=False)
    max_timeout: int = field(init=False)
    default_timeout: int = field(init=False)
    min_workers: int = field(init=False)
    min_timeout: int = field(init=False)

    # Connection Pool
    max_pool_size: int = field(init=False)
    min_pool_size: int = field(init=False)
    # #74: max_connection_age удалён как дубликат connection_max_age
    connection_max_age: int = field(init=False)

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
        """Инициализация полей после создания объекта.

        Note:
            Используется object.__setattr__() вместо прямого присваивания,
            так как dataclass может быть frozen (frozen=True), что запрещает
            обычное присваивание атрибутов после инициализации.
        """
        # Инициализация logger
        object.__setattr__(self, "_logger", logging.getLogger("parser_2gis.constants.env_config"))

        # Инициализация полей со значениями по умолчанию
        object.__setattr__(self, "min_workers", 1)
        object.__setattr__(self, "min_timeout", 1)
        object.__setattr__(self, "max_temp_files", 1000)

        # ISSUE-012: Логирование используемых ENV переменных при инициализации
        self._logger.info("Инициализация конфигурации ENV переменных")

        # P0-10: Маппинг ENV переменных для устранения дублирования кода
        # Формат: EnvValidationEntry(env_name, default, min_value, max_value, attr_name, log_template)
        env_validations: list[EnvValidationEntry] = [
            # Параллельный парсинг
            EnvValidationEntry(
                "PARSER_MAX_WORKERS",
                DEFAULT_MAX_WORKERS,
                MIN_MAX_WORKERS,
                MAX_MAX_WORKERS,
                "max_workers",
                "PARSER_MAX_WORKERS: %d (по умолчанию: 50)",
            ),
            EnvValidationEntry(
                "PARSER_MAX_TIMEOUT",
                72000,
                60,
                172800,
                "max_timeout",
                "PARSER_MAX_TIMEOUT: %d сек (по умолчанию: 72000)",
            ),
            EnvValidationEntry(
                "PARSER_DEFAULT_TIMEOUT",
                7200,
                60,
                72000,
                "default_timeout",
                "PARSER_DEFAULT_TIMEOUT: %d сек (по умолчанию: 7200)",
            ),
            # Connection Pool
            EnvValidationEntry(
                "PARSER_MAX_POOL_SIZE",
                20,
                5,
                50,
                "max_pool_size",
                "PARSER_MAX_POOL_SIZE: %d (по умолчанию: 20)",
            ),
            EnvValidationEntry(
                "PARSER_MIN_POOL_SIZE",
                5,
                1,
                10,
                "min_pool_size",
                "PARSER_MIN_POOL_SIZE: %d (по умолчанию: 5)",
            ),
            EnvValidationEntry(
                "PARSER_CONNECTION_MAX_AGE",
                600,
                60,
                7200,
                "connection_max_age",
                "PARSER_CONNECTION_MAX_AGE: %d сек (по умолчанию: 600)",
            ),
            # #74: PARSER_MAX_CONNECTION_AGE удалён как дубликат PARSER_CONNECTION_MAX_AGE
            # Кэширование
            EnvValidationEntry(
                "PARSER_MAX_CACHE_SIZE_MB",
                500,
                100,
                2000,
                "max_cache_size_mb",
                "PARSER_MAX_CACHE_SIZE_MB: %d MB (по умолчанию: 500)",
            ),
            # Временные файлы
            EnvValidationEntry(
                "PARSER_MAX_TEMP_FILES_MONITORING",
                1000,
                100,
                10000,
                "max_temp_files_monitoring",
                "PARSER_MAX_TEMP_FILES_MONITORING: %d (по умолчанию: 1000)",
            ),
            EnvValidationEntry(
                "PARSER_TEMP_FILE_CLEANUP_INTERVAL",
                120,
                10,
                7200,
                "temp_file_cleanup_interval",
                "PARSER_TEMP_FILE_CLEANUP_INTERVAL: %d сек (по умолчанию: 120)",
            ),
            EnvValidationEntry(
                "PARSER_ORPHANED_TEMP_FILE_AGE",
                600,
                60,
                172800,
                "orphaned_temp_file_age",
                "PARSER_ORPHANED_TEMP_FILE_AGE: %d сек (по умолчанию: 600)",
            ),
            # Merge операции
            EnvValidationEntry(
                "PARSER_MERGE_LOCK_TIMEOUT",
                7200,
                60,
                14400,
                "merge_lock_timeout",
                "PARSER_MERGE_LOCK_TIMEOUT: %d сек (по умолчанию: 7200)",
            ),
            EnvValidationEntry(
                "PARSER_MAX_LOCK_FILE_AGE",
                120,
                10,
                1200,
                "max_lock_file_age",
                "PARSER_MAX_LOCK_FILE_AGE: %d сек (по умолчанию: 120)",
            ),
        ]

        for entry in env_validations:
            value = self._validate_env_int(
                entry.env_name, entry.default, entry.min_value, entry.max_value
            )
            object.__setattr__(self, entry.attr_name, value)
            self._logger.info(entry.log_template, value)


# =============================================================================
# LAZY ИНИЦИАЛИЗАЦИЯ ENV CONFIG (SINGLETON PATTERN С THREADING.LOCK)
# =============================================================================
# ISSUE-010: Устранено глобальное состояние _env_config_instance
# Используем threading.Lock для thread-safe ленивой инициализации

# Блокировка для thread-safe инициализации singleton
_env_config_lock = threading.Lock()


def get_env_config() -> EnvConfig:
    """Получает singleton экземпляр EnvConfig с lazy инициализацией.

    EnvConfig создаётся только при первом вызове функции, а не при импорте модуля.
    Это предотвращает лишние вычисления при импорте и ускоряет запуск модуля.

    ISSUE-010: Устранено глобальное состояние через threading.Lock based singleton.

    Returns:
        Singleton экземпляр EnvConfig.

    Example:
        >>> config = get_env_config()
        >>> print(config.max_workers)  # 50 (или значение из PARSER_MAX_WORKERS)

    """
    if not hasattr(get_env_config, "_instance"):
        with _env_config_lock:
            if not hasattr(get_env_config, "_instance"):
                object.__setattr__(get_env_config, "_instance", EnvConfig())
    return cast(EnvConfig, get_env_config._instance)


# Для обратной совместимости используем __getattr__ для ленивой инициализации
# ISSUE-010: Кэширование результатов __getattr__ через lru_cache для оптимизации

# P0-12: Словарь маппинга ENV-зависимых констант для устранения длинной цепи if
_ENV_CONSTANTS_MAPPING: dict[str, str] = {
    # Connection pool
    # #74: MAX_CONNECTION_AGE удалён как дубликат CONNECTION_MAX_AGE
    "MAX_CACHE_SIZE_MB": "max_cache_size_mb",
    "MAX_POOL_SIZE": "max_pool_size",
    "MIN_POOL_SIZE": "min_pool_size",
    "CONNECTION_MAX_AGE": "connection_max_age",
    # #74: MAX_CONNECTION_AGE удалён как дубликат CONNECTION_MAX_AGE
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

    Raises:
        AttributeError: Если константа с указанным именем не найдена.

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


def _reset_constant_cache() -> None:
    """Сбрасывает кэш lru_cache для _get_constant_value.

    #150: Функция для инвалидации кэша при изменении ENV переменных.
    Необходима для тестирования и динамического изменения конфигурации.

    Example:
        >>> from parser_2gis.constants import _reset_constant_cache, MAX_WORKERS
        >>> os.environ['PARSER_MAX_WORKERS'] = '10'
        >>> _reset_constant_cache()  # Сбросить кэш
        >>> assert MAX_WORKERS == 10  # Теперь вернёт новое значение

    """
    _get_constant_value.cache_clear()


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
    return get_env_config().validate_env_int(env_name, default, min_value, max_value)


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


__all__: list[str] = [  # noqa: F822
    "CHROME_STARTUP_DELAY",
    "CONNECTION_MAX_AGE",
    "CSV_BATCH_SIZE",
    "CSV_COLUMNS_PER_ENTITY",
    # Кэширование
    "DEFAULT_BATCH_SIZE",
    # Буферизация
    "DEFAULT_BUFFER_SIZE",
    # Polling
    "DEFAULT_POLL_INTERVAL",
    # Таймауты и задержки
    "DEFAULT_SLEEP_TIME",
    "DEFAULT_TIMEOUT",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    # Rate limiting
    "EXTERNAL_RATE_LIMIT_CALLS",
    "EXTERNAL_RATE_LIMIT_PERIOD",
    "FORBIDDEN_PATH_CHARS",
    "HTTP_CACHE_MAXSIZE",
    # HTTP кэширование
    "HTTP_CACHE_TTL_SECONDS",
    # HTTP статус коды
    "HTTP_STATUS_OK",
    "LRU_EVICT_BATCH",
    # #74: MAX_CONNECTION_AGE удалён как дубликат CONNECTION_MAX_AGE
    "MAX_BATCH_SIZE",
    "MAX_CACHE_SIZE_MB",
    "MAX_CITIES_COUNT",
    # Валидация городов
    "MAX_CITIES_FILE_SIZE",
    "MAX_COLLECTION_SIZE",
    # Безопасность данных
    "MAX_DATA_DEPTH",
    "MAX_DATA_SIZE",
    "MAX_DICT_RECURSION_DEPTH",
    # Безопасность initialState (firm_parser.py)
    "MAX_INITIAL_STATE_DEPTH",
    "MAX_INITIAL_STATE_SIZE",
    "MAX_ITEMS_IN_COLLECTION",
    # JS безопасность
    "MAX_JS_CODE_LENGTH",
    "MAX_LOCK_FILE_AGE",
    "MAX_PATH_LENGTH",
    # Безопасность путей
    "MAX_PATH_LENGTH_SAFE",
    "MAX_POLL_INTERVAL",
    # Connection Pool
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
    # Уникальные имена файлов
    "MAX_UNIQUE_NAME_ATTEMPTS",
    # Безопасность путей
    "MAX_URL_DECODE_ITERATIONS",
    # Парсер - лимиты
    "MAX_VISITED_LINKS_SIZE",
    "MAX_WORKERS",
    "MERGE_BATCH_SIZE",
    "MERGE_BUFFER_SIZE",
    "MERGE_LOCK_TIMEOUT",
    "MIN_POOL_SIZE",
    "MIN_TIMEOUT",
    # Параллельный парсинг
    "MIN_WORKERS",
    "MMAP_CITIES_THRESHOLD",
    "ORPHANED_TEMP_FILE_AGE",
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL",
    "SHA256_HASH_LENGTH",
    "TEMP_FILE_CLEANUP_INTERVAL",
    # Конфигурация ENV
    "EnvConfig",
    "get_env_config",
    "validate_env_int",
]
