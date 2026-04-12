"""Модуль утилит для генерации URL в parser-2gis.

Содержит функции для генерации URL для парсинга городов и категорий 2GIS:
- url_query_encode: кодирование строки запроса для URL
- generate_category_url: генерация URL для категории в городе
- generate_city_urls: генерация URL для списка городов
- clear_url_query_cache: очистка кэша кодирования
- clear_category_url_cache: очистка кэша URL категорий

Пример использования:
    >>> from parser_2gis.utils.url_utils import generate_category_url
    >>> city = {"code": "msk", "domain": "moscow.2gis.ru"}
    >>> category = {"name": "Аптеки", "query": "Аптеки"}
    >>> url = generate_category_url(city, category)
"""

from __future__ import annotations

import urllib.parse
from functools import lru_cache
from typing import Any

# =============================================================================
# ФУНКЦИИ КОДИРОВАНИЯ
# =============================================================================


@lru_cache(maxsize=1024)
def _url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL с кэшированием.

    Args:
        query: Исходная строка запроса.

    Returns:
        Закодированная строка для URL.

    """
    return urllib.parse.quote(query, safe="")


def url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL.

    Кэширование:
        - Размер кэша ограничен до 1024 для оптимального использования памяти
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
# Размер кэша уменьшен до 512 для снижения потребления памяти (lru_cache хранит сильные ссылки,
# что при большом maxsize может приводить к утечке памяти при длительной работе парсера)
@lru_cache(maxsize=512)
def _generate_category_url_cached(city_key: tuple[str, ...], category_key: tuple[str, ...]) -> str:
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
        msg = "city не может быть None"
        raise TypeError(msg)
    if not isinstance(city, dict):
        local_logger.warning("Некорректный город (не dict): %s", city)
        msg = "city должен быть словарём (dict)"
        raise TypeError(msg)
    if "code" not in city:
        local_logger.warning("Некорректный город (нет code): %s", city)
        msg = "city должен содержать code"
        raise ValueError(msg)
    if "domain" not in city:
        local_logger.warning("Некорректный город (нет domain): %s", city)
        msg = "city должен содержать domain"
        raise ValueError(msg)
    if not isinstance(city.get("code"), str) or not city["code"]:
        local_logger.warning("Некорректный city code: %s", city.get("code"))
        msg = "city['code'] должен быть непустой строкой"
        raise ValueError(msg)
    if not isinstance(city.get("domain"), str) or not city["domain"]:
        local_logger.warning("Некорректный city domain: %s", city.get("domain"))
        msg = "city['domain'] должен быть непустой строкой"
        raise ValueError(msg)

    # Проверка category
    if category is None:
        msg = "category не может быть None"
        raise TypeError(msg)
    if not isinstance(category, dict):
        local_logger.warning("Некорректная категория (не dict): %s", category)
        msg = "category должен быть словарём (dict)"
        raise TypeError(msg)

    # Получаем query категории с fallback на name
    category_query = category.get("query", category.get("name", ""))
    if not category_query:
        local_logger.warning("Категория не содержит query или name: %s", category)
        msg = "category должен содержать query или name"
        raise ValueError(msg)
    if not isinstance(category_query, str):
        local_logger.warning("category query/name не строка: %s", category_query)
        msg = "category['query'] или category['name'] должен быть строкой"
        raise TypeError(msg)

    # Проверка rubric_code если указан
    rubric_code = category.get("rubric_code", "")
    if rubric_code and not isinstance(rubric_code, str):
        local_logger.warning("rubric_code не строка: %s", rubric_code)
        msg = "category['rubric_code'] должен быть строкой"
        raise TypeError(msg)

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

    Raises:
        ValueError: Если список городов пуст.

    """
    from parser_2gis.utils.validation_utils import _get_logger

    local_logger = _get_logger()

    # Валидация пустого списка городов
    if not cities:
        local_logger.warning("Получен пустой список городов для генерации URL")
        msg = "Список городов не может быть пустым"
        raise ValueError(msg)

    urls: list[str] = []

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
            local_logger.exception("Ошибка при генерации URL для города %s: %s", city, e)
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
