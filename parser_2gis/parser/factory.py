import re

from .parsers import FirmParser, InBuildingParser, MainParser


def get_parser(url, chrome_options, parser_options):
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
