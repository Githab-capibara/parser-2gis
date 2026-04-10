"""Общие типы для parser-2gis.

Модуль для типов, которые используются в нескольких пакетах и не должны
создавать циклические зависимости.

ISSUE-041: Создан для разрыва цикла constants -> parser -> parser.options -> utils -> constants.

Пример использования:
    >>> from parser_2gis.types import ConfigDict
    >>> config: ConfigDict = {"key": "value"}
"""

from __future__ import annotations

from typing import Any, TypedDict

# Общие словари конфигурации


class ConfigDict(TypedDict, total=False):
    """Общий словарь конфигурации.

    Attributes:
        key: Ключ конфигурации.
        value: Значение конфигурации.
        description: Описание конфигурации.

    """

    key: str
    value: Any
    description: str


class CityDict(TypedDict, total=False):
    """Словарь города.

    Attributes:
        name: Название города.
        code: Код города.
        domain: Домен города.
        country_code: Код страны.

    """

    name: str
    code: str
    domain: str
    country_code: str


class CategoryDict(TypedDict, total=False):
    """Словарь категории.

    Attributes:
        name: Название категории.
        id: Идентификатор категории.
        rubric_code: Код рубрики.

    """

    name: str
    id: str
    rubric_code: str


# Тип для валидации ENV


class EnvValidationResult(tuple[bool, str | None]):
    """Тип для результата валидации ENV.

    Кортеж (is_valid: bool, error_message: str | None).
    """

    def __new__(cls, *, is_valid: bool, error_message: str | None = None) -> EnvValidationResult:
        """Создаёт результат валидации.

        Args:
            is_valid: Результат валидации.
            error_message: Текст ошибки.

        """
        return super().__new__(cls, (is_valid, error_message))


# Alias для обратной совместимости
EnvValidationTuple = EnvValidationResult
