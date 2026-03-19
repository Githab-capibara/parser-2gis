"""
Тесты для исправлений TUI компонентов.
Проверяют наличие исправлений в исходном коде.
"""

import inspect


class TestContainerWidgetAccessFixes:
    """Тесты исправлений доступа к виджетам Container."""

    def test_category_list_has_safe_widget_access(self):
        """CategoryList использует hasattr для безопасного доступа."""
        from parser_2gis.tui_pytermgui.widgets import category_list

        source = inspect.getsource(category_list.CategoryList._populate)
        assert "hasattr" in source

    def test_city_list_has_safe_widget_access(self):
        """CityList использует hasattr для безопасного доступа."""
        from parser_2gis.tui_pytermgui.widgets import city_list

        source = inspect.getsource(city_list.CityList._populate)
        assert "hasattr" in source

    def test_city_selector_has_safe_widgets_access(self):
        """CitySelectorScreen использует getattr для widgets."""
        from parser_2gis.tui_pytermgui.screens import city_selector

        source = inspect.getsource(city_selector.CitySelectorScreen._update_counter)
        assert "getattr" in source or "_widgets" in source


class TestUnionTypeHandlingFixes:
    """Тесты исправлений Union типов."""

    def test_browser_settings_has_isinstance_check(self):
        """BrowserSettingsScreen проверяет тип перед strip()."""
        from parser_2gis.tui_pytermgui.screens import browser_settings

        source = inspect.getsource(browser_settings.BrowserSettingsScreen._save)
        assert "isinstance" in source and "str" in source


class TestCallableTypeAnnotationFixes:
    """Тесты исправлений аннотаций Callable."""

    def test_main_menu_uses_callable_capitalized(self):
        """MainMenuScreen использует Callable с заглавной буквы."""
        from parser_2gis.tui_pytermgui.screens import main_menu

        source = inspect.getsource(main_menu.MainMenuScreen)
        assert "Callable" in source


class TestNoneValueHandlingFixes:
    """Тесты исправлений обработки None значений."""

    def test_animation_has_duration_check(self):
        """SpinnerAnimation.animate_generator проверяет duration на None."""
        from parser_2gis.tui_pytermgui.utils import SpinnerAnimation

        source = inspect.getsource(SpinnerAnimation.animate_generator)
        assert "duration is not None" in source or "if duration" in source


class TestShowMessageImplementationFixes:
    """Тесты реализации _show_message."""

    def test_browser_settings_show_message_not_pass(self):
        """BrowserSettingsScreen._show_message не заглушка."""
        from parser_2gis.tui_pytermgui.screens import browser_settings

        source = inspect.getsource(browser_settings.BrowserSettingsScreen._show_message)
        assert "pass" not in source or "notify" in source

    def test_output_settings_show_message_not_pass(self):
        """OutputSettingsScreen._show_message не заглушка."""
        from parser_2gis.tui_pytermgui.screens import output_settings

        source = inspect.getsource(output_settings.OutputSettingsScreen._show_message)
        assert "pass" not in source or "notify" in source


class TestRunParallelTimeoutFixes:
    """Тесты исправлений timeout в run_parallel."""

    def test_run_parallel_no_parser_timeout(self):
        """run_parallel не устанавливает config.parser.timeout."""
        from parser_2gis.tui_pytermgui import run_parallel

        source = inspect.getsource(run_parallel.run_parallel_with_tui)
        assert "config.parser.timeout =" not in source


class TestTUIImportFixes:
    """Тесты исправлений импортов TUI."""

    def test_parsing_screen_no_monitor_import(self):
        """ParsingScreen не импортирует Monitor."""
        from parser_2gis.tui_pytermgui.screens import parsing_screen

        source = inspect.getsource(parsing_screen)
        assert "from pytermgui import Monitor" not in source

    def test_unicodeicons_has_emoji_start(self):
        """UnicodeIcons имеет EMOJI_START."""
        from parser_2gis.tui_pytermgui.utils import UnicodeIcons

        assert hasattr(UnicodeIcons, "EMOJI_START")


class TestSignalHandlerLockFixes:
    """Тесты исправлений SignalHandler lock."""

    def test_signal_handler_has_lock(self):
        """SignalHandler имеет _lock атрибут."""
        from parser_2gis.signal_handler import SignalHandler

        handler = SignalHandler(cleanup_callback=lambda: None)
        assert hasattr(handler, "_lock")

    def test_signal_handler_lock_type(self):
        """SignalHandler._lock это threading.Lock."""
        import threading

        from parser_2gis.signal_handler import SignalHandler

        handler = SignalHandler(cleanup_callback=lambda: None)
        assert isinstance(handler._lock, type(threading.Lock()))


class TestConfigParallelMaxWorkersFixes:
    """Тесты использования config.parallel.max_workers."""

    def test_app_uses_parallel_max_workers(self):
        """TUIApp использует config.parallel.max_workers."""
        from parser_2gis.tui_pytermgui.app import TUIApp

        source = inspect.getsource(TUIApp)
        assert "parallel.max_workers" in source
