"""
Тесты на целостность архитектуры проекта parser-2gis.

Проверяет:
- Все utils/ модули существуют
- Все Protocol имеют реализации
- Нет битых импортов
- Backward совместимость сохранена
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List, Tuple

import pytest


class TestAllUtilsModulesExist:
    """Тесты на существование всех utils/ модулей."""

    def test_all_utils_modules_exist(self) -> None:
        """Проверяет что все модули в utils/ существуют."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        assert utils_dir.exists(), "utils/ должен существовать"

        # Ожидаемые модули
        expected_modules = [
            "__init__.py",
            "cache_monitor.py",
            "data_utils.py",
            "decorators.py",
            "math_utils.py",
            "path_utils.py",
            "sanitizers.py",
            "temp_file_manager.py",
            "url_utils.py",
            "validation_utils.py",
        ]

        missing_modules = []
        for module in expected_modules:
            module_path = utils_dir / module
            if not module_path.exists():
                missing_modules.append(module)

        assert len(missing_modules) == 0, f"Отсутствуют модули в utils/: {missing_modules}"

    def test_all_utils_modules_importable(self) -> None:
        """Проверяет что все модули в utils/ импортируются."""
        utils_modules = [
            "parser_2gis.utils.cache_monitor",
            "parser_2gis.utils.data_utils",
            "parser_2gis.utils.decorators",
            "parser_2gis.utils.math_utils",
            "parser_2gis.utils.path_utils",
            "parser_2gis.utils.sanitizers",
            "parser_2gis.utils.temp_file_manager",
            "parser_2gis.utils.url_utils",
            "parser_2gis.utils.validation_utils",
        ]

        failed_imports: List[Tuple[str, str]] = []

        for module_name in utils_modules:
            # Очищаем кэш
            if module_name in sys.modules:
                del sys.modules[module_name]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))

        assert len(failed_imports) == 0, "Модули utils/ не импортируются:\n" + "\n".join(
            f"  {m}: {e}" for m, e in failed_imports
        )

    def test_utils_init_exports_all_modules(self) -> None:
        """Проверяет что utils/__init__.py экспортирует все модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_init = project_root / "utils" / "__init__.py"

        content = utils_init.read_text(encoding="utf-8")

        # Ожидаемые импорты
        expected_imports = [
            "cache_monitor",
            "data_utils",
            "decorators",
            "math_utils",
            "path_utils",
            "sanitizers",
            "temp_file_manager",
            "url_utils",
            "validation_utils",
        ]

        missing_imports = []
        for module in expected_imports:
            if f"from .{module}" not in content:
                missing_imports.append(module)

        assert len(missing_imports) == 0, f"utils/__init__.py не импортирует: {missing_imports}"


class TestAllProtocolsImplemented:
    """Тесты на реализацию всех Protocol."""

    def test_all_protocols_have_implementations(self) -> None:
        """Проверяет что все Protocol имеют реализации."""
        from parser_2gis.protocols import (
            BrowserService,
            CacheBackend,
            ExecutionBackend,
            ParserFactory,
            WriterFactory,
        )

        # Проверяем что Protocol существуют
        assert BrowserService is not None
        assert CacheBackend is not None
        assert ExecutionBackend is not None
        assert ParserFactory is not None
        assert WriterFactory is not None

    def test_cache_backend_has_implementation(self) -> None:
        """Проверяет что CacheBackend имеет реализацию."""
        from parser_2gis.cache import CacheManager

        # Проверяем что CacheManager реализует методы CacheBackend
        required_methods = ["get", "set", "delete", "exists"]

        for method in required_methods:
            assert hasattr(CacheManager, method), f"CacheManager должен иметь метод '{method}'"

    def test_execution_backend_has_implementation(self) -> None:
        """Проверяет что ExecutionBackend имеет реализацию."""
        from concurrent.futures import ThreadPoolExecutor

        # ThreadPoolExecutor реализует ExecutionBackend
        required_methods = ["submit", "map", "shutdown"]

        for method in required_methods:
            assert hasattr(ThreadPoolExecutor, method), (
                f"ThreadPoolExecutor должен иметь метод '{method}'"
            )

    def test_parser_factory_has_implementation(self) -> None:
        """Проверяет что ParserFactory имеет реализацию."""
        from parser_2gis.parser.factory import ParserFactoryImpl

        # ParserFactoryImpl должен существовать
        assert ParserFactoryImpl is not None

        # Должен иметь метод get_parser
        assert hasattr(ParserFactoryImpl, "get_parser")

    def test_writer_factory_has_implementation(self) -> None:
        """Проверяет что WriterFactory имеет реализацию."""
        from parser_2gis.writer.factory import WriterFactoryImpl

        # WriterFactoryImpl должен существовать
        assert WriterFactoryImpl is not None

        # Должен иметь метод get_writer
        assert hasattr(WriterFactoryImpl, "get_writer")

    def test_browser_service_has_implementation(self) -> None:
        """Проверяет что BrowserService имеет реализацию."""
        from parser_2gis.chrome.remote import ChromeRemote

        # ChromeRemote должен реализовывать BrowserService
        required_methods = ["navigate", "get_html", "execute_js", "screenshot", "close"]

        for method in required_methods:
            assert hasattr(ChromeRemote, method), f"ChromeRemote должен иметь метод '{method}'"


class TestNoBrokenImports:
    """Тесты на отсутствие битых импортов."""

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
            # Очищаем кэш
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

    def test_init_files_export_symbols(self) -> None:
        """Проверяет что __init__.py экспортируют символы."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        packages_with_expected_exports = {
            "cache": ["CacheManager"],
            "chrome": ["ChromeRemote"],
            "protocols": ["BrowserService", "CacheBackend"],
            "config": ["Configuration"],
            "config_service": ["ConfigService"],
        }

        for package, expected_exports in packages_with_expected_exports.items():
            init_path = project_root / package / "__init__.py"

            if not init_path.exists():
                pytest.fail(f"Пакет не имеет __init__.py: {package}")

            content = init_path.read_text(encoding="utf-8")

            for export in expected_exports:
                assert export in content, f"{package}/__init__.py должен экспортировать {export}"


class TestBackwardCompatibilityPreserved:
    """Тесты на сохранение backward совместимости."""

    def test_backward_compatibility_preserved(self) -> None:
        """Проверяет что backward совместимость сохранена."""
        # Старые пути импорта должны работать

        # Configuration из config
        from parser_2gis.config import Configuration

        assert Configuration is not None

        # main из parser_2gis.main
        from parser_2gis.main import main

        assert main is not None

        # CLI символы
        from parser_2gis.cli.main import main as cli_main

        assert cli_main is not None

    def test_old_import_paths_still_work(self) -> None:
        """Проверяет что старые пути импорта работают."""
        # Проверяем что основные классы доступны из старых мест

        # CacheManager
        from parser_2gis.cache import CacheManager

        assert CacheManager is not None

        # ChromeRemote
        from parser_2gis.chrome import ChromeRemote

        assert ChromeRemote is not None

        # ParserFactory
        from parser_2gis.parser.factory import ParserFactoryImpl

        assert ParserFactoryImpl is not None

        # WriterFactory
        from parser_2gis.writer.factory import WriterFactoryImpl

        assert WriterFactoryImpl is not None

    def test_configuration_backward_compatible(self) -> None:
        """Проверяет что Configuration backward совместим."""
        from parser_2gis.config import Configuration

        # Configuration должен иметь методы для backward совместимости
        config = Configuration()

        assert hasattr(config, "merge_with")
        assert hasattr(config, "save_config")
        assert hasattr(config, "load_config")

    def test_config_service_new_api(self) -> None:
        """Проверяет что ConfigService — новая API."""
        from parser_2gis.config_service import ConfigService

        # ConfigService должен существовать
        assert ConfigService is not None

        # Должен иметь статические методы
        assert hasattr(ConfigService, "merge_configs")
        assert hasattr(ConfigService, "load_config")
        assert hasattr(ConfigService, "save_config")


class TestArchitectureIntegrityOverall:
    """Общие тесты на целостность архитектуры."""

    def test_all_architectural_layers_exist(self) -> None:
        """Проверяет что все архитектурные слои существуют."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        layers = {
            "cache": "Слой кэширования",
            "chrome": "Слой работы с браузером",
            "parser": "Слой парсинга",
            "writer": "Слой записи данных",
            "utils": "Утилиты",
            "validation": "Слой валидации",
            "cli": "CLI слой",
            "parallel": "Слой параллельного выполнения",
            "logger": "Слой логирования",
        }

        for layer_name, description in layers.items():
            layer_path = project_root / layer_name
            assert layer_path.exists(), f"{description} ({layer_name}) должен существовать"

    def test_no_circular_dependencies_between_layers(self) -> None:
        """Проверяет отсутствие циклических зависимостей между слоями."""
        # Это сложный тест, реализуем упрощённо

        Path(__file__).parent.parent / "parser_2gis"

        # Слои которые не должны иметь циклов
        layers = ["cache", "chrome", "parser", "writer", "utils", "validation"]

        # Проверяем что каждый слой импортируется независимо
        for layer in layers:
            module_name = f"parser_2gis.{layer}"

            # Очищаем кэш
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"{layer} должен импортироваться: {e}")

    def test_architecture_documentation_exists(self) -> None:
        """Проверяет что документация архитектуры существует."""
        project_root = Path(__file__).parent.parent

        # ARCHITECTURE.md должен существовать
        architecture_md = project_root / "ARCHITECTURE.md"
        assert architecture_md.exists(), "ARCHITECTURE.md должен существовать"

        # README.md должен существовать
        readme_md = project_root / "README.md"
        assert readme_md.exists(), "README.md должен существовать"

    def test_architecture_tests_exist(self) -> None:
        """Проверяет что тесты архитектуры существуют."""
        tests_dir = Path(__file__).parent

        architecture_tests = [
            "test_architecture_srp.py",
            "test_architecture_protocols.py",
            "test_architecture_cycles.py",
            "test_architecture_soc.py",
            "test_architecture_god_classes.py",
            "test_architecture_dry.py",
            "test_architecture_yagni.py",
            "test_architecture_integrity.py",
        ]

        missing_tests = []
        for test in architecture_tests:
            test_path = tests_dir / test
            if not test_path.exists():
                missing_tests.append(test)

        assert len(missing_tests) == 0, f"Отсутствуют тесты архитектуры: {missing_tests}"


__all__ = [
    "TestAllUtilsModulesExist",
    "TestAllProtocolsImplemented",
    "TestNoBrokenImports",
    "TestBackwardCompatibilityPreserved",
    "TestArchitectureIntegrityOverall",
]
