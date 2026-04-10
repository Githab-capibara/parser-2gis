"""Модуль координации потоков для параллельного парсинга.

Этот модуль предоставляет класс ThreadCoordinator для координации
параллельного парсинга:
- Управление потоками и семафорами
- Обработка отмены и сигналов
- Координация задач парсинга

Поддерживает два режима выполнения:
- ThreadPoolExecutor: Для I/O-bound операций (по умолчанию)
- ProcessPoolExecutor: Для CPU-bound операций
"""

from __future__ import annotations

import asyncio
import signal
import threading
from collections.abc import Callable
from concurrent.futures import (
    Executor,
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from concurrent.futures import TimeoutError as FuturesTimeoutError
from threading import BoundedSemaphore
from typing import TYPE_CHECKING, Literal

from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MIN_TIMEOUT,
    MIN_WORKERS,
)
from parser_2gis.logger.logger import logger
from parser_2gis.parallel.signal_handler import create_signal_handler

if TYPE_CHECKING:
    from parser_2gis.parallel.url_parser import ParallelUrlParser


# =============================================================================
# THREAD-LOCAL COORDINATOR CONTEXT (ISSUE-111: Устранено глобальное состояние)
# =============================================================================


class _CoordinatorContext:
    """Контекстный менеджер для хранения активного координатора.

    ISSUE-111: Вместо глобальной переменной _active_coordinator используем
    thread-local хранение для устранения race condition.
    """

    def __init__(self) -> None:
        """Инициализирует контекстный менеджер."""
        self._local = threading.local()

    def set_coordinator(self, coordinator: ThreadCoordinator | None) -> None:
        """Устанавливает активный координатор для текущего потока."""
        self._local.active_coordinator = coordinator

    def get_coordinator(self) -> ThreadCoordinator | None:
        """Получает активный координатор для текущего потока."""
        return getattr(self._local, "active_coordinator", None)


# Глобальный экземпляр контекста (не изменяемое состояние, а контейнер)
# Используем ленивую инициализацию через замыкание для предотвращения race condition при импорте


def _get_coordinator_context() -> _CoordinatorContext:
    """Лениво создаёт и возвращает глобальный контекст координатора."""
    if not hasattr(_get_coordinator_context, "_instance"):
        _get_coordinator_context._instance = _CoordinatorContext()
    return _get_coordinator_context._instance  # type: ignore[attr-defined]


# Общий обработчик сигналов (#62: вынесен в signal_handler.py)
_signal_handler = create_signal_handler(_get_coordinator_context)


ExecutorType = Literal["thread", "process"]


class ThreadCoordinator:
    """Координатор потоков для параллельного парсинга.

    Отвечает за:
    - Управление пулом потоков/процессов
    - Контроль одновременного запуска браузеров через семафор
    - Обработку отмены и сигналов
    - Координацию задач парсинга

    Args:
        url_parser: Экземпляр парсера URL.
        max_workers: Максимальное количество рабочих потоков.
        timeout_per_url: Таймаут на один URL в секундах.
        executor_type: Тип executor ("thread" или "process").

    Note:
        ProcessPoolExecutor рекомендуется для CPU-bound операций,
        но требует чтобы функции были pickleable.

    """

    def __init__(
        self,
        url_parser: ParallelUrlParser,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        executor_type: ExecutorType = "thread",
    ) -> None:
        """Инициализирует координатор потоков.

        Args:
            url_parser: Экземпляр парсера URL.
            max_workers: Максимальное количество рабочих потоков.
            timeout_per_url: Таймаут на один URL в секундах.
            executor_type: Тип executor ("thread" или "process").

        Raises:
            ValueError: Если max_workers или timeout_per_url некорректны.
            ValueError: Если executor_type некорректен.

        """
        self._validate_coordinator_config(max_workers, timeout_per_url)
        self._validate_executor_type(executor_type)

        self._url_parser = url_parser
        self._max_workers = max_workers
        self._timeout_per_url = timeout_per_url
        self._executor_type = executor_type

        # Семафор для контроля одновременного запуска браузеров
        # ИСПРАВЛЕНИЕ #182: Используем ровно max_workers без дополнительных слотов
        self._browser_semaphore = BoundedSemaphore(max_workers)

        # Флаг отмены
        self._cancel_event = threading.Event()

        # Событие для координации остановки
        self._stop_event = threading.Event()

        # Блокировка для защиты общих ресурсов
        self._lock = threading.Lock()

        logger.info(
            "Инициализирован координатор: max_workers=%d, timeout=%d сек, executor=%s",
            max_workers,
            timeout_per_url,
            executor_type,
        )

    @staticmethod
    def _validate_coordinator_config(max_workers: int, timeout_per_url: int) -> None:
        """Валидирует конфигурацию координатора.

        Args:
            max_workers: Максимальное количество рабочих потоков.
            timeout_per_url: Таймаут на один URL в секундах.

        Raises:
            ValueError: Если параметры некорректны.

        """
        if max_workers < MIN_WORKERS:
            raise ValueError(
                f"max_workers должен быть не менее {MIN_WORKERS}, получено {max_workers}",
            )
        if max_workers > MAX_WORKERS:
            raise ValueError(
                f"max_workers не должен превышать {MAX_WORKERS}, получено {max_workers}",
            )
        if timeout_per_url < MIN_TIMEOUT:
            raise ValueError(
                f"timeout_per_url должен быть не менее {MIN_TIMEOUT}, получено {timeout_per_url}",
            )
        if timeout_per_url > MAX_TIMEOUT:
            raise ValueError(
                f"timeout_per_url не должен превышать {MAX_TIMEOUT}, получено {timeout_per_url}",
            )

    @staticmethod
    def _validate_executor_type(executor_type: ExecutorType) -> None:
        """Валидирует тип executor.

        Args:
            executor_type: Тип executor.

        Raises:
            ValueError: Если тип некорректен.

        """
        if executor_type not in ("thread", "process"):
            raise ValueError(
                f"executor_type должен быть 'thread' или 'process', получено {executor_type}",
            )

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def run_parsing(
        self,
        all_urls: list[tuple[str, str, str]],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг всех URL.

        Args:
            all_urls: Список кортежей (url, category_name, city_name).
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если парсинг успешен, False иначе.

        """
        # Установка глобального обработчика сигнала SIGINT
        old_signal_handler = signal.signal(signal.SIGINT, _signal_handler)
        _get_coordinator_context().set_coordinator(self)

        # Синхронизируем флаг отмены с url_parser
        self._url_parser._cancel_event = self._cancel_event

        executor: Executor | None = None
        futures: dict[Future[tuple[bool, str]], tuple[str, str, str]] = {}

        try:
            # Создаём executor в зависимости от типа
            if self._executor_type == "process":
                executor = ProcessPoolExecutor(max_workers=self._max_workers)
                logger.debug("Использован ProcessPoolExecutor для CPU-bound операций")
            else:
                executor = ThreadPoolExecutor(max_workers=self._max_workers)
                logger.debug("Использован ThreadPoolExecutor для I/O-bound операций")

            # Отправляем задачи на выполнение
            futures = {
                executor.submit(
                    self._parse_url_task, url, category_name, city_name, progress_callback,
                ): (url, category_name, city_name)
                for url, category_name, city_name in all_urls
            }

            # Обрабатываем результаты по мере завершения
            for future in as_completed(futures):
                _url, category_name, city_name = futures[future]
                try:
                    success, result = future.result(timeout=self._timeout_per_url)
                    if not success:
                        self.log(f"Не удалось: {city_name} - {category_name}: {result}", "error")
                except FuturesTimeoutError:
                    self.log(f"Таймаут при парсинге {city_name} - {category_name}", "error")
                except (KeyboardInterrupt, asyncio.CancelledError):
                    self.log("Парсинг прерван пользователем", "warning")
                    self._cancel_event.set()
                    for f in futures:
                        f.cancel()
                    return False
                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    self.log(f"Исключение при парсинге {city_name} - {category_name}: {e}", "error")

        except (KeyboardInterrupt, asyncio.CancelledError):
            self.log("Парсинг прерван пользователем", "warning")
            self._cancel_event.set()
            if executor is not None:
                for f in futures:
                    f.cancel()
            return False
        finally:
            # Восстановление обработчика сигнала и очистка ресурсов
            _get_coordinator_context().set_coordinator(None)
            try:
                signal.signal(signal.SIGINT, old_signal_handler)
            except (ValueError, TypeError) as signal_error:
                logger.debug(
                    "Ошибка при восстановлении обработчика SIGINT (игнорируется): %s", signal_error,
                )

            if executor is not None:
                try:
                    executor.shutdown(wait=True, cancel_futures=True)
                    self.log(f"{self._executor_type} executor корректно завершён", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as shutdown_error:
                    self.log(
                        f"Ошибка при shutdown {self._executor_type} executor: {shutdown_error}",
                        "error",
                    )

            self.log("Ресурсы координатора освобождены", "debug")

        return True

    def _parse_url_task(
        self,
        url: str,
        category_name: str,
        city_name: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[bool, str]:
        """Выполняет задачу парсинга одного URL.

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (успех, сообщение).

        """
        return self._url_parser.parse_single_url(
            url=url,
            category_name=category_name,
            city_name=city_name,
            browser_semaphore=self._browser_semaphore,
            progress_callback=progress_callback,
        )

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._cancel_event.set()
        self._stop_event.set()
        self.log("Получена команда остановки парсинга", "warning")
        # Синхронизируем с url_parser
        self._url_parser._cancel_event = self._cancel_event

    @property
    def is_cancelled(self) -> bool:
        """Проверяет, отменён ли парсинг."""
        return self._cancel_event.is_set()

    @property
    def browser_semaphore(self) -> BoundedSemaphore:
        """Возвращает семафор для контроля браузеров."""
        return self._browser_semaphore

    @property
    def stats(self) -> dict[str, int]:
        """Возвращает статистику парсинга.

        Примечание: Делегирует получение статистики объекту _url_parser.
        """
        return self._url_parser.stats
