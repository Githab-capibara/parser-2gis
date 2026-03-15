#!/usr/bin/env python3
"""
Тесты для выявления ошибок с InputField.

Эти тесты помогают выявлять ошибки типа:
- AttributeError при попытке установить value через присваивание
- Неправильное использование API InputField
- Отсутствие вспомогательных методов для установки значений

Примечание:
    Тесты требуют установки pytermgui:
    pip install pytermgui

    Если pytermgui не установлен, тесты будут пропущены.
"""

import pytest
import sys
import ast
import re
from pathlib import Path
from typing import List, Tuple

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


class TestInputFieldValueSetter:
    """Тесты проверки отсутствия setter для value у InputField."""

    def test_inputfield_has_no_value_setter(self):
        """
        Тест 1: Проверка что InputField не имеет setter для value.

        InputField в pytermgui имеет свойство value только для чтения.
        Попытка установить значение через присваивание должна вызывать AttributeError.
        
        Эта ошибка часто возникает при неправильном использовании API:
            field.value = "новое значение"  # НЕПРАВИЛЬНО!
        
        Правильный способ:
            field.delete_back()  # Очистить
            field.insert_text("новое значение")  # Вставить новое
        """
        # Создаём InputField
        field = ptg.InputField(label="Тест:", value="старое значение")
        
        # Проверяем что начальное значение установлено
        assert field.value == "старое значение"
        
        # Попытка установить value через присваивание должна вызвать AttributeError
        with pytest.raises(AttributeError) as exc_info:
            field.value = "новое значение"
        
        # Проверяем что ошибка связана с отсутствием setter
        assert "setter" in str(exc_info.value).lower() or "no setter" in str(exc_info.value).lower()


class TestInputFieldCorrectUsage:
    """Тесты правильного способа установки значения в InputField."""

    def test_inputfield_value_change_via_delete_insert(self):
        """
        Тест 2: Проверка правильного способа установки значения через delete_back + insert_text.

        Правильный API для изменения значения InputField:
        1. Очистить текущее значение через delete_back()
        2. Вставить новое значение через insert_text()
        
        Этот тест проверяет что такой подход работает корректно.
        """
        # Создаём InputField с начальным значением
        field = ptg.InputField(label="Тест:", value="старое значение")
        
        # Проверяем начальное значение
        assert field.value == "старое значение"
        
        # Очищаем поле через delete_back()
        # delete_back() удаляет по одному символу с конца
        original_length = len(field.value)
        for _ in range(original_length):
            field.delete_back()
        
        # Проверяем что поле очищено
        assert field.value == ""
        
        # Устанавливаем новое значение через insert_text()
        field.insert_text("новое значение")
        
        # Проверяем что значение установлено правильно
        assert field.value == "новое значение"

    def test_inputfield_delete_back_removes_characters(self):
        """
        Дополнительный тест: Проверка работы метода delete_back().

        Проверяет что delete_back() действительно удаляет символы по одному.
        """
        field = ptg.InputField(label="Тест:", value="12345")
        
        assert field.value == "12345"
        
        # Удаляем по одному символу
        field.delete_back()
        assert field.value == "1234"
        
        field.delete_back()
        assert field.value == "123"
        
        # Очищаем полностью
        field.delete_back()
        field.delete_back()
        field.delete_back()
        assert field.value == ""


class TestCheckboxValueSetter:
    """Тесты проверки наличия setter для value у Checkbox."""

    def test_custom_checkbox_has_value_setter(self):
        """
        Тест 3: Проверка что Checkbox имеет setter для value (кастомная реализация).

        В отличие от InputField, наш кастомный Checkbox из parser_2gis
        имеет полноценный setter для свойства value.
        
        Это позволяет устанавливать значение через присваивание:
            checkbox.value = True  # ПРАВИЛЬНО для Checkbox!
        """
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        
        # Создаём Checkbox с начальным значением
        checkbox = Checkbox(label="Тест", value=False)
        
        # Проверяем начальное значение
        assert checkbox.value is False
        
        # Устанавливаем новое значение через присваивание
        checkbox.value = True
        
        # Проверяем что значение установлено
        assert checkbox.value is True
        
        # Устанавливаем обратно в False
        checkbox.value = False
        assert checkbox.value is False

    def test_custom_checkbox_on_change_callback(self):
        """
        Дополнительный тест: Проверка вызова on_change при установке value.

        Проверяет что callback on_change вызывается при изменении значения.
        """
        from parser_2gis.tui_pytermgui.widgets import Checkbox
        
        callback_called = False
        received_value = None
        
        def on_change(value: bool) -> None:
            nonlocal callback_called, received_value
            callback_called = True
            received_value = value
        
        # Создаём Checkbox с callback
        checkbox = Checkbox(label="Тест", value=False, on_change=on_change)
        
        # Устанавливаем новое значение
        checkbox.value = True
        
        # Проверяем что callback был вызван
        assert callback_called is True
        assert received_value is True


class TestInputFieldAssignmentStaticAnalysis:
    """Тесты статического анализа кода на наличие неправильных присваиваний value."""

    def _get_python_files(self, directory: Path) -> List[Path]:
        """
        Получить все Python файлы в директории.
        
        Args:
            directory: Директория для поиска файлов
            
        Returns:
            Список путей к Python файлам
        """
        if not directory.exists():
            return []
        return list(directory.rglob("*.py"))

    def _find_value_assignments(self, file_path: Path) -> List[Tuple[int, str]]:
        """
        Найти присваивания вида `variable.value = ` в файле.
        
        Анализирует код и находит строки где происходит присваивание
        свойства value у переменных.
        
        Args:
            file_path: Путь к файлу для анализа
            
        Returns:
            Список кортежей (номер_строки, текст_строки)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []
        
        # Ищем присваивания вида: что-то.value = 
        # Регулярное выражение ищет паттерн: идентификатор.value = значение
        pattern = r'^\s*(\w+)\.value\s*=\s*[^=]'
        
        lines_with_assignments = []
        for i, line in enumerate(content.split('\n'), 1):
            # Пропускаем комментарии
            if line.strip().startswith('#'):
                continue
            
            match = re.search(pattern, line)
            if match:
                variable_name = match.group(1)
                # Пропускаем известные корректные случаи:
                # - self.value (это может быть setter внутри класса)
                # - checkbox (это наш кастомный Checkbox с setter)
                if variable_name in ('self', 'checkbox', 'cb'):
                    continue
                
                lines_with_assignments.append((i, line.strip()))
        
        return lines_with_assignments

    def _is_inputfield_variable(self, variable_name: str, file_content: str) -> bool:
        """
        Определить является ли переменная InputField по контексту объявления.
        
        Args:
            variable_name: Имя переменной
            file_content: Содержимое файла для анализа
            
        Returns:
            True если переменная является InputField
        """
        # Ищем объявления переменных типа ptg.InputField или InputField
        patterns = [
            rf'{variable_name}\s*=\s*ptg\.InputField\(',
            rf'{variable_name}\s*=\s*InputField\(',
            rf'self\._fields\["\w+"\]\s*=\s*ptg\.InputField\(',
            rf'self\._fields\["\w+"\]\s*=\s*InputField\(',
        ]
        
        for pattern in patterns:
            if re.search(pattern, file_content):
                return True
        
        return False

    def test_no_inputfield_value_assignment_in_screens(self):
        """
        Тест 4: Статический анализ кода на отсутствие присваиваний value у InputField.

        Сканирует все файлы в tui_pytermgui/screens/ и ищет присваивания вида:
            field.value = "значение"  # НЕПРАВИЛЬНО для InputField!
        
        Если найдены такие присваивания для переменных типа InputField,
        тест завершается ошибностью.
        
        Примечание:
            - Присваивания self.value пропускаются (это может быть setter внутри класса)
            - Присваивания checkbox.value пропускаются (Checkbox имеет setter)
        """
        tui_screens_dir = Path(__file__).parent.parent / 'parser_2gis' / 'tui_pytermgui' / 'screens'
        
        if not tui_screens_dir.exists():
            pytest.skip("Директория tui_pytermgui/screens не найдена")
        
        python_files = self._get_python_files(tui_screens_dir)
        assert len(python_files) > 0, "Не найдено Python файлов в директории экранов"
        
        files_with_violations = {}
        
        for file_path in python_files:
            # Пропускаем __init__.py файлы
            if file_path.name == '__init__.py':
                continue
            
            assignments = self._find_value_assignments(file_path)
            
            if assignments:
                # Проверяем каждый случай
                violations = []
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                
                for line_num, line_text in assignments:
                    # Извлекаем имя переменной
                    match = re.search(r'^\s*(\w+)\.value\s*=', line_text)
                    if match:
                        var_name = match.group(1)
                        # Проверяем является ли переменная InputField
                        if self._is_inputfield_variable(var_name, content):
                            violations.append((line_num, line_text))
                
                if violations:
                    files_with_violations[str(file_path.relative_to(Path(__file__).parent.parent))] = violations
        
        assert not files_with_violations, \
            "Найдено неправильное использование InputField.value:\n" + \
            "\n".join([
                f"  {f}:\n" + "\n".join([f"    Строка {line}: {text}" for line, text in violations])
                for f, violations in files_with_violations.items()
            ]) + \
            "\n\nInputField не имеет setter для value! " \
            "Используйте delete_back() + insert_text() вместо присваивания."


class TestBrowserSettingsHelperMethod:
    """Тесты вспомогательного метода _set_input_field_value."""

    def test_set_input_field_value_method_exists(self):
        """
        Тест 5: Проверка что метод _set_input_field_value существует в BrowserSettingsScreen.

        BrowserSettingsScreen должен иметь вспомогательный метод _set_input_field_value
        для корректной установки значений в InputField.
        
        Этот метод инкапсулирует правильную последовательность:
        1. delete_back() для очистки
        2. insert_text() для установки нового значения
        """
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = BrowserSettingsScreen(app)
        
        # Проверяем что метод существует
        assert hasattr(screen, '_set_input_field_value'), \
            "BrowserSettingsScreen должен иметь метод _set_input_field_value"
        
        # Проверяем что метод вызываемый
        assert callable(getattr(screen, '_set_input_field_value')), \
            "_set_input_field_value должен быть вызываемым методом"

    def test_set_input_field_value_works_correctly(self):
        """
        Тест 5 (продолжение): Проверка корректной работы метода _set_input_field_value.

        Проверяет что метод правильно устанавливает значение в InputField:
        - Очищает старое значение
        - Устанавливает новое значение
        """
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        import pytermgui as ptg
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = BrowserSettingsScreen(app)
        
        # Создаём тестовый InputField
        field = ptg.InputField(label="Тест:", value="старое значение")
        
        # Проверяем начальное значение
        assert field.value == "старое значение"
        
        # Используем вспомогательный метод для установки нового значения
        screen._set_input_field_value(field, "новое значение")
        
        # Проверяем что значение установлено правильно
        assert field.value == "новое значение"

    def test_set_input_field_value_with_empty_string(self):
        """
        Дополнительный тест: Проверка работы метода с пустой строкой.

        Проверяет что метод может очистить поле установкой пустой строки.
        """
        from parser_2gis.tui_pytermgui.screens.browser_settings import BrowserSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        import pytermgui as ptg
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = BrowserSettingsScreen(app)
        
        # Создаём тестовый InputField с начальным значением
        field = ptg.InputField(label="Тест:", value="значение для очистки")
        
        # Проверяем начальное значение
        assert field.value == "значение для очистки"
        
        # Очищаем поле через вспомогательный метод
        screen._set_input_field_value(field, "")
        
        # Проверяем что поле очищено
        assert field.value == ""


# Запуск тестов через pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
