"""
Модуль работы с базой данных.

Предоставляет инфраструктуру для работы с SQLite:
- Обработка ошибок БД
- Декораторы для обработки исключений
- Транслятор исключений
"""

from .error_handler import (
    DatabaseError,
    DatabaseErrorTranslator,
    DBError,
    DBErrorTranslator,
    handle_db_errors,
)

__all__ = [
    "DatabaseError",
    "DatabaseErrorTranslator",
    "handle_db_errors",
    "DBError",
    "DBErrorTranslator",
]
