"""Утилиты для работы с Future и ThreadPoolExecutor.

ISSUE 053: Вынесено из parallel_parser.py и coordinator.py (thread_coordinator)
для устранения дублирования логики отмены Future и очистки.

Пример использования:
    >>> from concurrent.futures import Future
    >>> from parser_2gis.parallel.common.future_utils import cancel_futures_safely
    >>> cancel_futures_safely([future1, future2])
"""

from __future__ import annotations

import logging
from concurrent.futures import Future
from typing import Any

logger = logging.getLogger(__name__)


def cancel_futures_safely(
    futures: list[Future[Any]] | dict[Future[Any], Any], log_prefix: str = "Future"
) -> int:
    """Безопасно отменяет список Future.

    Общая функция для устранения дублирования между:
    - parallel_parser.py: отмена future при KeyboardInterrupt
    - coordinator.py: отмена future при отмене парсинга

    Args:
        futures: Список Future или словарь {Future: data} для отмены.
        log_prefix: Префикс для логирования.

    Returns:
        Количество отменённых Future.

    """
    if isinstance(futures, dict):
        future_list = list(futures.keys())
    else:
        future_list = futures

    cancelled_count = 0
    for future in future_list:
        try:
            if future.cancel():
                cancelled_count += 1
                logger.debug("%s отменён", log_prefix)
        except (OSError, RuntimeError, ValueError) as cancel_error:
            logger.debug("Не удалось отменить %s: %s", log_prefix, cancel_error)

    logger.info("Отменено %d из %d %s", cancelled_count, len(future_list), log_prefix)
    return cancelled_count


def get_future_result_safely(
    future: Future[Any], timeout: float | None = None, default: Any = None
) -> tuple[bool, Any]:
    """Безопасно получает результат Future.

    Args:
        future: Future для получения результата.
        timeout: Таймаут ожидания.
        default: Значение по умолчанию при ошибке.

    Returns:
        Кортеж (success, result_or_default).

    """
    try:
        result = future.result(timeout=timeout)
        return True, result
    except Exception as error:
        logger.warning("Ошибка получения результата Future: %s", error)
        return False, default


def shutdown_executor_safely(executor: Any, *, wait: bool = True, cancel_futures: bool = True) -> bool:
    """Безопасно завершает ThreadPoolExecutor.

    Args:
        executor: ThreadPoolExecutor для завершения.
        wait: Ждать ли завершения задач.
        cancel_futures: Отменять ли оставшиеся задачи.

    Returns:
        True если shutdown успешен.

    """
    try:
        executor.shutdown(wait=wait, cancel_futures=cancel_futures)
        logger.debug("ThreadPoolExecutor завершён корректно")
        return True
    except (OSError, RuntimeError, ValueError) as shutdown_error:
        logger.exception("Ошибка при shutdown ThreadPoolExecutor: %s", shutdown_error)
        return False
