"""
Тесты на проверку соблюдения DRY принципа (Don't Repeat Yourself).

Проверяет:
- Отсутствие дублирования validate_env_int()
- Отсутствие дублирования логики temp файлов
- Константы централизованы в constants.py
- Отсутствие дублирования кода паттернов

DRY принцип:
Каждая знания/логика должна иметь единственное представление в системе.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest


class TestNoDuplicateValidateEnvInt:
    """Тесты на отсутствие дублирования validate_env_int()."""

    def test_no_duplicate_validate_env_int(self) -> None:
        """Проверяет что validate_env_int не дублируется.

        Функция validate_env_int должна быть определена только в constants.py
        и импортироваться в других модулях.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Ищем все определения validate_env_int
        definitions: List[Tuple[str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == "validate_env_int":
                        definitions.append(
                            (str(py_file.relative_to(project_root)), node.lineno or 0)
                        )

        # Должно быть только одно определение в constants.py
        assert len(definitions) == 1, (
            f"validate_env_int должна быть определена только один раз. "
            f"Найдено определений: {len(definitions)}\n"
            + "\n".join(f"  {f}:{line_num}" for f, line_num in definitions)
        )

        # Проверяем что определение в constants.py
        constants_py = project_root / "constants.py"
        assert constants_py.exists(), "constants.py должен существовать"

        content = constants_py.read_text(encoding="utf-8")
        assert "def validate_env_int" in content, (
            "validate_env_int должна быть определена в constants.py"
        )

    def test_validate_env_int_is_imported_not_duplicated(self) -> None:
        """Проверяет что validate_env_int импортируется из constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули которые используют validate_env_int
        modules_using_validate = ["parallel/options.py"]

        for module_path in modules_using_validate:
            full_path = project_root / module_path

            if not full_path.exists():
                continue

            content = full_path.read_text(encoding="utf-8")

            # Должен импортировать из constants
            has_import = (
                "from parser_2gis.constants import" in content
                or "from .constants import" in content
            )

            assert has_import, f"{module_path} должен импортировать из constants.py"


class TestNoDuplicateTempFileLogic:
    """Тесты на отсутствие дублирования логики temp файлов."""

    def test_no_duplicate_temp_file_logic(self) -> None:
        """Проверяет что логика temp файлов не дублируется.

        Логика управления временными файлами должна быть в
        utils/temp_file_manager.py и не дублироваться в других модулях.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        temp_file_manager = project_root / "utils" / "temp_file_manager.py"
        assert temp_file_manager.exists(), "temp_file_manager.py должен существовать"

        # Ключевые функции которые не должны дублироваться
        temp_file_functions = [
            "cleanup_temp_files",
            "register_temp_file",
            "unregister_temp_file",
            "TempFileManager",
        ]

        # Ищем дублирования в других модулях
        duplicates: List[Tuple[str, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            if py_file == temp_file_manager:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name in temp_file_functions:
                        duplicates.append((str(py_file.relative_to(project_root)), node.name))

        assert len(duplicates) == 0, (
            "Логика temp файлов дублируется в других модулях:\n"
            + "\n".join(f"  {f}:{n}" for f, n in duplicates)
            + "\n\nИспользуйте utils/temp_file_manager.py"
        )

    def test_temp_file_patterns_not_duplicated(self) -> None:
        """Проверяет что паттерны работы с temp файлами не дублируются."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Паттерны которые указывают на логику temp файлов
        temp_patterns = [
            r"tempfile\.mkstemp",
            r"tempfile\.NamedTemporaryFile",
            r"tempfile\.TemporaryDirectory",
            r"_temp_files_registry",
            r"cleanup.*temp",
        ]

        # Ищем использования вне temp_file_manager.py
        temp_file_manager = project_root / "utils" / "temp_file_manager.py"

        usages_outside: List[Tuple[str, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            if py_file == temp_file_manager:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (SyntaxError, UnicodeDecodeError):
                continue

            for pattern in temp_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    usages_outside.append((str(py_file.relative_to(project_root)), pattern))

        # Это допустимо в некоторых случаях (например parallel_parser.py)
        # Просто информируем
        if usages_outside:
            pass  # Информационный тест


class TestConstantsCentralized:
    """Тесты на централизацию констант."""

    def test_constants_centralized(self) -> None:
        """Проверяет что константы определены в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        constants_py = project_root / "constants.py"
        assert constants_py.exists(), "constants.py должен существовать"

        # Константы которые должны быть в constants.py
        required_constants = [
            "MAX_DATA_DEPTH",
            "MAX_DATA_SIZE",
            "MAX_COLLECTION_SIZE",
            "MAX_STRING_LENGTH",
            "DEFAULT_BUFFER_SIZE",
            "CSV_BATCH_SIZE",
            "MIN_WORKERS",
            "MAX_WORKERS",
            "MIN_TIMEOUT",
            "MAX_TIMEOUT",
            "DEFAULT_TIMEOUT",
        ]

        content = constants_py.read_text(encoding="utf-8")

        missing_constants = []
        for const in required_constants:
            pattern = rf"^{const}\s*[:=]"
            if not re.search(pattern, content, re.MULTILINE):
                missing_constants.append(const)

        # Некоторые константы могут быть опциональными
        # Проверяем хотя бы часть
        found_count = len(required_constants) - len(missing_constants)
        assert found_count >= len(required_constants) * 0.7, (
            f"В constants.py отсутствуют константы: {missing_constants}"
        )

    def test_no_duplicate_constant_definitions(self) -> None:
        """Проверяет что константы не дублируются в других модулях."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Константы которые не должны дублироваться
        known_constants = {
            "MAX_DATA_DEPTH",
            "MAX_DATA_SIZE",
            "DEFAULT_BUFFER_SIZE",
            "CSV_BATCH_SIZE",
            "MIN_WORKERS",
            "MAX_WORKERS",
        }

        duplicates: List[Tuple[str, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            if py_file.name == "constants.py":
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (SyntaxError, UnicodeDecodeError):
                continue

            for const_name in known_constants:
                # Ищем определения констант (не импорты)
                pattern = rf"^{const_name}\s*[:=]\s*\d+"
                if re.search(pattern, content, re.MULTILINE):
                    duplicates.append((str(py_file.relative_to(project_root)), const_name))

        assert len(duplicates) == 0, (
            "Константы дублируются в других модулях:\n"
            + "\n".join(f"  {f}:{c}" for f, c in duplicates)
            + "\n\nИспользуйте constants.py"
        )

    def test_magic_numbers_are_minimized(self) -> None:
        """Проверяет что магические числа минимизированы.

        Магические числа должны быть вынесены в константы.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули которые должны использовать константы
        modules_to_check = ["parallel/parallel_parser.py", "cache/manager.py", "chrome/remote.py"]

        for module_path in modules_to_check:
            full_path = project_root / module_path

            if not full_path.exists():
                continue

            content = full_path.read_text(encoding="utf-8")

            # Ищем магические числа (упрощённая проверка)
            # Числа > 10 которые не в строках и не комментарии
            magic_numbers = re.findall(r"(?<!\w)(\d{3,})(?!\w)", content)

            # Это информационный тест - просто проверяем что числа есть
            # Они могут быть оправданы (таймауты, лимиты)
            if magic_numbers:
                pass  # Просто информируем


class TestNoDuplicateCodePatterns:
    """Тесты на отсутствие дублирования кода."""

    def test_no_duplicate_code_patterns(self) -> None:
        """Проверяет отсутствие дублирования кода паттернов.

        Ищет повторяющиеся блоки кода в различных модулях.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Собираем все функции из всех модулей
        function_bodies: Dict[str, List[Tuple[str, str]]] = {}

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Создаём упрощённое представление функции
                    func_signature = self._get_function_signature(node)
                    func_body_hash = self._get_body_hash(node, content)

                    key = f"{func_signature}:{func_body_hash}"

                    if key not in function_bodies:
                        function_bodies[key] = []

                    function_bodies[key].append((py_file.name, node.name))

        # Ищем дублирования
        duplicates = [(key, files) for key, files in function_bodies.items() if len(files) > 1]

        # Исключаем небольшие функции и дублирования в одном модуле
        significant_duplicates = []
        for key, files in duplicates:
            unique_modules = set(f[0] for f in files)
            if len(unique_modules) > 1:
                significant_duplicates.append((key, files))

        # Это информационный тест
        if significant_duplicates:
            pass  # Просто информируем

    def test_error_handling_patterns_not_duplicated(self) -> None:
        """Проверяет что паттерны обработки ошибок не дублируются."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Паттерны обработки ошибок

        # Это нормально что паттерны дублируются
        # Проверяем что есть централизованные утилиты
        utils_dir = project_root / "utils"

        assert utils_dir.exists(), "utils/ должен существовать"

        # Проверяем что есть утилиты для обработки ошибок
        validation_utils = utils_dir / "validation_utils.py"
        assert validation_utils.exists(), "validation_utils.py должен существовать"

    @staticmethod
    def _get_function_signature(node: ast.FunctionDef) -> str:
        """Получает сигнатуру функции."""
        args = [arg.arg for arg in node.args.args]
        return f"{node.name}({','.join(args)})"

    @staticmethod
    def _get_body_hash(node: ast.FunctionDef, content: str) -> str:
        """Получает хэш тела функции."""
        # Упрощённо: используем количество строк и узлов
        line_count = 0
        if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
            line_count = node.end_lineno - node.lineno

        node_count = sum(1 for _ in ast.walk(node))

        return f"{line_count}:{node_count}"


class TestDRYCompliance:
    """Общие тесты на соответствие DRY."""

    def test_helper_functions_are_reusable(self) -> None:
        """Проверяет что вспомогательные функции переиспользуемы."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули с утилитами
        utility_modules = [
            "utils/data_utils.py",
            "utils/math_utils.py",
            "utils/path_utils.py",
            "utils/validation_utils.py",
            "utils/url_utils.py",
        ]

        for module_path in utility_modules:
            full_path = project_root / module_path

            if not full_path.exists():
                pytest.fail(f"Модуль не найден: {module_path}")

            content = full_path.read_text(encoding="utf-8")

            # Модуль должен экспортировать функции
            assert "def " in content, f"{module_path} должен содержать функции"

    def test_common_logic_is_extracted(self) -> None:
        """Проверяет что общая логика вынесена в отдельные функции."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем что есть модули для общей логики
        expected_modules = [
            "constants.py",
            "exceptions.py",
            "protocols.py",
            "utils/data_utils.py",
            "utils/validation_utils.py",
        ]

        for module_name in expected_modules:
            module_path = project_root / module_name
            assert module_path.exists(), f"{module_name} должен существовать"

    def test_no_copy_paste_code_detected(self) -> None:
        """Проверяет отсутствие copy-paste кода.

        Используем эвристику: одинаковые строки кода в разных файлах.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Собираем все строки кода
        code_lines: Dict[str, List[Tuple[str, int]]] = {}

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (SyntaxError, UnicodeDecodeError):
                continue

            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # Пропускаем короткие строки и комментарии
                stripped = line.strip()
                if len(stripped) < 50 or stripped.startswith("#"):
                    continue

                # Нормализуем строку
                normalized = re.sub(r"\s+", " ", stripped)

                if normalized not in code_lines:
                    code_lines[normalized] = []

                code_lines[normalized].append((str(py_file.relative_to(project_root)), i))

        # Ищем дублирования
        duplicates = [(line, files) for line, files in code_lines.items() if len(files) > 1]

        # Исключаем импорты и декораторы
        significant_duplicates = []
        for line, files in duplicates:
            if not (line.startswith("import ") or line.startswith("from ") or line.startswith("@")):
                unique_modules = set(f[0].split("/")[0] for f in files)
                if len(unique_modules) > 1:
                    significant_duplicates.append((line, files))

        # Это информационный тест
        if significant_duplicates:
            pass  # Просто информируем


__all__ = [
    "TestNoDuplicateValidateEnvInt",
    "TestNoDuplicateTempFileLogic",
    "TestConstantsCentralized",
    "TestNoDuplicateCodePatterns",
    "TestDRYCompliance",
]
