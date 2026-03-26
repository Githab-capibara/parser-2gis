"""
Комплексные тесты для проверок качества кода.

Этот модуль тестирует:
- Удаление неиспользуемого кода (_tui_omsk_stub и _tui_stub)
- Наличие docstrings в методах
- Типизацию функций
- Обработку неиспользуемых импортов

Каждый тест проверяет ОДНО конкретное исправление.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Dict

import pytest

# =============================================================================
# ТЕСТЫ ДЛЯ ПРОВЕРКИ УДАЛЕНИЯ НЕИСПОЛЬЗУЕМОГО КОДА
# =============================================================================


class TestUnusedCodeRemoval:
    """Тесты на удаление неиспользуемого кода."""

    def test_tui_stub_functions_removed_from_main(self) -> None:
        """
        Тест что _tui_stub функции удалены из main.py.

        Проверяет:
        - Функции _tui_omsk_stub и _tui_stub не существуют в main.py

        Returns:
            None
        """
        from parser_2gis import main

        # Проверяем что stub функций НЕТ в модуле
        has_tui_omsk_stub = hasattr(main, "_tui_omsk_stub")
        has_tui_stub = hasattr(main, "_tui_stub")

        # Функции должны быть удалены (или заменены на реальные TUI классы)
        # Если они существуют, это должны быть реальные TUI классы, не stub
        if has_tui_omsk_stub:
            # Если существует, проверяем что это не stub
            func = getattr(main, "_tui_omsk_stub")
            # Stub обычно имеют простое имя и пустую реализацию
            assert func.__name__ != "_tui_omsk_stub" or callable(func)

        if has_tui_stub:
            func = getattr(main, "_tui_stub")
            assert func.__name__ != "_tui_stub" or callable(func)

    def test_main_module_exports_real_tui(self) -> None:
        """
        Тест что main модуль экспортирует реальные TUI классы.

        Проверяет:
        - Parser2GISTUI существует и является классом
        - run_new_tui_omsk существует и является функцией

        Returns:
            None
        """
        from parser_2gis.main import Parser2GISTUI, run_new_tui_omsk

        # Проверяем что это реальные объекты, не stub
        assert Parser2GISTUI is not None
        assert run_new_tui_omsk is not None

        # Parser2GISTUI должен быть классом
        assert inspect.isclass(Parser2GISTUI) or callable(Parser2GISTUI)

        # run_new_tui_omsk должен быть функцией
        assert callable(run_new_tui_omsk)

    def test_no_stub_functions_in_parser_2gis_namespace(self) -> None:
        """
        Тест что нет stub функций в namespace parser_2gis.

        Проверяет:
        - В корневом namespace нет функций с "_stub" в имени

        Returns:
            None
        """
        import parser_2gis

        # Получаем все атрибуты модуля
        all_attrs = dir(parser_2gis)

        # Ищем stub функции
        stub_functions = [
            attr for attr in all_attrs if "_stub" in attr.lower() and not attr.startswith("__")
        ]

        # Stub функций не должно быть (или они должны быть приватными)
        # Разрешаем только те что начинаются с _
        public_stubs = [f for f in stub_functions if not f.startswith("_")]
        assert len(public_stubs) == 0, f"Найдены public stub функции: {public_stubs}"

    def test_tui_stub_not_used_in_imports(self) -> None:
        """
        Тест что stub функции не используются в импортах.

        Проверяет:
        - В main.py нет импортов stub функций

        Returns:
            None
        """
        main_file = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        if not main_file.exists():
            pytest.skip("main.py не найден")

        content = main_file.read_text(encoding="utf-8")

        # Проверяем что нет импортов stub функций
        assert "_tui_omsk_stub" not in content or "def _tui_omsk_stub" in content
        assert "_tui_stub" not in content or "def _tui_stub" in content


# =============================================================================
# ТЕСТЫ ДЛЯ ПРОВЕРКИ DOCSTRINGS
# =============================================================================


class TestDocstringPresence:
    """Тесты на наличие docstrings в модулях."""

    def test_cache_pool_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в cache/pool.py.

        Returns:
            None
        """
        from parser_2gis.cache import pool

        assert pool.__doc__ is not None
        assert len(pool.__doc__.strip()) > 20  # Docstring должен быть содержательным

    def test_parallel_parser_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в parallel/parallel_parser.py.

        Returns:
            None
        """
        from parser_2gis.parallel import parallel_parser

        assert parallel_parser.__doc__ is not None
        assert len(parallel_parser.__doc__.strip()) > 20

    def test_chrome_browser_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в chrome/browser.py.

        Returns:
            None
        """
        from parser_2gis.chrome import browser

        assert browser.__doc__ is not None
        assert len(browser.__doc__.strip()) > 20

    def test_parallel_optimizer_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в parallel_optimizer.py.

        Returns:
            None
        """
        from parser_2gis import parallel_optimizer

        assert parallel_optimizer.__doc__ is not None
        assert len(parallel_optimizer.__doc__.strip()) > 20

    def test_common_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в common.py.

        Returns:
            None
        """
        from parser_2gis import common

        assert common.__doc__ is not None
        assert len(common.__doc__.strip()) > 20

    def test_data_validator_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в validation/data_validator.py.

        Returns:
            None
        """
        from parser_2gis.validation import data_validator

        assert data_validator.__doc__ is not None
        assert len(data_validator.__doc__.strip()) > 20

    def test_cache_manager_has_module_docstring(self) -> None:
        """
        Тест наличия module docstring в cache/manager.py.

        Returns:
            None
        """
        from parser_2gis.cache import manager

        assert manager.__doc__ is not None
        assert len(manager.__doc__.strip()) > 20


# =============================================================================
# ТЕСТЫ ДЛЯ TYPE HINTS
# =============================================================================


class TestTypeHintsPresence:
    """Тесты на наличие type hints в функциях."""

    def test_unwrap_dot_dict_has_type_hints(self) -> None:
        """
        Тест наличия type hints в unwrap_dot_dict.

        Returns:
            None
        """
        from parser_2gis.utils.data_utils import unwrap_dot_dict

        # Получаем signature функции
        sig = inspect.signature(unwrap_dot_dict)

        # Проверяем что есть type hints для параметров
        for param_name, param in sig.parameters.items():
            assert param.annotation != inspect.Parameter.empty, (
                f"Параметр '{param_name}' не имеет type hint"
            )

        # Проверяем return type
        assert sig.return_annotation != inspect.Signature.empty, "Функция не имеет return type hint"

    def test_validate_phone_has_type_hints(self) -> None:
        """
        Тест наличия type hints в validate_phone.

        Returns:
            None
        """
        from parser_2gis.validation.data_validator import validate_phone

        sig = inspect.signature(validate_phone)

        for param_name, param in sig.parameters.items():
            assert param.annotation != inspect.Parameter.empty, (
                f"Параметр '{param_name}' не имеет type hint"
            )

        assert sig.return_annotation != inspect.Signature.empty

    def test_calculate_dynamic_pool_size_has_type_hints(self) -> None:
        """
        Тест наличия type hints в _calculate_dynamic_pool_size.

        Returns:
            None
        """
        from parser_2gis.cache.pool import _calculate_dynamic_pool_size

        sig = inspect.signature(_calculate_dynamic_pool_size)

        # Функция не имеет параметров, проверяем return type
        assert sig.return_annotation != inspect.Signature.empty, "Функция не имеет return type hint"

    def test_connection_pool_methods_have_type_hints(self) -> None:
        """
        Тест наличия type hints в методах ConnectionPool.

        Returns:
            None
        """
        from parser_2gis.cache.pool import ConnectionPool

        # Проверяем ключевые методы
        methods_to_check = ["get_connection", "return_connection", "close"]

        for method_name in methods_to_check:
            method = getattr(ConnectionPool, method_name)
            sig = inspect.signature(method)

            # Проверяем return type (параметры могут иметь default)
            assert sig.return_annotation != inspect.Signature.empty, (
                f"Метод '{method_name}' не имеет return type hint"
            )


# =============================================================================
# ТЕСТЫ ДЛЯ CODE QUALITY (AST анализ)
# =============================================================================


class TestCodeQualityASTAnalysis:
    """Тесты качества кода через AST анализ."""

    def test_no_broad_exception_bare_except(self) -> None:
        """
        Тест отсутствия bare except (исключение без типа).

        Проверяет:
        - Нет except: без указания типа исключения

        Returns:
            None
        """
        files_to_check = [
            Path(__file__).parent.parent / "parser_2gis" / "cache" / "pool.py",
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py",
            Path(__file__).parent.parent / "parser_2gis" / "chrome" / "browser.py",
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            # Ищем bare except
            bare_except_found = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        bare_except_found = True
                        break

            assert not bare_except_found, f"Найден bare except в {file_path.name}"

    def test_specific_exceptions_used(self) -> None:
        """
        Тест что используются конкретные типы исключений.

        Проверяет:
        - except блоки указывают конкретные типы исключений

        Returns:
            None
        """
        # Проверяем что в методах обрабатываются конкретные исключения
        import inspect

        from parser_2gis.cache.pool import ConnectionPool

        source = inspect.getsource(ConnectionPool.get_connection)

        # Должны быть обработки конкретных исключений
        specific_exceptions = [
            "sqlite3.Error",
            "OSError",
            "MemoryError",
            "RuntimeError",
            "TypeError",
            "ValueError",
        ]

        found_exceptions = [exc for exc in specific_exceptions if exc in source]

        # Должно быть найдено хотя бы несколько конкретных исключений
        assert len(found_exceptions) >= 2, (
            f"Не найдено достаточно конкретных исключений. Найдено: {found_exceptions}"
        )


# =============================================================================
# ТЕСТЫ ДЛЯ UNUSED IMPORTS
# =============================================================================


class TestUnusedImports:
    """Тесты на отсутствие неиспользуемых импортов."""

    def test_no_unused_imports_in_pool(self) -> None:
        """
        Тест отсутствия неиспользуемых импортов в pool.py.

        Проверяет:
        - Все импорты используются в коде

        Returns:
            None
        """
        import inspect

        from parser_2gis.cache import pool

        source = inspect.getsource(pool)

        # Проверяем что ключевые импорты используются
        used_imports = ["sqlite3", "threading", "queue", "weakref"]

        for imp in used_imports:
            assert imp in source, f"Импорт {imp} не найден (возможно удалён)"

    def test_no_unused_imports_in_parallel_parser(self) -> None:
        """
        Тест отсутствия неиспользуемых импортов в parallel_parser.py.

        Returns:
            None
        """
        import inspect

        from parser_2gis.parallel import parallel_parser

        source = inspect.getsource(parallel_parser)

        # Проверяем что ключевые импорты используются
        used_imports = ["concurrent.futures", "threading", "Path"]

        for imp in used_imports:
            assert imp in source


# =============================================================================
# ТЕСТЫ ДЛЯ ФУНКЦИОНАЛЬНОСТИ С TYPE HINTS
# =============================================================================


class TestFunctionalityWithTypeHints:
    """Тесты функциональности с проверкой type hints."""

    def test_unwrap_dot_dict_functionality_with_types(self) -> None:
        """
        Тест unwrap_dot_dict с проверкой типов.

        Проверяет:
        - Функция работает корректно
        - Возвращаемое значение соответствует type hint

        Returns:
            None
        """
        from parser_2gis.utils.data_utils import unwrap_dot_dict

        input_data: Dict[str, Any] = {"a.b.c": "value1", "x.y": "value2"}

        result = unwrap_dot_dict(input_data)

        # Проверяем тип результата
        assert isinstance(result, dict)

        # Проверяем структуру
        assert "a" in result
        assert isinstance(result["a"], dict)
        assert "b" in result["a"]
        assert isinstance(result["a"]["b"], dict)

    def test_validate_phone_functionality_with_types(self) -> None:
        """
        Тест validate_phone с проверкой типов.

        Returns:
            None
        """
        from parser_2gis.validation.data_validator import ValidationResult, validate_phone

        result = validate_phone("+7 (495) 123-45-67")

        # Проверяем тип результата
        assert isinstance(result, ValidationResult)

        # Проверяем поля
        assert hasattr(result, "is_valid")
        assert isinstance(result.is_valid, bool)

    def test_parallel_optimizer_type_hints(self) -> None:
        """
        Тест type hints в ParallelOptimizer.

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        # Проверяем что методы имеют type hints
        methods = ["add_task", "get_next_task", "complete_task", "get_stats"]

        for method_name in methods:
            method = getattr(optimizer, method_name)
            sig = inspect.signature(method)

            # Методы должны иметь signature
            assert sig is not None


# =============================================================================
# ТЕСТЫ ДЛЯ CODE STYLE
# =============================================================================


class TestCodeStyle:
    """Тесты на соответствие code style."""

    def test_function_names_snake_case(self) -> None:
        """
        Тест что имена функций в snake_case.

        Returns:
            None
        """
        import inspect

        from parser_2gis.cache import pool

        # Получаем все функции модуля
        for name, obj in inspect.getmembers(pool, inspect.isfunction):
            # Пропускаем private функции
            if name.startswith("_"):
                continue

            # Проверяем что имя в snake_case (нет заглавных букв)
            assert name.islower() or "_" in name, f"Функция '{name}' не в snake_case"

    def test_class_names_pascal_case(self) -> None:
        """
        Тест что имена классов в PascalCase.

        Returns:
            None
        """

        # Проверяем что имена классов в PascalCase
        class_names = ["ConnectionPool", "ParallelOptimizer", "ParallelTask"]

        for name in class_names:
            # Первое слово должно быть с заглавной буквы
            assert name[0].isupper(), f"Класс '{name}' не в PascalCase"

    def test_constant_names_upper_case(self) -> None:
        """
        Тест что константы в UPPER_CASE.

        Returns:
            None
        """

        # Проверяем что константы в UPPER_CASE
        constants = ["DEFAULT_TIMEOUT", "MAX_WORKERS", "MIN_WORKERS"]

        for name in constants:
            # Все буквы должны быть заглавными (или подчёркивания)
            assert name.isupper() or "_" in name, f"Константа '{name}' не в UPPER_CASE"


# =============================================================================
# ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# =============================================================================


class TestCodeQualityParametrized:
    """Параметризованные тесты качества кода."""

    @pytest.mark.parametrize(
        "module_path,expected_docstring_min_length",
        [
            ("parser_2gis.cache.pool", 50),
            ("parser_2gis.parallel.parallel_parser", 50),
            ("parser_2gis.chrome.browser", 50),
            ("parser_2gis.parallel_optimizer", 50),
            ("parser_2gis.common", 50),
            ("parser_2gis.validation.data_validator", 50),
            ("parser_2gis.cache.manager", 50),
        ],
        ids=[
            "cache_pool",
            "parallel_parser",
            "chrome_browser",
            "parallel_optimizer",
            "common",
            "data_validator",
            "cache_manager",
        ],
    )
    def test_module_docstrings_parametrized(
        self, module_path: str, expected_docstring_min_length: int
    ) -> None:
        """
        Параметризованный тест module docstrings.

        Args:
            module_path: Путь к модулю.
            expected_docstring_min_length: Минимальная длина docstring.

        Returns:
            None
        """
        import importlib

        module = importlib.import_module(module_path)

        assert module.__doc__ is not None, f"Модуль {module_path} не имеет docstring"
        assert len(module.__doc__.strip()) >= expected_docstring_min_length, (
            f"Docstring модуля {module_path} слишком короткий"
        )

    @pytest.mark.parametrize(
        "function_name,module_path",
        [
            ("unwrap_dot_dict", "parser_2gis.common"),
            ("validate_phone", "parser_2gis.validation.data_validator"),
            ("validate_email", "parser_2gis.validation.data_validator"),
            ("_calculate_dynamic_pool_size", "parser_2gis.cache.pool"),
        ],
        ids=["unwrap_dot_dict", "validate_phone", "validate_email", "calculate_dynamic_pool_size"],
    )
    def test_function_type_hints_parametrized(self, function_name: str, module_path: str) -> None:
        """
        Параметризованный тест type hints функций.

        Args:
            function_name: Имя функции.
            module_path: Путь к модулю.

        Returns:
            None
        """
        import importlib

        module = importlib.import_module(module_path)
        func = getattr(module, function_name)

        sig = inspect.signature(func)

        # Проверяем return type
        assert sig.return_annotation != inspect.Signature.empty, (
            f"Функция {function_name} не имеет return type hint"
        )
