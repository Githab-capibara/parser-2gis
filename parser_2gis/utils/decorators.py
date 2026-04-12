"""Модуль декораторов для ожидания завершения операций в parser-2gis.

Содержит декораторы для синхронного и асинхронного ожидания
завершения функций с поддержкой экспоненциальной задержки:
- wait_until_finished: синхронный декоратор ожидания
- async_wait_until_finished: асинхронный декоратор ожидания
- WaitConfig: конфигурация для декоратора wait_until_finished

Пример использования:
    >>> from parser_2gis.utils.decorators import wait_until_finished
    >>> @wait_until_finished(timeout=30, finished=lambda x: x > 0)
    ... def fetch_data() -> int:
    ...     return some_api_call()
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from functools import wraps

# ИСПРАВЛЕНИЕ #20: Используем ParamSpec и TypeVar для точной типизации декоратора
from typing import Any, ParamSpec, TypeVar

# ISSUE-041: Разрыв цикла imports — константы polling определены напрямую
# чтобы utils.decorators не зависел от constants (через parser.options -> utils)
_DEFAULT_POLL_INTERVAL_VALUE = 0.1
_MAX_POLL_INTERVAL_VALUE = 2.0
_EXPONENTIAL_BACKOFF_MULTIPLIER_VALUE = 2.0

# ИСПРАВЛЕНИЕ #20: ParamSpec для сохранения сигнатуры декорируемой функции
P = ParamSpec("P")
R = TypeVar("R")

# =============================================================================
# КОНСТАНТЫ ДЛЯ POLLING
# =============================================================================

DEFAULT_POLL_INTERVAL: float = _DEFAULT_POLL_INTERVAL_VALUE
"""Начальный интервал опроса в секундах (максимально ускорено)."""

MAX_POLL_INTERVAL: float = _MAX_POLL_INTERVAL_VALUE
"""Максимальный интервал опроса в секундах (максимально ускорено)."""

EXPONENTIAL_BACKOFF_MULTIPLIER: float = _EXPONENTIAL_BACKOFF_MULTIPLIER_VALUE
"""Множитель для экспоненциальной задержки."""

# Максимальный допустимый таймаут в секундах
# (24 часа — максимальное разумное время для одной операции)
MAX_TIMEOUT_SECONDS: int = 86400

# Максимальный допустимый интервал опроса в секундах
MAX_POLL_INTERVAL_LIMIT: float = 60.0


@dataclass
class WaitConfig:
    """Конфигурация для декоратора wait_until_finished.

    Attributes:
        timeout: Таймаут ожидания в секундах.
        finished: Функция-предикат для проверки завершения.
        throw_exception: Бросать ли исключение при таймауте.
        poll_interval: Начальный интервал опроса.
        max_retries: Максимальное количество попыток.

    """

    timeout: int | None = None
    finished: Callable[[Any], bool] | None = None
    throw_exception: bool = False
    poll_interval: float = DEFAULT_POLL_INTERVAL
    max_retries: int | None = None


# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ POLLING
# =============================================================================


def _check_timeout_expired(
    start_time: float, timeout: int | None, func_name: str, *, throw_exception: bool
) -> tuple[bool, Any]:
    """Проверяет, истёк ли таймаут.

    Args:
        start_time: Время начала выполнения.
        timeout: Таймаут в секундах.
        func_name: Имя функции.
        throw_exception: Бросать ли исключение.

    Returns:
        Кортеж (timeout_expired, result_or_none).

    """
    if timeout is not None and time.time() - start_time > timeout:
        timeout_msg = f"Превышено время ожидания для {func_name} ({timeout} сек)"
        if throw_exception:
            raise TimeoutError(timeout_msg)
        logger.warning(timeout_msg)
        return True, None
    return False, None


def _check_max_retries_exceeded(
    attempt_count: int, max_retries: int | None, func_name: str, *, throw_exception: bool
) -> tuple[bool, Any]:
    """Проверяет, превышено ли максимальное количество попыток.

    Args:
        attempt_count: Текущий счётчик попыток.
        max_retries: Максимальное количество попыток.
        func_name: Имя функции.
        throw_exception: Бросать ли исключение.

    Returns:
        Кортеж (retries_exceeded, result_or_none).

    """
    if max_retries is not None and attempt_count >= max_retries:
        retries_msg = (
            f"Превышено максимальное количество попыток для {func_name} ({max_retries} попыток)"
        )
        if throw_exception:
            raise TimeoutError(retries_msg)
        logger.warning(retries_msg)
        return True, None
    return False, None


def _update_poll_interval(
    *,
    use_exponential_backoff: bool,
    consecutive_failures: int,
    base_poll_interval: float,
    max_poll_interval: float,
) -> float:
    """Вычисляет следующий интервал опроса.

    Args:
        use_exponential_backoff: Использовать ли экспоненциальную задержку.
        consecutive_failures: Количество последовательных неудач.
        base_poll_interval: Базовый интервал опроса.
        max_poll_interval: Максимальный интервал опроса.

    Returns:
        Вычисленный интервал опроса.

    """
    if use_exponential_backoff and consecutive_failures > 0:
        return min(float(base_poll_interval * (2 ** (consecutive_failures - 1))), max_poll_interval)
    return base_poll_interval


def _handle_execution_error(
    error: Exception, func_name: str, attempt_count: int, consecutive_failures: int
) -> int:
    """Обрабатывает ошибку выполнения функции.

    Args:
        error: Произошедшее исключение.
        func_name: Имя функции.
        attempt_count: Текущий счётчик попыток.
        consecutive_failures: Текущий счётчик неудач.

    Returns:
        Обновлённый счётчик consecutive_failures.

    """
    if isinstance(error, TimeoutError):
        raise error
    if isinstance(error, (MemoryError, OSError)):
        error_type = "MemoryError" if isinstance(error, MemoryError) else "OSError"
        logger.error(
            "Критическая ошибка %s при выполнении функции %s (попытка %d): %s",
            error_type,
            func_name,
            attempt_count,
            error,
        )
        raise error
    if isinstance(error, (RuntimeError, ValueError, TypeError)):
        logger.debug(
            "Ошибка при выполнении функции %s (попытка %d): %s", func_name, attempt_count, error
        )
        return consecutive_failures + 1
    return consecutive_failures


def _default_predicate(value: Any) -> bool:
    """Предикат по умолчанию для проверки результата.

    Args:
        value: Значение для проверки.

    Returns:
        True если значение истинно, False иначе.

    """
    return bool(value)


# =============================================================================
# ДЕКОРАТОРЫ
# =============================================================================


def wait_until_finished(
    timeout: float | None = None,
    finished: Callable[[Any], bool] | None = None,
    *,
    throw_exception: bool = True,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    use_exponential_backoff: bool = True,
    max_poll_interval: float = MAX_POLL_INTERVAL,
    max_retries: int | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени.

    ИСПРАВЛЕНИЕ 18:
    - Добавлен максимальный таймаут (timeout параметр)
    - Используется threading.Event.wait() вместо time.sleep() для возможности прерывания
    - Добавлен счётчик попыток с максимумом (max_retries)
    - Выбрасывает TimeoutError при превышении таймаута или количества попыток

    Оптимизация:
    - Экспоненциальная задержка снижает нагрузку на CPU
    - Увеличенный начальный poll_interval для быстрых операций

    Args:
        timeout: Максимальное время ожидания в секундах.
        finished: Предикат для успешного результата обёрнутой функции.
        throw_exception: Выбрасывать ли `TimeoutError`.
        poll_interval: Начальный интервал опроса результата в секундах.
        use_exponential_backoff: Использовать экспоненциальную задержку.
        max_poll_interval: Максимальный интервал опроса при экспоненциальной задержке.
        max_retries: Максимальное количество попыток (None для неограниченного).

    Returns:
        Декоратор для функции с ожиданием завершения.

    Raises:
        TimeoutError: Если истекло время ожидания или количество попыток и throw_exception=True.
        ValueError: Если параметры некорректны.

    Пример:
        >>> @wait_until_finished(timeout=30, finished=lambda x: x > 0, max_retries=100)
        ... def fetch_data() -> int:
        ...     return some_api_call()

    """
    # ISSUE-099: Валидация timeout на отрицательное значение
    if timeout is not None and timeout <= 0:
        raise ValueError(f"timeout должен быть положительным числом: {timeout}")

    # ISSUE-100: Валидация max_poll_interval на положительное значение
    if max_poll_interval <= 0:
        raise ValueError(f"max_poll_interval должен быть положительным числом: {max_poll_interval}")

    if poll_interval <= 0:
        raise ValueError(f"poll_interval должен быть положительным числом: {poll_interval}")
    if max_retries is not None and max_retries <= 0:
        raise ValueError(f"max_retries должен быть положительным числом: {max_retries}")
    if poll_interval > max_poll_interval:
        raise ValueError(
            f"poll_interval ({poll_interval}) не может быть больше "
            f"max_poll_interval ({max_poll_interval})"
        )

    # ISSUE-099: Дополнительная проверка timeout на разумность (максимум 24 часа)
    if timeout is not None and timeout > MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"timeout не должен превышать {MAX_TIMEOUT_SECONDS} секунд "
            f"(24 часа), получено {timeout}"
        )

    # ISSUE-100: Дополнительная проверка max_poll_interval на разумность (максимум 60 секунд)
    if max_poll_interval > MAX_POLL_INTERVAL_LIMIT:
        raise ValueError(
            f"max_poll_interval не должен превышать "
            f"{MAX_POLL_INTERVAL_LIMIT} секунд, получено {max_poll_interval}"
        )

    # Сохраняем значения декоратора в замыкании
    decorator_timeout = timeout
    decorator_finished = finished
    decorator_throw_exception = throw_exception
    decorator_poll_interval = poll_interval
    decorator_max_retries = max_retries

    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        """Внешняя функция декоратора, принимающая декорируемый метод."""

        @wraps(func)
        def inner(
            *args: Any,
            # Переопределение параметров на уровне вызова
            override_timeout: int | None = None,
            override_finished: Callable[[Any], bool] | None = None,
            override_throw_exception: bool | None = None,
            override_poll_interval: float | None = None,
            override_max_retries: int | None = None,
            **kwargs: Any,
        ) -> Any:
            """Обёртка вокруг функции с ожиданием завершения операции."""
            # Группировка эффективных параметров в dataclass
            effective_config = WaitConfig(
                timeout=(override_timeout if override_timeout is not None else decorator_timeout),
                finished=(
                    override_finished
                    if override_finished is not None
                    else decorator_finished or _default_predicate
                ),
                throw_exception=(
                    override_throw_exception
                    if override_throw_exception is not None
                    else decorator_throw_exception
                ),
                poll_interval=(
                    override_poll_interval
                    if override_poll_interval is not None
                    else decorator_poll_interval
                ),
                max_retries=(
                    override_max_retries
                    if override_max_retries is not None
                    else decorator_max_retries
                ),
            )

            result: Any = None
            start_time = time.time()
            current_poll_interval = effective_config.poll_interval
            consecutive_failures = 0  # Счётчик неудач для экспоненциальной задержки
            attempt_count = 0  # ИСПРАВЛЕНИЕ 18: Счётчик попыток
            max_attempts = effective_config.max_retries or float(
                "inf"
            )  # ISSUE-151: Явный лимит попыток

            # ИСПРАВЛЕНИЕ 18: Создаём Event для возможности прерывания
            stop_event = threading.Event()

            # ISSUE-151: Явное условие выхода - цикл по attempt_count вместо while True
            while attempt_count < max_attempts:
                # Проверяем таймаут
                timeout_expired, timeout_result = _check_timeout_expired(
                    start_time=start_time,
                    timeout=effective_config.timeout,
                    func_name=func.__name__,
                    throw_exception=effective_config.throw_exception,
                )
                if timeout_expired:
                    return timeout_result

                # Проверяем максимальное количество попыток
                retries_exceeded, retries_result = _check_max_retries_exceeded(
                    attempt_count=attempt_count,
                    max_retries=effective_config.max_retries,
                    func_name=func.__name__,
                    throw_exception=effective_config.throw_exception,
                )
                if retries_exceeded:
                    return retries_result

                attempt_count += 1

                try:
                    result = func(*args, **kwargs)
                    if effective_config.finished is not None and effective_config.finished(result):
                        return result
                    consecutive_failures = 0  # Сброс при успехе
                except Exception as exc:
                    consecutive_failures = _handle_execution_error(
                        error=exc,
                        func_name=func.__name__,
                        attempt_count=attempt_count,
                        consecutive_failures=consecutive_failures,
                    )

                # Экспоненциальная задержка для снижения нагрузки на CPU
                current_poll_interval = _update_poll_interval(
                    use_exponential_backoff=use_exponential_backoff,
                    consecutive_failures=consecutive_failures,
                    base_poll_interval=effective_config.poll_interval,
                    max_poll_interval=max_poll_interval,
                )

                # Проверяем stop_event перед ожиданием
                if stop_event.is_set():
                    logger.warning("Получен сигнал остановки для %s", func.__name__)
                    return result

                # Ждём с использованием Event.wait() вместо time.sleep()
                stopped = stop_event.wait(timeout=current_poll_interval)
                if stopped:
                    logger.warning(
                        "Ожидание прервано для %s (попыток: %d)", func.__name__, attempt_count
                    )
                    return result

            # Явный return None для соответствия всем путям выполнения
            return None

        return inner

    return outer


def async_wait_until_finished(
    timeout: int | None = None,
    finished: Callable[[Any], bool] | None = None,
    *,
    throw_exception: bool = True,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    use_exponential_backoff: bool = True,
    max_poll_interval: float = MAX_POLL_INTERVAL,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """Async версия декоратора wait_until_finished для asyncio.

    - Использует asyncio.sleep() вместо time.sleep()
    - Совместим с asyncio event loop
    - Не блокирует event loop при ожидании

    ИСПРАВЛЕНИЕ #20: Использует ParamSpec P и TypeVar R для сохранения
    сигнатуры декорируемой async функции.

    Args:
        timeout: Максимальное время ожидания в секундах.
        finished: Предикат для успешного результата.
        throw_exception: Выбрасывать ли TimeoutError.
        poll_interval: Начальный интервал опроса в секундах.
        use_exponential_backoff: Использовать экспоненциальную задержку.
        max_poll_interval: Максимальный интервал опроса.

    Returns:
        Декоратор для async функции с ожиданием завершения.

    Raises:
        TimeoutError: Если истекло время ожидания и throw_exception=True.

    Example:
        @async_wait_until_finished(timeout=30)
        async def my_async_function():
            return await some_async_operation()

    """
    decorator_timeout = timeout
    decorator_finished = finished
    decorator_throw_exception = throw_exception
    decorator_poll_interval = poll_interval

    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        """Внешняя функция асинхронного декоратора, принимающая декорируемый метод."""

        @wraps(func)
        async def inner(
            *args: Any,
            override_timeout: int | None = None,
            override_finished: Callable[[Any], bool] | None = None,
            override_throw_exception: bool | None = None,
            override_poll_interval: float | None = None,
            **kwargs: Any,
        ) -> Any:
            """Асинхронная обёртка вокруг функции с ожиданием завершения операции."""
            # Приоритет: override_* > значения из декоратора
            effective_timeout = (
                override_timeout if override_timeout is not None else decorator_timeout
            )
            effective_finished = (
                override_finished
                if override_finished is not None
                else decorator_finished or _default_predicate
            )
            effective_throw_exception = (
                override_throw_exception
                if override_throw_exception is not None
                else decorator_throw_exception
            )
            effective_poll_interval = (
                override_poll_interval
                if override_poll_interval is not None
                else decorator_poll_interval
            )

            start_time = asyncio.get_running_loop().time()
            current_poll_interval = effective_poll_interval
            result = None

            while True:
                # Проверяем таймаут
                if effective_timeout is not None:
                    elapsed = asyncio.get_running_loop().time() - start_time
                    if elapsed > effective_timeout and effective_throw_exception:
                        raise TimeoutError(
                            f"Функция {func.__name__} не завершилась за {effective_timeout} секунд"
                        )
                    elif elapsed > effective_timeout:
                        return None

                # Вызываем функцию
                result = await func(*args, **kwargs)

                # Проверяем результат
                if effective_finished(result):
                    return result

                # Ждём следующий опрос
                await asyncio.sleep(current_poll_interval)

                # Увеличиваем интервал при экспоненциальной задержке
                if use_exponential_backoff:
                    current_poll_interval = min(
                        current_poll_interval * EXPONENTIAL_BACKOFF_MULTIPLIER, max_poll_interval
                    )

        return inner

    return outer


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "DEFAULT_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
    "MAX_POLL_INTERVAL",
    "async_wait_until_finished",
    "wait_until_finished",
]
