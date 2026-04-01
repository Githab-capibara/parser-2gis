"""Модуль парсера для 2GIS.

Предоставляет классы и функции для парсинга данных с 2GIS:
- ParserOptions - настройка параметров парсинга
- get_parser - фабрика для получения парсера
"""

from .factory import get_parser
from .options import ParserOptions

__all__ = ["ParserOptions", "get_parser"]
