"""Модуль работы с базой данных.

Предоставляет инфраструктуру для работы с SQLite:
- Обработка ошибок БД
- Декораторы для обработки исключений
- Упрощённая классификация ошибок (временные/критические)
"""

from .error_handler import DatabaseError, DBError, handle_db_errors

__all__ = ["DBError", "DatabaseError", "handle_db_errors"]
