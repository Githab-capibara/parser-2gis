"""Протоколы для подсистемы параллельного парсинга.

Определяет интерфейсы для координации, объединения файлов и управления сигналами:
- CoordinatorProtocol — интерфейс координатора параллельного парсинга
- FileMergerProtocol — интерфейс объединителя файлов
- TempFileManagerProtocol — интерфейс менеджера временных файлов
- SignalHandlerProtocol — интерфейс обработчика сигналов

ISSUE 071: Создание protocols.py для параллельной подсистемы.
ISSUE 073: Создание SignalHandlerProtocol.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass

type UrlTuple = tuple[str, str, str]  # (url, category_name, city_name)


@runtime_checkable
class CoordinatorProtocol(Protocol):
    """Протокол координатора параллельного парсинга.

    ISSUE 071: Определяет интерфейс координатора для устранения
    прямой зависимости от конкретной реализации.
    """

    def run(
        self,
        output_file: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
        merge_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг всех городов и категорий."""
        ...

    def stop(self) -> None:
        """Останавливает парсинг."""
        ...

    def get_statistics(self) -> dict[str, Any]:
        """Возвращает статистику парсинга."""
        ...


@runtime_checkable
class FileMergerProtocol(Protocol):
    """Протокол объединителя файлов.

    ISSUE 071: Определяет интерфейс для объединения выходных файлов.
    """

    def merge_csv_files(
        self,
        output_file: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Объединяет CSV файлы в один выходной файл."""
        ...


@runtime_checkable
class TempFileManagerProtocol(Protocol):
    """Протокол менеджера временных файлов.

    ISSUE 071: Определяет интерфейс для управления временными файлами.
    """

    def register(self, file_path: Path) -> None:
        """Регистрирует временный файл для последующей очистки."""
        ...

    def unregister(self, file_path: Path) -> None:
        """Удаляет файл из реестра."""
        ...

    def cleanup_all(self) -> tuple[int, int]:
        """Очищает все зарегистрированные временные файлы."""
        ...

    def get_count(self) -> int:
        """Возвращает количество зарегистрированных файлов."""
        ...


@runtime_checkable
class SignalHandlerProtocol(Protocol):
    """Протокол обработчика сигналов.

    ISSUE 073: Определяет интерфейс для обработки системных сигналов
    (SIGINT, SIGTERM) в координаторах параллельного парсинга.
    """

    def __call__(self, signum: int, frame: Any | None) -> None:
        """Вызывается при получении сигнала."""
        ...

    def is_interrupt_requested(self) -> bool:
        """Проверяет, запрошена ли прерывание."""
        ...

    def reset(self) -> None:
        """Сбрасывает состояние обработчика сигналов."""
        ...


@runtime_checkable
class MemoryMonitorProtocol(Protocol):
    """Протокол мониторинга памяти.

    Определяет интерфейс для получения информации о памяти системы.
    """

    def get_available_memory(self) -> int:
        """Получает доступный объем памяти в байтах."""
        ...


__all__ = [
    "CoordinatorProtocol",
    "FileMergerProtocol",
    "MemoryMonitorProtocol",
    "SignalHandlerProtocol",
    "TempFileManagerProtocol",
    "UrlTuple",
]
