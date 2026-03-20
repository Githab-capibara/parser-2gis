"""Модуль базового runner.

Предоставляет абстрактный класс AbstractRunner и реализацию GUIRunner:
- AbstractRunner - базовый класс для всех runner
- GUIRunner - заглушка для GUI режима парсинга
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Configuration


class AbstractRunner(ABC):
    def __init__(
        self, urls: list[str], output_path: str, format: str, config: Configuration
    ):
        self._urls = urls
        self._output_path = output_path
        self._format = format
        self._config = config

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class GUIRunner(AbstractRunner):
    """Простейшая заглушка GUIRunner для тестов.

    Наследуется от AbstractRunner и предоставляет методы start/stop.
    В рамках тестов поведение не требуется; важна лишь корректная инициализация.
    """

    def start(self):  # type: ignore[override]
        # В реальном приложении здесь запуск GUI и параллельного парсинга
        return None

    def stop(self):  # type: ignore[override]
        # Остановка GUI/процесса парсинга
        return None
