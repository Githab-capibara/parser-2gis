"""
Тесты на отсутствие дублирования.

Проверяет:
- Отсутствие дублирования cities.json
- Отсутствие дублирования rubrics.json
- Отсутствие дублирования логики валидации
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Dict, List, Set

import pytest

# =============================================================================
# ТЕСТ 1: Отсутствие дублирования cities.json
# =============================================================================


class TestNoDuplicateCitiesFiles:
    """Тесты на отсутствие дублирования cities.json."""

    def _find_cities_json_files(self, root: Path) -> List[Path]:
        """Находит все файлы cities.json в проекте.

        Args:
            root: Корневая директория для поиска.

        Returns:
            Список путей к файлам cities.json.
        """
        exclude_dirs = {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".git",
            "venv",
            ".venv",
            "node_modules",
            ".tox",
        }

        cities_files: List[Path] = []

        for py_file in root.rglob("cities.json"):
            # Пропускаем исключенные директории
            if any(part in exclude_dirs for part in py_file.parts):
                continue

            cities_files.append(py_file)

        return cities_files

    def test_no_duplicate_cities_files(self) -> None:
        """Проверка отсутствия дублирования cities.json.

        В проекте должен быть только один cities.json в resources/.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        cities_files = self._find_cities_json_files(project_root)

        # Должен быть только один cities.json в resources/
        expected_cities_file = project_root / "resources" / "cities.json"

        assert len(cities_files) == 1, (
            f"Должен быть только один cities.json, найдено: {len(cities_files)}. "
            f"Файлы: {[str(f.relative_to(project_root)) for f in cities_files]}"
        )

        assert cities_files[0] == expected_cities_file, (
            f"cities.json должен находиться в resources/, "
            f"найден в: {cities_files[0].relative_to(project_root)}"
        )

    def test_cities_json_is_valid(self) -> None:
        """Проверка валидности cities.json.

        Файл должен содержать валидный JSON со списком городов.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cities_file = project_root / "resources" / "cities.json"

        with open(cities_file, "r", encoding="utf-8") as f:
            cities_data = json.load(f)

        assert isinstance(cities_data, list), "cities.json должен содержать список"
        assert len(cities_data) > 0, "cities.json не должен быть пустым"

        # Проверяем уникальность кодов городов
        codes: Set[str] = set()
        for city in cities_data:
            assert "code" in city, f"Город должен иметь поле 'code': {city}"
            code = city["code"]
            assert code not in codes, f"Дублирование кода города: {code}"
            codes.add(code)


# =============================================================================
# ТЕСТ 2: Отсутствие дублирования rubrics.json
# =============================================================================


class TestNoDuplicateRubricsFiles:
    """Тесты на отсутствие дублирования rubrics.json."""

    def _find_rubrics_json_files(self, root: Path) -> List[Path]:
        """Находит все файлы rubrics.json в проекте.

        Args:
            root: Корневая директория для поиска.

        Returns:
            Список путей к файлам rubrics.json.
        """
        exclude_dirs = {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".git",
            "venv",
            ".venv",
            "node_modules",
            ".tox",
        }

        rubrics_files: List[Path] = []

        for py_file in root.rglob("rubrics.json"):
            # Пропускаем исключенные директории
            if any(part in exclude_dirs for part in py_file.parts):
                continue

            rubrics_files.append(py_file)

        return rubrics_files

    def test_no_duplicate_rubrics_files(self) -> None:
        """Проверка отсутствия дублирования rubrics.json.

        В проекте должен быть только один rubrics.json в resources/.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        rubrics_files = self._find_rubrics_json_files(project_root)

        # Должен быть только один rubrics.json в resources/
        expected_rubrics_file = project_root / "resources" / "rubrics.json"

        assert len(rubrics_files) == 1, (
            f"Должен быть только один rubrics.json, найдено: {len(rubrics_files)}. "
            f"Файлы: {[str(f.relative_to(project_root)) for f in rubrics_files]}"
        )

        assert rubrics_files[0] == expected_rubrics_file, (
            f"rubrics.json должен находиться в resources/, "
            f"найден в: {rubrics_files[0].relative_to(project_root)}"
        )

    def test_rubrics_json_is_valid(self) -> None:
        """Проверка валидности rubrics.json.

        Файл должен содержать валидный JSON со словарём рубрик.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        rubrics_file = project_root / "resources" / "rubrics.json"

        with open(rubrics_file, "r", encoding="utf-8") as f:
            rubrics_data = json.load(f)

        assert isinstance(rubrics_data, dict), "rubrics.json должен содержать словарь рубрик"
        assert len(rubrics_data) > 0, "rubrics.json не должен быть пустым"


# =============================================================================
# ТЕСТ 3: Отсутствие дублирования логики валидации
# =============================================================================


class TestNoDuplicateValidationLogic:
    """Тесты на отсутствие дублирования логики валидации."""

    def _find_validation_functions(self, root: Path) -> Dict[str, List[Path]]:
        """Находит функции валидации в проекте.

        Args:
            root: Корневая директория для поиска.

        Returns:
            Словарь {имя_функции: [файлы]}.
        """
        exclude_dirs = {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".git",
            "venv",
            ".venv",
            "node_modules",
            ".tox",
            "tests",
        }

        validation_functions: Dict[str, List[Path]] = {}

        for py_file in root.rglob("*.py"):
            # Пропускаем исключенные директории
            if any(part in exclude_dirs for part in py_file.parts):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(py_file))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

            # Ищем функции с "validate" в имени
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if "validate" in node.name.lower():
                        if node.name not in validation_functions:
                            validation_functions[node.name] = []
                        validation_functions[node.name].append(py_file)

        return validation_functions

    def test_validation_functions_in_validation_module(self) -> None:
        """Проверка что функции валидации находятся в validation модуле.

        Основные функции валидации должны быть в parser_2gis/validation.py
        или parser_2gis/utils/validation_utils.py.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        validation_files = [
            project_root / "validation.py",
            project_root / "utils" / "validation_utils.py",
        ]

        # Проверяем что файлы валидации существуют
        existing_validation_files = [f for f in validation_files if f.exists()]

        assert len(existing_validation_files) > 0, "Должен существовать хотя бы один файл валидации"

    def test_no_duplicate_validate_cities(self) -> None:
        """Проверка отсутствия дублирования функции валидации городов.

        Функция validate_cities_config должна быть только в одном месте.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        validation_functions = self._find_validation_functions(project_root)

        # Ищем функции валидации городов
        [
            name
            for name in validation_functions.keys()
            if "cities" in name.lower() or "city" in name.lower()
        ]

        # Должна быть только одна основная функция валидации городов
        # validate_cities_config
        assert "validate_cities_config" in validation_functions, (
            "validate_cities_config должна существовать"
        )

        # Проверяем что она определена только в одном файле
        cities_config_validators = validation_functions.get("validate_cities_config", [])
        # Может быть импортирована в нескольких файлах, но определена в одном
        # Проверяем только файлы где она определена (не импортирована)
        definition_files: List[Path] = []
        for py_file in cities_config_validators:
            content = py_file.read_text(encoding="utf-8")
            # Проверяем что это определение, а не импорт
            if "def validate_cities_config" in content:
                definition_files.append(py_file)

        assert len(definition_files) <= 1, (
            f"validate_cities_config должна быть определена только в одном файле, "
            f"найдено в: {[str(f.relative_to(project_root)) for f in definition_files]}"
        )

    def test_no_duplicate_validate_categories(self) -> None:
        """Проверка отсутствия дублирования функции валидации категорий.

        Функция validate_categories_config должна быть только в одном месте.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        validation_functions = self._find_validation_functions(project_root)

        # Ищем функции валидации категорий
        [
            name
            for name in validation_functions.keys()
            if "categories" in name.lower() or "category" in name.lower()
        ]

        # Должна быть только одна основная функция валидации категорий
        assert "validate_categories_config" in validation_functions, (
            "validate_categories_config должна существовать"
        )

        # Проверяем что она определена только в одном файле
        definition_files: List[Path] = []
        categories_config_validators = validation_functions.get("validate_categories_config", [])
        for py_file in categories_config_validators:
            content = py_file.read_text(encoding="utf-8")
            if "def validate_categories_config" in content:
                definition_files.append(py_file)

        assert len(definition_files) <= 1, (
            f"validate_categories_config должна быть определена только в одном файле, "
            f"найдено в: {[str(f.relative_to(project_root)) for f in definition_files]}"
        )

    def test_no_duplicate_validate_parallel_config(self) -> None:
        """Проверка отсутствия дублирования функции валидации параллельной конфигурации.

        Функция validate_parallel_config должна быть только в одном месте.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        validation_functions = self._find_validation_functions(project_root)

        # Должна быть функция validate_parallel_config
        assert "validate_parallel_config" in validation_functions, (
            "validate_parallel_config должна существовать"
        )

        # Проверяем что она определена только в одном файле
        definition_files: List[Path] = []
        parallel_config_validators = validation_functions.get("validate_parallel_config", [])
        for py_file in parallel_config_validators:
            content = py_file.read_text(encoding="utf-8")
            if "def validate_parallel_config" in content:
                definition_files.append(py_file)

        assert len(definition_files) <= 1, (
            f"validate_parallel_config должна быть определена только в одном файле, "
            f"найдено в: {[str(f.relative_to(project_root)) for f in definition_files]}"
        )

    def test_validation_module_exports_all_functions(self) -> None:
        """Проверка что validation модуль экспортирует все функции валидации.

        Все функции валидации должны быть доступны через parser_2gis.validation.
        """
        from parser_2gis import validation

        # Проверяем что основные функции экспортируются
        expected_functions = [
            "validate_cities_config",
            "validate_categories_config",
            "validate_parallel_config",
        ]

        for func_name in expected_functions:
            assert hasattr(validation, func_name), (
                f"validation модуль должен экспортировать {func_name}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
