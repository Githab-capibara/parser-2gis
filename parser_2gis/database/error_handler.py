"""Модуль обработки ошибок базы данных.

Предоставляет централизованную обработку ошибок SQLite:
- Декоратор @handle_db_errors
- Exception Translator
- Классификация ошибок БД
"""

from __future__ import annotations

import functools
import sqlite3
from typing import Any, ClassVar, TypeVar
from collections.abc import Callable

from parser_2gis.logger.logger import logger

# Тип для декорируемых функций
F = TypeVar("F", bound=Callable[..., Any])


class DatabaseError(Exception):
    """Базовое исключение для ошибок базы данных."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """Инициализирует исключение БД.

        Args:
            message: Сообщение об ошибке.
            original_error: Оригинальное исключение.

        """
        super().__init__(message)
        self.original_error = original_error
        self.error_type = self._classify_error(original_error)

    @staticmethod
    def _classify_error(error: Exception | None) -> str:
        """Классифицирует тип ошибки.

        Args:
            error: Исключение для классификации.

        Returns:
            Строка с типом ошибки.

        """
        if error is None:
            return "unknown"

        error_str = str(error).lower()

        if "disk i/o" in error_str:
            return "disk_io"
        elif "database is locked" in error_str or "busy" in error_str:
            return "locked"
        elif "no such table" in error_str:
            return "schema"
        elif "corrupt" in error_str or "malformed" in error_str:
            return "corrupt"
        elif "unique constraint" in error_str:
            return "constraint"
        elif "foreign key" in error_str:
            return "foreign_key"
        elif "timeout" in error_str:
            return "timeout"
        else:
            return "general"


class DatabaseErrorTranslator:
    """Транслятор исключений базы данных.

    Преобразует sqlite3.Error в более специфичные исключения
    для упрощения обработки ошибок.
    """

    # Карта соответствия типов ошибок
    ERROR_CLASSES: ClassVar[dict[str, type[Exception]]] = {
        "disk_io": sqlite3.DatabaseError,
        "locked": sqlite3.OperationalError,
        "schema": sqlite3.OperationalError,
        "corrupt": sqlite3.DatabaseError,
        "constraint": sqlite3.IntegrityError,
        "foreign_key": sqlite3.IntegrityError,
        "timeout": sqlite3.OperationalError,
    }

    @classmethod
    def translate(cls, error: sqlite3.Error, context: str = "") -> DatabaseError:
        """Транслирует sqlite3.Error в DatabaseError.

        Args:
            error: Исключение sqlite3.
            context: Контекст возникновения ошибки.

        Returns:
            DatabaseError с дополнительной информацией.

        """
        error_str = str(error).lower()
        error_type = "general"

        # Определяем тип ошибки
        if "disk i/o" in error_str:
            error_type = "disk_io"
        elif "database is locked" in error_str or "busy" in error_str:
            error_type = "locked"
        elif "no such table" in error_str:
            error_type = "schema"
        elif "corrupt" in error_str or "malformed" in error_str:
            error_type = "corrupt"
        elif "unique constraint" in error_str:
            error_type = "constraint"
        elif "foreign key" in error_str:
            error_type = "foreign_key"
        elif "timeout" in error_str:
            error_type = "timeout"

        # Формируем сообщение с контекстом
        context_str = f" в контексте '{context}'" if context else ""
        message = f"Ошибка БД{context_str} [{error_type}]: {error}"

        return DatabaseError(message, original_error=error)

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """Проверяет, можно ли повторить операцию.

        Args:
            error: Исключение для проверки.

        Returns:
            True если операция может быть повторена.

        """
        if isinstance(error, DatabaseError):
            return error.error_type in ("locked", "timeout", "busy")

        if isinstance(error, sqlite3.Error):
            error_str = str(error).lower()
            return (
                "database is locked" in error_str or "busy" in error_str or "timeout" in error_str
            )

        return False

    @classmethod
    def is_critical(cls, error: Exception) -> bool:
        """Проверяет, является ли ошибка критической.

        Args:
            error: Исключение для проверки.

        Returns:
            True если ошибка критическая.

        """
        if isinstance(error, DatabaseError):
            return error.error_type in ("disk_io", "corrupt", "schema")

        if isinstance(error, sqlite3.Error):
            error_str = str(error).lower()
            return "disk i/o" in error_str or "corrupt" in error_str or "malformed" in error_str

        return False


def handle_db_errors(
    retry_count: int = 3, retry_delay: float = 0.5, context: str = "", reraise_critical: bool = True
) -> Callable[[F], F]:
    """Декоратор для обработки ошибок базы данных.

    Args:
        retry_count: Количество попыток повторения для retryable ошибок.
        retry_delay: Задержка между попытками в секундах.
        context: Контекст возникновения ошибки (для логирования).
        reraise_critical: Пробрасывать ли критические ошибки дальше.

    Returns:
        Декоратор для функции.

    Example:
        >>> @handle_db_errors(retry_count=3, context="user_insert")
        ... def insert_user(conn, user_data):
        ...     conn.execute("INSERT INTO users VALUES (?)", (user_data,))

    """

    def decorator(func: F) -> F:
        """Декоратор для функции."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Обертка для обработки ошибок."""
            last_error: Exception | None = None
            func_name = func.__name__

            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)

                except sqlite3.Error as db_error:
                    last_error = db_error
                    translated_error = DatabaseErrorTranslator.translate(db_error, context)

                    # Проверяем тип ошибки
                    if DatabaseErrorTranslator.is_critical(db_error):
                        logger.critical(
                            "Критическая ошибка БД в %s (попытка %d/%d): %s",
                            func_name,
                            attempt + 1,
                            retry_count + 1,
                            db_error,
                        )
                        if reraise_critical:
                            raise translated_error from db_error
                        return None

                    if DatabaseErrorTranslator.is_retryable(db_error):
                        if attempt < retry_count:
                            logger.warning(
                                "Временная ошибка БД в %s (попытка %d/%d): %s. "
                                "Повтор через %.2f сек...",
                                func_name,
                                attempt + 1,
                                retry_count + 1,
                                db_error,
                                retry_delay,
                            )
                            import time

                            time.sleep(retry_delay * (attempt + 1))  # Экспоненциальная задержка
                            continue
                        else:
                            logger.error(
                                "Исчерпаны попытки повторения для %s после %d попыток: %s",
                                func_name,
                                retry_count + 1,
                                db_error,
                            )
                    else:
                        logger.error(
                            "Ошибка БД в %s (попытка %d/%d): %s",
                            func_name,
                            attempt + 1,
                            retry_count + 1,
                            db_error,
                        )
                        raise translated_error from db_error

                except (OSError, MemoryError, RuntimeError) as general_error:
                    logger.error("Общая ошибка при работе с БД в %s: %s", func_name, general_error)
                    raise DatabaseError(
                        f"Общая ошибка при работе с БД: {general_error}",
                        original_error=general_error,
                    ) from general_error

            # Исчерпаны попытки повторения
            if last_error is not None:
                raise DatabaseError(
                    f"Исчерпаны попытки повторения ({retry_count + 1}): {last_error}",
                    original_error=last_error,
                ) from last_error

            return None

        return wrapper  # type: ignore[return-value]

    return decorator


# Алиасы для обратной совместимости
DBError = DatabaseError
DBErrorTranslator = DatabaseErrorTranslator


__all__ = [
    "DBError",
    "DBErrorTranslator",
    "DatabaseError",
    "DatabaseErrorTranslator",
    "handle_db_errors",
]
