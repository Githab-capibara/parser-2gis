"""Модуль базового runner.

Предоставляет абстрактный класс AbstractRunner:
- AbstractRunner - базовый класс для всех runner

Примечание:
    GUIRunner был удалён как неиспользуемый код (YAGNI).
    Для GUI режима используется TUI (Textual).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


class AbstractRunner(ABC):
    """Абстрактный базовый класс для всех runner.

    Определяет интерфейс для запуска и остановки процесса парсинга.
    Конкретные реализации (CLIRunner, TUIRunner) наследуются от этого класса.

    Example:
        >>> class MyRunner(AbstractRunner):
        ...     def start(self) -> None:
        ...         print("Запуск парсинга")
        ...     def stop(self) -> None:
        ...         print("Остановка парсинга")

    Args:
        urls: Список URL для парсинга.
        output_path: Путь к выходному файлу.
        output_format: Формат вывода (csv, xlsx, json).
        config: Конфигурация парсера.

    """

    def __init__(
        self,
        urls: list[str],
        output_path: str,
        output_format: str,
        config: Configuration,
    ) -> None:
        """Инициализирует базовый runner с параметрами парсинга.

        Args:
            urls: Список URL для парсинга.
            output_path: Путь к выходному файлу.
            output_format: Формат вывода (csv, xlsx, json).
            config: Конфигурация парсера.

        """
        self._urls = urls
        self._output_path = output_path
        self._output_format = output_format
        self._config = config

    @abstractmethod
    def start(self) -> None:
        """Запускает процесс парсинга."""

    @abstractmethod
    def stop(self) -> None:
        """Останавливает процесс парсинга."""


__all__ = ["AbstractRunner"]
