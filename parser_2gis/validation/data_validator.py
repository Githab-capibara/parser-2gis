"""
Модуль валидации данных.

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
from dataclasses import dataclass
from typing import Optional

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
    value: Optional[str] = None
    error: Optional[str] = None


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
            error=f"Телефон слишком короткий: {phone}. Ожидался формат: +7 (XXX) XXX-XX-XX",
        )

    if not _PHONE_PATTERN.match(phone):
        return ValidationResult(
            is_valid=False,
            error=f"Некорректный формат телефона: {phone}. Ожидался формат: +7 (XXX) XXX-XX-XX",
        )

    normalized = f"8 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:9]}-{cleaned[9:11]}"

    return ValidationResult(is_valid=True, value=normalized, error=None)


__all__ = [
    "ValidationResult",
    "validate_positive_int",
    "validate_positive_float",
    "validate_non_empty_string",
    "validate_string_length",
    "validate_non_empty_list",
    "validate_list_length",
    "validate_email",
    "validate_phone",
]
