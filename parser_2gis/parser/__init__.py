"""Модуль парсера для 2GIS.

Предоставляет классы и функции для парсинга данных с 2GIS:
- ParserOptions - настройка параметров парсинга
- get_parser - фабрика для получения парсера
"""

# NOTE: Циклический импорт: constants -> parser -> parser.options -> utils -> constants
# Данный модуль импортируется из constants.py, но сам зависит от options,
# который зависит от utils, который зависит от constants.
from .factory import get_parser
from .options import ParserOptions

__all__ = ["ParserOptions", "get_parser"]
