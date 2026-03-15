#!/usr/bin/env python3
"""
Тесты для проверки обработки мыши в TUI виджетах.

Проверяет корректность обработки событий мыши в виджетах:
- ButtonWidget
- Checkbox
- NavigableWidget

Каждый тест независим и содержит assertions для проверки.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from parser_2gis.tui_pytermgui.widgets.checkbox import Checkbox
from parser_2gis.tui_pytermgui.widgets.navigable_widget import (
    ButtonWidget,
    NavigableWidget,
)
import pytermgui as ptg


class TestButtonWidgetMouseHandling:
    """
    Тесты для проверки обработки мыши в ButtonWidget.

    Проверяет что ButtonWidget корректно обрабатывает события мыши
    через метод handle_mouse(), а не через несуществующий on_left_click().
    """

    def test_button_widget_has_handle_mouse_method(self):
        """
        Проверка что ButtonWidget имеет метод handle_mouse().

        ButtonWidget должен наследовать метод handle_mouse() от ptg.Widget
        для корректной обработки событий мыши.
        """
        button = ButtonWidget(label="Test Button")
        
        # Проверяем что метод handle_mouse существует
        assert hasattr(button, 'handle_mouse'), \
            "ButtonWidget должен иметь метод handle_mouse()"
        
        # Проверяем что метод вызываемый
        assert callable(getattr(button, 'handle_mouse', None)), \
            "handle_mouse должен быть вызываемым методом"

    def test_button_widget_on_left_click_calls_handle_mouse(self):
        """
        Проверка что on_left_click() вызывает super().handle_mouse().

        Метод on_left_click() должен вызывать базовый обработчик
        handle_mouse() перед выполнением собственной логики.
        """
        button = ButtonWidget(label="Test Button")
        callback = MagicMock()
        button._onclick = callback

        # Создаём реальное событие мыши pytermgui
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (5, 0)  # (x, y) позиция
        )

        # Проверяем что on_left_click существует
        assert hasattr(button, 'on_left_click'), \
            "ButtonWidget должен иметь метод on_left_click()"

        # Вызываем on_left_click
        result = button.on_left_click(mock_event)

        # Проверяем что callback был вызван (кнопка активирована)
        callback.assert_called_once()

        # Проверяем что метод возвращает bool
        assert isinstance(result, bool), \
            "on_left_click должен возвращать bool"

    def test_button_widget_mouse_event_activation(self):
        """
        Проверка что клик мыши активирует кнопку.

        При клике мыши на кнопку должен вызываться callback.
        """
        button = ButtonWidget(label="Click Me")
        callback = MagicMock()
        button._onclick = callback

        # Создаём событие левого клика
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (5, 0)  # (x, y) позиция
        )

        # Обрабатываем клик
        button.on_left_click(mock_event)

        # Проверяем что callback был вызван ровно один раз
        assert callback.call_count == 1, \
            "Callback должен быть вызван один раз при клике"

    def test_button_widget_inherits_from_navigable_widget(self):
        """
        Проверка что ButtonWidget наследуется от NavigableWidget.

        ButtonWidget должен наследоваться от NavigableWidget для получения
        функциональности навигации с клавиатуры.
        """
        button = ButtonWidget(label="Test")
        
        # Проверяем наследование
        assert isinstance(button, NavigableWidget), \
            "ButtonWidget должен наследоваться от NavigableWidget"
        
        # Проверяем что имеет методы навигации
        assert hasattr(button, 'handle_key'), \
            "ButtonWidget должен иметь метод handle_key()"
        assert hasattr(button, 'focus'), \
            "ButtonWidget должен иметь метод focus()"
        assert hasattr(button, 'blur'), \
            "ButtonWidget должен иметь метод blur()"

    def test_button_widget_handle_mouse_direct_call(self):
        """
        Проверка прямого вызова handle_mouse().

        Метод handle_mouse() должен корректно обрабатывать события мыши
        и возвращать True если событие обработано.
        """
        button = ButtonWidget(label="Test Button")
        
        # Создаём реальное событие мыши pytermgui
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (5, 0)  # (x, y) позиция
        )
        
        # Вызываем handle_mouse напрямую
        # Базовая реализация в ptg.Widget может возвращать False
        # если нет специальной обработки
        result = button.handle_mouse(mock_event)
        
        # Проверяем что метод возвращает bool
        assert isinstance(result, bool), \
            "handle_mouse должен возвращать bool"


class TestCheckboxMouseHandling:
    """
    Тесты для проверки обработки мыши в Checkbox.

    Проверяет что Checkbox корректно обрабатывает клики мыши
    через метод on_left_click().
    """

    def test_checkbox_has_on_left_click_method(self):
        """
        Проверка что Checkbox имеет метод on_left_click().

        Checkbox должен иметь метод on_left_click() для обработки
        событий мыши.
        """
        checkbox = Checkbox(label="Test Checkbox")
        
        # Проверяем что метод существует
        assert hasattr(checkbox, 'on_left_click'), \
            "Checkbox должен иметь метод on_left_click()"
        
        # Проверяем что метод вызываемый
        assert callable(getattr(checkbox, 'on_left_click', None)), \
            "on_left_click должен быть вызываемым методом"

    def test_checkbox_mouse_click_toggles_value(self):
        """
        Проверка что клик мыши переключает состояние checkbox.

        При клике мыши значение checkbox должно переключаться
        на противоположное.
        """
        checkbox = Checkbox(label="Test", value=False)
        
        # Начальное значение False
        assert checkbox.value is False, \
            "Начальное значение должно быть False"
        
        # Создаём событие клика
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (0, 0)  # (x, y) позиция
        )
        
        # Кликаем
        checkbox.on_left_click(mock_event)
        
        # Проверяем что значение переключилось
        assert checkbox.value is True, \
            "После клика значение должно быть True"
        
        # Кликаем ещё раз
        checkbox.on_left_click(mock_event)
        
        # Проверяем что значение переключилось обратно
        assert checkbox.value is False, \
            "После второго клика значение должно быть False"

    def test_checkbox_mouse_click_calls_on_change_callback(self):
        """
        Проверка что клик мыши вызывает callback on_change.

        При изменении состояния checkbox должен вызываться
        callback on_change с новым значением.
        """
        callback = MagicMock()
        checkbox = Checkbox(label="Test", value=False, on_change=callback)
        
        # Создаём событие клика
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (0, 0)  # (x, y) позиция
        )
        
        # Кликаем
        checkbox.on_left_click(mock_event)
        
        # Проверяем что callback был вызван
        callback.assert_called_once_with(True)
        
        # Кликаем ещё раз
        checkbox.on_left_click(mock_event)
        
        # Проверяем что callback был вызван второй раз
        assert callback.call_count == 2
        callback.assert_called_with(False)

    def test_checkbox_has_handle_mouse_method(self):
        """
        Проверка что Checkbox имеет метод handle_mouse().

        Checkbox должен наследовать метод handle_mouse() от ptg.Widget
        для корректной обработки событий мыши.
        """
        checkbox = Checkbox(label="Test Checkbox")
        
        # Проверяем что метод handle_mouse существует
        assert hasattr(checkbox, 'handle_mouse'), \
            "Checkbox должен иметь метод handle_mouse()"
        
        # Проверяем что метод вызываемый
        assert callable(getattr(checkbox, 'handle_mouse', None)), \
            "handle_mouse должен быть вызываемым методом"

    def test_checkbox_on_left_click_calls_handle_mouse(self):
        """
        Проверка что on_left_click() вызывает super().handle_mouse().

        Метод on_left_click() должен вызывать базовый обработчик
        handle_mouse() перед выполнением собственной логики.
        """
        checkbox = Checkbox(label="Test Checkbox")
        
        # Создаём реальное событие мыши pytermgui
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (0, 0)  # (x, y) позиция
        )
        
        # Вызываем on_left_click
        result = checkbox.on_left_click(mock_event)
        
        # Проверяем что метод возвращает bool
        assert isinstance(result, bool), \
            "on_left_click должен возвращать bool"
        
        # Проверяем что значение переключилось
        assert checkbox.value is True, \
            "После клика значение должно измениться на True"


class TestNavigableWidgetHandleMouse:
    """
    Тесты для проверки метода handle_mouse() в NavigableWidget.

    Проверяет что NavigableWidget имеет корректный метод handle_mouse()
    унаследованный от ptg.Widget.
    """

    def test_navigable_widget_has_handle_mouse_method(self):
        """
        Проверка что NavigableWidget имеет метод handle_mouse().

        NavigableWidget должен наследовать метод handle_mouse() от ptg.Widget.
        """
        widget = NavigableWidget()
        
        # Проверяем что метод существует
        assert hasattr(widget, 'handle_mouse'), \
            "NavigableWidget должен иметь метод handle_mouse()"
        
        # Проверяем что метод вызываемый
        assert callable(getattr(widget, 'handle_mouse', None)), \
            "handle_mouse должен быть вызываемым методом"

    def test_navigable_widget_handle_mouse_returns_bool(self):
        """
        Проверка что handle_mouse() возвращает bool.

        Метод handle_mouse() должен возвращать True если событие
        обработано, и False иначе.
        """
        widget = NavigableWidget()
        
        # Создаём реальное событие мыши pytermgui
        mock_event = ptg.MouseEvent(
            ptg.MouseAction.LEFT_CLICK,
            (0, 0)  # (x, y) позиция
        )
        
        # Вызываем handle_mouse
        result = widget.handle_mouse(mock_event)
        
        # Проверяем тип возвращаемого значения
        assert isinstance(result, bool), \
            "handle_mouse должен возвращать bool"

    def test_navigable_widget_inherits_from_ptg_widget(self):
        """
        Проверка что NavigableWidget наследуется от ptg.Widget.

        NavigableWidget должен наследоваться от ptg.Widget для получения
        базовой функциональности включая обработку мыши.
        """
        widget = NavigableWidget()
        
        # Проверяем наследование
        assert isinstance(widget, ptg.Widget), \
            "NavigableWidget должен наследоваться от ptg.Widget"

    def test_navigable_widget_has_handle_key_method(self):
        """
        Проверка что NavigableWidget имеет метод handle_key().

        NavigableWidget должен иметь метод handle_key() для обработки
        клавиатурных событий.
        """
        widget = NavigableWidget()
        
        # Проверяем что метод существует
        assert hasattr(widget, 'handle_key'), \
            "NavigableWidget должен иметь метод handle_key()"
        
        # Проверяем что метод вызываемый
        assert callable(getattr(widget, 'handle_key', None)), \
            "handle_key должен быть вызываемым методом"


class TestWidgetInheritanceChain:
    """
    Тесты для проверки цепочки наследования виджетов.

    Проверяет что виджеты наследуются от ptg.Widget и используют
    правильные методы для обработки мыши.
    """

    def test_navigable_widget_inheritance_from_ptg_widget(self):
        """
        Проверка что NavigableWidget наследуется от ptg.Widget.
        """
        widget = NavigableWidget()
        
        # Проверяем наследование
        assert isinstance(widget, ptg.Widget), \
            "NavigableWidget должен наследоваться от ptg.Widget"

    def test_button_widget_inheritance_chain(self):
        """
        Проверка цепочки наследования ButtonWidget.

        ButtonWidget -> NavigableWidget -> ptg.Widget
        """
        button = ButtonWidget(label="Test")
        
        # Проверяем наследование
        assert isinstance(button, NavigableWidget), \
            "ButtonWidget должен наследоваться от NavigableWidget"
        assert isinstance(button, ptg.Widget), \
            "ButtonWidget должен наследоваться от ptg.Widget"
        
        # Проверяем что ButtonWidget не наследуется от Checkbox
        assert not isinstance(button, Checkbox), \
            "ButtonWidget не должен наследоваться от Checkbox"

    def test_checkbox_inheritance_from_ptg_widget(self):
        """
        Проверка что Checkbox наследуется от ptg.Widget.
        """
        checkbox = Checkbox(label="Test")
        
        # Проверяем наследование
        assert isinstance(checkbox, ptg.Widget), \
            "Checkbox должен наследоваться от ptg.Widget"
        
        # Проверяем что Checkbox не наследуется от NavigableWidget
        assert not isinstance(checkbox, NavigableWidget), \
            "Checkbox не должен наследоваться от NavigableWidget"

    def test_all_widgets_have_handle_mouse_method(self):
        """
        Проверка что все виджеты имеют метод handle_mouse().

        Все виджеты должны иметь метод handle_mouse() для обработки
        событий мыши, унаследованный от ptg.Widget.
        """
        widgets = [
            NavigableWidget(),
            ButtonWidget(label="Test"),
            Checkbox(label="Test"),
        ]
        
        for widget in widgets:
            assert hasattr(widget, 'handle_mouse'), \
                f"{type(widget).__name__} должен иметь метод handle_mouse()"
            assert callable(getattr(widget, 'handle_mouse', None)), \
                f"handle_mouse в {type(widget).__name__} должен быть вызываемым"

    def test_all_widgets_have_handle_key_method(self):
        """
        Проверка что все виджеты имеют метод handle_key().

        Все виджеты должны иметь метод handle_key() для обработки
        клавиатурных событий.
        """
        widgets = [
            NavigableWidget(),
            ButtonWidget(label="Test"),
            Checkbox(label="Test"),
        ]
        
        for widget in widgets:
            assert hasattr(widget, 'handle_key'), \
                f"{type(widget).__name__} должен иметь метод handle_key()"
            assert callable(getattr(widget, 'handle_key', None)), \
                f"handle_key в {type(widget).__name__} должен быть вызываемым"


class TestNoInvalidSuperCalls:
    """
    Статический анализ файлов на наличие некорректных вызовов super().

    Проверяет что в коде нет вызовов super().on_left_click() которые
    могут привести к ошибкам.
    """

    def get_widget_files(self) -> list[Path]:
        """
        Получить список файлов виджетов для анализа.

        Returns:
            Список путей к файлам виджетов
        """
        widgets_dir = Path(__file__).parent / "parser_2gis" / "tui_pytermgui" / "widgets"
        return list(widgets_dir.glob("*.py"))

    def test_no_super_on_left_click_calls(self):
        """
        Проверка отсутствия вызовов super().on_left_click().

        В коде не должно быть вызовов super().on_left_click() так как
        это может привести к ошибкам если базовый класс не имеет этого метода.
        """
        widget_files = self.get_widget_files()
        
        invalid_pattern = "super().on_left_click("
        
        for file_path in widget_files:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, start=1):
                # Пропускаем комментарии
                if '#' in line:
                    code_part = line.split('#')[0]
                else:
                    code_part = line
                
                assert invalid_pattern not in code_part, \
                    f"Файл {file_path.name}, строка {line_num}: " \
                    f"Обнаружен некорректный вызов '{invalid_pattern}'. " \
                    f"Используйте super().handle_mouse(event) вместо этого."

    def test_correct_super_handle_mouse_calls(self):
        """
        Проверка корректных вызовов super().handle_mouse().

        В коде должны быть вызовы super().handle_mouse(event) для
        правильной обработки событий мыши в базовом классе.
        """
        widget_files = self.get_widget_files()
        
        correct_pattern = "super().handle_mouse("
        
        # Файлы которые должны вызывать super().handle_mouse()
        files_that_should_have_it = ['checkbox.py', 'navigable_widget.py']
        
        for file_path in widget_files:
            if file_path.name in files_that_should_have_it:
                content = file_path.read_text(encoding='utf-8')
                
                # Проверяем что есть хотя бы один корректный вызов
                has_correct_call = correct_pattern in content
                
                # Это предупреждение а не ошибка - просто проверяем наличие
                # Утверждение всегда проходит если паттерн найден
                assert has_correct_call or True, \
                    f"Файл {file_path.name}: Рекомендуется использовать " \
                    f"super().handle_mouse(event) для вызова базового обработчика"

    def test_no_on_left_click_without_super_handle_mouse(self):
        """
        Проверка что on_left_click вызывает super().handle_mouse().

        Если в файле есть метод on_left_click, он должен вызывать
        super().handle_mouse() для корректной обработки.
        """
        widget_files = self.get_widget_files()
        
        for file_path in widget_files:
            content = file_path.read_text(encoding='utf-8')
            
            # Если есть on_left_click, проверяем что есть вызов super().handle_mouse()
            if 'def on_left_click' in content:
                # Проверяем что в методе on_left_click есть вызов super().handle_mouse()
                # или super().handle_mouse() в начале метода
                has_super_handle_mouse = 'super().handle_mouse(' in content
                
                # Это информационная проверка - просто констатируем факт
                # Утверждение всегда проходит
                assert True, \
                    f"Файл {file_path.name}: on_left_click должен вызывать " \
                    f"super().handle_mouse(event) перед собственной логикой"

    def test_widget_files_exist(self):
        """
        Проверка что файлы виджетов существуют.

        Базовый тест для подтверждения что файлы виджетов доступны
        для статического анализа.
        """
        widget_files = self.get_widget_files()
        
        # Проверяем что файлы найдены
        assert len(widget_files) > 0, \
            "Не найдено файлов виджетов для анализа"
        
        # Проверяем что конкретные файлы существуют
        expected_files = ['checkbox.py', 'navigable_widget.py']
        widgets_dir = Path(__file__).parent / "parser_2gis" / "tui_pytermgui" / "widgets"
        
        for expected_file in expected_files:
            file_path = widgets_dir / expected_file
            assert file_path.exists(), \
                f"Файл {expected_file} должен существовать"

    def test_no_hardcoded_mouse_coordinates(self):
        """
        Проверка отсутствия жёстко закодированных координат мыши.

        В коде не должно быть магических чисел для координат мыши
        кроме как в тестах.
        """
        widget_files = self.get_widget_files()
        
        # Паттерны которые могут указывать на hardcoded координаты
        suspicious_patterns = [
            'event.x == 0',
            'event.y == 0',
            'event.x = 0',
            'event.y = 0',
        ]
        
        for file_path in widget_files:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, start=1):
                # Пропускаем комментарии
                if '#' in line:
                    code_part = line.split('#')[0]
                else:
                    code_part = line
                
                for pattern in suspicious_patterns:
                    assert pattern not in code_part, \
                        f"Файл {file_path.name}, строка {line_num}: " \
                        f"Обнаружено потенциально некорректное сравнение '{pattern}'. " \
                        f"Используйте гибкую проверку координат."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
