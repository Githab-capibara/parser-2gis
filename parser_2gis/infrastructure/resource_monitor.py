"""Модуль инфраструктуры для мониторинга ресурсов в parser-2gis.

Предоставляет абстракции для мониторинга системных ресурсов:
- MemoryInfo: информация об использовании памяти
- MemoryMonitor: мониторинг памяти с использованием psutil
- ResourceMonitor: общий мониторинг ресурсов (память, CPU)

H9: Выделение инфраструктурных зависимостей (psutil) в отдельный модуль.
ISSUE-166: Добавлено кэширование для часто вызываемых методов.
ISSUE-019: Dependency Injection — MemoryMonitor внедряется через конструктор.

Пример использования:
    >>> from parser_2gis.infrastructure.resource_monitor import ResourceMonitor
    >>> monitor = ResourceMonitor()
    >>> if monitor.is_memory_critical():
    ...     print("Критический уровень памяти!")
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemoryInfo:
    """Информация об использовании памяти в системе.

    Содержит данные об общем, использованном и доступном объёме памяти,
    а также процент использования. Предоставляет свойства для получения
    значений в байтах и мегабайтах.

    Attributes:
        total: Общий объём памяти в байтах.
        available: Доступный объём памяти в байтах.
        used: Использованный объём памяти в байтах.
        percent: Процент использования памяти (0-100).

    Example:
        >>> info = MemoryInfo(total=16000000000, available=8000000000,
        ...                   used=8000000000, percent=50.0)
        >>> print(f"Доступно: {info.available_mb:.2f} MB")
        Доступно: 7629.39 MB

    """

    total: int
    available: int
    used: int
    percent: float

    @property
    def available_mb(self) -> float:
        """Доступный объём памяти в мегабайтах.

        Returns:
            Доступная память в мегабайтах.

        """
        return self.available / (1024 * 1024)

    @property
    def used_mb(self) -> float:
        """Использованный объём памяти в мегабайтах.

        Returns:
            Использованная память в мегабайтах.

        """
        return self.used / (1024 * 1024)

    @property
    def total_mb(self) -> float:
        """Общий объём памяти в мегабайтах.

        Returns:
            Общая память в мегабайтах.

        """
        return self.total / (1024 * 1024)


class MemoryMonitor:
    """Монитор памяти на основе psutil для parser-2gis.

    H9: Инкапсуляция psutil зависимостей в инфраструктурном модуле.
    Предоставляет методы для получения информации о памяти и проверки
    низкого уровня доступной памяти.

    ISSUE 072: Реализует протокол MemoryManagerProtocol из protocols.py.

    Example:
        >>> monitor = MemoryMonitor()
        >>> info = monitor.get_memory_usage()
        >>> print(f"Доступно: {info.available_mb:.2f} MB")
        >>> if monitor.is_low_memory(threshold_mb=500):
        ...     print("Низкий уровень памяти!")

    """

    def get_available_memory(self) -> int:
        """Получает доступный объём памяти в байтах.

        Returns:
            Доступный объём памяти в байтах.

        Example:
            >>> monitor = MemoryMonitor()
            >>> available = monitor.get_available_memory()
            >>> print(f"Доступно: {available / (1024*1024):.2f} MB")

        """
        import psutil

        return psutil.virtual_memory().available

    def get_memory_usage(self) -> MemoryInfo:
        """Получает полную информацию об использовании памяти.

        Returns:
            MemoryInfo с информацией о памяти (total, available, used, percent).

        Example:
            >>> monitor = MemoryMonitor()
            >>> info = monitor.get_memory_usage()
            >>> print(f"Использовано: {info.used_mb:.2f} MB ({info.percent:.1f}%)")

        """
        import psutil

        mem = psutil.virtual_memory()
        return MemoryInfo(
            total=mem.total, available=mem.available, used=mem.used, percent=mem.percent
        )

    def is_low_memory(self, threshold_mb: float = 100.0) -> bool:
        """Проверяет низкий уровень памяти.

        Args:
            threshold_mb: Порог в мегабайтах для определения "низкой" памяти
                         (по умолчанию 100.0 MB).

        Returns:
            True если доступной памяти меньше порога.

        Example:
            >>> monitor = MemoryMonitor()
            >>> if monitor.is_low_memory(threshold_mb=500):
            ...     print("Меньше 500 MB доступно!")

        """
        return self.get_available_memory() < (threshold_mb * 1024 * 1024)


# =============================================================================
# PROTOCOL ДЛЯ MEMORY MONITOR (ISSUE-019: DIP)
# =============================================================================


class MemoryMonitorProtocol:
    """Protocol для MemoryMonitor (для type checking).

    ISSUE-019: Позволяет внедрять mock MemoryMonitor для тестирования.
    """

    def get_available_memory(self) -> int:
        """Получает доступный объём памяти в байтах."""

    def get_memory_usage(self) -> MemoryInfo:
        """Получает полную информацию об использовании памяти."""

    def is_low_memory(self, threshold_mb: float = 100.0) -> bool:
        """Проверяет низкий уровень памяти."""


# =============================================================================
# RESOURCE MONITOR (ISSUE-019: DIP)
# =============================================================================


class ResourceMonitor:
    """Общий монитор системных ресурсов для parser-2gis.

    Предоставляет расширенный мониторинг ресурсов системы:
    - Мониторинг памяти через MemoryMonitor
    - Мониторинг использования CPU
    - Проверка памяти перед операциями

    ISSUE-166: Добавлено кэширование для часто вызываемых методов.
    ISSUE-019: Dependency Injection — MemoryMonitor внедряется через конструктор.

    Example:
        >>> monitor = ResourceMonitor()
        >>> if monitor.is_memory_critical():
        ...     print("Критический уровень памяти!")
        >>> cpu = monitor.get_cpu_usage()
        >>> print(f"CPU: {cpu:.1f}%")

    """

    def __init__(self, memory_monitor: MemoryMonitor | None = None) -> None:
        """Инициализация монитора ресурсов.

        ISSUE-019: MemoryMonitor внедряется через конструктор для улучшения
        тестируемости и снижения связности.

        Args:
            memory_monitor: Опциональный MemoryMonitor для DI.
                           Если не передан, создаётся по умолчанию.

        Example:
            >>> # Использование по умолчанию
            >>> monitor = ResourceMonitor()
            >>> # Использование с внедрённой зависимостью (для тестирования)
            >>> mock_monitor = MockMemoryMonitor()
            >>> monitor = ResourceMonitor(memory_monitor=mock_monitor)

        """
        self._memory_monitor = memory_monitor or MemoryMonitor()

    def get_memory_monitor(self) -> MemoryMonitor:
        """Получает монитор памяти.

        Returns:
            Экземпляр MemoryMonitor для мониторинга памяти.

        """
        return self._memory_monitor

    def is_memory_critical(self, threshold_mb: float = 50.0) -> bool:
        """Проверяет критический уровень памяти.

        Args:
            threshold_mb: Порог в мегабайтах для критического уровня
                         (по умолчанию 50.0 MB).

        Returns:
            True если память на критическом уровне.

        Example:
            >>> monitor = ResourceMonitor()
            >>> if monitor.is_memory_critical():
            ...     print("Критический уровень памяти!")

        """
        return self._memory_monitor.is_low_memory(threshold_mb)

    def check_memory_before_operation(
        self, required_mb: float = 100.0, threshold_mb: float = 100.0
    ) -> bool:
        """Проверяет память перед операцией.

        Args:
            required_mb: Требуемый объём памяти в мегабайтах для операции.
            threshold_mb: Минимальный порог свободной памяти в мегабайтах.

        Returns:
            True если операция может быть выполнена (достаточно памяти).

        Example:
            >>> monitor = ResourceMonitor()
            >>> if monitor.check_memory_before_operation(required_mb=500):
            ...     perform_memory_intensive_operation()

        """
        available_mb = self._memory_monitor.get_memory_usage().available_mb
        return available_mb >= (required_mb + threshold_mb)

    def get_cpu_usage(self, interval: float = 0.1) -> float:
        """Получает процент использования CPU.

        ISSUE-166: Убран lru_cache с метода экземпляра для предотвращения утечки памяти.
        #153: Метод выполняет измерения напрямую без кэширования.

        Args:
            interval: Интервал измерения в секундах (по умолчанию 0.1 сек).

        Returns:
            Процент использования CPU (0-100).

        Example:
            >>> monitor = ResourceMonitor()
            >>> cpu = monitor.get_cpu_usage(interval=0.5)
            >>> print(f"CPU usage: {cpu:.1f}%")

        """
        import psutil

        return psutil.cpu_percent(interval=interval)


__all__ = ["MemoryInfo", "MemoryMonitor", "ResourceMonitor"]
