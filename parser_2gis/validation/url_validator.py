"""
Модуль валидации URL.

Содержит функции для валидации URL на корректность формата и безопасность.

Пример использования:
    >>> from parser_2gis.validation.url_validator import validate_url, is_valid_url
    >>> result = validate_url("https://2gis.ru/moscow")
    >>> print(result.is_valid)
    True
    >>> is_valid_url("https://2gis.ru/moscow")
    True
"""

from __future__ import annotations

import ipaddress
import socket
from functools import lru_cache
from urllib.parse import urlparse

from .data_validator import ValidationResult

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


__all__ = ["validate_url", "is_valid_url", "clear_url_cache"]
