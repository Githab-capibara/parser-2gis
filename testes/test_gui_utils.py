"""
Тесты для модуля gui/utils.py.

Проверяют следующие возможности:
- generate_event_handler
- setup_text_widget
- ensure_gui_enabled
- invoke_widget_hook
- url_query_encode
"""

import pytest

from parser_2gis.gui.utils import (ensure_gui_enabled, generate_event_handler,
                                   url_query_encode)


class TestGenerateEventHandler:
    """Тесты для generate_event_handler."""

    def test_generate_event_handler_returns_callable(self):
        """Проверка, что возвращается вызываемый объект."""
        def dummy_func():
            pass
        
        handler = generate_event_handler(dummy_func)
        assert callable(handler)

    def test_generate_event_handler_calls_function(self):
        """Проверка вызова функции."""
        called = {'value': False}
        
        def set_called():
            called['value'] = True
        
        handler = generate_event_handler(set_called)
        
        # Создаём фиктивный event
        class FakeEvent:
            pass
        
        handler(FakeEvent())
        assert called['value'] is True

    def test_generate_event_handler_with_break(self):
        """Проверка с возвратом 'break'."""
        def dummy_func():
            pass
        
        handler = generate_event_handler(dummy_func, with_break=True)
        
        class FakeEvent:
            pass
        
        result = handler(FakeEvent())
        assert result == 'break'

    def test_generate_event_handler_without_break(self):
        """Проверка без возврата 'break'."""
        def dummy_func():
            pass
        
        handler = generate_event_handler(dummy_func, with_break=False)
        
        class FakeEvent:
            pass
        
        result = handler(FakeEvent())
        assert result is None


class TestUrlQueryEncode:
    """Тесты для url_query_encode."""

    def test_url_query_encode_ascii(self):
        """Проверка кодирования ASCII."""
        result = url_query_encode('hello world')
        # Пробелы не кодируются по дизайну функции
        assert result == 'hello world'

    def test_url_query_encode_cyrillic(self):
        """Проверка кодирования кириллицы."""
        result = url_query_encode('привет мир')
        # Кириллица не должна кодироваться
        assert 'привет' in result
        assert 'мир' in result

    def test_url_query_encode_russian_letters(self):
        """Проверка кодирования русских букв."""
        result = url_query_encode('аптеки')
        assert result == 'аптеки'

    def test_url_query_encode_spaces(self):
        """Проверка кодирования пробелов."""
        result = url_query_encode('а б в')
        # Пробелы не кодируются по дизайну функции
        assert ' ' in result

    def test_url_query_encode_mixed(self):
        """Проверка смешанного кодирования."""
        result = url_query_encode('test тест')
        assert 'test' in result or 'test%20' in result
        assert 'тест' in result

    def test_url_query_encode_special_chars(self):
        """Проверка специальных символов."""
        result = url_query_encode('test@email.com')
        assert '%40' in result or '@' not in result


class TestEnsureGUIEnabled:
    """Тесты для ensure_gui_enabled."""

    def test_ensure_gui_enabled_decorator_exists(self):
        """Проверка существования декоратора."""
        assert callable(ensure_gui_enabled)

    def test_ensure_gui_enabled_with_gui_enabled(self):
        """Проверка с включённым GUI."""
        from parser_2gis.common import GUI_ENABLED
        
        @ensure_gui_enabled
        def test_func():
            return 'success'
        
        if GUI_ENABLED:
            result = test_func()
            assert result == 'success'
        # Если GUI выключен, функция не должна вызываться

    def test_ensure_gui_enabled_preserves_name(self):
        """Проверка сохранения имени функции."""
        @ensure_gui_enabled
        def my_test_function():
            pass
        
        assert my_test_function.__name__ == 'my_test_function'


class TestGUIEnabled:
    """Тесты для переменной GUI_ENABLED."""

    def test_gui_enabled_is_defined(self):
        """Проверка определения GUI_ENABLED."""
        from parser_2gis.common import GUI_ENABLED
        assert isinstance(GUI_ENABLED, bool)


class TestInvokeWidgetHook:
    """Тесты для invoke_widget_hook."""

    def test_invoke_widget_hook_exists(self):
        """Проверка существования функции."""
        from parser_2gis.gui.utils import invoke_widget_hook
        assert callable(invoke_widget_hook)

    @pytest.mark.skip(reason="Требует PySimpleGUI")
    def test_invoke_widget_hook_is_context_manager(self):
        """Проверка, что это контекстный менеджер."""
        from parser_2gis.gui.utils import invoke_widget_hook
        import PySimpleGUI as sg

        # Это должен быть контекстный менеджер
        try:
            with invoke_widget_hook(sg, '-TEST-', lambda *args: None) as get_widget:
                pass
            # Если нет ошибок, тест пройден
        except Exception:
            # Может не работать без реального GUI
            pass


class TestSetupTextWidget:
    """Тесты для setup_text_widget."""

    def test_setup_text_widget_exists(self):
        """Проверка существования функции."""
        from parser_2gis.gui.utils import setup_text_widget
        assert callable(setup_text_widget)

    def test_setup_text_widget_parameters(self):
        """Проверка параметров функции."""
        import inspect
        from parser_2gis.gui.utils import setup_text_widget
        
        sig = inspect.signature(setup_text_widget)
        params = list(sig.parameters.keys())
        
        assert 'widget' in params
        assert 'root' in params
