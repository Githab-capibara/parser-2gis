"""Модуль утилит для работы с данными.

Содержит функции для преобразования и обработки структур данных.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

# =============================================================================
# TYPE VARIABLES
# =============================================================================

T = TypeVar("T")

# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


def _get_logger() -> Any:
    """Получает logger для модуля data_utils.

    Returns:
        Экземпляр logger из модуля logger.

    """
    from parser_2gis.logger import logger as app_logger

    return app_logger


# =============================================================================
# ПРЕОБРАЗОВАНИЕ ДАННЫХ
# =============================================================================


def unwrap_dot_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Разворачивает плоский словарь с ключами в виде точечного пути к значениям.

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
        ValueError: Если ключ содержит недопустимые символы.

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
            _get_logger().warning("Пустой ключ в словаре, пропускаем")
            continue

        path = key.split(".")
        if any(not p for p in path):
            _get_logger().warning("Ключ '%s' содержит пустые сегменты, пропускаем", key)
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

__all__ = ["_get_logger", "unwrap_dot_dict"]
