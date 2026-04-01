"""
Пакет валидации данных для Parser2GIS.

Этот пакет предоставляет централизованные функции и классы для валидации
различных типов данных: URL, числовых значений, строк, списков, email,
телефонов и путей.

Структура пакета:
    - url_validator: Валидация URL (validate_url, is_valid_url)
    - data_validator: Валидация данных (числа, строки, списки, email, телефоны)
    - path_validator: Валидация путей (PathValidator, validate_path)
    - path_validation: Консолидированная валидация путей
    - legacy: Экспорт для обратной совместимости

Пример использования:
    >>> from parser_2gis.validation import validate_url, validate_positive_int, PathValidator
    >>> result = validate_url("https://2gis.ru/moscow")
    >>> print(result.is_valid)
    True
    >>> value = validate_positive_int(5, 1, 100, "--parser.max-retries")
    >>> print(value)
    5
    >>> validator = PathValidator()
    >>> validator.validate("/safe/path/file.txt")
"""

from __future__ import annotations

from .data_validator import (
    ValidationResult,
    validate_categories_config,
    validate_cities_config,
    validate_email,
    validate_list_length,
    validate_non_empty_list,
    validate_non_empty_string,
    validate_parallel_config,
    validate_phone,
    validate_positive_float,
    validate_positive_int,
    validate_string_length,
)

# Импортируем всё из legacy для обратной совместимости
from .legacy import *  # noqa: F401,F403
from .path_validation import (
    PathSafetyValidator,
    PathTraversalError,
    validate_path_safety,
    validate_path_traversal,
)
from .path_validator import PathValidator, get_path_validator, validate_path

# Импортируем всё из подмодулей для удобного доступа
from .url_validator import clear_url_cache, is_valid_url, validate_url

__all__ = [
    # URL валидация
    "validate_url",
    "is_valid_url",
    "clear_url_cache",
    # Валидация данных
    "ValidationResult",
    "validate_positive_int",
    "validate_positive_float",
    "validate_non_empty_string",
    "validate_string_length",
    "validate_non_empty_list",
    "validate_list_length",
    "validate_email",
    "validate_phone",
    # Валидация конфигурации параллельного парсинга
    "validate_cities_config",
    "validate_categories_config",
    "validate_parallel_config",
    # Валидация путей (старый модуль)
    "PathValidator",
    "get_path_validator",
    "validate_path",
    # Валидация путей (новый консолидированный модуль)
    "PathSafetyValidator",
    "PathTraversalError",
    "validate_path_traversal",
    "validate_path_safety",
]
