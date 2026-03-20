import inspect

from pychrome.exceptions import (
    RuntimeException as _RuntimeException,
    UserAbortException as _UserAbortException,
)


class ChromeException(Exception):
    """Базовое исключение Chrome.

    Добавляет контекстную информацию об ошибке:
    - Имя функции, где произошла ошибка
    - Номер строки
    - Полную трассировку стека
    """

    def __init__(self, message: str = "", **kwargs) -> None:
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


class ChromeRuntimeException(_RuntimeException, ChromeException):
    """Исключение времени выполнения Chrome."""

    pass


class ChromeUserAbortException(_UserAbortException, ChromeException):
    """Исключение прерывания пользователем Chrome."""

    pass


class ChromePathNotFound(ChromeException):
    """Исключение: браузер Chrome не найден."""

    def __init__(self, msg: str = "Chrome браузер не найден", *args, **kwargs) -> None:
        super().__init__(msg, *args, **kwargs)


__all__ = [
    "ChromeUserAbortException",
    "ChromeRuntimeException",
    "ChromeException",
    "ChromePathNotFound",
]
