"""
Тесты для Dependency Injection.

Проверяет:
- DI через конструктор ParallelCoordinator
- Значения по умолчанию для зависимостей
- DI browser в парсерах
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ТЕСТ 1: DI через конструктор ParallelCoordinator
# =============================================================================


class TestParallelCoordinatorDI:
    """Тесты для DI в ParallelCoordinator."""

    def test_parallel_coordinator_accepts_dependencies(self) -> None:
        """Проверка что ParallelCoordinator принимает зависимости через конструктор.

        ParallelCoordinator должен принимать error_handler и file_merger
        через конструктор для поддержки Dependency Injection.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator
        from parser_2gis.parallel.error_handler import ParallelErrorHandler
        from parser_2gis.parallel.merger import ParallelFileMerger

        # Создаём тестовые данные
        cities: List[Dict[str, Any]] = [
            {"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}
        ]
        categories: List[Dict[str, Any]] = [{"name": "Рестораны", "query": "рестораны"}]
        config = Configuration()

        # Создаём зависимости для DI
        error_handler = ParallelErrorHandler(output_dir="./output", config=config)
        file_merger = ParallelFileMerger(
            output_dir="./output",
            config=config,
            cancel_event=None,  # type: ignore
            lock=None,  # type: ignore
        )

        # Создаём координатор с внедрёнными зависимостями
        coordinator = ParallelCoordinator(
            cities=cities,
            categories=categories,
            output_dir="./output",
            config=config,
            max_workers=2,
            timeout_per_url=300,
            error_handler=error_handler,
            file_merger=file_merger,
        )

        assert coordinator is not None, (
            "ParallelCoordinator должен создаться с внедрёнными зависимостями"
        )

        # Проверяем что зависимости были приняты
        assert coordinator._error_handler is error_handler, (
            "error_handler должен быть внедрён через конструктор"
        )
        assert coordinator._file_merger is file_merger, (
            "file_merger должен быть внедрён через конструктор"
        )

    def test_parallel_coordinator_default_dependencies(self) -> None:
        """Проверка что ParallelCoordinator создаёт зависимости по умолчанию.

        Если зависимости не переданы, ParallelCoordinator должен создать
        их самостоятельно для обратной совместимости.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator
        from parser_2gis.parallel.error_handler import ParallelErrorHandler
        from parser_2gis.parallel.merger import ParallelFileMerger

        # Создаём тестовые данные
        cities: List[Dict[str, Any]] = [
            {"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}
        ]
        categories: List[Dict[str, Any]] = [{"name": "Рестораны", "query": "рестораны"}]
        config = Configuration()

        # Создаём координатор без явных зависимостей
        coordinator = ParallelCoordinator(
            cities=cities,
            categories=categories,
            output_dir="./output",
            config=config,
            max_workers=2,
            timeout_per_url=300,
            # error_handler и file_merger не переданы
        )

        assert coordinator is not None, (
            "ParallelCoordinator должен создаться без явных зависимостей"
        )

        # Проверяем что зависимости созданы по умолчанию
        assert isinstance(coordinator._error_handler, ParallelErrorHandler), (
            "error_handler должен быть создан по умолчанию"
        )
        assert isinstance(coordinator._file_merger, ParallelFileMerger), (
            "file_merger должен быть создан по умолчанию"
        )

    def test_parallel_coordinator_constructor_signature(self) -> None:
        """Проверка сигнатуры конструктора ParallelCoordinator.

        Конструктор должен иметь параметры error_handler и file_merger
        с значениями по умолчанию None.
        """
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        sig = inspect.signature(ParallelCoordinator.__init__)
        params = sig.parameters

        # Проверяем наличие параметров DI
        assert "error_handler" in params, "Конструктор должен иметь параметр error_handler"
        assert "file_merger" in params, "Конструктор должен иметь параметр file_merger"

        # Проверяем что параметры опциональны (None по умолчанию)
        assert params["error_handler"].default is None, "error_handler должен иметь default None"
        assert params["file_merger"].default is None, "file_merger должен иметь default None"


# =============================================================================
# ТЕСТ 2: DI browser в парсерах
# =============================================================================


class TestParserDI:
    """Тесты для DI browser в парсерах."""

    def test_main_page_parser_accepts_browser(self) -> None:
        """Проверка что MainPageParser принимает browser через конструктор.

        MainPageParser должен принимать BrowserService через конструктор
        для поддержки Dependency Injection.
        """
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.parser.parsers.main_parser import MainPageParser
        from parser_2gis.protocols import BrowserService

        chrome_options = ChromeOptions()
        parser_options = ParserOptions()
        mock_browser = MagicMock(spec=BrowserService)
        mock_browser.add_blocked_requests = MagicMock()

        # Создаём парсер с внедрённым браузером
        parser = MainPageParser(
            url="https://2gis.ru/moscow/search/Аптеки",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        assert parser is not None, "MainPageParser должен создаться с внедрённым браузером"

    def test_main_page_parser_constructor_signature(self) -> None:
        """Проверка сигнатуры конструктора MainPageParser.

        Конструктор должен иметь параметр browser с значением по умолчанию None.
        """
        from parser_2gis.parser.parsers.main_parser import MainPageParser

        sig = inspect.signature(MainPageParser.__init__)
        params = sig.parameters

        # Проверяем наличие параметра browser
        assert "browser" in params, "Конструктор должен иметь параметр browser"

        # Проверяем что параметр опционален (None по умолчанию)
        assert params["browser"].default is None, "browser должен иметь default None"

    def test_firm_parser_accepts_browser(self) -> None:
        """Проверка что FirmParser принимает browser через конструктор.

        FirmParser должен принимать BrowserService через конструктор.
        """
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.parser.parsers.firm import FirmParser
        from parser_2gis.protocols import BrowserService

        chrome_options = ChromeOptions()
        parser_options = ParserOptions()
        mock_browser = MagicMock(spec=BrowserService)
        mock_browser.add_blocked_requests = MagicMock()

        # Создаём парсер с внедрённым браузером
        parser = FirmParser(
            url="https://2gis.ru/moscow/firm/123456789",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        assert parser is not None, "FirmParser должен создаться с внедрённым браузером"

    def test_in_building_parser_accepts_browser(self) -> None:
        """Проверка что InBuildingParser принимает browser через конструктор.

        InBuildingParser должен принимать BrowserService через конструктор.
        """
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.parser.parsers.in_building import InBuildingParser
        from parser_2gis.protocols import BrowserService

        chrome_options = ChromeOptions()
        parser_options = ParserOptions()
        mock_browser = MagicMock(spec=BrowserService)
        mock_browser.add_blocked_requests = MagicMock()

        # Создаём парсер с внедрённым браузером
        parser = InBuildingParser(
            url="https://2gis.ru/moscow/building/123456789",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        assert parser is not None, "InBuildingParser должен создаться с внедрённым браузером"


# =============================================================================
# ТЕСТ 3: DI в фабрике парсеров
# =============================================================================


class TestParserFactoryDI:
    """Тесты для DI в фабрике парсеров."""

    def test_get_parser_accepts_browser(self) -> None:
        """Проверка что get_parser принимает browser параметр.

        Фабричная функция get_parser должна принимать browser
        для передачи его в парсер.
        """
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.factory import get_parser
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.protocols import BrowserService

        chrome_options = ChromeOptions()
        parser_options = ParserOptions()
        mock_browser = MagicMock(spec=BrowserService)
        mock_browser.add_blocked_requests = MagicMock()

        # Создаём парсер через фабрику с внедрённым браузером
        parser = get_parser(
            url="https://2gis.ru/moscow/search/Аптеки",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        assert parser is not None, "get_parser должен вернуть парсер с внедрённым браузером"

    def test_get_parser_factory_signature(self) -> None:
        """Проверка сигнатуры функции get_parser.

        Функция должна иметь параметр browser с значением по умолчанию None.
        """
        from parser_2gis.parser.factory import get_parser

        sig = inspect.signature(get_parser)
        params = sig.parameters

        # Проверяем наличие параметра browser
        assert "browser" in params, "get_parser должен иметь параметр browser"

        # Проверяем что параметр опционален (None по умолчанию)
        assert params["browser"].default is None, "browser должен иметь default None"


# =============================================================================
# ТЕСТ 4: DI в ApplicationLauncher
# =============================================================================


class TestApplicationLauncherDI:
    """Тесты для DI в ApplicationLauncher."""

    def test_application_launcher_accepts_signal_handler_factory(self) -> None:
        """Проверка что ApplicationLauncher принимает signal_handler_factory.

        ApplicationLauncher должен принимать signal_handler_factory
        через конструктор для поддержки тестирования.
        """
        from parser_2gis.cli.launcher import ApplicationLauncher
        from parser_2gis.config import Configuration
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.utils.signal_handler import SignalHandler

        config = Configuration()
        options = ParserOptions()

        # Создаём factory для DI
        def mock_factory(cleanup_callback=None) -> SignalHandler:
            mock_handler = MagicMock(spec=SignalHandler)
            mock_handler.setup.return_value = None
            return mock_handler  # type: ignore

        # Создаём лаунчер с внедрённой фабрикой
        launcher = ApplicationLauncher(
            config=config, options=options, signal_handler_factory=mock_factory
        )

        assert launcher is not None, "ApplicationLauncher должен создаться с внедрённой фабрикой"

    def test_application_launcher_default_signal_handler(self) -> None:
        """Проверка что ApplicationLauncher создаёт SignalHandler по умолчанию.

        Если factory не передана, должен использоваться SignalHandler.
        """
        from parser_2gis.cli.launcher import ApplicationLauncher
        from parser_2gis.config import Configuration
        from parser_2gis.parser.options import ParserOptions

        config = Configuration()
        options = ParserOptions()

        # Создаём лаунчер без явной фабрики
        launcher = ApplicationLauncher(
            config=config,
            options=options,
            # signal_handler_factory не передана
        )

        assert launcher is not None, "ApplicationLauncher должен создаться без явной фабрики"

    def test_application_launcher_constructor_signature(self) -> None:
        """Проверка сигнатуры конструктора ApplicationLauncher.

        Конструктор должен иметь параметр signal_handler_factory
        с значением по умолчанию None.
        """
        from parser_2gis.cli.launcher import ApplicationLauncher

        sig = inspect.signature(ApplicationLauncher.__init__)
        params = sig.parameters

        # Проверяем наличие параметра signal_handler_factory
        assert "signal_handler_factory" in params, (
            "Конструктор должен иметь параметр signal_handler_factory"
        )

        # Проверяем что параметр опционален (None по умолчанию)
        assert params["signal_handler_factory"].default is None, (
            "signal_handler_factory должен иметь default None"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
