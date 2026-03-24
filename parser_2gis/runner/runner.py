"""Модуль базового runner.

Предоставляет абстрактный класс AbstractRunner и реализацию GUIRunner:
- AbstractRunner - базовый класс для всех runner
- GUIRunner - заглушка для GUI режима парсинга (используется в тестах)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


class AbstractRunner(ABC):
    """Абстрактный базовый класс для всех runner.

    Args:
        urls: Список URL для парсинга.
        output_path: Путь к выходному файлу.
        format: Формат вывода (csv, xlsx, json).
        config: Конфигурация парсера.
    """

    def __init__(
        self, urls: list[str], output_path: str, format: str, config: Configuration
    ) -> None:
        self._urls = urls
        self._output_path = output_path
        self._format = format
        self._config = config

    @abstractmethod
    def start(self) -> None:
        """Запускает процесс парсинга."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Останавливает процесс парсинга."""
        ...


class GUIRunner(AbstractRunner):
    """Заглушка для GUI режима парсинга.

    Используется в тестах и для будущей интеграции с GUI.
    В текущей реализации методы start/stop не выполняют действий.

    Note:
        Этот класс существует для обратной совместимости тестов.
        В реальном приложении GUI режим использует TUI (Textual).
    """

    def start(self) -> None:
        """Запускает процесс парсинга в GUI режиме.

        Note:
            В текущей реализации метод не выполняет действий.
            Для GUI режима используется TUI (Textual).
        """
        pass

    def stop(self) -> None:
        """Останавливает процесс парсинга в GUI режиме.

        Note:
            В текущей реализации метод не выполняет действий.
            Для остановки GUI режима используется TUI (Textual).
        """
        pass


__all__ = ["AbstractRunner", "GUIRunner"]
