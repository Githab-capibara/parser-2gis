"""
Модуль глобальных констант проекта parser-2gis.

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
from typing import Optional

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
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
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
            self, "max_timeout", self._validate_env_int("PARSER_MAX_TIMEOUT", 36000, 60, 86400)
        )
        object.__setattr__(
            self,
            "default_timeout",
            self._validate_env_int("PARSER_DEFAULT_TIMEOUT", 3600, 60, 36000),
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
            self._validate_env_int("PARSER_CONNECTION_MAX_AGE", 300, 60, 3600),
        )
        object.__setattr__(
            self,
            "max_connection_age",
            self._validate_env_int("PARSER_MAX_CONNECTION_AGE", 300, 60, 3600),
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
            self._validate_env_int("PARSER_TEMP_FILE_CLEANUP_INTERVAL", 60, 10, 3600),
        )
        object.__setattr__(
            self,
            "orphaned_temp_file_age",
            self._validate_env_int("PARSER_ORPHANED_TEMP_FILE_AGE", 300, 60, 86400),
        )

        # Merge операции
        object.__setattr__(
            self,
            "merge_lock_timeout",
            self._validate_env_int("PARSER_MERGE_LOCK_TIMEOUT", 3600, 60, 7200),
        )
        object.__setattr__(
            self,
            "max_lock_file_age",
            self._validate_env_int("PARSER_MAX_LOCK_FILE_AGE", 60, 10, 600),
        )


# Глобальный экземпляр конфигурации ENV
env_config: EnvConfig = EnvConfig()


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
    return env_config._validate_env_int(env_name, default, min_value, max_value)


# =============================================================================
# КОНСТАНТЫ БЕЗОПАСНОСТИ ДЛЯ ВАЛИДАЦИИ ДАННЫХ
# =============================================================================

# Максимальная глубина вложенности данных кэша
# ОБОСНОВАНИЕ: 100 уровней достаточно для любых реалистичных структур данных
# Превышение может указывать на циклические ссылки или DoS атаку
MAX_DATA_DEPTH: int = 100

# Максимальная длина строки в байтах
# ОБОСНОВАНИЕ: 10000 байт достаточно для хранения любых текстовых данных
# Превышение может указывать на попытку хранения больших объёмов данных в кэше
MAX_STRING_LENGTH: int = 10000

# Максимальный размер данных в байтах (10 MB)
# ОБОСНОВАНИЕ: 10MB достаточно для обработки данных парсинга
# Превышение может указывать на DoS атаку или некорректные данные
MAX_DATA_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Максимальное количество элементов в коллекциях
# ОБОСНОВАНИЕ: 100,000 элементов достаточно для обработки
# Превышение может привести к MemoryError
MAX_COLLECTION_SIZE: int = 100000

# Максимальная длина пути в символах
# ОБОСНОВАНИЕ: 4096 символов - стандартный лимит PATH_MAX в Linux
# Превышение может указывать на некорректные данные или атаку
MAX_PATH_LENGTH: int = 4096

# =============================================================================
# КОНСТАНТЫ ДЛЯ КЭШИРОВАНИЯ
# =============================================================================

# Размер пакета для пакетных операций вставки/удаления
DEFAULT_BATCH_SIZE: int = 100

# Максимальный возраст соединения в секундах (5 минут)
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
MAX_CONNECTION_AGE: int = env_config.max_connection_age

# Максимальный размер пакета для предотвращения DoS атак
MAX_BATCH_SIZE: int = 1000

# Максимальный размер кэша в мегабайтах
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
MAX_CACHE_SIZE_MB: int = env_config.max_cache_size_mb

# Количество записей для удаления при LRU eviction
LRU_EVICT_BATCH: int = 100

# Длина SHA256 хеша в hex формате
SHA256_HASH_LENGTH: int = 64

# =============================================================================
# КОНСТАНТЫ ДЛЯ CONNECTION POOL
# =============================================================================

# Максимальное количество соединений в пуле (10-20 соединений)
# ОБОСНОВАНИЕ: 20 соединений выбрано исходя из:
# - Типичное количество потоков: 5-15
# - Каждое соединение занимает ~1-5MB памяти
# - 20 * 5MB = 100MB - разумный предел для большинства систем
# - queue.Queue для управления соединениями обеспечивает потокобезопасность
# Допустимый диапазон: 5-50 соединений
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
MAX_POOL_SIZE: int = env_config.max_pool_size

# Минимальное количество соединений в пуле
# Допустимый диапазон: 1-10 соединений
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
MIN_POOL_SIZE: int = env_config.min_pool_size

# Время жизни соединения в секундах (5 минут)
# Соединения старше этого возраста будут пересозданы
# Допустимый диапазон: 60-3600 секунд (1 час)
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
CONNECTION_MAX_AGE: int = env_config.connection_max_age

# =============================================================================
# КОНСТАНТЫ ДЛЯ ПАРАЛЛЕЛЬНОГО ПАРСИНГА
# =============================================================================

# Минимальное количество рабочих потоков
MIN_WORKERS: int = env_config.min_workers

# Максимальное количество рабочих потоков (разумный предел для I/O операций)
# ОБОСНОВАНИЕ: 50 потоков - оптимально для современных систем с 16-32+ ядрами
# При 50 потоках с 200MB на браузер = ~10GB памяти (требуется мощная система)
# Может быть переопределено через ENV переменную PARSER_MAX_WORKERS (диапазон: 1-100)
MAX_WORKERS: int = env_config.max_workers

# Минимальный таймаут на один URL в секундах
MIN_TIMEOUT: int = env_config.min_timeout

# Максимальный таймаут на один URL в секундах (10 часов - практически безлимит)
# Увеличено для поддержки 40+ параллельных браузеров без таймаутов
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
MAX_TIMEOUT: int = env_config.max_timeout

# Таймаут по умолчанию на один URL в секундах (1 час)
# Увеличено для стабильной работы с большим количеством параллельных браузеров
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
DEFAULT_TIMEOUT: int = env_config.default_timeout

# Интервал периодической очистки временных файлов в секундах (60 секунд)
# Допустимый диапазон: 10-3600 секунд (10 минут)
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
TEMP_FILE_CLEANUP_INTERVAL: int = env_config.temp_file_cleanup_interval

# Максимальное количество временных файлов для мониторинга
# Допустимый диапазон: 100-10000
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
MAX_TEMP_FILES_MONITORING: int = env_config.max_temp_files_monitoring

# Возраст временного файла в секундах, после которого он считается осиротевшим
# Допустимый диапазон: 60-86400 секунд (1 день)
# HIGH 10: Вынесено в ENV переменную для гибкой настройки
ORPHANED_TEMP_FILE_AGE: int = env_config.orphaned_temp_file_age

# Максимальное количество отслеживаемых временных файлов
# ОБОСНОВАНИЕ: 1000 файлов выбрано исходя из:
# - Типичное количество временных файлов: 10-100
# - 1000 - разумный лимит для предотвращения утечки памяти
# - При достижении лимита происходит LRU eviction
# Допустимый диапазон: 100-5000 файлов
MAX_TEMP_FILES: int = 1000

# Таймаут ожидания блокировки merge операции в секундах
# ОБОСНОВАНИЕ: 60 секунд выбрано исходя из:
# - Типичное время merge операции: 5-30 секунд
# - 60 секунд - достаточно для обработки больших файлов
# - Защита от зависших процессов (осиротевшие lock файлы)
MERGE_LOCK_TIMEOUT: int = env_config.merge_lock_timeout

# Максимальный возраст lock файла в секундах (1 минута)
# ОБОСНОВАНИЕ: 60 секунд выбрано исходя из:
# - Типичное время merge: 5-30 секунд
# - 1 минута - достаточно для завершения merge операции
# - Lock файлы старше считаются осиротевшими (процесс упал)
MAX_LOCK_FILE_AGE: int = env_config.max_lock_file_age

# =============================================================================
# КОНСТАНТЫ ДЛЯ БУФЕРИЗАЦИИ
# =============================================================================

# Размер буфера для чтения/записи файлов в байтах (512 KB)
# ОБОСНОВАНИЕ: 512KB выбрано исходя из:
# - Стандартный размер страницы памяти в Linux: 4KB
# - 512KB = 128 страниц - оптимально для системных вызовов read/write
# - Тесты показывают плато производительности на 64-512KB
# - 512KB баланс между использованием памяти и производительностью
DEFAULT_BUFFER_SIZE: int = 524288  # 512 KB

# Размер буфера для слияния файлов в байтах (128 KB)
# ОБОСНОВАНИЕ: 128KB выбрано исходя из:
# - Меньший размер для снижения потребления памяти при слиянии
# - Достаточно для эффективной пакетной обработки
# - Тесты показывают хорошее соотношение память/производительность
MERGE_BUFFER_SIZE: int = 131072  # 128 KB

# Размер пакета строк для пакетной записи в CSV
CSV_BATCH_SIZE: int = 1000

# Размер пакета строк для слияния файлов
MERGE_BATCH_SIZE: int = 500

# =============================================================================
# КОНСТАНТЫ ДЛЯ ВАЛИДАЦИИ ГОРОДОВ
# =============================================================================

# Максимальный размер файла городов в байтах (10 MB)
# ОБОСНОВАНИЕ: 10MB достаточно для хранения ~5000 городов с метаданными
# Защита от DoS атак через загрузку чрезмерно больших файлов
MAX_CITIES_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Максимальное количество городов для парсинга
# ОБОСНОВАНИЕ: 1000 городов - разумный предел для одного сеанса парсинга
# Превышение может привести к чрезмерному времени выполнения и потреблению ресурсов
MAX_CITIES_COUNT: int = 1000

# Порог использования mmap для больших файлов (1 MB)
# Файлы больше этого размера будут читаться через mmap для оптимизации памяти
MMAP_CITIES_THRESHOLD: int = 1 * 1024 * 1024  # 1 MB

# =============================================================================
# КОНСТАНТЫ ДЛЯ JS БЕЗОПАСНОСТИ
# =============================================================================

# Максимальная длина JavaScript кода в символах
# ОБОСНОВАНИЕ: 100,000 символов достаточно для любых скриптов парсинга
# Превышение может указывать на попытку инъекции или DoS атаку
MAX_JS_CODE_LENGTH: int = 100000

# Максимальный размер ответа в байтах (10 MB)
# ОБОСНОВАНИЕ: 10MB достаточно для загрузки любых ресурсов страницы
# Превышение может указывать на попытку загрузки больших файлов
MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Максимальный суммарный размер всех JS скриптов в байтах (5 MB)
# ОБОСНОВАНИЕ: 5MB достаточно для загрузки всех скриптов страницы
# Превышение может указывать на попытку DoS атаки
MAX_TOTAL_JS_SIZE: int = 5 * 1024 * 1024  # 5 MB

# Задержка при старте Chrome в секундах
# Увеличено для поддержки 40+ параллельных браузеров
CHROME_STARTUP_DELAY: float = 5.0

# =============================================================================
# КОНСТАНТЫ ДЛЯ RATE LIMITING
# =============================================================================

# Количество внешних запросов в период
# ОБОСНОВАНИЕ: 10 запросов в 60 секунд - разумный лимит для внешних API
EXTERNAL_RATE_LIMIT_CALLS: int = 10

# Период rate limiting в секундах
EXTERNAL_RATE_LIMIT_PERIOD: int = 60

# =============================================================================
# КОНСТАНТЫ ДЛЯ HTTP КЭШИРОВАНИЯ
# =============================================================================

# Время жизни кэша HTTP запросов в секундах (5 минут)
HTTP_CACHE_TTL_SECONDS: int = 300

# Размер кэша HTTP запросов (максимальное количество записей)
HTTP_CACHE_MAXSIZE: int = 1024

# =============================================================================
# КОНСТАНТЫ ДЛЯ POLLING
# =============================================================================

# Стандартный интервал опроса в секундах
DEFAULT_POLL_INTERVAL: float = 0.1

# Максимальный интервал опроса в секундах
MAX_POLL_INTERVAL: float = 2.0

# Множитель экспоненциальной задержки
EXPONENTIAL_BACKOFF_MULTIPLIER: float = 2

# =============================================================================
# КОНСТАНТЫ ДЛЯ ПРОГРЕССА
# =============================================================================

# Интервал обновления прогресс-бара в секундах
PROGRESS_UPDATE_INTERVAL: int = 3

# =============================================================================
# КОНСТАНТЫ ДЛЯ УНИКАЛЬНЫХ ИМЁН ФАЙЛОВ
# =============================================================================

# Максимальное количество попыток создания уникального имени файла
# ОБОСНОВАНИЕ: 10 попыток выбрано исходя из:
# - Вероятность коллизии UUID4: ~10^-15 (практически невозможно)
# - 10 попыток - защита от крайне редких случаев генерации дубликатов
# - Достаточно для защиты от бесконечного цикла при сбоях ФС
MAX_UNIQUE_NAME_ATTEMPTS: int = 10

# =============================================================================
# КОНСТАНТЫ ДЛЯ ТАЙМАУТОВ И ЗАДЕРЖЕК
# =============================================================================

# Стандартная задержка по умолчанию в секундах
# ОБОСНОВАНИЕ: 0.1 секунды (100 мс) - разумный баланс между
# скоростью реакции и снижением нагрузки на CPU при polling
DEFAULT_SLEEP_TIME: float = 0.1

# =============================================================================
# КОНСТАНТЫ БЕЗОПАСНОСТИ ПУТЕЙ
# =============================================================================

# Максимальная длина пути для предотвращения переполнения буфера
MAX_PATH_LENGTH_SAFE: int = 4096

# Запрещённые символы в путях для предотвращения path traversal атак
FORBIDDEN_PATH_CHARS: list[str] = ["..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"]

# =============================================================================
# ЭКСПОРТИРУЕМЫЕ СИМВОЛЫ
# =============================================================================

__all__ = [
    # Конфигурация ENV
    "env_config",
    "EnvConfig",
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
