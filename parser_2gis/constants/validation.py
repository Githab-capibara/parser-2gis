"""Константы валидации для parser-2gis.

Этот модуль содержит константы связанные с валидацией:
- Лимиты для городов
- Пороги для mmap

Пример использования:
    >>> from parser_2gis.constants.validation import MAX_CITIES_COUNT, MAX_CITIES_FILE_SIZE
    >>> print(f"Максимальное количество городов: {MAX_CITIES_COUNT}")
"""

from __future__ import annotations

# =============================================================================
# ВАЛИДАЦИЯ ГОРОДОВ
# =============================================================================

# Максимальный размер файла городов
MAX_CITIES_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Максимальное количество городов
MAX_CITIES_COUNT: int = 1000

# Порог mmap для городов
MMAP_CITIES_THRESHOLD: int = 1 * 1024 * 1024  # 1 MB


# =============================================================================
# POLLING
# =============================================================================

# Интервал polling по умолчанию
DEFAULT_POLL_INTERVAL: float = 0.1

# Максимальный интервал polling
MAX_POLL_INTERVAL: float = 2.0

# Множитель экспоненциального backoff
EXPONENTIAL_BACKOFF_MULTIPLIER: int = 2


__all__ = [
    "DEFAULT_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    "MAX_CITIES_COUNT",
    "MAX_CITIES_FILE_SIZE",
    "MAX_POLL_INTERVAL",
    "MMAP_CITIES_THRESHOLD",
]
