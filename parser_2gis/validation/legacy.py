"""
Модуль для обратной совместимости.

Этот модуль предоставляет экспорт функций валидации из новых модулей
для обеспечения обратной совместимости со старым кодом.

Пример использования:
    >>> from parser_2gis.validation.legacy import ValidationResult, validate_email, validate_phone
    >>> result = validate_email('test@example.com')
    >>> print(result.is_valid)
    True

Примечание:
    Этот модуль предназначен только для обратной совместимости.
    Новый код должен использовать импорты напрямую из соответствующих модулей:
    - from parser_2gis.validation import validate_url, is_valid_url
    - from parser_2gis.validation import validate_positive_int, validate_positive_float
    - и т.д.
"""

from __future__ import annotations

from .data_validator import (
    ValidationResult,
    validate_email,
    validate_phone,
    validate_positive_float,
    validate_positive_int,
)
from .url_validator import validate_url

__all__ = [
    "ValidationResult",
    "validate_email",
    "validate_phone",
    "validate_url",
    "validate_positive_int",
    "validate_positive_float",
]
