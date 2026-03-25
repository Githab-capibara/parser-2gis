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

from pychrome.exceptions import RuntimeException as _RuntimeException
from pychrome.exceptions import UserAbortException as _UserAbortException

from parser_2gis.exceptions import ExceptionContextMixin


class ChromeException(ExceptionContextMixin, Exception):
    """Базовое исключение Chrome.

    Наследуется от ExceptionContextMixin для автоматического добавления:
    - Имени функции, где произошла ошибка
    - Номера строки
    - Полной трассировки стека
    - Имени файла
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        # Получаем контекст через миксин
        func_name, line_num, filename = self._capture_context()
        self.function_name = func_name
        self.line_number = line_num
        self.filename = filename

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
