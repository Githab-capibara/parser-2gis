"""Фабричный модуль парсеров.

Предоставляет фабричную функцию get_parser для получения экземпляра
парсера в зависимости от URL (MainParser, FirmParser, InBuildingParser).

Использует Registry pattern для регистрации и получения parser классов.
Это позволяет добавлять новые парсеры без модификации фабричной функции.

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

import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Type

if TYPE_CHECKING:
    from parser_2gis.chrome.options import ChromeOptions
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.protocols import BrowserService

from .parsers import FirmParser, InBuildingParser, MainParser
from .parsers.base import BaseParser

# =============================================================================
# REGISTRY PATTERN ДЛЯ PARSERS
# =============================================================================

PARSER_REGISTRY: Dict[str, Type[BaseParser]] = {}
"""Реестр зарегистрированных parser классов по названию."""

_PARSER_PATTERNS: List[Tuple[Type[BaseParser], re.Pattern]] = []
"""Список кортежей (parser_class, compiled_pattern) для сопоставления URL."""


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
    """

    def decorator(cls: Type[BaseParser]) -> Type[BaseParser]:
        # Регистрируем класс в реестре
        PARSER_REGISTRY[cls.__name__] = cls

        # Компилируем паттерн и добавляем в список
        try:
            pattern_str = cls.url_pattern()
            compiled_pattern = re.compile(pattern_str)
            _PARSER_PATTERNS.append((cls, compiled_pattern))

            # Сортируем по приоритету (убывание) и имени (возрастание)
            _PARSER_PATTERNS.sort(key=lambda x: (-getattr(x[0], "priority", 0), x[0].__name__))
        except (AttributeError, TypeError) as e:
            # Если у класса нет url_pattern, пропускаем его
            import logging

            logging.getLogger(__name__).warning(
                "Парсер %s не имеет url_pattern, пропускаем регистрацию: %s", cls.__name__, e
            )

        return cls

    return decorator


def get_parser(
    url: str,
    chrome_options: ChromeOptions,
    parser_options: ParserOptions,
    browser: Optional[BrowserService] = None,
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
    for parser_cls, pattern in _PARSER_PATTERNS:
        if pattern.match(url):
            return parser_cls(url, chrome_options, parser_options, browser=browser)

    # Возвращаем парсер по умолчанию
    return MainParser(url, chrome_options, parser_options, browser=browser)


def get_registered_parsers() -> Dict[str, Type[BaseParser]]:
    """Возвращает словарь зарегистрированных парсеров.

    Returns:
        Словарь {название_парсера: класс_парсера}.
    """
    return PARSER_REGISTRY.copy()


def clear_parser_registry() -> None:
    """Очищает реестр парсеров.

    Полезно для тестирования или перерегистрации парсеров.
    """
    global _PARSER_PATTERNS, PARSER_REGISTRY
    PARSER_REGISTRY.clear()
    _PARSER_PATTERNS.clear()


# =============================================================================
# РЕГИСТРАЦИЯ ВСТРОЕННЫХ PARSERS
# =============================================================================

# Регистрируем встроенные parser классы с приоритетами
# Приоритет определяет порядок проверки паттернов (чем выше, тем раньше)
register_parser(priority=100)(FirmParser)
register_parser(priority=50)(InBuildingParser)
register_parser(priority=0)(MainParser)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "get_parser",
    "register_parser",
    "get_registered_parsers",
    "clear_parser_registry",
    "PARSER_REGISTRY",
    "_PARSER_PATTERNS",
]
