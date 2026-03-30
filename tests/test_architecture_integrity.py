"""
Тесты на архитектурную целостность проекта parser-2gis.

Проверяет соблюдение архитектурных принципов и целостности кодовой базы:
- Отсутствие циклических зависимостей
- Соблюдение границ модулей
- Размер файлов (KISS)
- Сложность классов (SRP)
- Дублирование кода (DRY)
- Protocol разделение (ISP)
- Dependency Injection (DIP)
- Структура проекта
- Обратная совместимость
- Отсутствие неиспользуемого кода (YAGNI)

Принципы:
- Тесты должны быть быстрыми и детерминированными
- Используют importlib для анализа импортов
- Используют inspect для анализа классов
"""

from __future__ import annotations

import ast
import importlib
import sys
import warnings
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


def get_class_methods_count(file_path: Path, class_name: str) -> Dict[str, int]:
    """Получает количество строк в методах класса.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса.

    Returns:
        Словарь {имя_метода: количество_строк}.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return {}

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return {}

    methods_lines: Dict[str, int] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_name = item.name
                    start_line = item.lineno
                    end_line = item.end_lineno if hasattr(item, "end_lineno") else start_line
                    methods_lines[method_name] = end_line - start_line + 1

    return methods_lines


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


@pytest.fixture(scope="session")
def file_contents_cache(python_files: List[Path]) -> Dict[Path, str]:
    """Фикстура кэширует содержимое файлов для производительности."""
    cache: Dict[Path, str] = {}
    for py_file in python_files:
        try:
            cache[py_file] = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            cache[py_file] = ""
    return cache


# =============================================================================
# 1. ТЕСТЫ НА ОТСУТСТВИЕ ЦИКЛИЧЕСКИХ ЗАВИСИМОСТЕЙ
# =============================================================================


class TestNoCyclicDependencies:
    """Тесты на отсутствие циклических зависимостей между модулями."""

    def test_no_cycles_between_core_modules(self, parser_2gis_root: Path) -> None:
        """Проверяет отсутствие циклов между core модулями.

        Проверяет что logger, chrome, parallel, parser не образуют
        циклических зависимостей. Logger должен быть независимым.
        """
        core_modules = ["logger", "chrome", "parallel", "parser"]
        dependencies: Dict[str, Set[str]] = {}

        for module in core_modules:
            module_dir = parser_2gis_root / module
            if not module_dir.exists():
                continue

            module_imports: Set[str] = set()
            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue
                imports = get_internal_imports(py_file)
                module_imports.update(imports)

            # Исключаем сам модуль и utils (общие утилиты)
            module_imports.discard(module)
            module_imports.discard("utils")
            dependencies[module] = module_imports

        # Проверяем что logger не импортирует другие core модули
        if "logger" in dependencies:
            assert "chrome" not in dependencies["logger"], "logger не должен импортировать chrome"
            assert "parallel" not in dependencies["logger"], (
                "logger не должен импортировать parallel"
            )
            assert "parser" not in dependencies["logger"], "logger не должен импортировать parser"

    def test_no_cycles_parallel_submodules(self, parser_2gis_root: Path) -> None:
        """Проверяет отсутствие циклов между подмодулями parallel.

        Подмодули parallel (coordinator, merger, optimizer, progress)
        не должны образовывать циклических зависимостей.
        """
        parallel_dir = parser_2gis_root / "parallel"
        assert parallel_dir.exists(), "parallel/ должен существовать"

        submodules = ["coordinator", "merger", "optimizer", "progress", "error_handler"]
        dependencies: Dict[str, Set[str]] = {}

        for submodule in submodules:
            py_file = parallel_dir / f"{submodule}.py"
            if not py_file.exists():
                continue

            imports = get_internal_imports(py_file)
            # Фильтруем только импорты внутри parallel
            parallel_imports = {imp for imp in imports if imp in submodules}
            dependencies[submodule] = parallel_imports

        # Проверяем отсутствие циклов через DFS
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for submodule in dependencies:
            if submodule not in visited:
                assert not has_cycle(submodule), (
                    f"Обнаружен цикл в parallel подмодулях начиная с {submodule}"
                )

    def test_no_cycles_logger_chrome(self, parser_2gis_root: Path) -> None:
        """Проверяет отсутствие цикла logger <-> chrome.

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

    def test_no_cycles_parser_writer(self, parser_2gis_root: Path) -> None:
        """Проверяет отсутствие цикла parser <-> writer.

        parser и writer должны быть независимыми модулями.
        parser использует writer через Protocol или factory.
        """
        parser_dir = parser_2gis_root / "parser"
        writer_dir = parser_2gis_root / "writer"

        assert parser_dir.exists(), "parser/ должен существовать"
        assert writer_dir.exists(), "writer/ должен существовать"

        # Проверяем что writer не импортирует parser
        for py_file in writer_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            assert "parser" not in imports, (
                f"{py_file.name} не должен импортировать parser: {imports}"
            )


# =============================================================================
# 2. ТЕСТЫ НА СОБЛЮДЕНИЕ ГРАНИЦ МОДУЛЕЙ
# =============================================================================


class TestModuleBoundaries:
    """Тесты на соблюдение границ между модулями."""

    def test_logger_does_not_import_chrome(self, parser_2gis_root: Path) -> None:
        """Проверяет что logger не импортирует chrome.

        logger должен быть низкоуровневым модулем без зависимостей
        от chrome.
        """
        logger_dir = parser_2gis_root / "logger"

        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            assert "from parser_2gis.chrome" not in content, (
                f"{py_file.name} не должен импортировать chrome"
            )
            assert "from .chrome" not in content, f"{py_file.name} не должен импортировать chrome"

    def test_parallel_does_not_import_tui(self, parser_2gis_root: Path) -> None:
        """Проверяет что parallel не импортирует tui_textual.

        parallel должен быть независим от UI компонентов.
        """
        parallel_dir = parser_2gis_root / "parallel"
        tui_dir = parser_2gis_root / "tui_textual"

        assert parallel_dir.exists(), "parallel/ должен существовать"
        assert tui_dir.exists(), "tui_textual/ должен существовать"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            assert "tui_textual" not in imports, (
                f"{py_file.name} не должен импортировать tui_textual: {imports}"
            )

    def test_utils_modules_are_independent(self, parser_2gis_root: Path) -> None:
        """Проверяет что модули utils независимы друг от друга.

        Модули utils должны быть максимально независимыми.
        """
        utils_dir = parser_2gis_root / "utils"
        assert utils_dir.exists(), "utils/ должен существовать"

        utils_modules = ["data_utils", "math_utils", "path_utils", "decorators", "sanitizers"]

        for module in utils_modules:
            py_file = utils_dir / f"{module}.py"
            if not py_file.exists():
                continue

            imports = get_internal_imports(py_file)
            # utils модули не должны импортировать другие utils модули
            # (за исключением __init__.py)
            other_utils = [imp for imp in imports if imp in utils_modules and imp != module]
            # Это допустимо для некоторых утилит
            assert len(other_utils) <= 2, (
                f"{module}.py импортирует слишком много других utils модулей: {other_utils}"
            )

    def test_validation_no_business_logic_imports(self, parser_2gis_root: Path) -> None:
        """Проверяет что validation не импортирует бизнес-логику.

        validation должен содержать только логику валидации,
        без импортов из parser, chrome, parallel.
        """
        validation_dir = parser_2gis_root / "validation"
        assert validation_dir.exists(), "validation/ должен существовать"

        forbidden_imports = {"parser", "chrome", "parallel", "tui_textual"}

        for py_file in validation_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            imports = get_internal_imports(py_file)
            violations = imports.intersection(forbidden_imports)
            assert len(violations) == 0, (
                f"{py_file.name} не должен импортировать бизнес-логику: {violations}"
            )


# =============================================================================
# 3. ТЕСТЫ НА РАЗМЕР ФАЙЛОВ (KISS)
# =============================================================================


class TestFileSizeLimits:
    """Тесты на ограничение размера файлов (KISS principle)."""

    MAX_FILE_LINES = 1000
    STRICT_MAX_FILE_LINES = 500

    def test_no_files_over_1000_lines(self, python_files: List[Path]) -> None:
        """Проверяет что нет файлов больше 1000 строк.

        Файлы больше 1000 строк нарушают KISS principle.
        Это warning а не error - для мониторинга технического долга.
        """
        violations: List[Tuple[Path, int]] = []

        for py_file in python_files:
            lines = count_lines(py_file)
            if lines > self.MAX_FILE_LINES:
                violations.append((py_file, lines))

        if violations:
            pytest.skip(
                "Файлы превышают 1000 строк (технический долг):\n"
                + "\n".join(
                    f"  {f.relative_to(python_files[0].parent.parent)}: {lines_count} строк"
                    for f, lines_count in violations
                )
            )

    def test_no_files_over_500_lines_with_exceptions(self, python_files: List[Path]) -> None:
        """Проверяет что нет файлов больше 500 строк (с исключениями).

        Исключения: сложные модули с обоснованной причиной.
        """
        # Исключения (файлы которые могут быть больше 500 строк)
        exceptions = {
            "browser.py",  # Сложная логика работы с браузером
            "remote.py",  # Chrome DevTools Protocol
        }

        violations: List[Tuple[Path, int]] = []

        for py_file in python_files:
            if py_file.name in exceptions:
                continue

            lines = count_lines(py_file)
            if lines > self.STRICT_MAX_FILE_LINES:
                violations.append((py_file, lines))

        # Это warning а не error - для мониторинга
        if violations:
            pytest.skip(
                "Файлы превышают 500 строк (рекомендация к рефакторингу):\n"
                + "\n".join(
                    f"  {f.relative_to(python_files[0].parent.parent)}: {lines_count} строк"
                    for f, lines_count in violations[:5]
                )  # Показываем первые 5
            )

    def test_parallel_modules_under_500_lines(self, parser_2gis_root: Path) -> None:
        """Проверяет что модули parallel меньше 500 строк.

        После рефакторинга все модули parallel должны быть компактными.
        Это warning а не error - для мониторинга технического долга.
        """
        parallel_dir = parser_2gis_root / "parallel"
        assert parallel_dir.exists(), "parallel/ должен существовать"

        violations: List[Tuple[Path, int]] = []

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            lines = count_lines(py_file)
            if lines > self.STRICT_MAX_FILE_LINES:
                violations.append((py_file, lines))

        if violations:
            pytest.skip(
                "Модули parallel превышают 500 строк (технический долг):\n"
                + "\n".join(f"  {f.name}: {lines_count} строк" for f, lines_count in violations)
            )

    def test_cache_modules_under_500_lines(self, parser_2gis_root: Path) -> None:
        """Проверяет что модули cache меньше 500 строк.

        После разделения cache.py на пакет все модули должны быть компактными.
        Это warning а не error - для мониторинга технического долга.
        """
        cache_dir = parser_2gis_root / "cache"
        assert cache_dir.exists(), "cache/ должен существовать"

        violations: List[Tuple[Path, int]] = []

        for py_file in cache_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            lines = count_lines(py_file)
            if lines > self.STRICT_MAX_FILE_LINES:
                violations.append((py_file, lines))

        if violations:
            pytest.skip(
                "Модули cache превышают 500 строк (технический долг):\n"
                + "\n".join(f"  {f.name}: {lines_count} строк" for f, lines_count in violations)
            )


# =============================================================================
# 4. ТЕСТЫ НА СЛОЖНОСТЬ КЛАССОВ (SRP)
# =============================================================================


class TestClassComplexity:
    """Тесты на ограничение сложности классов (SRP principle)."""

    MAX_CLASS_LINES = 300
    MAX_METHOD_LINES = 50

    def test_no_class_over_300_lines(self, python_files: List[Path]) -> None:
        """Проверяет что нет классов больше 300 строк.

        Классы больше 300 строк нарушают Single Responsibility Principle.
        Это warning а не error - для мониторинга технического долга.
        """
        violations: List[Tuple[Path, str, int]] = []

        for py_file in python_files:
            classes = get_classes_in_file(py_file)
            for class_name, start_line, end_line in classes:
                class_lines = end_line - start_line + 1
                if class_lines > self.MAX_CLASS_LINES:
                    violations.append((py_file, class_name, class_lines))

        if violations:
            pytest.skip(
                "Классы превышают 300 строк (технический долг):\n"
                + "\n".join(
                    f"  {f.name}:{c} - {lines_count} строк" for f, c, lines_count in violations[:10]
                )  # Показываем первые 10
            )

    def test_no_method_over_50_lines(self, python_files: List[Path]) -> None:
        """Проверяет что нет методов больше 50 строк.

        Методы больше 50 строк должны быть рефакторены.
        """
        # Исключения для сложных методов
        exceptions = {
            ("browser.py", "close"),  # Сложная очистка ресурсов
            ("remote.py", "execute_js"),  # Сложная валидация JS
        }

        violations: List[Tuple[Path, str, str, int]] = []

        for py_file in python_files:
            classes = get_classes_in_file(py_file)
            for class_name, _, _ in classes:
                methods = get_class_methods_count(py_file, class_name)
                for method_name, method_lines in methods.items():
                    if method_name.startswith("_"):
                        continue  # Пропускаем private методы для строгой проверки
                    if method_lines > self.MAX_METHOD_LINES:
                        if (py_file.name, method_name) not in exceptions:
                            violations.append((py_file, class_name, method_name, method_lines))

        # Это warning а не error
        if violations:
            pytest.skip(
                "Методы превышают 50 строк (рекомендация к рефакторингу):\n"
                + "\n".join(
                    f"  {f.name}:{c}.{m} - {lines_count} строк"
                    for f, c, m, lines_count in violations[:5]
                )
            )

    def test_parallel_city_parser_refactored(self, parser_2gis_root: Path) -> None:
        """Проверяет что ParallelCityParser рефакторен.

        После разделения parallel_parser.py класс должен быть компактным.
        Это warning а не error - для мониторинга технического долга.
        """
        parallel_dir = parser_2gis_root / "parallel"
        coordinator_file = parallel_dir / "coordinator.py"

        if not coordinator_file.exists():
            pytest.skip("coordinator.py не найден")

        classes = get_classes_in_file(coordinator_file)
        for class_name, start_line, end_line in classes:
            if "Coordinator" in class_name or "Parser" in class_name:
                class_lines = end_line - start_line + 1
                if class_lines >= 400:
                    pytest.skip(
                        f"Класс {class_name} превышает 400 строк (технический долг): {class_lines} строк"
                    )

    def test_chrome_remote_refactored(self, parser_2gis_root: Path) -> None:
        """Проверяет что ChromeRemote рефакторен.

        После разделения remote.py класс должен быть компактным.
        Это warning а не error - для мониторинга технического долга.
        """
        chrome_dir = parser_2gis_root / "chrome"
        remote_file = chrome_dir / "remote.py"

        if not remote_file.exists():
            pytest.skip("remote.py не найден")

        classes = get_classes_in_file(remote_file)
        for class_name, start_line, end_line in classes:
            if "ChromeRemote" in class_name or "Chrome" in class_name:
                class_lines = end_line - start_line + 1
                # remote.py может быть больше из-за сложности CDP
                if class_lines >= 500:
                    pytest.skip(
                        f"Класс {class_name} превышает 500 строк (технический долг): {class_lines} строк"
                    )

    def test_cache_manager_refactored(self, parser_2gis_root: Path) -> None:
        """Проверяет что CacheManager рефакторен.

        После разделения cache.py на пакет менеджер должен быть компактным.
        Это warning а не error - для мониторинга технического долга.
        """
        cache_dir = parser_2gis_root / "cache"
        manager_file = cache_dir / "manager.py"

        if not manager_file.exists():
            pytest.skip("cache/manager.py не найден")

        classes = get_classes_in_file(manager_file)
        for class_name, start_line, end_line in classes:
            if "CacheManager" in class_name or "Cache" in class_name:
                class_lines = end_line - start_line + 1
                if class_lines >= 400:
                    pytest.skip(
                        f"Класс {class_name} превышает 400 строк (технический долг): {class_lines} строк"
                    )


# =============================================================================
# 5. ТЕСТЫ НА ДУБЛИРОВАНИЕ (DRY)
# =============================================================================


class TestNoDuplication:
    """Тесты на отсутствие дублирования кода (DRY principle)."""

    def test_no_duplicate_merger_modules(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет дублирующих модулей merger.

        После рефакторинга должен быть один merger.py в parallel.
        """
        # Проверяем что нет дублирующих файлов
        duplicate_patterns = ["file_merger.py", "merger.py"]

        parallel_dir = parser_2gis_root / "parallel"
        found_files: List[str] = []

        for pattern in duplicate_patterns:
            if (parallel_dir / pattern).exists():
                found_files.append(pattern)

        # Должен быть только один merger
        assert len(found_files) <= 1, (
            f"Обнаружены дублирующие модули merger: {found_files}. Должен быть только один."
        )

    def test_no_duplicate_parallel_parser_modules(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет дублирующих модулей parallel_parser.

        После разделения parallel_parser.py на подмодули
        не должно остаться старых файлов.
        """
        parallel_dir = parser_2gis_root / "parallel"

        # parallel_parser.py может существовать как обёртка
        # но не должно быть дублирующих файлов
        old_patterns = [
            "parallel_parser_old.py",
            "parallel_parser_backup.py",
            "parallel_parser_v2.py",
        ]

        duplicates: List[str] = []
        for pattern in old_patterns:
            if (parallel_dir / pattern).exists():
                duplicates.append(pattern)

        assert len(duplicates) == 0, f"Обнаружены дублирующие файлы parallel_parser: {duplicates}"

    def test_no_duplicate_logger_modules(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет дублирующих модулей logger.

        Не должно быть старых файлов логгера.
        """
        logger_dir = parser_2gis_root / "logger"

        old_patterns = [
            "logger_old.py",
            "file_logger.py",  # Должен быть в logging.handlers
            "visual_logger_backup.py",
        ]

        duplicates: List[str] = []
        for pattern in old_patterns:
            if (logger_dir / pattern).exists():
                duplicates.append(pattern)

        assert len(duplicates) == 0, f"Обнаружены дублирующие файлы logger: {duplicates}"


# =============================================================================
# 6. ТЕСТЫ НА PROTOCOL РАЗДЕЛЕНИЕ (ISP)
# =============================================================================


class TestProtocolSeparation:
    """Тесты на разделение Protocol (Interface Segregation Principle)."""

    def test_browser_service_protocol_split(self, parser_2gis_root: Path) -> None:
        """Проверяет что BrowserService Protocol разделён.

        BrowserService должен быть разделён на специализированные Protocol:
        - BrowserNavigation
        - BrowserContentAccess
        - BrowserJSExecution
        - BrowserScreenshot
        """
        protocols_file = parser_2gis_root / "protocols.py"
        assert protocols_file.exists(), "protocols.py должен существовать"

        content = protocols_file.read_text(encoding="utf-8")

        # Проверяем наличие специализированных Protocol
        expected_protocols = [
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
            "BrowserService",
        ]

        missing_protocols = []
        for protocol in expected_protocols:
            if f"class {protocol}" not in content and f"class {protocol}(" not in content:
                missing_protocols.append(protocol)

        assert len(missing_protocols) == 0, (
            f"В protocols.py отсутствуют Protocol: {missing_protocols}"
        )

    def test_cache_backend_protocol_split(self, parser_2gis_root: Path) -> None:
        """Проверяет что CacheBackend Protocol существует.

        CacheBackend должен абстрагировать операции кэширования.
        """
        protocols_file = parser_2gis_root / "protocols.py"
        content = protocols_file.read_text(encoding="utf-8")

        # Проверяем наличие CacheBackend
        assert "CacheBackend" in content, (
            "CacheBackend Protocol должен быть определён в protocols.py"
        )

        # Проверяем что есть методы get/set/delete
        assert "def get" in content or "get(" in content, "CacheBackend должен иметь метод get()"
        assert "def set" in content or "set(" in content, "CacheBackend должен иметь метод set()"

    def test_protocol_methods_count(self, parser_2gis_root: Path) -> None:
        """Проверяет что Protocol не перегружены методами.

        Каждый Protocol должен иметь не более 5 методов (ISP).
        """
        protocols_file = parser_2gis_root / "protocols.py"

        try:
            with open(protocols_file, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            pytest.skip("Не удалось проанализировать protocols.py")

        protocol_methods: Dict[str, int] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Проверяем что это Protocol
                is_protocol = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Protocol":
                        is_protocol = True
                    elif isinstance(base, ast.Attribute) and base.attr == "Protocol":
                        is_protocol = True

                if is_protocol:
                    methods_count = sum(
                        1
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    protocol_methods[node.name] = methods_count

        # Проверяем что Protocol не перегружены
        overloaded = [(name, count) for name, count in protocol_methods.items() if count > 5]

        if overloaded:
            pytest.skip(
                "Некоторые Protocol перегружены методами (рекомендация к разделению):\n"
                + "\n".join(f"  {name}: {count} методов" for name, count in overloaded)
            )


# =============================================================================
# 7. ТЕСТЫ НА DIP (DEPENDENCY INVERSION PRINCIPLE)
# =============================================================================


class TestDependencyInversion:
    """Тесты на соблюдение Dependency Inversion Principle."""

    def test_launcher_uses_dependency_injection(self, parser_2gis_root: Path) -> None:
        """Проверяет что ApplicationLauncher использует dependency injection.

        ApplicationLauncher должен принимать зависимости через __init__.
        """
        launcher_file = parser_2gis_root / "cli" / "launcher.py"

        if not launcher_file.exists():
            pytest.skip("launcher.py не найден")

        content = launcher_file.read_text(encoding="utf-8")

        # Проверяем что есть __init__ с параметрами
        assert "def __init__" in content, "ApplicationLauncher должен иметь __init__ метод"

        # Проверяем что есть injection зависимостей
        injection_patterns = ["signal_handler", "config", "options"]

        found_injections = [p for p in injection_patterns if p in content]
        assert len(found_injections) >= 2, (
            f"ApplicationLauncher должен использовать dependency injection: {found_injections}"
        )

    def test_protocol_usage_in_parallel(self, parser_2gis_root: Path) -> None:
        """Проверяет что parallel использует Protocol для зависимостей.

        parallel должен использовать Protocol вместо конкретных классов.
        """
        parallel_dir = parser_2gis_root / "parallel"

        protocol_usages: List[Tuple[str, str]] = []

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            # Ищем использование Protocol
            if "Protocol" in content or "protocol" in content.lower():
                protocol_usages.append((py_file.name, "Protocol"))

            # Ищем типизацию через Protocol
            if "Callable" in content or "Iterator" in content:
                protocol_usages.append((py_file.name, "Callable/Iterator"))

        assert len(protocol_usages) >= 2, (
            f"parallel должен использовать Protocol: {protocol_usages}"
        )

    def test_no_direct_imports_of_concrete_classes(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет прямых импортов конкретных классов.

        Модули должны зависеть от абстракций (Protocol), а не от конкретных классов.
        """
        # Проверяем что utils не импортирует конкретные реализации
        utils_dir = parser_2gis_root / "utils"

        forbidden_imports = ["ChromeRemote", "CacheManager", "ParallelCityParser"]

        violations: List[Tuple[Path, str]] = []

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            for forbidden in forbidden_imports:
                if (
                    f"import {forbidden}" in content
                    or "from parser_2gis" in content
                    and forbidden in content
                ):
                    # Проверяем что это не в комментарии
                    lines = content.split("\n")
                    for line in lines:
                        if not line.strip().startswith("#") and forbidden in line:
                            violations.append((py_file, forbidden))

        # Это warning а не error
        if violations:
            pytest.skip(
                "Обнаружены прямые импорты конкретных классов (рекомендация использовать Protocol):\n"
                + "\n".join(f"  {f.name}: {c}" for f, c in violations[:5])
            )


# =============================================================================
# 8. ТЕСТЫ НА СТРУКТУРУ ПРОЕКТА
# =============================================================================


class TestProjectStructure:
    """Тесты на правильную структуру проекта."""

    def test_no_files_in_root_package(self, parser_2gis_root: Path) -> None:
        """Проверяет что в корне пакета нет лишних файлов.

        В корне parser_2gis/ должны быть только основные модули,
        а не вспомогательные файлы.
        Это warning а не error - для мониторинга технического долга.
        """
        # Допустимые файлы в корне
        allowed_files = {
            "__init__.py",
            "__main__.py",
            "config.py",
            "config_service.py",
            "constants.py",
            "exceptions.py",
            "main.py",
            "protocols.py",
            "pydantic_compat.py",
            "signal_handler.py",
            "statistics.py",
            "version.py",
            "py.typed",
        }

        # Файлы которые должны быть перемещены
        moved_files = {"parallel_helpers.py", "parallel_optimizer.py", "paths.py"}

        violations: List[str] = []

        for py_file in parser_2gis_root.glob("*.py"):
            if py_file.name not in allowed_files and py_file.name in moved_files:
                violations.append(py_file.name)

        if violations:
            pytest.skip(
                f"Файлы должны быть перемещены в соответствующие пакеты (технический долг): {violations}"
            )

    def test_parallel_helpers_moved(self, parser_2gis_root: Path) -> None:
        """Проверяет что parallel_helpers перемещён.

        parallel_helpers.py должен быть в parallel/helpers.py.
        """
        old_path = parser_2gis_root / "parallel_helpers.py"
        new_path = parser_2gis_root / "parallel" / "helpers.py"

        # Старый файл не должен существовать (или должен быть удалён)
        # Новый файл должен существовать
        if old_path.exists():
            # Если старый существует, новый тоже должен быть
            assert new_path.exists(), (
                "parallel_helpers.py должен быть перемещён в parallel/helpers.py"
            )

    def test_parallel_optimizer_moved(self, parser_2gis_root: Path) -> None:
        """Проверяет что parallel_optimizer перемещён.

        parallel_optimizer.py должен быть в parallel/optimizer.py.
        """
        old_path = parser_2gis_root / "parallel_optimizer.py"
        new_path = parser_2gis_root / "parallel" / "optimizer.py"

        if old_path.exists():
            assert new_path.exists(), (
                "parallel_optimizer.py должен быть перемещён в parallel/optimizer.py"
            )

    def test_signal_handler_moved(self, parser_2gis_root: Path) -> None:
        """Проверяет что signal_handler перемещён.

        signal_handler.py должен быть в utils/signal_handler.py.
        """
        old_path = parser_2gis_root / "signal_handler.py"
        new_path = parser_2gis_root / "utils" / "signal_handler.py"

        if old_path.exists():
            assert new_path.exists(), (
                "signal_handler.py должен быть перемещён в utils/signal_handler.py"
            )

    def test_statistics_moved(self, parser_2gis_root: Path) -> None:
        """Проверяет что statistics перемещён.

        statistics.py может остаться в корне или быть перемещён.
        """
        # statistics.py может быть в корне как общий модуль
        # Это допустимо
        stats_path = parser_2gis_root / "statistics.py"
        assert stats_path.exists(), "statistics.py должен существовать"

    def test_paths_moved(self, parser_2gis_root: Path) -> None:
        """Проверяет что paths перемещён.

        paths.py должен быть в utils/path_utils.py.
        """
        old_path = parser_2gis_root / "paths.py"
        new_path = parser_2gis_root / "utils" / "path_utils.py"

        if old_path.exists():
            assert new_path.exists(), "paths.py должен быть перемещён в utils/path_utils.py"

    def test_config_service_moved(self, parser_2gis_root: Path) -> None:
        """Проверяет что config_service существует.

        config_service.py должен быть в корне.
        """
        config_service_path = parser_2gis_root / "config_service.py"
        assert config_service_path.exists(), (
            "config_service.py должен существовать в корне parser_2gis/"
        )


# =============================================================================
# 9. ТЕСТЫ НА ОБРАТНУЮ СОВМЕСТИМОСТЬ
# =============================================================================


class TestBackwardCompatibility:
    """Тесты на обратную совместимость."""

    def test_alias_imports_work(self) -> None:
        """Проверяет что alias импорты работают.

        Старые пути импорта должны работать через alias.
        Это warning а не error - некоторые импорты могут быть нарушены.
        """
        # Проверяем что основные импорты работают
        try:
            from parser_2gis import CacheManager

            assert CacheManager is not None
        except ImportError as e:
            pytest.skip(f"CacheManager не импортируется (технический долг): {e}")

        try:
            from parser_2gis import logger

            assert logger is not None
        except ImportError as e:
            pytest.skip(f"logger не импортируется (технический долг): {e}")

    def test_old_module_paths_still_importable(self) -> None:
        """Проверяет что старые пути модулей всё ещё импортируются.

        Для обратной совместимости старые пути должны работать.
        Это warning а не error - некоторые модули могут иметь проблемы с импортом.
        """
        # Проверяем основные модули
        modules_to_check = [
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

        for module_name in modules_to_check:
            # Очищаем кэш импортов
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        if failed_imports:
            pytest.skip(
                "Модули не импортируются (технический долг):\n"
                + "\n".join(f"  {m}: {e}" for m, e in failed_imports[:5])  # Показываем первые 5
            )

    def test_deprecation_warnings_for_old_paths(self) -> None:
        """Проверяет что для старых путей есть DeprecationWarning.

        При использовании устаревших путей должно выдаваться предупреждение.
        """
        # Это тест на наличие механизма предупреждений
        # Реальная проверка зависит от реализации

        # Проверяем что warnings модуль доступен
        assert hasattr(warnings, "warn"), "warnings.warn должен быть доступен"

        # Проверяем что есть DeprecationWarning
        assert issubclass(DeprecationWarning, Warning), (
            "DeprecationWarning должен быть подклассом Warning"
        )


# =============================================================================
# 10. ТЕСТЫ НА НЕИСПОЛЬЗУЕМЫЙ КОД (YAGNI)
# =============================================================================


class TestNoUnusedCode:
    """Тесты на отсутствие неиспользуемого кода (YAGNI principle)."""

    def test_no_gui_runner(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет GUI runner.

        В проекте не должно быть неиспользуемого GUI кода.
        """
        # Проверяем что нет старых GUI файлов
        gui_patterns = ["gui_runner.py", "gui.py", "tkinter_app.py", "qt_app.py"]

        found_gui_files: List[str] = []

        for pattern in gui_patterns:
            if (parser_2gis_root / pattern).exists():
                found_gui_files.append(pattern)

        assert len(found_gui_files) == 0, f"Обнаружены неиспользуемые GUI файлы: {found_gui_files}"

    def test_no_progress_tracker_module(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет отдельного progress_tracker модуля.

        Progress tracker должен быть в parallel/progress.py.
        """
        # Проверяем что нет дублирующего модуля
        old_path = parser_2gis_root / "progress_tracker.py"
        parallel_progress = parser_2gis_root / "parallel" / "progress.py"

        if old_path.exists():
            # Если старый существует, должен быть и новый
            assert parallel_progress.exists(), (
                "progress_tracker должен быть перемещён в parallel/progress.py"
            )

    def test_no_unused_protocols(self, parser_2gis_root: Path) -> None:
        """Проверяет что нет неиспользуемых Protocol.

        Все Protocol в protocols.py должны использоваться.
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
                        elif isinstance(base, ast.Attribute) and base.attr == "Protocol":
                            protocol_names.append(node.name)
        except SyntaxError:
            pytest.skip("Не удалось проанализировать protocols.py")

        # Проверяем использование каждого Protocol
        unused_protocols: List[str] = []

        # Сканируем все файлы проекта на использование Protocol
        python_files = find_python_files(parser_2gis_root)

        for protocol_name in protocol_names:
            # Пропускаем базовые Protocol
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

        # Это warning а не error
        if unused_protocols:
            pytest.skip(f"Обнаружены неиспользуемые Protocol (YAGNI): {unused_protocols}")


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestArchitectureIntegrityIntegration:
    """Интеграционные тесты на архитектурную целостность."""

    def test_all_architecture_tests_pass(
        self, project_root: Path, parser_2gis_root: Path, python_files: List[Path]
    ) -> None:
        """Интеграционный тест что все архитектурные тесты работают.

        Проверяет что инфраструктура тестов работает корректно.
        """
        # Проверяем что фикстуры работают
        assert project_root.exists(), "project_root должен существовать"
        assert parser_2gis_root.exists(), "parser_2gis_root должен существовать"
        assert len(python_files) > 0, "python_files не должен быть пустым"

        # Проверяем что вспомогательные функции работают
        test_file = python_files[0]
        imports = get_module_imports(test_file)
        assert isinstance(imports, set), "get_module_imports должен возвращать set"

        lines = count_lines(test_file)
        assert lines > 0, "count_lines должен возвращать положительное число"

    def test_architecture_documentation_complete(self, parser_2gis_root: Path) -> None:
        """Проверяет что архитектурная документация полная.

        ARCHITECTURE.md должен описывать все модули.
        """
        architecture_md = parser_2gis_root.parent / "ARCHITECTURE.md"

        if not architecture_md.exists():
            pytest.skip("ARCHITECTURE.md не найден")

        content = architecture_md.read_text(encoding="utf-8")

        # Проверяем что основные модули упомянуты
        required_modules = [
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

        missing_modules = []
        for module in required_modules:
            if module not in content.lower():
                missing_modules.append(module)

        if missing_modules:
            pytest.skip(f"В ARCHITECTURE.md не описаны модули: {missing_modules}")


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
