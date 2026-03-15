"""
Тесты для проверки работы фокуса в TUI приложении Parser2GIS.

Проверяет корректность работы с фокусом виджетов pytermgui,
особенно InputField, который не имеет метода focus().
"""

import pytest
import pytermgui as ptg

# Импорты для тестирования
from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
from parser_2gis.tui_pytermgui.widgets import NavigableContainer, NavigableWidget


class MockTUIApp:
    """
    Мок объекта TUIApp для тестирования.
    
    Предоставляет минимальный интерфейс, необходимый для работы экранов.
    """
    
    def __init__(self):
        """Инициализация мок-объекта приложения."""
        self.selected_cities = []
        self.selected_categories = []
        self._manager = None
        self._current_screen = None
        
    def get_cities(self):
        """Вернуть список городов для тестирования."""
        return [
            {"name": "Москва", "country_code": "RU"},
            {"name": "Санкт-Петербург", "country_code": "RU"},
            {"name": "Новосибирск", "country_code": "RU"},
        ]
    
    def get_categories(self):
        """Вернуть список категорий для тестирования."""
        return [
            {"name": "Рестораны"},
            {"name": "Кафе"},
            {"name": "Бары"},
        ]
    
    def go_back(self):
        """Заглушка для метода возврата назад."""
        pass
    
    def _show_category_selector(self):
        """Заглушка для метода показа селектора категорий."""
        pass


class TestInputFieldNoFocusMethod:
    """
    Тест 1: Проверка что InputField не имеет метода focus().
    
    Защита от регрессии API pytermgui.
    """
    
    def test_inputfield_has_no_focus_method(self):
        """
        Проверить что у InputField нет метода focus().
        
        Это тест на защиту от регрессии - если в будущих версиях
        pytermgui добавят метод focus(), тест упадёт и нужно будет
        пересмотреть логику работы с фокусом.
        """
        input_field = ptg.InputField(placeholder="Тест")
        
        # У InputField не должно быть метода focus()
        assert not hasattr(input_field, 'focus'), \
            "InputField не должен иметь метод focus() - это изменит API"
        
        # Проверяем что есть свойство value для работы с текстом
        assert hasattr(input_field, 'value'), \
            "InputField должен иметь свойство value"
        
        # Проверяем что есть метод handle_key для обработки ввода
        assert hasattr(input_field, 'handle_key'), \
            "InputField должен иметь метод handle_key"


class TestCitySelectorCreation:
    """
    Тест 2: Проверка корректного создания CitySelectorScreen.
    
    Проверяет что экран создаётся без ошибок AttributeError.
    """
    
    def test_city_selector_screen_creation_no_attribute_error(self):
        """
        Проверить что CitySelectorScreen создаётся без AttributeError.
        
        Ранее был баг с вызовом несуществующего метода focus() у InputField.
        Этот тест защищает от регрессии.
        """
        mock_app = MockTUIApp()
        
        # Создание экрана не должно вызывать AttributeError
        screen = CitySelectorScreen(mock_app)
        
        # Проверка что экран создан
        assert screen is not None
        
        # Создаём окно чтобы инициализировать _search_field
        window = screen.create_window()
        
        # Проверка что search_field создан и является InputField
        assert screen._search_field is not None
        assert isinstance(screen._search_field, ptg.InputField)
        
        # Проверка что у search_field нет метода focus()
        assert not hasattr(screen._search_field, 'focus'), \
            "InputField не должен иметь метод focus()"
        
        # Проверка что окно создано
        assert window is not None
        assert isinstance(window, ptg.Window)


class TestCreateWindowNoAttributeError:
    """
    Тест 3: Проверка что create_window() не вызывает AttributeError.
    
    Проверяет что метод create_window() работает корректно
    и не пытается вызвать несуществующий метод focus().
    """
    
    def test_city_selector_create_window_no_attribute_error(self):
        """
        Проверить что create_window() не вызывает AttributeError.
        
        Тест проверяет что окно создаётся без попытки вызвать
        несуществующий метод focus() у InputField.
        """
        mock_app = MockTUIApp()
        screen = CitySelectorScreen(mock_app)
        
        # Создание окна не должно вызывать AttributeError
        window = screen.create_window()
        
        # Проверка что окно создано
        assert window is not None
        assert isinstance(window, ptg.Window)
        
    def test_category_selector_create_window_no_attribute_error(self):
        """
        Проверить что create_window() в CategorySelectorScreen не вызывает AttributeError.
        
        Аналогичный тест для экрана выбора категорий.
        """
        mock_app = MockTUIApp()
        screen = CategorySelectorScreen(mock_app)
        
        # Создание окна не должно вызывать AttributeError
        window = screen.create_window()
        
        # Проверка что окно создано
        assert window is not None
        assert isinstance(window, ptg.Window)


class TestCorrectFocusMethodInPytermgui:
    """
    Тест 4: Проверка наличия правильного метода для установки фокуса в pytermgui.
    
    Проверяет что WindowManager имеет метод focus() для работы с окнами.
    """
    
    def test_windowmanager_has_focus_method(self):
        """
        Проверить что WindowManager имеет метод focus().
        
        В pytermgui фокус управляется через WindowManager,
        а не напрямую через виджеты.
        """
        manager = ptg.WindowManager()
        
        # У WindowManager должен быть метод focus()
        assert hasattr(manager, 'focus'), \
            "WindowManager должен иметь метод focus()"
        
        # Метод focus() должен быть вызываемым
        assert callable(getattr(manager, 'focus')), \
            "focus должен быть вызываемым методом"
    
    def test_inputfield_has_handle_key_method(self):
        """
        Проверить что InputField имеет метод handle_key().
        
        InputField обрабатывает ввод через handle_key(),
        а не через метод focus().
        """
        input_field = ptg.InputField(placeholder="Тест")
        
        # У InputField должен быть метод handle_key()
        assert hasattr(input_field, 'handle_key'), \
            "InputField должен иметь метод handle_key()"
        
        # Метод handle_key() должен быть вызываемым
        assert callable(input_field.handle_key), \
            "handle_key должен быть вызываемым методом"


class TestCitySelectorIntegration:
    """
    Тест 5: Интеграционный тест для CitySelectorScreen.
    
    Проверяет что окно city_selector создаётся и может быть
    добавлено в WindowManager.
    """
    
    def test_city_selector_window_can_be_added_to_windowmanager(self):
        """
        Проверить что окно city_selector может быть добавлено в WindowManager.
        
        Интеграционный тест проверяет полную совместимость
        экрана с системой окон pytermgui.
        """
        mock_app = MockTUIApp()
        screen = CitySelectorScreen(mock_app)
        
        # Создаём окно
        window = screen.create_window()
        
        # Создаём WindowManager
        manager = ptg.WindowManager()
        
        # Добавляем окно в менеджер - не должно вызывать ошибок
        manager.add(window)
        
        # Проверка что окно добавлено
        assert len(manager._windows) == 1
        assert manager._windows[0] is window
    
    def test_category_selector_window_can_be_added_to_windowmanager(self):
        """
        Проверить что окно category_selector может быть добавлено в WindowManager.
        
        Аналогичный интеграционный тест для экрана выбора категорий.
        """
        mock_app = MockTUIApp()
        screen = CategorySelectorScreen(mock_app)
        
        # Создаём окно
        window = screen.create_window()
        
        # Создаём WindowManager
        manager = ptg.WindowManager()
        
        # Добавляем окно в менеджер - не должно вызывать ошибок
        manager.add(window)
        
        # Проверка что окно добавлено
        assert len(manager._windows) == 1
        assert manager._windows[0] is window


class TestNavigableWidgetFocusProperty:
    """
    Дополнительные тесты для проверки работы фокуса в NavigableWidget.
    """
    
    def test_navigable_widget_has_focused_property(self):
        """
        Проверить что NavigableWidget имеет свойство focused.
        
        NavigableWidget использует свойство focused вместо метода focus().
        """
        widget = NavigableWidget()
        
        # Проверка наличия свойства focused
        assert hasattr(widget, 'focused'), \
            "NavigableWidget должен иметь свойство focused"
        
        # Проверка что focused имеет булево значение
        assert isinstance(widget.focused, bool), \
            "focused должен быть булевым значением"
    
    def test_navigable_widget_focus_blur_methods(self):
        """
        Проверить что NavigableWidget имеет методы focus() и blur().
        
        Эти методы используются для управления фокусом.
        """
        widget = NavigableWidget()
        
        # Проверка наличия методов
        assert hasattr(widget, 'focus'), \
            "NavigableWidget должен иметь метод focus()"
        assert hasattr(widget, 'blur'), \
            "NavigableWidget должен иметь метод blur()"
        
        # Проверка что методы вызываемы
        assert callable(widget.focus), \
            "focus должен быть вызываемым методом"
        assert callable(widget.blur), \
            "blur должен быть вызываемым методом"
        
        # Проверка работы методов
        widget.focus()
        assert widget.focused is True
        
        widget.blur()
        assert widget.focused is False
    
    def test_navigable_container_sets_focus_via_property(self):
        """
        Проверить что NavigableContainer устанавливает фокус через свойство focused.
        
        Тест проверяет что контейнер корректно управляет фокусом
        дочерних виджетов через свойство focused, а не через метод focus().
        """
        container = NavigableContainer()
        
        # Добавляем виджеты
        widget1 = NavigableWidget()
        widget2 = NavigableWidget()
        container.add_widget(widget1)
        container.add_widget(widget2)
        
        # Устанавливаем фокус на первый виджет
        container.focus_index = 0
        
        # Проверка что фокус установлен
        assert container.focus_index == 0
        assert widget1.focused is True
        assert widget2.focused is False
        
        # Переключаем фокус на второй виджет
        container.focus_index = 1
        
        # Проверка что фокус переключен
        assert container.focus_index == 1
        assert widget1.focused is False
        assert widget2.focused is True
