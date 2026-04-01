"""Абстрактный базовый класс для всех парсеров.

Предоставляет ABC (Abstract Base Class) BaseParser с обязательными методами:
- parse() — основной метод парсинга
- get_stats() — получение статистики парсинга

Все парсеры должны наследоваться от этого класса и реализовывать
абстрактные методы.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from parser_2gis.protocols import BrowserService
    from parser_2gis.writer import FileWriter


class BaseParser(ABC):
    """Абстрактный базовый класс для всех парсеров.

    Этот класс определяет общий интерфейс для всех парсеров проекта.
    Каждый парсер должен реализовать следующие абстрактные методы:
    - parse() — основной метод парсинга данных
    - get_stats() — получение статистики работы парсера

    Пример использования:
        >>> from parser_2gis.protocols import BrowserService
        >>> class MyParser(BaseParser):
        ...     def __init__(self, browser: BrowserService):
        ...         super().__init__(browser)
        ...
        ...     def parse(self, writer: FileWriter) -> None:
        ...         # Реализация парсинга
        ...         pass
        ...
        ...     def get_stats(self) -> Dict[str, Any]:
        ...         # Возврат статистики
        ...         return {"parsed": 100}

    Пример наследования:
        >>> from parser_2gis.parser.parsers.base import BaseParser
        >>> from parser_2gis.protocols import BrowserService
        >>> from parser_2gis.writer import FileWriter
        >>>
        >>> class FirmParser(BaseParser):
        ...     def __init__(self, browser: BrowserService):
        ...         super().__init__(browser)
        ...         self._stats = {"parsed": 0, "errors": 0}
        ...
        ...     def parse(self, writer: FileWriter) -> None:
        ...         # Парсинг данных фирмы
        ...         self._stats["parsed"] += 1
        ...
        ...     def get_stats(self) -> Dict[str, Any]:
        ...         return self._stats

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
        self._stats: dict[str, Any] = {"parsed": 0, "errors": 0, "skipped": 0}

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

        Этот метод должен быть реализован в каждом конкретном парсере
        и содержать логику извлечения данных из источника.

        Args:
            writer: Объект FileWriter для записи распарсенных данных.

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.

        Пример реализации:
            >>> def parse(self, writer: FileWriter) -> None:
            ...     data = self._extract_data()
            ...     writer.write(data)
            ...     self._stats["parsed"] += 1

        """
        pass  # pragma: no cover

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Получение статистики работы парсера.

        Этот метод должен быть реализован в каждом конкретном парсере
        и возвращать словарь со статистикой работы.

        Returns:
            Словарь со статистикой парсера. Обычно включает:
            - parsed: количество распарсенных элементов
            - errors: количество ошибок
            - skipped: количество пропущенных элементов

        Raises:
            NotImplementedError: Если метод не реализован в дочернем классе.

        Пример реализации:
            >>> def get_stats(self) -> Dict[str, Any]:
            ...     return {
            ...         "parsed": self._stats["parsed"],
            ...         "errors": self._stats["errors"],
            ...         "skipped": self._stats["skipped"],
            ...     }

        """
        pass  # pragma: no cover

    def __repr__(self) -> str:
        """Строковое представление парсера.

        Returns:
            Строка с названием класса и статистикой.

        """
        stats_str = ", ".join(f"{k}={v}" for k, v in self._stats.items())
        return f"{self.__class__.__name__}({stats_str})"
