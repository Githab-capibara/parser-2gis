"""Модуль парсера для 2GIS.

Предоставляет классы и функции для парсинга данных с 2GIS:
- ParserOptions - настройка параметров парсинга
- get_parser - фабрика для получения парсера

ISSUE-041: Устранён цикл импортов — parser.options больше не импортирует из constants.
"""
from .factory import get_parser
from .options import ParserOptions

__all__ = ["ParserOptions", "get_parser"]
