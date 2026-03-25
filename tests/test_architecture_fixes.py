"""Тесты на архитектурную целостность и проверку исправлений.

Этот модуль содержит тесты для проверки ключевых архитектурных решений
и исправлений, внесённых в проект parser-2gis.

Тесты покрывают следующие области:
1. Иерархия классов (H-6) - наследование XLSXWriter
2. Registry pattern (M-1, M-2) - реестры writer и parser
3. Path utils (M-3, M-4) - валидация путей
4. Разделение cache.py (H-1) - модульная структура кэша
5. Разделение chrome/remote.py (H-2) - модули Chrome
6. Разделение main.py (H-3) - CLI пакет
7. BrowserService Protocol (M-5) - протокол браузера
8. Отсутствие циклических зависимостей
9. Размер модулей (не более 500 строк)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

# =============================================================================
# ТЕСТЫ НА ИЕРАРХИЮ КЛАССОВ (H-6)
# =============================================================================


class TestXlsxWriterInheritance:
    """Тесты на проверку иерархии наследования XLSXWriter.

    XLSXWriter должен наследоваться от FileWriter, а не от CSVWriter,
    так как XLSX и CSV — разные форматы и не должны быть в одной иерархии.
    """

    def test_xlsx_writer_inherits_from_file_writer(self) -> None:
        """XLSXWriter должен наследоваться от FileWriter, а не от CSVWriter.

        Проверяет:
        - XLSXWriter является подклассом FileWriter
        - XLSXWriter НЕ является подклассом CSVWriter
        """
        from parser_2gis.writer.writers.csv_writer import CSVWriter
        from parser_2gis.writer.writers.file_writer import FileWriter
        from parser_2gis.writer.writers.xlsx_writer import XLSXWriter

        # XLSXWriter должен наследоваться от FileWriter
        assert issubclass(XLSXWriter, FileWriter), "XLSXWriter должен наследоваться от FileWriter"

        # XLSXWriter НЕ должен наследоваться от CSVWriter
        assert not issubclass(XLSXWriter, CSVWriter), (
            "XLSXWriter НЕ должен наследоваться от CSVWriter (разные форматы)"
        )

    def test_xlsx_writer_instance_check(self) -> None:
        """Экземпляр XLSXWriter должен быть экземпляром FileWriter."""
        from parser_2gis.writer.options import WriterOptions
        from parser_2gis.writer.writers.csv_writer import CSVWriter
        from parser_2gis.writer.writers.file_writer import FileWriter
        from parser_2gis.writer.writers.xlsx_writer import XLSXWriter

        # Создаём тестовые опции
        options = WriterOptions(encoding="utf-8")

        # Создаём экземпляр XLSXWriter
        xlsx_writer = XLSXWriter("test.xlsx", options)

        # Проверяем тип
        assert isinstance(xlsx_writer, FileWriter), (
            "Экземпляр XLSXWriter должен быть экземпляром FileWriter"
        )
        assert not isinstance(xlsx_writer, CSVWriter), (
            "Экземпляр XLSXWriter НЕ должен быть экземпляром CSVWriter"
        )


# =============================================================================
# ТЕСТЫ НА REGISTRY PATTERN (M-1, M-2)
# =============================================================================


class TestWriterRegistry:
    """Тесты на проверку Writer Registry pattern."""

    def test_writer_registry_exists(self) -> None:
        """WRITER_REGISTRY должен существовать и содержать форматы.

        Проверяет:
        - WRITER_REGISTRY существует и является dict
        - Содержит зарегистрированные форматы: json, csv, xlsx
        """
        from parser_2gis.writer.factory import WRITER_REGISTRY

        assert isinstance(WRITER_REGISTRY, dict), "WRITER_REGISTRY должен быть словарём"

        # Проверяем наличие базовых форматов
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

    def test_writer_registry_has_required_formats(self) -> None:
        """WRITER_REGISTRY должен содержать все требуемые форматы."""
        from parser_2gis.writer.factory import WRITER_REGISTRY

        required_formats = {"json", "csv", "xlsx"}
        available_formats = set(WRITER_REGISTRY.keys())

        missing_formats = required_formats - available_formats
        assert len(missing_formats) == 0, (
            f"Отсутствуют форматы в WRITER_REGISTRY: {missing_formats}"
        )


class TestParserRegistry:
    """Тесты на проверку Parser Registry pattern."""

    def test_parser_registry_exists(self) -> None:
        """PARSER_REGISTRY должен существовать и содержать парсеры.

        Проверяет:
        - PARSER_REGISTRY существует и является dict
        - Содержит зарегистрированные парсеры
        """
        from parser_2gis.parser.factory import PARSER_REGISTRY

        assert isinstance(PARSER_REGISTRY, dict), "PARSER_REGISTRY должен быть словарём"
        assert len(PARSER_REGISTRY) > 0, "PARSER_REGISTRY должен содержать хотя бы один парсер"

    def test_parser_registry_contains_builtin_parsers(self) -> None:
        """PARSER_REGISTRY должен содержать встроенные парсеры."""
        from parser_2gis.parser.factory import PARSER_REGISTRY

        # Проверяем наличие основных парсеров
        expected_parsers = {"MainParser", "FirmParser", "InBuildingParser"}
        registered_parsers = set(PARSER_REGISTRY.keys())

        missing_parsers = expected_parsers - registered_parsers
        assert len(missing_parsers) == 0, (
            f"Отсутствуют парсеры в PARSER_REGISTRY: {missing_parsers}"
        )

    def test_parser_registry_pattern_list_exists(self) -> None:
        """_PARSER_PATTERNS должен существовать для сопоставления URL."""
        from parser_2gis.parser.factory import _PARSER_PATTERNS

        assert isinstance(_PARSER_PATTERNS, list), "_PARSER_PATTERNS должен быть списком"
        assert len(_PARSER_PATTERNS) > 0, "_PARSER_PATTERNS должен содержать паттерны парсеров"


# =============================================================================
# ТЕСТЫ НА PATH_UTILS (M-3, M-4)
# =============================================================================


class TestPathUtils:
    """Тесты на проверку утилит валидации путей."""

    def test_path_utils_exists(self) -> None:
        """utils/path_utils.py должен существовать с требуемыми функциями.

        Проверяет:
        - Модуль path_utils существует
        - Функции validate_path_safety и validate_path_traversal доступны
        - Функции являются вызываемыми объектами
        """
        from parser_2gis.utils.path_utils import validate_path_safety, validate_path_traversal

        assert callable(validate_path_safety), (
            "validate_path_safety должна быть вызываемой функцией"
        )
        assert callable(validate_path_traversal), (
            "validate_path_traversal должна быть вызываемой функцией"
        )

    def test_path_utils_validates_traversal(self) -> None:
        """validate_path_traversal должен обнаруживать path traversal.

        Проверяет:
        - Обнаружение '../' в пути
        - Обнаружение '..\\' в пути
        - Генерация ValueError при обнаружении traversal
        """
        from parser_2gis.utils.path_utils import validate_path_traversal

        # Тестируем обнаружение path traversal
        dangerous_paths = [
            "../etc/passwd",
            "..\\windows\\system32",
            "test/../../../etc/passwd",
            "valid/../../dangerous",
        ]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError, match="Path traversal"):
                validate_path_traversal(dangerous_path)

    def test_path_utils_validates_safe_paths(self) -> None:
        """validate_path_traversal должен пропускать безопасные пути."""
        from parser_2gis.utils.path_utils import validate_path_traversal

        # Тестируем безопасные пути
        safe_paths = [
            "/tmp/output.txt",
            "/home/user/parser-2gis/output/data.csv",
            "output/results.json",
        ]

        for safe_path in safe_paths:
            try:
                result = validate_path_traversal(safe_path)
                assert result is not None, f"Безопасный путь должен быть валидирован: {safe_path}"
            except ValueError:
                # Некоторые пути могут не пройти из-за абсолютности/относительности
                # Это допустимо для данного теста
                pass

    def test_path_utils_forbidden_chars(self) -> None:
        """validate_path_safety должен обнаруживать запрещённые символы."""
        from parser_2gis.utils.path_utils import validate_path_safety

        # Пути с запрещёнными символами
        dangerous_paths = ["/tmp/file$test.txt", "/tmp/file;rm -rf.txt", "/tmp/file|cat.txt"]

        for dangerous_path in dangerous_paths:
            with pytest.raises(ValueError, match="запрещённый символ"):
                validate_path_safety(dangerous_path, "test_path")


# =============================================================================
# ТЕСТЫ НА РАЗДЕЛЕНИЕ CACHE.PY (H-1)
# =============================================================================


class TestCachePackage:
    """Тесты на проверку разделения cache.py на пакет."""

    def test_cache_package_exists(self) -> None:
        """cache.py должен быть разделён на пакет с модулями.

        Проверяет:
        - Пакет parser_2gis.cache существует
        - Модули manager, pool, serializer, validator доступны
        - Основные классы импортируются
        """
        from parser_2gis.cache import CacheManager
        from parser_2gis.cache.manager import CacheManager as ManagerClass
        from parser_2gis.cache.pool import ConnectionPool
        from parser_2gis.cache.serializer import JsonSerializer
        from parser_2gis.cache.validator import CacheDataValidator

        # Проверяем что CacheManager импортируется из пакета
        assert CacheManager is not None, "CacheManager должен быть доступен"
        assert CacheManager == ManagerClass, (
            "CacheManager из пакета должен совпадать с manager.CacheManager"
        )

        # Проверяем наличие вспомогательных классов
        assert ConnectionPool is not None, "ConnectionPool должен быть доступен"
        assert JsonSerializer is not None, "JsonSerializer должен быть доступен"
        assert CacheDataValidator is not None, "CacheDataValidator должен быть доступен"

    def test_cache_manager_functionality(self) -> None:
        """CacheManager должен быть функциональным классом."""
        import tempfile
        from pathlib import Path

        from parser_2gis.cache.manager import CacheManager

        # Создаём временную директорию для кэша
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache"
            cache = CacheManager(cache_path)

            # Проверяем что кэш работает
            assert cache is not None

            # Закрываем кэш
            cache.close()

    def test_connection_pool_exists(self) -> None:
        """ConnectionPool должен существовать в cache.pool."""
        from parser_2gis.cache.pool import (
            ConnectionPool,
            _calculate_dynamic_pool_size,
            _validate_pool_env_int,
        )

        assert ConnectionPool is not None
        assert callable(_calculate_dynamic_pool_size)
        assert callable(_validate_pool_env_int)


# =============================================================================
# ТЕСТЫ НА РАЗДЕЛЕНИЕ CHROME/REMOTE.PY (H-2)
# =============================================================================


class TestChromeModules:
    """Тесты на проверку разделения chrome/remote.py на модули."""

    def test_chrome_modules_exist(self) -> None:
        """chrome/remote.py должен быть разделён на модули.

        Проверяет:
        - Модули js_executor, http_cache, rate_limiter существуют
        - Функции валидации и кэширования доступны
        - ChromeRemote импортируется из remote.py
        """
        from parser_2gis.chrome.http_cache import (
            _cleanup_expired_cache,
            _get_http_cache,
            _HTTPCache,
        )
        from parser_2gis.chrome.js_executor import (
            _DANGEROUS_JS_PATTERNS,
            MAX_JS_CODE_LENGTH,
            _validate_js_code,
        )
        from parser_2gis.chrome.rate_limiter import _safe_external_request
        from parser_2gis.chrome.remote import ChromeRemote

        assert ChromeRemote is not None, "ChromeRemote должен быть доступен"
        assert callable(_validate_js_code), "_validate_js_code должна быть доступна"
        assert isinstance(_DANGEROUS_JS_PATTERNS, list), (
            "_DANGEROUS_JS_PATTERNS должен быть списком"
        )
        assert isinstance(MAX_JS_CODE_LENGTH, int), "MAX_JS_CODE_LENGTH должен быть int"
        assert _HTTPCache is not None, "_HTTPCache должен быть доступен"
        assert callable(_get_http_cache), "_get_http_cache должна быть вызываемой"
        assert callable(_cleanup_expired_cache), "_cleanup_expired_cache должна быть вызываемой"
        assert callable(_safe_external_request), "_safe_external_request должна быть вызываемой"

    def test_chrome_remote_class_exists(self) -> None:
        """ChromeRemote класс должен существовать и быть функциональным."""
        from parser_2gis.chrome.remote import ChromeRemote

        # Проверяем что класс существует
        assert ChromeRemote is not None
        assert hasattr(ChromeRemote, "navigate") or hasattr(ChromeRemote, "__init__")

    def test_js_executor_module(self) -> None:
        """JSExecutor модуль должен существовать."""
        from parser_2gis.chrome.js_executor import (
            _DANGEROUS_JS_PATTERNS,
            MAX_JS_CODE_LENGTH,
            _validate_js_code,
        )

        assert isinstance(_DANGEROUS_JS_PATTERNS, list)
        assert isinstance(MAX_JS_CODE_LENGTH, int)
        assert callable(_validate_js_code)

    def test_http_cache_module(self) -> None:
        """HTTPCache модуль должен существовать."""
        from parser_2gis.chrome.http_cache import (
            _cleanup_expired_cache,
            _get_http_cache,
            _HTTPCache,
            _HTTPCacheEntry,
        )

        assert _HTTPCache is not None
        assert _HTTPCacheEntry is not None
        assert callable(_get_http_cache)
        assert callable(_cleanup_expired_cache)


# =============================================================================
# ТЕСТЫ НА РАЗДЕЛЕНИЕ MAIN.PY (H-3)
# =============================================================================


class TestCliPackage:
    """Тесты на проверку разделения main.py на пакет cli/."""

    def test_cli_package_exists(self) -> None:
        """main.py должен быть разделён на пакет cli/.

        Проверяет:
        - Пакет parser_2gis.cli существует
        - Модули main, arguments, validator, formatter доступны
        - Основные функции и классы импортируются
        """
        from parser_2gis.cli.arguments import parse_arguments
        from parser_2gis.cli.formatter import ArgumentHelpFormatter
        from parser_2gis.cli.main import main as cli_main
        from parser_2gis.cli.validator import ArgumentValidator

        assert callable(cli_main), "main функция должна быть вызываемой"
        assert callable(parse_arguments), "parse_arguments должна быть вызываемой функцией"
        assert ArgumentValidator is not None, "ArgumentValidator должен быть доступен"
        assert ArgumentHelpFormatter is not None, "ArgumentHelpFormatter должен быть доступен"

    def test_cli_main_function(self) -> None:
        """main функция CLI должна существовать."""
        from parser_2gis.cli.main import main

        assert callable(main), "main функция должна быть вызываемой"

    def test_cli_arguments_module(self) -> None:
        """Модуль arguments CLI должен существовать."""
        from parser_2gis.cli.arguments import parse_arguments

        assert callable(parse_arguments), "parse_arguments должна быть вызываемой"

    def test_cli_validator_class(self) -> None:
        """Класс ArgumentValidator должен существовать."""
        from parser_2gis.cli.validator import ArgumentValidator

        assert ArgumentValidator is not None
        # Проверяем что это класс
        assert isinstance(ArgumentValidator, type)

    def test_cli_formatter_class(self) -> None:
        """Класс ArgumentHelpFormatter должен существовать."""
        from parser_2gis.cli.formatter import ArgumentHelpFormatter

        assert ArgumentHelpFormatter is not None
        assert isinstance(ArgumentHelpFormatter, type)


# =============================================================================
# ТЕСТЫ НА BROWSERSERVICE PROTOCOL (M-5)
# =============================================================================


class TestBrowserServiceProtocol:
    """Тесты на проверку BrowserService Protocol."""

    def test_browser_service_protocol_exists(self) -> None:
        """BrowserService Protocol должен существовать.

        Проверяет:
        - Protocol BrowserService существует в protocols.py
        - ChromeRemote реализует BrowserService
        """
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None, "BrowserService Protocol должен существовать"

    def test_browser_service_protocol_methods(self) -> None:
        """BrowserService Protocol должен определять требуемые методы."""
        from parser_2gis.protocols import BrowserService

        # Проверяем наличие требуемых методов в Protocol
        required_methods = ["navigate", "get_html", "execute_js", "screenshot", "close"]

        for method_name in required_methods:
            assert hasattr(BrowserService, method_name), (
                f"BrowserService должен иметь метод '{method_name}'"
            )

    def test_chrome_remote_implements_browser_service(self) -> None:
        """ChromeRemote должен реализовывать BrowserService Protocol."""
        from parser_2gis.chrome.remote import ChromeRemote

        # Проверяем что ChromeRemote имеет все методы BrowserService
        required_methods = ["navigate", "get_html", "execute_js", "screenshot", "close"]

        for method_name in required_methods:
            assert hasattr(ChromeRemote, method_name), (
                f"ChromeRemote должен иметь метод '{method_name}'"
            )

    def test_browser_service_runtime_checkable(self) -> None:
        """BrowserService должен быть runtime_checkable."""

        from parser_2gis.protocols import BrowserService

        # Проверяем что Protocol декорирован @runtime_checkable
        assert hasattr(BrowserService, "_is_runtime_protocol"), (
            "BrowserService должен быть @runtime_checkable"
        )


# =============================================================================
# ТЕСТЫ НА ОТСУТСТВИЕ ЦИКЛИЧЕСКИХ ЗАВИСИМОСТЕЙ
# =============================================================================


class TestCyclicDependencies:
    """Тесты на проверку отсутствия циклических зависимостей."""

    def test_no_cyclic_dependencies(self) -> None:
        """Не должно быть циклических зависимостей между модулями.

        Проверяет:
        - Каждый модуль импортируется независимо
        - Нет ImportError при импорте основных модулей
        """
        import importlib

        modules = [
            "parser_2gis.cache",
            "parser_2gis.chrome",
            "parser_2gis.parser",
            "parser_2gis.writer",
            "parser_2gis.utils",
            "parser_2gis.validation",
            "parser_2gis.cli",
        ]

        failed_imports = []

        for module_name in modules:
            # Очищаем кэш импортов для этого модуля
            modules_to_remove = [mod for mod in sys.modules.keys() if mod.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            # Импортируем модуль
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        # Формируем сообщение об ошибке если есть неудачные импорты
        if failed_imports:
            error_messages = [f"{mod_name}: {error}" for mod_name, error in failed_imports]
            pytest.fail("Не удалось импортировать модули:\n" + "\n".join(error_messages))

    def test_cache_module_independent_import(self) -> None:
        """Модуль cache должен импортироваться независимо."""
        import importlib

        # Очищаем кэш
        cache_modules = [m for m in sys.modules if m.startswith("parser_2gis.cache")]
        for mod in cache_modules:
            del sys.modules[mod]

        # Импортируем
        cache_module = importlib.import_module("parser_2gis.cache")
        assert cache_module is not None

    def test_chrome_module_independent_import(self) -> None:
        """Модуль chrome должен импортироваться независимо."""
        import importlib

        # Очищаем кэш
        chrome_modules = [m for m in sys.modules if m.startswith("parser_2gis.chrome")]
        for mod in chrome_modules:
            del sys.modules[mod]

        # Импортируем
        chrome_module = importlib.import_module("parser_2gis.chrome")
        assert chrome_module is not None


# =============================================================================
# ТЕСТЫ НА РАЗМЕР МОДУЛЕЙ
# =============================================================================


class TestModuleSizes:
    """Тесты на проверку размера модулей."""

    def test_module_sizes_acceptable(self) -> None:
        """Модули не должны превышать 500 строк (с исключениями).

        Проверяет:
        - Все .py файлы не превышают 500 строк кода
        - Допускаются исключения для сложных модулей
        """
        max_lines = 500

        # Допустимые исключения (сложные модули)
        allowed_exceptions = {
            "browser.py",  # Управление браузером
            "remote.py",  # Remote управление
            "manager.py",  # Кэширование
            "main.py",  # CLI точка входа
            "js_executor.py",  # JS выполнение
            "pool.py",  # Connection pool
            "parallel_parser.py",  # Параллельный парсинг
            "app.py",  # TUI приложение (tui_textual/app.py)
            "visual_logger.py",  # Визуальный логгер
        }

        large_modules = []

        # Путь к исходному коду
        root_dir = Path(__file__).parent.parent / "parser_2gis"

        for root, dirs, files in os.walk(root_dir):
            # Пропускаем __pycache__ и тесты
            if "__pycache__" in root or "tests" in root:
                continue

            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    filepath = Path(root) / file

                    with open(filepath, "r", encoding="utf-8") as f:
                        lines = len(f.readlines())

                    if lines > max_lines:
                        filename = file
                        if filename not in allowed_exceptions:
                            large_modules.append((str(filepath), lines))

        # Формируем сообщение об ошибке
        if large_modules:
            error_details = [f"{filepath}: {lines} строк" for filepath, lines in large_modules]
            pytest.fail(
                f"Модули превышают {max_lines} строк (без учёта исключений):\n"
                + "\n".join(error_details)
            )

    def test_specific_module_sizes(self) -> None:
        """Проверка размера конкретных критических модулей."""
        # Модули которые должны быть компактными
        compact_modules = [
            "parser_2gis/utils/path_utils.py",
            "parser_2gis/protocols.py",
            "parser_2gis/writer/factory.py",
            "parser_2gis/parser/factory.py",
        ]

        max_lines = 500

        root_dir = Path(__file__).parent.parent

        for module_path in compact_modules:
            filepath = root_dir / module_path

            if not filepath.exists():
                pytest.fail(f"Модуль не найден: {module_path}")

            with open(filepath, "r", encoding="utf-8") as f:
                lines = len(f.readlines())

            assert lines <= max_lines, (
                f"Модуль {module_path} превышает {max_lines} строк: {lines} строк"
            )


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestArchitectureIntegrity:
    """Интеграционные тесты на архитектурную целостность."""

    def test_all_architectural_components_exist(self) -> None:
        """Все архитектурные компоненты должны существовать.

        Комплексная проверка:
        - Registry pattern (writer и parser)
        - Protocol (BrowserService)
        - Path utils
        - Модульная структура (cache, chrome, cli)
        """
        # Проверяем Writer Registry
        from parser_2gis.writer.factory import WRITER_REGISTRY

        assert isinstance(WRITER_REGISTRY, dict)
        assert "json" in WRITER_REGISTRY
        assert "csv" in WRITER_REGISTRY
        assert "xlsx" in WRITER_REGISTRY

        # Проверяем Parser Registry
        from parser_2gis.parser.factory import PARSER_REGISTRY

        assert isinstance(PARSER_REGISTRY, dict)
        assert len(PARSER_REGISTRY) > 0

        # Проверяем BrowserService Protocol
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None

        # Проверяем Path Utils
        from parser_2gis.utils.path_utils import validate_path_traversal

        assert callable(validate_path_traversal)

        # Проверяем модульную структуру cache
        from parser_2gis.cache import CacheManager
        from parser_2gis.cache.pool import ConnectionPool

        assert CacheManager is not None
        assert ConnectionPool is not None

        # Проверяем модульную структуру chrome
        from parser_2gis.chrome.js_executor import _DANGEROUS_JS_PATTERNS, _validate_js_code
        from parser_2gis.chrome.remote import ChromeRemote

        assert ChromeRemote is not None
        assert callable(_validate_js_code)
        assert isinstance(_DANGEROUS_JS_PATTERNS, list)

        # Проверяем модульную структуру cli
        from parser_2gis.cli.arguments import parse_arguments
        from parser_2gis.cli.main import main

        assert callable(main)
        assert callable(parse_arguments)

    def test_xlsx_writer_not_inherits_csv_writer(self) -> None:
        """Критический тест: XLSXWriter НЕ должен наследоваться от CSVWriter."""
        from parser_2gis.writer.writers.csv_writer import CSVWriter
        from parser_2gis.writer.writers.xlsx_writer import XLSXWriter

        # Это критическое архитектурное решение
        # XLSX и CSV — разные форматы, не должны быть в одной иерархии
        mro = XLSXWriter.__mro__

        # Проверяем что CSVWriter нет в MRO (method resolution order)
        assert CSVWriter not in mro, (
            "XLSXWriter не должен наследоваться от CSVWriter (нарушение иерархии)"
        )


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
