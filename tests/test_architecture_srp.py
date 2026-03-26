"""
Тесты на проверку соблюдения принципа единственной ответственности (SRP).

Проверяет:
- Отсутствие модуля common.py (разделён на специализированные модули)
- Существование специализированных утилит в utils/
- Отсутствие импортов из common.py

SRP (Single Responsibility Principle):
Каждый модуль должен иметь одну ответственность и быть специализированным.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

import pytest


class TestCommonPyModuleDoesNotExist:
    """Тесты на отсутствие общего модуля common.py."""

    def test_common_py_module_does_not_exist(self) -> None:
        """Проверяет что common.py удалён из проекта.

        Согласно SRP, общий модуль common.py был разделён на
        специализированные модули в utils/.

        Raises:
            AssertionError: Если common.py существует.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        common_py = project_root / "common.py"

        assert not common_py.exists(), (
            f"common.py не должен существовать в {project_root}. "
            "Модуль должен быть разделён на специализированные утилиты."
        )

    def test_no_common_py_in_parser_2gis_root(self) -> None:
        """Проверяет что нет common.py в корне parser_2gis/.

        Дополнительная проверка что common.py отсутствует.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Ищем все файлы common.py
        common_files = list(project_root.rglob("common.py"))

        # Исключаем __pycache__ и тесты
        common_files = [
            f for f in common_files if "__pycache__" not in str(f) and "tests" not in str(f)
        ]

        assert len(common_files) == 0, (
            f"Обнаружены файлы common.py: {[str(f) for f in common_files]}. "
            "Все функции должны быть распределены по специализированным модулям."
        )


class TestUtilsModulesExist:
    """Тесты на существование специализированных утилит."""

    @pytest.mark.parametrize(
        "module_name,expected_functions",
        [
            ("data_utils", ["unwrap_dot_dict"]),
            ("math_utils", ["floor_to_hundreds"]),
            ("temp_file_manager", ["TempFileManager", "TempFileTimer"]),
            (
                "validation_utils",
                ["_validate_city", "_validate_category", "report_from_validation_error"],
            ),
            ("url_utils", ["generate_category_url", "generate_city_urls", "url_query_encode"]),
            ("sanitizers", ["_sanitize_value", "_is_sensitive_key"]),
            ("path_utils", ["validate_path_safety", "validate_path_traversal"]),
        ],
        ids=[
            "data_utils",
            "math_utils",
            "temp_file_manager",
            "validation_utils",
            "url_utils",
            "sanitizers",
            "path_utils",
        ],
    )
    def test_utils_module_exists_with_functions(
        self, module_name: str, expected_functions: List[str]
    ) -> None:
        """Проверяет что модуль utils/{module_name}.py существует и содержит функции.

        Args:
            module_name: Имя модуля для проверки.
            expected_functions: Список ожидаемых функций/классов.

        Raises:
            AssertionError: Если модуль не существует или не содержит функций.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"
        module_path = utils_dir / f"{module_name}.py"

        assert module_path.exists(), f"Модуль {module_name}.py должен существовать в utils/"

        content = module_path.read_text(encoding="utf-8")
        tree = ast.parse(content)

        # Собираем все имена функций и классов
        defined_names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.append(node.name)

        # Проверяем наличие ожидаемых функций/классов
        missing_functions = [func for func in expected_functions if func not in defined_names]

        assert len(missing_functions) == 0, (
            f"Модуль {module_name}.py не содержит функций: {missing_functions}"
        )

    def test_utils_data_utils_exists(self) -> None:
        """Проверяет что data_utils.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        data_utils = project_root / "utils" / "data_utils.py"

        assert data_utils.exists(), "data_utils.py должен существовать в utils/"

    def test_utils_math_utils_exists(self) -> None:
        """Проверяет что math_utils.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        math_utils = project_root / "utils" / "math_utils.py"

        assert math_utils.exists(), "math_utils.py должен существовать в utils/"

    def test_utils_temp_file_manager_exists(self) -> None:
        """Проверяет что temp_file_manager.py существует в utils/."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        temp_file_manager = project_root / "utils" / "temp_file_manager.py"

        assert temp_file_manager.exists(), "temp_file_manager.py должен существовать в utils/"

    def test_utils_init_exports_all_modules(self) -> None:
        """Проверяет что utils/__init__.py экспортирует основные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_init = project_root / "utils" / "__init__.py"

        assert utils_init.exists(), "utils/__init__.py должен существовать"

        content = utils_init.read_text(encoding="utf-8")

        # Проверяем что основные модули импортируются
        # temp_file_manager не экспортируется из __init__ по дизайну
        expected_modules = [
            "cache_monitor",
            "data_utils",
            "decorators",
            "math_utils",
            "path_utils",
            "sanitizers",
            "url_utils",
            "validation_utils",
        ]

        missing_imports = []
        for module in expected_modules:
            if f"from .{module}" not in content:
                missing_imports.append(module)

        assert len(missing_imports) == 0, (
            f"utils/__init__.py не импортирует модули: {missing_imports}"
        )


class TestNoImportsFromCommon:
    """Тесты на отсутствие импортов из common.py."""

    def test_no_imports_from_common(self) -> None:
        """Проверяет что нет импортов из common.py.

        Сканирует все .py файлы проекта на наличие импортов
        из common.py.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        violations: List[Tuple[str, int, str]] = []

        for py_file in project_root.rglob("*.py"):
            # Пропускаем тесты и __pycache__
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and "common" in node.module:
                            violations.append(
                                (
                                    str(py_file.relative_to(project_root)),
                                    node.lineno or 0,
                                    f"from {node.module} import ...",
                                )
                            )
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if "common" in alias.name:
                                violations.append(
                                    (
                                        str(py_file.relative_to(project_root)),
                                        node.lineno or 0,
                                        f"import {alias.name}",
                                    )
                                )

            except (SyntaxError, UnicodeDecodeError):
                # Пропускаем файлы с ошибками синтаксиса
                continue

        assert len(violations) == 0, (
            "Обнаружены импорты из common.py:\n"
            + "\n".join(f"  {f}:{line}: {i}" for f, line, i in violations)
            + "\n\ncommon.py был удалён. Используйте специализированные модули из utils/."
        )

    def test_no_references_to_common_module(self) -> None:
        """Проверяет что нет ссылок на common module в коде."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Паттерны которые указывают на использование common.py
        common_patterns = [
            "from .common import",
            "from parser_2gis.common import",
            "import common",
            "import parser_2gis.common",
        ]

        violations: List[Tuple[str, int, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    # Пропускаем комментарии и строки документации
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue

                    for pattern in common_patterns:
                        if pattern in line:
                            violations.append(
                                (str(py_file.relative_to(project_root)), line_num, line.strip())
                            )

            except (SyntaxError, UnicodeDecodeError):
                continue

        assert len(violations) == 0, "Обнаружены ссылки на common.py:\n" + "\n".join(
            f"  {f}:{line}: {c}" for f, line, c in violations
        )


class TestSRPCompliance:
    """Тесты на общее соответствие принципу SRP."""

    def test_each_util_module_has_single_responsibility(self) -> None:
        """Проверяет что каждый модуль utils/ имеет одну ответственность.

        Модули должны быть специализированными:
        - data_utils: преобразование данных
        - math_utils: математические операции
        - path_utils: валидация путей
        - url_utils: генерация URL
        - sanitizers: санитаризация данных
        - validation_utils: валидация
        - temp_file_manager: управление временными файлами
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        # Ожидаемые ответственности модулей
        expected_responsibilities = {
            "data_utils.py": ["преобразование", "трансформация", "данные"],
            "math_utils.py": ["математичес", "вычислени", "округлени"],
            "path_utils.py": ["путь", "валидаци", "безопасност"],
            "url_utils.py": ["url", "генераци", "кодировани"],
            "sanitizers.py": ["санитаризаци", "очистк", "чувствительн"],
            "validation_utils.py": ["валидаци", "проверк", "ошибк"],
            "temp_file_manager.py": ["временн", "файл", "очистк"],
            "cache_monitor.py": ["кэш", "статистик", "мониторинг"],
            "decorators.py": ["декоратор", "ожидани", "poll"],
        }

        for module_name, keywords in expected_responsibilities.items():
            module_path = utils_dir / module_name

            if not module_path.exists():
                pytest.fail(f"Модуль {module_name} не найден")

            content = module_path.read_text(encoding="utf-8").lower()

            # Проверяем что хотя бы один ключевой слово присутствует
            has_responsibility = any(keyword in content for keyword in keywords)

            assert has_responsibility, (
                f"Модуль {module_name} не соответствует ожидаемой ответственности. "
                f"Ключевые слова: {keywords}"
            )

    def test_no_god_module_in_utils(self) -> None:
        """Проверяет что нет модулей с чрезмерной ответственностью в utils/.

        Модули в utils/ должны быть компактными (< 500 строк).
        Допускаются исключения для сложных модулей.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        max_lines = 500

        # Допустимые исключения для сложных утилит
        allowed_exceptions = {
            "temp_file_manager.py",  # Управление временными файлами
            "decorators.py",  # Декораторы ожидания
            "sanitizers.py",  # Санитаризация данных
        }

        large_modules: List[Tuple[str, int]] = []

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            lines = len(content.splitlines())

            if lines > max_lines:
                if py_file.name not in allowed_exceptions:
                    large_modules.append((py_file.name, lines))

        assert len(large_modules) == 0, (
            f"Модули в utils/ превышают {max_lines} строк:\n"
            + "\n".join(f"  {name}: {lines} строк" for name, lines in large_modules)
            + "\n\nРазделите большие модули на специализированные."
        )


__all__ = [
    "TestCommonPyModuleDoesNotExist",
    "TestUtilsModulesExist",
    "TestNoImportsFromCommon",
    "TestSRPCompliance",
]
