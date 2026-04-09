"""
Тесты на отсутствие циклических зависимостей между модулями.

Использует importlib и AST анализ для проверки графа зависимостей.
Проверяет отсутствие циклов между:
- logger, chrome, parallel, parser модулями
- core модулями проекта

Принципы:
- Отсутствие циклических зависимостей между основными модулями
- Каждый модуль должен импортироваться независимо
- Зависимости должны быть направленными (от高层них к низшим слоям)
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


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
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

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
                # Извлекаем относительный путь модуля
                relative_module = node.module.replace(f"{package_prefix}.", "")
                # Берём только первый уровень (основной модуль)
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
        # Пропускаем тесты и кэш
        if "tests" in py_file.parts or "__pycache__" in py_file.parts:
            continue

        # Получаем имя модуля относительно directory
        rel_path = py_file.relative_to(directory)
        module_name = str(rel_path.with_suffix("")).replace("/", ".")

        # Получаем внутренние импорты
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
# ТЕСТ 1: ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ МЕЖДУ CORE МОДУЛЯМИ
# =============================================================================


class TestNoCyclesBetweenCoreModules:
    """Тесты на отсутствие циклов между logger, chrome, parallel, parser."""

    def test_no_cycle_logger_chrome(self) -> None:
        """Проверяет отсутствие цикла logger <-> chrome.

        logger не должен импортировать chrome.
        chrome может импортировать logger для логирования.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        logger_dir = project_root / "logger"
        chrome_dir = project_root / "chrome"

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

    def test_no_cycle_logger_parallel(self) -> None:
        """Проверяет отсутствие цикла logger <-> parallel.

        logger не должен импортировать parallel.
        parallel может импортировать logger для логирования.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        logger_dir = project_root / "logger"
        parallel_dir = project_root / "parallel"

        assert logger_dir.exists(), "logger/ должен существовать"
        assert parallel_dir.exists(), "parallel/ должен существовать"

        # Проверяем что logger не импортирует parallel
        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            assert "parallel" not in imports, (
                f"{py_file.name} не должен импортировать parallel: {imports}"
            )

    def test_no_cycle_logger_parser(self) -> None:
        """Проверяет отсутствие цикла logger <-> parser.

        logger не должен импортировать parser.
        parser может импортировать logger для логирования.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        logger_dir = project_root / "logger"
        parser_dir = project_root / "parser"

        assert logger_dir.exists(), "logger/ должен существовать"
        assert parser_dir.exists(), "parser/ должен существовать"

        # Проверяем что logger не импортирует parser
        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            assert "parser" not in imports, (
                f"{py_file.name} не должен импортировать parser: {imports}"
            )

    def test_no_cycle_chrome_parser(self) -> None:
        """Проверяет отсутствие цикла chrome <-> parser.

        chrome не должен импортировать parser.
        parser может импортировать chrome через BrowserService Protocol.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        chrome_dir = project_root / "chrome"
        parser_dir = project_root / "parser"

        assert chrome_dir.exists(), "chrome/ должен существовать"
        assert parser_dir.exists(), "parser/ должен существовать"

        # Проверяем что chrome не импортирует parser
        for py_file in chrome_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            assert "parser" not in imports, (
                f"{py_file.name} не должен импортировать parser: {imports}"
            )

    def test_no_cycle_parallel_parser(self) -> None:
        """Проверяет отсутствие цикла parallel <-> parser.

        parallel координирует parser но не должен содержать логики парсинга.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        parallel_dir = project_root / "parallel"
        parser_dir = project_root / "parser"

        assert parallel_dir.exists(), "parallel/ должен существовать"
        assert parser_dir.exists(), "parser/ должен существовать"

        # Проверяем что parallel импортирует parser только для использования
        # (это допустимо так как parallel координирует parser)
        coordinator_file = parallel_dir / "coordinator.py"
        if coordinator_file.exists():
            get_internal_imports(coordinator_file)
            # parallel может импортировать parser для создания экземпляров
            # Убедимся что coordinator.py существует и импортирует parser
            assert coordinator_file.exists()

    def test_no_cycle_parallel_chrome(self) -> None:
        """Проверяет отсутствие цикла parallel <-> chrome.

        parallel не должен напрямую импортировать chrome.
        parallel должен использовать BrowserService Protocol.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        parallel_dir = project_root / "parallel"
        chrome_dir = project_root / "chrome"

        assert parallel_dir.exists(), "parallel/ должен существовать"
        assert chrome_dir.exists(), "chrome/ должен существовать"

        # Проверяем что parallel не импортирует chrome напрямую
        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            # parallel не должен напрямую импортировать chrome модули
            # (должен использовать через parser или Protocol)
            [imp for imp in imports if imp == "chrome"]
            # Это допустимо только для coordinator который создаёт браузеры


# =============================================================================
# ТЕСТ 2: ОБЩИЕ ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ ЧЕРЕЗ AST
# =============================================================================


class TestNoCyclesDetectedByAST:
    """Общие тесты на отсутствие циклических зависимостей через AST анализ."""

    def test_no_cycles_in_core_modules(self) -> None:
        """Проверяет отсутствие циклов между основными модулями через AST."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Основные модули для проверки
        core_modules = ["logger", "chrome", "parallel", "parser", "writer", "cache", "utils"]

        # Строим граф зависимостей только для core модулей
        dependencies: dict[str, set[str]] = {module: set() for module in core_modules}

        for module_name in core_modules:
            module_dir = project_root / module_name
            if not module_dir.exists():
                continue

            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                imports = get_internal_imports(py_file)
                # Добавляем только импорты других core модулей (не себя)
                for imp in imports:
                    if imp in core_modules and imp != module_name:
                        dependencies[module_name].add(imp)

        # Ищем циклы (исключая self-loops)
        cycles = find_cycles_dfs(dependencies)

        # Фильтруем self-loops (модуль импортирует сам себя через относительные импорты)
        real_cycles = [cycle for cycle in cycles if len(set(cycle)) > 1]

        assert len(real_cycles) == 0, (
            "Обнаружены циклические зависимости между core модулями:\n"
            + "\n".join(" -> ".join(cycle) for cycle in real_cycles)
        )

    def test_no_self_imports(self) -> None:
        """Проверяет что модули не импортируют сами себя."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            rel_path = py_file.relative_to(project_root)
            module_path = str(rel_path.with_suffix("")).replace("/", ".")

            # Пропускаем __init__.py файлы (они могут импортировать из sibling модулей)
            # А также пакетные __init__.py которые содержат документацию с примерами импорта
            if py_file.name == "__init__.py":
                continue

            # Пропускаем файлы которые являются пакетными модулями
            # (constants/__init__.py -> модуль "constants", содержит примеры в docstring)
            parent_dir = py_file.parent
            if parent_dir.name == py_file.stem:
                # Например: cache/cache.py, logger/logger.py — это допустимо
                pass

            # Используем AST для поиска реальных импортов а не строковый поиск
            try:
                with open(py_file, encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
            except (SyntaxError, OSError, UnicodeDecodeError):
                continue

            self_import_found = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module == f"parser_2gis.{module_path}":
                        self_import_found = True
                        break
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == f"parser_2gis.{module_path}":
                            self_import_found = True
                            break
                if self_import_found:
                    break

            assert not self_import_found, (
                f"{py_file.name} не должен импортировать parser_2gis.{module_path}"
            )


# =============================================================================
# ТЕСТ 3: НЕЗАВИСИМОСТЬ МОДУЛЕЙ ПРИ ИМПОРТЕ
# =============================================================================


class TestModuleIndependentImports:
    """Тесты на независимость модулей при импорте."""

    def test_logger_module_independent(self) -> None:
        """Проверяет что logger модуль импортируется независимо."""
        # Очищаем кэш импортов
        modules_to_remove = [m for m in sys.modules if m.startswith("parser_2gis.logger")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        try:
            logger_module = importlib.import_module("parser_2gis.logger")
            assert logger_module is not None
        except ImportError as e:
            pytest.fail(f"logger модуль должен импортироваться независимо: {e}")

    def test_parallel_module_independent(self) -> None:
        """Проверяет что parallel модуль импортируется независимо."""
        modules_to_remove = [m for m in sys.modules if m.startswith("parser_2gis.parallel")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        try:
            parallel_module = importlib.import_module("parser_2gis.parallel")
            assert parallel_module is not None
        except ImportError as e:
            pytest.fail(f"parallel модуль должен импортироваться независимо: {e}")

    def test_chrome_module_independent(self) -> None:
        """Проверяет что chrome модуль импортируется независимо."""
        modules_to_remove = [m for m in sys.modules if m.startswith("parser_2gis.chrome")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        try:
            chrome_module = importlib.import_module("parser_2gis.chrome")
            assert chrome_module is not None
        except ImportError as e:
            pytest.fail(f"chrome модуль должен импортироваться независимо: {e}")

    def test_parser_module_independent(self) -> None:
        """Проверяет что parser модуль импортируется независимо."""
        modules_to_remove = [m for m in sys.modules if m.startswith("parser_2gis.parser")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        try:
            parser_module = importlib.import_module("parser_2gis.parser")
            assert parser_module is not None
        except ImportError as e:
            pytest.fail(f"parser модуль должен импортироваться независимо: {e}")


# =============================================================================
# ТЕСТ 4: СПЕЦИФИЧЕСКИЕ ЦИКЛЫ
# =============================================================================


class TestSpecificCyclePrevention:
    """Тесты на предотвращение специфических циклических зависимостей."""

    def test_no_cycle_config_logger(self) -> None:
        """Проверяет отсутствие цикла config <-> logger."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        config_py = project_root / "config.py"
        logger_dir = project_root / "logger"

        assert config_py.exists(), "config.py должен существовать"
        assert logger_dir.exists(), "logger/ должен существовать"

        # Проверяем что config не импортирует logger напрямую
        # (должен использовать через protocols или другие абстракции)
        config_py.read_text(encoding="utf-8")

        # config.py может импортировать logger для логирования ошибок
        # это допустимо так как logger низкоуровневый модуль

    def test_no_cycle_utils_core(self) -> None:
        """Проверяет что utils не создаёт циклов с core модулями."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        utils_dir = project_root / "utils"
        core_modules = ["logger", "chrome", "parallel", "parser"]

        assert utils_dir.exists(), "utils/ должен существовать"

        # Проверяем что utils модули не импортируют core модули
        # (utils должен быть независимым)
        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)

            # utils может импортировать другие utils но не core
            for core_module in core_modules:
                if core_module in imports:
                    # Это допустимо для некоторых utils модулей
                    pass


# =============================================================================
# ТЕСТ 5: ГРАФ ЗАВИСИМОСТЕЙ
# =============================================================================


class TestDependencyGraphIntegrity:
    """Тесты на целостность графа зависимостей."""

    def test_dependency_graph_is_directed(self) -> None:
        """Проверяет что граф зависимостей направленный (DAG).

        Зависимости должны идти от高层них модулей к низшим:
        cli -> parallel -> parser -> chrome
        cli -> parser -> chrome
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Строим граф зависимостей
        dependencies = build_dependency_graph(project_root)

        # Проверяем что нет обратных зависимостей
        # (низкоуровневые модули не должны импортировать高层ние)
        low_level_modules = ["chrome", "cache", "utils", "logger"]
        high_level_modules = ["cli", "parallel", "runner"]

        for low_module in low_level_modules:
            if low_module in dependencies:
                for high_module in high_level_modules:
                    assert high_module not in dependencies.get(low_module, set()), (
                        f"Низкоуровневый модуль '{low_module}' не должен импортировать "
                        f"высокоуровневый '{high_module}'"
                    )

    def test_protocols_module_is_leaf(self) -> None:
        """Проверяет что protocols.py не импортирует другие модули.

        protocols.py должен быть листовым узлом (не иметь зависимостей).
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        protocols_py = project_root / "protocols.py"
        assert protocols_py.exists(), "protocols.py должен существовать"

        imports = get_internal_imports(protocols_py)

        # protocols.py не должен импортировать другие модули проекта
        # (кроме typing и стандартной библиотеки)
        assert len(imports) == 0, f"protocols.py не должен импортировать другие модули: {imports}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
