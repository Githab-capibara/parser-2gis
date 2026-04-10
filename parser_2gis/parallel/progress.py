"""Модуль отслеживания прогресса для параллельного парсинга.

Предоставляет класс ParallelProgressReporter для отслеживания прогресса:
- Отслеживание прогресса парсинга
- Отслеживание прогресса объединения файлов
- Потокобезопасное обновление статистики
- Интервал обновления прогресс-бара
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from parser_2gis.logger import logger, print_progress

# Константы
PROGRESS_THROTTLE_INTERVAL: float = 0.5
"""Минимальный интервал между обновлениями прогресса (секунды)."""


class ParallelProgressReporter:
    """Класс для отслеживания прогресса параллельного парсинга.

    Предоставляет функциональность для:
    - Отслеживания прогресса парсинга
    - Отслеживания прогресса объединения файлов
    - Потокобезопасного обновления статистики
    - Интервала обновления прогресс-бара

    Attributes:
        total_tasks: Общее количество задач.
        lock: Блокировка для потокобезопасного доступа.
        progress_callback: Функция обратного вызова для прогресса.
        merge_callback: Функция обратного вызова для объединения.

    """

    def __init__(
        self,
        total_tasks: int,
        lock: threading.RLock,
        progress_callback: Callable[[int, int, str], None] | None = None,
        merge_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Инициализация репортёра прогресса.

        #193: Добавлена валидация total_tasks.

        Args:
            total_tasks: Общее количество задач.
            lock: Блокировка для потокобезопасного доступа.
            progress_callback: Функция обратного вызова для прогресса.
            merge_callback: Функция обратного вызова для объединения.

        Raises:
            ValueError: Если total_tasks отрицательный.

        """
        # #193: Валидация total_tasks
        if total_tasks < 0:
            raise ValueError(f"total_tasks не может быть отрицательным, получено {total_tasks}")

        self.total_tasks = total_tasks
        self._lock = lock
        self._progress_callback = progress_callback
        self._merge_callback = merge_callback
        self._last_progress_time = time.time()
        self._stats: dict[str, int] = {"success": 0, "failed": 0, "total": total_tasks}
        # H019: Throttling - минимальный интервал между обновлениями (сек)
        self._throttle_interval = PROGRESS_THROTTLE_INTERVAL

    def log(self, message: str, level: str = "info") -> None:
        """Логгирование сообщения.

        Args:
            message: Текст сообщения.
            level: Уровень логирования.

        """
        log_func = getattr(logger, level)
        log_func(message)

    def update_progress(self, *, success: bool, filename: str = "N/A", force: bool = False) -> None:
        """Обновляет прогресс парсинга.

        H019: Throttling обновлений для снижения нагрузки на CPU.

        Args:
            success: Была ли операция успешной.
            filename: Имя файла результата.
            force: Принудительно обновить прогресс (игнорировать интервал).

        """
        current_time = time.time()
        # H019: Throttling - проверяем минимальный интервал
        time_since_last = current_time - self._last_progress_time
        should_update = force or (time_since_last >= self._throttle_interval)

        with self._lock:
            if success:
                self._stats["success"] += 1
            else:
                self._stats["failed"] += 1

            completed = self._stats["success"] + self._stats["failed"]

            # H019: Обновляем только если прошло достаточно времени или завершено
            if should_update or completed == self.total_tasks:
                progress_bar = print_progress(completed, self.total_tasks, prefix="   Прогресс")
                self.log(progress_bar, "info")
                self._last_progress_time = current_time

            if self._progress_callback:
                self._progress_callback(self._stats["success"], self._stats["failed"], filename)

    def report_merge_progress(self, filename: str) -> None:
        """Сообщает о прогрессе объединения файлов.

        Args:
            filename: Имя обрабатываемого файла.

        """
        if self._merge_callback:
            self._merge_callback(f"Обработка: {filename}")

    def get_stats(self) -> dict[str, int]:
        """Возвращает текущую статистику.

        Returns:
            Словарь со статистикой.

        """
        with self._lock:
            return dict(self._stats)

    def is_complete(self) -> bool:
        """Проверяет, завершён ли парсинг.

        Returns:
            True если все задачи завершены.

        """
        with self._lock:
            return (self._stats["success"] + self._stats["failed"]) >= self.total_tasks

    def get_summary(self) -> str:
        """Возвращает краткую сводку прогресса.

        Returns:
            Строка с краткой сводкой.

        """
        with self._lock:
            success = self._stats["success"]
            failed = self._stats["failed"]
            total = self.total_tasks
            return f"Парсинг: {success}/{total} успешно, {failed} ошибок"
