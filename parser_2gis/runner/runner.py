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

    Args:
        urls: Список URL для парсинга.
        output_path: Путь к выходному файлу.
        format: Формат вывода (csv, xlsx, json).
        config: Конфигурация парсера.
    """

    def __init__(
        self, urls: list[str], output_path: str, format: str, config: "Configuration"
    ) -> None:
        self._urls = urls
        self._output_path = output_path
        self._format = format
        self._config = config

    @abstractmethod
    def start(self) -> None:
        """Запускает процесс парсинга."""

    @abstractmethod
    def stop(self) -> None:
        """Останавливает процесс парсинга."""


__all__ = ["AbstractRunner"]
