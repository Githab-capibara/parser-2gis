"""Модуль исключений парсера.

Предоставляет базовое исключение ParserException с контекстной информацией
об ошибке (имя функции, номер строки, имя файла).

Наследуется от BaseContextualException для автоматического добавления
контекстной информации.
"""

from __future__ import annotations

# Импортируем базовый класс на верхнем уровне
from parser_2gis.exceptions import BaseContextualException


class ParserException(BaseContextualException):
    """Базовое исключение парсера.

    Наследуется от BaseContextualException для автоматического добавления:
    - Имени функции, где произошла ошибка
    - Номера строки
    - Имени файла
    """

    pass


__all__ = ["ParserException"]
