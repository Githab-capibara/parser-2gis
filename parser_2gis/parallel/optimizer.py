"""Модуль для оптимизации параллельного парсинга.

Этот модуль предоставляет логику для эффективного распределения
ресурсов между браузерами при параллельном парсинга.

Оптимизации:
- Кэширование psutil.Process объекта
- Улучшенное управление очередями задач
- Оптимизированная проверка ресурсов
"""

from __future__ import annotations

import itertools
import queue
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import psutil

from parser_2gis.logger import logger

# Константы
DEFAULT_MEMORY_PERCENT_THRESHOLD: float = 0.10
"""Доля доступной памяти для использования по умолчанию (10%)."""

MIN_MEMORY_LIMIT_MB: int = 512
"""Минимальный лимит памяти в МБ."""

MAX_MEMORY_LIMIT_MB: int = 8192
"""Максимальный лимит памяти в МБ."""

# Интервалы мониторинга ресурсов
MONITOR_INTERVAL = 5.0
"""Интервал проверки ресурсов в секундах."""

SHORT_CHECK_INTERVAL = 0.1
"""Короткий интервал проверки в секундах."""

_task_counter = itertools.count()


class ParallelTask:
    """Задача для параллельного парсинга."""

    def __init__(self, url: str, category_name: str, city_name: str, priority: int = 0) -> None:
        """Инициализирует задачу.

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            priority: Приоритет задачи (0 - обычный, 1 - высокий).

        """
        self.url = url
        self.category_name = category_name
        self.city_name = city_name
        self.priority = priority
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self) -> None:
        """Отмечает начало выполнения задачи."""
        self.start_time = time.time()
        logger.debug("Начало задачи: %s - %s", self.city_name, self.category_name)

    def finish(self) -> None:
        """Отмечает завершение задачи."""
        self.end_time = time.time()
        duration = self.duration()
        logger.debug(
            "Завершение задачи: %s - %s (время: %.2f сек)",
            self.city_name,
            self.category_name,
            duration,
        )

    def duration(self) -> float:
        """Возвращает длительность выполнения задачи.

        Returns:
            Длительность в секундах или 0 если не завершена.

        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        if self.start_time:
            return time.time() - self.start_time
        return 0


class ParallelOptimizer:
    """Оптимизатор для параллельного парсинга.

    Оптимизация:
    - Кэширование psutil.Process объекта
    - Улучшенное управление очередями задач

    Управляет очередями задач, балансирует нагрузку между браузерами,
    контролирует использование ресурсов системы.
    """

    def __init__(
        self,
        max_workers: int = 3,
        max_memory_mb: int | None = None,
        memory_percent_threshold: float = DEFAULT_MEMORY_PERCENT_THRESHOLD,
    ) -> None:
        """Инициализирует оптимизатор.

        #194: Добавлена валидация max_workers.

        Args:
            max_workers: Максимальное количество рабочих потоков.
            max_memory_mb: Максимальное использование памяти в МБ.
                         Если None, автоматически определяется через psutil.
            memory_percent_threshold: Доля доступной памяти для использования
                         при автоматическом определении (по умолчанию 0.10 = 10%).

        Raises:
            ValueError: Если max_workers <= 0.

        """
        # #194: Валидация max_workers
        if max_workers <= 0:
            msg = f"max_workers должен быть положительным, получено {max_workers}"
            raise ValueError(msg)

        self._max_workers = max_workers
        self._memory_percent_threshold = memory_percent_threshold
        # Автоматическое определение лимита памяти через psutil
        if max_memory_mb is None:
            try:
                available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
                # Используем заданный процент от доступной памяти
                self._max_memory_mb = int(available_memory_mb * self._memory_percent_threshold)
                # Ограничиваем разумным диапазоном: минимум 512 MB, максимум 8192 MB
                self._max_memory_mb = max(
                    MIN_MEMORY_LIMIT_MB, min(self._max_memory_mb, MAX_MEMORY_LIMIT_MB)
                )
                logger.debug(
                    "Автоматически определён лимит памяти: %d MB "
                    "(доступно: %.0f MB, процент: %.0f%%)",
                    self._max_memory_mb,
                    available_memory_mb,
                    self._memory_percent_threshold * 100,
                )
            except (OSError, AttributeError, ImportError) as e:
                # Fallback если psutil недоступен
                self._max_memory_mb = 4096
                logger.warning(
                    "Не удалось определить доступную память через psutil: %s. "
                    "Используется лимит по умолчанию: %d MB",
                    e,
                    self._max_memory_mb,
                )
        else:
            self._max_memory_mb = max_memory_mb
        # Оптимизация 3.5: используем queue.Queue для потокобезопасной очереди задач
        # Queue автоматически синхронизирует доступ из разных потоков
        self._tasks: queue.Queue[ParallelTask] = queue.Queue()
        self._active_tasks: dict[int, ParallelTask] = {}
        self._completed_tasks: list[ParallelTask] = []
        # ИСПОЛЬЗУЕМ RLock (Reentrant Lock) для предотвращения deadlock
        # RLock позволяет одному и тому же потоку захватывать блокировку несколько раз
        self._lock = threading.RLock()
        self._stats = {"total_tasks": 0, "completed": 0, "failed": 0, "avg_duration": 0.0}

        # Оптимизация: кэшируем psutil.Process объект
        self._process_cache: psutil.Process | None = None
        try:
            self._process_cache = psutil.Process()
        except (OSError, ValueError, RuntimeError) as process_error:
            # Логгируем ошибку создания процесса
            logger.debug("Не удалось создать кэш процесса psutil: %s", process_error)

        # Кэш для проверки ресурсов
        self._resource_cache: tuple[bool, float, float] = (True, 0.0, 0.0)
        self._resource_cache_time: float = 0
        self._resource_cache_ttl: float = 1.0  # TTL 1 секунда
        # #160: Блокировка для защиты кэша от race condition
        self._resource_cache_lock = threading.Lock()

        logger.info(
            "Инициализирован ParallelOptimizer: max_workers=%d, max_memory=%d МБ",
            max_workers,
            max_memory_mb,
        )

    def add_task(self, url: str, category_name: str, city_name: str, priority: int = 0) -> None:
        """Добавляет задачу в очередь.

        Оптимизация 3.5:
        - Используем queue.Queue для потокобезопасной очереди
        - put() автоматически синхронизирует доступ
        #185: Объединяем проверку и добавление под одной блокировкой

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            priority: Приоритет задачи (0 - обычный, 1 - высокий).

        """
        task = ParallelTask(url, category_name, city_name, priority)

        # #185: Объединяем проверку ресурсов и добавление задачи под одной блокировкой
        with self._lock:
            # Проверяем доступные ресурсы перед добавлением
            available, _ = self.check_resources()
            if not available:
                logger.warning(
                    "Ресурсы ограничены, задача не добавлена: %s - %s", city_name, category_name
                )
                return
            # Оптимизация 3.5: Queue потокобезопасен, но блокировка гарантирует атомарность
            self._tasks.put(task, block=True)
            self._stats["total_tasks"] += 1

        logger.debug(
            "Добавлена задача: %s - %s (приоритет: %d)", city_name, category_name, priority
        )

    def check_resources(self) -> tuple[bool, float]:
        """Проверяет доступность ресурсов системы.

        Оптимизация:
        - Кэширование psutil.Process объекта
        - Кэширование результатов проверки для снижения частоты проверок
        #160: Защищает кэш через threading.Lock от race condition.

        Returns:
            Кортеж (доступно ли, использование_памяти_МБ).

        """
        current_time = time.time()

        # #160: Защищаем чтение кэша блокировкой
        with self._resource_cache_lock:
            if current_time - self._resource_cache_time < self._resource_cache_ttl:
                # Возвращаем кэшированный результат
                available, memory_mb, _ = self._resource_cache
                return available, memory_mb

        try:
            # Оптимизация: используем кэшированный Process объект
            if self._process_cache is None:
                return True, 0.0

            memory_info = self._process_cache.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Получаем загрузку CPU (быстрая проверка без интервала)
            cpu_percent = self._process_cache.cpu_percent(interval=0)

            # Проверяем лимиты
            memory_ok = memory_mb < self._max_memory_mb
            cpu_ok = cpu_percent < 95  # Не перегружать CPU

            available = memory_ok and cpu_ok

            if not available:
                logger.debug(
                    "Ресурсы ограничены: память=%.1f МБ (лимит %d), CPU=%.1f%%",
                    memory_mb,
                    self._max_memory_mb,
                    cpu_percent,
                )

            # #160: Защищаем запись в кэш блокировкой
            result = (available, memory_mb, cpu_percent)
            with self._resource_cache_lock:
                self._resource_cache = result
                self._resource_cache_time = current_time

            return available, memory_mb

        except (OSError, ValueError, RuntimeError, psutil.Error) as e:
            logger.warning("Ошибка при проверке ресурсов: %s", e)
            return True, 0.0

    def get_next_task(self) -> ParallelTask | None:
        """Получает следующую задачу из очереди.

        Оптимизация 3.5:
        - Используем queue.Queue для потокобезопасного извлечения
        - get_nowait() для неблокирующего извлечения задачи
        - Не требуется ручная блокировка

        Returns:
            Следующая задача или None если очередь пуста.

        """
        task: ParallelTask | None = None

        try:
            # Оптимизация 3.5: Queue.get_nowait() для неблокирующего извлечения
            # Queue потокобезопасен, не нужна ручная блокировка
            task = self._tasks.get_nowait()
        except queue.Empty:
            # Очередь пуста
            return None

        task.start()

        return task

    def complete_task(self, task: ParallelTask, *, success: bool) -> None:
        """Отмечает задачу как завершенную.

        Args:
            task: Задача.
            success: Успешно ли выполнена.

        """
        task.finish()

        with self._lock:
            self._completed_tasks.append(task)

            # Увеличиваем счётчик только один раз в соответствующем блоке
            if success:
                self._stats["completed"] += 1
            else:
                self._stats["failed"] += 1

            # Пересчитываем среднюю длительность
            total_duration = sum(t.duration() for t in self._completed_tasks)
            self._stats["avg_duration"] = total_duration / len(self._completed_tasks)

            # Удаляем из активных задач
            task_id = getattr(task, "_task_id", None)
            if task_id is not None and task_id in self._active_tasks:
                del self._active_tasks[task_id]

        logger.info(
            "Задача завершена: %s - %s (успех: %s, время: %.2f сек)",
            task.city_name,
            task.category_name,
            success,
            task.duration(),
        )

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику оптимизатора.

        Returns:
            Словарь со статистикой.

        """
        with self._lock:
            stats = self._stats.copy()
            # Оптимизация 3.5: Queue.qsize() вместо len() для получения размера очереди
            stats["pending_tasks"] = self._tasks.qsize()
            stats["active_tasks"] = len(self._active_tasks)
            stats["progress"] = (
                self._stats["completed"] / self._stats["total_tasks"] * 100
                if self._stats["total_tasks"] > 0
                else 0
            )
            return stats

    def reset(self) -> None:
        """Сбрасывает состояние оптимизатора.

        Оптимизация 3.5:
        - Queue не имеет clear(), поэтому создаём новую очередь
        - Потокобезопасная очистка через создание нового объекта
        """
        with self._lock:
            # Оптимизация 3.5: Queue не имеет clear(), создаём новую очередь
            self._tasks = queue.Queue()
            self._active_tasks.clear()
            self._completed_tasks.clear()
            self._stats = {"total_tasks": 0, "completed": 0, "failed": 0, "avg_duration": 0.0}
        logger.debug("ParallelOptimizer сброшен")

    def run_parallel(
        self,
        parse_func: Callable[[ParallelTask], tuple[bool, str]],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг с оптимизацией.

        Оптимизация 3.5:
        - Используем Queue.empty() для проверки очереди
        - Queue потокобезопасен, упрощает управление задачами

        Args:
            parse_func: Функция парсинга, принимающая ParallelTask.
            progress_callback: Функция обратного вызова для прогресса.

        Returns:
            True если все задачи выполнены успешно.

        """
        logger.info("Запуск параллельного парсинга с оптимизацией (%d потоков)", self._max_workers)

        success_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Создаём futures для всех задач
            futures = {}

            # Оптимизация 3.5: используем Queue.empty() для проверки
            while not self._tasks.empty() or self._active_tasks:
                # Проверяем ресурсы
                available, _ = self.check_resources()

                if not available:
                    logger.warning("Ожидание освобождения ресурсов...")
                    time.sleep(MONITOR_INTERVAL)
                    continue

                # Запускаем новые задачи если есть ресурсы
                # Оптимизация 3.5: Queue.empty() для проверки наличия задач
                while len(self._active_tasks) < self._max_workers and not self._tasks.empty():
                    task = self.get_next_task()
                    if task:
                        future = executor.submit(parse_func, task)
                        with self._lock:
                            futures[future] = task
                            task_id = next(_task_counter)
                            task._task_id = task_id  # type: ignore[attr-defined]
                            self._active_tasks[task_id] = task
                        logger.debug("Запущена задача: %s - %s", task.city_name, task.category_name)

                # Проверяем завершенные задачи
                completed = []
                for future in as_completed(futures.keys(), timeout=1.0):
                    try:
                        task = futures[future]
                        success, _ = future.result(timeout=300)
                        self.complete_task(task, success=success)
                        completed.append(future)

                        if success:
                            success_count += 1
                        else:
                            failed_count += 1

                        if progress_callback:
                            progress_callback(
                                success_count,
                                failed_count,
                                f"{task.city_name}_{task.category_name}",
                            )
                    except (OSError, ValueError, RuntimeError) as e:
                        task = futures[future]
                        logger.error(
                            "Ошибка в задаче %s - %s: %s", task.city_name, task.category_name, e
                        )
                        self.complete_task(task, success=False)
                        completed.append(future)
                        failed_count += 1

                # Удаляем завершенные futures
                for future in completed:
                    del futures[future]

                # Небольшая пауза если нет активных задач
                if not self._active_tasks:
                    time.sleep(SHORT_CHECK_INTERVAL)

        logger.info(
            "Параллельный парсинг завершен. Успешно: %d, Ошибок: %d", success_count, failed_count
        )

        return failed_count == 0
