"""Модуль обработки ошибок базы данных для parser-2gis.

Предоставляет централизованную обработку ошибок SQLite:
- handle_db_errors: декоратор для обработки ошибок с повторными попытками
- DatabaseError: базовое исключение для ошибок БД
- DBError: алиас для DatabaseError
- _is_retryable_error: проверка ошибки на временную
- _is_critical_error: проверка ошибки на критическую

Пример использования:
    >>> from parser_2gis.database.error_handler import handle_db_errors
    >>> @handle_db_errors(retry_count=3)
    ... def insert_user(conn, user_data):
    ...     conn.execute("INSERT INTO users VALUES (?)", (user_data,))
"""

from __future__ import annotations

import functools
import sqlite3
import time
from collections.abc import Callable
from typing import Any, TypeVar

from parser_2gis.logger.logger import logger

# Тип для декорируемых функций
F = TypeVar("F", bound=Callable[..., Any])


class DatabaseError(Exception):
    """Базовое исключение для ошибок базы данных в parser-2gis.

    Обёртывает оригинальные исключения SQLite для предоставления единого
    интерфейса обработки ошибок базы данных.

    Attributes:
        original_error: Оригинальное исключение, вызвавшее ошибку.

    Example:
        >>> try:
        ...     conn.execute("INVALID SQL")
        ... except sqlite3.Error as e:
        ...     raise DatabaseError("Ошибка выполнения SQL", original_error=e)

    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """Инициализирует исключение БД.

        Args:
            message: Сообщение об ошибке.
            original_error: Оригинальное исключение.

        """
        super().__init__(message)
        self.original_error = original_error


def handle_db_errors(
    retry_count: int = 3, retry_delay: float = 0.5, *, reraise_critical: bool = True
) -> Callable[[F], F]:
    """Декоратор для обработки ошибок базы данных.

    Классифицирует ошибки на 2 категории:
    - Временные (OperationalError, DatabaseError): можно повторить
    - Критические (IntegrityError, ProgrammingError): требуют вмешательства

    Args:
        retry_count: Количество попыток повторения для временных ошибок.
        retry_delay: Задержка между попытками в секундах.
        reraise_critical: Пробрасывать ли критические ошибки дальше.

    Returns:
        Декоратор для функции.

    Example:
        >>> @handle_db_errors(retry_count=3)
        ... def insert_user(conn, user_data):
        ...     conn.execute("INSERT INTO users VALUES (?)", (user_data,))

    """

    def decorator(func: F) -> F:
        """Декоратор для функции."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any | None:
            """Обертка для обработки ошибок."""
            last_error: Exception | None = None
            func_name = func.__name__

            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)

                except sqlite3.Error as db_error:
                    last_error = db_error
                    is_retryable = _is_retryable_error(db_error)
                    is_critical = _is_critical_error(db_error)

                    if is_critical:
                        logger.critical(
                            "Критическая ошибка БД в %s (попытка %d/%d): %s",
                            func_name,
                            attempt + 1,
                            retry_count + 1,
                            db_error,
                        )
                        if reraise_critical:
                            msg = f"Критическая ошибка БД: {db_error}"
                            raise DatabaseError(msg, original_error=db_error) from db_error
                        return None

                    if is_retryable and attempt < retry_count:
                        logger.warning(
                            "Временная ошибка БД в %s (попытка %d/%d): %s. "
                            "Повтор через %.2f сек...",
                            func_name,
                            attempt + 1,
                            retry_count + 1,
                            db_error,
                            retry_delay,
                        )
                        time.sleep(retry_delay * (attempt + 1))
                        continue

                    logger.error(
                        "Ошибка БД в %s (попытка %d/%d): %s",
                        func_name,
                        attempt + 1,
                        retry_count + 1,
                        db_error,
                    )
                    msg = f"Ошибка БД: {db_error}"
                    raise DatabaseError(msg, original_error=db_error) from db_error

                except (OSError, MemoryError, RuntimeError) as general_error:
                    logger.error("Общая ошибка при работе с БД в %s: %s", func_name, general_error)
                    msg = f"Общая ошибка при работе с БД: {general_error}"
                    raise DatabaseError(msg, original_error=general_error) from general_error

            if last_error is not None:
                msg = f"Исчерпаны попытки повторения ({retry_count + 1}): {last_error}"
                raise DatabaseError(msg, original_error=last_error) from last_error

            return None

        return wrapper  # type: ignore[return-value]

    return decorator


def _is_retryable_error(error: sqlite3.Error) -> bool:
    """Проверяет, является ли ошибка временной (можно повторить).

    Временные ошибки возникают из-за блокировок базы данных, таймаутов
    или временных проблем с диском. Эти ошибки можно обработать повторной
    попыткой выполнения операции.

    Args:
        error: Исключение sqlite3 для проверки.

    Returns:
        True если ошибка временная и можно повторить попытку.

    Example:
        >>> import sqlite3
        >>> error = sqlite3.OperationalError("database is locked")
        >>> _is_retryable_error(error)
        True

    """
    error_str = str(error).lower()
    return (
        "database is locked" in error_str
        or "busy" in error_str
        or "timeout" in error_str
        or isinstance(error, sqlite3.OperationalError)
    )


def _is_critical_error(error: sqlite3.Error) -> bool:
    """Проверяет, является ли ошибка критической.

    Критические ошибки требуют вмешательства разработчика или изменения
    логики приложения. Повторная попытка не поможет решить проблему.

    Критические ошибки:
    - IntegrityError: нарушение целостности (unique constraint, foreign key)
    - ProgrammingError: ошибки SQL синтаксиса

    Args:
        error: Исключение sqlite3 для проверки.

    Returns:
        True если ошибка критическая и требует вмешательства.

    Example:
        >>> import sqlite3
        >>> error = sqlite3.IntegrityError("UNIQUE constraint failed")
        >>> _is_critical_error(error)
        True

    """
    return isinstance(error, (sqlite3.IntegrityError, sqlite3.ProgrammingError))


# Алиасы для обратной совместимости
DBError = DatabaseError


__all__ = ["DBError", "DatabaseError", "handle_db_errors"]
