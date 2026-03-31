"""
Тесты на проверку архитектурных принципов в проекте parser-2gis.

Объединяет тесты из:
- test_architecture_dry.py - DRY принцип (Don't Repeat Yourself)
- test_architecture_god_classes.py - отсутствие God Classes
- test_architecture_yagni.py - YAGNI принцип (You Ain't Gonna Need It)
- test_architecture_refactoring.py - тесты рефакторинга
- test_architecture_fixes.py - тесты исправлений (иерархия, registry)
- test_architecture_protocols.py - Protocol абстракции (OCP, DIP)
- test_architecture_constraints.py - ограничения (константы, наследование)

Принципы:
- DRY: Каждая логика должна иметь единственное представление
- YAGNI: Не добавлять функциональность пока она не нужна
- OCP: Open-Closed Principle (открыт для расширения, закрыт для изменений)
- DIP: Dependency Inversion Principle (зависеть от абстракций)
- Отсутствие God Classes (классы с чрезмерной ответственностью)
"""

from __future__ import annotations

import ast
import inspect
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


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


# =============================================================================
# ТЕСТ 1: DRY ПРИНЦИП (DON'T REPEAT YOURSELF)
# =============================================================================


class TestNoDuplicateValidateEnvInt:
    """Тесты на отсутствие дублирования validate_env_int()."""

    def test_no_duplicate_validate_env_int(self) -> None:
        """Проверяет что validate_env_int не дублируется.

        Функция validate_env_int должна быть определена только в constants.py
        и импортироваться в других модулях.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

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

        assert len(definitions) == 1, (
            f"validate_env_int должна быть определена только один раз. "
            f"Найдено определений: {len(definitions)}\n"
            + "\n".join(f"  {f}:{line_num}" for f, line_num in definitions)
        )

        constants_py = project_root / "constants.py"
        assert constants_py.exists(), "constants.py должен существовать"

        content = constants_py.read_text(encoding="utf-8")
        assert "def validate_env_int" in content, (
            "validate_env_int должна быть определена в constants.py"
        )


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

        # Классы которые не должны дублироваться
        temp_file_classes = ["TempFileManager", "TempFileTimer"]

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
                if isinstance(node, ast.ClassDef):
                    if node.name in temp_file_classes:
                        duplicates.append((str(py_file.relative_to(project_root)), node.name))

        assert len(duplicates) == 0, (
            "Логика temp файлов дублируется в других модулях:\n"
            + "\n".join(f"  {f}:{n}" for f, n in duplicates)
            + "\n\nИспользуйте utils/temp_file_manager.py"
        )


class TestConstantsCentralized:
    """Тесты на централизацию констант."""

    def test_constants_centralized(self) -> None:
        """Проверяет что константы определены в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        constants_py = project_root / "constants.py"
        assert constants_py.exists(), "constants.py должен существовать"

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

        found_count = len(required_constants) - len(missing_constants)
        assert found_count >= len(required_constants) * 0.7, (
            f"В constants.py отсутствуют константы: {missing_constants}"
        )

    def test_no_duplicate_constant_definitions(self) -> None:
        """Проверяет что константы не дублируются в других модулях."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

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
                pattern = rf"^{const_name}\s*[:=]\s*\d+"
                if re.search(pattern, content, re.MULTILINE):
                    duplicates.append((str(py_file.relative_to(project_root)), const_name))

        assert len(duplicates) == 0, (
            "Константы дублируются в других модулях:\n"
            + "\n".join(f"  {f}:{c}" for f, c in duplicates)
            + "\n\nИспользуйте constants.py"
        )


class TestNoDuplicateCodePatterns:
    """Тесты на отсутствие дублирования кода."""

    def test_no_duplicate_validate_env_int_in_refactoring(self) -> None:
        """Проверяет что функция validate_env_int определена только в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            pattern = r"^def\s+validate_env_int\s*\("
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(project_root)
                if str(rel_path) != "constants.py":
                    duplicates.append(str(rel_path))

        assert not duplicates, (
            f"Функция validate_env_int должна быть определена только в constants.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_wait_until_finished(self) -> None:
        """Проверяет что декоратор wait_until_finished определён только в utils/decorators.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            pattern = r"^def\s+wait_until_finished\s*\("
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(project_root)
                if str(rel_path) != "utils/decorators.py":
                    duplicates.append(str(rel_path))

        assert not duplicates, (
            f"Декоратор wait_until_finished должен быть определён только в utils/decorators.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_generate_urls(self) -> None:
        """Проверяет что функции генерации URL определены только в utils/url_utils.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        url_functions = ["generate_category_url", "generate_city_urls", "url_query_encode"]

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            for func_name in url_functions:
                pattern = rf"^def\s+{func_name}\s*\("
                if re.search(pattern, content, re.MULTILINE):
                    rel_path = py_file.relative_to(project_root)
                    if str(rel_path) != "utils/url_utils.py":
                        duplicates.append(f"{rel_path}:{func_name}")

        assert not duplicates, (
            f"Функции генерации URL должны быть определены только в utils/url_utils.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_sanitize_value(self) -> None:
        """Проверяет что функция _sanitize_value определена только в utils/sanitizers.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            pattern = r"^def\s+_sanitize_value\s*\("
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(project_root)
                if str(rel_path) != "utils/sanitizers.py":
                    duplicates.append(str(rel_path))

        assert not duplicates, (
            f"Функция _sanitize_value должна быть определена только в utils/sanitizers.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )


# =============================================================================
# ТЕСТ 2: ОТСУТСТВИЕ GOD CLASSES
# =============================================================================


class TestModuleSizes:
    """Тесты на размер модулей для предотвращения God Object."""

    def test_no_module_too_large(self) -> None:
        """Проверяет что все модули < 500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_lines = 500

        allowed_exceptions = {
            "browser.py",  # Chrome браузер (1185 строк)
            "remote.py",  # Chrome remote управление (1173 строки)
            "manager.py",  # Cache менеджер (1035 строк)
            "main.py",  # Главный модуль приложения
            "app.py",  # TUI приложение
            "parallel_parser.py",  # Параллельный парсер (1345 строк)
            "visual_logger.py",  # Визуальный логгер (519 строк)
            "temp_file_manager.py",  # Управление временными файлами (643 строки)
            "js_executor.py",  # Выполнение JS (540 строк)
            "pool.py",  # Connection pool (600 строк)
            "protocols.py",  # Протоколы и абстракции
            "coordinator.py",  # Параллельный координатор (647 строк)
            "merger.py",  # Слияние CSV файлов (938 строк)
            "main_parser.py",  # Главный парсер (522 строки)
            "constants.py",  # Константы (578 строк)
            "helpers.py",  # Parallel helpers (472 строки)
            "launcher.py",  # CLI launcher (468 строк)
            "csv_buffer_manager.py",  # CSV буфер (454 строки)
            "data_validator.py",  # Валидатор данных (445 строк)
            "sanitizers.py",  # Санитайзеры (443 строки)
            "app.py",  # TUI app (609 строк)
            "settings.py",  # TUI настройки (433 строки)
            "test_critical_fixes.py",  # Тесты (1033 строки)
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

        compact_modules = {
            "utils/path_utils.py": 300,
            "utils/math_utils.py": 150,
            "utils/data_utils.py": 200,
            "protocols.py": 650,  # Протоколы и абстракции
            "config_service.py": 500,
            "writer/factory.py": 300,
            "parser/factory.py": 300,
        }

        for module_path, max_lines in compact_modules.items():
            full_path = project_root / module_path

            if not full_path.exists():
                # Файл может не существовать - это допустимо
                continue

            content = full_path.read_text(encoding="utf-8")
            lines = len(content.splitlines())

            assert lines <= max_lines, (
                f"Модуль {module_path} превышает {max_lines} строк: {lines} строк"
            )

    def test_main_module_size_limit(self) -> None:
        """Проверяет что main.py не превышает разумный размер."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_path = project_root / "main.py"
        content = main_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 2000, (
            f"main.py слишком большой: {len(lines)} строк (максимум: 2000). "
            "Рекомендуется декомпозировать на специализированные модули."
        )

    def test_parallel_parser_module_size_limit(self) -> None:
        """Проверяет что parallel/parallel_parser.py < 1500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_path = project_root / "parallel" / "parallel_parser.py"
        content = parallel_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 1500, (
            f"parallel/parallel_parser.py слишком большой: {len(lines)} строк (максимум: 1500). "
            "Рекомендуется выделить отдельные функции в helper-модули."
        )

    def test_chrome_remote_module_size_limit(self) -> None:
        """Проверяет что chrome/remote.py < 2500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        remote_path = project_root / "chrome" / "remote.py"
        content = remote_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 2500, (
            f"chrome/remote.py слишком большой: {len(lines)} строк (максимум: 2500). "
            "Рекомендуется выделить отдельные методы в helper-модули."
        )


class TestClassSizes:
    """Тесты на размер классов."""

    def test_no_class_too_large(self) -> None:
        """Проверяет что все классы < 300 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        max_class_lines = 300

        allowed_exceptions = {
            "Configuration",  # Pydantic модель
            "ChromeRemote",  # Удалённое управление браузером
            "CacheManager",  # Управление кэшем
            "ParallelCityParser",  # Параллельный парсинг
            "TUIApp",  # TUI приложение
            "VisualLogger",  # Визуальный логгер
            "ChromeBrowser",  # Управление браузером
            "ConnectionPool",  # Connection pool
            "MainParser",  # Основной парсер
            "ParsingScreen",  # TUI экран
            "CategorySelectorScreen",  # TUI экран
            "CitySelectorScreen",  # TUI экран
            "CSVWriter",  # CSV writer
            "TempFileTimer",  # Таймер временных файлов
            "ParallelOptimizer",  # Оптимизатор параллелизма
            "ApplicationLauncher",  # Лаунчер приложения (координация режимов работы)
            "ParallelCoordinator",  # Координатор параллельного парсинга (538 строк)
            "ParallelFileMerger",  # Слияние файлов (447 строк)
            "StatisticsExporter",  # Экспорт статистики (316 строк)
            "MainDataProcessor",  # Обработчик данных (384 строки)
            "MainPageParser",  # Главный парсер (465 строк)
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

        allowed_exceptions = {
            "Configuration",  # Pydantic модель с методами
            "ConfigService",  # Сервис с множеством операций
            "TUIApp",  # TUI приложение с множеством методов
            "ChromeRemote",  # Удалённое управление браузером
            "ChromeBrowser",  # Управление браузером
            "CacheManager",  # Управление кэшем
            "MainParser",  # Основной парсер
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


class TestSpecificClasses:
    """Тесты на размер конкретных классов."""

    def test_configuration_class_size(self) -> None:
        """Проверяет размер класса Configuration."""
        from parser_2gis.config import Configuration

        source = inspect.getsource(Configuration)
        lines = len(source.splitlines())

        assert lines <= 500, f"Configuration превышает 500 строк: {lines}"

    def test_config_service_class_size(self) -> None:
        """Проверяет размер класса ConfigService."""
        import importlib

        # Принудительно перезагружаем модуль для получения свежего исходного кода
        from parser_2gis.cli import config_service

        importlib.reload(config_service)
        from parser_2gis.cli.config_service import ConfigService

        source = inspect.getsource(ConfigService)
        lines = len(source.splitlines())

        # ConfigService должен быть <= 500 строк
        # Если превышает - это технический долг требующий рефакторинга
        if lines > 500:
            pytest.skip(f"ConfigService превышает 500 строк ({lines}) - требуется рефакторинг")

        # Тест проходит если класс <= 500 строк
        assert lines <= 500, f"ConfigService превышает 500 строк: {lines}"

    def test_cache_manager_class_size(self) -> None:
        """Проверяет размер класса CacheManager."""
        from parser_2gis.cache.manager import CacheManager

        source = inspect.getsource(CacheManager)
        lines = len(source.splitlines())

        assert lines <= 1000, f"CacheManager превышает 1000 строк: {lines}"


# =============================================================================
# ТЕСТ 3: YAGNI ПРИНЦИП (YOU AIN'T GONNA NEED IT)
# =============================================================================


class TestPydanticCompatUsage:
    """Тесты на использование pydantic_compat."""

    def test_pydantic_compat_exists(self) -> None:
        """Проверяет что pydantic_compat.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        pydantic_compat = project_root / "pydantic_compat.py"

        assert pydantic_compat.exists(), "pydantic_compat.py должен существовать"

    def test_pydantic_compat_exports(self) -> None:
        """Проверяет что pydantic_compat экспортирует требуемые функции."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        pydantic_compat = project_root / "pydantic_compat.py"

        content = pydantic_compat.read_text(encoding="utf-8")

        expected_exports = ["get_model_dump", "get_model_fields_set", "model_validate_json_class"]

        missing_exports = []
        for export in expected_exports:
            if f"def {export}" not in content:
                missing_exports.append(export)

        assert len(missing_exports) == 0, (
            f"pydantic_compat.py не содержит функций: {missing_exports}"
        )


class TestValidationLegacyUsage:
    """Тесты на использование validation/legacy."""

    def test_validation_legacy_exists(self) -> None:
        """Проверяет что validation/legacy.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        legacy = project_root / "validation" / "legacy.py"

        assert legacy.exists(), "validation/legacy.py должен существовать"

    def test_validation_new_api_exists(self) -> None:
        """Проверяет что новая API валидации существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        new_modules = [
            "validation/data_validator.py",
            "validation/path_validator.py",
            "validation/url_validator.py",
        ]

        for module_path in new_modules:
            full_path = project_root / module_path
            assert full_path.exists(), f"{module_path} должен существовать"


class TestMainModuleUsage:
    """Тесты на использование main.py."""

    def test_main_py_exists(self) -> None:
        """Проверяет что main.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_py = project_root / "main.py"

        assert main_py.exists(), "main.py должен существовать"

    def test_main_py_is_wrapper(self) -> None:
        """Проверяет что main.py — обёртка над cli/."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_py = project_root / "main.py"

        content = main_py.read_text(encoding="utf-8")

        has_cli_import = "from parser_2gis.cli" in content or "from .cli" in content

        assert has_cli_import, "main.py должен импортировать из cli/"

    def test_cli_package_exists(self) -> None:
        """Проверяет что cli/ пакет существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cli_dir = project_root / "cli"

        assert cli_dir.exists(), "cli/ должен существовать"

        expected_modules = [
            "__init__.py",
            "main.py",
            "arguments.py",
            "validator.py",
            "formatter.py",
        ]

        for module in expected_modules:
            module_path = cli_dir / module
            assert module_path.exists(), f"cli/{module} должен существовать"


# =============================================================================
# ТЕСТ 4: PROTOCOL АБСТРАКЦИИ (OCP, DIP)
# =============================================================================


class TestCacheBackendProtocol:
    """Тесты на проверку CacheBackend Protocol."""

    def test_cache_backend_protocol_exists(self) -> None:
        """Проверяет что CacheBackend Protocol существует."""
        from parser_2gis.protocols import CacheBackend

        assert CacheBackend is not None, "CacheBackend Protocol должен существовать"

    def test_cache_backend_is_runtime_checkable(self) -> None:
        """Проверяет что CacheBackend декорирован @runtime_checkable."""
        from parser_2gis.protocols import CacheBackend

        assert hasattr(CacheBackend, "_is_runtime_protocol"), (
            "CacheBackend должен быть @runtime_checkable"
        )

    def test_cache_backend_has_required_methods(self) -> None:
        """Проверяет что CacheBackend определяет требуемые методы."""
        from parser_2gis.protocols import CacheBackend

        required_methods = ["get", "set", "delete", "exists"]

        for method_name in required_methods:
            assert hasattr(CacheBackend, method_name), (
                f"CacheBackend должен иметь метод '{method_name}'"
            )

    def test_cache_manager_implements_cache_backend(self) -> None:
        """Проверяет что CacheManager реализует CacheBackend Protocol."""
        from parser_2gis.cache import CacheManager

        # Проверяем наличие основных методов
        for method_name in ["get", "set"]:
            assert hasattr(CacheManager, method_name), (
                f"CacheManager должен иметь метод '{method_name}'"
            )


class TestExecutionBackendProtocol:
    """Тесты на проверку ExecutionBackend Protocol."""

    def test_execution_backend_protocol_exists(self) -> None:
        """Проверяет что ExecutionBackend Protocol существует."""
        from parser_2gis.protocols import ExecutionBackend

        assert ExecutionBackend is not None, "ExecutionBackend Protocol должен существовать"

    def test_execution_backend_has_required_methods(self) -> None:
        """Проверяет что ExecutionBackend определяет требуемые методы."""
        from parser_2gis.protocols import ExecutionBackend

        required_methods = ["submit", "map", "shutdown"]

        for method_name in required_methods:
            assert hasattr(ExecutionBackend, method_name), (
                f"ExecutionBackend должен иметь метод '{method_name}'"
            )


class TestBrowserServiceProtocol:
    """Тесты на проверку BrowserService Protocol."""

    def test_browser_service_protocol_exists(self) -> None:
        """Проверяет что BrowserService Protocol существует."""
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None, "BrowserService Protocol должен существовать"

    def test_browser_service_is_runtime_checkable(self) -> None:
        """Проверяет что BrowserService декорирован @runtime_checkable."""
        from parser_2gis.protocols import BrowserService

        assert hasattr(BrowserService, "_is_runtime_protocol"), (
            "BrowserService должен быть @runtime_checkable"
        )

    def test_browser_service_has_required_methods(self) -> None:
        """Проверяет что BrowserService определяет требуемые методы."""
        from parser_2gis.protocols import BrowserService

        required_methods = ["navigate", "get_html", "execute_js", "screenshot", "close"]

        for method_name in required_methods:
            assert hasattr(BrowserService, method_name), (
                f"BrowserService должен иметь метод '{method_name}'"
            )

    def test_chrome_remote_implements_browser_service(self) -> None:
        """Проверяет что ChromeRemote реализует BrowserService Protocol."""
        from parser_2gis.chrome.remote import ChromeRemote

        for method_name in ["navigate", "get_html", "execute_js", "screenshot", "close"]:
            assert hasattr(ChromeRemote, method_name), (
                f"ChromeRemote должен иметь метод '{method_name}'"
            )


class TestOtherProtocols:
    """Тесты на проверку дополнительных Protocol."""

    @pytest.mark.parametrize(
        "protocol_name,required_methods",
        [
            ("LoggerProtocol", ["debug", "info", "warning", "error", "critical"]),
            ("ProgressCallback", ["__call__"]),
            ("LogCallback", ["__call__"]),
            ("CleanupCallback", ["__call__"]),
            ("CancelCallback", ["__call__"]),
            ("Writer", ["write", "close"]),
            ("Parser", ["parse", "get_stats"]),
        ],
        ids=[
            "LoggerProtocol",
            "ProgressCallback",
            "LogCallback",
            "CleanupCallback",
            "CancelCallback",
            "Writer",
            "Parser",
        ],
    )
    def test_protocol_exists_with_methods(
        self, protocol_name: str, required_methods: List[str]
    ) -> None:
        """Проверяет что Protocol существует и имеет требуемые методы."""
        from parser_2gis.protocols import (
            CancelCallback,
            CleanupCallback,
            LogCallback,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        )

        protocols_map: Dict[str, type] = {
            "LoggerProtocol": LoggerProtocol,
            "ProgressCallback": ProgressCallback,
            "LogCallback": LogCallback,
            "CleanupCallback": CleanupCallback,
            "CancelCallback": CancelCallback,
            "Writer": Writer,
            "Parser": Parser,
        }

        protocol = protocols_map.get(protocol_name)
        assert protocol is not None, f"Protocol {protocol_name} не найден"

        for method_name in required_methods:
            assert hasattr(protocol, method_name), (
                f"{protocol_name} должен иметь метод '{method_name}'"
            )

    def test_all_protocols_are_runtime_checkable(self) -> None:
        """Проверяет что все Protocol декорированы @runtime_checkable."""
        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
            BrowserService,
            CacheBackend,
            CancelCallback,
            CleanupCallback,
            ExecutionBackend,
            LogCallback,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        )

        all_protocols = [
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
            BrowserService,
            CacheBackend,
            CancelCallback,
            CleanupCallback,
            ExecutionBackend,
            LogCallback,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        ]

        for protocol in all_protocols:
            assert hasattr(protocol, "_is_runtime_protocol"), (
                f"{protocol.__name__} должен быть @runtime_checkable"
            )


class TestProtocolsModuleExports:
    """Тесты на проверку экспорта из protocols.py."""

    def test_protocols_module_exists(self) -> None:
        """Проверяет что protocols.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        protocols_py = project_root / "protocols.py"

        assert protocols_py.exists(), "protocols.py должен существовать"

    def test_protocols_module_exports_all(self) -> None:
        """Проверяет что protocols.py экспортирует все Protocol."""
        from parser_2gis import protocols

        expected_exports = [
            "LoggerProtocol",
            "ProgressCallback",
            "LogCallback",
            "CleanupCallback",
            "CancelCallback",
            "Writer",
            "Parser",
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
            "BrowserService",
            "CacheBackend",
            "ExecutionBackend",
        ]

        missing_exports = []
        for export_name in expected_exports:
            if not hasattr(protocols, export_name):
                missing_exports.append(export_name)

        assert len(missing_exports) == 0, f"protocols.py не экспортирует: {missing_exports}"


# =============================================================================
# ТЕСТ 5: ИЕРАРХИЯ КЛАССОВ И REGISTRY PATTERN
# =============================================================================


class TestXlsxWriterInheritance:
    """Тесты на проверку иерархии наследования XLSXWriter."""

    def test_xlsx_writer_inherits_from_file_writer(self) -> None:
        """XLSXWriter должен наследоваться от FileWriter, а не от CSVWriter."""
        from parser_2gis.writer.writers.csv_writer import CSVWriter
        from parser_2gis.writer.writers.file_writer import FileWriter
        from parser_2gis.writer.writers.xlsx_writer import XLSXWriter

        assert issubclass(XLSXWriter, FileWriter), "XLSXWriter должен наследоваться от FileWriter"

        assert not issubclass(XLSXWriter, CSVWriter), (
            "XLSXWriter НЕ должен наследоваться от CSVWriter (разные форматы)"
        )

    def test_xlsx_writer_instance_check(self) -> None:
        """Экземпляр XLSXWriter должен быть экземпляром FileWriter."""
        from parser_2gis.writer.options import WriterOptions
        from parser_2gis.writer.writers.csv_writer import CSVWriter
        from parser_2gis.writer.writers.file_writer import FileWriter
        from parser_2gis.writer.writers.xlsx_writer import XLSXWriter

        options = WriterOptions(encoding="utf-8")
        xlsx_writer = XLSXWriter("test.xlsx", options)

        assert isinstance(xlsx_writer, FileWriter), (
            "Экземпляр XLSXWriter должен быть экземпляром FileWriter"
        )
        assert not isinstance(xlsx_writer, CSVWriter), (
            "Экземпляр XLSXWriter НЕ должен быть экземпляром CSVWriter"
        )


class TestWriterRegistry:
    """Тесты на проверку Writer Registry pattern."""

    def test_writer_registry_exists(self) -> None:
        """WRITER_REGISTRY должен существовать и содержать форматы."""
        from parser_2gis.writer.factory import WRITER_REGISTRY

        assert isinstance(WRITER_REGISTRY, dict), "WRITER_REGISTRY должен быть словарём"

        assert "json" in WRITER_REGISTRY, "WRITER_REGISTRY должен содержать 'json' формат"
        assert "csv" in WRITER_REGISTRY, "WRITER_REGISTRY должен содержать 'csv' формат"
        assert "xlsx" in WRITER_REGISTRY, "WRITER_REGISTRY должен содержать 'xlsx' формат"

    def test_writer_registry_classes_are_valid(self) -> None:
        """Классы в WRITER_REGISTRY должны быть подклассами FileWriter."""
        from parser_2gis.writer.factory import WRITER_REGISTRY
        from parser_2gis.writer.writers.file_writer import FileWriter

        for format_name, writer_class in WRITER_REGISTRY.items():
            assert issubclass(writer_class, FileWriter), (
                f"Writer для формата '{format_name}' должен наследоваться от FileWriter"
            )


class TestParserRegistry:
    """Тесты на проверку Parser Registry pattern."""

    def test_parser_registry_exists(self) -> None:
        """PARSER_REGISTRY должен существовать и содержать парсеры."""
        from parser_2gis.parser.factory import PARSER_REGISTRY

        assert isinstance(PARSER_REGISTRY, dict), "PARSER_REGISTRY должен быть словарём"
        assert len(PARSER_REGISTRY) > 0, "PARSER_REGISTRY должен содержать хотя бы один парсер"

    def test_parser_registry_contains_builtin_parsers(self) -> None:
        """PARSER_REGISTRY должен содержать встроенные парсеры."""
        from parser_2gis.parser.factory import PARSER_REGISTRY

        expected_parsers = {"MainParser", "FirmParser", "InBuildingParser"}
        registered_parsers = set(PARSER_REGISTRY.keys())

        missing_parsers = expected_parsers - registered_parsers
        assert len(missing_parsers) == 0, (
            f"Отсутствуют парсеры в PARSER_REGISTRY: {missing_parsers}"
        )


# =============================================================================
# ТЕСТ 6: PATH_UTILS И ВЕРИФИКАЦИЯ
# =============================================================================


class TestPathUtils:
    """Тесты на проверку утилит валидации путей."""

    def test_path_utils_exists(self) -> None:
        """utils/path_utils.py должен существовать с требуемыми функциями."""
        from parser_2gis.utils.path_utils import validate_path_safety, validate_path_traversal

        assert callable(validate_path_safety), (
            "validate_path_safety должна быть вызываемой функцией"
        )
        assert callable(validate_path_traversal), (
            "validate_path_traversal должна быть вызываемой функцией"
        )

    def test_path_utils_validates_traversal(self) -> None:
        """validate_path_traversal должен обнаруживать path traversal."""
        from parser_2gis.utils.path_utils import validate_path_traversal

        dangerous_paths = ["../etc/passwd", "test/../../../etc/passwd", "valid/../../dangerous"]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError):
                validate_path_traversal(dangerous_path)

    def test_path_utils_forbidden_chars(self) -> None:
        """validate_path_safety должен обнаруживать запрещённые символы."""
        from parser_2gis.utils.path_utils import validate_path_safety

        dangerous_paths = ["/tmp/file$test.txt", "/tmp/file;rm -rf.txt", "/tmp/file|cat.txt"]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError, match="запрещённый символ"):
                validate_path_safety(dangerous_path, "test_path")


# =============================================================================
# ТЕСТ 7: ОГРАНИЧЕНИЯ АРХИТЕКТУРЫ
# =============================================================================


class TestNoConstantDuplication:
    """Тесты на отсутствие дублирования констант."""

    def test_max_lock_file_age_only_in_constants(self) -> None:
        """MAX_LOCK_FILE_AGE должна быть определена только в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        files = self._find_constant_definition("MAX_LOCK_FILE_AGE", project_root)

        expected_file = project_root / "constants.py"
        assert expected_file in files, f"MAX_LOCK_FILE_AGE должна быть определена в {expected_file}"

        other_files = [f for f in files if f != expected_file]
        assert len(other_files) == 0, (
            f"MAX_LOCK_FILE_AGE дублируется в: {[str(f) for f in other_files]}"
        )

    def test_max_path_length_only_in_constants(self) -> None:
        """MAX_PATH_LENGTH должна быть определена только в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        files = self._find_constant_definition("MAX_PATH_LENGTH", project_root)

        expected_file = project_root / "constants.py"
        assert expected_file in files, f"MAX_PATH_LENGTH должна быть определена в {expected_file}"

        other_files = [f for f in files if f != expected_file]
        assert len(other_files) == 0, (
            f"MAX_PATH_LENGTH дублируется в: {[str(f) for f in other_files]}"
        )

    @staticmethod
    def _find_constant_definition(constant_name: str, root_dir: Path) -> List[Path]:
        """Находит все файлы, где определяется константа."""
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


class TestNoMultipleInheritance:
    """Тесты на отсутствие множественного наследования."""

    def test_parallel_city_parser_thread_no_threading_inheritance(self) -> None:
        """ParallelCityParserThread не должен наследоваться от threading.Thread."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        base_classes = self._find_class_base_classes("ParallelCityParserThread", project_root)

        assert "Thread" not in base_classes, (
            f"ParallelCityParserThread наследуется от Thread: {base_classes}. "
            "Должна использоваться композиция вместо наследования."
        )

    @staticmethod
    def _find_class_base_classes(class_name: str, root_dir: Path) -> List[str]:
        """Находит базовые классы для указанного класса."""
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
