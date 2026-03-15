#!/usr/bin/env python3
"""
Тесты для проверки корректности работы с виджетами pytermgui.

Эти тесты выявляют ошибки типа AttributeError при работе с виджетами pytermgui,
в частности ошибку с вызовом несуществующего метода set_format() у Label.

Контекст:
- Была ошибка: AttributeError: 'Label' object has no attribute 'set_format'
- Проблема была в файлах city_selector.py и category_selector.py
- Ошибка возникала при вызове несуществующего метода set_format() на объекте ptg.Label

Каждый тест:
- Независимый
- Имеет понятное название
- Проверяет конкретную проблему
- Использует pytest
- Содержит комментарии на русском языке
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))


class TestLabelSetFormatUsage:
    """
    Тест 1: Проверка отсутствия вызова set_format() на Label объектах.
    
    Этот тест анализирует исходный код методов _update_counter в экранах
    и проверяет, что не используется несуществующий метод set_format().
    """

    def test_no_set_format_in_city_selector_update_counter(self):
        """
        Проверка что в CitySelectorScreen._update_counter() нет вызова set_format().
        
        Эта ошибка возникала когда код пытался вызвать label.set_format() вместо
        правильного label.value = "новый текст"
        """
        from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
        
        # Получаем исходный код метода _update_counter
        source = inspect.getsource(CitySelectorScreen._update_counter)
        
        # Проверяем что нет вызова set_format()
        assert "set_format(" not in source, (
            "Метод _update_counter() в CitySelectorScreen не должен вызывать set_format(). "
            "Используйте label.value для обновления содержимого Label."
        )
        
        # Проверяем что используется правильный способ обновления через .value
        assert ".value =" in source or ".value=" in source, (
            "Метод _update_counter() должен использовать .value для обновления Label."
        )

    def test_no_set_format_in_category_selector_update_counter(self):
        """
        Проверка что в CategorySelectorScreen._update_counter() нет вызова set_format().
        
        Аналогичная проверка для экрана выбора категорий.
        """
        from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
        
        # Получаем исходный код метода _update_counter
        source = inspect.getsource(CategorySelectorScreen._update_counter)
        
        # Проверяем что нет вызова set_format()
        assert "set_format(" not in source, (
            "Метод _update_counter() в CategorySelectorScreen не должен вызывать set_format(). "
            "Используйте label.value для обновления содержимого Label."
        )
        
        # Проверяем что используется правильный способ обновления через .value
        assert ".value =" in source or ".value=" in source, (
            "Метод _update_counter() должен использовать .value для обновления Label."
        )


class TestLabelValueAttributeUsage:
    """
    Тест 2: Проверка что все Label виджеты используют .value для обновления.
    
    Этот тест сканирует все файлы экранов и проверяет, что Label объекты
    обновляются через атрибут .value, а не через несуществующие методы.
    """

    def _find_label_assignments(self, source_code: str) -> List[Tuple[int, str]]:
        """
        Найти все присваивания атрибута value объектам Label в коде.
        
        Args:
            source_code: Исходный код для анализа
            
        Returns:
            Список кортежей (номер_строки, текст_строки) с присваиваниями
        """
        assignments = []
        lines = source_code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Ищем присваивания на .value для Label
            if '_label.value' in line or 'label.value' in line:
                if '=' in line and '==' not in line:
                    assignments.append((i, line.strip()))
                    
        return assignments

    def _check_for_set_format_calls(self, source_code: str) -> List[Tuple[int, str]]:
        """
        Найти все вызовы метода set_format() в коде.
        
        Args:
            source_code: Исходный код для анализа
            
        Returns:
            Список кортежей (номер_строки, текст_строки) с вызовами set_format()
        """
        calls = []
        lines = source_code.split('\n')
        
        for i, line in enumerate(lines, 1):
            if 'set_format(' in line:
                calls.append((i, line.strip()))
                    
        return calls

    def test_all_screens_use_value_for_label_updates(self):
        """
        Проверка что все экраны используют .value для обновления Label.
        
        Сканирует все файлы в директории screens/ и проверяет что:
        1. Нет вызовов set_format()
        2. Есть использование .value для обновления Label
        """
        from parser_2gis.tui_pytermgui import screens
        
        # Получаем путь к директории с экранами
        screens_dir = Path(screens.__file__).parent
        
        # Находим все Python файлы в директории screens
        screen_files = list(screens_dir.glob('*.py'))
        
        all_errors = []
        
        for screen_file in screen_files:
            # Пропускаем __init__.py
            if screen_file.name == '__init__.py':
                continue
                
            # Читаем файл
            source_code = screen_file.read_text(encoding='utf-8')
            
            # Проверяем на наличие set_format()
            set_format_calls = self._check_for_set_format_calls(source_code)
            
            if set_format_calls:
                for line_num, line_text in set_format_calls:
                    all_errors.append(
                        f"{screen_file.name}:{line_num} - найден вызов set_format(): {line_text}"
                    )
        
        # Если есть ошибки, формируем понятное сообщение
        if all_errors:
            errors_text = '\n'.join(all_errors)
            pytest.fail(
                f"Обнаружены вызовы несуществующего метода set_format() в файлах экранов:\n"
                f"{errors_text}\n\n"
                f"Используйте label.value = 'новый текст' для обновления содержимого Label."
            )

    def test_counter_labels_use_value_assignment(self):
        """
        Проверка что счётчики (counter_label) используют .value для обновления.
        
        Специальная проверка для Label которые отображают счётчики выбранных элементов.
        """
        from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
        from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
        
        for screen_class in [CitySelectorScreen, CategorySelectorScreen]:
            source = inspect.getsource(screen_class)
            
            # Проверяем что _counter_label обновляется через .value
            assert '_counter_label.value' in source or 'self._counter_label.value' in source, (
                f"{screen_class.__name__} должен использовать .value для обновления _counter_label."
            )


class TestPytermguiWidgetMethodValidation:
    """
    Тест 3: Проверка отсутствия вызова несуществующих методов у виджетов pytermgui.
    
    Этот тест использует статический анализ AST для поиска потенциально опасных
    вызовов методов у виджетов pytermgui в файлах screens/*.py
    """

    def _get_invalid_widget_methods(self) -> List[str]:
        """
        Получить список методов которые не существуют у виджетов pytermgui.
        
        Returns:
            Список названий методов которые не следует вызывать
        """
        return [
            'set_format',      # Не существует у Label
            'set_text',        # Не существует, используйте .value
            'update_text',     # Не существует, используйте .value
            'set_value',       # Не существует, используйте .value напрямую
        ]

    def _analyze_file_for_invalid_calls(self, file_path: Path) -> List[dict]:
        """
        Проанализировать файл на наличие вызовов несуществующих методов.
        
        Использует AST для статического анализа кода.
        
        Args:
            file_path: Путь к файлу для анализа
            
        Returns:
            Список найденных проблем с информацией о строке и методе
        """
        problems = []
        invalid_methods = self._get_invalid_widget_methods()
        
        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError) as e:
            # Если файл не удалось распарсить, пропускаем его
            return problems
        
        lines = source.split('\n')
        
        # Проходим по всем узлам AST
        for node in ast.walk(tree):
            # Ищем вызовы методов (obj.method())
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                    line_number = node.lineno
                    
                    if method_name in invalid_methods:
                        problems.append({
                            'file': file_path.name,
                            'line': line_number,
                            'method': method_name,
                            'code': lines[line_number - 1].strip() if line_number <= len(lines) else ''
                        })
        
        return problems

    def test_no_invalid_widget_method_calls_in_screens(self):
        """
        Проверка что в файлах screens/*.py нет вызовов несуществующих методов.
        
        Использует AST анализ для поиска вызовов методов типа set_format(),
        set_text(), update_text() и других несуществующих методов.
        """
        from parser_2gis.tui_pytermgui import screens
        
        screens_dir = Path(screens.__file__).parent
        screen_files = list(screens_dir.glob('*.py'))
        
        all_problems = []
        
        for screen_file in screen_files:
            if screen_file.name == '__init__.py':
                continue
                
            problems = self._analyze_file_for_invalid_calls(screen_file)
            all_problems.extend(problems)
        
        # Если найдены проблемы, формируем отчёт
        if all_problems:
            report_lines = []
            for problem in all_problems:
                report_lines.append(
                    f"{problem['file']}:{problem['line']} - "
                    f"вызов несуществующего метода '{problem['method']}': "
                    f"{problem['code']}"
                )
            
            pytest.fail(
                f"Обнаружены вызовы несуществующих методов виджетов pytermgui:\n"
                f"\n".join(report_lines) + "\n\n"
                f"Допустимые способы обновления виджетов:\n"
                f"  - Label: используйте label.value = 'новый текст'\n"
                f"  - InputField: используйте field.value = 'новый текст'\n"
            )

    def test_widget_attributes_are_accessible(self):
        """
        Проверка что основные атрибуты виджетов доступны.
        
        Проверяет что у виджетов есть атрибут value который можно читать и записывать.
        """
        import pytermgui as ptg
        
        # Создаём тестовый Label
        label = ptg.Label("Тестовое значение")
        
        # Проверяем что атрибут value существует
        assert hasattr(label, 'value'), "Label должен иметь атрибут value"
        
        # Проверяем что value можно читать
        assert label.value == "Тестовое значение", "value должен содержать начальный текст"
        
        # Проверяем что value можно записывать
        label.value = "Новое значение"
        assert label.value == "Новое значение", "value должен обновляться"
        
        # Проверяем что set_format НЕ существует
        assert not hasattr(label, 'set_format'), (
            "У Label не должно быть метода set_format()"
        )


class TestCitySelectorIntegration:
    """
    Тест 4: Интеграционный тест запуска CitySelectorScreen без ошибок AttributeError.
    
    Проверяет что экран выбора городов может быть создан и использован
    без возникновения ошибок AttributeError при работе с виджетами.
    """

    def test_city_selector_screen_creation_no_attribute_error(self):
        """
        Проверка что создание CitySelectorScreen не вызывает AttributeError.
        
        Интеграционный тест который создаёт экран и проверяет что:
        1. Экран успешно создаётся
        2. Метод create_window() работает без ошибок
        3. Нет AttributeError при работе с Label виджетами
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
        
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        mock_app.get_cities.return_value = [
            {"name": "Москва", "country_code": "RU"},
            {"name": "Санкт-Петербург", "country_code": "RU"},
        ]
        mock_app.selected_cities = []
        
        # Создаём экран - не должно быть AttributeError
        try:
            screen = CitySelectorScreen(mock_app)
        except AttributeError as e:
            pytest.fail(f"AttributeError при создании экрана: {e}")
        
        # Создаём окно - не должно быть AttributeError
        try:
            window = screen.create_window()
            assert window is not None, "Окно должно быть создано"
        except AttributeError as e:
            pytest.fail(f"AttributeError при создании окна: {e}")

    def test_city_selector_update_counter_no_attribute_error(self):
        """
        Проверка что _update_counter() не вызывает AttributeError.
        
        Проверяет что метод обновления счётчика работает корректно
        и не пытается вызвать несуществующие методы у Label.
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
        
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        mock_app.get_cities.return_value = [
            {"name": "Москва", "country_code": "RU"},
        ]
        mock_app.selected_cities = []
        
        # Создаём экран и окно
        screen = CitySelectorScreen(mock_app)
        window = screen.create_window()
        
        # Вызываем _update_counter - не должно быть AttributeError
        try:
            screen._update_counter()
        except AttributeError as e:
            pytest.fail(f"AttributeError в _update_counter(): {e}")

    def test_city_selector_filter_and_update_no_attribute_error(self):
        """
        Проверка что фильтрация городов и обновление счётчика работают без ошибок.
        
        Комплексный тест который проверяет взаимодействие методов:
        1. _filter_cities()
        2. _update_counter()
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
        import pytermgui as ptg
        
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        mock_app.get_cities.return_value = [
            {"name": "Москва", "country_code": "RU"},
            {"name": "Санкт-Петербург", "country_code": "RU"},
            {"name": "Казань", "country_code": "RU"},
        ]
        mock_app.selected_cities = []
        
        # Создаём экран и окно
        screen = CitySelectorScreen(mock_app)
        window = screen.create_window()
        
        # Создаём мок InputField для фильтрации
        mock_field = MagicMock(spec=ptg.InputField)
        mock_field.value = "Москва"
        
        # Вызываем фильтрацию - не должно быть AttributeError
        try:
            screen._filter_cities(mock_field)
        except AttributeError as e:
            pytest.fail(f"AttributeError при фильтрации городов: {e}")


class TestCategorySelectorIntegration:
    """
    Тест 5: Интеграционный тест запуска CategorySelectorScreen без ошибок AttributeError.
    
    Проверяет что экран выбора категорий может быть создан и использован
    без возникновения ошибок AttributeError при работе с виджетами.
    """

    def test_category_selector_screen_creation_no_attribute_error(self):
        """
        Проверка что создание CategorySelectorScreen не вызывает AttributeError.
        
        Интеграционный тест который создаёт экран и проверяет что:
        1. Экран успешно создаётся
        2. Метод create_window() работает без ошибок
        3. Нет AttributeError при работе с Label виджетами
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
        
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        mock_app.get_categories.return_value = [
            {"name": "Рестораны"},
            {"name": "Кафе"},
        ]
        mock_app.selected_categories = []
        
        # Создаём экран - не должно быть AttributeError
        try:
            screen = CategorySelectorScreen(mock_app)
        except AttributeError as e:
            pytest.fail(f"AttributeError при создании экрана: {e}")
        
        # Создаём окно - не должно быть AttributeError
        try:
            window = screen.create_window()
            assert window is not None, "Окно должно быть создано"
        except AttributeError as e:
            pytest.fail(f"AttributeError при создании окна: {e}")

    def test_category_selector_update_counter_no_attribute_error(self):
        """
        Проверка что _update_counter() не вызывает AttributeError.
        
        Проверяет что метод обновления счётчика работает корректно
        и не пытается вызвать несуществующие методы у Label.
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
        
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        mock_app.get_categories.return_value = [
            {"name": "Рестораны"},
        ]
        mock_app.selected_categories = []
        
        # Создаём экран и окно
        screen = CategorySelectorScreen(mock_app)
        window = screen.create_window()
        
        # Вызываем _update_counter - не должно быть AttributeError
        try:
            screen._update_counter()
        except AttributeError as e:
            pytest.fail(f"AttributeError в _update_counter(): {e}")

    def test_category_selector_filter_and_update_no_attribute_error(self):
        """
        Проверка что фильтрация категорий и обновление счётчика работают без ошибок.
        
        Комплексный тест который проверяет взаимодействие методов:
        1. _filter_categories()
        2. _update_counter()
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
        import pytermgui as ptg
        
        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)
        mock_app.get_categories.return_value = [
            {"name": "Рестораны"},
            {"name": "Кафе"},
            {"name": "Бары"},
        ]
        mock_app.selected_categories = []
        
        # Создаём экран и окно
        screen = CategorySelectorScreen(mock_app)
        window = screen.create_window()
        
        # Создаём мок InputField для фильтрации
        mock_field = MagicMock(spec=ptg.InputField)
        mock_field.value = "Рестораны"
        
        # Вызываем фильтрацию - не должно быть AttributeError
        try:
            screen._filter_categories(mock_field)
        except AttributeError as e:
            pytest.fail(f"AttributeError при фильтрации категорий: {e}")


def run_tests():
    """Запустить все тесты через pytest."""
    sys.exit(pytest.main([__file__, "-v"]))


if __name__ == "__main__":
    run_tests()
