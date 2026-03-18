"""
Тесты для проверки TypedDict категорий.

Проверяет корректность типизации словарей категорий.
Тесты покрывают исправления из отчета FIXES_IMPLEMENTATION_REPORT.md:
- Добавлен TypedDict для типизации словарей категорий
- Функция get_category_by_name возвращает CategoryDict
- Type checking через mypy
"""

import subprocess
import sys
from typing import Optional

import pytest


class TestCategoryTypedDict:
    """Тесты для проверки TypedDict категорий."""

    def test_get_category_by_name_returns_typed_dict(self):
        """
        Тест 4.1: Проверка get_category_by_name.
        
        Вызывает функцию с существующей категорией.
        Проверяет что возвращается CategoryDict со всеми полями.
        """
        from parser_2gis.data.categories_93 import (
            CategoryDict,
            CATEGORIES_93,
            get_category_by_name,
        )
        
        # Вызываем функцию с существующей категорией
        result = get_category_by_name("Кафе")
        
        # Проверяем что результат не None
        assert result is not None, "Категория 'Кафе' не найдена"
        
        # Проверяем что это словарь с правильными полями
        assert isinstance(result, dict), "Результат должен быть словарем"
        
        # Проверяем наличие всех обязательных полей CategoryDict
        assert "name" in result, "Отсутствует поле 'name'"
        assert "query" in result, "Отсутствует поле 'query'"
        assert "rubric_code" in result, "Отсутствует поле 'rubric_code'"
        
        # Проверяем типы полей
        assert isinstance(result["name"], str), "Поле 'name' должно быть строкой"
        assert isinstance(result["query"], str), "Поле 'query' должно быть строкой"
        # rubric_code может быть str или None
        assert result["rubric_code"] is None or isinstance(result["rubric_code"], str), \
            "Поле 'rubric_code' должно быть строкой или None"
        
        # Проверяем конкретные значения
        assert result["name"] == "Кафе"
        assert result["query"] == "Кафе"
        assert result["rubric_code"] == "161"

    def test_get_category_by_name_returns_none_for_unknown(self):
        """
        Тест 4.2: Проверка get_category_by_name для несуществующей категории.
        
        Вызывает функцию с несуществующей категорией.
        Проверяет что возвращается None.
        """
        from parser_2gis.data.categories_93 import get_category_by_name
        
        # Вызываем функцию с несуществующей категорией
        result = get_category_by_name("Несуществующая категория 12345")
        
        # Проверяем что результат None
        assert result is None, "Для несуществующей категории должен вернуться None"

    def test_all_categories_have_required_fields(self):
        """
        Проверка что все категории в CATEGORIES_93 имеют требуемые поля.
        
        Проверяет что каждый словарь в списке имеет все поля CategoryDict.
        """
        from parser_2gis.data.categories_93 import CATEGORIES_93
        
        required_fields = {"name", "query", "rubric_code"}
        
        for i, category in enumerate(CATEGORIES_93, 1):
            # Проверяем наличие всех полей
            assert required_fields.issubset(category.keys()), \
                f"Категория {i} ({category.get('name', 'unknown')}) не имеет всех полей: {required_fields - set(category.keys())}"
            
            # Проверяем что name и query - строки
            assert isinstance(category["name"], str), \
                f"Категория {i}: поле 'name' должно быть строкой"
            assert isinstance(category["query"], str), \
                f"Категория {i}: поле 'query' должно быть строкой"
            
            # Проверяем что rubric_code - строка или None
            assert category["rubric_code"] is None or isinstance(category["rubric_code"], str), \
                f"Категория {i}: поле 'rubric_code' должно быть строкой или None"
        
        # Проверяем что всего 93 категории
        assert len(CATEGORIES_93) == 93, f"Ожидалось 93 категории, найдено: {len(CATEGORIES_93)}"


class TestCategoryFunctions:
    """Тесты для вспомогательных функций категорий."""

    def test_get_categories_list_returns_all(self):
        """
        Проверка что get_categories_list возвращает все категории.
        """
        from parser_2gis.data.categories_93 import (
            CATEGORIES_93,
            get_categories_list,
        )
        
        result = get_categories_list()
        
        assert len(result) == 93
        assert result is CATEGORIES_93  # Тот же объект

    def test_generate_urls_for_city(self):
        """
        Проверка генерации URL для города.
        """
        from parser_2gis.data.categories_93 import generate_urls_for_city
        from urllib.parse import unquote
        
        # Тестовый город
        city = {
            "code": "132",
            "domain": "msk",
        }
        
        # Генерируем URL для первых 3 категорий
        test_categories = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "164"},
            {"name": "Бары", "query": "Бары", "rubric_code": "159"},
        ]
        
        urls = generate_urls_for_city(city, test_categories)
        
        # Проверяем количество URL
        assert len(urls) == 3
        
        # Проверяем формат URL (декодируем URL-encoded символы)
        assert urls[0].startswith("https://2gis.msk/132/search/")
        decoded_url = unquote(urls[0])
        assert "Кафе" in decoded_url
        assert "rubricId/161" in urls[0]

    def test_generate_urls_for_city_with_none_rubric(self):
        """
        Проверка генерации URL для категории без rubric_code.
        """
        from parser_2gis.data.categories_93 import generate_urls_for_city
        from urllib.parse import unquote
        
        city = {
            "code": "132",
            "domain": "msk",
        }
        
        # Категория без rubric_code
        test_categories = [
            {"name": "Бургерные", "query": "Бургерные", "rubric_code": None},
        ]
        
        urls = generate_urls_for_city(city, test_categories)
        
        assert len(urls) == 1
        # URL не должен содержать rubricId
        assert "rubricId" not in urls[0]
        decoded_url = unquote(urls[0])
        assert "Бургерные" in decoded_url


class TestTypeChecking:
    """Тесты для проверки type checking через mypy."""

    def test_mypy_passes_on_categories_module(self):
        """
        Тест 4.3: Проверка type checking.
        
        Запускает mypy на тестовом файле.
        Проверяет что нет type errors.
        """
        # Запускаем mypy на модуле categories_93
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--ignore-missing-imports",
                "parser_2gis/data/categories_93.py",
            ],
            capture_output=True,
            text=True,
            cwd="/home/d/parser-2gis",
        )
        
        # mypy может вернуть 0 (успех) или 1 (ошибки)
        # Если mypy не установлен, пропускаем тест
        if result.returncode == 127:
            pytest.skip("mypy не установлен")
        
        # Выводим вывод mypy для отладки
        print(f"mypy stdout: {result.stdout}")
        print(f"mypy stderr: {result.stderr}")
        
        # Проверяем что нет критичных ошибок в categories_93.py
        # Игнорируем ошибки в других файлах
        if result.returncode != 0:
            errors_in_categories = [
                e for e in result.stdout.split('\n')
                if e and 'error:' in e.lower() and 'categories_93.py' in e
            ]
            
            # Тест проходит если нет ошибок в categories_93.py
            assert len(errors_in_categories) == 0, \
                f"mypy обнаружил ошибки в categories_93.py: {errors_in_categories}"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
