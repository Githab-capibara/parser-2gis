"""Фабричный модуль парсеров.

Предоставляет фабричную функцию get_parser для получения экземпляра
парсера в зависимости от URL (MainParser, FirmParser, InBuildingParser).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .parsers import FirmParser, InBuildingParser, MainParser

if TYPE_CHECKING:
    from parser_2gis.chrome.options import ChromeOptions
    from parser_2gis.parser.options import ParserOptions

_PARSER_PATTERNS: list[tuple[type, re.Pattern]] = [
    (FirmParser, re.compile(FirmParser.url_pattern())),
    (InBuildingParser, re.compile(InBuildingParser.url_pattern())),
    (MainParser, re.compile(MainParser.url_pattern())),
]


def get_parser(
    url: str, chrome_options: ChromeOptions, parser_options: ParserOptions
) -> MainParser | FirmParser | InBuildingParser:
    """Фабричная функция для получения парсера.

    Args:
        url: URL 2GIS с элементами для сбора.
        chrome_options: Опции Chrome.
        parser_options: Опции парсера.

    Returns:
        Экземпляр парсера.
    """
    for parser_cls, pattern in _PARSER_PATTERNS:
        if pattern.match(url):
            return parser_cls(url, chrome_options, parser_options)

    return MainParser(url, chrome_options, parser_options)
