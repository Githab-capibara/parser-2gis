"""Модуль управления семафорами для параллельного парсинга.

Предоставляет класс SemaphoreManager для:
- Управления семафорами браузеров
- Контроля одновременного доступа к ресурсам
- Мониторинга состояния семафоров
"""

from __future__ import annotations

import threading
from threading import BoundedSemaphore
from typing import Any

from parser_2gis.constants import MAX_WORKERS, MIN_WORKERS
from parser_2gis.logger.logger import logger


class SemaphoreManager:
    """Менеджер управления семафорами.

    Отвечает за:
    - Создание и управление семафорами
    - Контроль одновременного запуска браузеров
    - Мониторинг доступных слотов
    - Безопасное освобождение слотов

    Args:
        max_workers: Максимальное количество рабочих потоков.
        extra_slots: Дополнительные слоты для поддержки burst нагрузки.

    """

    _instance: SemaphoreManager | None = None

    def __init__(self, max_workers: int = 3, extra_slots: int = 20) -> None:
        """Инициализирует менеджер семафоров.

        Args:
            max_workers: Максимальное количество рабочих потоков.
            extra_slots: Дополнительные слоты для burst нагрузки.

        Raises:
            ValueError: Если max_workers некорректен.

        """
        self._validate_max_workers(max_workers)

        self._max_workers = max_workers
        self._extra_slots = extra_slots
        self._semaphore = BoundedSemaphore(max_workers + extra_slots)
        self._acquired_count = 0
        self._lock = threading.Lock()

        logger.info(
            "Инициализирован SemaphoreManager: max_workers=%d, extra_slots=%d, всего слотов=%d",
            max_workers,
            extra_slots,
            max_workers + extra_slots,
        )

    @staticmethod
    def _validate_max_workers(max_workers: int) -> None:
        """Валидирует max_workers.

        Args:
            max_workers: Максимальное количество рабочих потоков.

        Raises:
            ValueError: Если max_workers некорректен.

        """
        if max_workers < MIN_WORKERS:
            msg = f"max_workers должен быть не менее {MIN_WORKERS}, получено {max_workers}"
            raise ValueError(msg)
        if max_workers > MAX_WORKERS:
            msg = f"max_workers не должен превышать {MAX_WORKERS}, получено {max_workers}"
            raise ValueError(msg)

    def acquire(self, *, blocking: bool = True, timeout: float | None = None) -> bool:
        """Захватывает слот семафора.

        Args:
            blocking: Блокировать ли если слоты недоступны.
            timeout: Таймаут ожидания в секундах.

        Returns:
            True если слот захвачен, False иначе.

        """
        acquired = self._semaphore.acquire(blocking=blocking, timeout=timeout)
        if acquired:
            with self._lock:
                self._acquired_count += 1
            logger.debug(
                "Слот семафора захвачен (активно: %d/%d)",
                self._acquired_count,
                self._max_workers + self._extra_slots,
            )
        return acquired

    def release(self) -> None:
        """Освобождает слот семафора.

        Raises:
            ValueError: Если семафор уже полностью освобождён.

        """
        try:
            with self._lock:
                if self._acquired_count > 0:
                    self._acquired_count -= 1
            self._semaphore.release()
            logger.debug(
                "Слот семафора освобождён (активно: %d/%d)",
                self._acquired_count,
                self._max_workers + self._extra_slots,
            )
        except ValueError as e:
            # Семафор уже полностью освобождён
            logger.warning("Попытка освободить семафор сверх лимита: %s", e)

    def get_available_slots(self) -> int:
        """Получает количество доступных слотов.

        Returns:
            Количество доступных слотов.

        """
        # BoundedSemaphore не предоставляет прямого способа получить количество доступных слотов
        # Используем счётчик
        with self._lock:
            return (self._max_workers + self._extra_slots) - self._acquired_count

    def get_acquired_count(self) -> int:
        """Получает количество захваченных слотов.

        Returns:
            Количество захваченных слотов.

        """
        with self._lock:
            return self._acquired_count

    def is_fully_acquired(self) -> bool:
        """Проверяет, все ли слоты захвачены.

        Returns:
            True если все слоты захвачены, False иначе.

        """
        return self.get_available_slots() == 0

    def get_stats(self) -> dict[str, Any]:
        """Получает статистику семафора.

        Returns:
            Словарь со статистикой:
            - max_workers: Максимальное количество рабочих
            - extra_slots: Дополнительные слоты
            - total_slots: Всего слотов
            - acquired: Захвачено слотов
            - available: Доступно слотов
            - utilization: Процент использования

        """
        with self._lock:
            total = self._max_workers + self._extra_slots
            acquired = self._acquired_count
            available = total - acquired
            utilization = (acquired / total * 100) if total > 0 else 0

            return {
                "max_workers": self._max_workers,
                "extra_slots": self._extra_slots,
                "total_slots": total,
                "acquired": acquired,
                "available": available,
                "utilization": round(utilization, 2),
            }

    def reset_stats(self) -> None:
        """Сбрасывает статистику."""
        with self._lock:
            self._acquired_count = 0
        logger.debug("Статистика SemaphoreManager сброшена")

    @property
    def semaphore(self) -> BoundedSemaphore:
        """Возвращает семафор для прямого использования."""
        return self._semaphore

    @property
    def max_workers(self) -> int:
        """Возвращает max_workers."""
        return self._max_workers

    @property
    def extra_slots(self) -> int:
        """Возвращает extra_slots."""
        return self._extra_slots


def get_semaphore_manager(max_workers: int = 3) -> SemaphoreManager:
    """Получает глобальный экземпляр SemaphoreManager (ленивая инициализация через замыкание).

    Args:
        max_workers: Максимальное количество рабочих потоков.

    Returns:
        Экземпляр SemaphoreManager.

    """
    if (
        not hasattr(get_semaphore_manager, "_instance")
        or get_semaphore_manager._instance.max_workers != max_workers
    ):
        get_semaphore_manager._instance = SemaphoreManager(max_workers=max_workers)  # type: ignore[attr-defined]
    return get_semaphore_manager._instance  # type: ignore[attr-defined,no-any-return]
