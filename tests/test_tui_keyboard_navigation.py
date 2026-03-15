#!/usr/bin/env python3
"""
Тесты для проверки навигации TUI с клавиатуры.

Эти тесты проверяют обработку клавиш навигации:
- Esc - возврат назад
- Tab - переключение фокуса вперёд
- Shift+Tab - переключение фокуса назад
- Enter - активация элементов (checkbox, кнопки)
- Навигация по всем экранам

Тесты автономны и не требуют GUI. Все зависимости мокаются.

Примечание:
    Тесты требуют установки pytermgui:
    pip install pytermgui

    Если pytermgui не установлен, тесты будут пропущены.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent.parent))

# Проверяем доступность pytermgui
PYTERMGUI_AVAILABLE = False
try:
    import pytermgui as ptg
    PYTERMGUI_AVAILABLE = True
except ImportError:
    pass

# Пропускаем все тесты в этом файле, если pytermgui не установлен
pytestmark = pytest.mark.skipif(
    not PYTERMGUI_AVAILABLE,
    reason="pytermgui не установлен. Установите: pip install pytermgui"
)

# Условные импорты - выполняются только если pytermgui доступен
if PYTERMGUI_AVAILABLE:
    from parser_2gis.tui_pytermgui.widgets.navigable_widget import (
        NavigableWidget,
        NavigableContainer,
        ButtonWidget,
    )
    from parser_2gis.tui_pytermgui.widgets.checkbox import Checkbox
    from parser_2gis.tui_pytermgui.app import TUIApp
    from parser_2gis.tui_pytermgui.utils.navigation import ScreenManager


class TestEscKeyHandling:
    """
    Тесты обработки клавиши Esc.
    
    Проверяют, что клавиша Esc вызывает возврат назад к предыдущему экрану.
    """

    def test_esc_key_calls_go_back(self):
        """
        Тест 1: Проверка обработки клавиши Esc.
        
        Проверяет, что при нажатии Esc вызывается метод go_back() приложения.
        """
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        
        # Создаём виджет и устанавливаем приложение
        widget = NavigableWidget()
        widget.set_app(mock_app)
        
        # Вызываем глобальный обработчик клавиш (эмуляция нажатия Esc)
        # В TUIApp._handle_global_key() обрабатывается Esc
        TUIApp._handle_global_key(mock_app, ptg.keys.ESC)
        
        # Проверяем, что был вызван метод go_back()
        mock_app.go_back.assert_called_once()

    def test_global_key_handler_esc(self):
        """
        Проверка глобального обработчика клавиш для Esc.
        
        Проверяет, что _handle_global_key возвращает None для Esc
        (клавиша обработана и не передаётся дальше).
        """
        mock_app = MagicMock(spec=TUIApp)
        
        # Вызываем обработчик
        result = TUIApp._handle_global_key(mock_app, ptg.keys.ESC)
        
        # Esc должен быть обработан (возвращает None)
        assert result is None
        mock_app.go_back.assert_called_once()

    def test_global_key_handler_other_keys(self):
        """
        Проверка, что другие клавиши передаются дальше.
        
        Проверяет, что клавиши кроме Esc возвращаются из обработчика
        для дальнейшей обработки виджетами.
        """
        mock_app = MagicMock(spec=TUIApp)
        
        # Проверяем различные клавиши
        test_keys = [ptg.keys.TAB, ptg.keys.ENTER, "a", "b", "1"]
        
        for key in test_keys:
            # Сбрасываем мок
            mock_app.reset_mock()
            
            # Вызываем обработчик
            result = TUIApp._handle_global_key(mock_app, key)
            
            # Клавиша должна быть возвращена для дальнейшей обработки
            assert result == key
            # go_back не должен вызываться
            mock_app.go_back.assert_not_called()


class TestTabKeyHandling:
    """
    Тесты обработки клавиши Tab.
    
    Проверяют переключение фокуса на следующий элемент.
    """

    def test_tab_switches_focus_forward(self):
        """
        Тест 2: Проверка переключения фокуса вперёд (Tab).
        
        Проверяет, что при нажатии Tab фокус переключается на следующий виджет.
        """
        # Создаём виджеты заранее
        widget1 = NavigableWidget()
        widget2 = NavigableWidget()
        widget3 = NavigableWidget()
        
        # Создаём контейнер с виджетами (передаём в конструктор)
        container = NavigableContainer(widget1, widget2, widget3)
        mock_app = MagicMock(spec=TUIApp)
        container.set_app(mock_app)
        
        # Устанавливаем фокус на первый виджет
        container.focus_first()
        assert container.focus_index == 0
        assert widget1.focused is True
        
        # Эмулируем нажатие Tab
        container.handle_key(ptg.keys.TAB)
        
        # Фокус должен переключиться на второй виджет
        assert container.focus_index == 1
        assert widget1.focused is False
        assert widget2.focused is True

    def test_tab_cyclic_navigation(self):
        """
        Проверка циклической навигации Tab.
        
        Проверяет, что после последнего элемента Tab переключает на первый.
        """
        # Создаём виджеты
        widgets = [NavigableWidget() for _ in range(3)]
        
        # Создаём контейнер с виджетами
        container = NavigableContainer(*widgets)
        mock_app = MagicMock(spec=TUIApp)
        container.set_app(mock_app)
        
        # Устанавливаем фокус на последний элемент
        container.focus_index = 2
        assert container.focus_index == 2
        
        # Эмулируем нажатие Tab
        container.handle_key(ptg.keys.TAB)
        
        # Фокус должен переключиться на первый элемент (циклически)
        assert container.focus_index == 0

    def test_tab_focus_methods(self):
        """
        Проверка методов focus_next() и focus_prev().
        
        Проверяет корректность методов переключения фокуса.
        """
        # Создаём виджеты
        widgets = [NavigableWidget() for _ in range(5)]
        
        # Создаём контейнер с виджетами
        container = NavigableContainer(*widgets)
        mock_app = MagicMock(spec=TUIApp)
        container.set_app(mock_app)
        
        # Начинаем с первого
        container.focus_first()
        assert container.focus_index == 0
        
        # Переключаем вперёд
        container.focus_next()
        assert container.focus_index == 1
        
        container.focus_next()
        assert container.focus_index == 2
        
        # Переключаем назад
        container.focus_prev()
        assert container.focus_index == 1


class TestShiftTabKeyHandling:
    """
    Тесты обработки клавиши Shift+Tab.
    
    Проверяют переключение фокуса на предыдущий элемент.
    """

    def test_shift_tab_switches_focus_backward(self):
        """
        Тест 3: Проверка переключения фокуса назад (Shift+Tab).
        
        Проверяет, что при нажатии Shift+Tab фокус переключается на предыдущий виджет.
        """
        # Создаём виджеты
        widget1 = NavigableWidget()
        widget2 = NavigableWidget()
        widget3 = NavigableWidget()
        
        # Создаём контейнер с виджетами
        container = NavigableContainer(widget1, widget2, widget3)
        mock_app = MagicMock(spec=TUIApp)
        container.set_app(mock_app)
        
        # Устанавливаем фокус на второй виджет
        container.focus_index = 1
        assert widget2.focused is True
        
        # Эмулируем нажатие Shift+Tab
        container.handle_key(ptg.keys.SHIFT_TAB)
        
        # Фокус должен переключиться на первый виджет
        assert container.focus_index == 0
        assert widget2.focused is False
        assert widget1.focused is True

    def test_shift_tab_cyclic_navigation(self):
        """
        Проверка циклической навигации Shift+Tab.
        
        Проверяет, что при нажатии Shift+Tab на первом элементе
        фокус переключается на последний.
        """
        # Создаём виджеты
        widgets = [NavigableWidget() for _ in range(3)]
        
        # Создаём контейнер с виджетами
        container = NavigableContainer(*widgets)
        mock_app = MagicMock(spec=TUIApp)
        container.set_app(mock_app)
        
        # Устанавливаем фокус на первый элемент
        container.focus_index = 0
        
        # Эмулируем нажатие Shift+Tab
        container.handle_key(ptg.keys.SHIFT_TAB)
        
        # Фокус должен переключиться на последний элемент (циклически)
        assert container.focus_index == 2

    def test_shift_tab_from_middle(self):
        """
        Проверка Shift+Tab с середины списка.
        
        Проверяет корректное переключение назад из средней позиции.
        """
        # Создаём виджеты
        widgets = [NavigableWidget() for _ in range(5)]
        
        # Создаём контейнер с виджетами
        container = NavigableContainer(*widgets)
        mock_app = MagicMock(spec=TUIApp)
        container.set_app(mock_app)
        
        # Устанавливаем фокус на средний элемент (индекс 2)
        container.focus_index = 2
        assert widgets[2].focused is True
        
        # Эмулируем нажатие Shift+Tab
        container.handle_key(ptg.keys.SHIFT_TAB)
        
        # Фокус должен переключиться на индекс 1
        assert container.focus_index == 1
        assert widgets[1].focused is True
        assert widgets[2].focused is False


class TestEnterKeyOnCheckbox:
    """
    Тесты обработки клавиши Enter на Checkbox.
    
    Проверяют переключение состояния checkbox при нажатии Enter.
    """

    def test_enter_toggles_checkbox(self):
        """
        Тест 4: Проверка переключения checkbox клавишей Enter.
        
        Проверяет, что при нажатии Enter checkbox переключает своё состояние.
        """
        # Создаём checkbox с начальным состоянием False
        checkbox = Checkbox(label="Test Checkbox", value=False)
        
        # Проверяем начальное состояние
        assert checkbox.value is False
        
        # Эмулируем нажатие Enter
        result = checkbox.handle_key(ptg.keys.ENTER)
        
        # Клавиша должна быть обработана
        assert result is True
        # Состояние должно переключиться
        assert checkbox.value is True

    def test_enter_toggles_checkbox_back(self):
        """
        Проверка переключения checkbox в обратное состояние.
        
        Проверяет, что повторное нажатие Enter переключает checkbox обратно.
        """
        # Создаём checkbox с начальным состоянием True
        checkbox = Checkbox(label="Test Checkbox", value=True)
        
        assert checkbox.value is True
        
        # Эмулируем нажатие Enter
        checkbox.handle_key(ptg.keys.ENTER)
        
        # Состояние должно переключиться
        assert checkbox.value is False

    def test_checkbox_on_change_callback(self):
        """
        Проверка вызова callback при переключении Enter.
        
        Проверяет, что при переключении checkbox вызывается on_change callback.
        """
        # Создаём мок callback
        mock_callback = MagicMock()
        
        # Создаём checkbox с callback
        checkbox = Checkbox(
            label="Test Checkbox",
            value=False,
            on_change=mock_callback
        )
        
        # Эмулируем нажатие Enter
        checkbox.handle_key(ptg.keys.ENTER)
        
        # Callback должен быть вызван с новым значением
        mock_callback.assert_called_once_with(True)

    def test_checkbox_toggle_method(self):
        """
        Проверка метода toggle().
        
        Проверяет, что метод toggle() переключает состояние checkbox.
        """
        checkbox = Checkbox(label="Test Checkbox", value=False)
        
        # Переключаем несколько раз
        checkbox.toggle()
        assert checkbox.value is True
        
        checkbox.toggle()
        assert checkbox.value is False
        
        checkbox.toggle()
        assert checkbox.value is True

    def test_checkbox_focus_visual(self):
        """
        Проверка визуального отображения фокуса.
        
        Проверяет, что get_lines() возвращает разные строки
        для сфокусированного и несфокусированного состояния.
        """
        checkbox = Checkbox(label="Test Checkbox", value=True)
        
        # Без фокуса
        checkbox.focused = False
        lines_unfocused = checkbox.get_lines()
        
        # С фокусом
        checkbox.focused = True
        lines_focused = checkbox.get_lines()
        
        # Строки должны отличаться (разные стили)
        assert lines_unfocused != lines_focused
        # Сфокусированный должен содержать маркер фокуса
        assert ">" in lines_focused[0]


class TestFullNavigationCycle:
    """
    Тесты полного цикла навигации по экранам.
    
    Проверяют навигацию между всеми экранами приложения.
    """

    def test_navigation_stack_push_pop(self):
        """
        Тест 5: Проверка стека навигации.
        
        Проверяет корректность работы ScreenManager push/pop.
        """
        mock_app = MagicMock()
        screen_manager = ScreenManager(mock_app)
        
        # Создаём моки экранов
        screen1 = MagicMock()
        screen2 = MagicMock()
        screen3 = MagicMock()
        
        # Изначально стек пуст
        assert screen_manager.stack_size == 0
        assert screen_manager.get_current() is None
        
        # Push первого экрана
        screen_manager.push("main_menu", screen1)
        assert screen_manager.stack_size == 0  # Первый экран не добавляется в стек
        assert screen_manager.get_current() == "main_menu"
        
        # Push второго экрана
        screen_manager.push("city_selector", screen2)
        assert screen_manager.stack_size == 1
        assert screen_manager.get_current() == "city_selector"
        
        # Push третьего экрана
        screen_manager.push("category_selector", screen3)
        assert screen_manager.stack_size == 2
        assert screen_manager.get_current() == "category_selector"
        
        # Pop - возврат к предыдущему
        previous = screen_manager.pop()
        assert previous == "city_selector"
        assert screen_manager.get_current() == "city_selector"
        assert screen_manager.stack_size == 1
        
        # Pop - возврат к главному меню
        previous = screen_manager.pop()
        assert previous == "main_menu"  # Возвращаем main_menu
        assert screen_manager.get_current() == "main_menu"
        assert screen_manager.stack_size == 0
        
        # Ещё один pop должен вернуть None (стек пуст)
        previous = screen_manager.pop()
        assert previous is None

    def test_screen_manager_clear(self):
        """
        Проверка очистки стека экранов.
        
        Проверяет, что clear() полностью очищает стек.
        """
        mock_app = MagicMock()
        screen_manager = ScreenManager(mock_app)
        
        # Добавляем экраны
        screen_manager.push("main_menu", MagicMock())
        screen_manager.push("city_selector", MagicMock())
        screen_manager.push("category_selector", MagicMock())
        
        assert screen_manager.stack_size == 2
        
        # Очищаем стек
        screen_manager.clear()
        
        assert screen_manager.stack_size == 0
        assert screen_manager.get_current() is None
        assert screen_manager.current_instance is None

    def test_screen_manager_current_instance(self):
        """
        Проверка получения текущего экземпляра экрана.
        
        Проверяет, что current_instance возвращает правильный экземпляр.
        """
        mock_app = MagicMock()
        screen_manager = ScreenManager(mock_app)
        
        # Создаём экран
        main_menu_screen = MagicMock()
        
        # Push экрана
        screen_manager.push("main_menu", main_menu_screen)
        
        # Проверяем current_instance
        assert screen_manager.current_instance == main_menu_screen

    def test_navigation_button_widget(self):
        """
        Проверка активации кнопки через Enter.

        Проверяет, что ButtonWidget корректно обрабатывает Enter
        и вызывает callback.
        """
        mock_callback = MagicMock()

        # Создаём кнопку (используем onclick вместо callback)
        button = ButtonWidget(label="Test Button", onclick=mock_callback)

        # Эмулируем нажатие Enter
        result = button.handle_key(ptg.keys.ENTER)

        # Клавиша должна быть обработана
        assert result is True
        # Callback должен быть вызван
        mock_callback.assert_called_once()

    def test_button_widget_on_enter(self):
        """
        Проверка метода on_enter() у ButtonWidget.

        Проверяет, что on_enter() вызывает activate().
        """
        mock_callback = MagicMock()
        # Используем onclick вместо callback
        button = ButtonWidget(label="Test Button", onclick=mock_callback)

        # Вызываем on_enter
        result = button.on_enter()

        # Должен вернуть True
        assert result is True
        # Callback должен быть вызван
        mock_callback.assert_called_once()

    def test_navigable_widget_on_enter(self):
        """
        Проверка метода on_enter() у базового NavigableWidget.
        
        Проверяет, что базовый класс возвращает False по умолчанию.
        """
        widget = NavigableWidget()
        
        # Вызываем on_enter
        result = widget.on_enter()
        
        # Базовый класс возвращает False
        assert result is False


# Запуск тестов через pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
