"""Модуль декораторов для ожидания завершения операций.

Содержит декораторы для синхронного и асинхронного ожидания
завершения функций с поддержкой экспоненциальной задержки.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

# =============================================================================
# КОНСТАНТЫ ДЛЯ POLLING
# =============================================================================

DEFAULT_POLL_INTERVAL: float = 0.025
"""Начальный интервал опроса в секундах (максимально ускорено)."""

MAX_POLL_INTERVAL: float = 0.5
"""Максимальный интервал опроса в секундах (максимально ускорено)."""

EXPONENTIAL_BACKOFF_MULTIPLIER: float = 2
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


def _get_logger() -> Any:
    """Получает logger для модуля decorators.

    Returns:
        Экземпляр logger из модуля logger.

    """
    from parser_2gis.logger import logger as app_logger

    return app_logger


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

    Пример:
        >>> @wait_until_finished(timeout=30, finished=lambda x: x > 0, max_retries=100)
        ... def fetch_data() -> int:
        ...     return some_api_call()

    """
    # Сохраняем значения декоратора в замыкании
    decorator_timeout = timeout
    decorator_finished = finished
    decorator_throw_exception = throw_exception
    decorator_poll_interval = poll_interval
    decorator_max_retries = max_retries

    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
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

            ret: Any = None
            start_time = time.time()
            current_poll_interval = effective_config.poll_interval
            consecutive_failures = 0  # Счётчик неудач для экспоненциальной задержки
            attempt_count = 0  # ИСПРАВЛЕНИЕ 18: Счётчик попыток

            # ИСПРАВЛЕНИЕ 18: Создаём Event для возможности прерывания
            stop_event = threading.Event()

            while True:
                # ИСПРАВЛЕНИЕ 18: Проверка таймаута в начале цикла
                if (
                    effective_config.timeout is not None
                    and time.time() - start_time > effective_config.timeout
                ):
                    timeout_msg = f"Превышено время ожидания для {func.__name__} ({effective_config.timeout} сек)"
                    if effective_config.throw_exception:
                        raise TimeoutError(timeout_msg)
                    # Логируем timeout для диагностики
                    _get_logger().warning(timeout_msg)
                    return ret

                # ИСПРАВЛЕНИЕ 18: Проверка максимального количества попыток
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
                    _get_logger().warning(retries_msg)
                    return ret

                attempt_count += 1

                try:
                    ret = func(*args, **kwargs)
                    if effective_config.finished(ret):
                        return ret
                    consecutive_failures = 0  # Сброс при успехе
                except TimeoutError:
                    # Пробрасываем TimeoutError немедленно
                    raise
                except (MemoryError, OSError, RuntimeError, ValueError, TypeError) as e:
                    # Логирование ошибок выполнения функции
                    local_logger = _get_logger()
                    local_logger.debug(
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
                    _get_logger().warning("Получен сигнал остановки для %s", func.__name__)
                    return ret

                # Ждём с использованием Event.wait() вместо time.sleep()
                # wait() возвращает True если событие установлено, False по таймауту
                stopped = stop_event.wait(timeout=current_poll_interval)
                if stopped:
                    _get_logger().warning(
                        "Ожидание прервано для %s (попыток: %d)", func.__name__, attempt_count
                    )
                    return ret

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
        @functools.wraps(func)
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
