"""Модуль исключений парсера.

Предоставляет базовый класс исключений BaseContextualException для обработки ошибок
в различных компонентах парсера (Chrome, парсер, writer).

Использует иерархию исключений с базовым классом BaseContextualException,
который добавляет контекстную информацию об ошибках.

Примечание:
    Специфичные исключения (ChromeException, ParserException, WriterUnknownFileFormat)
    находятся в соответствующих модулях:
    - Chrome: parser_2gis.chrome.exceptions
    - Parser: parser_2gis.parser.exceptions
    - Writer: parser_2gis.writer.exceptions
"""

from __future__ import annotations

import inspect
from typing import Any


class ExceptionContextMixin:
    """Миксин для получения контекста исключения.

    Предоставляет метод для извлечения информации о месте возникновения ошибки:
    - Имя функции, где произошла ошибка
    - Номер строки
    - Имя файла

    Пример использования:
        >>> class MyException(ExceptionContextMixin, Exception):
        ...     pass
    """

    def _capture_context(self) -> tuple[str, int, str]:
        """Получает имя функции, номер строки и имя файла.

        Returns:
            Кортеж (function_name, line_number, filename).

        """
        frame = inspect.currentframe()
        if frame and frame.f_back:
            return (
                frame.f_back.f_code.co_name,
                frame.f_back.f_lineno,
                frame.f_back.f_code.co_filename,
            )
        return "unknown", 0, "unknown"


# Базовый класс исключений
class BaseContextualException(Exception):
    """Базовый класс для всех исключений с контекстной информацией.

    Добавляет автоматическое извлечение информации о месте возникновения ошибки:
    - Имя функции, где произошла ошибка
    - Номер строки
    - Полную трассировку стека
    - Имя файла

    Пример использования:
        >>> class MyException(BaseContextualException):
        ...     pass

        >>> raise MyException("Произошла ошибка")
        MyException: Произошла ошибка. Функция: my_func, Строка: 42, Файл: /path/to/file.py
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        # Получаем информацию о вызове
        frame = inspect.currentframe()
        if frame and frame.f_back:
            self.function_name = frame.f_back.f_code.co_name
            self.line_number = frame.f_back.f_lineno
            self.filename = frame.f_back.f_code.co_filename
        else:
            self.function_name = "unknown"
            self.line_number = 0
            self.filename = "unknown"

        # Формируем полное сообщение с контекстом
        full_message = (
            f"{message}. "
            f"Функция: {self.function_name}, "
            f"Строка: {self.line_number}, "
            f"Файл: {self.filename}"
        )
        super().__init__(full_message, **kwargs)


__all__ = ["BaseContextualException", "ExceptionContextMixin"]
