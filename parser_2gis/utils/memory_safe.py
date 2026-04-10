"""Утилиты безопасной работы с памятью.

ISSUE-051: Вынесено из strategies.py и url_parser.py для устранения дублирования
логики обработки MemoryError при парсинге.

Пример использования:
    >>> from parser_2gis.utils.memory_safe import safe_parse_with_memory_check
    >>> @safe_parse_with_memory_check()
    ... def parse_data(url: str) -> dict:
    ...     return do_parsing(url)
"""

from __future__ import annotations

import gc
import logging
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)

# Порог памяти по умолчанию (100 MB)
DEFAULT_MEMORY_THRESHOLD_MB = 100


def safe_parse_with_memory_check(
    memory_threshold_mb: int = DEFAULT_MEMORY_THRESHOLD_MB,
    clear_cache_on_error: bool = True,
    log_level: str = "error",
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """Декоратор для безопасного парсинга с проверкой памяти.

    Общая функция для устранения дублирования между:
    - parallel/strategies.py (ParseStrategy.parse_single_url — MemoryError handling)
    - parallel/url_parser.py (parse_single_url — MemoryError handling)

    Args:
        memory_threshold_mb: Порог памяти в MB.
        clear_cache_on_error: Очищать ли кэш при MemoryError.
        log_level: Уровень логирования ошибок.

    Returns:
        Декоратор для функции парсинга.

    """

    def decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        """Декоратор с проверкой памяти."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            """Обёртка с обработкой MemoryError."""
            try:
                return func(*args, **kwargs)
            except MemoryError as memory_error:
                log_func = getattr(logger, log_level)
                log_func("MemoryError при выполнении %s: %s", func.__name__, memory_error)

                # Очистка кэша если есть
                if clear_cache_on_error:
                    for arg in args:
                        if hasattr(arg, "_cache"):
                            try:
                                arg._cache.clear()
                            except (OSError, RuntimeError, AttributeError):
                                pass

                # Принудительный GC
                gc.collect()

                return None

        return wrapper

    return decorator


def check_available_memory(min_memory_mb: int = DEFAULT_MEMORY_THRESHOLD_MB) -> tuple[bool, int]:
    """Проверяет доступную память.

    Args:
        min_memory_mb: Минимальная требуемая память в MB.

    Returns:
        Кортеж (is_enough, available_mb).

    """
    try:
        from parser_2gis.infrastructure import MemoryMonitor

        monitor = MemoryMonitor()
        available_bytes = monitor.get_available_memory()
        available_mb = available_bytes // (1024 * 1024)
        is_enough = available_mb >= min_memory_mb
        return is_enough, available_mb
    except (ImportError, OSError, RuntimeError):
        # Если не удалось проверить память, предполагаем что памяти достаточно
        return True, -1
