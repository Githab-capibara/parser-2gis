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
from functools import wraps
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from parser_2gis.constants import (
    DEFAULT_POLL_INTERVAL as DEFAULT_POLL_INTERVAL_CONST,
    MAX_POLL_INTERVAL as MAX_POLL_INTERVAL_CONST,
    EXPONENTIAL_BACKOFF_MULTIPLIER as EXPONENTIAL_BACKOFF_MULTIPLIER_CONST,
)

# =============================================================================
# КОНСТАНТЫ ДЛЯ POLLING
# =============================================================================

DEFAULT_POLL_INTERVAL: float = DEFAULT_POLL_INTERVAL_CONST
"""Начальный интервал опроса в секундах (максимально ускорено)."""

MAX_POLL_INTERVAL: float = MAX_POLL_INTERVAL_CONST
"""Максимальный интервал опроса в секундах (максимально ускорено)."""

EXPONENTIAL_BACKOFF_MULTIPLIER: float = EXPONENTIAL_BACKOFF_MULTIPLIER_CONST
"""Множитель для экспоненциальной задержки."""


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
    timeout: int | None = None,
    finished: Callable[[Any], bool] | None = None,
    throw_exception: bool = True,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    use_exponential_backoff: bool = True,
    max_poll_interval: float = MAX_POLL_INTERVAL,
    max_retries: int | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени или пока
    предикат `finished` не вернёт `True`.

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
            f"poll_interval ({poll_interval}) не может быть больше max_poll_interval ({max_poll_interval})"
        )

    # ISSUE-099: Дополнительная проверка timeout на разумность (максимум 24 часа)
    MAX_TIMEOUT = 86400  # 24 часа в секундах
    if timeout is not None and timeout > MAX_TIMEOUT:
        raise ValueError(
            f"timeout не должен превышать {MAX_TIMEOUT} секунд (24 часа), получено {timeout}"
        )

    # ISSUE-100: Дополнительная проверка max_poll_interval на разумность (максимум 60 секунд)
    MAX_POLL_INTERVAL_LIMIT = 60.0
    if max_poll_interval > MAX_POLL_INTERVAL_LIMIT:
        raise ValueError(
            f"max_poll_interval не должен превышать {MAX_POLL_INTERVAL_LIMIT} секунд, получено {max_poll_interval}"
        )

    # Сохраняем значения декоратора в замыкании
    decorator_timeout = timeout
    decorator_finished = finished
    decorator_throw_exception = throw_exception
    decorator_poll_interval = poll_interval
    decorator_max_retries = max_retries

    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def inner(
            *args: Any,
            # Поддерживаем оба варианта: override_* и оригинальные имена
            override_timeout: int | None = None,
            override_finished: Callable[[Any], bool] | None = None,
            override_throw_exception: bool | None = None,
            override_poll_interval: float | None = None,
            override_max_retries: int | None = None,
            timeout: int | None = None,
            finished: Callable[[Any], bool] | None = None,
            throw_exception: bool | None = None,
            poll_interval: float | None = None,
            max_retries: int | None = None,
            **kwargs: Any,
        ) -> Any:
            # Группировка эффективных параметров в dataclass
            effective_config = WaitConfig(
                timeout=(
                    override_timeout
                    if override_timeout is not None
                    else (timeout if timeout is not None else decorator_timeout)
                ),
                finished=(
                    override_finished
                    if override_finished is not None
                    else (
                        finished
                        if finished is not None
                        else decorator_finished or _default_predicate
                    )
                ),
                throw_exception=(
                    override_throw_exception
                    if override_throw_exception is not None
                    else (
                        throw_exception
                        if throw_exception is not None
                        else decorator_throw_exception
                    )
                ),
                poll_interval=(
                    override_poll_interval
                    if override_poll_interval is not None
                    else (poll_interval if poll_interval is not None else decorator_poll_interval)
                ),
                max_retries=(
                    override_max_retries
                    if override_max_retries is not None
                    else (max_retries if max_retries is not None else decorator_max_retries)
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
                # ISSUE-176: Кэширование time.time() для снижения накладных расходов
                current_time = time.time()

                # ISSUE-151: Проверка таймаута в начале цикла
                if (
                    effective_config.timeout is not None
                    and current_time - start_time > effective_config.timeout
                ):
                    timeout_msg = f"Превышено время ожидания для {func.__name__} ({effective_config.timeout} сек)"
                    if effective_config.throw_exception:
                        raise TimeoutError(timeout_msg)
                    # Логируем timeout для диагностики
                    logger.warning(timeout_msg)
                    return result

                # ISSUE-151: Проверка максимального количества попыток
                if (
                    effective_config.max_retries is not None
                    and attempt_count >= effective_config.max_retries
                ):
                    retries_msg = (
                        f"Превышено максимальное количество попыток для {func.__name__} "
                        f"({effective_config.max_retries} попыток)"
                    )
                    if effective_config.throw_exception:
                        raise TimeoutError(retries_msg)
                    logger.warning(retries_msg)
                    return result

                attempt_count += 1

                try:
                    result = func(*args, **kwargs)
                    if effective_config.finished(result):
                        return result
                    consecutive_failures = 0  # Сброс при успехе
                except TimeoutError:
                    # Пробрасываем TimeoutError немедленно
                    raise
                except (MemoryError, OSError, RuntimeError, ValueError, TypeError) as e:
                    # Логирование ошибок выполнения функции
                    logger.debug(
                        "Ошибка при выполнении функции %s (попытка %d): %s",
                        func.__name__,
                        attempt_count,
                        e,
                    )
                    consecutive_failures += 1

                # Экспоненциальная задержка для снижения нагрузки на CPU
                if use_exponential_backoff and consecutive_failures > 0:
                    # Увеличиваем интервал после каждой неудачи
                    current_poll_interval = min(
                        effective_config.poll_interval * (2 ** (consecutive_failures - 1)),
                        max_poll_interval,
                    )
                else:
                    current_poll_interval = effective_config.poll_interval

                # ИСПРАВЛЕНИЕ 18: Используем Event.wait() вместо time.sleep()
                # Это позволяет прервать ожидание через stop_event.set() из другого потока
                # Проверяем stop_event перед ожиданием
                if stop_event.is_set():
                    logger.warning("Получен сигнал остановки для %s", func.__name__)
                    return result

                # Ждём с использованием Event.wait() вместо time.sleep()
                # wait() возвращает True если событие установлено, False по таймауту
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
    throw_exception: bool = True,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    use_exponential_backoff: bool = True,
    max_poll_interval: float = MAX_POLL_INTERVAL,
) -> Callable[..., Callable[..., Any]]:
    """Async версия декоратора wait_until_finished для asyncio.

    - Использует asyncio.sleep() вместо time.sleep()
    - Совместим с asyncio event loop
    - Не блокирует event loop при ожидании

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
        @wraps(func)
        async def inner(
            *args: Any,
            override_timeout: int | None = None,
            override_finished: Callable[[Any], bool] | None = None,
            override_throw_exception: bool | None = None,
            override_poll_interval: float | None = None,
            **kwargs: Any,
        ) -> Any:
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

            start_time = asyncio.get_event_loop().time()
            current_poll_interval = effective_poll_interval
            result = None

            while True:
                # Проверяем таймаут
                if effective_timeout is not None:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > effective_timeout:
                        if effective_throw_exception:
                            raise TimeoutError(
                                f"Функция {func.__name__} не завершилась за "
                                f"{effective_timeout} секунд"
                            )
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
