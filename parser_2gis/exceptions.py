"""
Модуль исключений парсера.

Предоставляет базовые классы исключений для обработки ошибок
в различных компонентах парсера (Chrome, парсер, writer).

Использует иерархию исключений с базовым классом BaseContextualException,
который добавляет контекстную информацию об ошибках.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any


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


# =============================================================================
# ЭКСПОРТ ИСКЛЮЧЕНИЙ ИЗ МОДУЛЕЙ (ленивый импорт для избежания циклических зависимостей)
# =============================================================================

if TYPE_CHECKING:
    # Импорты только для type checking
    pass

__all__ = [
    # Базовый класс
    "BaseContextualException"
]


def __getattr__(name: str) -> Any:
    """Ленивый импорт исключений для избежания циклических зависимостей.

    Args:
        name: Имя экспортируемого символа.

    Returns:
        Импортированный класс исключения.

    Raises:
        AttributeError: Если запрошен несуществующий символ.
    """
    if name in (
        "ChromeException",
        "ChromePathNotFound",
        "ChromeRuntimeException",
        "ChromeUserAbortException",
    ):
        from .chrome.exceptions import (
            ChromeException,
            ChromePathNotFound,
            ChromeRuntimeException,
            ChromeUserAbortException,
        )

        return {
            "ChromeException": ChromeException,
            "ChromePathNotFound": ChromePathNotFound,
            "ChromeRuntimeException": ChromeRuntimeException,
            "ChromeUserAbortException": ChromeUserAbortException,
        }[name]

    if name == "ParserException":
        from .parser.exceptions import ParserException

        return ParserException

    if name == "WriterUnknownFileFormat":
        from .writer.exceptions import WriterUnknownFileFormat

        return WriterUnknownFileFormat

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
