"""Модуль управления потоками для параллельного парсинга.

Предоставляет класс ThreadManager для управления потоками:
- Создание и запуск потоков
- Контроль выполнения задач
- Обработка завершения и отмены
- Сбор результатов выполнения
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, TypedDict

logger = logging.getLogger("parser_2gis.parallel.thread_manager")


class ThreadManagerStats(TypedDict):
    """TypedDict для статистики ThreadManager."""

    max_workers: int
    timeout_per_task: int
    total_tasks: int
    cancelled: bool


class ThreadManager:
    """Менеджер управления потоками для параллельного парсинга.

    Отвечает за создание, запуск и управление потоками выполнения.
    Использует ThreadPoolExecutor для управления пулом потоков.

    Attributes:
        max_workers: Максимальное количество одновременных потоков.
        timeout_per_task: Таймаут на одну задачу в секундах.
        executor: ThreadPoolExecutor для управления потоками.

    """

    def __init__(self, max_workers: int = 3, timeout_per_task: int = 300) -> None:
        """Инициализация менеджера потоков.

        Args:
            max_workers: Максимальное количество одновременных потоков.
            timeout_per_task: Таймаут на одну задачу в секундах.

        """
        self.max_workers = max_workers
        self.timeout_per_task = timeout_per_task
        self._executor: ThreadPoolExecutor | None = None
        self._futures: dict[Future[Any], tuple[str, str, str]] = {}
        self._cancel_event = threading.Event()
        self._lock = threading.RLock()

    def submit_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """Отправляет задачу на выполнение в пул потоков.

        Args:
            func: Функция для выполнения.
            *args: Позиционные аргументы для функции.
            **kwargs: Именованные аргументы для функции.

        Returns:
            Future объект для получения результата.

        Raises:
            RuntimeError: Если executor не инициализирован.

        """
        if self._executor is None:
            raise RuntimeError("ThreadPoolExecutor не инициализирован")

        future = self._executor.submit(func, *args, **kwargs)
        return future

    def execute_all(
        self,
        tasks: list[tuple[str, str, str]],
        task_func: Callable[..., tuple[bool, str]],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[int, int]:
        """Выполняет все задачи в пуле потоков.

        Args:
            tasks: Список задач (url, category_name, city_name).
            task_func: Функция для выполнения каждой задачи.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (success_count, failed_count).

        """
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        success_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            self._executor = executor
            self._futures = {
                executor.submit(task_func, url, category_name, city_name, progress_callback): (
                    url,
                    category_name,
                    city_name,
                )
                for url, category_name, city_name in tasks
            }

            for _idx, future in enumerate(as_completed(self._futures), 1):
                _url, category_name, city_name = self._futures[future]

                try:
                    if self._cancel_event.is_set():
                        logger.warning("Выполнение отменено пользователем")
                        for f in self._futures:
                            f.cancel()
                        break

                    success, result = future.result(timeout=self.timeout_per_task)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        logger.error("Не удалось: %s - %s: %s", city_name, category_name, result)

                except FuturesTimeoutError:
                    failed_count += 1
                    logger.exception(
                        "Таймаут при парсинге %s - %s (%d сек)",
                        city_name,
                        category_name,
                        self.timeout_per_task,
                    )

                except (KeyboardInterrupt, SystemExit):
                    raise
                except (OSError, RuntimeError, ValueError) as e:
                    failed_count += 1
                    logger.exception("Исключение при парсинге %s - %s: %s", city_name, category_name, e)

        # Очистка executor в finally-стиле — гарантированно при любом выходе
        self._executor = None

        return success_count, failed_count

    def cancel_all(self) -> None:
        """Отменяет все выполняемые задачи."""
        self._cancel_event.set()
        logger.warning("Отмена всех задач")

    def is_cancelled(self) -> bool:
        """Проверяет флаг отмены задач.

        Returns:
            True если задачи отменены.

        """
        return self._cancel_event.is_set()

    def get_statistics(self) -> ThreadManagerStats:
        """Возвращает статистику выполнения.

        Returns:
            Словарь со статистикой.

        """
        return {
            "max_workers": self.max_workers,
            "timeout_per_task": self.timeout_per_task,
            "total_tasks": len(self._futures),
            "cancelled": self._cancel_event.is_set(),
        }
