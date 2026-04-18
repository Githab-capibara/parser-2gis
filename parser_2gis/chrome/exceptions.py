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

from parser_2gis.exceptions import ExceptionContextMixin

if TYPE_CHECKING:
    pass


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
            f"{cleaned_message}. Функция: {self.function_name}, Строка: {self.line_number}, Файл: {self.filename}"
        )
        super().__init__(full_message, **kwargs)


class ChromeRuntimeException(ChromeException):
    """Исключение времени выполнения Chrome.

    Наследуется от pychrome.exceptions.RuntimeException если доступен,
    иначе только от ChromeException.
    """


class ChromeUserAbortException(ChromeException):
    """Исключение прерывания пользователем Chrome.

    Наследуется от pychrome.exceptions.UserAbortException если доступен,
    иначе только от ChromeException.
    """


# Динамически добавляем pychrome базовые классы если доступны
def _add_pychrome_base_classes() -> None:
    """Добавляет pychrome base classes к исключениям во время выполнения."""
    try:
        from pychrome.exceptions import RuntimeException as PychromeRuntime
        from pychrome.exceptions import UserAbortException as PychromeUserAbort

        # Пересоздаём классы с правильными базами
        class _ChromeRuntimeException(PychromeRuntime, ChromeException):  # type: ignore[misc]
            pass

        class _ChromeUserAbortException(PychromeUserAbort, ChromeException):  # type: ignore[misc]
            pass

        # Динамическое присваивание только во время выполнения
        globals()["ChromeRuntimeException"] = _ChromeRuntimeException
        globals()["ChromeUserAbortException"] = _ChromeUserAbortException
    except ImportError:
        pass


_add_pychrome_base_classes()


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
