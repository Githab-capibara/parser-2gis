from pychrome.exceptions import UserAbortException as _UserAbortException
from pychrome.exceptions import RuntimeException as _RuntimeException


class ChromeException(Exception):
    """Базовое исключение Chrome."""
    pass


class ChromeRuntimeException(_RuntimeException, ChromeException):
    """Исключение времени выполнения Chrome."""
    pass


class ChromeUserAbortException(_UserAbortException, ChromeException):
    """Исключение прерывания пользователем Chrome."""
    pass


class ChromePathNotFound(ChromeException):
    """Исключение: браузер Chrome не найден."""
    def __init__(self, msg: str = 'Chrome браузер не найден', *args, **kwargs) -> None:
        super().__init__(msg, *args, **kwargs)


__all__ = [
    'ChromeUserAbortException',
    'ChromeRuntimeException',
    'ChromeException',
    'ChromePathNotFound',
]
