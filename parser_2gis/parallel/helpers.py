"""Модуль для вспомогательных классов параллельного парсинга.

Содержит классы:
- ProgressTracker: Отслеживание прогресса
- StatsCollector: Сбор статистики
- Выделены из ParallelCityParser для снижения сложности

Примечание: класс FileMerger был удалён, т.к. полностью дублирует
ParallelFileMerger из parser_2gis/parallel/merger.py.
Используйте ParallelFileMerger вместо FileMerger.
Для общего кода слияния CSV используйте:
    parser_2gis.parallel.common.csv_merge_common.merge_csv_files_common

ISSUE-059: Импорты FileMerger из тестов удалены.
"""

from __future__ import annotations

import threading
import time
from typing import Any, TypedDict


class StatsSummary(TypedDict):
    """TypedDict для сводки статистики."""

    success_count: int
    error_count: int
    total: int
    elapsed_time: float
    errors: list[dict[str, Any]]


class ProgressTracker:
    """Потокобезопасный трекер прогресса.

    Отслеживает:
    - Количество обработанных городов
    - Количество обработанных категорий
    - Общее количество задач
    - Прогресс в процентах

    Все методы защищены через RLock для предотвращения race conditions
    при конкурентном доступе из нескольких потоков.

    Пример использования:
        >>> tracker = ProgressTracker(total_cities=10, total_categories=5)
        >>> tracker.update(city_name="Москва", category_name="Рестораны")
        >>> print(tracker.get_progress_percent())
        10.0
    """

    def __init__(self, total_cities: int, total_categories: int) -> None:
        """Инициализация трекера прогресса.

        Args:
            total_cities: Общее количество городов.
            total_categories: Общее количество категорий.

        """
        self.total_cities = total_cities
        self.total_categories = total_categories
        self.total_tasks = total_cities * total_categories
        self.completed_tasks = 0
        self.current_city = ""
        self.current_category = ""
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

    def update(self, city_name: str, category_name: str) -> None:
        """Обновляет прогресс после завершения задачи.

        Args:
            city_name: Название текущего города.
            category_name: Название текущей категории.

        """
        with self._lock:
            self.completed_tasks += 1
            self.current_city = city_name
            self.current_category = category_name

    def get_progress_percent(self) -> float:
        """Получает процент выполнения.

        Returns:
            Процент выполнения (0.0 - 100.0).

        """
        with self._lock:
            if self.total_tasks is None or self.total_tasks <= 0:
                return 0.0
            return (self.completed_tasks / self.total_tasks) * 100.0

    def get_status(self) -> dict[str, Any]:
        """Получает текущий статус прогресса.

        Returns:
            Словарь со статусом прогресса.

        """
        with self._lock:
            return {
                "completed": self.completed_tasks,
                "total": self.total_tasks,
                "percent": self.get_progress_percent(),
                "current_city": self.current_city,
                "current_category": self.current_category,
            }


class StatsCollector:
    """Сборщик статистики с ограничением максимального значения счётчика.

    Собирает:
    - Количество успешных операций
    - Количество ошибок
    - Время выполнения
    - Детали ошибок

    Максимальное значение счётчика: _MAX_COUNTER_VALUE (10^9). При достижении
    лимита счётчик сбрасывается для предотвращения переполнения.

    Пример использования:
        >>> stats = StatsCollector()
        >>> stats.record_success()
        >>> stats.record_error("Ошибка подключения", city="Москва")
        >>> print(stats.get_summary())
    """

    def __init__(self) -> None:
        """Инициализация сборщика статистики."""
        self.success_count = 0
        self.error_count = 0
        self.errors: list[dict[str, Any]] = []
        self.start_time: float | None = None
        self.end_time: float | None = None
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

    def start(self) -> None:
        """Начинает сбор статистики."""
        with self._lock:
            self.start_time = time.time()

    def stop(self) -> None:
        """Завершает сбор статистики."""
        with self._lock:
            self.end_time = time.time()

    # Максимальное значение счётчика для предотвращения overflow
    _MAX_COUNTER_VALUE: int = 10**9

    def record_success(self) -> None:
        """Записывает успешную операцию."""
        with self._lock:
            if self.success_count < self._MAX_COUNTER_VALUE:
                self.success_count += 1

    def record_error(self, error_message: str, city: str = "", category: str = "") -> None:
        """Записывает ошибку.

        Args:
            error_message: Сообщение об ошибке.
            city: Название города (опционально).
            category: Название категории (опционально).

        """
        with self._lock:
            if self.error_count < self._MAX_COUNTER_VALUE:
                self.error_count += 1
            self.errors.append(
                {
                    "message": error_message,
                    "city": city,
                    "category": category,
                    "timestamp": time.time(),
                }
            )

    def get_elapsed_time(self) -> float:
        """Получает прошедшее время.

        Returns:
            Время в секундах.

        """
        with self._lock:
            if self.start_time is None:
                return 0.0
            end = self.end_time or time.time()
            return end - self.start_time

    def get_summary(self) -> StatsSummary:
        """Получает сводку статистики.

        Returns:
            Словарь со сводкой статистики.

        """
        with self._lock:
            return {
                "success_count": self.success_count,
                "error_count": self.error_count,
                "total": self.success_count + self.error_count,
                "elapsed_time": self.get_elapsed_time(),
                "errors": self.errors.copy(),  # Копия для безопасности
            }
