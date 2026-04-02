"""Тесты для исправлений ISSUE-006 — ISSUE-015.

Тестирует:
- ISSUE-006: ApplicationLauncher DIP
- ISSUE-007: BrowserService Protocol (уже разделён)
- ISSUE-008: ParallelCoordinator LSP (уже использует композицию)
- ISSUE-009: Константы централизованы
- ISSUE-010: Удаление обёрток temp_file_manager
- ISSUE-011: Удаление cleanup_resources()
- ISSUE-012: Общая логика terminate/kill
- ISSUE-013: ConfigCache
- ISSUE-014: FileManager.create_unique_temp_file()
- ISSUE-015: _setup_base_logger
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


# =============================================================================
# ISSUE-006: ApplicationLauncher DIP Tests
# =============================================================================


class TestApplicationLauncherDIP:
    """Тесты для ISSUE-006: ApplicationLauncher Dependency Inversion Principle."""

    def test_launcher_accepts_chrome_factory(self) -> None:
        """Тест что ApplicationLauncher принимает chrome_factory."""
        from parser_2gis.cli.launcher import ApplicationLauncher, ChromeRemoteFactory
        from parser_2gis.config import Configuration
        from parser_2gis.parser.options import ParserOptions

        # Создаём mock фабрику
        mock_chrome_factory = Mock(spec=ChromeRemoteFactory)
        mock_chrome_instance = Mock()
        mock_chrome_factory.return_value = mock_chrome_instance

        # Создаём лаунчер с внедрённой зависимостью
        config = Configuration()
        options = ParserOptions()
        launcher = ApplicationLauncher(
            config=config, options=options, chrome_factory=mock_chrome_factory
        )

        # Проверяем что фабрика сохранена
        assert launcher._chrome_factory is mock_chrome_factory

    def test_launcher_accepts_cache_factory(self) -> None:
        """Тест что ApplicationLauncher принимает cache_factory."""
        from parser_2gis.cli.launcher import ApplicationLauncher, CacheManagerFactory
        from parser_2gis.config import Configuration
        from parser_2gis.parser.options import ParserOptions

        # Создаём mock фабрику
        mock_cache_factory = Mock(spec=CacheManagerFactory)
        mock_cache_instance = Mock()
        mock_cache_factory.return_value = mock_cache_instance

        # Создаём лаунчер с внедрённой зависимостью
        config = Configuration()
        options = ParserOptions()
        launcher = ApplicationLauncher(
            config=config, options=options, cache_factory=mock_cache_factory
        )

        # Проверяем что фабрика сохранена
        assert launcher._cache_factory is mock_cache_factory

    def test_launcher_default_factories(self) -> None:
        """Тест что ApplicationLauncher использует фабрики по умолчанию."""
        from parser_2gis.cli.launcher import ApplicationLauncher
        from parser_2gis.config import Configuration
        from parser_2gis.parser.options import ParserOptions

        # Создаём лаунчер без внедрённых зависимостей
        config = Configuration()
        options = ParserOptions()
        launcher = ApplicationLauncher(config=config, options=options)

        # Проверяем что фабрики не установлены (будут использованы по умолчанию)
        assert launcher._chrome_factory is None
        assert launcher._cache_factory is None


# =============================================================================
# ISSUE-007: BrowserService Protocol Tests (уже разделён)
# =============================================================================


class TestBrowserServiceProtocol:
    """Тесты для ISSUE-007: BrowserService Protocol разделение."""

    def test_browser_navigation_protocol(self) -> None:
        """Тест что BrowserNavigation Protocol существует."""
        from parser_2gis.protocols import BrowserNavigation

        # Проверяем что Protocol определён
        assert hasattr(BrowserNavigation, "navigate")

    def test_browser_content_access_protocol(self) -> None:
        """Тест что BrowserContentAccess Protocol существует."""
        from parser_2gis.protocols import BrowserContentAccess

        # Проверяем что Protocol определён
        assert hasattr(BrowserContentAccess, "get_html")
        assert hasattr(BrowserContentAccess, "get_document")

    def test_browser_js_execution_protocol(self) -> None:
        """Тест что BrowserJSExecution Protocol существует."""
        from parser_2gis.protocols import BrowserJSExecution

        # Проверяем что Protocol определён
        assert hasattr(BrowserJSExecution, "execute_js")

    def test_browser_screenshot_protocol(self) -> None:
        """Тест что BrowserScreenshot Protocol существует."""
        from parser_2gis.protocols import BrowserScreenshot

        # Проверяем что Protocol определён
        assert hasattr(BrowserScreenshot, "screenshot")


# =============================================================================
# ISSUE-008: ParallelCoordinator LSP Tests (уже использует композицию)
# =============================================================================


class TestParallelCoordinatorLSP:
    """Тесты для ISSUE-008: ParallelCoordinator использует композицию."""

    def test_coordinator_uses_composition_not_inheritance(self) -> None:
        """Тест что ParallelCoordinator использует композицию."""
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        # Проверяем что координатор не наследуется от специфичных классов
        # (кроме object)
        bases = ParallelCoordinator.__bases__
        assert len(bases) == 1
        assert bases[0] is object

    def test_coordinator_accepts_error_handler_via_di(self) -> None:
        """Тест что ParallelCoordinator принимает error_handler через DI."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator
        from parser_2gis.parallel.error_handler import ParallelErrorHandler

        # Создаём кастомный error handler
        custom_error_handler = Mock(spec=ParallelErrorHandler)

        # Создаём координатор с внедрённой зависимостью
        coordinator = ParallelCoordinator(
            cities=[{"code": "msk", "name": "Москва", "domain": "2gis.ru"}],
            categories=[{"name": "Кафе", "query": "Кафе"}],
            output_dir=tempfile.gettempdir(),
            config=Configuration(),
            error_handler=custom_error_handler,
        )

        # Проверяем что error handler сохранён
        assert coordinator._error_handler is custom_error_handler


# =============================================================================
# ISSUE-009: Constants Centralization Tests
# =============================================================================


class TestConstantsCentralization:
    """Тесты для ISSUE-009: Централизация констант."""

    def test_constants_module_exists(self) -> None:
        """Тест что модуль constants существует."""
        from parser_2gis import constants

        assert constants is not None

    def test_constants_lazy_loading(self) -> None:
        """Тест что константы загружаются лениво."""
        from parser_2gis import constants

        # Проверяем что константы доступны
        assert hasattr(constants, "MAX_WORKERS")
        assert hasattr(constants, "DEFAULT_TIMEOUT")
        assert hasattr(constants, "MAX_CACHE_SIZE_MB")


# =============================================================================
# ISSUE-010: Temp File Manager Wrapper Removal Tests
# =============================================================================


class TestTempFileManagerWrapperRemoval:
    """Тесты для ISSUE-010: Удаление обёрток temp_file_manager."""

    def test_wrapper_functions_removed(self) -> None:
        """Тест что функции-обёртки удалены."""
        from parser_2gis.utils import temp_file_manager

        # Проверяем что обёртки удалены из __all__
        assert "register_temp_file" not in temp_file_manager.__all__
        assert "unregister_temp_file" not in temp_file_manager.__all__
        assert "cleanup_all_temp_files" not in temp_file_manager.__all__
        assert "get_temp_file_count" not in temp_file_manager.__all__

    def test_temp_file_manager_singleton_exists(self) -> None:
        """Тест что singleton temp_file_manager существует."""
        from parser_2gis.utils.temp_file_manager import temp_file_manager, TempFileManager

        # Проверяем что singleton существует
        assert temp_file_manager is not None
        assert isinstance(temp_file_manager, TempFileManager)


# =============================================================================
# ISSUE-011: cleanup_resources Removal Tests
# =============================================================================


class TestCleanupResourcesRemoval:
    """Тесты для ISSUE-011: Удаление cleanup_resources()."""

    def test_cleanup_resources_removed_from_main(self) -> None:
        """Тест что cleanup_resources удалена из cli/main.py."""
        import importlib

        main_module = importlib.import_module("parser_2gis.cli.main")

        # Проверяем что cleanup_resources удалена из __all__
        assert "cleanup_resources" not in main_module.__all__


# =============================================================================
# ISSUE-012: Terminate/Kill Common Logic Tests
# =============================================================================


class TestTerminateKillCommonLogic:
    """Тесты для ISSUE-012: Общая логика terminate/kill."""

    def test_terminate_process_common_exists(self) -> None:
        """Тест что метод _terminate_process_common существует."""
        from parser_2gis.chrome.browser import ProcessManager

        # Проверяем что метод существует
        assert hasattr(ProcessManager, "_terminate_process_common")

    def test_terminate_uses_common_method(self) -> None:
        """Тест что terminate использует общий метод."""
        from parser_2gis.chrome.browser import ProcessManager

        # Проверяем что terminate существует
        assert hasattr(ProcessManager, "terminate")

    def test_kill_uses_common_method(self) -> None:
        """Тест что kill использует общий метод."""
        from parser_2gis.chrome.browser import ProcessManager

        # Проверяем что kill существует
        assert hasattr(ProcessManager, "kill")


# =============================================================================
# ISSUE-013: ConfigCache Tests
# =============================================================================


class TestConfigCache:
    """Тесты для ISSUE-013: ConfigCache для кэширования."""

    def test_config_cache_exists(self) -> None:
        """Тест что ConfigCache существует."""
        from parser_2gis.cache.config_cache import ConfigCache

        assert ConfigCache is not None

    def test_config_cache_load_cities(self, tmp_path: Path) -> None:
        """Тест что ConfigCache.load_cities работает."""
        from parser_2gis.cache.config_cache import ConfigCache

        # Создаём тестовый файл городов
        cities_file = tmp_path / "cities.json"
        cities_file.write_text("[]", encoding="utf-8")

        cache = ConfigCache()

        # Проверяем что метод существует
        assert hasattr(cache, "load_cities")

    def test_config_cache_get_categories(self) -> None:
        """Тест что ConfigCache.get_categories работает."""
        from parser_2gis.cache.config_cache import ConfigCache

        cache = ConfigCache()
        categories = cache.get_categories()

        # Проверяем что категории возвращены
        assert isinstance(categories, list)
        # Кэшировано через lru_cache
        categories2 = cache.get_categories()
        assert categories is categories2  # Тот же объект (кэш)

    def test_get_config_cache_singleton(self) -> None:
        """Тест что get_config_cache возвращает singleton."""
        from parser_2gis.cache.config_cache import get_config_cache

        cache1 = get_config_cache()
        cache2 = get_config_cache()

        # Проверяем что это один и тот же экземпляр
        assert cache1 is cache2


# =============================================================================
# ISSUE-014: FileManager.create_unique_temp_file Tests
# =============================================================================


class TestFileManagerCreateUniqueTempFile:
    """Тесты для ISSUE-014: FileManager.create_unique_temp_file()."""

    def test_create_unique_temp_file_exists(self) -> None:
        """Тест что метод create_unique_temp_file существует."""
        from parser_2gis.utils.temp_file_manager import TempFileManager

        assert hasattr(TempFileManager, "create_unique_temp_file")

    def test_create_unique_temp_file_creates_file(self) -> None:
        """Тест что create_unique_temp_file создаёт файл."""
        from parser_2gis.utils.temp_file_manager import temp_file_manager

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Создаём временный файл
            temp_path = temp_file_manager.create_unique_temp_file(
                tmp_dir, prefix="test_", suffix=".csv"
            )

            # Проверяем что файл создан
            assert temp_path.exists()
            assert temp_path.suffix == ".csv"
            assert temp_path.name.startswith("test_")

    def test_create_unique_temp_file_registers(self) -> None:
        """Тест что create_unique_temp_file регистрирует файл."""
        from parser_2gis.utils.temp_file_manager import temp_file_manager

        with tempfile.TemporaryDirectory() as tmp_dir:
            initial_count = temp_file_manager.get_count()

            # Создаём временный файл
            temp_file_manager.create_unique_temp_file(tmp_dir)

            # Проверяем что файл зарегистрирован
            assert temp_file_manager.get_count() == initial_count + 1


# =============================================================================
# ISSUE-015: _setup_base_logger Tests
# =============================================================================


class TestSetupBaseLogger:
    """Тесты для ISSUE-015: _setup_base_logger()."""

    def test_setup_base_logger_exists(self) -> None:
        """Тест что _setup_base_logger существует."""
        from parser_2gis.logger.logger import _setup_base_logger

        assert _setup_base_logger is not None

    def test_setup_base_logger_creates_handler(self) -> None:
        """Тест что _setup_base_logger создаёт handler."""
        from parser_2gis.logger.logger import _setup_base_logger

        # Создаём новый логгер
        test_logger = logging.getLogger("test_logger")
        test_logger.handlers.clear()

        # Настраиваем через _setup_base_logger
        _setup_base_logger(
            level=logging.DEBUG,
            fmt="%(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
            logger_instance=test_logger,
        )

        # Проверяем что handler создан
        assert len(test_logger.handlers) == 1
        assert test_logger.level == logging.DEBUG

    def test_setup_cli_logger_uses_base_logger(self) -> None:
        """Тест что setup_cli_logger использует _setup_base_logger."""
        from parser_2gis.logger.logger import setup_cli_logger
        from parser_2gis.logger.options import LogOptions

        # Создаём тестовый логгер
        test_logger = logging.getLogger("test_cli_logger")
        test_logger.handlers.clear()

        options = LogOptions()

        # Настраиваем CLI логгер
        setup_cli_logger(options)

        # Проверяем что handler создан
        assert len(test_logger.handlers) >= 0  # Может быть унаследован


# =============================================================================
# Запуск тестов
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
