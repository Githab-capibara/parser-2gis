"""Базовые типы для parser-2gis без зависимостей от других модулей проекта.

Этот модуль содержит минимальные типы, от которых зависят другие модули.
НЕ ИМЕЕТ импортов из других модулей parser_2gis для предотвращения циклических зависимостей.

ISSUE-043: Создан для разрыва цикла chrome.remote -> utils.decorators -> constants -> parser.
ISSUE-041: Содержит базовые типы для shared type definitions.

Пример использования:
    >>> from parser_2gis.core_types import T
    >>> from typing import Generic
    >>> class Container(Generic[T]): ...
"""

from __future__ import annotations

from typing import Any, Generic, NamedTuple, Protocol, TypeVar

# Type variables для дженериков
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# Протокол для функций логирования


class LogCallback(Protocol):
    """Протокол для callback-функции логирования.

    Attributes:
        __call__: Вызывается с сообщением и уровнем логирования.

    """

    def __call__(self, message: str, level: str = "info") -> None:
        """Вызывает функцию логирования.

        Args:
            message: Текст сообщения.
            level: Уровень логирования (debug, info, warning, error).

        """
        ...  # pylint: disable=unnecessary-ellipsis


# Протокол для функций прогресса


class ProgressCallback(Protocol):
    """Протокол для callback-функции обновления прогресса.

    Attributes:
        __call__: Вызывается с параметрами прогресса.

    """

    def __call__(self, success: int, failed: int, filename: str) -> None:
        """Вызывает функцию обновления прогресса.

        Args:
            success: Количество успешных операций.
            failed: Количество операций с ошибками.
            filename: Имя текущего обрабатываемого файла.

        """
        ...  # pylint: disable=unnecessary-ellipsis


# Базовые NamedTuple для переиспользования


class FileOperationResult(NamedTuple):
    """Результат файловой операции.

    Attributes:
        success: True если операция успешна.
        message: Описание результата.
        data: Дополнительные данные (опционально).

    """

    success: bool
    message: str
    data: Any = None


class MergeStats(NamedTuple):
    """Статистика операции объединения.

    Attributes:
        total_files: Общее количество обработанных файлов.
        total_rows: Общее количество строк.
        deleted_files: Количество удалённых исходных файлов.

    """

    total_files: int
    total_rows: int
    deleted_files: int


# Generic container для результатов парсинга


class ParseResult(Generic[T]):
    """Универсальный контейнер результата парсинга.

    Attributes:
        value: Значение результата.
        success: Флаг успешности операции.
        error: Текст ошибки (если есть).

    """

    def __init__(
        self, value: T | None = None, *, success: bool = True, error: str | None = None
    ) -> None:
        """Инициализирует результат парсинга.

        Args:
            value: Значение результата.
            success: Флаг успешности.
            error: Текст ошибки.

        """
        self.value = value
        self.success = success
        self.error = error

    @classmethod
    def ok(cls, value: T) -> ParseResult[T]:
        """Создаёт успешный результат.

        Args:
            value: Значение результата.

        Returns:
            Успешный ParseResult.

        """
        return cls(value=value, success=True)

    @classmethod
    def fail(cls, error: str) -> ParseResult[None]:
        """Создаёт результат с ошибкой.

        Args:
            error: Текст ошибки.

        Returns:
            ParseResult с ошибкой.

        """
        return cls(value=None, success=False, error=error)


# Тип для URL кортежей
type UrlTuple = tuple[str, str, str]  # (url, category_name, city_name)

# Тип для результата парсинга (bool, message)
type ParserResult = tuple[bool, str]
