"""
Архитектурные тесты для проверки ограничений архитектуры проекта parser-2gis.

Тесты проверяют:
1. Отсутствие дублирования констант
2. Отсутствие множественного наследования
3. Границы модулей (isolation)
4. Отсутствие циклических зависимостей
5. Разделение concerns (separation of concerns)
"""

import ast
import os
from pathlib import Path
from typing import List, Set

import pytest


PROJECT_ROOT = Path(__file__).parent.parent
PARSER_2GIS_ROOT = PROJECT_ROOT / "parser_2gis"


def get_module_imports(file_path: Path) -> Set[str]:
    """Извлекает все импорты из Python файла.

    Args:
        file_path: Путь к Python файлу.

    Returns:
        Множество импортированных модулей.
    """
    imports: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
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
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def get_all_python_files(directory: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Рекурсивно получает все Python файлы в директории.

    Args:
        directory: Корневая директория.
        exclude_dirs: Список директорий для исключения.

    Returns:
        Список путей к Python файлам.
    """
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]

    python_files: List[Path] = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def find_constant_definition(constant_name: str, root_dir: Path) -> List[Path]:
    """Находит все файлы, где определяется константа.

    Args:
        constant_name: Имя константы для поиска.
        root_dir: Корневая директория поиска.

    Returns:
        Список файлов с определением константы.
    """
    import re

    definition_pattern = rf"^\s*{re.escape(constant_name)}\s*:\s*int\s*="
    files_with_definition: List[Path] = []

    for py_file in get_all_python_files(root_dir):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                for line in f:
                    if re.match(definition_pattern, line):
                        files_with_definition.append(py_file)
                        break
        except (OSError, UnicodeDecodeError):
            pass

    return files_with_definition


def find_class_base_classes(class_name: str, root_dir: Path) -> List[str]:
    """Находит базовые классы для указанного класса.

    Args:
        class_name: Имя класса для поиска.
        root_dir: Корневая директория поиска.

    Returns:
        Список базовых классов.
    """
    for py_file in get_all_python_files(root_dir):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
                tree = ast.parse(source, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_classes.append(base.attr)
                    return base_classes
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

    return []


def get_file_imports_from_module(file_path: Path, module_root: Path) -> Set[str]:
    """Получает все относительные импорты из файла в рамках module_root.

    Args:
        file_path: Путь к файлу.
        module_root: Корневая директория модуля.

    Returns:
        Множество импортированных модулей (относительные пути).
    """
    imports: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
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


# =============================================================================
# ТЕСТ 1: Отсутствие дублирования констант
# =============================================================================


class TestNoConstantDuplication:
    """Тесты на отсутствие дублирования констант в коде."""

    def test_max_lock_file_age_only_in_constants(self):
        """MAX_LOCK_FILE_AGE должна быть определена только в constants.py."""
        files = find_constant_definition("MAX_LOCK_FILE_AGE", PARSER_2GIS_ROOT)

        expected_file = PARSER_2GIS_ROOT / "constants.py"
        assert expected_file in files, f"MAX_LOCK_FILE_AGE должна быть определена в {expected_file}"

        other_files = [f for f in files if f != expected_file]
        assert len(other_files) == 0, (
            f"MAX_LOCK_FILE_AGE дублируется в: {[str(f) for f in other_files]}"
        )

    def test_max_path_length_only_in_constants(self):
        """MAX_PATH_LENGTH должна быть определена только в constants.py."""
        files = find_constant_definition("MAX_PATH_LENGTH", PARSER_2GIS_ROOT)

        expected_file = PARSER_2GIS_ROOT / "constants.py"
        assert expected_file in files, f"MAX_PATH_LENGTH должна быть определена в {expected_file}"

        other_files = [f for f in files if f != expected_file]
        assert len(other_files) == 0, (
            f"MAX_PATH_LENGTH дублируется в: {[str(f) for f in other_files]}"
        )

    def test_max_cities_file_size_only_in_constants(self):
        """MAX_CITIES_FILE_SIZE должна быть определена только в constants.py."""
        files = find_constant_definition("MAX_CITIES_FILE_SIZE", PARSER_2GIS_ROOT)

        expected_file = PARSER_2GIS_ROOT / "constants.py"
        assert expected_file in files, (
            f"MAX_CITIES_FILE_SIZE должна быть определена в {expected_file}"
        )

        other_files = [f for f in files if f != expected_file]
        assert len(other_files) == 0, (
            f"MAX_CITIES_FILE_SIZE дублируется в: {[str(f) for f in other_files]}"
        )


# =============================================================================
# ТЕСТ 2: Отсутствие множественного наследования
# =============================================================================


class TestNoMultipleInheritance:
    """Тесты на отсутствие множественного наследования."""

    def test_parallel_city_parser_thread_no_threading_inheritance(self):
        """ParallelCityParserThread не должен наследоваться от threading.Thread."""
        base_classes = find_class_base_classes("ParallelCityParserThread", PARSER_2GIS_ROOT)

        assert "Thread" not in base_classes, (
            f"ParallelCityParserThread наследуется от Thread: {base_classes}. "
            "Должна использоваться композиция вместо наследования."
        )

        assert len(base_classes) == 0 or all(
            b not in ("Thread", "threading.Thread") for b in base_classes
        ), f"ParallelCityParserThread имеет неправильные базовые классы: {base_classes}"


# =============================================================================
# ТЕСТ 3: Границы модулей
# =============================================================================


class TestModuleBoundaries:
    """Тесты на соблюдение границ модулей (isolation)."""

    def test_utils_no_business_logic_imports(self):
        """utils/ не должен импортировать business logic модули (parser/, writer/, chrome/)."""
        utils_dir = PARSER_2GIS_ROOT / "utils"

        if not utils_dir.exists():
            pytest.skip("Директория utils/ не существует")

        business_logic_modules = {"parser", "writer", "chrome"}

        for py_file in get_all_python_files(utils_dir):
            imports = get_file_imports_from_module(py_file, PARSER_2GIS_ROOT)
            illegal_imports = imports.intersection(business_logic_modules)

            assert len(illegal_imports) == 0, (
                f"{py_file.relative_to(PROJECT_ROOT)} импортирует бизнес-логику: {illegal_imports}. "
                "utils/ должен быть изолирован от business logic модулей."
            )

    def test_validation_no_business_logic_imports(self):
        """validation/ не должен импортировать parser/, writer/, chrome/."""
        validation_dir = PARSER_2GIS_ROOT / "validation"

        if not validation_dir.exists():
            pytest.skip("Директория validation/ не существует")

        business_logic_modules = {"parser", "writer", "chrome"}

        for py_file in get_all_python_files(validation_dir):
            imports = get_file_imports_from_module(py_file, PARSER_2GIS_ROOT)
            illegal_imports = imports.intersection(business_logic_modules)

            assert len(illegal_imports) == 0, (
                f"{py_file.relative_to(PROJECT_ROOT)} импортирует бизнес-логику: {illegal_imports}. "
                "validation/ должен быть изолирован от business logic модулей."
            )

    def test_constants_no_other_module_imports(self):
        """constants.py не должен импортировать другие модули проекта (только стандартные)."""
        constants_file = PARSER_2GIS_ROOT / "constants.py"

        if not constants_file.exists():
            pytest.skip("constants.py не существует")

        imports = get_module_imports(constants_file)

        parser_2gis_imports = {imp for imp in imports if imp.startswith("parser_2gis")}
        allowed_imports = {"typing", "os", "typing.Optional"}

        illegal_imports = parser_2gis_imports - allowed_imports

        assert len(illegal_imports) == 0, (
            f"constants.py импортирует другие модули: {illegal_imports}. "
            "constants.py должен содержать только константы без зависимостей от других модулей."
        )


# =============================================================================
# ТЕСТ 4: Отсутствие циклических зависимостей
# =============================================================================


class TestNoCyclicDependencies:
    """Тесты на отсутствие циклических зависимостей между модулями."""

    def test_main_no_circular_imports_with_parser(self):
        """main.py не должен иметь циклических зависимостей с parser/."""
        main_imports = get_file_imports_from_module(PARSER_2GIS_ROOT / "main.py", PARSER_2GIS_ROOT)

        if "main" in main_imports:
            pytest.fail("Обнаружена циклическая зависимость: main импортирует main")

    def test_no_circular_dependencies_between_core_modules(self):
        """Проверка отсутствия циклических зависимостей между основными модулями."""
        core_modules = [
            "cache",
            "config",
            "constants",
            "logger",
            "parallel",
            "parser",
            "utils",
            "validation",
        ]

        dependency_graph: dict[str, set[str]] = {}

        for module in core_modules:
            module_file = PARSER_2GIS_ROOT / f"{module}.py"
            if module_file.exists():
                imports = get_file_imports_from_module(module_file, PARSER_2GIS_ROOT)
                dependency_graph[module] = imports.intersection(set(core_modules))

        for module, deps in dependency_graph.items():
            if module in deps:
                pytest.fail(f"Циклическая зависимость: {module} импортирует себя")


# =============================================================================
# ТЕСТ 5: Разделение concerns (Separation of Concerns)
# =============================================================================


class TestSeparationOfConcerns:
    """Тесты на разделение ответственности между модулями."""

    def test_main_no_business_logic_classes(self):
        """main.py не должен содержать классы бизнес-логики (только CLI/аргументы)."""
        main_file = PARSER_2GIS_ROOT / "main.py"

        if not main_file.exists():
            pytest.skip("main.py не существует")

        try:
            with open(main_file, "r", encoding="utf-8") as f:
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
            if isinstance(node, ast.ClassDef):
                if node.name in business_logic_classes:
                    found_classes.append(node.name)

        assert len(found_classes) == 0, (
            f"main.py содержит классы бизнес-логики: {found_classes}. "
            "main.py должен содержать только CLI логику и парсинг аргументов."
        )

    def test_cli_no_data_parsing(self):
        """cli/ не должен содержать парсинг данных (только UI/интерфейс)."""
        cli_dir = PARSER_2GIS_ROOT / "cli"

        if not cli_dir.exists():
            pytest.skip("Директория cli/ не существует")

        parsing_keywords = ["parse_html", "parse_json", "parse_response", "extract_data", "scrape"]

        for py_file in get_all_python_files(cli_dir):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                for keyword in parsing_keywords:
                    if keyword in content:
                        pytest.fail(
                            f"{py_file.relative_to(PROJECT_ROOT)} содержит '{keyword}'. "
                            "cli/ не должен содержать парсинг данных."
                        )
            except (OSError, UnicodeDecodeError):
                continue


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Фикстура возвращает корневую директорию проекта."""
    return PROJECT_ROOT


@pytest.fixture
def parser_2gis_root() -> Path:
    """Фикстура возвращает корневую директорий модуля parser_2gis."""
    return PARSER_2GIS_ROOT


@pytest.fixture
def all_python_files() -> List[Path]:
    """Фикстура возвращает все Python файлы в проекте."""
    return get_all_python_files(PROJECT_ROOT)


@pytest.fixture
def all_parser_2gis_files() -> List[Path]:
    """Фикстура возвращает все Python файлы в модуле parser_2gis."""
    return get_all_python_files(PARSER_2GIS_ROOT)
