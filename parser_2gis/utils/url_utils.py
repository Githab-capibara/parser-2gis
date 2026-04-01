"""Модуль утилит для генерации URL.

Содержит функции для генерации URL для парсинга городов и категорий 2GIS.
"""

from __future__ import annotations

import urllib.parse
from functools import lru_cache
from typing import Any

# =============================================================================
# ФУНКЦИИ КОДИРОВАНИЯ
# =============================================================================


_url_query_encode = lru_cache(maxsize=2048)(lambda query: urllib.parse.quote(query, safe=""))


def url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL.

    - Размер кэша установлен в 2048 вместо 4096 (оптимально для часто используемых запросов)
    - Снижение потребления памяти без потери производительности
    - lru_cache для кэширования часто используемых запросов
    - Снижение количества вызовов urllib.parse.quote

    Args:
        query: Исходная строка запроса.

    Returns:
        Закодированная строка для URL.

    """
    return _url_query_encode(query)


def clear_url_query_cache() -> None:
    """Очищает кэш закодированных URL запросов."""
    _url_query_encode.cache_clear()


def clear_category_url_cache() -> None:
    """Очищает кэш сгенерированных URL категорий.

    C002: Функция для управления кэшем URL категорий.
    """
    _generate_category_url_cached.cache_clear()


# =============================================================================
# ГЕНЕРАЦИЯ URL ДЛЯ КАТЕГОРИЙ
# =============================================================================


# Оптимизация: кэширование сгенерированных URL
# C002: Размер кэша увеличен до 4096 для поддержки большего количества URL
@lru_cache(maxsize=4096)
def _generate_category_url_cached(city_key: tuple, category_key: tuple) -> str:
    """Кэшированная версия генерации URL.

    Args:
        city_key: Кортеж (code, domain).
        category_key: Кортеж (query, rubric_code).

    Returns:
        Сгенерированный URL.

    """
    city_code, city_domain = city_key
    category_query, rubric_code = category_key

    base_url = f"https://2gis.{city_domain}/{city_code}"
    rest_url = f"/search/{url_query_encode(category_query)}"

    if rubric_code:
        rest_url += f"/rubricId/{rubric_code}"

    rest_url += "/filters/sort=name"

    return base_url + rest_url


def generate_category_url(city: dict[str, Any], category: dict[str, Any]) -> str:
    """Генерирует URL для парсинга категории в городе.

    Оптимизация:
    - lru_cache для кэширования результатов
    - Минимальная валидация для уже валидированных данных

    Args:
        city: Словарь города с обязательными полями:
            - code (str): код города
            - domain (str): домен региона
        category: Словарь категории с полями:
            - name (str): название категории
            - query (str, optional): поисковый запрос
            - rubric_code (str, optional): код рубрики

    Returns:
        URL для парсинга категории в городе.

    Raises:
        ValueError: Если город или категория некорректны.
        TypeError: Если типы данных некорректны.

    """
    from parser_2gis.utils.validation_utils import _get_logger

    local_logger = _get_logger()

    # HIGH 11: Явная валидация параметров
    # Проверка city
    if city is None:
        raise TypeError("city не может быть None")
    if not isinstance(city, dict):
        local_logger.warning("Некорректный город (не dict): %s", city)
        raise TypeError("city должен быть словарём (dict)")
    if "code" not in city:
        local_logger.warning("Некорректный город (нет code): %s", city)
        raise ValueError("city должен содержать code")
    if "domain" not in city:
        local_logger.warning("Некорректный город (нет domain): %s", city)
        raise ValueError("city должен содержать domain")
    if not isinstance(city.get("code"), str) or not city["code"]:
        local_logger.warning("Некорректный city code: %s", city.get("code"))
        raise ValueError("city['code'] должен быть непустой строкой")
    if not isinstance(city.get("domain"), str) or not city["domain"]:
        local_logger.warning("Некорректный city domain: %s", city.get("domain"))
        raise ValueError("city['domain'] должен быть непустой строкой")

    # Проверка category
    if category is None:
        raise TypeError("category не может быть None")
    if not isinstance(category, dict):
        local_logger.warning("Некорректная категория (не dict): %s", category)
        raise TypeError("category должен быть словарём (dict)")

    # Получаем query категории с fallback на name
    category_query = category.get("query", category.get("name", ""))
    if not category_query:
        local_logger.warning("Категория не содержит query или name: %s", category)
        raise ValueError("category должен содержать query или name")
    if not isinstance(category_query, str):
        local_logger.warning("category query/name не строка: %s", category_query)
        raise TypeError("category['query'] или category['name'] должен быть строкой")

    # Проверка rubric_code если указан
    rubric_code = category.get("rubric_code", "")
    if rubric_code and not isinstance(rubric_code, str):
        local_logger.warning("rubric_code не строка: %s", rubric_code)
        raise TypeError("category['rubric_code'] должен быть строкой")

    # Используем кэшированную версию
    city_key = (city["code"], city["domain"])
    category_key = (category_query, rubric_code)

    return _generate_category_url_cached(city_key, category_key)


# =============================================================================
# ГЕНЕРАЦИЯ URL ДЛЯ ГОРОДОВ
# =============================================================================


def generate_city_urls(
    cities: list[dict[str, Any]], query: str, rubric: dict[str, Any] | None = None
) -> list[str]:
    """Генерирует URL для парсинга по списку городов.

    Оптимизация:
    - Предварительное вычисление rubric_code
    - Минимальная валидация

    Args:
        cities: Список словарей городов.
        query: Поисковый запрос.
        rubric: Словарь рубрики с полем code.

    Returns:
        Список URL для парсинга.

    """
    urls: list[str] = []
    from parser_2gis.utils.validation_utils import _get_logger

    local_logger = _get_logger()

    # Предварительно вычисляем rubric_code
    rubric_code = rubric.get("code", "") if rubric else ""

    # Кодируем query один раз для всех городов
    encoded_query = url_query_encode(query)

    for city in cities:
        try:
            # Минимальная валидация
            if not isinstance(city, dict):
                local_logger.warning("Город не является словарём: %s", city)
                continue

            if "code" not in city or "domain" not in city:
                local_logger.warning("Город без code/domain: %s", city)
                continue

            if not isinstance(city["code"], str) or not isinstance(city["domain"], str):
                local_logger.warning("code/domain должны быть строками: %s", city)
                continue

            # Формирование URL
            base_url = f"https://2gis.{city['domain']}/{city['code']}"
            rest_url = f"/search/{encoded_query}"

            if rubric_code:
                rest_url += f"/rubricId/{rubric_code}"

            rest_url += "/filters/sort=name"
            urls.append(base_url + rest_url)

        except (ValueError, TypeError, MemoryError, OSError) as e:
            local_logger.error("Ошибка при генерации URL для города %s: %s", city, e)
            continue

    return urls


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "_generate_category_url_cached",
    "clear_category_url_cache",
    "clear_url_query_cache",
    "generate_category_url",
    "generate_city_urls",
    "url_query_encode",
]
