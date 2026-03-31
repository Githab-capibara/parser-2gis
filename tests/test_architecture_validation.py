"""
Тесты для централизованной валидации.

Проверяет:
- Существование функций валидации конфигурации
- Использование валидации в parallel_parser.py и coordinator.py
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List

import pytest

# =============================================================================
# ТЕСТ 1: validate_cities_config
# =============================================================================


class TestValidateCitiesConfig:
    """Тесты для функции validate_cities_config."""

    def test_validate_cities_config_exists(self) -> None:
        """Проверка существования функции validate_cities_config.

        Функция должна существовать в parser_2gis.validation
        и предоставлять централизованную валидацию городов.
        """
        from parser_2gis.validation import validate_cities_config

        assert validate_cities_config is not None, "validate_cities_config должна существовать"
        assert callable(validate_cities_config), "validate_cities_config должна быть вызываемой"

    def test_validate_cities_config_valid(self) -> None:
        """Проверка валидации корректных данных городов.

        Функция не должна выбрасывать исключений для валидных данных.
        """
        from parser_2gis.validation import validate_cities_config

        cities: List[Dict[str, Any]] = [
            {"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"},
            {"code": "spb", "domain": "spb.2gis.ru", "name": "Санкт-Петербург"},
        ]

        # Не должно выбрасывать исключений
        try:
            validate_cities_config(cities, "cities")
        except Exception as e:
            pytest.fail(f"validate_cities_config выбросила исключение для валидных данных: {e}")

    def test_validate_cities_config_invalid(self) -> None:
        """Проверка валидации некорректных данных городов.

        Функция должна выбрасывать ValueError для некорректных данных.
        """
        from parser_2gis.validation import validate_cities_config

        # Пустой список
        with pytest.raises(ValueError):
            validate_cities_config([], "cities")

        # Не список
        with pytest.raises(ValueError):
            validate_cities_config("not a list", "cities")  # type: ignore

    def test_validate_cities_config_missing_fields(self) -> None:
        """Проверка валидации городов с отсутствующими полями.

        Функция должна выбрасывать ValueError для городов без code/domain.
        """
        from parser_2gis.validation import validate_cities_config

        cities_missing_fields: List[Dict[str, Any]] = [
            {"code": "msk"}  # Нет domain
        ]

        with pytest.raises(ValueError):
            validate_cities_config(cities_missing_fields, "cities")


# =============================================================================
# ТЕСТ 2: validate_categories_config
# =============================================================================


class TestValidateCategoriesConfig:
    """Тесты для функции validate_categories_config."""

    def test_validate_categories_config_exists(self) -> None:
        """Проверка существования функции validate_categories_config.

        Функция должна существовать в parser_2gis.validation
        и предоставлять централизованную валидацию категорий.
        """
        from parser_2gis.validation import validate_categories_config

        assert validate_categories_config is not None, (
            "validate_categories_config должна существовать"
        )
        assert callable(validate_categories_config), (
            "validate_categories_config должна быть вызываемой"
        )

    def test_validate_categories_config_valid(self) -> None:
        """Проверка валидации корректных данных категорий.

        Функция не должна выбрасывать исключений для валидных данных.
        """
        from parser_2gis.validation import validate_categories_config

        categories: List[Dict[str, Any]] = [
            {"name": "Рестораны", "query": "рестораны"},
            {"name": "Аптеки", "query": "аптеки"},
        ]

        # Не должно выбрасывать исключений
        try:
            validate_categories_config(categories, "categories")
        except Exception as e:
            pytest.fail(f"validate_categories_config выбросила исключение для валидных данных: {e}")

    def test_validate_categories_config_invalid(self) -> None:
        """Проверка валидации некорректных данных категорий.

        Функция должна выбрасывать ValueError для некорректных данных.
        """
        from parser_2gis.validation import validate_categories_config

        # Пустой список
        with pytest.raises(ValueError):
            validate_categories_config([], "categories")

        # Не список
        with pytest.raises(ValueError):
            validate_categories_config("not a list", "categories")  # type: ignore


# =============================================================================
# ТЕСТ 3: validate_parallel_config
# =============================================================================


class TestValidateParallelConfig:
    """Тесты для функции validate_parallel_config."""

    def test_validate_parallel_config_exists(self) -> None:
        """Проверка существования функции validate_parallel_config.

        Функция должна существовать в parser_2gis.validation
        и предоставлять централизованную валидацию параллельного парсинга.
        """
        from parser_2gis.validation import validate_parallel_config

        assert validate_parallel_config is not None, "validate_parallel_config должна существовать"
        assert callable(validate_parallel_config), "validate_parallel_config должна быть вызываемой"

    def test_validate_parallel_config_valid(self) -> None:
        """Проверка валидации корректной конфигурации.

        Функция не должна выбрасывать исключений для валидных данных.
        """
        from parser_2gis.validation import validate_parallel_config

        # Не должно выбрасывать исключений
        try:
            validate_parallel_config(
                max_workers=5,
                timeout_per_url=300,
                min_workers=1,
                max_workers_limit=100,
                min_timeout=60,
                max_timeout=3600,
            )
        except Exception as e:
            pytest.fail(f"validate_parallel_config выбросила исключение для валидных данных: {e}")

    def test_validate_parallel_config_invalid_workers(self) -> None:
        """Проверка валидации некорректного max_workers.

        Функция должна выбрасывать ValueError для некорректного max_workers.
        """
        from parser_2gis.validation import validate_parallel_config

        # Слишком мало workers
        with pytest.raises(ValueError):
            validate_parallel_config(
                max_workers=0,
                timeout_per_url=300,
                min_workers=1,
                max_workers_limit=100,
                min_timeout=60,
                max_timeout=3600,
            )

        # Слишком много workers
        with pytest.raises(ValueError):
            validate_parallel_config(
                max_workers=200,
                timeout_per_url=300,
                min_workers=1,
                max_workers_limit=100,
                min_timeout=60,
                max_timeout=3600,
            )

    def test_validate_parallel_config_invalid_timeout(self) -> None:
        """Проверка валидации некорректного timeout.

        Функция должна выбрасывать ValueError для некорректного timeout.
        """
        from parser_2gis.validation import validate_parallel_config

        # Слишком маленький timeout
        with pytest.raises(ValueError):
            validate_parallel_config(
                max_workers=5,
                timeout_per_url=10,
                min_workers=1,
                max_workers_limit=100,
                min_timeout=60,
                max_timeout=3600,
            )


# =============================================================================
# ТЕСТ 4: Использование валидации в parallel_parser.py
# =============================================================================


class TestValidationInParallelParser:
    """Тесты для использования валидации в parallel_parser.py."""

    def test_validation_used_in_parallel_parser(self) -> None:
        """Проверка использования валидации в parallel_parser.py.

        parallel_parser.py должен использовать централизованные функции валидации.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_parser_file = project_root / "parallel" / "parallel_parser.py"

        assert parallel_parser_file.exists(), "parallel/parallel_parser.py должен существовать"

        content = parallel_parser_file.read_text(encoding="utf-8")

        # Проверяем импорт функций валидации
        assert "validate_cities_config" in content, (
            "parallel_parser.py должен использовать validate_cities_config"
        )
        assert "validate_categories_config" in content, (
            "parallel_parser.py должен использовать validate_categories_config"
        )
        assert "validate_parallel_config" in content, (
            "parallel_parser.py должен использовать validate_parallel_config"
        )

        # Проверяем что импорт есть из parser_2gis.validation
        assert "from parser_2gis.validation import" in content, (
            "parallel_parser.py должен импортировать из parser_2gis.validation"
        )

    def test_parallel_parser_calls_validation(self) -> None:
        """Проверка что parallel_parser.py вызывает функции валидации.

        Функции валидации должны вызываться в __init__ методе.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_parser_file = project_root / "parallel" / "parallel_parser.py"

        content = parallel_parser_file.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content, filename=str(parallel_parser_file))
        except SyntaxError:
            pytest.fail("parallel_parser.py содержит синтаксические ошибки")

        # Ищем вызовы функций валидации в классе ParallelCityParser
        validation_calls: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ParallelCityParser":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        for subnode in ast.walk(item):
                            if isinstance(subnode, ast.Call):
                                if isinstance(subnode.func, ast.Name):
                                    if "validate" in subnode.func.id:
                                        validation_calls.append(subnode.func.id)

        assert len(validation_calls) >= 3, (
            f"ParallelCityParser.__init__ должен вызывать >=3 функций валидации, "
            f"найдено: {validation_calls}"
        )


# =============================================================================
# ТЕСТ 5: Использование валидации в coordinator.py
# =============================================================================


class TestValidationInCoordinator:
    """Тесты для использования валидации в coordinator.py."""

    def test_validation_used_in_coordinator(self) -> None:
        """Проверка использования валидации в coordinator.py.

        coordinator.py должен использовать централизованные функции валидации.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Проверяем импорт функций валидации
        assert "validate_cities_config" in content, (
            "coordinator.py должен использовать validate_cities_config"
        )
        assert "validate_categories_config" in content, (
            "coordinator.py должен использовать validate_categories_config"
        )
        assert "validate_parallel_config" in content, (
            "coordinator.py должен использовать validate_parallel_config"
        )

        # Проверяем что импорт есть из parser_2gis.validation
        assert "from parser_2gis.validation import" in content, (
            "coordinator.py должен импортировать из parser_2gis.validation"
        )

    def test_coordinator_calls_validation(self) -> None:
        """Проверка что coordinator.py вызывает функции валидации.

        Функции валидации должны вызываться в __init__ методе.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        content = coordinator_file.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content, filename=str(coordinator_file))
        except SyntaxError:
            pytest.fail("coordinator.py содержит синтаксические ошибки")

        # Ищем вызовы функций валидации в классе ParallelCoordinator
        validation_calls: List[str] = []
        validate_methods_called: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ParallelCoordinator":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        for subnode in ast.walk(item):
                            if isinstance(subnode, ast.Call):
                                if isinstance(subnode.func, ast.Name):
                                    if "validate" in subnode.func.id:
                                        validation_calls.append(subnode.func.id)
                                # Ищем вызов self._validate_inputs
                                elif isinstance(subnode.func, ast.Attribute):
                                    if "_validate_inputs" in subnode.func.attr:
                                        validate_methods_called.append("_validate_inputs")
                    # Также ищем в методе _validate_inputs
                    elif isinstance(item, ast.FunctionDef) and item.name == "_validate_inputs":
                        for subnode in ast.walk(item):
                            if isinstance(subnode, ast.Call):
                                if isinstance(subnode.func, ast.Name):
                                    if "validate" in subnode.func.id:
                                        validation_calls.append(subnode.func.id)

        # Должны быть вызовы валидации либо напрямую, либо через _validate_inputs
        total_validation_calls = len(validation_calls) + (3 if validate_methods_called else 0)

        assert total_validation_calls >= 3, (
            f"ParallelCoordinator должен вызывать >=3 функций валидации, "
            f"найдено: {validation_calls + validate_methods_called}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
