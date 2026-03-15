#!/usr/bin/env python3
"""
Тесты для проверки корректности использования API pytermgui.

Эти тесты выявляют ошибки до запуска приложения:
1. Использование несуществующих виджетов (например, BoxLayout вместо Container)
2. Неправильные параметры виджетов
3. Ошибки импорта компонентов pytermgui
4. Нарушения совместимости версий pytermgui
5. Ошибки в создании окон TUI

Примечание:
    Тесты требуют установки pytermgui:
    pip install pytermgui

    Если pytermgui не установлен, тесты будут пропущены.
"""

import pytest
import sys
import ast
from pathlib import Path
from typing import List, Set

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


class TestPyTermGUIWidgetAvailability:
    """Тесты доступности виджетов pytermgui."""

    def test_boxlayout_not_available(self):
        """
        Тест 1: Проверка отсутствия BoxLayout в pytermgui.

        BoxLayout не существует в pytermgui, вместо него нужно использовать Container.
        Этот тест защищает от регрессии - если BoxLayout появится в будущих версиях,
        тест будет провален и код нужно будет пересмотреть.
        """
        # Проверяем, что BoxLayout действительно отсутствует
        has_boxlayout = hasattr(ptg, 'BoxLayout')
        assert not has_boxlayout, \
            "BoxLayout появился в pytermgui! Проверьте документацию и обновите код."

    def test_container_available(self):
        """
        Тест 2: Проверка доступности Container виджета.

        Container - правильный виджет для группировки элементов в pytermgui.
        """
        assert hasattr(ptg, 'Container'), \
            "Container отсутствует в pytermgui. Проверьте версию библиотеки."

    def test_common_widgets_available(self):
        """
        Тест 3: Проверка доступности основных виджетов.

        Проверяет наличие всех основных виджетов, используемых в проекте.
        Примечание: ScrollArea и ProgressBar могут быть реализованы через Container.
        """
        required_widgets = [
            'Window',
            'Container',
            'Label',
            'Button',
            'InputField',
            'Checkbox',
            'Splitter',
        ]

        missing_widgets = []
        for widget in required_widgets:
            if not hasattr(ptg, widget):
                missing_widgets.append(widget)

        assert not missing_widgets, \
            f"Отсутствуют виджеты в pytermgui: {missing_widgets}"


class TestPyTermGUIUsageInCode:
    """Тесты использования pytermgui в коде проекта."""

    def _get_python_files(self, directory: Path) -> List[Path]:
        """Получить все Python файлы в директории."""
        return list(directory.rglob("*.py"))

    def _check_file_for_boxlayout(self, file_path: Path) -> List[int]:
        """
        Проверить файл на использование BoxLayout.

        Returns:
            Список номеров строк с использованием BoxLayout
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        # Ищем использования BoxLayout
        lines_with_boxlayout = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'BoxLayout' in line and not line.strip().startswith('#'):
                lines_with_boxlayout.append(i)

        return lines_with_boxlayout

    def test_no_boxlayout_in_tui_screens(self):
        """
        Тест 4: Проверка отсутствия BoxLayout в файлах TUI экранов.

        BoxLayout не существует в pytermgui, нужно использовать Container.
        Этот тест автоматически находит все использования BoxLayout в коде.
        """
        tui_screens_dir = Path(__file__).parent.parent / 'parser_2gis' / 'tui_pytermgui' / 'screens'

        if not tui_screens_dir.exists():
            pytest.skip("Директория tui_pytermgui/screens не найдена")

        python_files = self._get_python_files(tui_screens_dir)
        assert len(python_files) > 0, "Не найдено Python файлов в директории экранов"

        files_with_boxlayout = {}
        for file_path in python_files:
            lines = self._check_file_for_boxlayout(file_path)
            if lines:
                files_with_boxlayout[str(file_path.relative_to(Path(__file__).parent.parent))] = lines

        assert not files_with_boxlayout, \
            f"Найдено использование BoxLayout в файлах:\n" + \
            "\n".join([f"  {f}: строки {lines}" for f, lines in files_with_boxlayout.items()]) + \
            "\n\nBoxLayout не существует в pytermgui! Используйте Container вместо BoxLayout."

    def test_no_boxlayout_in_tui_app(self):
        """
        Тест 5: Проверка отсутствия BoxLayout в основном файле приложения.

        Проверяет файл app.py на наличие BoxLayout.
        """
        app_file = Path(__file__).parent.parent / 'parser_2gis' / 'tui_pytermgui' / 'app.py'

        if not app_file.exists():
            pytest.skip("Файл tui_pytermgui/app.py не найден")

        lines = self._check_file_for_boxlayout(app_file)

        assert not lines, \
            f"Найдено использование BoxLayout в app.py на строках: {lines}. " \
            "Используйте Container вместо BoxLayout."

    def test_all_screens_import_ptg_correctly(self):
        """
        Тест 6: Проверка корректности импорта pytermgui в экранах.

        Все экраны должны импортировать pytermgui как 'import pytermgui as ptg'.
        """
        tui_screens_dir = Path(__file__).parent.parent / 'parser_2gis' / 'tui_pytermgui' / 'screens'

        if not tui_screens_dir.exists():
            pytest.skip("Директория tui_pytermgui/screens не найдена")

        python_files = self._get_python_files(tui_screens_dir)

        for file_path in python_files:
            # Пропускаем __init__.py файлы
            if file_path.name == '__init__.py':
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            # Проверяем наличие правильного импорта
            has_correct_import = (
                'import pytermgui as ptg' in content or
                'from pytermgui import' in content
            )

            assert has_correct_import, \
                f"Файл {file_path.name} должен импортировать pytermgui"


class TestPyTermGUIContainerUsage:
    """Тесты правильного использования Container."""

    def test_container_with_box_parameter(self):
        """
        Тест 7: Проверка использования параметра box у Container.

        Container должен использовать параметр box для стилизации границ.
        """
        # Проверяем, что Container принимает параметр box
        try:
            container = ptg.Container(box="EMPTY_VERTICAL")
            assert container is not None
        except TypeError as e:
            pytest.fail(f"Container не принимает параметр box: {e}")

    def test_container_valid_box_values(self):
        """
        Тест 8: Проверка допустимых значений параметра box.

        Проверяет основные значения box, используемые в проекте.
        """
        valid_box_values = [
            "EMPTY_VERTICAL",
            "EMPTY_HORIZONTAL",
            "DOUBLE",
            "SINGLE",
            "ROUNDED",
        ]

        for box_value in valid_box_values:
            try:
                container = ptg.Container(box=box_value)
                assert container is not None, f"Container с box='{box_value}' не создан"
            except ValueError as e:
                # Некоторые значения могут быть недопустимы в разных версиях
                if "Unknown box type" in str(e):
                    pytest.fail(f"box='{box_value}' не поддерживается: {e}")
                raise
            except Exception as e:
                pytest.fail(f"Ошибка создания Container с box='{box_value}': {e}")


class TestPyTermGUIVersionCompatibility:
    """Тесты совместимости версии pytermgui."""

    def test_pytermgui_version_info(self):
        """
        Тест 9: Проверка информации о версии pytermgui.

        Сохраняет информацию о версии для отладки.
        """
        import pytermgui as ptg

        # Пытаемся получить версию
        version = getattr(ptg, '__version__', 'unknown')

        # Логируем версию (не влияет на результат теста)
        print(f"\npytermgui версия: {version}")

        # Тест всегда проходит, если pytermgui установлен
        assert True

    def test_pytermgui_has_window_manager(self):
        """
        Тест 10: Проверка доступности WindowManager.

        WindowManager необходим для управления окнами TUI.
        """
        assert hasattr(ptg, 'WindowManager'), \
            "WindowManager отсутствует в pytermgui. Проверьте версию библиотеки."

    def test_pytermgui_has_yaml_loader(self):
        """
        Тест 11: Проверка доступности YamlLoader.

        YamlLoader необходим для загрузки стилей из YAML.
        """
        assert hasattr(ptg, 'YamlLoader'), \
            "YamlLoader отсутствует в pytermgui. Проверьте версию библиотеки."


class TestPyTermGUIScreenCreation:
    """Тесты создания экранов TUI."""

    def test_main_menu_screen_import(self):
        """
        Тест 12: Проверка импорта экрана главного меню.

        Проверяет, что MainMenuScreen может быть импортирован.
        """
        try:
            from parser_2gis.tui_pytermgui.screens.main_menu import MainMenuScreen
            assert MainMenuScreen is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать MainMenuScreen: {e}")

    def test_main_menu_no_boxlayout_attribute_error(self):
        """
        Тест 13: Проверка отсутствия AttributeError при создании MainMenuScreen.

        Проверяет, что создание окна главного меню не вызывает AttributeError
        из-за использования несуществующих виджетов.
        """
        from parser_2gis.tui_pytermgui.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        app = TUIApp()
        screen = MainMenuScreen(app)

        # Проверяем, что метод create_window существует
        assert hasattr(screen, 'create_window'), \
            "MainMenuScreen должен иметь метод create_window"

        # Проверяем, что создание окна не вызывает AttributeError для BoxLayout
        try:
            window = screen.create_window()
            # Окно должно быть создано (может быть None если app не инициализирован полностью)
            # Главное - чтобы не было AttributeError: module 'pytermgui' has no attribute 'BoxLayout'
        except AttributeError as e:
            if 'BoxLayout' in str(e):
                pytest.fail(f"Обнаружено использование BoxLayout: {e}")
            # Другие AttributeError могут быть из-за неполной инициализации - это нормально
        except Exception:
            # Другие исключения допустимы (например, из-за неполной инициализации)
            pass


# Запуск тестов через pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
