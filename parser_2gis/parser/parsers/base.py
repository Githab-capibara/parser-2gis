"""Абстрактный базовый класс для всех парсеров.

Предоставляет ABC (Abstract Base Class) BaseParser с обязательмыми методами:
- parse() — основной метод парсинга
- get_stats() — получение статистики парсинга

Все парсеры должны наследоваться от этого класса и реализовывать
абстрактные методы.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from parser_2gis.protocols import BrowserService
    from parser_2gis.writer import FileWriter


class ParserStats(dict[str, int]):
    """TypedDict-совместимый словарь для статистики парсера.

    P1-7: Замена dict[str, Any] на типизированный словарь для лучшей типизации.
    """

    parsed: int
    errors: int
    skipped: int


class BaseParser(ABC):
    """Абстрактный базовый класс для всех парсеров.

    Этот класс определяет общий интерфейс для всех парсеров проекта.
    Каждый парсер должен реализовать следующие абстрактные методы:
    - parse() — основной метод парсинга данных
    - get_stats() — получение статистики работы парсера

    Attributes:
        _browser: Объект BrowserService для работы с браузером.
        _stats: Словарь для хранения статистики парсера.

    """

    def __init__(self, browser: BrowserService) -> None:
        """Инициализация базового парсера.

        Args:
            browser: Объект BrowserService для работы с браузером.

        Создаёт словарь для хранения статистики парсера.
        Дочерние классы должны расширять этот словарь своими полями.

        """
        self._browser = browser
        self._stats: ParserStats = ParserStats(parsed=0, errors=0, skipped=0)

    def __enter__(self) -> Self:
        """Контекстный менеджер — вход.

        Returns:
            Экземпляр парсера.

        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Контекстный менеджер — выход. Никого не глотает исключения."""
        return None

    @property
    def _chrome_remote(self) -> BrowserService:
        """Алиас для _browser для обратной совместимости.

        Returns:
            Объект BrowserService для работы с браузером.

        """
        return self._browser

    @abstractmethod
    def parse(self, writer: FileWriter) -> None:
        """Основной метод парсинга данных.

        Args:
            writer: Объект FileWriter для записи распарсенных данных.

        """
        raise NotImplementedError("Subclasses must implement this method")  # pragma: no cover

    @abstractmethod
    def get_stats(self) -> ParserStats:
        """Получение статистики работы парсера.

        Returns:
            Словарь со статистикой парсера.

        """
        raise NotImplementedError("Subclasses must implement this method")  # pragma: no cover

    def __repr__(self) -> str:
        """Строковое представление парсера.

        Returns:
            Строка с названием класса и статистикой.

        """
        stats_str = ", ".join(f"{k}={v}" for k, v in self._stats.items())
        return f"{self.__class__.__name__}({stats_str})"
