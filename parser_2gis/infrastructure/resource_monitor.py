"""
Модуль инфраструктуры для мониторинга ресурсов.

Предоставляет абстракции для мониторинга системных ресурсов:
- MemoryMonitor: мониторинг памяти
- ResourceMonitor: общий мониторинг ресурсов

H9: Выделение инфраструктурных зависимостей (psutil) в отдельный модуль.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class ResourceMonitorProtocol(Protocol):
    """Protocol для монитора ресурсов.

    Определяет интерфейс для всех мониторов ресурсов.
    """

    def get_available_memory(self) -> int:
        """Получает доступный объём памяти в байтах."""
        ...

    def get_memory_usage(self) -> "MemoryInfo":
        """Получает информацию об использовании памяти."""
        ...


@dataclass
class MemoryInfo:
    """Информация об использовании памяти.

    Attributes:
        total: Общий объём памяти в байтах.
        available: Доступный объём памяти в байтах.
        used: Использованный объём памяти в байтах.
        percent: Процент использования памяти.
    """

    total: int
    available: int
    used: int
    percent: float

    @property
    def available_mb(self) -> float:
        """Доступный объём памяти в мегабайтах."""
        return self.available / (1024 * 1024)

    @property
    def used_mb(self) -> float:
        """Использованный объём памяти в мегабайтах."""
        return self.used / (1024 * 1024)

    @property
    def total_mb(self) -> float:
        """Общий объём памяти в мегабайтах."""
        return self.total / (1024 * 1024)


class MemoryMonitor:
    """Монитор памяти на основе psutil.

    H9: Инкапсуляция psutil зависимостей в инфраструктурном модуле.

    Example:
        >>> monitor = MemoryMonitor()
        >>> info = monitor.get_memory_usage()
        >>> print(f"Доступно: {info.available_mb:.2f} MB")
    """

    def get_available_memory(self) -> int:
        """Получает доступный объём памяти в байтах.

        Returns:
            Доступный объём памяти в байтах.
        """
        import psutil

        return psutil.virtual_memory().available

    def get_memory_usage(self) -> MemoryInfo:
        """Получает полную информацию об использовании памяти.

        Returns:
            MemoryInfo с информацией о памяти.
        """
        import psutil

        mem = psutil.virtual_memory()
        return MemoryInfo(
            total=mem.total, available=mem.available, used=mem.used, percent=mem.percent
        )

    def is_low_memory(self, threshold_mb: float = 100.0) -> bool:
        """Проверяет низкий уровень памяти.

        Args:
            threshold_mb: Порог в мегабайтах для определения "низкой" памяти.

        Returns:
            True если памяти меньше порога.
        """
        return self.get_available_memory() < (threshold_mb * 1024 * 1024)


class ResourceMonitor:
    """Общий монитор системных ресурсов.

    Предоставляет расширенный мониторинг ресурсов системы.

    Example:
        >>> monitor = ResourceMonitor()
        >>> if monitor.is_memory_critical():
        >>>     print("Критический уровень памяти!")
    """

    def __init__(self) -> None:
        """Инициализация монитора ресурсов."""
        self._memory_monitor = MemoryMonitor()

    def get_memory_monitor(self) -> MemoryMonitor:
        """Получает монитор памяти.

        Returns:
            Экземпляр MemoryMonitor.
        """
        return self._memory_monitor

    def is_memory_critical(self, threshold_mb: float = 50.0) -> bool:
        """Проверяет критический уровень памяти.

        Args:
            threshold_mb: Порог в мегабайтах для критического уровня.

        Returns:
            True если память на критическом уровне.
        """
        return self._memory_monitor.is_low_memory(threshold_mb)

    def check_memory_before_operation(
        self, required_mb: float = 100.0, threshold_mb: float = 100.0
    ) -> bool:
        """Проверяет память перед операцией.

        Args:
            required_mb: Требуемый объём памяти в мегабайтах.
            threshold_mb: Минимальный порог свободной памяти.

        Returns:
            True если операция может быть выполнена.
        """
        available_mb = self._memory_monitor.get_memory_usage().available_mb
        return available_mb >= (required_mb + threshold_mb)


# =============================================================================
# FACADE ДЛЯ МОНИТОРИНГА РЕСУРСОВ
# =============================================================================


class ResourceMonitorFacade:
    """Фасад для мониторинга ресурсов.

    Упрощает использование мониторов ресурсов, предоставляя
    простой интерфейс для типичных операций.

    Example:
        >>> facade = ResourceMonitorFacade()
        >>> if facade.has_enough_memory(200):
        >>>     # Выполнить операцию требующую 200MB
        >>>     pass
    """

    def __init__(self) -> None:
        """Инициализация фасада."""
        self._monitor = ResourceMonitor()

    def has_enough_memory(self, required_mb: float = 100.0) -> bool:
        """Проверяет достаточно ли памяти.

        Args:
            required_mb: Требуемый объём памяти в мегабайтах.

        Returns:
            True если памяти достаточно.
        """
        return self._monitor.check_memory_before_operation(required_mb)

    def get_available_memory_mb(self) -> float:
        """Получает доступный объём памяти в мегабайтах.

        Returns:
            Доступный объём памяти в MB.
        """
        return self._monitor.get_memory_monitor().get_memory_usage().available_mb

    def is_memory_low(self, threshold_mb: float = 100.0) -> bool:
        """Проверяет низкий уровень памяти.

        Args:
            threshold_mb: Порог в мегабайтах.

        Returns:
            True если памяти меньше порога.
        """
        return self._monitor.get_memory_monitor().is_low_memory(threshold_mb)


__all__ = [
    "MemoryInfo",
    "MemoryMonitor",
    "ResourceMonitor",
    "ResourceMonitorFacade",
    "ResourceMonitorProtocol",
]
