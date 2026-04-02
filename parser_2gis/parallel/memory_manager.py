"""Модуль управления памятью для параллельного парсинга.

Этот модуль предоставляет класс MemoryManager для:
- Мониторинга использования памяти
- Принудительного сбора мусора
- Обработки MemoryError
- Управления кэшем при нехватке памяти

ISSUE-019: Реализует протокол MemoryManagerProtocol из protocols.py.
ISSUE-152: Оптимизация gc.collect() с учётом размера памяти.
"""

from __future__ import annotations

import gc
import time
from typing import Any

from parser_2gis.constants import GC_MEMORY_THRESHOLD_MB
from parser_2gis.infrastructure import MemoryMonitor
from parser_2gis.logger.logger import logger
from parser_2gis.protocols import MemoryManagerProtocol


class MemoryManager(MemoryManagerProtocol):
    """Менеджер управления памятью.

    ISSUE-019: Реализует протокол MemoryManagerProtocol.

    Отвечает за:
    - Мониторинг доступной и используемой памяти
    - Принудительный сбор мусора (GC)
    - Обработку ситуаций нехватки памяти
    - Очистку кэшей при MemoryError

    Attributes:
        memory_threshold_mb: Порог нехватки памяти в MB (по умолчанию 100).

    """

    def __init__(self, memory_threshold_mb: int | None = None) -> None:
        """Инициализирует менеджер памяти.

        ISSUE-152: Использует константу GC_MEMORY_THRESHOLD_MB по умолчанию.

        Args:
            memory_threshold_mb: Порог нехватки памяти в мегабайтах.

        """
        self._memory_threshold_mb = memory_threshold_mb or GC_MEMORY_THRESHOLD_MB
        self._memory_monitor = MemoryMonitor()
        self._memory_warnings: int = 0
        self._gc_count: int = 0
        # H016: Кэширование результатов проверки памяти
        self._last_memory_check: float = 0.0
        self._last_memory_value: int = 0
        self._memory_cache_ttl: float = 1.0  # Кэшируем на 1 секунду

    def get_available_memory(self) -> int:
        """Получает доступный объем памяти в байтах.

        H016: Кэширует результат на 1 секунду для снижения накладных расходов.

        Returns:
            Доступный объем памяти в байтах.

        """
        current_time = time.time()
        # Возвращаем кэшированное значение если прошло меньше TTL
        if current_time - self._last_memory_check < self._memory_cache_ttl:
            return self._last_memory_value

        # Получаем новое значение
        self._last_memory_value = self._memory_monitor.get_available_memory()
        self._last_memory_check = current_time
        return self._last_memory_value

    def get_available_memory_mb(self) -> float:
        """Получает доступный объем памяти в мегабайтах.

        Returns:
            Доступный объем памяти в мегабайтах.

        """
        return self.get_available_memory() / (1024 * 1024)

    def is_memory_low(self) -> bool:
        """Проверяет, является ли доступная память низкой.

        Returns:
            True если доступная память ниже порога, False иначе.

        """
        available_mb = self.get_available_memory_mb()
        return available_mb < self._memory_threshold_mb

    def check_memory_and_warn(self, context: str = "") -> bool:
        """Проверяет память и выводит предупреждение если она низкая.

        Args:
            context: Контекст проверки (для логирования).

        Returns:
            True если память низкая, False иначе.

        """
        if self.is_memory_low():
            available_mb = self.get_available_memory_mb()
            self._memory_warnings += 1
            logger.warning(
                "Low memory detected (%.1f MB available) [%s] (warning #%d)",
                available_mb,
                context,
                self._memory_warnings,
            )
            return True
        return False

    def force_gc(self) -> int:
        """Выполняет принудительный сбор мусора.

        ISSUE-152: Оптимизация - проверяет размер памяти перед вызовом GC.
        Вызывает gc.collect() только если доступно меньше порога памяти.

        Returns:
            Количество собранных объектов (0 если GC не вызывался).

        """
        available_mb = self.get_available_memory_mb()

        # ISSUE-152: Вызываем GC только если память ниже порога
        if available_mb >= self._memory_threshold_mb:
            logger.debug(
                "GC пропущен: доступно %.1f MB (порог: %d MB)",
                available_mb,
                self._memory_threshold_mb,
            )
            return 0

        logger.debug(
            "Выполнение принудительного сбора мусора (GC): доступно %.1f MB (порог: %d MB)",
            available_mb,
            self._memory_threshold_mb,
        )
        collected = gc.collect()
        self._gc_count += 1
        logger.debug("GC завершён: собрано %d объектов (всего GC: %d)", collected, self._gc_count)
        return collected

    def handle_memory_error(
        self, error: MemoryError, context: str = "", cache_object: Any | None = None
    ) -> None:
        """Обрабатывает MemoryError.

        Args:
            error: Исключение MemoryError.
            context: Контекст ошибки (для логирования).
            cache_object: Объект кэша для очистки (опционально).

        """
        logger.error("MemoryError в контексте '%s': %s", context, error)

        # Очищаем кэш если предоставлен
        if cache_object is not None:
            try:
                if hasattr(cache_object, "clear"):
                    cache_object.clear()
                    logger.debug("Кэш очищен после MemoryError")
            except (AttributeError, RuntimeError, TypeError, ValueError) as cache_error:
                logger.warning("Ошибка при очистке кэша: %s", cache_error)

        # Принудительный GC
        self.force_gc()

        # Логируем текущее состояние памяти
        available_mb = self.get_available_memory_mb()
        logger.info("Состояние памяти после обработки MemoryError: %.1f MB доступно", available_mb)

    def get_memory_stats(self) -> dict[str, Any]:
        """Получает статистику использования памяти.

        Returns:
            Словарь со статистикой:
            - available_mb: Доступно памяти (MB)
            - is_low: Флаг низкой памяти
            - gc_count: Количество выполненных GC
            - memory_warnings: Количество предупреждений о памяти

        """
        return {
            "available_mb": self.get_available_memory_mb(),
            "is_low": self.is_memory_low(),
            "gc_count": self._gc_count,
            "memory_warnings": self._memory_warnings,
        }

    def reset_stats(self) -> None:
        """Сбрасывает статистику."""
        self._memory_warnings = 0
        self._gc_count = 0
        logger.debug("Статистика MemoryManager сброшена")


# Глобальный экземпляр для удобного доступа
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """Получает глобальный экземпляр MemoryManager.

    Returns:
        Экземпляр MemoryManager.

    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def check_memory_safety(context: str = "") -> bool:
    """Проверяет безопасность памяти и выполняет GC если нужно.

    Args:
        context: Контекст проверки.

    Returns:
        True если память в норме, False если низкая.

    """
    manager = get_memory_manager()

    if manager.is_memory_low():
        manager.check_memory_and_warn(context)
        manager.force_gc()
        return not manager.is_memory_low()

    return True
