"""Модуль повторных попыток (retry logic) для parser-2gis.

Предоставляет универсальные декораторы и функции для повторного выполнения операций:
- retry_with_backoff: декоратор с экспоненциальной задержкой
- retry_with_fixed_delay: декоратор с фиксированной задержкой
- retry_with_jitter: декоратор со случайной задержкой
- retry_with_tenacity: декоратор с использованием tenacity (если доступна)
- is_tenacity_available: проверка доступности tenacity
- RetryError: исключение при исчерпании попыток

Пример использования:
    >>> from parser_2gis.utils.retry import retry_with_backoff
    >>> @retry_with_backoff(max_attempts=3, delay=1.0)
    ... def unstable_operation():
    ...     # операция которая может упасть
    ...     pass
"""

from __future__ import annotations

import functools
import random
import time
from typing import Any, TypeVar
from collections.abc import Callable

from parser_2gis.logger.logger import logger

# Тип для декорируемых функций
F = TypeVar("F", bound=Callable[..., Any])

# Типы исключений которые можно retry
RetryableException = type[Exception] | tuple[type[Exception], ...]

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# Максимальная задержка по умолчанию для retry стратегий (секунды)
DEFAULT_MAX_RETRY_DELAY: float = 60.0


class RetryError(Exception):
    """Исключение при исчерпании попыток повторения."""

    def __init__(
        self, message: str, last_error: Exception | None = None, attempts: int = 0
    ) -> None:
        """Инициализирует исключение.

        Args:
            message: Сообщение об ошибке.
            last_error: Последнее исключение.
            attempts: Количество попыток.

        """
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


def retry_with_backoff(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = DEFAULT_MAX_RETRY_DELAY,
    jitter: bool = True,
    exceptions: RetryableException = Exception,
    logger_name: str | None = None,
) -> Callable[[F], F]:
    """Декоратор для повторных попыток с экспоненциальной задержкой.

    Args:
        max_attempts: Максимальное количество попыток.
        delay: Начальная задержка в секундах.
        backoff_factor: Множитель задержки (экспоненциальный рост).
        max_delay: Максимальная задержка в секундах.
        jitter: Добавлять ли случайную задержку (для предотвращения thundering herd).
        exceptions: Тип или кортеж типов исключений для обработки.
        logger_name: Имя логгера (по умолчанию используется logger).

    Returns:
        Декоратор для функции.

    Example:
        >>> @retry_with_backoff(max_attempts=3, delay=0.5, exceptions=(TimeoutError,))
        ... def fetch_data(url):
        ...     # сетевой запрос
        ...     pass

    """
    log_func = logger
    if logger_name:
        import logging

        log_func = logging.getLogger(logger_name)

    def decorator(func: F) -> F:
        """Декоратор для функции."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Обертка для повторных попыток."""
            current_delay = delay
            func_name = func.__name__

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:  # type: ignore[misc]
                    if attempt < max_attempts:
                        # Вычисляем задержку с jitter
                        actual_delay = current_delay
                        if jitter:
                            # Добавляем случайность от 0% до 50% от задержки
                            actual_delay = current_delay * (1 + random.uniform(0, 0.5))

                        log_func.warning(
                            "Попытка %d/%d не удалась для %s: %s. Повтор через %.2f сек...",
                            attempt,
                            max_attempts,
                            func_name,
                            e,
                            actual_delay,
                        )

                        time.sleep(actual_delay)

                        # Увеличиваем задержку для следующей попытки (экспоненциальный backoff)
                        current_delay = min(current_delay * backoff_factor, max_delay)
                    else:
                        log_func.error(
                            "Исчерпаны попытки повторения для %s после %d попыток: %s",
                            func_name,
                            max_attempts,
                            e,
                        )
                        raise RetryError(
                            f"Исчерпаны попытки повторения ({max_attempts}) для {func_name}",
                            last_error=e,
                            attempts=attempt,
                        ) from e

        return wrapper  # type: ignore[return-value]

    return decorator


def retry_with_fixed_delay(
    max_attempts: int = 3, delay: float = 1.0, exceptions: RetryableException = Exception
) -> Callable[[F], F]:
    """Декоратор для повторных попыток с фиксированной задержкой.

    Использует фиксированную задержку между попытками без экспоненциального роста.
    Подходит для операций с предсказуемым временем восстановления.

    Args:
        max_attempts: Максимальное количество попыток (по умолчанию 3).
        delay: Фиксированная задержка в секундах между попытками (по умолчанию 1.0).
        exceptions: Тип или кортеж типов исключений для обработки (по умолчанию Exception).

    Returns:
        Декоратор для функции.

    Example:
        >>> @retry_with_fixed_delay(max_attempts=5, delay=0.5, exceptions=(TimeoutError,))
        ... def fetch_data(url):
        ...     # сетевой запрос с фиксированной задержкой между попытками
        ...     pass

    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        delay=delay,
        backoff_factor=1.0,  # Фиксированная задержка
        max_delay=delay,
        jitter=False,
        exceptions=exceptions,
    )


def retry_with_jitter(
    max_attempts: int = 3,
    min_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: RetryableException = Exception,
) -> Callable[[F], F]:
    """Декоратор для повторных попыток со случайной задержкой.

    Использует случайную задержку между min_delay и max_delay для предотвращения
    thundering herd problem при одновременном выполнении множества операций.

    Args:
        max_attempts: Максимальное количество попыток (по умолчанию 3).
        min_delay: Минимальная задержка в секундах (по умолчанию 1.0).
        max_delay: Максимальная задержка в секундах (по умолчанию 10.0).
        exceptions: Тип или кортеж типов исключений для обработки (по умолчанию Exception).

    Returns:
        Декоратор для функции.

    Example:
        >>> @retry_with_jitter(max_attempts=5, min_delay=0.5, max_delay=2.0)
        ... def api_call():
        ...     # API вызов со случайной задержкой для предотвращения thundering herd
        ...     pass

    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:  # type: ignore[misc]
                    if attempt < max_attempts:
                        # Случайная задержка между min_delay и max_delay
                        actual_delay = random.uniform(min_delay, max_delay)
                        logger.warning(
                            "Попытка %d/%d не удалась для %s: %s. Повтор через %.2f сек...",
                            attempt,
                            max_attempts,
                            func_name,
                            e,
                            actual_delay,
                        )
                        time.sleep(actual_delay)
                    else:
                        logger.error(
                            "Исчерпаны попытки повторения для %s после %d попыток: %s",
                            func_name,
                            max_attempts,
                            e,
                        )
                        raise RetryError(
                            f"Исчерпаны попытки повторения ({max_attempts}) для {func_name}",
                            last_error=e,
                            attempts=attempt,
                        ) from e

        return wrapper  # type: ignore[return-value]

    return decorator


# Проверка доступности tenacity
_TENACITY_AVAILABLE = False
try:
    import tenacity as _tenacity  # noqa: F401

    _TENACITY_AVAILABLE = True
except ImportError:
    pass


def retry_with_tenacity(
    max_attempts: int = 3,
    delay: float = 1.0,
    max_delay: float = DEFAULT_MAX_RETRY_DELAY,
    exceptions: RetryableException = Exception,
) -> Callable[[F], F]:
    """Декоратор с использованием tenacity (если доступна).

    Использует библиотеку tenacity для более продвинутой обработки повторных попыток.
    Требует установленной библиотеки tenacity.

    Args:
        max_attempts: Максимальное количество попыток (по умолчанию 3).
        delay: Начальная задержка в секундах (по умолчанию 1.0).
        max_delay: Максимальная задержка в секундах (по умолчанию DEFAULT_MAX_RETRY_DELAY).
        exceptions: Тип или кортеж типов исключений для обработки (по умолчанию Exception).

    Returns:
        Декоратор для функции.

    Raises:
        ImportError: Если tenacity не установлена.

    Example:
        >>> @retry_with_tenacity(max_attempts=5, delay=0.5, exceptions=(ConnectionError,))
        ... def network_request():
        ...     # сетевой запрос с использованием tenacity
        ...     pass

    """
    if not _TENACITY_AVAILABLE:
        raise ImportError(
            "tenacity не установлена. Установите: pip install tenacity "
            "или используйте retry_with_backoff"
        )

    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

    def decorator(func: F) -> F:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=delay, max=max_delay),
            retry=retry_if_exception_type(exceptions),  # type: ignore[arg-type]
            reraise=True,
        )
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def is_tenacity_available() -> bool:
    """Проверяет доступность tenacity.

    Returns:
        True если tenacity доступна, False иначе.

    Example:
        >>> if is_tenacity_available():
        ...     print("tenacity установлена, можно использовать retry_with_tenacity")
        ... else:
        ...     print("tenacity не установлена, используйте retry_with_backoff")

    """
    return _TENACITY_AVAILABLE


__all__ = [
    "RetryError",
    "is_tenacity_available",
    "retry_with_backoff",
    "retry_with_fixed_delay",
    "retry_with_jitter",
    "retry_with_tenacity",
]
