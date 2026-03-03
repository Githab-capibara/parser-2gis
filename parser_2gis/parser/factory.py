from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .parsers import FirmParser, InBuildingParser, MainParser

if TYPE_CHECKING:
    from ..chrome.options import ChromeOptions
    from ..parser.options import ParserOptions


def get_parser(url: str, chrome_options: ChromeOptions, parser_options: ParserOptions) -> MainParser | FirmParser | InBuildingParser:
    """Фабричная функция для получения парсера.

    Args:
        url: URL 2GIS с элементами для сбора.
        chrome_options: Опции Chrome.
        parser_options: Опции парсера.

    Returns:
        Экземпляр парсера.
    """
    for parser in (FirmParser, InBuildingParser, MainParser):
        if re.match(parser.url_pattern(), url):
            return parser(url, chrome_options, parser_options)

    # Резервный вариант по умолчанию
    return MainParser(url, chrome_options, parser_options)
