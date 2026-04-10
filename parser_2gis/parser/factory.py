"""Фабричный модуль парсеров.

Предоставляет фабричную функцию get_parser для получения экземпляра
парсера в зависимости от URL (MainParser, FirmParser, InBuildingParser).

Использует Registry pattern для регистрации и получения parser классов.
Это позволяет добавлять новые парсеры без модификации фабричной функции.

ISSUE-033: Используется plugin discovery через importlib для автоматического
обнаружения и регистрации парсеров из entry_points.

Пример регистрации нового парсера:
    >>> from parser_2gis.parser.factory import register_parser, get_parser
    >>> @register_parser(priority=10)
    ... class CustomParser(BaseParser):
    ...     @staticmethod
    ...     def url_pattern() -> str:
    ...         return r".*custom.*"
    >>> parser = get_parser(url, chrome_options, parser_options)
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .parsers import FirmParser, InBuildingParser, MainParser
from .parsers.base import BaseParser

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from parser_2gis.chrome.options import ChromeOptions
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.protocols import BrowserService

# =============================================================================
# PARSER REGISTRY CLASS (ISSUE 064: Инкапсуляция реестра парсеров)
# =============================================================================


class ParserRegistry:
    """Реестр парсеров с инкапсуляцией и thread-safe доступом.

    ISSUE 064: Оборачивает PARSER_REGISTRY и _PARSER_PATTERNS в класс
    с надлежащей инкапсуляцией.
    """

    def __init__(self) -> None:
        """Инициализирует реестр парсеров."""
        self._registry: dict[str, type[BaseParser]] = {}
        self._patterns: list[tuple[type[BaseParser], re.Pattern[str]]] = []
        self._lock = threading.Lock()

    def register(self, parser_cls: type[BaseParser], _priority: int = 0) -> None:
        """Регистрирует класс парсера в реестре.

        Args:
            parser_cls: Класс парсера.
            _priority: Приоритет (чем выше, тем раньше проверяется).

        """
        with self._lock:
            self._registry[parser_cls.__name__] = parser_cls

            try:
                pattern_str = parser_cls.url_pattern()
                compiled_pattern = re.compile(pattern_str)
                self._patterns.append((parser_cls, compiled_pattern))

                # Сортируем по приоритету (убывание) и имени (возрастание)
                self._patterns.sort(key=lambda x: (-getattr(x[0], "priority", 0), x[0].__name__))
            except (AttributeError, TypeError) as e:
                logger.warning(
                    "Парсер %s не имеет url_pattern, пропускаем регистрацию: %s",
                    parser_cls.__name__,
                    e,
                )

    def unregister(self, parser_name: str) -> None:
        """Удаляет парсер из реестра.

        Args:
            parser_name: Имя парсера для удаления.

        """
        with self._lock:
            self._registry.pop(parser_name, None)
            self._patterns = [
                (cls, pat) for cls, pat in self._patterns if cls.__name__ != parser_name
            ]

    def find_parser(self, url: str) -> type[BaseParser] | None:
        """Находит парсер по URL.

        Args:
            url: URL для поиска парсера.

        Returns:
            Класс парсера или None если не найден.

        """
        with self._lock:
            for parser_cls, pattern in self._patterns:
                if pattern.match(url):
                    return parser_cls
        return None

    def get_registry(self) -> dict[str, type[BaseParser]]:
        """Возвращает копию реестра.

        Returns:
            Словарь {название_парсера: класс_парсера}.

        """
        with self._lock:
            return self._registry.copy()

    def clear(self) -> None:
        """Очищает реестр."""
        with self._lock:
            self._registry.clear()
            self._patterns.clear()

    @property
    def patterns(self) -> list[tuple[type[BaseParser], re.Pattern[str]]]:
        """Возвращает список паттернов (для обратной совместимости).

        Returns:
            Список кортежей (parser_class, compiled_pattern).

        """
        with self._lock:
            return list(self._patterns)


# Глобальный экземпляр реестра для обратной совместимости
_parser_registry = ParserRegistry()

# Алиасы для обратной совместимости
PARSER_REGISTRY = _parser_registry._registry
_PARSER_PATTERNS = _parser_registry.patterns


def register_parser(priority: int = 0) -> Callable[..., Any]:
    """Декоратор для регистрации parser класса в реестре.

    Args:
        priority: Приоритет парсера (чем выше, тем раньше проверяется).
                  Парсеры с одинаковым приоритетом сортируются по имени.

    Returns:
        Декоратор для регистрации класса.

    Example:
        >>> @register_parser(priority=10)
        ... class CustomParser(BaseParser):
        ...     @staticmethod
        ...     def url_pattern() -> str:
        ...         return r".*custom.*"

    Raises:
        ValueError: Если priority отрицательный.

    """

    def decorator(parser_cls: type[BaseParser]) -> type[BaseParser]:
        """Декоратор для регистрации парсера."""
        # Валидация priority
        if priority < 0:
            raise ValueError(f"Приоритет парсера не может быть отрицательным: {priority}")

        # Регистрируем через ParserRegistry
        _parser_registry.register(parser_cls, priority)

        return parser_cls

    return decorator


def get_parser(
    url: str,
    chrome_options: ChromeOptions,
    parser_options: ParserOptions,
    browser: BrowserService | None = None,
) -> BaseParser:
    """Фабричная функция для получения парсера.

    Использует реестр для сопоставления URL с соответствующим парсером.

    Args:
        url: URL 2GIS с элементами для сбора.
        chrome_options: Опции Chrome.
        parser_options: Опции парсера.
        browser: Опциональный объект BrowserService. Если не передан,
                 парсер создаст внутренний ChromeRemote.

    Returns:
        Экземпляр парсера соответствующий URL.
        Если ни один паттерн не подошёл, возвращается MainParser.

    Example:
        >>> parser = get_parser(url, chrome_options, parser_options)
        >>> parser.parse()

    """
    parser_cls = _parser_registry.find_parser(url)
    if parser_cls is not None:
        return parser_cls(url, chrome_options, parser_options, browser=browser)

    # ISSUE 078: Возвращаем MainParser как явно помеченный fallback
    from parser_2gis.logger.logger import logger as fallback_logger

    fallback_logger.warning(
        "Не найден специализированный парсер для URL: %s. Используется MainParser по умолчанию.",
        url,
    )
    return MainParser(url, chrome_options, parser_options, browser=browser)


def get_registered_parsers() -> dict[str, type[BaseParser]]:
    """Возвращает словарь зарегистрированных парсеров.

    Returns:
        Словарь {название_парсера: класс_парсера}.

    """
    return _parser_registry.get_registry()


def clear_parser_registry() -> None:
    """Очищает реестр парсеров.

    Полезно для тестирования или перерегистрации парсеров.
    """
    _parser_registry.clear()


def get_parser_registry() -> ParserRegistry:
    """Возвращает экземпляр реестра парсеров.

    Returns:
        Экземпляр ParserRegistry.

    """
    return _parser_registry


# =============================================================================
# РЕГИСТРАЦИЯ ВСТРОЕННЫХ PARSERS
# =============================================================================

# Регистрируем встроенные parser классы с приоритетами
# Приоритет определяет порядок проверки паттернов (чем выше, тем раньше)
register_parser(priority=100)(FirmParser)
register_parser(priority=50)(InBuildingParser)
register_parser(priority=0)(MainParser)


# =============================================================================
# PLUGIN DISCOVERY (ISSUE-033)
# =============================================================================


def _discover_parsers_via_importlib() -> None:
    """Автоматически обнаруживает и регистрирует парсеры через importlib.

    ISSUE-033: Plugin discovery вместо жёсткой регистрации.
    Сканирует пакет parser_2gis.parser.parsers на наличие классов,
    наследующих BaseParser и имеющих метод url_pattern().
    """
    try:
        import parser_2gis.parser.parsers as parsers_pkg

        pkg_path = getattr(parsers_pkg, "__path__", None)
        if pkg_path is None:
            return

        # Импортируем все модули из пакета parsers
        import importlib.util

        for _finder, module_name, _is_pkg in getattr(
            __import__("pkgutil"), "_iter_importers", lambda *_: [],
        )(parsers_pkg, parsers_pkg.__name__, pkg_path):
            if module_name.startswith("_") or module_name in ("base", "__init__"):
                continue

            try:
                full_module_name = f"parser_2gis.parser.parsers.{module_name}"
                if full_module_name not in sys.modules:
                    importlib.import_module(full_module_name)
            except (ImportError, ModuleNotFoundError):
                pass
    except (ImportError, AttributeError):
        pass  # Если пакет parsers не найден, пропускаем


def auto_discover_parsers() -> None:
    """Автоматически обнаруживает и регистрирует все доступные парсеры.

    ISSUE-033: Комбинирует встроенную регистрацию и plugin discovery.

    Example:
        >>> from parser_2gis.parser.factory import auto_discover_parsers
        >>> auto_discover_parsers()
        >>> parsers = get_registered_parsers()

    """
    _discover_parsers_via_importlib()


# Автоматическое обнаружение парсеров при импорте модуля
auto_discover_parsers()


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "PARSER_REGISTRY",
    "_PARSER_PATTERNS",
    "ParserRegistry",
    "auto_discover_parsers",
    "clear_parser_registry",
    "get_parser",
    "get_parser_registry",
    "get_registered_parsers",
    "register_parser",
]
