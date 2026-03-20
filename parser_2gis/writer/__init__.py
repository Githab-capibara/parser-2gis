"""Модуль writer для записи данных.

Предоставляет классы и функции для записи результатов парсинга:
- WriterOptions, CSVOptions - опции записи
- FileWriter, CSVWriter, XLSXWriter, JSONWriter - писатели файлов
- get_writer - фабрика для получения писателя
"""

from .factory import get_writer
from .options import CSVOptions, WriterOptions
from .writers import CSVWriter, FileWriter, JSONWriter, XLSXWriter

__all__ = [
    "WriterOptions",
    "CSVOptions",
    "CSVWriter",
    "XLSXWriter",
    "JSONWriter",
    "FileWriter",
    "get_writer",
]
