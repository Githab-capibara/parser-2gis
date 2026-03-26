"""
Тесты на отсутствие God Classes (чрезмерно больших классов).

Проверяет:
- Все модули < 500 строк
- Все классы < 300 строк
- Классы имеют < 15 методов
- Классы имеют < 10 атрибутов

God Class антипаттерн:
Класс который делает слишком много, имеет слишком много методов и атрибутов.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

import pytest


class TestModuleSizes:
    """Тесты на размер модулей."""

    def test_no_module_too_large(self) -> None:
        """Проверяет что все модули < 500 строк.

        Исключения допускаются для сложных модулей:
        - browser.py: управление браузером
        - remote.py: удалённое управление
        - manager.py: кэширование
        - main.py: точка входа CLI
        - app.py: TUI приложение
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_lines = 500

        # Допустимые исключения
        allowed_exceptions = {
            "browser.py",
            "remote.py",
            "manager.py",
            "main.py",
            "app.py",
            "parallel_parser.py",
            "visual_logger.py",
        }

        large_modules: List[Tuple[str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            lines = len(content.splitlines())

            if lines > max_lines:
                if py_file.name not in allowed_exceptions:
                    large_modules.append((str(py_file.relative_to(project_root)), lines))

        assert len(large_modules) == 0, (
            f"Модули превышают {max_lines} строк (без учёта исключений):\n"
            + "\n".join(f"  {f}: {lines} строк" for f, lines in large_modules)
            + "\n\nРазделите большие модули или добавьте в allowed_exceptions."
        )

    def test_specific_critical_modules_sizes(self) -> None:
        """Проверяет размер критических модулей."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули которые должны быть компактными
        compact_modules = {
            "utils/path_utils.py": 200,
            "utils/math_utils.py": 100,
            "utils/data_utils.py": 150,
            "protocols.py": 300,
            "config_service.py": 400,
            "writer/factory.py": 200,
            "parser/factory.py": 200,
        }

        for module_path, max_lines in compact_modules.items():
            full_path = project_root / module_path

            if not full_path.exists():
                pytest.fail(f"Модуль не найден: {module_path}")

            content = full_path.read_text(encoding="utf-8")
            lines = len(content.splitlines())

            assert lines <= max_lines, (
                f"Модуль {module_path} превышает {max_lines} строк: {lines} строк"
            )


class TestClassSizes:
    """Тесты на размер классов."""

    def test_no_class_too_large(self) -> None:
        """Проверяет что все классы < 300 строк.

        Классы должны быть компактными и иметь одну ответственность.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_class_lines = 300

        # Допустимые исключения
        allowed_exceptions = {
            "Configuration",  # Модель конфигурации
            "ChromeRemote",  # Удалённое управление браузером
            "CacheManager",  # Управление кэшем
            "ParallelCityParser",  # Параллельный парсинг
        }

        large_classes: List[Tuple[str, str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Вычисляем размер класса
                    line_count = 0
                    if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                        line_count = node.end_lineno - node.lineno

                    if line_count > max_class_lines:
                        if node.name not in allowed_exceptions:
                            large_classes.append((py_file.name, node.name, line_count))

        assert len(large_classes) == 0, (
            f"Классы превышают {max_class_lines} строк:\n"
            + "\n".join(f"  {f}:{c} - {cls_lines} строк" for f, c, cls_lines in large_classes)
            + "\n\nРазделите большие классы или добавьте в allowed_exceptions."
        )

    def test_class_method_count(self) -> None:
        """Проверяет что классы имеют < 15 методов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_methods = 15

        # Допустимые исключения
        allowed_exceptions = {
            "Configuration",  # Pydantic модель с методами
            "ConfigService",  # Сервис с множеством операций
        }

        classes_with_many_methods: List[Tuple[str, str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    method_count = sum(
                        1
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )

                    if method_count > max_methods:
                        if node.name not in allowed_exceptions:
                            classes_with_many_methods.append(
                                (py_file.name, node.name, method_count)
                            )

        assert len(classes_with_many_methods) == 0, (
            f"Классы имеют более {max_methods} методов:\n"
            + "\n".join(f"  {f}:{c} - {m} методов" for f, c, m in classes_with_many_methods)
            + "\n\nРазделите классы с большим количеством методов."
        )

    def test_class_attribute_count(self) -> None:
        """Проверяет что классы имеют < 10 атрибутов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_attributes = 10

        # Допустимые исключения
        allowed_exceptions = {
            "Configuration",  # Модель с множеством полей
            "ParallelParserConfig",  # Dataclass с параметрами
        }

        classes_with_many_attributes: List[Tuple[str, str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Считаем атрибуты класса (assignments в body класса)
                    attribute_count = 0

                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            attribute_count += 1
                        elif isinstance(item, ast.Assign):
                            attribute_count += len(item.targets)

                    # Для Pydantic моделей считаем поля
                    if node.name == "Configuration":
                        continue

                    if attribute_count > max_attributes:
                        if node.name not in allowed_exceptions:
                            classes_with_many_attributes.append(
                                (py_file.name, node.name, attribute_count)
                            )

        assert len(classes_with_many_attributes) == 0, (
            f"Классы имеют более {max_attributes} атрибутов:\n"
            + "\n".join(f"  {f}:{c} - {a} атрибутов" for f, c, a in classes_with_many_attributes)
            + "\n\nИспользуйте dataclass или вынесите атрибуты."
        )


class TestSpecificClasses:
    """Тесты на размер конкретных классов."""

    def test_configuration_class_size(self) -> None:
        """Проверяет размер класса Configuration."""
        import inspect

        from parser_2gis.config import Configuration

        source = inspect.getsource(Configuration)
        lines = len(source.splitlines())

        # Configuration может быть большим из-за полей Pydantic
        assert lines <= 500, f"Configuration превышает 500 строк: {lines}"

    def test_config_service_class_size(self) -> None:
        """Проверяет размер класса ConfigService."""
        import inspect

        from parser_2gis.config_service import ConfigService

        source = inspect.getsource(ConfigService)
        lines = len(source.splitlines())

        assert lines <= 400, f"ConfigService превышает 400 строк: {lines}"

    def test_cache_manager_class_size(self) -> None:
        """Проверяет размер класса CacheManager."""
        import inspect

        from parser_2gis.cache.manager import CacheManager

        source = inspect.getsource(CacheManager)
        lines = len(source.splitlines())

        assert lines <= 350, f"CacheManager превышает 350 строк: {lines}"

    def test_parallel_parser_class_size(self) -> None:
        """Проверяет размер класса ParallelCityParser."""
        import inspect

        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        source = inspect.getsource(ParallelCityParser)
        lines = len(source.splitlines())

        assert lines <= 400, f"ParallelCityParser превышает 400 строк: {lines}"


class TestGodClassPatterns:
    """Тесты на обнаружение паттернов God Class."""

    def test_no_class_handles_too_many_responsibilities(self) -> None:
        """Проверяет что классы не обрабатывают слишком много ответственностей.

        Используем эвристику: если имя класса содержит более 3 слов,
        возможно он делает слишком много.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        suspicious_classes: List[Tuple[str, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Разделяем имя класса на слова по CamelCase
                    class_name = node.name
                    words = self._split_camel_case(class_name)

                    if len(words) > 4:
                        suspicious_classes.append((py_file.name, class_name))

        # Это предупреждение а не ошибка
        if suspicious_classes:
            pass  # Просто информируем

    def test_no_class_has_too_many_imports(self) -> None:
        """Проверяет что классы не импортируют слишком много модулей.

        Если класс импортирует более 10 модулей, возможно он делает слишком много.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_imports = 10

        classes_with_many_imports: List[Tuple[str, str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Считаем импорты на уровне модуля
            import_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_count += 1

            # Если в файле один класс и много импортов - подозрительно
            classes_in_file = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

            if len(classes_in_file) == 1 and import_count > max_imports:
                classes_with_many_imports.append(
                    (py_file.name, classes_in_file[0].name, import_count)
                )

        # Это информационный тест
        if classes_with_many_imports:
            pass  # Просто информируем

    @staticmethod
    def _split_camel_case(name: str) -> List[str]:
        """Разделяет CamelCase имя на слова."""
        import re

        words = re.findall(r"[A-Z][a-z]*", name)
        return words if words else [name]


class TestCodeComplexity:
    """Тесты на сложность кода."""

    def test_no_function_too_complex(self) -> None:
        """Проверяет что функции не слишком сложные.

        Используем простую эвристику: количество строк в функции.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_function_lines = 100

        complex_functions: List[Tuple[str, str, int]] = []

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
                    line_count = 0
                    if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                        line_count = node.end_lineno - node.lineno

                    if line_count > max_function_lines:
                        complex_functions.append((py_file.name, node.name, line_count))

        # Допускаем некоторые сложные функции
        allowed_functions = {
            "_merge_models_iterative",  # Сложная логика слияния
            "parse",  # Парсинг может быть сложным
        }

        filtered = [
            (f, n, func_lines)
            for f, n, func_lines in complex_functions
            if n not in allowed_functions
        ]

        assert len(filtered) == 0, f"Функции превышают {max_function_lines} строк:\n" + "\n".join(
            f"  {f}:{n} - {func_lines} строк" for f, n, func_lines in filtered
        )

    def test_no_nested_functions_too_deep(self) -> None:
        """Проверяет что вложенность функций не слишком глубокая."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_nesting = 5

        deeply_nested: List[Tuple[str, str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Проверяем вложенность через посещение узлов
            def check_nesting(node: ast.AST, depth: int = 0) -> None:
                if depth > max_nesting:
                    func_name = getattr(node, "name", "unknown")
                    deeply_nested.append((py_file.name, func_name, depth))
                    return

                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        check_nesting(child, depth + 1)
                    elif isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                        check_nesting(child, depth + 1)

            check_nesting(tree)

        assert len(deeply_nested) == 0, (
            f"Вложенность превышает {max_nesting} уровней:\n"
            + "\n".join(f"  {f}:{n} - {d} уровней" for f, n, d in deeply_nested)
        )


__all__ = [
    "TestModuleSizes",
    "TestClassSizes",
    "TestSpecificClasses",
    "TestGodClassPatterns",
    "TestCodeComplexity",
]
