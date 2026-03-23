"""
Модуль для валидации данных.

Этот модуль предоставляет экспорт функций валидации из validation.py
для обратной совместимости.

Пример использования:
    >>> from .validator import ValidationResult, validate_email, validate_phone
    >>> result = validate_email('test@example.com')
    >>> print(result.is_valid)
    True
"""

from __future__ import annotations

from .validation import (
    ValidationResult,
    validate_email,
    validate_phone,
    validate_positive_int,
    validate_url,
)

__all__ = [
    "ValidationResult",
    "validate_email",
    "validate_phone",
    "validate_url",
    "validate_positive_int",
]
