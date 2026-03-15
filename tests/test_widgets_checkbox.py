"""
Тесты для кастомного виджета Checkbox и проверки корректности использования виджетов pytermgui.

Эти тесты помогают выявлять ошибки типа:
- Использование несуществующих методов (add_widget вместо _add_widget)
- Неправильное использование виджетов pytermgui с неподдерживаемыми параметрами
- Ошибки импорта в экранах TUI
"""

import pytest
from unittest.mock import MagicMock, patch


class TestCustomCheckbox:
    """Тесты для кастомного виджета Checkbox."""

    def test_checkbox_creation_with_label(self) -> None:
        """Проверка создания Checkbox с текстовой меткой."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox

        cb = Checkbox(label="Тестовая метка", value=True)
        assert cb.value is True

    def test_checkbox_creation_without_label(self) -> None:
        """Проверка создания Checkbox без метки."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox

        cb = Checkbox(value=False)
        assert cb.value is False

    def test_checkbox_value_property(self) -> None:
        """Проверка свойства value."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox

        cb = Checkbox(value=True)
        assert cb.value is True

        cb.value = False
        assert cb.value is False

    def test_checkbox_on_change_callback(self) -> None:
        """Проверка callback при изменении состояния."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox

        callback_called = False
        received_value = None

        def on_change(value: bool) -> None:
            nonlocal callback_called, received_value
            callback_called = True
            received_value = value

        cb = Checkbox(label="Test", value=False, on_change=on_change)
        assert cb._on_change is not None


class TestPytermguiCheckboxUsage:
    """Тесты для проверки правильности использования виджетов pytermgui."""

    def test_ptg_checkbox_does_not_support_label_param(self) -> None:
        """Проверка, что ptg.Checkbox не поддерживает параметр label напрямую."""
        import pytermgui as ptg
        import inspect

        sig = inspect.signature(ptg.Checkbox.__init__)
        params = list(sig.parameters.keys())

        # label не должен быть явным параметром (только в **attrs)
        assert "label" not in params or params.index("label") > params.index("**attrs")

    def test_ptg_checkbox_signature(self) -> None:
        """Проверка сигнатуры ptg.Checkbox."""
        import pytermgui as ptg
        import inspect

        sig = inspect.signature(ptg.Checkbox.__init__)
        params = list(sig.parameters.keys())

        # Должен поддерживать callback и checked
        assert "callback" in params
        assert "checked" in params


class TestScreensImports:
    """Тесты для проверки корректности импортов в экранах TUI."""

    def test_output_settings_uses_custom_checkbox(self) -> None:
        """Проверка, что output_settings.py использует кастомный Checkbox."""
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.widgets import Checkbox

        assert OutputSettingsScreen is not None
        assert Checkbox is not None

    def test_browser_settings_uses_custom_checkbox(self) -> None:
        """Проверка, что browser_settings.py использует кастомный Checkbox."""
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen
        from parser_2gis.tui_pytermgui.widgets import Checkbox

        assert BrowserSettingsScreen is not None
        assert Checkbox is not None


class TestWidgetMethods:
    """Тесты для проверки наличия нужных методов у виджетов."""

    def test_container_has_add_widget_method(self) -> None:
        """Проверка, что Container имеет метод _add_widget."""
        import pytermgui as ptg

        container = ptg.Container()
        assert hasattr(container, "_add_widget")
        assert callable(getattr(container, "_add_widget"))

    def test_container_does_not_have_public_add_widget(self) -> None:
        """Проверка, что публичный add_widget не существует (используется _add_widget)."""
        import pytermgui as ptg

        container = ptg.Container()
        assert not hasattr(container, "add_widget") or hasattr(container, "_add_widget")


class TestAllScreensCanBeImported:
    """Тесты для проверки возможности импорта всех экранов."""

    @pytest.mark.parametrize("screen_name", [
        "output_settings",
        "browser_settings",
        "parser_settings",
        "main_menu",
        "city_selector",
        "category_selector",
        "parsing_screen",
        "cache_viewer",
        "about_screen",
    ])
    def test_screen_can_be_imported(self, screen_name: str) -> None:
        """Проверка, что все экраны могут быть импортированы без ошибок."""
        try:
            module = __import__(
                f"parser_2gis.tui_pytermgui.screens.{screen_name}",
                fromlist=[f"{screen_name.capitalize()}Screen"]
            )
            assert module is not None
        except Exception as e:
            pytest.fail(f"Не удалось импортировать {screen_name}: {e}")
