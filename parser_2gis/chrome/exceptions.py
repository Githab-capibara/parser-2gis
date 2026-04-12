"""Модуль исключений Chrome.

Предоставляет иерархию исключений для обработки ошибок Chrome:
- ChromeException - базовое исключение
- ChromeRuntimeException - исключение времени выполнения
- ChromeUserAbortException - исключение прерывания пользователем
- ChromePathNotFound - исключение ненайденного браузера

Все исключения наследуются от BaseContextualException для автоматического
добавления контекстной информации об ошибках.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pychrome.exceptions import RuntimeException as _RuntimeException
    from pychrome.exceptions import UserAbortException as _UserAbortException
else:
    try:
        from pychrome.exceptions import RuntimeException as _RuntimeException
        from pychrome.exceptions import UserAbortException as _UserAbortException
    except ImportError:
        _RuntimeException = RuntimeError  # type: ignore[misc]
        _UserAbortException = RuntimeError  # type: ignore[misc]

from parser_2gis.exceptions import ExceptionContextMixin


class ChromeException(ExceptionContextMixin, Exception):
    """Базовое исключение Chrome.

    Наследуется от ExceptionContextMixin для автоматического добавления:
    - Имени функции, где произошла ошибка
    - Номера строки
    - Полной трассировки стека
    - Имени файла

    Example:
        >>> try:
        ...     raise ChromeException("Ошибка подключения")
        ... except ChromeException as e:
        ...     print(f"Ошибка: {e}")

    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        """Инициализирует исключение Chrome с контекстной информацией.

        Args:
            message: Текст сообщения об ошибке.
            **kwargs: Дополнительные аргументы для базового класса Exception.

        """
        # Делегируем формирование контекста родительскому миксину
        # для избежания дублирования логики
        context = self._capture_context()
        self.function_name, self.line_number, self.filename = context

        # Формируем полное сообщение с контекстом (аналогично BaseContextualException)
        cleaned_message = message.rstrip(".")
        full_message = (
            f"{cleaned_message}. "
            f"Функция: {self.function_name}, "
            f"Строка: {self.line_number}, "
            f"Файл: {self.filename}"
        )
        super().__init__(full_message, **kwargs)


class ChromeRuntimeException(_RuntimeException, ChromeException):  # type: ignore[misc]
    """Исключение времени выполнения Chrome."""


class ChromeUserAbortException(_UserAbortException, ChromeException):  # type: ignore[misc]
    """Исключение прерывания пользователем Chrome."""


class ChromePathNotFound(ChromeException):
    """Исключение: браузер Chrome не найден.

    Вызывается когда не удалось найти исполняемый файл Chrome
    в системе или по указанному пути.

    Example:
        >>> raise ChromePathNotFound("Chrome не найден в /usr/bin/chrome")

    """

    def __init__(self, msg: str = "Chrome браузер не найден", *args: Any, **kwargs: Any) -> None:
        """Инициализирует исключение ненайденного браузера.

        Args:
            msg: Текст сообщения об ошибке.
            *args: Позиционные аргументы для базового класса.
            **kwargs: Именованные аргументы для базового класса.

        """
        super().__init__(msg, *args, **kwargs)


__all__ = [
    "ChromeException",
    "ChromePathNotFound",
    "ChromeRuntimeException",
    "ChromeUserAbortException",
]
