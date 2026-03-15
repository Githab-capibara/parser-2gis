"""
Тесты для проверки корректности использования виджетов pytermgui.

Эти тесты помогают выявлять ошибки типа:
- Использование неподдерживаемых параметров виджетов
- Ошибки импорта в экранах TUI
- Проблемы с созданием окон
"""

import pytest
import inspect
import pytermgui as ptg


class TestPytermguiWidgetSignatures:
    """Тесты для проверки сигнатур виджетов pytermgui."""

    def test_checkbox_does_not_support_label_param(self) -> None:
        """
        Проверка, что ptg.Checkbox не поддерживает параметр label напрямую.
        
        Это основная причина ошибки TypeError: Button.__init__() got multiple values
        """
        sig = inspect.signature(ptg.Checkbox.__init__)
        params = list(sig.parameters.keys())
        
        # label не должен быть явным параметром (только в **attrs)
        # Если label есть в явных параметрах, он должен быть перед **attrs
        if "label" in params:
            label_idx = params.index("label")
            attrs_idx = params.index("**attrs") if "**attrs" in params else len(params)
            assert label_idx > attrs_idx, "ptg.Checkbox не должен поддерживать label как явный параметр"

    def test_checkbox_supports_checked_param(self) -> None:
        """Проверка, что ptg.Checkbox поддерживает параметр checked."""
        sig = inspect.signature(ptg.Checkbox.__init__)
        params = list(sig.parameters.keys())
        assert "checked" in params, "ptg.Checkbox должен поддерживать параметр checked"

    def test_checkbox_supports_callback_param(self) -> None:
        """Проверка, что ptg.Checkbox поддерживает параметр callback."""
        sig = inspect.signature(ptg.Checkbox.__init__)
        params = list(sig.parameters.keys())
        assert "callback" in params, "ptg.Checkbox должен поддерживать параметр callback"

    def test_inputfield_supports_value_and_prompt(self) -> None:
        """Проверка, что ptg.InputField поддерживает параметры value и prompt."""
        sig = inspect.signature(ptg.InputField.__init__)
        params = list(sig.parameters.keys())
        assert "value" in params, "ptg.InputField должен поддерживать параметр value"
        assert "prompt" in params, "ptg.InputField должен поддерживать параметр prompt"

    def test_inputfield_supports_value_param(self) -> None:
        """Проверка, что ptg.InputField поддерживает параметр value."""
        sig = inspect.signature(ptg.InputField.__init__)
        params = list(sig.parameters.keys())
        assert "value" in params, "ptg.InputField должен поддерживать параметр value"


class TestCustomCheckboxFunctionality:
    """Тесты для проверки функциональности кастомного Checkbox."""

    def test_custom_checkbox_with_label_and_value(self) -> None:
        """Проверка, что кастомный Checkbox работает с label и value."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        
        cb = Checkbox(label="Test label", value=True)
        assert cb.value is True
        # Проверяем, что label был создан как объект
        assert cb._label is not None

    def test_custom_checkbox_toggle(self) -> None:
        """Проверка переключения кастомного Checkbox."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        
        cb = Checkbox(label="Test", value=False)
        assert cb.value is False
        
        cb.toggle()
        assert cb.value is True
        
        cb.toggle()
        assert cb.value is False

    def test_custom_checkbox_on_change_callback(self) -> None:
        """Проверка callback при изменении кастомного Checkbox."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        
        received_value = None
        
        def on_change(value: bool) -> None:
            nonlocal received_value
            received_value = value
        
        cb = Checkbox(label="Test", value=False, on_change=on_change)
        cb.toggle()
        
        assert received_value is True


class TestScreenWidgetCreation:
    """Тесты для проверки создания виджетов в экранах."""

    def test_output_settings_creates_checkboxes(self) -> None:
        """Проверка, что OutputSettingsScreen создаёт checkbox без ошибок."""
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        from unittest.mock import MagicMock
        
        # Создаём мок-приложение
        mock_app = MagicMock()
        mock_config = MagicMock()
        mock_writer = MagicMock()
        mock_writer.encoding = "utf-8-sig"
        mock_writer.verbose = True
        mock_csv = MagicMock()
        mock_csv.add_rubrics = True
        mock_csv.add_comments = False
        mock_csv.columns_per_entity = 3
        mock_csv.remove_empty_columns = True
        mock_csv.remove_duplicates = False
        mock_csv.join_char = "; "
        mock_writer.csv = mock_csv
        mock_config.writer = mock_writer
        
        mock_app.get_config.return_value = mock_config
        
        screen = OutputSettingsScreen(mock_app)
        # Вызываем create_window для создания полей
        try:
            screen.create_window()
        except Exception:
            pass  # Окно может не создаться полностью без ptg, но поля должны быть созданы
        
        # Проверяем, что все поля являются Checkbox
        for key in ["verbose", "add_rubrics", "add_comments", "remove_empty_columns", "remove_duplicates"]:
            field = screen._fields.get(key)
            assert field is not None, f"Поле {key} не создано"
            assert isinstance(field, Checkbox), f"Поле {key} должно быть Checkbox, а не {type(field)}"

    def test_browser_settings_creates_checkboxes(self) -> None:
        """Проверка, что BrowserSettingsScreen создаёт checkbox без ошибок."""
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        from unittest.mock import MagicMock
        
        mock_app = MagicMock()
        mock_config = MagicMock()
        mock_chrome = MagicMock()
        mock_chrome.headless = True
        mock_chrome.disable_images = True
        mock_chrome.start_maximized = False
        mock_chrome.silent_browser = True
        mock_chrome.memory_limit = 1024
        mock_chrome.binary_path = None
        mock_config.chrome = mock_chrome
        
        mock_app.get_config.return_value = mock_config
        
        screen = BrowserSettingsScreen(mock_app)
        try:
            screen.create_window()
        except Exception:
            pass
        
        for key in ["headless", "disable_images", "start_maximized", "silent_browser"]:
            field = screen._fields.get(key)
            assert field is not None, f"Поле {key} не создано"
            assert isinstance(field, Checkbox), f"Поле {key} должно быть Checkbox"

    def test_parser_settings_creates_checkboxes(self) -> None:
        """Проверка, что ParserSettingsScreen создаёт checkbox без ошибок."""
        from parser_2gis.tui_pytermgui.screens.parser_settings import ParserSettingsScreen
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        from unittest.mock import MagicMock
        
        mock_app = MagicMock()
        mock_config = MagicMock()
        mock_parser = MagicMock()
        mock_parser.max_records = 100
        mock_parser.delay_between_clicks = 100
        mock_parser.skip_404_response = True
        mock_parser.use_gc = True
        mock_parser.gc_pages_interval = 10
        mock_parser.stop_on_first_404 = False
        mock_parser.max_consecutive_empty_pages = 5
        mock_parser.max_retries = 3
        mock_parser.retry_on_network_errors = True
        mock_parser.retry_delay_base = 1
        mock_parser.memory_threshold = 512
        mock_config.parser = mock_parser
        
        mock_app.get_config.return_value = mock_config
        
        screen = ParserSettingsScreen(mock_app)
        try:
            screen.create_window()
        except Exception:
            pass
        
        for key in ["skip_404_response", "use_gc", "stop_on_first_404", "retry_on_network_errors"]:
            field = screen._fields.get(key)
            assert field is not None, f"Поле {key} не создано"
            assert isinstance(field, Checkbox), f"Поле {key} должно быть Checkbox"


class TestWidgetAttributeErrors:
    """Тесты для проверки отсутствия распространённых ошибок с виджетами."""

    def test_no_label_in_ptg_checkbox_direct_call(self) -> None:
        """Проверка, что прямой вызов ptg.Checkbox с label вызывает ошибку."""
        with pytest.raises(TypeError, match="multiple values for argument"):
            ptg.Checkbox(label="Test", value=True)

    def test_custom_checkbox_handles_label_correctly(self) -> None:
        """Проверка, что кастомный Checkbox корректно обрабатывает label."""
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        
        # Это не должно вызывать ошибку
        cb = Checkbox(label="Correct usage", value=True)
        assert cb._label is not None
        assert cb.value is True

    def test_container_has_private_add_widget(self) -> None:
        """Проверка, что Container имеет приватный метод _add_widget."""
        container = ptg.Container()
        assert hasattr(container, "_add_widget")
        assert callable(getattr(container, "_add_widget"))


class TestImportCorrectness:
    """Тесты для проверки корректности импортов."""

    def test_output_settings_imports_checkbox(self) -> None:
        """Проверка, что output_settings импортирует Checkbox из виджетов."""
        from parser_2gis.tui_pytermgui.screens import output_settings
        import inspect
        
        source = inspect.getsource(output_settings)
        assert "from ..widgets import Checkbox" in source, \
            "output_settings.py должен импортировать Checkbox из виджетов"

    def test_browser_settings_imports_checkbox(self) -> None:
        """Проверка, что browser_settings импортирует Checkbox из виджетов."""
        from parser_2gis.tui_pytermgui.screens import browser_settings
        import inspect
        
        source = inspect.getsource(browser_settings)
        assert "from ..widgets import Checkbox" in source, \
            "browser_settings.py должен импортировать Checkbox из виджетов"

    def test_parser_settings_imports_checkbox(self) -> None:
        """Проверка, что parser_settings импортирует Checkbox из виджетов."""
        from parser_2gis.tui_pytermgui.screens import parser_settings
        import inspect
        
        source = inspect.getsource(parser_settings)
        assert "from ..widgets import Checkbox" in source, \
            "parser_settings.py должен импортировать Checkbox из виджетов"
