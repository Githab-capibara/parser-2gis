"""
Тесты для Application Layer фасадов.

Проверяет:
- Существование ParserFacade, CacheFacade, BrowserFacade
- Использование фасадов в cli/launcher.py
- Корректность работы фасадов
"""

from __future__ import annotations

from pathlib import Path

import pytest

# =============================================================================
# ТЕСТ 1: ParserFacade
# =============================================================================


class TestParserFacade:
    """Тесты для ParserFacade."""

    def test_parser_facade_exists(self) -> None:
        """Проверка существования ParserFacade.

        ParserFacade должен существовать в parser_2gis.application.layer
        и предоставлять единый интерфейс для парсеров.
        """
        from parser_2gis.application.layer import ParserFacade

        assert ParserFacade is not None, "ParserFacade должен существовать"

        # Проверяем что это класс
        assert isinstance(ParserFacade, type), "ParserFacade должен быть классом"

        # Проверяем наличие основных методов
        assert hasattr(ParserFacade, "create_parser"), (
            "ParserFacade должен иметь метод create_parser"
        )
        assert hasattr(ParserFacade, "parse_url"), "ParserFacade должен иметь метод parse_url"

    def test_parser_facade_create_parser(self) -> None:
        """Проверка метода create_parser.

        Метод должен создавать парсер для указанного URL.
        """
        from unittest.mock import MagicMock

        from parser_2gis.application.layer import ParserFacade
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.protocols import BrowserService

        chrome_options = ChromeOptions()
        parser_options = ParserOptions()
        mock_browser = MagicMock(spec=BrowserService)
        mock_browser.add_blocked_requests = MagicMock()

        # Создаём парсер через фасад с mock браузером
        parser = ParserFacade.create_parser(
            url="https://2gis.ru/moscow/search/Аптеки",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        assert parser is not None, "create_parser должен вернуть парсер"

    def test_parser_facade_with_browser_di(self) -> None:
        """Проверка DI через browser параметр.

        ParserFacade должен поддерживать внедрение браузера.
        """
        from unittest.mock import MagicMock

        from parser_2gis.application.layer import ParserFacade
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.options import ParserOptions
        from parser_2gis.protocols import BrowserService

        chrome_options = ChromeOptions()
        parser_options = ParserOptions()
        mock_browser = MagicMock(spec=BrowserService)
        mock_browser.add_blocked_requests = MagicMock()

        # Создаём парсер с внедрённым браузером
        parser = ParserFacade.create_parser(
            url="https://2gis.ru/moscow/search/Аптеки",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        assert parser is not None, "create_parser с browser должен вернуть парсер"


# =============================================================================
# ТЕСТ 2: CacheFacade
# =============================================================================


class TestCacheFacade:
    """Тесты для CacheFacade."""

    def test_cache_facade_exists(self) -> None:
        """Проверка существования CacheFacade.

        CacheFacade должен существовать в parser_2gis.application.layer
        и предоставлять единый интерфейс для кэша.
        """
        from parser_2gis.application.layer import CacheFacade

        assert CacheFacade is not None, "CacheFacade должен существовать"

        # Проверяем что это класс
        assert isinstance(CacheFacade, type), "CacheFacade должен быть классом"

        # Проверяем наличие основных методов
        assert hasattr(CacheFacade, "get"), "CacheFacade должен иметь метод get"
        assert hasattr(CacheFacade, "set"), "CacheFacade должен иметь метод set"
        assert hasattr(CacheFacade, "exists"), "CacheFacade должен иметь метод exists"
        assert hasattr(CacheFacade, "delete"), "CacheFacade должен иметь метод delete"
        assert hasattr(CacheFacade, "close"), "CacheFacade должен иметь метод close"

    def test_cache_facade_operations(self, tmp_path: Path) -> None:
        """Проверка операций кэша.

        CacheFacade должен корректно выполнять операции get/set/delete.
        """
        from parser_2gis.application.layer import CacheFacade

        cache_file = tmp_path / "test_cache"
        facade = CacheFacade(cache_file)

        try:
            # Тест set/get - используем URL как ключ
            test_data = {"key": "test_value", "url": "https://test.com"}
            facade.set("https://test.com", test_data)
            value = facade.get("https://test.com")
            assert value == test_data, "CacheFacade.get должен вернуть установленное значение"

            # Тест exists
            assert facade.exists("https://test.com"), (
                "CacheFacade.exists должен вернуть True для существующего ключа"
            )
            assert not facade.exists("https://nonexistent.com"), (
                "CacheFacade.exists должен вернуть False для несуществующего ключа"
            )

            # Тест delete
            facade.delete("https://test.com")
            assert not facade.exists("https://test.com"), "CacheFacade.delete должен удалить ключ"
        finally:
            facade.close()

    def test_cache_facade_context_manager(self, tmp_path: Path) -> None:
        """Проверка использования как контекстного менеджера.

        CacheFacade должен поддерживать контекстный менеджер.
        """
        from parser_2gis.application.layer import CacheFacade

        cache_file = tmp_path / "test_cache"

        with CacheFacade(cache_file) as facade:
            test_data = {"key": "value", "url": "https://test.com"}
            facade.set("https://test.com", test_data)
            assert facade.get("https://test.com") == test_data


# =============================================================================
# ТЕСТ 3: BrowserFacade
# =============================================================================


class TestBrowserFacade:
    """Тесты для BrowserFacade."""

    def test_browser_facade_exists(self) -> None:
        """Проверка существования BrowserFacade.

        BrowserFacade должен существовать в parser_2gis.application.layer
        и предоставлять единый интерфейс для браузера.
        """
        from parser_2gis.application.layer import BrowserFacade

        assert BrowserFacade is not None, "BrowserFacade должен существовать"

        # Проверяем что это класс
        assert isinstance(BrowserFacade, type), "BrowserFacade должен быть классом"

        # Проверяем наличие основных методов
        assert hasattr(BrowserFacade, "create_browser"), (
            "BrowserFacade должен иметь метод create_browser"
        )
        assert hasattr(BrowserFacade, "navigate"), "BrowserFacade должен иметь метод navigate"
        assert hasattr(BrowserFacade, "get_html"), "BrowserFacade должен иметь метод get_html"
        assert hasattr(BrowserFacade, "execute_js"), "BrowserFacade должен иметь метод execute_js"
        assert hasattr(BrowserFacade, "close"), "BrowserFacade должен иметь метод close"

    def test_browser_facade_create_browser(self) -> None:
        """Проверка метода create_browser.

        Метод должен создавать экземпляр браузера.
        """
        from parser_2gis.application.layer import BrowserFacade
        from parser_2gis.chrome.options import ChromeOptions

        chrome_options = ChromeOptions(headless=True)
        facade = BrowserFacade(chrome_options)

        # Проверяем что браузер создаётся
        # (не запускаем реально, только проверяем наличие метода)
        assert callable(facade.create_browser), "create_browser должен быть вызываемым"


# =============================================================================
# ТЕСТ 4: Использование фасадов в cli/launcher.py
# =============================================================================


class TestFacadesInCLI:
    """Тесты для использования фасадов в cli/launcher.py."""

    def test_facades_used_in_cli(self) -> None:
        """Проверка использования фасадов в cli/launcher.py.

        cli/launcher.py должен использовать фасады из application.layer
        или напрямую импортировать компоненты (CacheManager, ChromeRemote и т.д.).
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        launcher_file = project_root / "cli" / "launcher.py"

        assert launcher_file.exists(), "cli/launcher.py должен существовать"

        content = launcher_file.read_text(encoding="utf-8")

        # Проверяем что launcher использует компоненты парсера
        # Это может быть через фасады или прямой импорт
        has_parser_components = (
            "CacheManager" in content
            or "ChromeRemote" in content
            or "ParallelCityParser" in content
            or "parser_2gis.parser" in content
            or "parser_2gis.cache" in content
            or "parser_2gis.chrome" in content
            or "parser_2gis.parallel" in content
        )

        # Проверяем импорт фасадов (альтернативный вариант)
        has_facade_import = (
            "from parser_2gis.application" in content
            or "ParserFacade" in content
            or "CacheFacade" in content
        )

        # Хотя бы один из вариантов должен присутствовать
        assert has_parser_components or has_facade_import, (
            "cli/launcher.py должен использовать компоненты парсера или фасады"
        )

    def test_facades_are_importable_from_application(self) -> None:
        """Проверка что фасады импортируются из parser_2gis.application.

        Фасады должны быть доступны через пакет application.
        """
        from parser_2gis.application import BrowserFacade, CacheFacade, ParserFacade

        assert ParserFacade is not None
        assert CacheFacade is not None
        assert BrowserFacade is not None

    def test_application_init_exports_facades(self) -> None:
        """Проверка что application/__init__.py экспортирует фасады.

        Фасады должны быть экспортированы из __init__.py пакета.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        application_init = project_root / "application" / "__init__.py"

        assert application_init.exists(), "application/__init__.py должен существовать"

        content = application_init.read_text(encoding="utf-8")

        # Проверяем экспорт фасадов
        assert "ParserFacade" in content, (
            "application/__init__.py должен экспортировать ParserFacade"
        )
        assert "CacheFacade" in content, "application/__init__.py должен экспортировать CacheFacade"
        assert "BrowserFacade" in content, (
            "application/__init__.py должен экспортировать BrowserFacade"
        )

        # Проверяем что __all__ содержит фасады
        assert "__all__" in content, "application/__init__.py должен иметь __all__"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
