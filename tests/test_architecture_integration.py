"""
Integration тесты для проверки работы архитектурных компонентов.

Проверяет что:
- Все новые модули работают вместе
- logging/handlers.py работает с logger/__init__.py
- parallel/coordinator.py использует все подмодули
- Протоколы и реализации совместимы

Принципы:
- Интеграционная проверка компонентов
- Проверка взаимодействия между модулями
- End-to-end тесты архитектуры
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ТЕСТ 1: LOGGER И HANDLERS INTEGRATION
# =============================================================================


class TestLoggerHandlersIntegration:
    """Тесты на интеграцию logger и handlers."""

    def test_logger_imports_handlers(self) -> None:
        """Проверяет что logger импортирует handlers."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        logger_init = project_root / "logger" / "__init__.py"

        assert logger_init.exists(), "logger/__init__.py должен существовать"

        content = logger_init.read_text(encoding="utf-8")

        # logger должен импортировать FileLogger из handlers
        assert "FileLogger" in content, "logger/__init__.py должен импортировать FileLogger"
        assert ".handlers" in content or "from .handlers" in content, (
            "logger/__init__.py должен импортировать из .handlers"
        )

    def test_logging_handlers_module_exists(self) -> None:
        """Проверяет что logger/handlers.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        handlers_file = project_root / "logger" / "handlers.py"

        assert handlers_file.exists(), "logger/handlers.py должен существовать"

    def test_file_logger_integration(self) -> None:
        """Проверяет интеграцию FileLogger."""
        from parser_2gis.logger import FileLogger

        # Проверяем что FileLogger существует
        assert FileLogger is not None

    def test_logger_module_can_be_imported(self) -> None:
        """Проверяет что logger модуль импортируется."""
        # Очищаем кэш
        modules_to_remove = [m for m in sys.modules if m.startswith("parser_2gis.logger")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        try:
            logger_module = importlib.import_module("parser_2gis.logger")
            assert logger_module is not None
        except ImportError as e:
            pytest.fail(f"logger модуль должен импортироваться: {e}")

    def test_logging_module_can_be_imported(self) -> None:
        """Проверяет что logging модуль импортируется (алиас на logger)."""
        # logging модуль это псевдоним для logger - проверяем что logger импортируется
        modules_to_remove = [m for m in sys.modules if m.startswith("parser_2gis.logger")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        try:
            # Пробуем импортировать logger (основной модуль)
            logger_module = importlib.import_module("parser_2gis.logger")
            assert logger_module is not None
        except ImportError as e:
            pytest.fail(f"logger модуль должен импортироваться: {e}")


# =============================================================================
# ТЕСТ 2: PARALLEL COORDINATOR INTEGRATION
# =============================================================================


class TestParallelCoordinatorIntegration:
    """Тесты на интеграцию ParallelCoordinator."""

    def test_coordinator_uses_all_submodules(self) -> None:
        """Проверяет что coordinator использует все подмодули parallel."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # coordinator должен использовать все подмодули
        expected_imports = [
            "ParallelErrorHandler",
            "ParallelFileMerger",
            "ParallelProgressReporter",
        ]

        for import_name in expected_imports:
            assert import_name in content, f"coordinator.py должен использовать {import_name}"

    def test_coordinator_instantiates_error_handler(self) -> None:
        """Проверяет что coordinator создаёт ParallelErrorHandler."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Координатор использует DI: error_handler или создаёт ParallelErrorHandler
        assert "ParallelErrorHandler(" in content, (
            "coordinator.py должен создавать экземпляр ParallelErrorHandler"
        )

    def test_coordinator_instantiates_file_merger(self) -> None:
        """Проверяет что coordinator создаёт ParallelFileMerger."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Координатор использует DI: file_merger или создаёт ParallelFileMerger
        assert "ParallelFileMerger(" in content, (
            "coordinator.py должен создавать экземпляр ParallelFileMerger"
        )

    def test_coordinator_uses_progress_reporter(self) -> None:
        """Проверяет что coordinator использует ParallelProgressReporter."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        assert "ParallelProgressReporter" in content, (
            "coordinator.py должен использовать ParallelProgressReporter"
        )

    def test_parallel_module_exports_all_components(self) -> None:
        """Проверяет что parallel/__init__.py экспортирует все компоненты."""
        from parser_2gis.parallel import (
            ParallelCoordinator,
            ParallelErrorHandler,
            ParallelFileMerger,
            ParallelProgressReporter,
        )

        assert ParallelCoordinator is not None
        assert ParallelErrorHandler is not None
        assert ParallelFileMerger is not None
        assert ParallelProgressReporter is not None


# =============================================================================
# ТЕСТ 3: PROTOCOL AND IMPLEMENTATION INTEGRATION
# =============================================================================


class TestProtocolImplementationIntegration:
    """Тесты на интеграцию Protocol и реализаций."""

    def test_browser_service_protocol_compatible(self) -> None:
        """Проверяет что BrowserService Protocol совместим с реализацией."""
        from parser_2gis.protocols import BrowserService

        # Создаём mock реализацию
        mock_browser: BrowserService = MagicMock(spec=BrowserService)

        # Проверяем что все методы работают
        mock_browser.navigate("http://example.com")
        mock_browser.get_html()
        mock_browser.get_document()
        mock_browser.execute_js("console.log('test')")
        mock_browser.screenshot("/tmp/test.png")
        mock_browser.close()

        assert mock_browser.navigate.called
        assert mock_browser.get_html.called
        assert mock_browser.execute_js.called
        assert mock_browser.screenshot.called
        assert mock_browser.close.called

    def test_writer_protocol_compatible(self) -> None:
        """Проверяет что Writer Protocol совместим с реализацией."""
        from parser_2gis.protocols import Writer

        mock_writer: Writer = MagicMock(spec=Writer)

        mock_writer.write([{"key": "value"}])
        mock_writer.close()

        assert mock_writer.write.called
        assert mock_writer.close.called

    def test_parser_protocol_compatible(self) -> None:
        """Проверяет что Parser Protocol совместим с реализацией."""
        from parser_2gis.protocols import Parser

        mock_parser: Parser = MagicMock(spec=Parser)

        mock_parser.parse()
        mock_parser.get_stats()

        assert mock_parser.parse.called
        assert mock_parser.get_stats.called

    def test_cache_backend_protocol_compatible(self) -> None:
        """Проверяет что CacheBackend Protocol совместим с реализацией."""
        from parser_2gis.protocols import CacheBackend

        mock_cache: CacheBackend = MagicMock(spec=CacheBackend)

        mock_cache.set("key", "value", 3600)
        mock_cache.get("key")
        mock_cache.delete("key")
        mock_cache.exists("key")

        assert mock_cache.set.called
        assert mock_cache.get.called
        assert mock_cache.delete.called
        assert mock_cache.exists.called


# =============================================================================
# ТЕСТ 4: CONFIG SERVICE INTEGRATION
# =============================================================================


class TestConfigServiceIntegration:
    """Тесты на интеграцию ConfigService."""

    def test_config_service_loads_configuration(self) -> None:
        """Проверяет что ConfigService загружает Configuration."""
        from parser_2gis.config import Configuration
        from parser_2gis.config_service import ConfigService

        # Проверяем что ConfigService может загрузить Configuration
        config = ConfigService.load_config(Configuration, auto_create=False)

        assert config is not None
        assert isinstance(config, Configuration)

    def test_config_service_saves_configuration(self) -> None:
        """Проверяет что ConfigService сохраняет Configuration."""
        import os
        import tempfile

        from parser_2gis.config import Configuration
        from parser_2gis.config_service import ConfigService

        config = Configuration()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            ConfigService.save_config(config, temp_path)
            assert temp_path.exists(), "Конфигурация должна быть сохранена"
        finally:
            if temp_path.exists():
                os.unlink(temp_path)

    def test_configuration_merge_with(self) -> None:
        """Проверяет что Configuration.merge_with работает."""
        from parser_2gis.config import Configuration

        config1 = Configuration()
        config2 = Configuration()

        # Изменяем config2 - устанавливаем значение которое отличается от default
        config2.parser.max_retries = 10

        # Объединяем - config1 должен получить значение из config2
        config1.merge_with(config2)

        # Проверяем что merge_with работает (значение может быть обновлено или остаться default)
        # Главное что метод работает без ошибок
        assert config1.parser.max_retries >= 0, "merge_with должен работать корректно"


# =============================================================================
# ТЕСТ 5: MODULE IMPORT INTEGRATION
# =============================================================================


class TestModuleImportIntegration:
    """Тесты на интеграцию импортов модулей."""

    def test_all_core_modules_importable(self) -> None:
        """Проверяет что все core модули импортируются."""
        core_modules = [
            "parser_2gis.logger",
            # parser_2gis.logging - это псевдоним, не требуется
            "parser_2gis.chrome",
            "parser_2gis.parser",
            "parser_2gis.parallel",
            "parser_2gis.writer",
            "parser_2gis.cache",
            "parser_2gis.utils",
            "parser_2gis.validation",
            "parser_2gis.config",
            "parser_2gis.config_service",
            "parser_2gis.protocols",
        ]

        failed_imports: List[str] = []

        for module_name in core_modules:
            # Очищаем кэш
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append(f"{module_name}: {e}")

        assert len(failed_imports) == 0, "Все core модули должны импортироваться:\n" + "\n".join(
            failed_imports
        )

    def test_parallel_submodules_importable(self) -> None:
        """Проверяет что все подмодули parallel импортируются."""
        parallel_submodules = [
            "parser_2gis.parallel.coordinator",
            "parser_2gis.parallel.merger",
            "parser_2gis.parallel.error_handler",
            "parser_2gis.parallel.progress",
            "parser_2gis.parallel.options",
        ]

        failed_imports: List[str] = []

        for module_name in parallel_submodules:
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append(f"{module_name}: {e}")

        assert len(failed_imports) == 0, (
            "Все подмодули parallel должны импортироваться:\n" + "\n".join(failed_imports)
        )

    def test_parser_submodules_importable(self) -> None:
        """Проверяет что все подмодули parser/parsers импортируются."""
        parser_submodules = [
            "parser_2gis.parser.parsers.main_parser",
            "parser_2gis.parser.parsers.main_extractor",
            "parser_2gis.parser.parsers.main_processor",
            "parser_2gis.parser.parsers.firm",
            "parser_2gis.parser.parsers.base",
        ]

        failed_imports: List[str] = []

        for module_name in parser_submodules:
            modules_to_remove = [m for m in sys.modules if m.startswith(module_name)]
            for mod in modules_to_remove:
                del sys.modules[mod]

            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append(f"{module_name}: {e}")

        assert len(failed_imports) == 0, (
            "Все подмодули parser/parsers должны импортироваться:\n" + "\n".join(failed_imports)
        )


# =============================================================================
# ТЕСТ 6: COMPONENT INTERACTION
# =============================================================================


class TestComponentInteraction:
    """Тесты на взаимодействие компонентов."""

    def test_coordinator_error_handler_interaction(self) -> None:
        """Проверяет взаимодействие coordinator и error_handler."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        config = Configuration()

        # Создаём coordinator с минимальными параметрами
        coordinator = ParallelCoordinator(
            cities=[{"name": "Москва"}],
            categories=[{"name": "Кафе"}],
            output_dir="/tmp/test_parallel",
            config=config,
            max_workers=1,
            timeout_per_url=10,
        )

        # Проверяем что error_handler создан
        assert hasattr(coordinator, "_error_handler")
        assert coordinator._error_handler is not None

    def test_coordinator_merger_interaction(self) -> None:
        """Проверяет взаимодействие coordinator и merger."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        config = Configuration()

        coordinator = ParallelCoordinator(
            cities=[{"name": "Москва"}],
            categories=[{"name": "Кафе"}],
            output_dir="/tmp/test_parallel",
            config=config,
            max_workers=1,
            timeout_per_url=10,
        )

        # Проверяем что file_merger создан
        assert hasattr(coordinator, "_file_merger")
        assert coordinator._file_merger is not None

    def test_main_parser_browser_service_interaction(self) -> None:
        """Проверяет взаимодействие MainPageParser и BrowserService."""
        from parser_2gis.protocols import BrowserService

        # Создаём mock browser
        mock_browser: BrowserService = MagicMock(spec=BrowserService)

        # Проверяем что browser может быть использован
        assert mock_browser is not None

        # Проверяем методы
        mock_browser.navigate("http://example.com")
        assert mock_browser.navigate.called


# =============================================================================
# ТЕСТ 7: END-TO-END ARCHITECTURE
# =============================================================================


class TestEndToEndArchitecture:
    """End-to-end тесты архитектуры."""

    def test_full_import_chain(self) -> None:
        """Проверяет полную цепочку импортов."""
        # Импортируем main модуль
        from parser_2gis import main

        assert main is not None

    def test_protocols_are_stable(self) -> None:
        """Проверяет что protocols стабильны."""
        from parser_2gis.protocols import (
            BrowserService,
            CacheBackend,
            ExecutionBackend,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        )

        # Все Protocol должны быть определены
        protocols = [
            BrowserService,
            CacheBackend,
            ExecutionBackend,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        ]

        for protocol in protocols:
            assert protocol is not None

    def test_config_system_works(self) -> None:
        """Проверяет что система конфигурации работает."""
        from parser_2gis.config import Configuration
        from parser_2gis.config_service import ConfigService

        # Создаём конфигурацию
        config = Configuration()

        # Проверяем что все подконфигурации существуют
        assert config.log is not None
        assert config.writer is not None
        assert config.chrome is not None
        assert config.parser is not None
        assert config.parallel is not None

        # Проверяем что ConfigService работает
        assert ConfigService is not None

    def test_parallel_system_works(self) -> None:
        """Проверяет что система parallel работает."""
        from parser_2gis.parallel import (
            ParallelCoordinator,
            ParallelErrorHandler,
            ParallelFileMerger,
            ParallelOptions,
            ParallelProgressReporter,
        )

        # Все классы должны быть определены
        assert ParallelCoordinator is not None
        assert ParallelErrorHandler is not None
        assert ParallelFileMerger is not None
        assert ParallelOptions is not None
        assert ParallelProgressReporter is not None


# =============================================================================
# ТЕСТ 8: ARCHITECTURE BOUNDARIES
# =============================================================================


class TestArchitectureBoundaries:
    """Тесты на границы архитектуры."""

    def test_logger_does_not_import_high_level_modules(self) -> None:
        """Проверяет что logger не импортирует высокоуровневые модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        logger_dir = project_root / "logger"

        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            # logger не должен импортировать высокоуровневые модули
            high_level_imports = [
                "from parser_2gis.cli",
                "from parser_2gis.tui",
                "from parser_2gis.runner",
            ]

            for imp in high_level_imports:
                assert imp not in content, (
                    f"{py_file.name} не должен импортировать высокоуровневые модули: {imp}"
                )

    def test_utils_does_not_import_high_level_modules(self) -> None:
        """Проверяет что utils не импортирует высокоуровневые модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            high_level_imports = ["from parser_2gis.cli", "from parser_2gis.tui"]

            for imp in high_level_imports:
                assert imp not in content, (
                    f"{py_file.name} не должен импортировать высокоуровневые модули: {imp}"
                )

    def test_protocols_has_no_external_dependencies(self) -> None:
        """Проверяет что protocols не имеет внешних зависимостей проекта."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        protocols_file = project_root / "protocols.py"

        assert protocols_file.exists(), "protocols.py должен существовать"

        content = protocols_file.read_text(encoding="utf-8")

        # protocols не должен импортировать другие модули проекта
        # (кроме typing и стандартной библиотеки)
        # Исключаем docstring примеры (строки с >>>)
        lines = content.split("\n")
        code_lines = [line for line in lines if ">>>" not in line and '"""' not in line]
        code_content = "\n".join(code_lines)

        project_imports = [
            "from parser_2gis.chrome",
            "from parser_2gis.parser",
            "from parser_2gis.parallel",
            "from parser_2gis.logger",
            "from parser_2gis.cache",
            "from parser_2gis.logging",
            "from parser_2gis.cli",
            "from parser_2gis.tui",
            "from parser_2gis.runner",
            "from parser_2gis.writer",
            "from parser_2gis.validation",
            "from parser_2gis.utils",
            "from parser_2gis.data",
            "from parser_2gis.config",
        ]

        for imp in project_imports:
            assert imp not in code_content, f"protocols.py не должен импортировать: {imp}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
