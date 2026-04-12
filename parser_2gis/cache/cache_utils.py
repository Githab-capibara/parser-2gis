"""Модуль вспомогательных функций для кэширования.

Предоставляет функции для:
- Хеширования URL
- Валидации хешей
- Вычисления CRC32 checksum
- Расчёта размера кэша

ISSUE-004: Выделено из CacheManager для соблюдения SRP.
"""

from __future__ import annotations

import functools
import hashlib
import sqlite3
import zlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from parser_2gis.constants import SHA256_HASH_LENGTH
from parser_2gis.logger.logger import logger as app_logger

if TYPE_CHECKING:
    from pathlib import Path


@functools.lru_cache(maxsize=1024)
def compute_crc32_cached(_data_json_hash: str, data_json: str) -> int:
    """Вычисляет CRC32 checksum с кэшированием.

    ISSUE-084: Уменьшен maxsize с 8192 до 1024 для снижения потребления памяти.

    Кэширование основано на хеше данных - одинаковые данные будут
    иметь одинаковый checksum без повторных вычислений.

    Args:
        _data_json_hash: Хеш данных (SHA256) — используется как часть ключа кэша.
        data_json: JSON строка данных.

    Returns:
        CRC32 checksum.

    """
    return zlib.crc32(data_json.encode("utf-8")) & 0xFFFFFFFF


def compute_data_json_hash(data_json: str) -> str:
    """Вычисляет SHA256 хеш от JSON строки.

    Args:
        data_json: JSON строка данных.

    Returns:
        SHA256 хеш в виде шестнадцатеричной строки.

    """
    return hashlib.sha256(data_json.encode("utf-8")).hexdigest()


def hash_url(url: str) -> str:
    """Хеширование URL.

    Вычисляет SHA256 хеш от указанного URL для использования
    в качестве ключа в базе данных кэша.

    Args:
        url: URL для хеширования. Должен быть непустой строкой.

    Returns:
        SHA256 хеш URL в виде шестнадцатеричной строки.

    Raises:
        ValueError: Если URL является None или пустой строкой.
        TypeError: Если URL не является строкой.

    """
    if url is None:
        error_msg = "URL не может быть None"
        raise TypeError(error_msg)

    if not isinstance(url, str):
        error_msg = f"URL должен быть строкой, получен {type(url).__name__}"
        raise TypeError(error_msg)

    if not url.strip():
        error_msg = "URL не может быть пустой строкой"
        raise ValueError(error_msg)

    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def validate_hash(hash_val: str) -> bool:
    """Валидация хеша.

    Проверяет, что хеш имеет корректный формат:
    - Длина ровно 64 символа (SHA256 hex)
    - Содержит только шестнадцатеричные символы (0-9, a-f)

    Args:
        hash_val: Хеш для валидации.

    Returns:
        True если хеш корректен, False иначе.

    """
    if len(hash_val) != SHA256_HASH_LENGTH:
        return False
    try:
        int(hash_val, 16)
    except ValueError:
        return False
    else:
        return True


def get_cache_size_mb(cache_file: Path, conn: sqlite3.Connection | None = None) -> float:
    """Получает размер кэша в мегабайтах.

    Args:
        cache_file: Путь к файлу кэша.
        conn: SQLite соединение (опционально, для проверки целостности).

    Returns:
        Размер кэша в мегабайтах.

    """
    try:
        if not cache_file.exists():
            return 0.0

        cache_size_bytes = cache_file.stat().st_size
        cache_size_mb = cache_size_bytes / (1024 * 1024)

        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA quick_check(1)")
                cursor.close()
            except sqlite3.Error:
                app_logger.warning("База данных кэша может быть повреждена")

        return cache_size_mb
    except OSError as os_error:
        app_logger.warning("Ошибка при получении размера кэша: %s", os_error)
        return 0.0


def parse_expires_at(expires_at_str: str) -> datetime | None:
    """Парсит строку даты истечения кэша.

    Args:
        expires_at_str: Строка даты в формате ISO.

    Returns:
        datetime объект или None при ошибке парсинга.

    """
    try:
        return datetime.fromisoformat(expires_at_str)
    except ValueError:
        app_logger.debug("Некорректный формат даты в кэше: %s", expires_at_str)
        return None


def is_cache_expired(expires_at: datetime | None) -> bool:
    """Проверяет истёк ли кэш.

    Args:
        expires_at: Время истечения кэша (datetime).

    Returns:
        True если кэш истёк, False иначе.

    """
    if expires_at is None:
        return True

    # Используем timezone-aware datetime
    return datetime.now(tz=UTC) > expires_at


__all__ = [
    "compute_crc32_cached",
    "compute_data_json_hash",
    "get_cache_size_mb",
    "hash_url",
    "is_cache_expired",
    "parse_expires_at",
    "validate_hash",
]
