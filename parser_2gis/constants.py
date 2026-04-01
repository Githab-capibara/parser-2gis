"""Модуль глобальных констант проекта parser-2gis.

Этот модуль содержит все магические числа и константы используемые в проекте.
Константы вынесены для централизованного управления и упрощения тестирования.

Пример использования:
    >>> from parser_2gis.constants import MAX_DATA_DEPTH, MAX_STRING_LENGTH
    >>> print(f"Максимальная глубина: {MAX_DATA_DEPTH}")
    Максимальная глубина: 15
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from typing import TypeAlias

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

    _logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("parser_2gis.constants.env_config"),
        repr=False,
        init=False,
    )

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
    min_workers: int = field(init=False, default=1)
    min_timeout: int = field(init=False, default=1)

    # Connection Pool
    max_pool_size: int = field(init=False)
    min_pool_size: int = field(init=False)
    connection_max_age: int = field(init=False)
    max_connection_age: int = field(init=False)

    # Кэширование
    max_cache_size_mb: int = field(init=False)

    # Временные файлы
    max_temp_files: int = field(init=False, default=1000)
    max_temp_files_monitoring: int = field(init=False)
    temp_file_cleanup_interval: int = field(init=False)
    orphaned_temp_file_age: int = field(init=False)

    # Merge операции
    merge_lock_timeout: int = field(init=False)
    max_lock_file_age: int = field(init=False)

    def __post_init__(self) -> None:
        """Инициализация полей после создания объекта."""
        # Параллельный парсинг
        object.__setattr__(
            self, "max_workers", self._validate_env_int("PARSER_MAX_WORKERS", 50, 1, 100)
        )
        object.__setattr__(
            self, "max_timeout", self._validate_env_int("PARSER_MAX_TIMEOUT", 72000, 60, 172800)
        )
        object.__setattr__(
            self,
            "default_timeout",
            self._validate_env_int("PARSER_DEFAULT_TIMEOUT", 7200, 60, 72000),
        )

        # Connection Pool
        object.__setattr__(
            self, "max_pool_size", self._validate_env_int("PARSER_MAX_POOL_SIZE", 20, 5, 50)
        )
        object.__setattr__(
            self, "min_pool_size", self._validate_env_int("PARSER_MIN_POOL_SIZE", 5, 1, 10)
        )
        object.__setattr__(
            self,
            "connection_max_age",
            self._validate_env_int("PARSER_CONNECTION_MAX_AGE", 600, 60, 7200),
        )
        object.__setattr__(
            self,
            "max_connection_age",
            self._validate_env_int("PARSER_MAX_CONNECTION_AGE", 600, 60, 7200),
        )

        # Кэширование
        object.__setattr__(
            self,
            "max_cache_size_mb",
            self._validate_env_int("PARSER_MAX_CACHE_SIZE_MB", 500, 100, 2000),
        )

        # Временные файлы
        object.__setattr__(
            self,
            "max_temp_files_monitoring",
            self._validate_env_int("PARSER_MAX_TEMP_FILES_MONITORING", 1000, 100, 10000),
        )
        object.__setattr__(
            self,
            "temp_file_cleanup_interval",
            self._validate_env_int("PARSER_TEMP_FILE_CLEANUP_INTERVAL", 120, 10, 7200),
        )
        object.__setattr__(
            self,
            "orphaned_temp_file_age",
            self._validate_env_int("PARSER_ORPHANED_TEMP_FILE_AGE", 600, 60, 172800),
        )

        # Merge операции
        object.__setattr__(
            self,
            "merge_lock_timeout",
            self._validate_env_int("PARSER_MERGE_LOCK_TIMEOUT", 7200, 60, 14400),
        )
        object.__setattr__(
            self,
            "max_lock_file_age",
            self._validate_env_int("PARSER_MAX_LOCK_FILE_AGE", 120, 10, 1200),
        )


# =============================================================================
# LAZY ИНИЦИАЛИЗАЦИЯ ENV CONFIG (SINGLETON PATTERN)
# =============================================================================

# Глобальная переменная для хранения singleton экземпляра
_env_config_instance: EnvConfig | None = None


def get_env_config() -> EnvConfig:
    """Получает singleton экземпляр EnvConfig с lazy инициализацией.

    EnvConfig создаётся только при первом вызове функции, а не при импорте модуля.
    Это предотвращает лишние вычисления при импорте и ускоряет запуск модуля.

    Returns:
        Singleton экземпляр EnvConfig.

    Example:
        >>> config = get_env_config()
        >>> print(config.max_workers)  # 50 (или значение из PARSER_MAX_WORKERS)

    """
    global _env_config_instance
    if _env_config_instance is None:
        _env_config_instance = EnvConfig()
    return _env_config_instance


# Для обратной совместимости используем __getattr__ для ленивой инициализации
def __getattr__(name: str) -> int | float | list[str] | EnvConfig:
    """Ленивая инициализация констант для устранения global singleton (A034).

    Константы, зависящие от ENV переменных, создаются только при первом обращении.
    Это предотвращает инициализацию global state при импорте модуля.
    """
    # Lazy initialization для env_config
    if name == "env_config":
        return get_env_config()

    # Lazy initialization для ENV-зависимых констант
    config = get_env_config()

    # Константы для кэширования
    if name == "MAX_CONNECTION_AGE":
        return config.max_connection_age
    if name == "MAX_CACHE_SIZE_MB":
        return config.max_cache_size_mb

    # Константы для connection pool
    if name == "MAX_POOL_SIZE":
        return config.max_pool_size
    if name == "MIN_POOL_SIZE":
        return config.min_pool_size
    if name == "CONNECTION_MAX_AGE":
        return config.connection_max_age

    # Константы для параллельного парсинга
    if name == "MIN_WORKERS":
        return config.min_workers
    if name == "MAX_WORKERS":
        return config.max_workers
    if name == "MIN_TIMEOUT":
        return config.min_timeout
    if name == "MAX_TIMEOUT":
        return config.max_timeout
    if name == "DEFAULT_TIMEOUT":
        return config.default_timeout
    if name == "TEMP_FILE_CLEANUP_INTERVAL":
        return config.temp_file_cleanup_interval
    if name == "MAX_TEMP_FILES_MONITORING":
        return config.max_temp_files_monitoring
    if name == "ORPHANED_TEMP_FILE_AGE":
        return config.orphaned_temp_file_age
    if name == "MERGE_LOCK_TIMEOUT":
        return config.merge_lock_timeout
    if name == "MAX_LOCK_FILE_AGE":
        return config.max_lock_file_age

    # Статические константы (для обратной совместимости)
    # Безопасность данных
    if name == "MAX_DATA_DEPTH":
        return 100
    if name == "MAX_STRING_LENGTH":
        return 10000
    if name == "MAX_DATA_SIZE":
        return 10 * 1024 * 1024
    if name == "MAX_COLLECTION_SIZE":
        return 100000
    if name == "MAX_PATH_LENGTH":
        return 4096

    # Кэширование
    if name == "DEFAULT_BATCH_SIZE":
        return 100
    if name == "MAX_BATCH_SIZE":
        return 1000
    if name == "LRU_EVICT_BATCH":
        return 100
    if name == "SHA256_HASH_LENGTH":
        return 64

    # Параллельный парсинг
    if name == "MAX_TEMP_FILES":
        return 1000

    # Буферизация
    if name == "DEFAULT_BUFFER_SIZE":
        return 524288
    if name == "MERGE_BUFFER_SIZE":
        return 131072
    if name == "CSV_BATCH_SIZE":
        return 1000
    if name == "MERGE_BATCH_SIZE":
        return 500

    # Валидация городов
    if name == "MAX_CITIES_FILE_SIZE":
        return 10 * 1024 * 1024
    if name == "MAX_CITIES_COUNT":
        return 1000
    if name == "MMAP_CITIES_THRESHOLD":
        return 1 * 1024 * 1024

    # JS безопасность
    if name == "MAX_JS_CODE_LENGTH":
        return 100000
    if name == "MAX_RESPONSE_SIZE":
        return 10 * 1024 * 1024
    if name == "MAX_TOTAL_JS_SIZE":
        return 5 * 1024 * 1024
    if name == "CHROME_STARTUP_DELAY":
        return 5.0

    # Rate limiting
    if name == "EXTERNAL_RATE_LIMIT_CALLS":
        return 10
    if name == "EXTERNAL_RATE_LIMIT_PERIOD":
        return 60

    # HTTP кэширование
    if name == "HTTP_CACHE_TTL_SECONDS":
        return 300
    if name == "HTTP_CACHE_MAXSIZE":
        return 1024

    # Polling
    if name == "DEFAULT_POLL_INTERVAL":
        return 0.1
    if name == "MAX_POLL_INTERVAL":
        return 2.0
    if name == "EXPONENTIAL_BACKOFF_MULTIPLIER":
        return 2

    # Прогресс
    if name == "PROGRESS_UPDATE_INTERVAL":
        return 3

    # Уникальные имена файлов
    if name == "MAX_UNIQUE_NAME_ATTEMPTS":
        return 10

    # Таймауты и задержки
    if name == "DEFAULT_SLEEP_TIME":
        return 0.1

    # Безопасность путей
    if name == "MAX_PATH_LENGTH_SAFE":
        return 4096
    if name == "FORBIDDEN_PATH_CHARS":
        return ["..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    return get_env_config()._validate_env_int(env_name, default, min_value, max_value)


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
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL",
    # Уникальные имена файлов
    "MAX_UNIQUE_NAME_ATTEMPTS",
    # Таймауты и задержки
    "DEFAULT_SLEEP_TIME",
    # Безопасность путей
    "MAX_PATH_LENGTH_SAFE",
    "FORBIDDEN_PATH_CHARS",
]


# =============================================================================
# __dir__ ДЛЯ КОРРЕКТНОЙ РАБОТЫ С __all__
# =============================================================================


def __dir__() -> list[str]:
    """Возвращает список экспортируемых имён для dir() и инструментов статического анализа.

    Это необходимо для корректной работы с __all__ при использовании __getattr__.
    """
    return __all__
