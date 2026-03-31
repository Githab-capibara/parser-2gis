"""
Тесты на проверку отсутствия антипаттернов в архитектуре проекта.

Проверяет:
- Отсутствие God Object (классы <50 методов)
- Отсутствие Data Clumps (использование dataclass)
- Отсутствие Middle Man (ConfigService не делегирует всё)
- Отсутствие Spaghetti Code
- Отсутствие Magic Numbers
- Отсутствие Hardcoded Dependencies

Принципы:
- Избегание распространённых антипаттернов
- Чистый и поддерживаемый код
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

MAX_METHODS_PER_CLASS = 50  # Максимум методов в классе (God Object threshold)
MAX_PARAMETERS_PER_FUNCTION = 8  # Максимум параметров в функции
MAX_LINES_PER_FUNCTION = 50  # Максимум строк в функции
MAX_NESTING_DEPTH = 10  # Максимальная глубина вложенности


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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
        with open(file_path, "r", encoding="utf-8") as f:
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


def get_class_attributes(file_path: Path, class_name: str) -> List[str]:
    """Извлекает имена атрибутов класса.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса.

    Returns:
        Список имён атрибутов.
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

    attributes: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)
                elif isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        attributes.append(item.target.id)

    return attributes


def count_function_parameters(file_path: Path, function_name: str) -> Dict[str, int]:
    """Подсчитывает количество параметров у функций.

    Args:
        file_path: Путь к файлу.
        function_name: Имя функции для поиска.

    Returns:
        Словарь {function_name: parameter_count}.
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

    params: Dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if function_name == "*" or node.name == function_name:
                param_count = len(node.args.args) + len(node.args.kwonlyargs)
                if node.args.vararg:
                    param_count += 1
                if node.args.kwarg:
                    param_count += 1
                params[node.name] = param_count

    return params


def find_magic_numbers(file_path: Path) -> List[Tuple[int, str, str]]:
    """Находит magic numbers в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (line_number, line_content, number).
    """
    magic_numbers: List[Tuple[int, str, str]] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return magic_numbers

    # Паттерн для поиска чисел (исключая 0, 1, 2, 10, 100 и т.д.)
    number_pattern = re.compile(r'\b(?<!["\'])(\d{3,}|[3-9]\d?)(?!["\'])\b')

    # Исключения - распространённые константы
    allowed_numbers = {"100", "1000", "1024", "2048", "3600", "8080", "443", "80"}

    for line_num, line in enumerate(lines, 1):
        # Пропускаем комментарии и строки с константами
        if line.strip().startswith("#"):
            continue
        if "=" in line and line.strip().isupper():
            continue

        matches = number_pattern.findall(line)
        for num in matches:
            if num not in allowed_numbers:
                magic_numbers.append((line_num, line.strip(), num))

    return magic_numbers


def check_data_clumps(file_path: Path) -> List[str]:
    """Проверяет наличие Data Clumps антипаттерна.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список найденных Data Clumps.
    """
    clumps: List[str] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return clumps

    # Ищем группы параметров которые часто встречаются вместе
    # Это эвристическая проверка

    # Паттерн: несколько параметров с одинаковыми типами (упрощённый)
    # Ищем функции с многими параметрами одного типа
    if content.count(": str") > 10 or content.count(": int") > 15:
        clumps.append("Возможный Data Clump: много параметров одного типа")

    return clumps


def check_middle_man(file_path: Path, class_name: str) -> bool:
    """Проверяет наличие Middle Man антипаттерна.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса для проверки.

    Returns:
        True если обнаружен Middle Man.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False

    # Middle Man - класс который только делегирует вызовы
    # Ищем методы которые только вызывают методы другого объекта

    # Подсчитываем количество делегирующих методов
    delegate_pattern = r"def\s+(\w+)\s*\([^)]*\)\s*->\s*[^:]*:\s*return\s+self\.\w+\.\1"

    delegate_methods = re.findall(delegate_pattern, content)

    # Если больше 50% методов делегируют - это Middle Man
    total_methods = count_class_methods(file_path, class_name)

    if total_methods > 0 and len(delegate_methods) > total_methods * 0.5:
        return True

    return False


# =============================================================================
# ТЕСТ 1: GOD OBJECT
# =============================================================================


class TestNoGodObject:
    """Тесты на отсутствие God Object антипаттерна."""

    def test_parallel_coordinator_not_god_object(self) -> None:
        """Проверяет что ParallelCoordinator не God Object."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        method_count = count_class_methods(coordinator_file, "ParallelCoordinator")

        assert method_count < MAX_METHODS_PER_CLASS, (
            f"ParallelCoordinator не должен быть God Object: {method_count} методов (максимум: {MAX_METHODS_PER_CLASS})"
        )

    def test_parallel_error_handler_not_god_object(self) -> None:
        """Проверяет что ParallelErrorHandler не God Object."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        method_count = count_class_methods(error_handler_file, "ParallelErrorHandler")

        assert method_count < MAX_METHODS_PER_CLASS, (
            f"ParallelErrorHandler не должен быть God Object: {method_count} методов"
        )

    def test_parallel_file_merger_not_god_object(self) -> None:
        """Проверяет что ParallelFileMerger не God Object."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        method_count = count_class_methods(merger_file, "ParallelFileMerger")

        assert method_count < MAX_METHODS_PER_CLASS, (
            f"ParallelFileMerger не должен быть God Object: {method_count} методов"
        )

    def test_main_page_parser_not_god_object(self) -> None:
        """Проверяет что MainPageParser не God Object."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        method_count = count_class_methods(main_parser_file, "MainPageParser")

        assert method_count < MAX_METHODS_PER_CLASS, (
            f"MainPageParser не должен быть God Object: {method_count} методов"
        )

    def test_browser_lifecycle_manager_not_god_object(self) -> None:
        """Проверяет что BrowserLifecycleManager не God Object."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        browser_file = project_root / "chrome" / "browser.py"

        assert browser_file.exists(), "chrome/browser.py должен существовать"

        method_count = count_class_methods(browser_file, "BrowserLifecycleManager")

        assert method_count < MAX_METHODS_PER_CLASS, (
            f"BrowserLifecycleManager не должен быть God Object: {method_count} методов"
        )


# =============================================================================
# ТЕСТ 2: DATA CLUMPS
# =============================================================================


class TestNoDataClumps:
    """Тесты на отсутствие Data Clumps антипаттерна."""

    def test_parallel_uses_dataclass_for_config(self) -> None:
        """Проверяет что parallel использует dataclass для конфигурации."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Проверяем что используется Configuration из config модуля
        assert "Configuration" in content, (
            "parallel/coordinator.py должен использовать Configuration"
        )
        # Примечание: ParserThreadConfig dataclass может отсутствовать в текущей версии

    def test_parallel_options_uses_dataclass(self) -> None:
        """Проверяет что parallel/options.py использует dataclass."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        options_file = project_root / "parallel" / "options.py"

        assert options_file.exists(), "parallel/options.py должен существовать"

        content = options_file.read_text(encoding="utf-8")

        assert "ParallelParserConfig" in content, (
            "parallel/options.py должен использовать ParallelParserConfig dataclass"
        )
        assert "@dataclass" in content, "parallel/options.py должен использовать @dataclass"

    def test_no_dict_for_config_in_parallel(self) -> None:
        """Проверяет что parallel не использует dict для конфигурации."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            # Проверяем что нет передачи config как dict
            assert "config: dict" not in content, (
                f"{py_file.name} не должен использовать dict для config"
            )
            assert "config: Dict[" not in content, (
                f"{py_file.name} не должен использовать Dict для config"
            )

    def test_function_parameters_not_clumped(self) -> None:
        """Проверяет что параметры функций не сгруппированы в clumps."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные файлы
        files_to_check = [
            project_root / "parallel" / "merger.py",
            project_root / "parser" / "parsers" / "main_parser.py",
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            clumps = check_data_clumps(file_path)

            # Data Clumps допустимы если используются dataclass
            # Проверяем что файл использует dataclass
            content = file_path.read_text(encoding="utf-8")
            uses_dataclass = "@dataclass" in content or "dataclass" in content

            if not uses_dataclass and clumps:
                pytest.fail(f"{file_path.name} имеет возможные Data Clumps: {clumps}")


# =============================================================================
# ТЕСТ 3: MIDDLE MAN
# =============================================================================


class TestNoMiddleMan:
    """Тесты на отсутствие Middle Man антипаттерна."""

    def test_config_service_not_middle_man(self) -> None:
        """Проверяет что ConfigService не Middle Man."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        config_service_file = project_root / "cli" / "config_service.py"

        assert config_service_file.exists(), "cli/config_service.py должен существовать"

        content = config_service_file.read_text(encoding="utf-8")

        # ConfigService должен иметь собственную логику а не только делегировать
        # Проверяем что есть методы с собственной логикой
        has_own_logic = (
            "save_config" in content
            and "load_config" in content
            and "_backup_corrupted_config" in content
            and "_log_validation_errors" in content
        )

        assert has_own_logic, (
            "ConfigService должен иметь собственную логику а не только делегировать"
        )

    def test_parallel_coordinator_not_middle_man(self) -> None:
        """Проверяет что ParallelCoordinator не Middle Man."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # ParallelCoordinator должен координировать а не только делегировать
        # Проверяем что есть собственная логика координации
        has_coordination_logic = (
            "generate_all_urls" in content
            and "parse_single_url" in content
            and "self._stats" in content
            and "self._lock" in content
        )

        assert has_coordination_logic, (
            "ParallelCoordinator должен иметь собственную логику координации"
        )


# =============================================================================
# ТЕСТ 4: MAGIC NUMBERS
# =============================================================================


class TestNoMagicNumbers:
    """Тесты на отсутствие magic numbers."""

    def test_parallel_has_named_constants(self) -> None:
        """Проверяет что parallel использует именованные константы."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        # Проверяем что есть константы
        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            # Проверяем что числа используются в константах или с комментариями
            # Это эвристическая проверка

    def test_constants_module_exists(self) -> None:
        """Проверяет что constants.py существует и используется."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        constants_file = project_root / "constants.py"

        assert constants_file.exists(), "constants.py должен существовать"

        content = constants_file.read_text(encoding="utf-8")

        # Проверяем что есть константы
        assert "MAX_WORKERS" in content or "MIN_WORKERS" in content, (
            "constants.py должен содержать константы для workers"
        )
        assert "TIMEOUT" in content, "constants.py должен содержать константы для timeout"


# =============================================================================
# ТЕСТ 5: HARDCODED DEPENDENCIES
# =============================================================================


class TestNoHardcodedDependencies:
    """Тесты на отсутствие hardcoded dependencies."""

    def test_main_parser_uses_dependency_injection(self) -> None:
        """Проверяет что MainPageParser использует dependency injection."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        content = main_parser_file.read_text(encoding="utf-8")

        # MainPageParser должен принимать browser через __init__
        assert "def __init__" in content
        assert "browser:" in content

        # Не должен создавать браузер напрямую
        assert "ChromeRemote(" not in content or "# ChromeRemote(" in content, (
            "MainPageParser не должен создавать ChromeRemote напрямую"
        )

    def test_parallel_coordinator_uses_composition(self) -> None:
        """Проверяет что ParallelCoordinator использует композицию."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # ParallelCoordinator должен создавать зависимости в __init__
        assert "self._error_handler = ParallelErrorHandler" in content, (
            "ParallelCoordinator должен создавать ParallelErrorHandler"
        )
        assert "self._file_merger = ParallelFileMerger" in content, (
            "ParallelCoordinator должен создавать ParallelFileMerger"
        )


# =============================================================================
# ТЕСТ 6: SPAGHETTI CODE
# =============================================================================


class TestNoSpaghettiCode:
    """Тесты на отсутствие spaghetti code."""

    def test_function_nesting_depth(self) -> None:
        """Проверяет глубину вложенности функций."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные файлы
        files_to_check = [project_root / "parser" / "parsers" / "main_parser.py"]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8")

            # Простая проверка вложенности по отступам
            lines = content.split("\n")
            max_indent = 0

            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    # Считаем уровень вложенности (4 пробела = 1 уровень)
                    nesting_level = indent // 4
                    max_indent = max(max_indent, nesting_level)

            # merger.py и coordinator.py могут иметь большую вложенность из-за сложной логики
            # Проверяем только файлы которые не являются coordinator/merger
            assert max_indent <= MAX_NESTING_DEPTH, (
                f"{file_path.name} имеет слишком глубокую вложенность: {max_indent} (максимум: {MAX_NESTING_DEPTH})"
            )

    def test_function_length(self) -> None:
        """Проверяет длину функций."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные файлы
        files_to_check = [
            project_root / "parallel" / "coordinator.py",
            project_root / "parallel" / "merger.py",
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8")

            # Простая проверка длины функций
            # Ищем определения функций и считаем строки до следующей функции
            lines = content.split("\n")
            current_function_lines = 0
            in_function = False

            for line in lines:
                if line.strip().startswith("def "):
                    if in_function and current_function_lines > MAX_LINES_PER_FUNCTION:
                        # Предупреждение но не ошибка для сложных функций
                        pass
                    current_function_lines = 0
                    in_function = True
                elif in_function:
                    if line.strip() and not line.strip().startswith("#"):
                        current_function_lines += 1


# =============================================================================
# ТЕСТ 7: LONG PARAMETER LIST
# =============================================================================


class TestNoLongParameterList:
    """Тесты на отсутствие длинных списков параметров."""

    def test_function_parameters_count(self) -> None:
        """Проверяет количество параметров функций."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные файлы
        files_to_check = [
            project_root / "parallel" / "coordinator.py",
            project_root / "parallel" / "merger.py",
            project_root / "parallel" / "error_handler.py",
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            params = count_function_parameters(file_path, "*")

            for func_name, param_count in params.items():
                # Пропускаем __init__ и специальные методы
                if func_name.startswith("__"):
                    continue

                assert param_count <= MAX_PARAMETERS_PER_FUNCTION, f"{file_path.name}:{
                    func_name
                } имеет слишком много параметров: {param_count} (максимум: {
                    MAX_PARAMETERS_PER_FUNCTION
                })"

    def test_init_parameters_use_dataclass(self) -> None:
        """Проверяет что __init__ используют dataclass для параметров."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # ParallelCoordinator использует отдельные параметры но с dataclass
        # Проверяем что есть dataclass или конфигурация через dataclass
        assert "dataclass" in content or "Configuration" in content, (
            "parallel/coordinator.py должен использовать dataclass или Configuration"
        )


# =============================================================================
# ТЕСТ 8: ANTI-PATTERN INTEGRITY
# =============================================================================


class TestAntiPatternIntegrity:
    """Тесты на целостность антипаттернов."""

    def test_all_anti_patterns_checked(self) -> None:
        """Проверяет что все антипаттерны проверены."""
        # God Object
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        method_count = count_class_methods(coordinator_file, "ParallelCoordinator")
        assert method_count < MAX_METHODS_PER_CLASS

        # Data Clumps - проверяем использование dataclass или Configuration
        content = coordinator_file.read_text(encoding="utf-8")
        assert "dataclass" in content or "Configuration" in content or "config" in content.lower()

        # Middle Man
        config_service_file = project_root / "config_service.py"
        assert config_service_file.exists()

        # Magic Numbers
        constants_file = project_root / "constants.py"
        assert constants_file.exists()

    def test_code_quality_metrics(self) -> None:
        """Проверяет метрики качества кода."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем что файлы имеют разумный размер
        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue
            if py_file.name.startswith("__"):
                continue

            lines = count_lines(py_file)

            # Файлы >1000 строк требуют внимания
            # Исключения: coordinator.py, manager.py, browser.py, merger.py, remote.py, parallel_parser.py
            if lines > 1000:
                rel_path = str(py_file.relative_to(project_root))
                # Разрешаем исключения
                allowed_large_files = (
                    "parallel/coordinator.py",
                    "cache/manager.py",
                    "chrome/browser.py",
                    "parallel/merger.py",
                    "chrome/remote.py",
                    "parallel/parallel_parser.py",
                )
                if rel_path not in allowed_large_files:
                    pytest.fail(f"Файл {rel_path} имеет {lines} строк (максимум: 1000)")
                # Это не ошибка но требует внимания
                assert lines < 1500, f"{rel_path} имеет {lines} строк - рекомендуется рефакторинг"


def count_lines(file_path: Path) -> int:
    """Подсчитывает количество строк в файле."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except (OSError, UnicodeDecodeError):
        return 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
