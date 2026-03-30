"""Модуль исключений writer.

Предоставляет исключение WriterUnknownFileFormat для обработки ошибок
неизвестного формата выходного файла.

Наследуется от BaseContextualException для автоматического добавления
контекстной информации об ошибке.
"""

from __future__ import annotations

# Импортируем базовый класс на верхнем уровне
from parser_2gis.exceptions import BaseContextualException


class WriterUnknownFileFormat(BaseContextualException):
    """Выбрасывается, когда пользователь указал неизвестный формат выходного файла.

    Наследуется от BaseContextualException для автоматического добавления:
    - Имени функции, где произошла ошибка
    - Номера строки
    - Имени файла
    """


__all__ = ["WriterUnknownFileFormat"]
