#!/usr/bin/env python3
"""
Тесты для выявления ошибок с неправильным использованием InputField.value = ...

Эти тесты помогают выявлять критические ошибки типа:
- Прямое присваивание value для InputField (вызывает AttributeError)
- Отсутствие вспомогательных методов для установки значений
- Неправильная реализация метода _reset

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
from typing import List, Tuple, Dict, Any

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


class TestInputFieldStaticAnalysis:
    """
    Тест 1: Статическая проверка кода на отсутствие присваиваний value для InputField.
    
    Этот тест сканирует исходный код проекта и ищет паттерны неправильного
    использования API InputField, а именно:
        field.value = "значение"  # НЕПРАВИЛЬНО!
    
    InputField в pytermgui не имеет setter для свойства value.
    Для изменения значения нужно использовать:
        field.delete_back()  # Очистить
        field.insert_text("новое")  # Вставить новое
    """

    def _get_python_files(self, directory: Path) -> List[Path]:
        """
        Получить все Python файлы в директории рекурсивно.

        Args:
            directory: Директория для поиска файлов

        Returns:
            Список путей к Python файлам
        """
        if not directory.exists():
            return []
        return list(directory.rglob("*.py"))

    def _find_inputfield_value_assignments(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Найти присваивания value для переменных типа InputField в файле.

        Анализирует код и находит строки где происходит присваивание
        свойства value у переменных, которые являются InputField.

        Args:
            file_path: Путь к файлу для анализа

        Returns:
            Список словарей с информацией о нарушениях:
            - line_number: номер строки
            - line_text: текст строки
            - variable_name: имя переменной
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except (OSError, UnicodeDecodeError):
            return []

        violations = []
        
        # Паттерн для поиска присваиваний вида: identifier.value = 
        assignment_pattern = r'^\s*(\w+(?:\[\w+\])?)\.value\s*=\s*[^=]'
        
        # Паттерны для определения является ли переменная InputField
        inputfield_patterns = [
            r'=\s*ptg\.InputField\(',
            r'=\s*InputField\(',
        ]
        
        # Собираем все переменные, которые являются InputField
        inputfield_vars = set()
        for line in lines:
            # Пропускаем комментарии
            if line.strip().startswith('#'):
                continue
            
            # Ищем объявления InputField
            for pattern in inputfield_patterns:
                match = re.search(r'(\w+(?:\[\w+\])?)\s*' + pattern, line)
                if match:
                    var_name = match.group(1)
                    inputfield_vars.add(var_name)
        
        # Ищем присваивания value
        for i, line in enumerate(lines, 1):
            # Пропускаем комментарии
            if line.strip().startswith('#'):
                continue
            
            match = re.search(assignment_pattern, line)
            if match:
                var_name = match.group(1)
                
                # Пропускаем известные корректные случаи:
                # - self.value (это может быть setter внутри класса)
                # - checkbox (это наш кастомный Checkbox с setter)
                # - cb (сокращение для checkbox)
                if var_name in ('self', 'checkbox', 'cb'):
                    continue
                
                # Проверяем является ли переменная InputField
                # или похожа на поле из словаря self._fields[...]
                is_inputfield = var_name in inputfield_vars
                is_fields_dict = '_fields' in var_name or var_name.startswith('self._fields')
                
                if is_inputfield or is_fields_dict:
                    violations.append({
                        'line_number': i,
                        'line_text': line.strip(),
                        'variable_name': var_name
                    })
        
        return violations

    def test_no_inputfield_value_assignment_in_project(self):
        """
        Тест 1: Статический анализ кода на отсутствие присваиваний value у InputField.
        
        Сканирует все файлы в parser_2gis/tui_pytermgui/ и ищет присваивания вида:
            field.value = "значение"  # НЕПРАВИЛЬНО для InputField!
            self._fields["name"].value = "значение"  # ТОЖЕ НЕПРАВИЛЬНО!
        
        Если найдены такие присваивания, тест завершается ошибкостью.
        
        Примечание:
            - Присваивания self.value пропускаются (это может быть setter внутри класса)
            - Присваивания checkbox.value пропускаются (Checkbox имеет setter)
        
        Raises:
            AssertionError: Если найдено неправильное использование InputField.value
        """
        tui_dir = Path(__file__).parent.parent / 'parser_2gis' / 'tui_pytermgui'
        
        if not tui_dir.exists():
            pytest.skip("Директория tui_pytermgui не найдена")
        
        python_files = self._get_python_files(tui_dir)
        assert len(python_files) > 0, "Не найдено Python файлов в tui_pytermgui"
        
        files_with_violations = {}
        
        for file_path in python_files:
            # Пропускаем __init__.py файлы и кэш
            if file_path.name == '__init__.py':
                continue
            if '__pycache__' in str(file_path):
                continue
            
            violations = self._find_inputfield_value_assignments(file_path)
            
            if violations:
                rel_path = str(file_path.relative_to(Path(__file__).parent.parent))
                files_with_violations[rel_path] = violations
        
        assert not files_with_violations, (
            "Найдено неправильное использование InputField.value:\n\n" +
            "\n\n".join([
                f"Файл: {f}\n" +
                "\n".join([
                    f"  Строка {v['line_number']}: {v['line_text']}\n"
                    f"    Переменная: {v['variable_name']}"
                    for v in violations
                ])
                for f, violations in files_with_violations.items()
            ]) +
            "\n\n❗ InputField не имеет setter для value! "
            "Используйте метод _set_input_field_value() или "
            "последовательность delete_back() + insert_text()."
        )


class TestOutputSettingsSetInputFieldValue:
    """
    Тест 2: Юнит-тест метода _set_input_field_value в output_settings.py.
    
    Проверяет корректность работы вспомогательного метода для установки
    значений в InputField. Этот метод инкапсулирует правильную
    последовательность операций:
    1. Очистка текущего значения через delete_back()
    2. Установка нового значения через insert_text()
    """

    def test_set_input_field_value_method_exists(self):
        """
        Проверить что метод _set_input_field_value существует в OutputSettingsScreen.
        
        OutputSettingsScreen должен иметь вспомогательный метод _set_input_field_value
        для корректной установки значений в InputField.
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Проверяем что метод существует
        assert hasattr(screen, '_set_input_field_value'), (
            "OutputSettingsScreen должен иметь метод _set_input_field_value"
        )
        
        # Проверяем что метод вызываемый
        assert callable(getattr(screen, '_set_input_field_value')), (
            "_set_input_field_value должен быть вызываемым методом"
        )

    def test_set_input_field_value_changes_value(self):
        """
        Проверить что метод _set_input_field_value корректно меняет значение.
        
        Тест проверяет что:
        - Старое значение полностью удаляется
        - Новое значение правильно устанавливается
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Создаём тестовый InputField с начальным значением
        field = ptg.InputField(label="Тест:", value="старое значение")
        
        # Проверяем начальное значение
        assert field.value == "старое значение", "Начальное значение должно быть установлено"
        
        # Используем вспомогательный метод для установки нового значения
        screen._set_input_field_value(field, "новое значение")
        
        # Проверяем что значение изменено
        assert field.value == "новое значение", (
            "Метод _set_input_field_value должен устанавливать новое значение"
        )

    def test_set_input_field_value_with_empty_string(self):
        """
        Проверить что метод _set_input_field_value работает с пустой строкой.
        
        Тест проверяет что метод может полностью очистить поле,
        устанавливая пустую строку.
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Создаём тестовый InputField с длинным значением
        field = ptg.InputField(label="Тест:", value="очень длинное значение для очистки")
        
        # Проверяем начальное значение
        assert len(field.value) > 0, "Начальное значение должно быть не пустым"
        
        # Очищаем поле через вспомогательный метод
        screen._set_input_field_value(field, "")
        
        # Проверяем что поле очищено
        assert field.value == "", (
            "Метод _set_input_field_value должен очищать поле при установке пустой строки"
        )

    def test_set_input_field_value_with_special_characters(self):
        """
        Проверить что метод _set_input_field_value работает со спецсимволами.
        
        Тест проверяет что метод корректно обрабатывает специальные символы,
        кириллицу и другие Unicode символы.
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Создаём тестовый InputField
        field = ptg.InputField(label="Тест:", value="old")
        
        # Тестовые значения с разными символами
        test_values = [
            "utf-8-sig",  # Латиница
            "кодировка",  # Кириллица
            "test;value",  # Спецсимволы
            "日本語",  # Unicode
            "12345",  # Цифры
        ]
        
        for test_value in test_values:
            screen._set_input_field_value(field, test_value)
            assert field.value == test_value, (
                f"Метод должен корректно устанавливать значение: {test_value}"
            )


class TestOutputSettingsReset:
    """
    Тест 3: Юнит-тест метода _reset в output_settings.py.
    
    Проверяет что метод _reset корректно сбрасывает настройки к значениям
    по умолчанию и НЕ вызывает AttributeError при работе с InputField.
    
    Это критически важный тест, так как неправильная реализация _reset
    может использовать прямое присваивание value, что вызывает ошибку:
        AttributeError: property 'value' has no setter
    """

    def test_reset_method_exists(self):
        """
        Проверить что метод _reset существует в OutputSettingsScreen.
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Проверяем что метод существует
        assert hasattr(screen, '_reset'), (
            "OutputSettingsScreen должен иметь метод _reset"
        )

    def test_reset_does_not_raise_attribute_error(self):
        """
        Проверить что метод _reset не вызывает AttributeError.
        
        Это основной тест который проверяет что метод _reset использует
        правильный API для установки значений в InputField (через
        _set_input_field_value), а не прямое присваивание value.
        
        Raises:
            AssertionError: Если метод вызывает AttributeError
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Создаём окно чтобы инициализировать все поля
        window = screen.create_window()
        
        # Проверяем что поля инициализированы
        assert len(screen._fields) > 0, "Поля должны быть инициализированы"
        
        # Вызываем метод _reset - не должно быть AttributeError
        try:
            screen._reset()
        except AttributeError as e:
            if "setter" in str(e).lower() or "no setter" in str(e).lower():
                pytest.fail(
                    f"Метод _reset вызывает AttributeError при работе с InputField: {e}\n"
                    "Возможно используется прямое присваивание value вместо "
                    "_set_input_field_value()"
                )
            raise
        
        # Если дошли сюда - тест пройден
        assert True, "Метод _reset выполнился без AttributeError"

    def test_reset_restores_default_values(self):
        """
        Проверить что метод _reset восстанавливает значения по умолчанию.
        
        Тест проверяет что после вызова _reset:
        - Поля InputField имеют значения по умолчанию
        - Поля Checkbox имеют значения по умолчанию
        - Конфигурация обновлена значениями по умолчанию
        """
        from parser_2gis.tui_pytermgui.screens.output_settings import OutputSettingsScreen
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.writer.options import WriterOptions, CSVOptions
        
        # Создаём приложение и экран
        app = TUIApp()
        screen = OutputSettingsScreen(app)
        
        # Создаём окно чтобы инициализировать все поля
        window = screen.create_window()
        
        # Меняем значения полей перед сбросом
        # Для InputField используем правильный API
        for field_name, field in screen._fields.items():
            if isinstance(field, ptg.InputField):
                screen._set_input_field_value(field, "test_value")
            elif hasattr(field, 'value'):
                # Для Checkbox
                field.value = not field.value
        
        # Вызываем сброс
        screen._reset()
        
        # Проверяем что значения сбросились к дефолтным
        default_writer = WriterOptions()
        default_csv = CSVOptions(columns_per_entity=3)
        
        # Проверяем encoding
        encoding_field = screen._fields.get("encoding")
        if encoding_field and isinstance(encoding_field, ptg.InputField):
            assert encoding_field.value == default_writer.encoding, (
                f"Поле encoding должно быть сброшено к '{default_writer.encoding}'"
            )
        
        # Проверяем columns_per_entity
        columns_field = screen._fields.get("columns_per_entity")
        if columns_field and isinstance(columns_field, ptg.InputField):
            assert columns_field.value == str(default_csv.columns_per_entity), (
                f"Поле columns_per_entity должно быть сброшено к '{default_csv.columns_per_entity}'"
            )


class TestAllScreensInputFieldUsage:
    """
    Тест 4: Проверка всех экранов tui_pytermgui на правильную обработку InputField.
    
    Этот тест сканирует все файлы экранов в директории screens/ и проверяет:
    1. Наличие вспомогательного метода _set_input_field_value (если есть InputField)
    2. Отсутствие прямого присваивания value для InputField
    3. Корректное использование API в методе _reset
    """

    def _get_screen_files(self) -> List[Path]:
        """
        Получить все файлы экранов в директории screens.

        Returns:
            Список путей к файлам экранов
        """
        screens_dir = Path(__file__).parent.parent / 'parser_2gis' / 'tui_pytermgui' / 'screens'
        if not screens_dir.exists():
            return []
        
        files = []
        for file_path in screens_dir.glob("*.py"):
            if file_path.name != '__init__.py':
                files.append(file_path)
        return files

    def _check_screen_has_helper_method(self, file_path: Path) -> Dict[str, Any]:
        """
        Проверить что экран с InputField и _reset имеет метод _set_input_field_value.

        Если экран использует InputField И имеет метод _reset, он должен иметь
        вспомогательный метод _set_input_field_value для корректной установки
        значений при сбросе настроек.

        Args:
            file_path: Путь к файлу экрана

        Returns:
            Словарь с результатом проверки:
            - has_inputfield: есть ли InputField
            - has_reset: есть ли метод _reset
            - has_helper_method: есть ли _set_input_field_value
            - screen_class: имя класса экрана
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return {'error': f"Не удалось прочитать файл {file_path}"}
        
        # Проверяем наличие InputField
        has_inputfield = bool(re.search(r'InputField\(', content))
        
        # Проверяем наличие метода _reset
        has_reset = bool(re.search(r'def\s+_reset\s*\(', content))
        
        # Проверяем наличие вспомогательного метода
        has_helper_method = bool(re.search(r'def\s+_set_input_field_value', content))
        
        # Извлекаем имя класса
        class_match = re.search(r'class\s+(\w+Screen)', content)
        screen_class = class_match.group(1) if class_match else "Unknown"
        
        return {
            'has_inputfield': has_inputfield,
            'has_reset': has_reset,
            'has_helper_method': has_helper_method,
            'screen_class': screen_class,
            'file_path': str(file_path)
        }

    def _check_reset_method_implementation(self, file_path: Path) -> Dict[str, Any]:
        """
        Проверить реализацию метода _reset на наличие прямого присваивания value.

        Args:
            file_path: Путь к файлу экрана

        Returns:
            Словарь с результатом проверки:
            - has_reset: есть ли метод _reset
            - has_direct_assignment: есть ли прямое присваивание value для InputField
            - violations: список нарушений (только для InputField)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except (OSError, UnicodeDecodeError):
            return {'error': f"Не удалось прочитать файл {file_path}"}
        
        has_reset = bool(re.search(r'def\s+_reset\s*\(', content))
        violations = []
        
        # Определяем какие переменные являются InputField
        inputfield_vars = set()
        for line in lines:
            # Ищем объявления InputField
            match = re.search(r'self\._fields\["(\w+)"\]\s*=\s*(?:ptg\.)?InputField\(', line)
            if match:
                inputfield_vars.add(match.group(1))
        
        if has_reset:
            # Находим метод _reset и анализируем его содержимое
            in_reset_method = False
            reset_indent = 0
            
            for i, line in enumerate(lines, 1):
                # Проверяем начало метода _reset
                reset_match = re.match(r'^(\s*)def\s+_reset\s*\(', line)
                if reset_match:
                    in_reset_method = True
                    reset_indent = len(reset_match.group(1))
                    continue
                
                # Проверяем выход из метода (новая функция или класс)
                if in_reset_method:
                    current_indent = len(line) - len(line.lstrip())
                    if line.strip() and current_indent <= reset_indent and not line.strip().startswith('#'):
                        if re.match(r'^\s*(def|class)\s', line):
                            in_reset_method = False
                            continue
                    
                    # Ищем присваивания value внутри _reset
                    value_match = re.search(r'self\._fields\["(\w+)"\]\.value\s*=\s*[^=]', line)
                    if value_match:
                        field_name = value_match.group(1)
                        
                        # Проверяем является ли поле InputField (а не Checkbox)
                        # InputField обычно имеют числовые или строковые значения
                        # Checkbox имеют булевы значения
                        is_inputfield = field_name in inputfield_vars
                        
                        # Дополнительная проверка: если в строке есть str() или int(),
                        # это скорее всего InputField
                        has_type_conversion = bool(re.search(r'\bstr\(|\bint\(', line))
                        
                        # Пропускаем если это Checkbox (булевы значения без конверсии)
                        is_checkbox_value = bool(re.search(
                            r'\.(True|False|headless|disable_images|start_maximized|'
                            r'silent_browser|verbose|add_rubrics|add_comments|'
                            r'remove_empty_columns|remove_duplicates|skip_404_response|'
                            r'use_gc|stop_on_first_404|retry_on_network_errors)\b',
                            line
                        ))
                        
                        if is_inputfield or has_type_conversion:
                            if not is_checkbox_value:
                                violations.append({
                                    'line_number': i,
                                    'line_text': line.strip(),
                                    'field_name': field_name
                                })
        
        return {
            'has_reset': has_reset,
            'has_direct_assignment': len(violations) > 0,
            'violations': violations,
            'file_path': str(file_path)
        }

    def test_screens_with_inputfield_have_helper_method(self):
        """
        Тест 4a: Проверить что все экраны с InputField и _reset имеют метод _set_input_field_value.
        
        Если экран использует InputField И имеет метод _reset, он должен иметь
        вспомогательный метод _set_input_field_value для корректной установки
        значений при сбросе настроек.
        
        Экраны без метода _reset (например, CitySelectorScreen) не требуют
        вспомогательного метода, так как они не меняют значение InputField
        программно.
        
        Raises:
            AssertionError: Если экран с InputField и _reset не имеет вспомогательного метода
        """
        screen_files = self._get_screen_files()
        assert len(screen_files) > 0, "Не найдено файлов экранов"
        
        screens_without_helper = []
        
        for file_path in screen_files:
            result = self._check_screen_has_helper_method(file_path)
            
            if 'error' in result:
                continue
            
            # Проверяем только экраны с InputField И _reset
            if result['has_inputfield'] and result['has_reset'] and not result['has_helper_method']:
                screens_without_helper.append(result)
        
        assert not screens_without_helper, (
            "Найдены экраны с InputField и _reset без метода _set_input_field_value:\n\n" +
            "\n".join([
                f"  {s['screen_class']} ({s['file_path']})"
                for s in screens_without_helper
            ]) +
            "\n\nЭкраны с InputField и _reset должны иметь метод _set_input_field_value "
            "для корректной установки значений."
        )

    def test_reset_method_no_direct_value_assignment(self):
        """
        Тест 4b: Проверить что метод _reset не использует прямое присваивание value.
        
        Метод _reset должен использовать _set_input_field_value для установки
        значений в InputField, а не прямое присваивание .value = ...
        
        Raises:
            AssertionError: Если найден метод _reset с прямым присваиванием value
        """
        screen_files = self._get_screen_files()
        assert len(screen_files) > 0, "Не найдено файлов экранов"
        
        screens_with_violations = []
        
        for file_path in screen_files:
            result = self._check_reset_method_implementation(file_path)
            
            if 'error' in result:
                continue
            
            if result['has_direct_assignment']:
                screens_with_violations.append(result)
        
        assert not screens_with_violations, (
            "Найдены экраны с прямым присваиванием value в методе _reset:\n\n" +
            "\n".join([
                f"  Файл: {s['file_path']}\n" +
                "\n".join([
                    f"    Строка {v['line_number']}: {v['line_text']}"
                    for v in s['violations']
                ])
                for s in screens_with_violations
            ]) +
            "\n\nМетод _reset должен использовать _set_input_field_value() "
            "вместо прямого присваивания .value = ..."
        )


class TestInputFieldIntegration:
    """
    Тест 5: Интеграционный тест с реальным InputField.
    
    Этот тест создаёт реальный экземпляр InputField и проверяет оба способа
    установки значения:
    1. Неправильный (прямое присваивание) - должен вызвать AttributeError
    2. Правильный (через delete_back + insert_text) - должен работать
    
    Тест демонстрирует разницу между правильным и неправильным API.
    """

    def test_inputfield_direct_assignment_raises_error(self):
        """
        Проверить что прямое присваивание value вызывает AttributeError.
        
        Это тест демонстрирует неправильный способ установки значения:
            field.value = "новое значение"  # ❌ НЕПРАВИЛЬНО!
        
        Raises:
            AssertionError: Если присваивание не вызывает AttributeError
        """
        # Создаём InputField
        field = ptg.InputField(label="Тест:", value="старое значение")
        
        # Проверяем начальное значение
        assert field.value == "старое значение"
        
        # Попытка прямого присваивания должна вызвать AttributeError
        with pytest.raises(AttributeError) as exc_info:
            field.value = "новое значение"
        
        # Проверяем что ошибка связана с отсутствием setter
        error_message = str(exc_info.value).lower()
        assert "setter" in error_message or "no setter" in error_message, (
            f"Ожидалась ошибка об отсутствии setter, получено: {exc_info.value}"
        )

    def test_inputfield_correct_api_works(self):
        """
        Проверить что правильный API (delete_back + insert_text) работает.
        
        Это тест демонстрирует правильный способ установки значения:
            for _ in range(len(field.value)):
                field.delete_back()  # Очищаем
            field.insert_text("новое")  # Вставляем новое
        
        Тест проверяет что такой подход работает корректно.
        """
        # Создаём InputField с начальным значением
        field = ptg.InputField(label="Тест:", value="старое значение")
        
        # Проверяем начальное значение
        assert field.value == "старое значение"
        
        # Правильный способ: очистка + вставка
        original_length = len(field.value)
        for _ in range(original_length):
            field.delete_back()
        
        field.insert_text("новое значение")
        
        # Проверяем что значение установлено правильно
        assert field.value == "новое значение"

    def test_inputfield_helper_method_pattern(self):
        """
        Проверить что вспомогательный метод _set_input_field_value работает.
        
        Этот тест проверяет паттерн использования вспомогательного метода,
        который инкапсулирует правильную последовательность операций.
        
        Тест создаёт mock-объект экрана с методом _set_input_field_value
        и проверяет что метод корректно устанавливает значения.
        """
        # Создаём класс с вспомогательным методом (как в output_settings.py)
        class MockScreen:
            def _set_input_field_value(self, field: ptg.InputField, value: str) -> None:
                """Установить значение для InputField."""
                for _ in range(len(field.value)):
                    field.delete_back()
                field.insert_text(value)
        
        # Создаём экран и поле
        screen = MockScreen()
        field = ptg.InputField(label="Тест:", value="initial")
        
        # Проверяем начальное значение
        assert field.value == "initial"
        
        # Используем вспомогательный метод
        screen._set_input_field_value(field, "changed")
        
        # Проверяем результат
        assert field.value == "changed"
        
        # Тестируем с пустой строкой
        screen._set_input_field_value(field, "")
        assert field.value == ""
        
        # Тестируем с кириллицей
        screen._set_input_field_value(field, "тест")
        assert field.value == "тест"

    def test_inputfield_multiple_changes(self):
        """
        Проверить что InputField поддерживает многократную смену значения.
        
        Тест проверяет что можно многократно менять значение поля,
        используя правильный API.
        """
        field = ptg.InputField(label="Тест:", value="start")
        
        # Последовательность изменений
        test_sequence = [
            "первое",
            "второе",
            "третье",
            "",
            "финальное значение",
        ]
        
        for expected_value in test_sequence:
            # Очищаем поле
            for _ in range(len(field.value)):
                field.delete_back()
            
            # Устанавливаем новое значение
            field.insert_text(expected_value)
            
            # Проверяем
            assert field.value == expected_value, (
                f"Значение должно быть '{expected_value}', получено '{field.value}'"
            )


# Запуск тестов через pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
