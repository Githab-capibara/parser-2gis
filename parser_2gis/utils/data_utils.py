"""Модуль утилит для работы с данными в parser-2gis.

Содержит функции для преобразования и обработки структур данных:
- unwrap_dot_dict: разворачивает плоский словарь с точечными ключами во вложенный

Пример использования:
    >>> from parser_2gis.utils.data_utils import unwrap_dot_dict
    >>> input_dict = {'a.b.c': 1, 'a.d': 2}
    >>> result = unwrap_dot_dict(input_dict)
    >>> result
    {'a': {'b': {'c': 1}, 'd': 2}}
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from parser_2gis.constants import MAX_DICT_RECURSION_DEPTH

# =============================================================================
# TYPE VARIABLES
# =============================================================================

T = TypeVar("T")

# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# ПРЕОБРАЗОВАНИЕ ДАННЫХ
# =============================================================================


def unwrap_dot_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Разворачивает плоский словарь с ключами в виде точечного пути к значениям.

    ISSUE-175: Добавлено ограничение глубины рекурсии.
    Оптимизация: используется setdefault вместо functools.reduce.

    Example:
        Вход:
            {
                'full.path.fieldname': 'value1',
                'another.fieldname': 'value2',
            }

        Выход:
            {
                'full': {
                    'path': {
                        'filedname': 'value1',
                    },
                },
                'another': {
                    'fieldname': 'value2',
                },
            }

    Args:
        d: Плоский словарь с ключами в виде точечного пути.

    Returns:
        Вложенный словарь с развёрнутой структурой.

    Raises:
        TypeError: Если входные данные не являются словарём.
        ValueError: Если ключ содержит недопустимые символы или превышена глубина.

    Пример:
        >>> input_dict = {'a.b.c': 1, 'a.d': 2}
        >>> result = unwrap_dot_dict(input_dict)
        >>> result
        {'a': {'b': {'c': 1}, 'd': 2}}

    """
    if not isinstance(d, dict):
        raise TypeError("Входные данные должны быть словарём")

    output: dict[str, Any] = {}
    for key, value in d.items():
        if not key:
            logger.warning("Пустой ключ в словаре, пропускаем")
            continue

        path = key.split(".")
        if any(not p for p in path):
            logger.warning("Ключ '%s' содержит пустые сегменты, пропускаем", key)
            continue

        # ISSUE-175: Проверка глубины рекурсии
        if len(path) > MAX_DICT_RECURSION_DEPTH:
            logger.warning(
                "Ключ '%s' превышает максимальную глубину вложенности (%d > %d), пропускаем",
                key,
                len(path),
                MAX_DICT_RECURSION_DEPTH,
            )
            continue

        # Оптимизация: используем setdefault вместо reduce
        target = output
        for segment in path[:-1]:
            target = target.setdefault(segment, {})
        target[path[-1]] = value

    return output


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = ["unwrap_dot_dict"]
