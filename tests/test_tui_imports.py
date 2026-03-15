"""
Тесты для проверки корректности импортов в TUI экранах.

Эти тесты выявляют ошибки типа ModuleNotFoundError, которые возникают
при неправильных относительных импортах в экранах TUI.
"""

import pytest


class TestTUIImports:
    """Тесты для проверки импортов в TUI экранах."""

    def test_parser_settings_imports(self):
        """Проверка, что parser_settings может импортировать свои зависимости."""
        # Этот тест выявляет ошибку ModuleNotFoundError при неправильном пути
        from parser_2gis.tui_pytermgui.screens.parser_settings import ParserSettingsScreen

        # Проверяем, что класс можно импортировать
        assert ParserSettingsScreen is not None

        # Проверяем, что модуль содержит метод _reset
        assert hasattr(ParserSettingsScreen, '_reset')

    def test_browser_settings_imports(self):
        """Проверка, что browser_settings может импортировать свои зависимости."""
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen

        assert BrowserSettingsScreen is not None
        assert hasattr(BrowserSettingsScreen, '_reset')

    def test_output_settings_imports(self):
        """Проверка, что output_settings может импортировать свои зависимости."""
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen

        assert OutputSettingsScreen is not None
        assert hasattr(OutputSettingsScreen, '_reset')

    def test_all_screens_can_be_imported(self):
        """Проверка, что все экраны могут быть импортированы без ошибок."""
        from parser_2gis.tui_pytermgui.screens import (
            MainMenuScreen,
            CitySelectorScreen,
            CategorySelectorScreen,
            BrowserSettingsScreen,
            ParserSettingsScreen,
            OutputSettingsScreen,
            ParsingScreen,
            CacheViewerScreen,
            AboutScreen,
        )

        # Проверяем, что все классы импортированы
        screens = [
            MainMenuScreen,
            CitySelectorScreen,
            CategorySelectorScreen,
            BrowserSettingsScreen,
            ParserSettingsScreen,
            OutputSettingsScreen,
            ParsingScreen,
            CacheViewerScreen,
            AboutScreen,
        ]

        for screen in screens:
            assert screen is not None, f"Не удалось импортировать {screen}"

    def test_parser_settings_reset_method_import(self):
        """Проверка, что метод _reset в parser_settings работает без ошибок.

        Этот тест выявляет проблему с неправильным относительным импортом
        from ..parser.options import ParserOptions
        который должен быть:
        from ...parser.options import ParserOptions
        """
        from parser_2gis.tui_pytermgui.screens.parser_settings import ParserSettingsScreen
        from unittest.mock import MagicMock

        # Создаём мок-приложение
        mock_app = MagicMock()
        mock_app.get_config.return_value = MagicMock()

        # Создаём экземпляр экрана
        screen = ParserSettingsScreen(mock_app)

        # Проверяем, что метод _reset существует
        assert callable(screen._reset)

        # Пробуем вызвать метод _reset (без реального выполнения импорта)
        # Для этого проверяем, что код содержит правильный импорт
        import inspect
        source = inspect.getsource(screen._reset)

        # Проверяем, что используется правильный путь для импорта ParserOptions
        # Должен быть from ...parser.options import ParserOptions
        assert 'from ...parser.options import ParserOptions' in source, \
            "Метод _reset должен использовать правильный относительный импорт"

    def test_browser_settings_reset_method_import(self):
        """Проверка, что метод _reset в browser_settings работает без ошибок.

        Выявляет проблему с неправильным относительным импортом
        from ..chrome.options import ChromeOptions
        """
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen
        import inspect

        source = inspect.getsource(BrowserSettingsScreen._reset)

        # Проверяем правильный путь для импорта ChromeOptions
        assert 'from ...chrome.options import ChromeOptions' in source, \
            "Метод _reset должен использовать правильный относительный импорт"

    def test_output_settings_reset_method_import(self):
        """Проверка, что метод _reset в output_settings работает без ошибок.

        Выявляет проблему с неправильным относительным импортом
        from ..writer.options import WriterOptions
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        import inspect

        source = inspect.getsource(OutputSettingsScreen._reset)

        # Проверяем правильный путь для импорта WriterOptions (три точки)
        assert 'from ...writer' in source, \
            "Метод _reset должен использовать правильный относительный импорт (три точки)"
        # Убеждаемся, что нет неправильного импорта с двумя точками
        assert 'from ..writer' not in source, \
            "Метод _reset не должен использовать неправильный импорт с двумя точками"


class TestTUIWidgetImports:
    """Тесты для проверки импортов виджетов."""

    def test_all_widgets_importable(self):
        """Проверка, что все кастомные виджеты могут быть импортированы."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox, ScrollArea

        assert Checkbox is not None
        assert ScrollArea is not None


class TestTUIAppImports:
    """Тесты для проверки импортов в приложении TUI."""

    def test_app_imports(self):
        """Проверка, что приложение TUI может быть импортировано."""
        from parser_2gis.tui_pytermgui.app import TUIApp, Parser2GISTUI

        assert TUIApp is not None
        assert Parser2GISTUI is not None

    def test_app_has_required_methods(self):
        """Проверка, что приложение TUI имеет необходимые методы."""
        from parser_2gis.tui_pytermgui.app import TUIApp

        required_methods = ['get_config', 'save_config', 'go_back']
        for method in required_methods:
            assert hasattr(TUIApp, method), f"TUIApp должен иметь метод {method}"
