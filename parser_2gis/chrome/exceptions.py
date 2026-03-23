"""Модуль исключений Chrome.

Предоставляет иерархию исключений для обработки ошибок Chrome:
- ChromeException - базовое исключение
- ChromeRuntimeException - исключение времени выполнения
- ChromeUserAbortException - исключение прерывания пользователем
- ChromePathNotFound - исключение ненайденного браузера

Все исключения наследуются от BaseContextualException для автоматического
добавления контекстной информации об ошибках.
"""

from typing import Any

from pychrome.exceptions import (
    RuntimeException as _RuntimeException,
    UserAbortException as _UserAbortException,
)


# Импортируем BaseContextualException внутри класса для избежания циклических зависимостей
def _get_base_exception() -> type:
    """Получает базовый класс исключения лениво."""
    from ..exceptions import BaseContextualException

    return BaseContextualException


class ChromeException(Exception):
    """Базовое исключение Chrome.

    Наследуется от BaseContextualException для автоматического добавления:
    - Имени функции, где произошла ошибка
    - Номера строки
    - Полной трассировки стека
    - Имени файла
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        # Импортируем базовый класс лениво
        _get_base_exception()

        # Получаем информацию о вызове
        import inspect

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


class ChromeRuntimeException(_RuntimeException, ChromeException):
    """Исключение времени выполнения Chrome."""

    pass


class ChromeUserAbortException(_UserAbortException, ChromeException):
    """Исключение прерывания пользователем Chrome."""

    pass


class ChromePathNotFound(ChromeException):
    """Исключение: браузер Chrome не найден."""

    def __init__(self, msg: str = "Chrome браузер не найден", *args: Any, **kwargs: Any) -> None:
        super().__init__(msg, *args, **kwargs)


__all__ = [
    "ChromeUserAbortException",
    "ChromeRuntimeException",
    "ChromeException",
    "ChromePathNotFound",
]
