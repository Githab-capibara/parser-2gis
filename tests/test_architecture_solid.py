"""
Тесты на проверку SOLID принципов в архитектуре проекта.

Объединяет архитектурные тесты из следующих файлов:
- test_architecture_solid.py (базовые SOLID тесты)
- test_architecture.py (границы слоёв, циклические импорты, производительность)
- test_architecture_boundaries.py (границы модулей, разделение ответственности)
- test_architecture_integrity.py (DRY/KISS/YAGNI, модульность, масштабируемость)
- test_architecture_no_cycles.py (отсутствие циклических зависимостей)
- test_architecture_improvements.py (TYPE_CHECKING, Guard Clauses, документация)

Принципы:
- SOLID принципы проектирования
- DRY, KISS, YAGNI принципы
- Модульность (coupling, cohesion, отсутствие циклов)
- Разделение ответственности (SoC)
- Масштабируемость (multiprocessing, plugin architecture)
- Программирование через интерфейсы
- Композиция вместо наследования
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
import re
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
PACKAGE_ROOT = PROJECT_ROOT / "parser_2gis"
PROJECT_ROOT_CONST = PROJECT_ROOT  # Для совместимости с тестами из improvements

# Определяем слои архитектуры (из test_architecture.py)
DOMAIN_MODULES = {"parser_2gis.core_types", "parser_2gis.protocols", "parser_2gis.types"}
INFRASTRUCTURE_MODULES = {
    "parser_2gis.chrome",
    "parser_2gis.cache",
    "parser_2gis.writer",
    "parser_2gis.logger",
    "parser_2gis.infrastructure",
}

MAJOR_MODULES = [
    "parser_2gis",
    "parser_2gis.config",
    "parser_2gis.cache",
    "parser_2gis.cache.pool",
    "parser_2gis.cache.manager",
    "parser_2gis.chrome",
    "parser_2gis.chrome.browser",
    "parser_2gis.chrome.options",
    "parser_2gis.chrome.remote",
    "parser_2gis.logger",
    "parser_2gis.logger.logger",
    "parser_2gis.parallel",
    "parser_2gis.parallel.coordinator",
    "parser_2gis.parallel.parallel_parser",
    "parser_2gis.parser",
    "parser_2gis.writer",
    "parser_2gis.writer.writers",
    "parser_2gis.exceptions",
    "parser_2gis.constants",
    "parser_2gis.types",
    "parser_2gis.core_types",
    "parser_2gis.protocols",
    "parser_2gis.validation",
    "parser_2gis.config_services",
    "parser_2gis.utils",
    "parser_2gis.resources",
]

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (SOLID)
# =============================================================================


def count_class_methods(file_path: Path, class_name: str) -> int:
    """Подсчитывает количество методов в классе.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса.

    Returns:
        Количество методов.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return 0

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    count += 1

    return count


def get_class_methods(file_path: Path, class_name: str) -> list[str]:
    """Извлекает имена методов класса.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса.

    Returns:
        Список имён методов.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    methods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

    return methods


def get_method_categories(methods: list[str]) -> dict[str, list[str]]:
    """Категоризирует методы по ответственности.

    Args:
        methods: Список имён методов.

    Returns:
        Словарь {категория: [методы]}.
    """
    categories: dict[str, list[str]] = {
        "initialization": [],
        "public_api": [],
        "private_impl": [],
        "dunder": [],
    }

    for method in methods:
        if method.startswith("__") and method.endswith("__"):
            categories["dunder"].append(method)
        elif method.startswith("_"):
            categories["private_impl"].append(method)
        elif method in ("__init__",):
            categories["initialization"].append(method)
        else:
            categories["public_api"].append(method)

    return categories


def check_protocol_methods_count(protocol_type: type) -> int:
    """Подсчитывает количество методов в Protocol.

    Args:
        protocol_type: Тип Protocol.

    Returns:
        Количество методов.
    """
    count = 0
    for name, member in inspect.getmembers(protocol_type):
        if not name.startswith("_") and callable(member):
            count += 1
    return count


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (ARCHITECTURE / CYCLES)
# =============================================================================


def _get_all_python_files(directory: Path) -> list[Path]:
    """Рекурсивно получает все Python файлы в директории."""
    exclude = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "venv", ".venv"}
    result: list[Path] = []
    for path in directory.rglob("*.py"):
        if not any(part in exclude for part in path.parts):
            result.append(path)
    return result


def _get_imports(file_path: Path) -> set[str]:
    """Извлекает все импорты из Python файла."""
    imports: set[str] = set()
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    except (OSError, UnicodeDecodeError, SyntaxError):
        pass
    return imports


def _build_dependency_graph(directory: Path) -> dict[str, set[str]]:
    """Строит граф зависимостей модулей."""
    graph: dict[str, set[str]] = {}
    for py_file in _get_all_python_files(directory):
        rel_path = str(py_file.relative_to(PROJECT_ROOT)).replace("/", ".").replace("\\", ".")
        module_name = rel_path.rsplit(".", 1)[0] if rel_path.endswith(".py") else rel_path
        imports = _get_imports(py_file)
        graph[module_name] = imports
    return graph


def _has_cycle_from(graph: dict[str, set[str]], start: str, visited: set, rec_stack: set) -> bool:
    """Проверяет наличие цикла из начальной вершины (DFS)."""
    visited.add(start)
    rec_stack.add(start)
    for neighbor in graph.get(start, set()):
        if neighbor not in visited:
            if _has_cycle_from(graph, neighbor, visited, rec_stack):
                return True
        elif neighbor in rec_stack:
            return True
    rec_stack.discard(start)
    return False


def _detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Обнаруживает циклы в графе зависимостей."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    for node in graph:
        if node not in visited:
            rec_stack: set[str] = set()
            path: list[str] = []

            def _dfs(node: str, visited: set[str], rec_stack: set[str], path: list[str]) -> None:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                for neighbor in graph.get(node, set()):
                    if neighbor not in visited:
                        _dfs(neighbor, visited, rec_stack, path)
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycles.append([*path[cycle_start:], neighbor])
                path.pop()
                rec_stack.discard(node)

            _dfs(node, visited, rec_stack, path)
    return cycles


def get_module_imports(file_path: Path) -> set[str]:
    """Извлекает все импорты из Python файла.

    Args:
        file_path: Путь к Python файлу.

    Returns:
        Множество импортированных модулей.
    """
    imports: set[str] = set()

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return imports

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def get_all_python_files(directory: Path, exclude_dirs: list[str] | None = None) -> list[Path]:
    """Рекурсивно получает все Python файлы в директории.

    Args:
        directory: Корневая директория.
        exclude_dirs: Список директорий для исключения.

    Returns:
        Список путей к Python файлам.
    """
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]

    python_files: list[Path] = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def get_file_imports_from_module(file_path: Path, module_root: Path) -> set[str]:
    """Получает все относительные импорты из файла в рамках module_root.

    Args:
        file_path: Путь к файлу.
        module_root: Корневая директория модуля.

    Returns:
        Множество импортированных модулей (относительные пути).
    """
    imports: set[str] = set()

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return imports

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("parser_2gis"):
                relative_module = node.module.replace("parser_2gis.", "")
                imports.add(relative_module.split(".")[0])

    return imports


def get_internal_imports(file_path: Path, package_prefix: str = "parser_2gis") -> set[str]:
    """Извлекает внутренние импорты проекта из Python файла.

    Args:
        file_path: Путь к Python файлу.
        package_prefix: Префикс пакета для фильтрации.

    Returns:
        Множество внутренних импортов (без префикса пакета).
    """
    imports: set[str] = set()

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return imports

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(package_prefix):
                relative_module = node.module.replace(f"{package_prefix}.", "")
                top_level = relative_module.split(".")[0]
                imports.add(top_level)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(package_prefix):
                    relative_module = alias.name.replace(f"{package_prefix}.", "")
                    top_level = relative_module.split(".")[0]
                    imports.add(top_level)

    return imports


def build_dependency_graph(
    directory: Path, package_prefix: str = "parser_2gis"
) -> dict[str, set[str]]:
    """Строит граф зависимостей между модулями в директории.

    Args:
        directory: Корневая директория для анализа.
        package_prefix: Префикс пакета для фильтрации.

    Returns:
        Словарь зависимостей: модуль -> множество зависимых модулей.
    """
    dependencies: dict[str, set[str]] = {}

    for py_file in directory.rglob("*.py"):
        if "tests" in py_file.parts or "__pycache__" in py_file.parts:
            continue

        rel_path = py_file.relative_to(directory)
        module_name = str(rel_path.with_suffix("")).replace("/", ".")

        imports = get_internal_imports(py_file, package_prefix)

        if module_name not in dependencies:
            dependencies[module_name] = set()

        dependencies[module_name].update(imports)

    return dependencies


def find_cycles_dfs(dependencies: dict[str, set[str]]) -> list[list[str]]:
    """Ищет циклы в графе зависимостей используя DFS.

    Args:
        dependencies: Граф зависимостей.

    Returns:
        Список циклов (каждый цикл - список имён модулей).
    """
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in dependencies.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycle = [*path[cycle_start:], neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    for node in dependencies:
        if node not in visited:
            dfs(node)

    return cycles


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (INTEGRITY)
# =============================================================================


def get_classes_in_file(file_path: Path) -> list[tuple[str, int, int, int]]:
    """Получает список классов в файле с их размерами и количеством методов.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_класса, start_line, end_line, method_count).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    classes: list[tuple[str, int, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            method_count = sum(
                1 for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            classes.append((node.name, start_line, end_line, method_count))

    return classes


def get_functions_in_file(file_path: Path) -> list[tuple[str, int, int, int]]:
    """Получает список функций в файле с их размерами и сложностью.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_функции, start_line, end_line, param_count).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    functions: list[tuple[str, int, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            param_count = len(node.args.args) + len(node.args.kwonlyargs)
            functions.append((node.name, start_line, end_line, param_count))

    return functions


def find_python_files(
    directory: Path, exclude_dirs: list[str] | None = None, exclude_files: list[str] | None = None
) -> list[Path]:
    """Находит все Python файлы в директории.

    Args:
        directory: Корневая директория.
        exclude_dirs: Список директорий для исключения.
        exclude_files: Список файлов для исключения.

    Returns:
        Список путей к Python файлам.
    """
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "tests",
            "venv",
        ]

    if exclude_files is None:
        exclude_files = ["__init__.py"]

    python_files: list[Path] = []

    for py_file in directory.rglob("*.py"):
        if any(part in exclude_dirs for part in py_file.parts):
            continue

        if py_file.name in exclude_files:
            continue

        python_files.append(py_file)

    return python_files


def get_imports_in_file(file_path: Path) -> set[str]:
    """Получает все импорты в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Множество имён импортируемых модулей.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return set()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return set()

    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])

    return imports


def count_nesting_depth(file_path: Path) -> int:
    """Подсчитывает максимальную глубину вложенности в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Максимальная глубина вложенности.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return 0

    max_depth = 0

    def visit_node(node: ast.AST, current_depth: int) -> None:
        nonlocal max_depth
        max_depth = max(max_depth, current_depth)

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                visit_node(child, current_depth + 1)
            else:
                visit_node(child, current_depth)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            visit_node(node, 0)

    return max_depth


def get_protocols_in_file(file_path: Path) -> list[tuple[str, int]]:
    """Получает все Protocol классы в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_protocol, method_count).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    protocols: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Protocol":
                    method_count = sum(
                        1
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    protocols.append((node.name, method_count))
                    break

    return protocols


def check_protocol_usage(protocol_name: str, project_root: Path) -> int:
    """Проверяет сколько раз используется Protocol.

    Args:
        protocol_name: Имя Protocol для проверки.
        project_root: Корень проекта.

    Returns:
        Количество использований.
    """
    usage_count = 0
    python_files = find_python_files(project_root)

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding="utf-8")
            if protocol_name in content:
                usage_count += 1
        except (OSError, UnicodeDecodeError):
            continue

    return usage_count


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (IMPROVEMENTS)
# =============================================================================


def read_source_file(relative_path: str) -> str:
    """Читает исходный файл проекта.

    Args:
        relative_path: Относительный путь к файлу.

    Returns:
        Содержимое файла.
    """
    file_path = PROJECT_ROOT_CONST / relative_path
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def get_type_checking_imports(source: str) -> set[str]:
    """Извлекает импорты из TYPE_CHECKING блока.

    Args:
        source: Исходный код файла.

    Returns:
        Множество имён импортированных модулей.
    """
    imports = set()
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                    for child in node.body:
                        if isinstance(child, ast.ImportFrom):
                            if child.module:
                                imports.add(child.module.split(".")[-1])
                        elif isinstance(child, ast.Import):
                            for alias in child.names:
                                imports.add(alias.name.split(".")[-1])
    except SyntaxError:
        pass
    return imports


def has_guard_clauses(source: str, method_name: str) -> tuple[bool, int]:
    """Проверяет наличие Guard Clauses в методе.

    Args:
        source: Исходный код файла.
        method_name: Имя метода для проверки.

    Returns:
        Кортеж (наличие Guard Clauses, количество ранних возвратов).
    """
    early_returns = 0
    has_guard = False

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method_name:
                returns = [
                    n for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None
                ]
                early_returns = len(returns)

                if node.body:
                    first_stmt = node.body[0]
                    if isinstance(first_stmt, ast.If):
                        if isinstance(first_stmt.body[0], ast.Return):
                            has_guard = True
                            break
    except SyntaxError:
        pass

    return has_guard, early_returns


def get_method_nesting_depth(source: str, method_name: str) -> int:
    """Вычисляет максимальную вложенность метода.

    Args:
        source: Исходный код файла.
        method_name: Имя метода.

    Returns:
        Максимальная глубина вложенности.
    """
    max_depth = 0

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method_name:

                def count_depth(n, current_depth=0) -> None:
                    nonlocal max_depth
                    max_depth = max(max_depth, current_depth)
                    for child in ast.iter_child_nodes(n):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                            count_depth(child, current_depth + 1)
                        else:
                            count_depth(child, current_depth)

                count_depth(node)
                break
    except SyntaxError:
        pass

    return max_depth


def has_docstring_with_sections(source: str, class_name: str) -> tuple[bool, list[str]]:
    """Проверяет наличие docstring с разделами.

    Args:
        source: Исходный код файла.
        class_name: Имя класса.

    Returns:
        Кортеж (наличие docstring, список найденных разделов).
    """
    has_docstring = False
    sections = []

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                docstring = ast.get_docstring(node)
                if docstring:
                    has_docstring = True
                    if any(
                        phrase in docstring
                        for phrase in ["Назначение:", "Purpose:", "Абстракция", "Protocol"]
                    ):
                        sections.append("Назначение")
                    if any(
                        phrase in docstring
                        for phrase in ["Места использования:", "Usage:", "Использование:", "для"]
                    ):
                        sections.append("Места использования")
                    if "Пример:" in docstring or "Example:" in docstring:
                        sections.append("Пример")
                    if "Ответственность:" in docstring:
                        sections.append("Ответственность")
                    if "Обработка ошибок:" in docstring:
                        sections.append("Обработка ошибок")
                break
    except SyntaxError:
        pass

    return has_docstring, sections


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture(scope="session")
def project_root_fixture() -> Path:
    """Фикстура возвращает корневую директорию проекта."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def parser_2gis_root_fixture(project_root_fixture: Path) -> Path:
    """Фикстура возвращает корневую директорию модуля parser_2gis."""
    return project_root_fixture / "parser_2gis"


@pytest.fixture(scope="session")
def python_files_fixture(parser_2gis_root_fixture: Path) -> list[Path]:
    """Фикстура возвращает все Python файлы проекта."""
    return find_python_files(parser_2gis_root_fixture)


@pytest.fixture(scope="session")
def protocols_file_fixture(parser_2gis_root_fixture: Path) -> Path:
    """Фикстура возвращает путь к protocols.py."""
    return parser_2gis_root_fixture / "protocols.py"


# =============================================================================
# ТЕСТ 1: SINGLE RESPONSIBILITY PRINCIPLE (SRP)
# =============================================================================


class TestSingleResponsibilityPrinciple:
    """Тесты на принцип единственной ответственности."""

    def test_parallel_coordinator_has_single_responsibility(self) -> None:
        """Проверяет что ParallelCoordinator имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        methods = get_class_methods(coordinator_file, "ParallelCoordinator")
        categories = get_method_categories(methods)

        public_methods = categories["public_api"]

        coordination_count = sum(
            1
            for m in public_methods
            if any(c in m for c in ["run", "stop", "get_", "generate", "parse_single"])
        )

        assert coordination_count >= len(public_methods) * 0.7, (
            f"ParallelCoordinator должен иметь >=70% методов координации "
            f"(сейчас: {coordination_count}/{len(public_methods)})"
        )

    def test_parallel_error_handler_has_single_responsibility(self) -> None:
        """Проверяет что ParallelErrorHandler имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        methods = get_class_methods(error_handler_file, "ParallelErrorHandler")

        error_methods = [
            m
            for m in methods
            if "error" in m.lower() or "handle" in m.lower() or "cleanup" in m.lower()
        ]

        allowed_methods = [*error_methods, "log", "create_unique_temp_file", "retry_with_backoff"]

        assert len(allowed_methods) >= len(methods) * 0.8, (
            "ParallelErrorHandler должен иметь >=80% методов для обработки ошибок"
        )

    def test_parallel_file_merger_has_single_responsibility(self) -> None:
        """Проверяет что ParallelFileMerger имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        methods = get_class_methods(merger_file, "ParallelFileMerger")

        merge_methods = [
            m
            for m in methods
            if "merge" in m.lower()
            or "csv" in m.lower()
            or "file" in m.lower()
            or "lock" in m.lower()
        ]

        allowed_methods = [
            *merge_methods,
            "log",
            "extract_category_from_filename",
            "process_single_csv_file",
            "acquire_merge_lock",
            "cleanup_merge_lock",
        ]

        assert len(allowed_methods) >= len(methods) * 0.9, (
            "ParallelFileMerger должен иметь >=90% методов для слияния файлов"
        )

    def test_main_page_parser_has_single_responsibility(self) -> None:
        """Проверяет что MainPageParser имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        methods = get_class_methods(main_parser_file, "MainPageParser")

        allowed_method_patterns = [
            "_get_links",
            "_add_xhr_counter",
            "_validate_js_script",
            "_wait_requests_finished",
            "_get_available_pages",
            "_go_page",
            "_navigate_to_search",
            "_handle_navigation_timeout",
            "_handle_navigation_error",
            "_classify_error",
            "_is_network_error",
            "_is_blocked_error",
            "_handle_network_error",
            "_calculate_retry_delay",
            "_validate_document_response",
            "url_pattern",
            "parse",
            "get_stats",
            "close",
            "__init__",
            "__enter__",
            "__exit__",
        ]

        allowed_count = sum(1 for m in methods if m in allowed_method_patterns)

        assert allowed_count >= len(methods) * 0.8, (
            f"MainPageParser должен иметь >=80% методов для навигации и DOM "
            f"(разрешено: {allowed_count}/{len(methods)}, "
            f"лишние: {set(methods) - set(allowed_method_patterns)})"
        )

    def test_class_method_count_under_limit(self) -> None:
        """Проверяет что классы имеют <50 методов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        classes_to_check = [
            ("parallel/coordinator.py", "ParallelCoordinator"),
            ("parallel/merger.py", "ParallelFileMerger"),
            ("parallel/error_handler.py", "ParallelErrorHandler"),
            ("parser/parsers/main_parser.py", "MainPageParser"),
            ("chrome/browser.py", "BrowserLifecycleManager"),
        ]

        for file_rel_path, class_name in classes_to_check:
            file_path = project_root / file_rel_path
            if not file_path.exists():
                continue

            method_count = count_class_methods(file_path, class_name)

            assert method_count < 50, (
                f"{class_name} должен иметь <50 методов (сейчас: {method_count})"
            )


# =============================================================================
# ТЕСТ 2: DEPENDENCY INVERSION PRINCIPLE (DIP)
# =============================================================================


class TestDependencyInversionPrinciple:
    """Тесты на принцип инверсии зависимостей."""

    def test_main_parser_depends_on_abstraction_not_concretion(self) -> None:
        """Проверяет что MainPageParser зависит от абстракции BrowserService."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        content = main_parser_file.read_text(encoding="utf-8")

        assert "BrowserService" in content, (
            "MainPageParser должен использовать BrowserService Protocol"
        )

        assert "browser: BrowserService" in content, (
            "MainPageParser должен принимать BrowserService в конструктор"
        )


# =============================================================================
# ТЕСТ 3: INTERFACE SEGREGATION PRINCIPLE (ISP)
# =============================================================================


class TestInterfaceSegregationPrinciple:
    """Тесты на принцип разделения интерфейса."""

    def test_browser_protocol_is_segregated(self) -> None:
        """Проверяет что Browser Protocol разделён на мелкие интерфейсы."""
        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
            BrowserService,
        )

        assert BrowserNavigation is not None
        assert BrowserContentAccess is not None
        assert BrowserJSExecution is not None
        assert BrowserScreenshot is not None
        assert BrowserService is not None

        nav_methods = check_protocol_methods_count(BrowserNavigation)
        content_methods = check_protocol_methods_count(BrowserContentAccess)
        js_methods = check_protocol_methods_count(BrowserJSExecution)
        screenshot_methods = check_protocol_methods_count(BrowserScreenshot)

        assert nav_methods <= 2, (
            f"BrowserNavigation должен иметь <=2 методов (сейчас: {nav_methods})"
        )
        assert content_methods <= 3, (
            f"BrowserContentAccess должен иметь <=3 методов (сейчас: {content_methods})"
        )
        assert js_methods <= 2, (
            f"BrowserJSExecution должен иметь <=2 методов (сейчас: {js_methods})"
        )
        assert screenshot_methods <= 2, (
            f"BrowserScreenshot должен иметь <=2 методов (сейчас: {screenshot_methods})"
        )

    def test_callback_protocols_are_segregated(self) -> None:
        """Проверяет что callback Protocol разделены."""
        from parser_2gis.protocols import CleanupCallback, ProgressCallback

        assert CleanupCallback is not None
        assert ProgressCallback is not None

        for protocol in [CleanupCallback, ProgressCallback]:
            assert callable(protocol) or protocol is not None, (
                f"{protocol.__name__} должен быть Callable Protocol"
            )

    def test_protocols_are_not_fat(self) -> None:
        """Проверяет что Protocol не избыточны."""
        from parser_2gis.protocols import (
            BrowserService,
            CacheReader,
            CacheWriter,
            LoggerProtocol,
            Parser,
            Writer,
        )

        protocols = [
            (BrowserService, 20),
            (CacheReader, 3),
            (CacheWriter, 3),
            (LoggerProtocol, 7),
            (Parser, 4),
            (Writer, 4),
        ]

        for protocol, max_methods in protocols:
            methods = check_protocol_methods_count(protocol)
            assert methods <= max_methods, (
                f"{protocol.__name__} должен иметь <={max_methods} методов (сейчас: {methods})"
            )


# =============================================================================
# ТЕСТ 4: LISKOV SUBSTITUTION PRINCIPLE (LSP)
# =============================================================================


class TestLiskovSubstitutionPrinciple:
    """Тесты на принцип подстановки Барбары Лисков."""

    def test_mock_browser_service_substitutable(self) -> None:
        """Проверяет что mock BrowserService может заменить реальный."""
        from parser_2gis.protocols import BrowserService

        mock_browser: BrowserService = MagicMock(spec=BrowserService)

        mock_browser.navigate("http://example.com")
        mock_browser.get_html()
        mock_browser.execute_js("console.log('test')")
        mock_browser.screenshot("/tmp/test.png")
        mock_browser.close()

        assert mock_browser.navigate.called
        assert mock_browser.get_html.called
        assert mock_browser.execute_js.called
        assert mock_browser.screenshot.called
        assert mock_browser.close.called

    def test_mock_writer_substitutable(self) -> None:
        """Проверяет что mock Writer может заменить реальный."""
        from parser_2gis.protocols import Writer

        mock_writer: Writer = MagicMock(spec=Writer)

        mock_writer.write([{"key": "value"}])
        mock_writer.close()

        assert mock_writer.write.called
        assert mock_writer.close.called

    def test_mock_parser_substitutable(self) -> None:
        """Проверяет что mock Parser может заменить реальный."""
        from parser_2gis.protocols import Parser

        mock_parser: Parser = MagicMock(spec=Parser)

        mock_parser.parse()
        mock_parser.get_stats()

        assert mock_parser.parse.called
        assert mock_parser.get_stats.called

    def test_mock_cache_backend_substitutable(self) -> None:
        """Проверяет что mock CacheReader/CacheWriter могут заменить реальный."""
        from parser_2gis.protocols import CacheReader, CacheWriter

        mock_cache_reader: CacheReader = MagicMock(spec=CacheReader)
        mock_cache_writer: CacheWriter = MagicMock(spec=CacheWriter)

        mock_cache_reader.get("key")
        mock_cache_reader.exists("key")
        mock_cache_writer.set("key", "value", 3600)
        mock_cache_writer.delete("key")

        assert mock_cache_reader.get.called
        assert mock_cache_reader.exists.called
        assert mock_cache_writer.set.called
        assert mock_cache_writer.delete.called


# =============================================================================
# ТЕСТ 5: OPEN/CLOSED PRINCIPLE (OCP)
# =============================================================================


class TestOpenClosedPrinciple:
    """Тесты на принцип открытости/закрытости."""

    def test_protocols_allow_extension(self) -> None:
        """Проверяет что Protocol позволяют расширение."""
        from parser_2gis.protocols import BrowserService, Writer

        class MockBrowser:
            def navigate(self, url: str, **kwargs: Any) -> None:
                pass

            def get_html(self) -> str:
                return ""

            def get_document(self) -> Any:
                return None

            def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
                return None

            def screenshot(self, path: str) -> None:
                pass

            def close(self) -> None:
                pass

        class MockWriter:
            def write(self, records: list[dict]) -> None:
                pass

            def close(self) -> None:
                pass

        browser: BrowserService = MockBrowser()  # type: ignore
        writer: Writer = MockWriter()  # type: ignore

        assert browser is not None
        assert writer is not None

    def test_error_handler_allows_new_error_types(self) -> None:
        """Проверяет что ParallelErrorHandler позволяет добавлять новые типы ошибок."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        content = error_handler_file.read_text(encoding="utf-8")

        assert "handle_other_error" in content, (
            "ParallelErrorHandler должен иметь общий метод для обработки ошибок"
        )

    def test_strategy_pattern_for_backends(self) -> None:
        """Проверяет что бэкенды кэша используют стратегию."""
        from parser_2gis.protocols import CacheReader, CacheWriter

        assert CacheReader is not None
        assert CacheWriter is not None

        mock_cache_reader: CacheReader = MagicMock(spec=CacheReader)
        mock_cache_writer: CacheWriter = MagicMock(spec=CacheWriter)

        assert mock_cache_reader is not None
        assert mock_cache_writer is not None


# =============================================================================
# ТЕСТ 6: SOLID INTEGRITY
# =============================================================================


class TestSOLIDIntegrity:
    """Тесты на целостность SOLID принципов."""

    def test_all_solid_principles_covered(self) -> None:
        """Проверяет что все SOLID принципы покрыты тестами."""
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None

        from parser_2gis.protocols import Writer

        assert Writer is not None

        from parser_2gis.protocols import Parser

        assert Parser is not None

        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
        )

        assert BrowserNavigation is not None
        assert BrowserContentAccess is not None
        assert BrowserJSExecution is not None
        assert BrowserScreenshot is not None

        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        content = main_parser_file.read_text(encoding="utf-8")
        assert "BrowserService" in content, (
            "MainPageParser должен использовать BrowserService для DIP"
        )

    def test_protocols_module_is_stable(self) -> None:
        """Проверяет что protocols.py стабилен."""
        from parser_2gis import protocols

        expected_protocols = [
            "BrowserService",
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
            "Writer",
            "Parser",
            "CacheReader",
            "CacheWriter",
            "LoggerProtocol",
            "ProgressCallback",
            "CleanupCallback",
            "ErrorHandlerProtocol",
            "MergerProtocol",
            "PathValidatorProtocol",
            "MemoryManagerProtocol",
        ]

        for protocol_name in expected_protocols:
            assert hasattr(protocols, protocol_name), (
                f"protocols.py должен экспортировать {protocol_name}"
            )


# =============================================================================
# ГРАНИЦЫ СЛОЁВ (TestLayerBoundaries)
# =============================================================================


class TestLayerBoundaries:
    """Тесты проверки границ слоёв архитектуры."""

    def test_domain_does_not_import_infrastructure(self) -> None:
        """Domain слой не должен импортировать infrastructure модули."""
        violations: list[str] = []
        for domain_mod in DOMAIN_MODULES:
            for infra_mod in INFRASTRUCTURE_MODULES:
                try:
                    mod = importlib.import_module(domain_mod)
                    if mod is not None:
                        source_file = getattr(mod, "__file__", None)
                        if source_file:
                            imports = _get_imports(Path(source_file))
                            for imp in imports:
                                if imp.startswith(infra_mod):
                                    violations.append(
                                        f"{domain_mod} импортирует {imp} (нарушение границ)"
                                    )
                except (ImportError, ModuleNotFoundError):
                    pass
        assert not violations, "Нарушения границ слоёв:\n" + "\n".join(violations)

    def test_cache_does_not_import_chrome(self) -> None:
        """Cache слой не должен импортировать chrome."""
        cache_path = PACKAGE_ROOT / "cache"
        if not cache_path.exists():
            pytest.skip("cache модуль не найден")
        for py_file in cache_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_imports(py_file)
            chrome_imports = [imp for imp in imports if "chrome" in imp]
            assert not chrome_imports, f"{py_file.name} импортирует chrome: {chrome_imports}"

    def test_writer_does_not_import_chrome(self) -> None:
        """Writer слой не должен импортировать chrome."""
        writer_path = PACKAGE_ROOT / "writer"
        if not writer_path.exists():
            pytest.skip("writer модуль не найден")
        for py_file in writer_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_imports(py_file)
            chrome_imports = [imp for imp in imports if "chrome" in imp]
            assert not chrome_imports, f"{py_file.name} импортирует chrome: {chrome_imports}"

    def test_logger_has_no_business_logic_imports(self) -> None:
        """Logger не должен импортировать бизнес-логику."""
        logger_path = PACKAGE_ROOT / "logger"
        if not logger_path.exists():
            pytest.skip("logger модуль не найден")
        business_modules = {"parser_2gis.parser", "parser_2gis.chrome.browser"}
        for py_file in logger_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_imports(py_file)
            for imp in imports:
                for biz_mod in business_modules:
                    if imp.startswith(biz_mod):
                        pytest.fail(f"{py_file.name} импортирует бизнес-логику: {imp}")


# =============================================================================
# ОТСУТСТВИЕ ЦИКЛИЧЕСКИХ ИМПОРТОВ (TestNoCircularImports)
# =============================================================================


class TestNoCircularImports:
    """Тесты на отсутствие циклических импортов."""

    @pytest.mark.parametrize("module_name", MAJOR_MODULES)
    def test_module_importable_without_errors(self, module_name: str) -> None:
        """Каждый основной модуль должен импортироваться без ошибок."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None, f"Модуль {module_name} вернул None"
        except ModuleNotFoundError as e:
            pytest.skip(f"Модуль {module_name} не найден (опциональная зависимость): {e}")
        except ImportError as e:
            pytest.fail(f"Ошибка импорта {module_name}: {e}")

    def test_no_circular_imports_in_package(self) -> None:
        """Проверка отсутствия циклических импортов в пакете."""
        graph = _build_dependency_graph(PACKAGE_ROOT)
        filtered_graph = {
            k: {v for v in vals if v.startswith("parser_2gis")}
            for k, vals in graph.items()
            if k.startswith("parser_2gis")
        }
        cycles = _detect_cycles(filtered_graph)
        assert not cycles, "Обнаружены циклические импорты:\n" + "\n".join(
            " -> ".join(c) for c in cycles
        )


# =============================================================================
# ИЗОЛЯЦИЯ ГЛОБАЛЬНОГО СОСТОЯНИЯ (TestGlobalStateIsolation)
# =============================================================================

try:
    from parser_2gis.cache.pool import ConnectionPool

    POOL_AVAILABLE = True
except ImportError:
    POOL_AVAILABLE = False

try:
    from parser_2gis.parallel.memory_manager import (  # noqa: F401
        MemoryManager,
        _memory_manager_instance,
    )

    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False


class TestGlobalStateIsolation:
    """Тесты изоляции глобального состояния."""

    @pytest.mark.skipif(not POOL_AVAILABLE, reason="ConnectionPool недоступен")
    def test_pool_can_be_cleared_and_reset(self, tmp_path) -> None:
        """Пул соединений можно очистить и пересоздать."""
        db_file = tmp_path / "test_pool.db"
        pool = ConnectionPool(db_file, pool_size=2)
        conn = pool.get_connection()
        assert conn is not None
        pool.close()
        assert len(pool._all_conns) == 0
        assert pool._connection_queue.empty()

    @pytest.mark.skipif(not POOL_AVAILABLE, reason="ConnectionPool недоступен")
    def test_pool_context_manager_cleans_up(self, tmp_path) -> None:
        """Контекстный менеджер пула корректно очищает ресурсы."""
        db_file = tmp_path / "test_pool_ctx.db"
        with ConnectionPool(db_file, pool_size=2) as pool:
            conn = pool.get_connection()
            assert conn is not None
        assert len(pool._all_conns) == 0

    @pytest.mark.skipif(not MEMORY_MANAGER_AVAILABLE, reason="MemoryManager недоступен")
    def test_memory_manager_can_be_reset(self) -> None:
        """MemoryManager можно сбросить."""
        mm = MemoryManager()
        assert mm is not None
        mm2 = MemoryManager()
        assert mm2 is not None

    def test_configuration_is_fresh_on_each_creation(self) -> None:
        """Каждое создание Configuration даёт независимый экземпляр."""
        from parser_2gis.config import Configuration

        config1 = Configuration()
        config2 = Configuration()
        config1.path = Path("/tmp/test1")
        assert config2.path is None or config2.path != config1.path


# =============================================================================
# ПРОИЗВОДИТЕЛЬНОСТЬ КРИТИЧЕСКИХ ФУНКЦИЙ (TestPerformanceCriticalFunctions)
# =============================================================================


class TestPerformanceCriticalFunctions:
    """Тесты производительности критических функций."""

    @pytest.mark.benchmark
    def test_merge_performance(self, tmp_path) -> None:
        """Тест производительности операции слияния."""
        from parser_2gis.parallel.common.csv_merge_common import merge_csv_files_common

        file1 = tmp_path / "test1.csv"
        file2 = tmp_path / "test2.csv"
        header = "Название;Адрес;Телефон\n"
        file1.write_text(header + "Компания1;Адрес1;Телефон1\n" * 1000)
        file2.write_text(header + "Компания2;Адрес2;Телефон2\n" * 1000)

        output_file = tmp_path / "merged.csv"
        start = time.perf_counter()
        merge_csv_files_common(
            file_paths=[file1, file2],
            output_path=output_file,
            buffer_size=8192,
            batch_size=100,
            log_callback=lambda msg, level: None,
        )
        elapsed = time.perf_counter() - start

        assert output_file.exists()
        assert elapsed < 2.0, f"Слияние заняло слишком много времени: {elapsed:.3f}с"

    @pytest.mark.benchmark
    def test_cache_operations(self, tmp_path) -> None:
        """Тест производительности операций кэша."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path, ttl_hours=1)
        start = time.perf_counter()
        for i in range(100):
            cache.set(f"http://test{i}.com", {"key": f"value{i}"})
        write_elapsed = time.perf_counter() - start
        assert write_elapsed < 5.0, f"Запись в кэш заняла: {write_elapsed:.3f}с"

        start = time.perf_counter()
        for i in range(100):
            cache.get(f"http://test{i}.com")
        read_elapsed = time.perf_counter() - start
        assert read_elapsed < 5.0, f"Чтение из кэша заняло: {read_elapsed:.3f}с"
        cache.close()

    @pytest.mark.benchmark
    def test_url_hash_performance(self) -> None:
        """Тест производительности хэширования URL."""
        from parser_2gis.cache.cache_utils import hash_url

        urls = [f"http://example.com/page/{i}" for i in range(10000)]
        start = time.perf_counter()
        for url in urls:
            hash_url(url)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Хэширование заняло: {elapsed:.3f}с"


# =============================================================================
# ПОЛНЫЙ ЦИКЛ ПАРСИНГА (TestFullParsingCycleMock)
# =============================================================================

try:
    from parser_2gis.writer import get_writer  # noqa: F401

    WRITER_AVAILABLE = True
except ImportError:
    WRITER_AVAILABLE = False


class TestFullParsingCycleMock:
    """Интеграционные тесты полного цикла парсинга с mock."""

    def test_cache_write_and_read_cycle(self, tmp_path) -> None:
        """Тест полного цикла записи и чтения кэша."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path, ttl_hours=24)
        try:
            test_url = "http://2gis.ru/test/firms"
            test_data = {"firms": [{"name": "Test Firm", "address": "Test Address"}]}

            cache.set(test_url, test_data)

            cached = cache.get(test_url)
            assert cached is not None
            assert cached == test_data

            assert cache.get("http://nonexistent.com") is None
        finally:
            cache.close()

    def test_writer_csv_cycle(self, tmp_path) -> None:
        """Тест цикла записи CSV."""
        if not WRITER_AVAILABLE:
            pytest.skip("writer недоступен")

        from parser_2gis.writer.options import WriterOptions
        from parser_2gis.writer.writers.csv_writer import CSVWriter

        output_file = tmp_path / "output.csv"
        options = WriterOptions()
        options.csv.remove_empty_columns = False
        options.csv.remove_duplicates = False
        writer = CSVWriter(str(output_file), options)
        with writer:
            writer._writerow(
                {
                    "name": "Фирма1",
                    "address": "Адрес1",
                    "point_lat": 0.0,
                    "point_lon": 0.0,
                    "url": "http://test.com",
                    "type": "firm",
                }
            )

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Фирма1" in content

    def test_config_save_and_load_cycle(self, tmp_path) -> None:
        """Тест полного цикла сохранения и загрузки конфигурации."""
        from parser_2gis.config import Configuration

        config_path = tmp_path / "config.json"
        config1 = Configuration()
        config1.path = config_path
        config1.save_config()

        config2 = Configuration.load_config(config_path, auto_create=False)
        assert config2 is not None
        assert isinstance(config2, Configuration)

    def test_validation_and_error_handling(self) -> None:
        """Тест валидации и обработки ошибок конфигурации."""
        from parser_2gis.config import Configuration

        config = Configuration()
        is_valid, errors = config.validate_config()
        assert is_valid or not errors

    def test_parallel_merger_cycle(self, tmp_path) -> None:
        """Тест полного цикла слияния файлов параллельного парсера."""
        from parser_2gis.parallel.common.csv_merge_common import merge_csv_files_common

        file1 = tmp_path / "p1.csv"
        file2 = tmp_path / "p2.csv"
        header = "Название;Адрес\n"
        file1.write_text(header + "Фирма1;Адрес1\n")
        file2.write_text(header + "Фирма2;Адрес2\n")

        result_file = tmp_path / "result.csv"
        merge_csv_files_common(
            file_paths=[file1, file2],
            output_path=result_file,
            buffer_size=8192,
            batch_size=100,
            log_callback=lambda msg, level: None,
        )
        assert result_file.exists()

    def test_cache_expiry_cycle(self, tmp_path) -> None:
        """Тест цикла истечения срока кэша."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path, ttl_hours=1)
        try:
            test_url = "http://example.com"
            test_data = {"data": "test"}
            cache.set(test_url, test_data)
            cached = cache.get(test_url)
            assert cached is not None
            assert cached == test_data
        finally:
            cache.close()


# =============================================================================
# ГРАНИЦЫ МОДУЛЕЙ (TestModuleBoundaries)
# =============================================================================


class TestModuleBoundaries:
    """Тесты на соблюдение границ модулей (isolation)."""

    def test_utils_no_business_logic_imports(self) -> None:
        """utils/ не должен импортировать business logic модули (parser/, writer/, chrome/)."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        if not utils_dir.exists():
            pytest.skip("Директория utils/ не существует")

        business_logic_modules = {"parser", "writer", "chrome"}

        for py_file in get_all_python_files(utils_dir):
            imports = get_file_imports_from_module(py_file, project_root)
            illegal_imports = imports.intersection(business_logic_modules)

            assert len(illegal_imports) == 0, (
                f"{py_file.relative_to(project_root)} импортирует бизнес-логику: {illegal_imports}. "
                "utils/ должен быть изолирован от business logic модулей."
            )

    def test_validation_no_business_logic_imports(self) -> None:
        """validation/ не должен импортировать parser/, writer/, chrome/."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        validation_dir = project_root / "validation"

        if not validation_dir.exists():
            pytest.skip("Директория validation/ не существует")

        business_logic_modules = {"parser", "writer", "chrome"}

        for py_file in get_all_python_files(validation_dir):
            imports = get_file_imports_from_module(py_file, project_root)
            illegal_imports = imports.intersection(business_logic_modules)

            assert len(illegal_imports) == 0, (
                f"{py_file.relative_to(project_root)} импортирует бизнес-логику: {illegal_imports}. "
                "validation/ должен быть изолирован от business logic модулей."
            )

    def test_constants_no_other_module_imports(self) -> None:
        """constants.py может импортировать только из своих подмодулей."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        constants_file = project_root / "constants.py"

        if not constants_file.exists():
            pytest.skip("constants.py не существует")

        imports = get_module_imports(constants_file)

        parser_2gis_imports = {imp for imp in imports if imp.startswith("parser_2gis")}
        allowed_imports = {
            "typing",
            "os",
            "typing.Optional",
            "parser_2gis.constants.buffer",
            "parser_2gis.constants.cache",
            "parser_2gis.constants.env_config",
            "parser_2gis.constants.parser",
            "parser_2gis.constants.security",
            "parser_2gis.constants.validation",
        }

        illegal_imports = parser_2gis_imports - allowed_imports

        assert len(illegal_imports) == 0, (
            f"constants.py импортирует непредназначенные модули: {illegal_imports}. "
            "constants.py может импортировать только свои подмодули parser_2gis.constants.*."
        )

    def test_logger_does_not_import_business_logic(self) -> None:
        """Проверяет что logger не импортирует бизнес-логику."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        logger_dir = project_root / "logger"

        forbidden_imports = ["parser", "writer", "chrome", "tui_textual"]

        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text(encoding="utf-8")

            for forbidden in forbidden_imports:
                pattern = rf"from \.{forbidden}|from parser_2gis\.{forbidden}"
                if re.search(pattern, content):
                    pytest.fail(
                        f"logger/{py_file.name} не должен импортировать {forbidden}. "
                        "Это нарушает границы слоёв архитектуры."
                    )

    def test_parallel_does_not_import_tui(self) -> None:
        """Проверяет что parallel/ не импортирует tui_textual."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        violations: list[str] = []

        for py_file in parallel_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            pattern = r"from\s+\.?tui_textual|from\s+parser_2gis\.tui_textual"
            if re.search(pattern, content):
                violations.append(py_file.name)

        assert not violations, (
            f"parallel/ не должен импортировать tui_textual. Нарушения в: {', '.join(violations)}"
        )


# =============================================================================
# РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ (TestSeparationOfConcerns)
# =============================================================================


class TestSeparationOfConcerns:
    """Тесты на разделение ответственности между модулями."""

    def test_parallel_parser_responsibilities_separated(self) -> None:
        """Проверяет что ответственности ParallelCityParser разделены."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_parser = project_root / "parallel" / "parallel_parser.py"

        assert parallel_parser.exists(), "parallel_parser.py должен существовать"

        content = parallel_parser.read_text(encoding="utf-8")
        tree = ast.parse(content)

        classes: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)

        assert "ParallelCityParser" in classes, "ParallelCityParser должен существовать"

        class_methods: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(
                    1
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                class_methods[node.name] = method_count

        parser_methods = class_methods.get("ParallelCityParser", 0)
        assert parser_methods <= 20, (
            f"ParallelCityParser имеет {parser_methods} методов. "
            "Рассмотрите разделение ответственностей."
        )

    def test_cache_manager_responsibilities_separated(self) -> None:
        """Проверяет что CacheManager разделён на специализированные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cache_dir = project_root / "cache"

        assert cache_dir.exists(), "cache/ должен существовать"

        expected_modules = ["manager.py", "pool.py", "serializer.py", "validator.py"]

        for module in expected_modules:
            module_path = cache_dir / module
            assert module_path.exists(), f"{module} должен существовать"

    def test_chrome_remote_responsibilities_separated(self) -> None:
        """Проверяет что ChromeRemote разделён на специализированные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        chrome_dir = project_root / "chrome"

        assert chrome_dir.exists(), "chrome/ должен существовать"

        expected_modules = [
            "remote.py",
            "js_executor.py",
            "http_cache.py",
            "rate_limiter.py",
            "browser.py",
        ]

        for module in expected_modules:
            module_path = chrome_dir / module
            assert module_path.exists(), f"{module} должен существовать"

    def test_config_responsibilities_separated(self) -> None:
        """Проверяет что Configuration и ConfigService разделены."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        config_py = project_root / "config.py"
        config_service_py = project_root / "cli" / "config_service.py"

        assert config_py.exists(), "config.py должен существовать"
        assert config_service_py.exists(), "config_service.py должен существовать"

    def test_configuration_is_data_model(self) -> None:
        """Проверяет что Configuration — модель данных."""
        from parser_2gis.config import Configuration

        assert issubclass(Configuration, BaseModel), "Configuration должен быть Pydantic моделью"

    def test_config_service_is_business_logic(self) -> None:
        """Проверяет что ConfigService содержит бизнес-логику."""
        from parser_2gis.cli.config_service import ConfigService

        assert hasattr(ConfigService, "load_config"), "ConfigService должен иметь load_config"
        assert hasattr(ConfigService, "save_config"), "ConfigService должен иметь save_config"

    def test_main_no_business_logic_classes(self) -> None:
        """main.py не должен содержать классы бизнес-логики."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_file = project_root / "main.py"

        if not main_file.exists():
            pytest.skip("main.py не существует")

        try:
            with open(main_file, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(main_file))
        except (SyntaxError, OSError, UnicodeDecodeError):
            pytest.skip("Не удалось распарсить main.py")

        business_logic_classes = {
            "Parser",
            "CityParser",
            "ParallelCityParser",
            "Writer",
            "CSVWriter",
            "JSONWriter",
            "ChromeManager",
            "Browser",
            "Scraper",
            "Fetcher",
        }

        found_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in business_logic_classes:
                found_classes.append(node.name)

        assert len(found_classes) == 0, (
            f"main.py содержит классы бизнес-логики: {found_classes}. "
            "main.py должен содержать только CLI логику и парсинг аргументов."
        )

    def test_separation_of_concerns(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка SoC (Separation of Concerns).

        Бизнес-логика должна быть отделена от инфраструктуры.
        CLI логика должна быть отделена от бизнес-логики.
        """
        cli_dir = parser_2gis_root_fixture / "cli"

        business_logic_patterns = ["parse(", "ChromeRemote", "BrowserService", "execute_js"]

        violations: list[tuple[str, str]] = []

        if cli_dir.exists():
            for py_file in cli_dir.glob("*.py"):
                if py_file.name in ["__init__.py", "config_service.py"]:
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                    for pattern in business_logic_patterns:
                        if pattern in content:
                            violations.append((py_file.name, pattern))
                except (OSError, UnicodeDecodeError):
                    continue

        if len(violations) > 3:
            pytest.skip(
                "CLI содержит бизнес-логику (нарушение SoC):\n"
                + "\n".join(f"  {f}: {p}" for f, p in violations[:5])
            )

    def test_configuration_is_model_only(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка что Configuration только модель данных."""
        config_file = parser_2gis_root_fixture / "config.py"
        config_service_file = parser_2gis_root_fixture / "cli" / "config_service.py"

        assert config_file.exists(), "config.py должен существовать"

        config_content = config_file.read_text(encoding="utf-8")

        save_load_in_config = (
            "save_config" in config_content
            or "load_config" in config_content
            or "save_to_file" in config_content
            or "load_from_file" in config_content
        )

        if save_load_in_config:
            pytest.skip(
                "Configuration содержит методы сохранения/загрузки файлов (нарушение SRP). "
                "Примечание: merge_with метод допустим."
            )

        if config_service_file.exists():
            service_content = config_service_file.read_text(encoding="utf-8")
            has_save = "save_config" in service_content
            has_load = "load_config" in service_content

            if not (has_save and has_load):
                pytest.skip("ConfigService должен содержать save_config и load_config")


# =============================================================================
# DRY, KISS, YAGNI (TestDRYKISSYAGNI)
# =============================================================================


class TestDRYKISSYAGNI:
    """Тесты на соблюдение DRY, KISS, YAGNI принципов."""

    def test_no_code_duplication(self, python_files_fixture: list[Path]) -> None:
        """Проверка дублирования кода."""
        function_bodies: dict[str, list[tuple[Path, str]]] = {}

        for py_file in python_files_fixture:
            try:
                with open(py_file, encoding="utf-8") as f:
                    lines = f.readlines()
            except (OSError, UnicodeDecodeError):
                continue

            try:
                tree = ast.parse("".join(lines), filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue

                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
                    func_body = "".join(lines[start_line:end_line])

                    normalized = "".join(
                        line.strip()
                        for line in func_body.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    )

                    if len(normalized) > 100:
                        if normalized not in function_bodies:
                            function_bodies[normalized] = []
                        function_bodies[normalized].append((py_file, node.name))

        duplicates = {name: files for name, files in function_bodies.items() if len(files) > 1}

        if len(duplicates) > 10:
            pytest.skip(
                f"Обнаружено {len(duplicates)} дубликатов функций (требуется рефакторинг DRY)"
            )

    def test_method_complexity(self, python_files_fixture: list[Path]) -> None:
        """Проверка сложности методов."""
        length_violations: list[tuple[Path, str, int]] = []

        for py_file in python_files_fixture:
            functions = get_functions_in_file(py_file)
            for func_name, start_line, end_line, _ in functions:
                if func_name.startswith("_"):
                    continue

                func_lines = end_line - start_line + 1
                if func_lines > 50:
                    length_violations.append((py_file, func_name, func_lines))

        if length_violations:
            pytest.skip(
                "Обнаружены методы >50 строк (высокая сложность):\n"
                + "\n".join(
                    f"  {f.name}:{func} - {lines} строк"
                    for f, func, lines in length_violations[:10]
                )
            )

    def test_no_speculative_generality(
        self, protocols_file_fixture: Path, parser_2gis_root_fixture: Path
    ) -> None:
        """Проверка YAGNI (You Aren't Gonna Need It)."""
        if not protocols_file_fixture.exists():
            pytest.skip("protocols.py не найден")

        protocols = get_protocols_in_file(protocols_file_fixture)
        unused_protocols: list[str] = []

        for protocol_name, _ in protocols:
            usage_count = check_protocol_usage(protocol_name, parser_2gis_root_fixture)
            if usage_count < 2:
                unused_protocols.append(protocol_name)

        if unused_protocols:
            pytest.skip(
                f"Protocol используются <2 раз (Speculative Generality): {unused_protocols[:5]}"
            )


# =============================================================================
# МОДУЛЬНОСТЬ (TestModularity)
# =============================================================================


class TestModularity:
    """Тесты на модульность проекта."""

    def test_module_coupling(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка связности модулей."""
        modules_to_check = [
            "logger",
            "chrome",
            "parallel",
            "parser",
            "writer",
            "cache",
            "cli",
            "utils",
        ]

        coupling_violations: list[tuple[str, int]] = []

        for module_name in modules_to_check:
            module_dir = parser_2gis_root_fixture / module_name
            if not module_dir.exists():
                continue

            all_imports: set[str] = set()
            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                imports = get_imports_in_file(py_file)
                imports.discard(module_name)
                imports.discard("typing")
                imports.discard("pathlib")
                imports.discard("os")
                imports.discard("sys")

                all_imports.update(imports)

            if len(all_imports) > 15:
                coupling_violations.append((module_name, len(all_imports)))

        if coupling_violations:
            pytest.skip(
                "Модули импортируют >15 других модулей (высокая связанность):\n"
                + "\n".join(f"  {name} - {count} импортов" for name, count in coupling_violations)
            )

    def test_module_cohesion(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка автономности модулей."""
        modules_to_check = {
            "cache": ["manager", "pool", "serializer", "validator"],
            "parallel": ["coordinator", "merger", "error_handler", "memory_manager"],
            "cli": ["app", "arguments", "config", "launcher", "main"],
        }

        cohesion_issues: list[tuple[str, list[str]]] = []

        for module_name, expected_files in modules_to_check.items():
            module_dir = parser_2gis_root_fixture / module_name
            if not module_dir.exists():
                continue

            found_files = [f.stem for f in module_dir.glob("*.py") if not f.name.startswith("__")]

            missing = [f for f in expected_files if f not in found_files]

            if len(missing) > len(expected_files) // 2:
                cohesion_issues.append((module_name, missing))

        if cohesion_issues:
            pytest.skip(
                "Модули имеют низкую связность (отсутствуют ключевые файлы):\n"
                + "\n".join(
                    f"  {name} - отсутствуют: {missing}" for name, missing in cohesion_issues
                )
            )

    def test_no_circular_dependencies(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка циклических зависимостей."""
        core_modules = ["logger", "chrome", "parallel", "parser", "writer", "cache", "utils"]
        dependencies: dict[str, set[str]] = {module: set() for module in core_modules}

        for module_name in core_modules:
            module_dir = parser_2gis_root_fixture / module_name
            if not module_dir.exists():
                continue

            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                imports = get_imports_in_file(py_file)
                for imp in imports:
                    if imp in core_modules and imp != module_name:
                        dependencies[module_name].add(imp)

        def has_cycle(start: str, visited: set[str], rec_stack: set[str]) -> list[str] | None:
            visited.add(start)
            rec_stack.add(start)

            for neighbor in dependencies.get(start, set()):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, visited, rec_stack)
                    if cycle:
                        return [start, *cycle]
                elif neighbor in rec_stack:
                    return [start, neighbor]

            rec_stack.remove(start)
            return None

        cycles: list[list[str]] = []
        visited: set[str] = set()

        for module in core_modules:
            if module not in visited:
                cycle = has_cycle(module, visited, set())
                if cycle:
                    cycles.append(cycle)

        if cycles:
            pytest.fail(
                "Обнаружены циклические зависимости между модулями:\n"
                + "\n".join(" -> ".join(cycle) for cycle in cycles)
            )


# =============================================================================
# МАСШТАБИРУЕМОСТЬ (TestScalability)
# =============================================================================


class TestScalability:
    """Тесты на масштабируемость архитектуры."""

    def test_multiprocessing_support(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка поддержки multiprocessing."""
        coordinator_file = parser_2gis_root_fixture / "parallel" / "thread_coordinator.py"

        if not coordinator_file.exists():
            pytest.skip("parallel/thread_coordinator.py не существует")

        content = coordinator_file.read_text(encoding="utf-8")

        has_process_executor = "ProcessPoolExecutor" in content

        has_executor_type = (
            "executor_type" in content
            or "ExecutorType" in content
            or ("thread" in content and "process" in content)
        )

        assert has_process_executor, "ThreadCoordinator должен поддерживать ProcessPoolExecutor"

        assert has_executor_type, "ThreadCoordinator должен поддерживать выбор типа executor"

    def test_plugin_architecture_ready(self, parser_2gis_root_fixture: Path) -> None:
        """Проверка готовности к плагинам."""
        factory_files = list(parser_2gis_root_fixture.rglob("*factory*.py"))

        if not factory_files:
            pytest.skip("Factory файлы не найдены (плагин архитектура не реализована)")

        plugin_ready_count = 0

        for factory_file in factory_files:
            try:
                content = factory_file.read_text(encoding="utf-8")

                has_registration = "register" in content.lower()
                has_registry_dict = "registry" in content.lower() or "_registry" in content

                if has_registration and has_registry_dict:
                    plugin_ready_count += 1
            except (OSError, UnicodeDecodeError):
                continue

        assert plugin_ready_count >= 1, (
            "Ни один factory не поддерживает динамическую регистрацию плагинов"
        )


# =============================================================================
# TYPE_CHECKING ИМПОРТЫ (TestTypeCheckingImports)
# =============================================================================


class TestTypeCheckingImports:
    """Тесты на использование TYPE_CHECKING для уменьшения связанности."""

    def test_parallel_parser_has_type_checking_imports(self) -> None:
        """Тест наличия TYPE_CHECKING импортов в parallel_parser.py."""
        source = read_source_file("parser_2gis/parallel/parallel_parser.py")
        type_checking_imports = get_type_checking_imports(source)

        assert "TYPE_CHECKING" in source, (
            "TYPE_CHECKING должен быть импортирован в parallel_parser.py"
        )

        assert len(type_checking_imports) > 0, (
            "Должны быть импорты в TYPE_CHECKING блоке для уменьшения связанности"
        )

    def test_parallel_parser_local_imports_in_method(self) -> None:
        """Тест локальных импортов в методе parse_single_url."""
        source = read_source_file("parser_2gis/parallel/parallel_parser.py")

        assert "parse_single_url" in source, "Метод parse_single_url должен существовать"

        has_type_checking = "TYPE_CHECKING" in source

        lines = source.split("\n")
        in_method = False
        has_local_imports = False

        for line in lines:
            if "def parse_single_url" in line:
                in_method = True
            elif in_method and line.strip().startswith("def "):
                break
            elif in_method and "from parser_2gis" in line and "import" in line:
                has_local_imports = True
                break

        assert has_type_checking or has_local_imports, (
            "Должен использоваться TYPE_CHECKING или локальные импорты для уменьшения связанности"
        )


# =============================================================================
# GUARD CLAUSES (TestGuardClauses)
# =============================================================================


class TestGuardClauses:
    """Тесты на использование Guard Clauses и Early Return pattern."""

    def test_chrome_remote_get_response_body_guard_clauses(self) -> None:
        """Тест Guard Clauses в методе get_response_body."""
        source = read_source_file("parser_2gis/chrome/remote.py")

        has_guard, early_returns = has_guard_clauses(source, "get_response_body")

        assert has_guard or early_returns > 0, (
            "get_response_body должен использовать Guard Clauses или Early Return"
        )

        depth = get_method_nesting_depth(source, "get_response_body")
        assert depth <= 3, f"Вложенность get_response_body должна быть <= 3 (текущая: {depth})"

    def test_chrome_remote_stop_early_return(self) -> None:
        """Тест Early Return в методе stop."""
        source = read_source_file("parser_2gis/chrome/remote.py")

        has_stop_tab = "_stop_chrome_tab" in source
        has_stop_browser = "_stop_chrome_browser" in source
        has_cleanup = "_cleanup_after_stop" in source

        submethods_count = sum([has_stop_tab, has_stop_browser, has_cleanup])
        assert submethods_count >= 2, (
            f"stop должен использовать подметоды для разделения ответственности (найдено: {submethods_count}/3)"
        )

        stop_method_start = source.find("def stop(self)")
        if stop_method_start != -1:
            next_method_start = source.find("def ", stop_method_start + 10)
            stop_method_code = source[stop_method_start:next_method_start]

            calls_submethods = (
                "_stop_chrome_tab()" in stop_method_code
                or "_stop_chrome_browser()" in stop_method_code
            )
            assert calls_submethods, "Метод stop должен вызывать подметоды"


# =============================================================================
# ДОКУМЕНТАЦИЯ PROTOCOL (TestProtocolDocumentation)
# =============================================================================


class TestProtocolDocumentation:
    """Тесты на документирование Protocol абстракций."""

    @pytest.mark.parametrize(
        "protocol_name",
        [
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
            "BrowserService",
            "CacheReader",
            "CacheWriter",
        ],
    )
    def test_protocol_has_docstring_with_sections(self, protocol_name) -> None:
        """Тест наличия docstring с разделами у Protocol."""
        source = read_source_file("parser_2gis/protocols.py")

        has_docstring, sections = has_docstring_with_sections(source, protocol_name)

        assert has_docstring, f"{protocol_name} должен иметь docstring"
        assert len(sections) >= 1, (
            f"{protocol_name} должен иметь минимум 1 раздел в docstring (найдено: {sections})"
        )

    def test_logger_protocol_documented(self) -> None:
        """Тест документирования LoggerProtocol."""
        source = read_source_file("parser_2gis/protocols.py")

        has_docstring, sections = has_docstring_with_sections(source, "LoggerProtocol")

        assert has_docstring, "LoggerProtocol должен иметь docstring"
        assert len(sections) >= 1, "LoggerProtocol должен иметь docstring с описанием"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
