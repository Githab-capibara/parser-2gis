"""Модуль валидации данных.

Содержит функции для валидации числовых значений, строк, списков,
email адресов и номеров телефонов.

Пример использования:
    >>> from parser_2gis.validation.data_validator import validate_positive_int, validate_email
    >>> value = validate_positive_int(5, 1, 100, "--parser.max-retries")
    >>> print(value)
    5
    >>> result = validate_email("test@example.com")
    >>> print(result.is_valid)
    True
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass

# =============================================================================
# РЕЗУЛЬТАТ ВАЛИДАЦИИ
# =============================================================================


@dataclass
class ValidationResult:
    """Результат валидации.

    Attributes:
        is_valid: Флаг успешности валидации.
        value: Валидированное значение (или None при ошибке).
        error: Сообщение об ошибке (или None при успехе).

    """

    is_valid: bool
    value: str | None = None
    error: str | None = None


# =============================================================================
# ВАЛИДАЦИЯ ЧИСЛОВЫХ ЗНАЧЕНИЙ
# =============================================================================


def validate_positive_int(value: int, min_val: int, max_val: int, arg_name: str) -> int:
    """Валидирует положительное целое число в заданном диапазоне.

    Args:
        value: Значение для валидации.
        min_val: Минимально допустимое значение (включительно).
        max_val: Максимально допустимое значение (включительно).
        arg_name: Имя аргумента для сообщения об ошибке.

    Returns:
        Валидированное значение.

    Raises:
        ValueError: Если значение выходит за пределы диапазона.

    Example:
        >>> validate_positive_int(5, 1, 100, "--parser.max-retries")
        5
        >>> validate_positive_int(0, 1, 100, "--parser.max-retries")
        ValueError: --parser.max-retries должен быть не менее 1 (получено 0)

    """
    if value < min_val:
        raise ValueError(f"{arg_name} должен быть не менее {min_val} (получено {value})")
    if value > max_val:
        raise ValueError(f"{arg_name} должен быть не более {max_val} (получено {value})")
    return value


def validate_positive_float(value: float, min_val: float, max_val: float, arg_name: str) -> float:
    """Валидирует положительное число с плавающей точкой в заданном диапазоне.

    Args:
        value: Значение для валидации.
        min_val: Минимально допустимое значение (включительно).
        max_val: Максимально допустимое значение (включительно).
        arg_name: Имя аргумента для сообщения об ошибке.

    Returns:
        Валидированное значение.

    Raises:
        ValueError: Если значение выходит за пределы диапазона.

    Example:
        >>> validate_positive_float(1.5, 0.0, 10.0, "--chrome.startup-delay")
        1.5

    """
    if value < min_val:
        raise ValueError(f"{arg_name} должен быть не менее {min_val} (получено {value})")
    if value > max_val:
        raise ValueError(f"{arg_name} должен быть не более {max_val} (получено {value})")
    return value


# =============================================================================
# ВАЛИДАЦИЯ СТРОКОВЫХ ЗНАЧЕНИЙ
# =============================================================================


def validate_non_empty_string(value: str, field_name: str) -> str:
    """Валидирует строку на непустоту.

    Args:
        value: Строка для валидации.
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Валидированную строку.

    Raises:
        ValueError: Если строка пустая или содержит только пробелы.

    Example:
        >>> validate_non_empty_string("Москва", "city_name")
        'Москва'
        >>> validate_non_empty_string("", "city_name")
        ValueError: city_name не может быть пустым

    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} не может быть пустым")
    return value.strip()


def validate_string_length(value: str, min_length: int, max_length: int, field_name: str) -> str:
    """Валидирует длину строки.

    Args:
        value: Строка для валидации.
        min_length: Минимальная длина (включительно).
        max_length: Максимальная длина (включительно).
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Валидированную строку.

    Raises:
        ValueError: Если длина строки выходит за пределы диапазона.

    Example:
        >>> validate_string_length("Москва", 2, 50, "city_name")
        'Москва'

    """
    if len(value) < min_length:
        raise ValueError(f"{field_name} должен быть не менее {min_length} символов")
    if len(value) > max_length:
        raise ValueError(f"{field_name} должен быть не более {max_length} символов")
    return value


# =============================================================================
# ВАЛИДАЦИЯ СПИСКОВ И КОЛЛЕКЦИЙ
# =============================================================================


def validate_non_empty_list(value: list, field_name: str) -> list:
    """Валидирует список на непустоту.

    Args:
        value: Список для валидации.
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Валидированный список.

    Raises:
        ValueError: Если список пустой.

    Example:
        >>> validate_non_empty_list([1, 2, 3], "items")
        [1, 2, 3]
        >>> validate_non_empty_list([], "items")
        ValueError: items не может быть пустым

    """
    if not value:
        raise ValueError(f"{field_name} не может быть пустым")
    return value


def validate_list_length(value: list, min_length: int, max_length: int, field_name: str) -> list:
    """Валидирует длину списка.

    Args:
        value: Список для валидации.
        min_length: Минимальная длина (включительно).
        max_length: Максимальная длина (включительно).
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Валидированный список.

    Raises:
        ValueError: Если длина списка выходит за пределы диапазона.

    Example:
        >>> validate_list_length([1, 2, 3], 1, 10, "items")
        [1, 2, 3]

    """
    if len(value) < min_length:
        raise ValueError(f"{field_name} должен содержать не менее {min_length} элементов")
    if len(value) > max_length:
        raise ValueError(f"{field_name} должен содержать не более {max_length} элементов")
    return value


# =============================================================================
# ВАЛИДАЦИЯ EMAIL
# =============================================================================

# Скомпилированный regex паттерн для валидации email
# Поддерживает IDN (Internationalized Domain Names) через Unicode символы
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
# Паттерн для IDN email (с поддержкой Unicode)
_IDN_EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def validate_email(email: str) -> ValidationResult:
    """Валидирует email адрес.

    Поддерживает как стандартные email, так и IDN (Internationalized Domain Names).

    Args:
        email: Email для валидации.

    Returns:
        ValidationResult с информацией о валидности email.

    Example:
        >>> result = validate_email("test@example.com")
        >>> print(result.is_valid)
        True
        >>> result = validate_email("test@пример.рф")
        >>> print(result.is_valid)
        True

    """
    if not email:
        return ValidationResult(is_valid=False, error="Email не может быть пустым")

    if len(email) > 254:
        return ValidationResult(
            is_valid=False, error=f"Email слишком длинный (максимум 254 символа): {email[:50]}..."
        )

    # Сначала пробуем стандартный ASCII email
    if _EMAIL_PATTERN.match(email):
        return ValidationResult(is_valid=True, value=email, error=None)

    # Если не подошло, пробуем IDN email (с Unicode символами)
    if _IDN_EMAIL_PATTERN.match(email):
        # Дополнительная проверка на наличие @ и домена
        parts = email.split("@")
        if len(parts) == 2 and len(parts[0]) > 0 and "." in parts[1]:
            return ValidationResult(is_valid=True, value=email, error=None)

    return ValidationResult(is_valid=False, error=f"Некорректный формат email: {email}")


# =============================================================================
# ВАЛИДАЦИЯ НОМЕРОВ ТЕЛЕФОНОВ
# =============================================================================

# Скомпилированный regex паттерн для валидации российских телефонов
_PHONE_PATTERN = re.compile(r"^\+?7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$")

# Пример ожидаемого формата телефона
PHONE_FORMAT_EXAMPLE = "+7 (XXX) XXX-XX-XX"
"""Пример ожидаемого формата номера телефона."""


def validate_phone(phone: str) -> ValidationResult:
    """Валидирует российский номер телефона.

    Args:
        phone: Телефон для валидации.

    Returns:
        ValidationResult с информацией о валидности телефона.

    Example:
        >>> result = validate_phone("+7 (495) 123-45-67")
        >>> print(result.is_valid)
        True

    """
    if not phone:
        return ValidationResult(is_valid=False, error="Телефон не может быть пустым")

    cleaned = re.sub(r"[\s\-()]", "", phone)

    if not cleaned:
        return ValidationResult(is_valid=False, error="Телефон не может быть пустым после очистки")

    if len(cleaned) < 10:
        return ValidationResult(
            is_valid=False,
            error=f"Телефон слишком короткий: {phone}. Ожидался формат: {PHONE_FORMAT_EXAMPLE}",
        )

    if not _PHONE_PATTERN.match(phone):
        return ValidationResult(
            is_valid=False,
            error=f"Некорректный формат телефона: {phone}. Ожидался формат: {PHONE_FORMAT_EXAMPLE}",
        )

    normalized = f"8 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:9]}-{cleaned[9:11]}"

    return ValidationResult(is_valid=True, value=normalized, error=None)


# =============================================================================
# ВАЛИДАЦИЯ КОНФИГУРАЦИИ ПАРАЛЛЕЛЬНОГО ПАРСИНГА
# =============================================================================

# ISSUE-154, ISSUE-155: Используем OrderedDict для true LRU кэширования
# C003: Кэш для валидации конфигурации городов на основе JSON хеша
# ISSUE-155: Используем OrderedDict для true LRU eviction
_CITIES_CONFIG_CACHE: OrderedDict[str, list] = OrderedDict()
_CATEGORIES_CONFIG_CACHE: OrderedDict[str, list] = OrderedDict()
_CACHE_MAX_SIZE = 256  # LRU eviction при 256 записях


def _compute_config_hash(config: list) -> str:
    """Вычисляет SHA256 хеш конфигурации для кэширования.

    C003: Хеширование для кэширования результатов валидации.
    """
    import hashlib
    import json

    config_json = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(config_json.encode("utf-8")).hexdigest()


def _evict_cache_if_needed(cache: OrderedDict[str, list], max_size: int = _CACHE_MAX_SIZE) -> None:
    """LRU eviction для кэша конфигураций.

    ISSUE-155: Используем OrderedDict для true LRU eviction.
    При переполнении удаляется самый старый элемент (первый в OrderedDict).
    """
    while len(cache) >= max_size:
        # Удаляем самый старый элемент (первый в OrderedDict - LRU)
        cache.popitem(last=False)


def _validate_config_data(config: list, field_name: str, cache: OrderedDict[str, list]) -> list:
    """Универсальная валидация конфигурации городов/категорий.

    ISSUE-154: Использует OrderedDict для true LRU кэширования.
    ISSUE-155: Корректная LRU eviction через OrderedDict.

    Args:
        config: Список конфигурации для валидации.
        field_name: Имя поля для сообщения об ошибке.
        cache: Кэш OrderedDict для сохранения результатов.

    Returns:
        Валидированный список конфигурации.

    Raises:
        ValueError: Если конфигурация некорректна.

    """
    config_hash = _compute_config_hash(config)
    if config_hash in cache:
        cache.move_to_end(config_hash)
        return cache[config_hash]

    if not config:
        raise ValueError(f"{field_name} не может быть пустым")

    if not isinstance(config, list):
        raise ValueError(f"{field_name} должен быть списком")

    for idx, item in enumerate(config):
        if not isinstance(item, dict):
            raise ValueError(f"{field_name}[{idx}] должен быть словарём (dict)")
        if "name" not in item:
            raise ValueError(f"{field_name}[{idx}] должен содержать ключ 'name'")
        if not isinstance(item.get("name"), str) or not item.get("name"):
            raise ValueError(f"{field_name}[{idx}]: 'name' должен быть непустой строкой")

    _evict_cache_if_needed(cache)
    cache[config_hash] = config
    return config


def validate_cities_config(cities: list, field_name: str = "cities") -> list:
    """Валидирует конфигурацию городов для параллельного парсинга.

    ISSUE-154: Использует OrderedDict для true LRU кэширования.
    ISSUE-155: Корректная LRU eviction через OrderedDict.

    Args:
        cities: Список городов для валидации.
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Валидированный список городов.

    Raises:
        ValueError: Если конфигурация городов некорректна.

    Example:
        >>> cities = [{"name": "Москва", "code": "msk", "domain": "moscow"}]
        >>> validate_cities_config(cities)
        [{'name': 'Москва', 'code': 'msk', 'domain': 'moscow'}]

    """
    return _validate_config_data(cities, field_name, _CITIES_CONFIG_CACHE)


def validate_categories_config(categories: list, field_name: str = "categories") -> list:
    """Валидирует конфигурацию категорий для параллельного парсинга.

    ISSUE-154: Использует OrderedDict для true LRU кэширования.
    ISSUE-155: Корректная LRU eviction через OrderedDict.

    Args:
        categories: Список категорий для валидации.
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Валидированный список категорий.

    Raises:
        ValueError: Если конфигурация категорий некорректна.

    Example:
        >>> categories = [{"name": "Кафе", "query": "Кафе"}]
        >>> validate_categories_config(categories)
        [{'name': 'Кафе', 'query': 'Кафе'}]

    """
    return _validate_config_data(categories, field_name, _CATEGORIES_CONFIG_CACHE)


def validate_parallel_config(
    max_workers: int,
    timeout_per_url: int,
    min_workers: int = 1,
    max_workers_limit: int = 100,
    min_timeout: int = 1,
    max_timeout: int = 7200,
) -> dict:
    """Валидирует конфигурацию параллельного парсинга.

    Args:
        max_workers: Максимальное количество рабочих потоков.
        timeout_per_url: Таймаут на один URL в секундах.
        min_workers: Минимальное количество рабочих потоков.
        max_workers_limit: Максимально допустимое количество рабочих потоков.
        min_timeout: Минимальный таймаут на один URL.
        max_timeout: Максимальный таймаут на один URL.

    Returns:
        Словарь с валидированными параметрами.

    Raises:
        ValueError: Если конфигурация некорректна.

    Example:
        >>> validate_parallel_config(5, 300)
        {'max_workers': 5, 'timeout_per_url': 300}

    """
    if max_workers < min_workers:
        raise ValueError(f"max_workers должен быть не менее {min_workers} (получено {max_workers})")
    if max_workers > max_workers_limit:
        raise ValueError(
            f"max_workers слишком большой: {max_workers} (максимум: {max_workers_limit})"
        )
    if timeout_per_url < min_timeout:
        raise ValueError(
            f"timeout_per_url должен быть не менее {min_timeout} секунд (получено {timeout_per_url})"
        )
    if timeout_per_url > max_timeout:
        raise ValueError(
            f"timeout_per_url слишком большой: {timeout_per_url} секунд (максимум: {max_timeout})"
        )

    return {"max_workers": max_workers, "timeout_per_url": timeout_per_url}


__all__ = [
    "ValidationResult",
    "validate_categories_config",
    "validate_cities_config",
    "validate_email",
    "validate_list_length",
    "validate_non_empty_list",
    "validate_non_empty_string",
    "validate_parallel_config",
    "validate_phone",
    "validate_positive_float",
    "validate_positive_int",
    "validate_string_length",
]
