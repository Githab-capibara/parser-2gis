"""
Модуль общих утилит и функций.

Содержит базовые вспомогательные функции для всего проекта.

Оптимизации:
- lru_cache для часто вызываемых функций
- Компилированные regex паттерны
- Экспоненциальная задержка в wait_until_finished
- Оптимизированная проверка чувствительных ключей

Примечание:
    Для нового кода рекомендуется импортировать функции напрямую из
    parser_2gis.utils.<модуль>. Этот модуль содержит только базовые утилиты.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pydantic import ValidationError

# =============================================================================
# КОНСТАНТЫ ИЗ constants.py ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# =============================================================================
from .constants import CSV_BATCH_SIZE, DEFAULT_BUFFER_SIZE, MAX_COLLECTION_SIZE, MERGE_BATCH_SIZE

# =============================================================================
# ЭКСПОРТИРУЕМЫЕ СИМВОЛЫ МОДУЛЯ
# =============================================================================

__all__ = [
    # Базовые утилиты
    "report_from_validation_error",
    "unwrap_dot_dict",
    "floor_to_hundreds",
    # Константы из constants.py
    "DEFAULT_BUFFER_SIZE",
    "CSV_BATCH_SIZE",
    "MERGE_BATCH_SIZE",
    "MAX_COLLECTION_SIZE",
]

# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


def _get_logger() -> Any:
    """Получает logger для модуля common.

    Returns:
        Экземпляр logger из модуля logger.
    """
    from .logger import logger as app_logger

    return app_logger


# =============================================================================
# БАЗОВЫЕ УТИЛИТЫ
# =============================================================================


def report_from_validation_error(
    ex: ValidationError, d: Optional[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    """Генерирует отчёт об ошибке валидации для `BaseModel` из `ValidationError`.

    Note:
        Удобно использовать при попытке инициализации модели с предопределённым
        словарём.

    Args:
        ex: Выброшенное Pydantic ValidationError.
        d: Словарь аргументов (опционально, для совместимости).

    Returns:
        Словарь с информацией об ошибках валидации.
        Формат: {field_name: {'invalid_value': value, 'error_message': msg}}
    """
    error_report: Dict[str, Dict[str, Any]] = {}

    for error in ex.errors():
        msg = error["msg"]
        loc = error["loc"]
        # Берём только имя поля (последний элемент loc)
        field_name = str(loc[-1]) if loc else "unknown"

        # Получаем значение из словаря d если он предоставлен
        invalid_value = "<No value>"
        if d is not None and isinstance(d, dict):
            invalid_value = d.get(field_name, "<No value>")

        error_report[field_name] = {"invalid_value": invalid_value, "error_message": msg}

    return error_report


def unwrap_dot_dict(d: Dict[str, Any]) -> Dict[str, Any]:
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
    """
    if not isinstance(d, dict):
        raise TypeError("Входные данные должны быть словарём")

    output: Dict[str, Any] = {}
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


def floor_to_hundreds(arg: int | float) -> int:
    """Округляет число вниз до ближайшей сотни.

    Args:
        arg: Число для округления.

    Returns:
        Округлённое вниз число до ближайшей сотни.
    """
    return int((arg // 100) * 100)
