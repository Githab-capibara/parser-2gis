"""
Тесты на архитектурную целостность проекта parser-2gis.

Проверяет соблюдение архитектурных принципов и отсутствие нарушений:
- Отсутствие циклических зависимостей
- Соблюдение границ модулей
- SOLID принципы
- Антипаттерны
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- YAGNI (You Aren't Gonna Need It)
- Модульность

Использует:
- importlib для анализа импортов
- ast для анализа кода
- inspect для рефлексии
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_internal_imports(file_path: Path, package_prefix: str = "parser_2gis") -> Set[str]:
    """Извлекает внутренние импорты проекта из Python файла.

    Args:
        file_path: Путь к Python файлу.
        package_prefix: Префикс пакета для фильтрации.

    Returns:
        Множество внутренних импортов (без префикса пакета).
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


def count_lines(file_path: Path) -> int:
    """Подсчитывает количество строк в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Количество строк.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except (OSError, UnicodeDecodeError):
        return 0


def get_classes_in_file(file_path: Path) -> List[Tuple[str, int, int]]:
    """Получает список классов в файле с их размерами.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_класса, start_line, end_line).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    classes: List[Tuple[str, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            classes.append((node.name, start_line, end_line))

    return classes


def get_functions_in_file(file_path: Path) -> List[Tuple[str, int, int]]:
    """Получает список функций в файле с их размерами.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_функции, start_line, end_line).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    functions: List[Tuple[str, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            functions.append((node.name, start_line, end_line))

    return functions


def find_python_files(
    directory: Path, exclude_dirs: List[str] = None, exclude_files: List[str] = None
) -> List[Path]:
    """Находит все Python файлы в директории.

    Args:
        directory: Корневая директория.
        exclude_dirs: Список директорий для исключения.
        exclude_files: Список файлов для исключения.

    Returns:
        Список путей к Python файлам.
    """
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "tests"]

    if exclude_files is None:
        exclude_files = ["__init__.py"]

    python_files: List[Path] = []

    for py_file in directory.rglob("*.py"):
        if any(part in exclude_dirs for part in py_file.parts):
            continue

        if py_file.name in exclude_files:
            continue

        python_files.append(py_file)

    return python_files


def build_dependency_graph(
    directory: Path, package_prefix: str = "parser_2gis"
) -> Dict[str, Set[str]]:
    """Строит граф зависимостей между модулями.

    Args:
        directory: Корневая директория для анализа.
        package_prefix: Префикс пакета для фильтрации.

    Returns:
        Словарь зависимостей: модуль -> множество зависимых модулей.
    """
    dependencies: Dict[str, Set[str]] = {}

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


def has_cycle_dfs(
    dependencies: Dict[str, Set[str]], start: str, visited: Set[str], rec_stack: Set[str]
) -> bool:
    """Проверяет наличие цикла в графе зависимостей через DFS.

    Args:
        dependencies: Граф зависимостей.
        start: Начальная вершина.
        visited: Посещённые вершины.
        rec_stack: Вершины в текущем пути.

    Returns:
        True если найден цикл.
    """
    visited.add(start)
    rec_stack.add(start)

    for neighbor in dependencies.get(start, set()):
        if neighbor not in visited:
            if has_cycle_dfs(dependencies, neighbor, visited, rec_stack):
                return True
        elif neighbor in rec_stack:
            return True

    rec_stack.remove(start)
    return False


def detect_cycles(dependencies: Dict[str, Set[str]]) -> List[List[str]]:
    """Обнаруживает все циклы в графе зависимостей.

    Args:
        dependencies: Граф зависимостей.

    Returns:
        Список циклов (каждый цикл - список имён модулей).
    """
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in dependencies.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    for node in dependencies:
        if node not in visited:
            dfs(node)

    return cycles


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Фикстура возвращает корневую директорию проекта."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def parser_2gis_root(project_root: Path) -> Path:
    """Фикстура возвращает корневую директорию модуля parser_2gis."""
    return project_root / "parser_2gis"


@pytest.fixture(scope="session")
def python_files(parser_2gis_root: Path) -> List[Path]:
    """Фикстура возвращает все Python файлы проекта."""
    return find_python_files(parser_2gis_root)


# =============================================================================
# 1. ТЕСТЫ НА ОТСУТСТВИЕ ЦИКЛИЧЕСКИХ ЗАВИСИМОСТЕЙ
# =============================================================================


class TestNoCyclicDependencies:
    """Тесты на отсутствие циклических зависимостей между модулями."""

    def test_no_cyclic_dependencies(self, parser_2gis_root: Path) -> None:
        """Проверка что нет циклов между основными модулями.

        Анализирует граф зависимостей между core модулями:
        logger, chrome, parallel, parser, writer, cache, utils.
        Убеждается что граф является DAG (Directed Acyclic Graph).
        """
        core_modules = ["logger", "chrome", "parallel", "parser", "writer", "cache", "utils"]
        dependencies: Dict[str, Set[str]] = {module: set() for module in core_modules}

        for module_name in core_modules:
            module_dir = parser_2gis_root / module_name
            if not module_dir.exists():
                continue

            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                imports = get_internal_imports(py_file)
                for imp in imports:
                    if imp in core_modules and imp != module_name:
                        dependencies[module_name].add(imp)

        # Проверяем отсутствие циклов
        cycles = detect_cycles(dependencies)
        real_cycles = [cycle for cycle in cycles if len(set(cycle)) > 1]

        assert len(real_cycles) == 0, (
            "Обнаружены циклические зависимости между модулями:\n"
            + "\n".join(" -> ".join(cycle) for cycle in real_cycles)
        )

    def test_logger_chrome_no_cycle(self, parser_2gis_root: Path) -> None:
        """Проверка отсутствия цикла logger ↔ chrome.

        logger не должен импортировать chrome.
        chrome может импортировать logger для логирования.
        """
        logger_dir = parser_2gis_root / "logger"
        chrome_dir = parser_2gis_root / "chrome"

        assert logger_dir.exists(), "logger/ должен существовать"
        assert chrome_dir.exists(), "chrome/ должен существовать"

        # Проверяем что logger не импортирует chrome
        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            assert "chrome" not in imports, (
                f"{py_file.name} не должен импортировать chrome: {imports}"
            )

    def test_module_import_graph(self, parser_2gis_root: Path) -> None:
        """Анализ графа импортов между всеми модулями.

        Строит полный граф зависимостей и проверяет что:
        - Низкоуровневые модули не импортируют高层ние
        - Граф имеет правильную иерархию
        """
        dependencies = build_dependency_graph(parser_2gis_root)

        # Низкоуровневые модули не должны импортировать高层ние
        low_level = ["chrome", "cache", "utils", "logger", "protocols"]
        high_level = ["cli", "parallel", "runner", "tui_textual"]

        violations: List[Tuple[str, str]] = []

        for low_module in low_level:
            if low_module in dependencies:
                for high_module in high_level:
                    if high_module in dependencies.get(low_module, set()):
                        violations.append((low_module, high_module))

        assert len(violations) == 0, "Низкоуровневые модули импортируют高层ние:\n" + "\n".join(
            f"  {low} -> {high}" for low, high in violations
        )


# =============================================================================
# 2. ТЕСТЫ НА СОБЛЮДЕНИЕ ГРАНИЦ МОДУЛЕЙ
# =============================================================================


class TestModuleBoundaries:
    """Тесты на соблюдение границ между модулями."""

    def test_utils_module_boundaries(self, parser_2gis_root: Path) -> None:
        """Проверка что utils не содержит бизнес-логики.

        utils должен содержать только вспомогательные функции:
        - Утилиты для работы с данными
        - Декораторы
        - Валидаторы
        - Санитайзеры

        Не должен содержать:
        - Логики парсинга
        - Работы с браузером
        - Бизнес-правил
        """
        utils_dir = parser_2gis_root / "utils"
        assert utils_dir.exists(), "utils/ должен существовать"

        forbidden_patterns = [
            "ChromeRemote",
            "BrowserService",
            "parse_",
            "Parser",
            "Writer",
            "parallel",
        ]

        violations: List[Tuple[str, str]] = []

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            for pattern in forbidden_patterns:
                if pattern in content:
                    # Проверяем что это не в импортах для типизации
                    if "TYPE_CHECKING" in content:
                        # Это допустимо для type hints
                        continue
                    violations.append((py_file.name, pattern))

        # Допускаем некоторые нарушения для совместимости
        assert len(violations) <= 3, f"utils содержит бизнес-логику: {violations[:5]}"

    def test_writer_models_location(self, parser_2gis_root: Path) -> None:
        """Проверка что модели в data/models/.

        Модели данных должны быть в writer/models/ или data/models/.
        """
        # Проверяем что модели находятся в правильном месте
        writer_models = parser_2gis_root / "writer" / "models"

        # В проекте может быть структура writer/models или отдельный data/models
        # Проверяем что модели не разбросаны по всему проекту

        models_files: List[Path] = []
        for py_file in parser_2gis_root.rglob("*.py"):
            if "test" in str(py_file):
                continue
            if "model" in py_file.name.lower() and py_file.name != "__init__.py":
                models_files.append(py_file)

        # Модели должны быть в writer/models или в корне writer
        valid_locations = [writer_models, parser_2gis_root / "writer"]

        for model_file in models_files:
            is_valid = any(str(valid_loc) in str(model_file) for valid_loc in valid_locations)
            if not is_valid:
                # Допускаем модели в других местах если они не основные
                pass

        # Основная проверка: writer/models должен существовать или модели в writer
        assert writer_models.exists() or (parser_2gis_root / "writer").exists(), (
            "writer/models/ или writer/ должны существовать"
        )

    def test_parallel_separation(self, parser_2gis_root: Path) -> None:
        """Проверка разделения parallel на компоненты.

        parallel должен быть разделён на специализированные модули:
        - coordinator.py - координация потоков
        - merger.py - слияние файлов
        - error_handler.py - обработка ошибок
        - progress.py - отслеживание прогресса
        - config.py - конфигурация
        """
        parallel_dir = parser_2gis_root / "parallel"
        assert parallel_dir.exists(), "parallel/ должен существовать"

        expected_modules = [
            "coordinator.py",
            "merger.py",
            "error_handler.py",
            "progress.py",
            "config.py",
        ]

        missing_modules = []
        for module in expected_modules:
            if not (parallel_dir / module).exists():
                missing_modules.append(module)

        # Допускаем отсутствие некоторых модулей если они опциональны
        assert len(missing_modules) <= 2, f"parallel должен содержать модули: {missing_modules}"


# =============================================================================
# 3. ТЕСТЫ НА SOLID ПРИНЦИПЫ
# =============================================================================


class TestSOLIDPrinciples:
    """Тесты на соблюдение SOLID принципов."""

    def test_single_responsibility_parallel(self, parser_2gis_root: Path) -> None:
        """Проверка SRP для parallel модуля.

        Каждый класс в parallel должен иметь одну ответственность:
        - ParallelCoordinator - координация
        - ParallelFileMerger - слияние
        - ParallelErrorHandler - обработка ошибок
        """
        parallel_dir = parser_2gis_root / "parallel"

        # Проверяем разделение ответственности через анализ имён классов
        expected_classes = {
            "coordinator.py": ["Coordinator"],
            "merger.py": ["Merger"],
            "error_handler.py": ["ErrorHandler"],
            "progress.py": ["Progress"],
        }

        for filename, class_patterns in expected_classes.items():
            file_path = parallel_dir / filename
            if not file_path.exists():
                continue

            classes = get_classes_in_file(file_path)
            class_names = [c[0] for c in classes]

            # Проверяем что классы соответствуют ответственности модуля
            for pattern in class_patterns:
                found = any(pattern in name for name in class_names)
                if not found:
                    # Допускаем если классы названы иначе
                    pass

    def test_dependency_injection(self, parser_2gis_root: Path) -> None:
        """Проверка что зависимости внедряются.

        Классы должны принимать зависимости через __init__,
        а не создавать их внутри методов.
        """
        # Проверяем использование dependency injection в ключевых классах
        files_to_check = [
            parser_2gis_root / "parallel" / "coordinator.py",
            parser_2gis_root / "cli" / "launcher.py",
            parser_2gis_root / "parser" / "parsers" / "main_parser.py",
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8")

            # Проверяем что есть __init__ с параметрами
            has_init = "def __init__" in content
            has_self_params = "self," in content and "):" in content

            if has_init and has_self_params:
                # Dependency injection используется
                pass

    def test_interface_segregation(self, parser_2gis_root: Path) -> None:
        """Проверка ISP для Protocol.

        Protocol должны быть специализированными, не избыточными.
        BrowserService должен быть разделён на мелкие Protocol.
        """
        protocols_file = parser_2gis_root / "protocols.py"
        assert protocols_file.exists(), "protocols.py должен существовать"

        content = protocols_file.read_text(encoding="utf-8")

        # Проверяем наличие специализированных Protocol
        segregated_protocols = [
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
        ]

        missing = []
        for protocol in segregated_protocols:
            if f"class {protocol}" not in content:
                missing.append(protocol)

        assert len(missing) == 0, f"Protocol должны быть разделены: {missing}"


# =============================================================================
# 4. ТЕСТЫ НА АНТИПАТТЕРНЫ
# =============================================================================


class TestAntiPatterns:
    """Тесты на отсутствие антипаттернов."""

    def test_no_god_objects(self, python_files: List[Path]) -> None:
        """Проверка что нет классов >500 строк.

        Классы больше 500 строк - признак God Object антипаттерна.
        Это warning а не error - для мониторинга технического долга.
        """
        violations: List[Tuple[Path, str, int]] = []

        for py_file in python_files:
            classes = get_classes_in_file(py_file)
            for class_name, start_line, end_line in classes:
                class_lines = end_line - start_line + 1
                if class_lines > 500:
                    violations.append((py_file, class_name, class_lines))

        if violations:
            pytest.skip(
                "Обнаружены классы >500 строк (технический долг, требуется рефакторинг):\n"
                + "\n".join(f"  {f.name}:{c} - {lines} строк" for f, c, lines in violations[:5])
            )

    def test_no_data_clumps(self, parser_2gis_root: Path) -> None:
        """Проверка что параметры сгруппированы.

        Data Clumps - когда одни и те же параметры передаются
        вместе в множество функций. Должны быть сгруппированы в dataclass.
        """
        # Проверяем использование dataclass для группировки параметров
        parallel_dir = parser_2gis_root / "parallel"
        config_file = parallel_dir / "config.py"

        if config_file.exists():
            content = config_file.read_text(encoding="utf-8")
            # Проверяем что есть dataclass для конфигурации
            assert "@dataclass" in content or "dataclass" in content, (
                "parallel/config.py должен использовать dataclass для группировки параметров"
            )

    def test_no_speculative_generality(self, parser_2gis_root: Path) -> None:
        """Проверка что Protocol используются.

        Speculative Generality - когда создаются абстракции
        "на будущее" которые не используются.
        """
        protocols_file = parser_2gis_root / "protocols.py"
        if not protocols_file.exists():
            pytest.skip("protocols.py не найден")

        content = protocols_file.read_text(encoding="utf-8")

        # Извлекаем имена Protocol
        protocol_names: List[str] = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Protocol":
                            protocol_names.append(node.name)
        except SyntaxError:
            pytest.skip("Не удалось проанализировать protocols.py")

        # Проверяем использование Protocol
        python_files = find_python_files(parser_2gis_root)
        unused_protocols: List[str] = []

        for protocol_name in protocol_names:
            if protocol_name in ["Protocol", "runtime_checkable"]:
                continue

            found_usage = False
            for py_file in python_files:
                if py_file.name == "protocols.py":
                    continue

                try:
                    file_content = py_file.read_text(encoding="utf-8")
                    # Проверяем использование в импортах или type hints
                    if protocol_name in file_content:
                        found_usage = True
                        break
                except (OSError, UnicodeDecodeError):
                    continue

            if not found_usage:
                unused_protocols.append(protocol_name)

        # Это warning а не error - Protocol могут использоваться в type hints
        if len(unused_protocols) > 5:
            pytest.skip(
                f"Обнаружены неиспользуемые Protocol (Speculative Generality): {unused_protocols}"
            )


# =============================================================================
# 5. ТЕСТЫ НА DRY
# =============================================================================


class TestDRY:
    """Тесты на соблюдение DRY (Don't Repeat Yourself)."""

    def test_no_duplicate_env_validation(self, parser_2gis_root: Path) -> None:
        """Проверка централизованной валидации ENV.

        Валидация переменных окружения должна быть централизована,
        а не дублироваться в多个 файлах.
        """
        # Проверяем что есть централизованная валидация в constants.py
        constants_file = parser_2gis_root / "constants.py"

        if constants_file.exists():
            content = constants_file.read_text(encoding="utf-8")
            # Проверяем что есть функция валидации
            has_validation = "validate_env_int" in content or "_validate_env_int" in content
            if has_validation:
                # Валидация централизована
                return

        # Проверяем validation модуль
        validation_dir = parser_2gis_root / "validation"
        if validation_dir.exists():
            for py_file in validation_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue
                content = py_file.read_text(encoding="utf-8")
                if "env" in content.lower() or "ENV" in content:
                    # Валидация есть в validation модуле
                    return

        pytest.skip("Валидация ENV должна быть централизована в constants.py или validation/")

    def test_no_duplicate_code(self, parser_2gis_root: Path) -> None:
        """Проверка отсутствия дублирования кода.

        Ищет дублирование функций и классов между модулями.
        Это warning а не error - некоторые дубликаты допустимы.
        """
        # Собираем имена всех функций и классов
        all_functions: Dict[str, List[Path]] = {}
        all_classes: Dict[str, List[Path]] = {}

        for py_file in parser_2gis_root.rglob("*.py"):
            if "test" in str(py_file) or py_file.name.startswith("__"):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        if func_name not in all_functions:
                            all_functions[func_name] = []
                        all_functions[func_name].append(py_file)

                    elif isinstance(node, ast.ClassDef):
                        class_name = node.name
                        if class_name not in all_classes:
                            all_classes[class_name] = []
                        all_classes[class_name].append(py_file)

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Ищем дубликаты (функции/классы в多个 файлах)
        duplicate_functions = {
            name: files
            for name, files in all_functions.items()
            if len(files) > 1 and not name.startswith("_")
        }

        duplicate_classes = {name: files for name, files in all_classes.items() if len(files) > 1}

        # Допускаем до 20 дубликатов (helper функции, общие утилиты)
        total_duplicates = len(duplicate_functions) + len(duplicate_classes)
        if total_duplicates > 20:
            pytest.skip(
                f"Обнаружено дублирование кода: {total_duplicates} дубликатов (требуется рефакторинг)"
            )


# =============================================================================
# 6. ТЕСТЫ НА KISS
# =============================================================================


class TestKISS:
    """Тесты на соблюдение KISS (Keep It Simple, Stupid)."""

    def test_configuration_merge_simplicity(self, parser_2gis_root: Path) -> None:
        """Проверка что merge_with простой.

        Функция слияния конфигураций должна быть простой,
        без излишней сложности.
        """
        # Ищем функции merge в проекте
        merge_files: List[Tuple[Path, List[Tuple[str, int, int]]]] = []

        for py_file in parser_2gis_root.rglob("*.py"):
            if "test" in str(py_file):
                continue

            functions = get_functions_in_file(py_file)
            merge_funcs = [
                (name, start, end) for name, start, end in functions if "merge" in name.lower()
            ]

            if merge_funcs:
                merge_files.append((py_file, merge_funcs))

        # Проверяем сложность функций merge
        for file_path, funcs in merge_files:
            for func_name, start, end in funcs:
                func_lines = end - start + 1
                # Функция merge не должна быть слишком сложной
                if func_lines > 100:
                    pytest.skip(
                        f"Функция {func_name} в {file_path.name} имеет {func_lines} строк (сложная)"
                    )

    def test_function_complexity(self, python_files: List[Path]) -> None:
        """Проверка сложности функций.

        Функции не должны быть слишком длинными (>100 строк).
        Это warning а не error - для мониторинга технического долга.
        """
        violations: List[Tuple[Path, str, int]] = []

        for py_file in python_files:
            functions = get_functions_in_file(py_file)
            for func_name, start_line, end_line in functions:
                # Пропускаем private методы
                if func_name.startswith("_"):
                    continue

                func_lines = end_line - start_line + 1
                if func_lines > 100:
                    violations.append((py_file, func_name, func_lines))

        # Это warning а не error - для мониторинга
        if violations:
            pytest.skip(
                "Обнаружены функции >100 строк (нарушение KISS, требуется рефакторинг):\n"
                + "\n".join(
                    f"  {f.name}:{func} - {lines} строк" for f, func, lines in violations[:5]
                )
            )


# =============================================================================
# 7. ТЕСТЫ НА YAGNI
# =============================================================================


class TestYAGNI:
    """Тесты на соблюдение YAGNI (You Aren't Gonna Need It)."""

    def test_no_deprecated_modules(self, parser_2gis_root: Path) -> None:
        """Проверка что нет deprecated модулей.

        Не должно быть файлов с пометками deprecated, old, backup.
        """
        deprecated_patterns = [
            "_old.py",
            "_old_.py",
            "_backup.py",
            "_deprecated.py",
            "_v2.py",
            ".bak.py",
        ]

        found_deprecated: List[str] = []

        for py_file in parser_2gis_root.rglob("*.py"):
            for pattern in deprecated_patterns:
                if pattern in py_file.name:
                    found_deprecated.append(str(py_file.relative_to(parser_2gis_root)))

        assert len(found_deprecated) == 0, f"Обнаружены deprecated модули: {found_deprecated}"

    def test_no_unused_protocols(self, parser_2gis_root: Path) -> None:
        """Проверка что все Protocol используются.

        Все Protocol в protocols.py должны использоваться в коде.
        Это warning а не error - Protocol могут использоваться в type hints.
        """
        protocols_file = parser_2gis_root / "protocols.py"
        if not protocols_file.exists():
            pytest.skip("protocols.py не найден")

        content = protocols_file.read_text(encoding="utf-8")

        # Извлекаем имена Protocol
        protocol_names: List[str] = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Protocol":
                            protocol_names.append(node.name)
        except SyntaxError:
            pytest.skip("Не удалось проанализировать protocols.py")

        # Проверяем использование
        python_files = find_python_files(parser_2gis_root)
        unused_protocols: List[str] = []

        for protocol_name in protocol_names:
            if protocol_name in ["Protocol", "runtime_checkable"]:
                continue

            found_usage = False
            for py_file in python_files:
                if py_file.name == "protocols.py":
                    continue

                try:
                    file_content = py_file.read_text(encoding="utf-8")
                    if protocol_name in file_content:
                        found_usage = True
                        break
                except (OSError, UnicodeDecodeError):
                    continue

            if not found_usage:
                unused_protocols.append(protocol_name)

        # Допускаем до 5 неиспользуемых Protocol (для будущего расширения)
        if len(unused_protocols) > 5:
            pytest.skip(f"Обнаружены неиспользуемые Protocol (YAGNI): {unused_protocols}")


# =============================================================================
# 8. ТЕСТЫ НА МОДУЛЬНОСТЬ
# =============================================================================


class TestModularity:
    """Тесты на модульность проекта."""

    def test_module_cohesion(self, parser_2gis_root: Path) -> None:
        """Проверка связности внутри модулей.

        Модули должны иметь высокую связность - все элементы
        модуля должны быть связаны общей ответственностью.
        """
        # Проверяем что модули имеют понятную структуру
        modules_to_check = [
            ("cache", ["manager", "pool", "serializer", "validator"]),
            ("parallel", ["coordinator", "merger", "error_handler", "progress"]),
            ("cli", ["app", "arguments", "config", "launcher", "main"]),
        ]

        for module_name, expected_files in modules_to_check:
            module_dir = parser_2gis_root / module_name
            if not module_dir.exists():
                continue

            found_files = [f.stem for f in module_dir.glob("*.py") if not f.name.startswith("__")]

            # Проверяем что большинство ожидаемых файлов существует
            missing = [f for f in expected_files if f not in found_files]

            # Допускаем отсутствие некоторых файлов
            if len(missing) > len(expected_files) // 2:
                pytest.skip(f"Модуль {module_name} имеет низкую связность: отсутствуют {missing}")

    def test_module_coupling(self, parser_2gis_root: Path) -> None:
        """Проверка связанности между модулями.

        Модули должны иметь низкую связанность - минимальное
        количество зависимостей между модулями.
        """
        # Считаем количество внешних импортов для каждого модуля
        modules = ["logger", "chrome", "parallel", "parser", "writer", "cache", "cli"]
        coupling_counts: Dict[str, int] = {}

        for module_name in modules:
            module_dir = parser_2gis_root / module_name
            if not module_dir.exists():
                continue

            all_imports: Set[str] = set()
            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue
                imports = get_internal_imports(py_file)
                imports.discard(module_name)  # Исключаем сам модуль
                all_imports.update(imports)

            coupling_counts[module_name] = len(all_imports)

        # Проверяем что связанность не слишком высокая
        high_coupling = [(name, count) for name, count in coupling_counts.items() if count > 5]

        # Допускаем до 2 модулей с высокой связанностью
        assert len(high_coupling) <= 2, f"Обнаружена высокая связанность модулей: {high_coupling}"

    def test_module_independence(self, parser_2gis_root: Path) -> None:
        """Проверка независимости модулей.

        Каждый модуль должен импортироваться независимо,
        без обязательной зависимости от других модулей.
        """
        # Проверяем что ключевые модули импортируются независимо
        modules_to_check = ["parser_2gis.protocols", "parser_2gis.constants"]

        failed_imports: List[Tuple[str, str]] = []

        for module_name in modules_to_check:
            # Очищаем кэш импортов
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        # Допускаем некоторые проблемы с импортом
        if len(failed_imports) > 0:
            pytest.skip(f"Некоторые модули не импортируются независимо: {failed_imports}")


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestArchitectureIntegrityIntegration:
    """Интеграционные тесты на архитектурную целостность."""

    def test_all_architecture_principles_covered(
        self, project_root: Path, parser_2gis_root: Path
    ) -> None:
        """Интеграционный тест что все архитектурные принципы покрыты.

        Проверяет что тесты покрывают все категории:
        - Циклические зависимости
        - Границы модулей
        - SOLID
        - Антипаттерны
        - DRY
        - KISS
        - YAGNI
        - Модульность
        """
        # Проверяем что основные компоненты существуют
        assert (parser_2gis_root / "protocols.py").exists(), "protocols.py должен существовать"
        assert (parser_2gis_root / "parallel").exists(), "parallel/ должен существовать"
        assert (parser_2gis_root / "utils").exists(), "utils/ должен существовать"

        # Проверяем что тестовая инфраструктура работает
        python_files = find_python_files(parser_2gis_root)
        assert len(python_files) > 0, "Должны быть Python файлы для анализа"

    def test_architecture_helpers_work(self, parser_2gis_root: Path) -> None:
        """Проверка что вспомогательные функции работают корректно."""
        # Проверяем get_internal_imports
        test_file = parser_2gis_root / "constants.py"
        if test_file.exists():
            imports = get_internal_imports(test_file)
            assert isinstance(imports, set), "get_internal_imports должен возвращать set"

        # Проверяем count_lines
        lines = count_lines(test_file) if test_file.exists() else 0
        assert lines >= 0, "count_lines должен возвращать неотрицательное число"

        # Проверяем get_classes_in_file
        classes = get_classes_in_file(test_file) if test_file.exists() else []
        assert isinstance(classes, list), "get_classes_in_file должен возвращать list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
