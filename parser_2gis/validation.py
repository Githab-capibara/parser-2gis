"""
Модуль централизованной валидации данных.

Этот модуль содержит все функции валидации используемые в проекте
для устранения дублирования кода валидации.

Пример использования:
    >>> from parser_2gis.validation import validate_url, validate_positive_int
    >>> result = validate_url("https://2gis.ru/moscow")
    >>> print(result.is_valid)
    True

    >>> value = validate_positive_int(5, 1, 100, "--parser.max-retries")
    >>> print(value)
    5
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse


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
# ВАЛИДАЦИЯ URL
# =============================================================================


@lru_cache(maxsize=1024)
def validate_url(url: str) -> ValidationResult:
    """Валидирует URL на корректность формата и безопасность.

    Проверяет:
        - Схема (http или https)
        - Наличие сетевого расположения (netloc)
        - Общий формат URL
        - Блокировка localhost и внутренних IP адресов
        - Максимальная длина URL (2048 символов)

    Args:
        url: URL для валидации.

    Returns:
        ValidationResult с информацией о валидности URL.

    Example:
        >>> result = validate_url("https://2gis.ru/moscow")
        >>> if result.is_valid:
        ...     print(f"URL валиден: {result.value}")
        ... else:
        ...     print(f"Ошибка: {result.error}")

    Примечание:
        Результаты валидации кэшируются с помощью lru_cache (maxsize=1024)
        для ускорения повторных проверок тех же URL.
    """
    # Проверка максимальной длины URL (2048 символов - стандартный лимит)
    if len(url) > 2048:
        return ValidationResult(
            is_valid=False,
            error=f"Длина URL превышает максимальную (2048 символов). Текущая длина: {len(url)}",
        )

    try:
        result = urlparse(url)

        # Проверка схемы и netloc
        if not all([result.scheme in ("http", "https"), result.netloc]):
            return ValidationResult(
                is_valid=False,
                error="URL должен начинаться с http:// или https:// и содержать домен",
            )

        # Извлекаем хост для проверки на внутренние IP
        hostname = result.hostname
        if hostname is None:
            return ValidationResult(is_valid=False, error="URL должен содержать домен")

        # Проверяем, не является ли хост localhost
        if hostname.lower() in ("localhost", "127.0.0.1"):
            return ValidationResult(is_valid=False, error="Использование localhost запрещено")

        # Проверяем, не является ли хост IP адресом
        try:
            ip_addr = ipaddress.ip_address(hostname)
            # Проверяем на private и loopback адреса
            if ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_link_local:
                return ValidationResult(
                    is_valid=False, error=f"Использование private IP адресов запрещено ({hostname})"
                )
        except ValueError:
            # Это доменное имя - проверяем через socket.getaddrinfo
            import socket

            # Устанавливаем таймаут для DNS запросов (5 секунд)
            # Это предотвращает зависание при недоступности DNS сервера
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(5)  # 5 секунд на DNS запрос
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for _, _, _, _, sockaddr in addr_info:
                    try:
                        ip = ipaddress.ip_address(sockaddr[0])
                        if ip.is_private or ip.is_loopback or ip.is_link_local:
                            return ValidationResult(
                                is_valid=False,
                                error=f"Домен {hostname} разрешается в private IP ({sockaddr[0]})",
                            )
                    except ValueError:
                        continue
            except socket.gaierror:
                # Домен не разрешается - это нормально, может быть рабочим
                pass
            finally:
                # Восстанавливаем исходный таймаут
                socket.setdefaulttimeout(old_timeout)

        return ValidationResult(is_valid=True, value=url, error=None)

    except Exception as e:
        return ValidationResult(is_valid=False, error=f"Ошибка валидации URL: {e}")


def is_valid_url(url: str) -> bool:
    """Проверяет валидность URL (упрощённая версия).

    Args:
        url: URL для проверки.

    Returns:
        True если URL валиден, False иначе.

    Example:
        >>> is_valid_url("https://2gis.ru/moscow")
        True
        >>> is_valid_url("http://localhost:8080")
        False
    """
    result = validate_url(url)
    return result.is_valid


def clear_url_cache() -> None:
    """Очищает кэш валидации URL.

    Используется для сброса кэша lru_cache при необходимости
    повторной валидации ранее проверенных URL.

    Example:
        >>> validate_url("https://2gis.ru/moscow")
        >>> clear_url_cache()  # Очищает кэш
    """
    validate_url.cache_clear()


# =============================================================================
# ВАЛИДАЦИЯ ЧИСЛОВЫХ ЗНАЧЕНИЙ
# =============================================================================


def validate_positive_int(value: int, min_val: int, max_val: int, arg_name: str) -> int:
    """Валидирует положительное целое число в заданном диапазоне.

    ЛИМИТЫ ОТКЛЮЧЕНЫ - если max_val = float('inf'), проверка максимума отключена.

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
        ValueError: --parser.max-retries должен быть от 1 до 100 (получено 0)
    """
    if value < min_val:
        raise ValueError(f"{arg_name} должен быть не менее {min_val} (получено {value})")
    # ЛИМИТЫ ОТКЛЮЧЕНЫ - проверка максимума только если он не inf
    if max_val != float("inf") and value > max_val:
        raise ValueError(f"{arg_name} должен быть не более {max_val} (получено {value})")
    return value


def validate_positive_float(value: float, min_val: float, max_val: float, arg_name: str) -> float:
    """Валидирует положительное число с плавающей точкой в заданном диапазоне.

    ЛИМИТЫ ОТКЛЮЧЕНЫ - если max_val = float('inf'), проверка максимума отключена.

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
    # ЛИМИТЫ ОТКЛЮЧЕНЫ - проверка максимума только если он не inf
    if max_val != float("inf") and value > max_val:
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
# ВАЛИДАЦИЯ TELEFONOV
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
    # Очищаем телефон от лишних символов
    cleaned = re.sub(r"[\s\-()]", "", phone)

    if not cleaned:
        return ValidationResult(is_valid=False, error="Телефон не может быть пустым")

    # Проверяем формат
    if not _PHONE_PATTERN.match(phone):
        return ValidationResult(
            is_valid=False,
            error=f"Некорректный формат телефона: {phone}. Ожидался формат: +7 (XXX) XXX-XX-XX",
        )

    # Нормализуем к формату 8 (XXX) XXX-XX-XX
    normalized = f"8 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:9]}-{cleaned[9:11]}"

    return ValidationResult(is_valid=True, value=normalized, error=None)


# =============================================================================
# ЭКСПОРТИРУЕМЫЕ СИМВОЛЫ
# =============================================================================

__all__ = [
    "ValidationResult",
    "validate_url",
    "is_valid_url",
    "validate_positive_int",
    "validate_positive_float",
    "validate_non_empty_string",
    "validate_string_length",
    "validate_non_empty_list",
    "validate_list_length",
    "validate_email",
    "validate_phone",
]
