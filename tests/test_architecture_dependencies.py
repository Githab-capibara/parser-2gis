"""
Тесты на проверку зависимостей и циклических импортов в архитектуре проекта parser-2gis.

Объединяет тесты из:
- test_architecture_cycles.py - циклические зависимости
- test_architecture_integrity.py - целостность импортов
- test_architecture_constraints.py - ограничения зависимостей
- test_architecture_fixes.py - исправления зависимостей

Принципы:
- Отсутствие циклических зависимостей между модулями
- Каждый модуль должен импортироваться независимо
- Зависимости должны быть направленными (от高层них к низшим слоям)
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


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
# ТЕСТ 1: ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ MAIN ↔ CLI
# =============================================================================


class TestNoCycleMainCli:
    """Тесты на отсутствие цикла main.py ↔ cli/.

    main.py может импортировать из cli/, но cli/ не должен импортировать
    обратно в main.py.
    """

    def test_no_cycle_main_cli(self) -> None:
        """Проверяет отсутствие циклической зависимости между main.py и cli/."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        main_py = project_root / "main.py"
        cli_dir = project_root / "cli"

        assert main_py.exists(), "main.py должен существовать"
        assert cli_dir.exists(), "cli/ должен существовать"

        # Собираем импорты из main.py
        main_imports = self._get_imports_from_file(main_py)

        # Проверяем что main.py импортирует из cli
        cli_imports = [imp for imp in main_imports if "cli" in imp]
        assert len(cli_imports) > 0, "main.py должен импортировать из cli/"

        # Собираем все импорты из cli/
        cli_files = list(cli_dir.glob("*.py"))
        cli_imports_to_main: List[Tuple[str, str]] = []

        for cli_file in cli_files:
            if cli_file.name.startswith("__"):
                continue

            imports = self._get_imports_from_file(cli_file)

            for imp in imports:
                if "main" in imp and "cli" not in imp:
                    cli_imports_to_main.append((cli_file.name, imp))

        assert len(cli_imports_to_main) == 0, (
            "cli/ не должен импортировать из main.py:\n"
            + "\n".join(f"  {f}: {i}" for f, i in cli_imports_to_main)
        )

    def test_cli_does_not_import_main_module(self) -> None:
        """Проверяет что модули cli/ не импортируют parser_2gis.main."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cli_dir = project_root / "cli"

        violations: List[Tuple[str, str]] = []

        for py_file in cli_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            if "from parser_2gis.main import" in content:
                violations.append((py_file.name, "from parser_2gis.main import"))
            if "from .main import" in content and py_file.name != "__init__.py":
                violations.append((py_file.name, "from .main import"))
            if "import parser_2gis.main" in content:
                violations.append((py_file.name, "import parser_2gis.main"))

        assert len(violations) == 0, (
            "Модули cli/ не должны импортировать из main.py:\n"
            + "\n".join(f"  {f}: {i}" for f, i in violations)
        )

    @staticmethod
    def _get_imports_from_file(file_path: Path) -> List[str]:
        """Извлекает список импортируемых модулей из файла."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return []

        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

        return imports


# =============================================================================
# ТЕСТ 2: ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ PARALLEL ↔ TEMP_FILE_MANAGER
# =============================================================================


class TestNoCycleParallelTempFiles:
    """Тесты на отсутствие цикла parallel/ ↔ temp_file_manager.py.

    parallel/ может импортировать из utils/temp_file_manager.py,
    но temp_file_manager.py не должен импортировать из parallel/.
    """

    def test_no_cycle_parallel_temp_files(self) -> None:
        """Проверяет отсутствие цикла между parallel/ и temp_file_manager.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        parallel_dir = project_root / "parallel"
        temp_file_manager = project_root / "utils" / "temp_file_manager.py"

        assert parallel_dir.exists(), "parallel/ должен существовать"
        assert temp_file_manager.exists(), "temp_file_manager.py должен существовать"

        # Проверяем что temp_file_manager.py не импортирует из parallel/
        content = temp_file_manager.read_text(encoding="utf-8")

        assert "from .parallel" not in content, (
            "temp_file_manager.py не должен импортировать из parallel/"
        )
        assert "from parser_2gis.parallel" not in content, (
            "temp_file_manager.py не должен импортировать из parser_2gis.parallel"
        )


# =============================================================================
# ТЕСТ 3: ОБЩИЕ ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ
# =============================================================================


class TestNoImportCyclesDetected:
    """Общие тесты на отсутствие циклических импортов."""

    def test_no_import_cycles_detected(self) -> None:
        """Проверяет отсутствие циклических импортов в проекте.

        Строит граф зависимостей и ищет циклы.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Собираем граф зависимостей
        dependencies = self._build_dependency_graph(project_root)

        # Ищем циклы
        cycles = self._find_cycles(dependencies)

        assert len(cycles) == 0, "Обнаружены циклические зависимости:\n" + "\n".join(
            " -> ".join(cycle) for cycle in cycles
        )

    def test_core_modules_independent(self) -> None:
        """Проверяет что основные модули импортируются независимо."""
        core_modules = [
            "parser_2gis.cache",
            "parser_2gis.chrome",
            "parser_2gis.parser",
            "parser_2gis.writer",
            "parser_2gis.utils",
            "parser_2gis.validation",
            "parser_2gis.cli",
            "parser_2gis.parallel",
            "parser_2gis.logger",
        ]

        failed_imports: List[Tuple[str, str]] = []

        for module_name in core_modules:
            # Очищаем кэш импортов
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                __import__(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        assert len(failed_imports) == 0, "Модули должны импортироваться независимо:\n" + "\n".join(
            f"  {m}: {e}" for m, e in failed_imports
        )

    def test_no_cyclic_dependencies_between_core_modules(self) -> None:
        """Проверяет отсутствие циклических зависимостей между основными модулями."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

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

        dependency_graph: Dict[str, Set[str]] = {}

        for module in core_modules:
            module_file = project_root / f"{module}.py"
            if module_file.exists():
                imports = get_file_imports_from_module(module_file, project_root)
                dependency_graph[module] = imports.intersection(set(core_modules))

        for module, deps in dependency_graph.items():
            if module in deps:
                pytest.fail(f"Циклическая зависимость: {module} импортирует себя")

    @staticmethod
    def _build_dependency_graph(project_root: Path) -> Dict[str, Set[str]]:
        """Строит граф зависимостей между модулями."""
        dependencies: Dict[str, Set[str]] = {}

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Получаем имя модуля относительно project_root
            rel_path = py_file.relative_to(project_root)
            module_name = str(rel_path.with_suffix("")).replace("/", ".")

            if module_name not in dependencies:
                dependencies[module_name] = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("parser_2gis"):
                        imported = node.module.replace("parser_2gis.", "")
                        dependencies[module_name].add(imported)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("parser_2gis"):
                            imported = alias.name.replace("parser_2gis.", "")
                            dependencies[module_name].add(imported)

        return dependencies

    @staticmethod
    def _find_cycles(dependencies: Dict[str, Set[str]]) -> List[List[str]]:
        """Ищет циклы в графе зависимостей используя DFS."""
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
                    # Нашли цикл
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
# ТЕСТ 4: НЕЗАВИСИМОСТЬ МОДУЛЕЙ
# =============================================================================


class TestModuleIndependence:
    """Тесты на независимость модулей."""

    def test_utils_modules_are_independent(self) -> None:
        """Проверяет что утилиты в utils/ независимы."""
        utils_dir = Path(__file__).parent.parent / "parser_2gis" / "utils"

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            module_name = f"parser_2gis.utils.{py_file.stem}"

            if module_name in sys.modules:
                del sys.modules[module_name]

            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"{module_name} должен импортироваться: {e}")

    def test_parallel_modules_are_independent(self) -> None:
        """Проверяет что модули parallel/ независимы."""
        parallel_dir = Path(__file__).parent.parent / "parser_2gis" / "parallel"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            module_name = f"parser_2gis.parallel.{py_file.stem}"

            if module_name in sys.modules:
                del sys.modules[module_name]

            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"{module_name} должен импортироваться: {e}")

    def test_cache_module_independent_import(self) -> None:
        """Модуль cache должен импортироваться независимо."""
        cache_modules = [m for m in sys.modules if m.startswith("parser_2gis.cache")]
        for mod in cache_modules:
            del sys.modules[mod]

        cache_module = importlib.import_module("parser_2gis.cache")
        assert cache_module is not None

    def test_chrome_module_independent_import(self) -> None:
        """Модуль chrome должен импортироваться независимо."""
        chrome_modules = [m for m in sys.modules if m.startswith("parser_2gis.chrome")]
        for mod in chrome_modules:
            del sys.modules[mod]

        chrome_module = importlib.import_module("parser_2gis.chrome")
        assert chrome_module is not None


# =============================================================================
# ТЕСТ 5: ЦЕЛОСТНОСТЬ ИМПОРТОВ
# =============================================================================


class TestImportIntegrity:
    """Тесты на целостность импортов."""

    def test_no_broken_imports(self) -> None:
        """Проверяет что нет битых импортов в основных модулях."""
        core_modules = [
            "parser_2gis",
            "parser_2gis.cache",
            "parser_2gis.chrome",
            "parser_2gis.parser",
            "parser_2gis.writer",
            "parser_2gis.utils",
            "parser_2gis.validation",
            "parser_2gis.cli",
            "parser_2gis.parallel",
            "parser_2gis.logger",
            "parser_2gis.config",
            "parser_2gis.config_service",
        ]

        failed_imports: List[Tuple[str, str]] = []

        for module_name in core_modules:
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        assert len(failed_imports) == 0, "Обнаружены битые импорты:\n" + "\n".join(
            f"  {m}: {e}" for m, e in failed_imports
        )

    def test_all_packages_have_init(self) -> None:
        """Проверяет что все пакеты имеют __init__.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        packages = [
            "cache",
            "chrome",
            "parser",
            "writer",
            "utils",
            "validation",
            "cli",
            "parallel",
            "logger",
        ]

        missing_inits = []

        for package in packages:
            init_path = project_root / package / "__init__.py"
            if not init_path.exists():
                missing_inits.append(package)

        assert len(missing_inits) == 0, f"Пакеты не имеют __init__.py: {missing_inits}"

    def test_no_cycle_main_config(self) -> None:
        """Проверяет отсутствие цикла main.py ↔ config.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        config_path = project_root / "config.py"

        config_content = config_path.read_text(encoding="utf-8")

        # config.py не должен импортировать main.py
        config_imports_main = (
            "from .main import" in config_content
            or "from parser_2gis.main import" in config_content
        )

        assert not config_imports_main, (
            "Обнаружена циклическая зависимость: main.py ↔ config.py. "
            "config.py не должен импортировать main.py."
        )


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Фикстура возвращает корневую директорию проекта."""
    return Path(__file__).parent.parent


@pytest.fixture
def parser_2gis_root() -> Path:
    """Фикстура возвращает корневую директорий модуля parser_2gis."""
    return project_root() / "parser_2gis"
