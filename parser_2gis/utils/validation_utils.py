"""Модуль утилит валидации для parser-2gis.

Содержит функции для валидации городов, категорий и обработки ошибок валидации:
- _get_logger: получение логгера для модуля
- report_from_validation_error: генерация отчёта об ошибке валидации
- _validate_city: валидация структуры города
- _validate_category: валидация структуры категории
- _validate_city_cached: кэшированная валидация города
- _validate_category_cached: кэшированная валидация категории

Пример использования:
    >>> from parser_2gis.utils.validation_utils import _validate_city, _validate_category
    >>> city = {"code": "msk", "domain": "moscow.2gis.ru"}
    >>> result = _validate_city(city)
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from pydantic import ValidationError

# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


def _get_logger() -> logging.Logger:
    """Получает экземпляр логгера для модуля валидации.

    Назначение:
        Эта функция-обёртка используется для получения логгера в функциях,
        где прямой импорт logger может вызвать циклическую зависимость модулей.

    Returns:
        Экземпляр logging.Logger для модуля validation_utils.

    Note:
        Функция возвращает тот же logger, что и переменная модуля logger.
        Используется в generate_category_url() и generate_city_urls() для
        логгирования ошибок валидации без создания циклических импортов.

    """
    return logger


# =============================================================================
# ОБРАБОТКА ОШИБОК ВАЛИДАЦИИ
# =============================================================================


def report_from_validation_error(
    ex: ValidationError, d: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
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

    Пример:
        >>> from pydantic import BaseModel, ValidationError
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>> try:
        ...     User(name="test", age="invalid")
        ... except ValidationError as e:
        ...     report = report_from_validation_error(e, {"name": "test", "age": "invalid"})
        ...     print(report)
        {'age': {'invalid_value': 'invalid', 'error_message': '...'}}

    """
    error_report: dict[str, dict[str, Any]] = {}

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


# =============================================================================
# ВАЛИДАЦИЯ ГОРОДОВ
# =============================================================================

# Кэшируем по отдельным полям (code, domain) для более эффективного использования памяти
# и уменьшения количества повторных валидаций одинаковых городов


# Увеличены размеры lru_cache для улучшения производительности
# _validate_city_cached=1024 (было 2048) - оптимизировано для баланса памяти и производительности
# _validate_category_cached=1024 (было 2048) - оптимизировано для баланса памяти и производительности
# ОБОСНОВАНИЕ: Уменьшение размеров кэша снижает потребление памяти при сохранении
# приемлемой производительности для большинства сценариев использования.
@lru_cache(maxsize=1024)
def _validate_city_cached(code: str, domain: str) -> dict[str, Any]:
    """Кэшированная версия валидации города.

    Кэширование:
        - Размер кэша: 1024 записи (оптимизировано для баланса памяти и производительности)
        - Кэширование по отдельным полям (code, domain) вместо кортежа

    Args:
        code: Код города (строка).
        domain: Домен города (строка).

    Returns:
        Валидированный словарь города с полями code и domain.

    Пример:
        >>> result = _validate_city_cached("msk", "moscow.2gis.ru")
        >>> result
        {'code': 'msk', 'domain': 'moscow.2gis.ru'}

    """
    # Возвращаем новый словарь для предотвращения мутаций
    return {"code": code, "domain": domain}


def _validate_city(city: Any, field_name: str = "city") -> dict[str, Any]:
    """Валидирует структуру города.

    Оптимизация:
    - Используется lru_cache для кэширования результатов валидации
    - Кэширование по отдельным полям code и domain
    - Эффективно для часто используемых городов (повторное использование кэша)

    Args:
        city: Словарь города для валидации. Должен содержать поля 'code' и 'domain'.
        field_name: Имя поля для сообщений об ошибках валидации.

    Returns:
        Валидированный словарь города с полями code и domain.

    Raises:
        ValueError: Если город некорректен (не dict, нет обязательных полей, неверный тип).

    Пример:
        >>> city = {"code": "msk", "domain": "moscow.2gis.ru"}
        >>> result = _validate_city(city)
        >>> result
        {'code': 'msk', 'domain': 'moscow.2gis.ru'}

    """
    if not isinstance(city, dict):
        logger.warning("%s не является словарём: %s", field_name, city)
        raise ValueError(f"{field_name} должен быть словарём")

    if not all(key in city for key in ("code", "domain")):
        logger.warning("Город не содержит обязательные поля (code, domain): %s", city)
        raise ValueError(f"{field_name} должен содержать поля code и domain")

    if not isinstance(city["code"], str) or not isinstance(city["domain"], str):
        logger.warning("Поля code и domain должны быть строками: %s", city)
        raise ValueError("code и domain должны быть строками")

    # Используем кэшированную версию для часто используемых городов
    # Оптимизация: передаём code и domain как отдельные аргументы для эффективного кэширования
    return _validate_city_cached(city["code"], city["domain"])


# =============================================================================
# ВАЛИДАЦИЯ КАТЕГОРИЙ
# =============================================================================


# Увеличены размеры lru_cache для улучшения производительности
# _validate_category_cached=1024 (было 2048) - оптимизировано для баланса памяти и производительности
# ОБОСНОВАНИЕ: Уменьшение размера кэша снижает потребление памяти при сохранении
# приемлемой производительности для большинства сценариев использования.
@lru_cache(maxsize=1024)
def _validate_category_cached(category_tuple: tuple) -> dict[str, Any]:
    """Кэшированная версия валидации категории.

    Кэширование:
        - Размер кэша: 1024 записи (оптимизировано для баланса памяти и производительности)

    Args:
        category_tuple: Кортеж (name, query, rubric_code) для кэширования.

    Returns:
        Валидированный словарь категории.

    """
    return {
        "name": category_tuple[0],
        "query": category_tuple[1],
        "rubric_code": category_tuple[2] if category_tuple[2] else None,
    }


def _validate_category(category: Any) -> dict[str, Any]:
    """Валидирует структуру категории.

    Оптимизация: используется lru_cache для кэширования результатов.

    Args:
        category: Словарь категории для валидации.

    Returns:
        Валидированный словарь категории.

    Raises:
        ValueError: Если категория некорректна.

    """
    if not isinstance(category, dict):
        logger.warning("category не является словарём: %s", category)
        raise ValueError("category должен быть словарём")

    # Проверка наличия name или query
    if "name" not in category and "query" not in category:
        logger.warning("Категория должна содержать 'name' или 'query': %s", category)
        raise ValueError("category должен содержать 'name' или 'query'")

    # Используем кэшированную версию
    category_key = (
        category.get("name", ""),
        category.get("query", ""),
        category.get("rubric_code", ""),
    )
    return _validate_category_cached(category_key)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    # Логгер
    "_get_logger",
    # Обработка ошибок валидации
    "report_from_validation_error",
    # Валидация
    "_validate_city",
    "_validate_category",
    "_validate_city_cached",
    "_validate_category_cached",
]
