"""Конфигурация ENV переменных для parser-2gis.

Этот модуль предоставляет класс EnvConfig для валидации ENV переменных:
- Валидация диапазонов значений
- Lazy инициализация singleton

Пример использования:
    >>> from parser_2gis.constants.env_config import get_env_config
    >>> config = get_env_config()
    >>> print(f"Максимальное количество workers: {config.max_workers}")

ISSUE-012: Рефакторинг — вынесена валидация в отдельные методы для упрощения __post_init__.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


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

    # ISSUE-012: Поля сгруппированы по назначению для лучшей читаемости
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

    # Приватные поля
    _logger: logging.Logger = field(
        init=False,
        repr=False,
        default_factory=lambda: logging.getLogger("parser_2gis.constants.env_config"),
    )

    # ISSUE-012: Конфигурация валидации вынесена в отдельные методы
    # Каждая группа настроек имеет свой метод инициализации

    def __post_init__(self) -> None:
        """Инициализация полей после создания объекта.

        ISSUE-012: Метод упрощён — вся логика вынесена в отдельные методы.
        """
        self._init_parallel_settings()
        self._init_connection_pool_settings()
        self._init_cache_settings()
        self._init_temp_file_settings()
        self._init_merge_settings()

    def _init_parallel_settings(self) -> None:
        """Инициализирует настройки параллельного парсинга.

        ISSUE-012: Вынесено из __post_init__ для улучшения читаемости.
        """
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

    def _init_connection_pool_settings(self) -> None:
        """Инициализирует настройки пула соединений.

        ISSUE-012: Вынесено из __post_init__ для улучшения читаемости.
        """
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

    def _init_cache_settings(self) -> None:
        """Инициализирует настройки кэширования.

        ISSUE-012: Вынесено из __post_init__ для улучшения читаемости.
        """
        object.__setattr__(
            self,
            "max_cache_size_mb",
            self._validate_env_int("PARSER_MAX_CACHE_SIZE_MB", 500, 100, 2000),
        )

    def _init_temp_file_settings(self) -> None:
        """Инициализирует настройки временных файлов.

        ISSUE-012: Вынесено из __post_init__ для улучшения читаемости.
        """
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

    def _init_merge_settings(self) -> None:
        """Инициализирует настройки merge операций.

        ISSUE-012: Вынесено из __post_init__ для улучшения читаемости.
        """
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

    def _validate_env_int(
        self,
        env_name: str,
        default: int,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        """Валидирует ENV переменную как целое число в допустимом диапазоне.

        ISSUE-012: Метод перемещён вниз для лучшей читаемости.

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

    def to_dict(self) -> dict[str, Any]:
        """Конвертирует конфигурацию в словарь.

        ISSUE-012: Добавлен метод для удобной сериализации.

        Returns:
            Словарь с настройками конфигурации.

        """
        return {
            # Параллельный парсинг
            "max_workers": self.max_workers,
            "max_timeout": self.max_timeout,
            "default_timeout": self.default_timeout,
            "min_workers": self.min_workers,
            "min_timeout": self.min_timeout,
            # Connection Pool
            "max_pool_size": self.max_pool_size,
            "min_pool_size": self.min_pool_size,
            "connection_max_age": self.connection_max_age,
            "max_connection_age": self.max_connection_age,
            # Кэширование
            "max_cache_size_mb": self.max_cache_size_mb,
            # Временные файлы
            "max_temp_files": self.max_temp_files,
            "max_temp_files_monitoring": self.max_temp_files_monitoring,
            "temp_file_cleanup_interval": self.temp_file_cleanup_interval,
            "orphaned_temp_file_age": self.orphaned_temp_file_age,
            # Merge операции
            "merge_lock_timeout": self.merge_lock_timeout,
            "max_lock_file_age": self.max_lock_file_age,
        }


# =============================================================================
# LAZY ИНИЦИАЛИЗАЦИЯ ENV CONFIG (SINGLETON PATTERN БЕЗ ГЛОБАЛЬНОГО СОСТОЯНИЯ)
# =============================================================================


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
    if not hasattr(get_env_config, "_instance"):
        get_env_config._instance = EnvConfig()  # type: ignore[attr-defined]
    return get_env_config._instance  # type: ignore[attr-defined]


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


__all__ = ["EnvConfig", "get_env_config", "validate_env_int"]
