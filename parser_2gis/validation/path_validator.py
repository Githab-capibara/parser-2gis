"""Модуль валидации путей — обратная совместимость.

ISSUE-055: Этот модуль перенаправляет импорты в path_validation.py
для обеспечения обратной совместимости.

Все новые импорты должны использовать:
    from parser_2gis.validation.path_validation import ...

Пример использования:
    >>> from parser_2gis.validation.path_validator import PathValidator, validate_path
    >>> validator = PathValidator()
    >>> validator.validate("/safe/path/file.txt")
    >>> validate_path("/safe/output.csv", "output_path")

"""

from __future__ import annotations

# ISSUE-055: Перенаправляем все импорты в консолидированный модуль
from .path_validation import PathSafetyValidator as PathValidator
from .path_validation import PathTraversalError
from .path_validation import get_path_safety_validator as get_path_validator
from .path_validation import validate_path_safety as validate_path

__all__ = ["PathTraversalError", "PathValidator", "get_path_validator", "validate_path"]
