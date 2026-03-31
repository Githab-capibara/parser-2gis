#!/usr/bin/env python3
"""
Тесты для новой функциональности параллельного парсинга городов.
"""

import sys
import urllib.parse
from pathlib import Path

import pytest

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импортируем напрямую без использования parser_2gis.__init__
from parser_2gis.resources.categories_93 import (  # noqa: E402
    CATEGORIES_93,
    generate_urls_for_city,
    get_categories_list,
    get_category_by_name,
)


class TestCategories93:
    """Тесты для списка из 93 категорий."""

    def test_categories_count(self):
        """Проверка количества категорий."""
        assert len(CATEGORIES_93) == 93, "Должно быть ровно 93 категории"

    def test_categories_structure(self):
        """Проверка структуры каждой категории."""
        required_keys = {"name", "query"}

        for i, cat in enumerate(CATEGORIES_93, 1):
            assert isinstance(cat, dict), f"Категория {i} должна быть словарём"
            assert required_keys.issubset(cat.keys()), (
                f"Категория {i} должна иметь ключи {required_keys}"
            )
            assert "name" in cat and len(cat["name"]) > 0, f"Категория {i} должна иметь название"
            assert "query" in cat and len(cat["query"]) > 0, (
                f"Категория {i} должна иметь поисковый запрос"
            )

            # rubric_code может быть None или строкой
            if "rubric_code" in cat and cat["rubric_code"] is not None:
                assert isinstance(cat["rubric_code"], str), (
                    f"rubric_code категории {i} должен быть строкой или None"
                )

    def test_get_categories_list(self):
        """Проверка функции get_categories_list."""
        categories = get_categories_list()
        assert len(categories) == 93
        assert categories == CATEGORIES_93

    def test_get_category_by_name_found(self):
        """Проверка поиска категории по названию (успешный)."""
        # Ищем известные категории
        cafe = get_category_by_name("Кафе")
        assert cafe is not None
        assert cafe["name"] == "Кафе"
        assert cafe["rubric_code"] == "161"

        restaurants = get_category_by_name("Рестораны")
        assert restaurants is not None
        assert restaurants["name"] == "Рестораны"

    def test_get_category_by_name_not_found(self):
        """Проверка поиска категории по названию (не найдено)."""
        result = get_category_by_name("Несуществующая категория")
        assert result is None

    def test_get_category_by_name_case_insensitive(self):
        """Проверка что поиск регистронезависимый."""
        cafe_lower = get_category_by_name("кафе")
        cafe_upper = get_category_by_name("КАФЕ")
        cafe_mixed = get_category_by_name("Кафе")

        assert cafe_lower is not None
        assert cafe_upper is not None
        assert cafe_mixed is not None
        assert cafe_lower == cafe_upper == cafe_mixed


class TestGenerateUrlsForCity:
    """Тесты для генерации URL по городам и категориям."""

    def test_generate_urls_single_category(self):
        """Проверка генерации URL для одной категории."""
        city = {"code": "moscow", "domain": "ru", "name": "Москва", "country_code": "ru"}

        categories = [{"name": "Кафе", "query": "Кафе", "rubric_code": "161"}]

        urls = generate_urls_for_city(city, categories)

        assert len(urls) == 1
        assert "2gis.ru/moscow" in urls[0]
        # Проверяем кодированный URL (urllib.parse.quote кодирует кириллицу)
        assert f"search/{urllib.parse.quote('Кафе')}" in urls[0]
        assert "rubricId/161" in urls[0]
        assert "filters/sort=name" in urls[0]

    def test_generate_urls_multiple_categories(self):
        """Проверка генерации URL для нескольких категорий."""
        city = {"code": "spb", "domain": "ru", "name": "Санкт-Петербург", "country_code": "ru"}

        categories = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "164"},
            {"name": "Бары", "query": "Бары", "rubric_code": "159"},
        ]

        urls = generate_urls_for_city(city, categories)

        assert len(urls) == 3
        assert all("2gis.ru/spb" in url for url in urls)

    def test_generate_urls_without_rubric(self):
        """Проверка генерации URL без рубрики."""
        city = {"code": "kazan", "domain": "ru", "name": "Казань", "country_code": "ru"}

        categories = [{"name": "Бургерные", "query": "Бургерные", "rubric_code": None}]

        urls = generate_urls_for_city(city, categories)

        assert len(urls) == 1
        assert "rubricId" not in urls[0]
        # Проверяем кодированный URL
        assert f"search/{urllib.parse.quote('Бургерные')}" in urls[0]

    def test_generate_urls_all_93_categories(self):
        """Проверка генерации URL для всех 93 категорий."""
        city = {"code": "moscow", "domain": "ru", "name": "Москва", "country_code": "ru"}

        urls = generate_urls_for_city(city, CATEGORIES_93)

        assert len(urls) == 93
        assert all("2gis.ru/moscow" in url for url in urls)
        assert all("filters/sort=name" in url for url in urls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
