#!/usr/bin/env python3
"""
Новые тесты для выявления проблем TUI.

Эти тесты проверяют:
1. Отсутствие несуществующих виджетов pytermgui (например, ScrollArea)
2. Корректность импорта кастомных виджетов
3. Отсутствие неправильных стилей [text] в коде
4. Корректность размеров окон (ширина должна быть указана)
5. Валидацию всех экранов на наличие распространённых ошибок
"""

import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))


class TestScrollAreaImport(unittest.TestCase):
    """Тесты для проверки импорта ScrollArea."""

    def test_scroll_area_import_from_widgets(self):
        """Проверка, что ScrollArea импортируется из widgets модуля."""
        from parser_2gis.tui_pytermgui.widgets import ScrollArea
        self.assertIsNotNone(ScrollArea)
        self.assertEqual(ScrollArea.__name__, "ScrollArea")

    def test_scroll_area_is_subclass_of_scrollable_widget(self):
        """Проверка, что ScrollArea наследуется от ScrollableWidget."""
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets import ScrollArea

        self.assertTrue(issubclass(ScrollArea, ptg.ScrollableWidget))

    def test_scroll_area_instantiation(self):
        """Проверка создания экземпляра ScrollArea."""
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets import ScrollArea

        container = ptg.Container()
        scroll_area = ScrollArea(container, height=10)

        self.assertIsNotNone(scroll_area)
        self.assertEqual(len(scroll_area), 10)

    def test_scroll_area_get_lines(self):
        """Проверка метода get_lines у ScrollArea."""
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets import ScrollArea

        label = ptg.Label("Test line 1\nTest line 2\nTest line 3")
        container = ptg.Container(label)
        scroll_area = ScrollArea(container, height=5)

        lines = scroll_area.get_lines()
        self.assertIsInstance(lines, list)


class TestNoPtgScrollAreaUsage(unittest.TestCase):
    """Тесты для проверки отсутствия ptg.ScrollArea в коде."""

    def test_no_ptg_scrollarea_in_city_selector(self):
        """Проверка, что city_selector не использует ptg.ScrollArea."""
        from parser_2gis.tui_pytermgui.screens import city_selector
        import inspect

        source = inspect.getsource(city_selector)

        # Проверяем, что не используется ptg.ScrollArea
        self.assertNotIn("ptg.ScrollArea", source, "city_selector не должен использовать ptg.ScrollArea")
        self.assertNotIn("pytermgui.ScrollArea", source, "city_selector не должен использовать pytermgui.ScrollArea")

    def test_no_ptg_scrollarea_in_category_selector(self):
        """Проверка, что category_selector не использует ptg.ScrollArea."""
        from parser_2gis.tui_pytermgui.screens import category_selector
        import inspect

        source = inspect.getsource(category_selector)

        self.assertNotIn("ptg.ScrollArea", source, "category_selector не должен использовать ptg.ScrollArea")
        self.assertNotIn("pytermgui.ScrollArea", source, "category_selector не должен использовать pytermgui.ScrollArea")

    def test_no_ptg_scrollarea_in_about_screen(self):
        """Проверка, что about_screen не использует ptg.ScrollArea."""
        from parser_2gis.tui_pytermgui.screens import about_screen
        import inspect

        source = inspect.getsource(about_screen)

        self.assertNotIn("ptg.ScrollArea", source, "about_screen не должен использовать ptg.ScrollArea")
        self.assertNotIn("pytermgui.ScrollArea", source, "about_screen не должен использовать pytermgui.ScrollArea")

    def test_no_ptg_scrollarea_in_cache_viewer(self):
        """Проверка, что cache_viewer не использует ptg.ScrollArea."""
        from parser_2gis.tui_pytermgui.screens import cache_viewer
        import inspect

        source = inspect.getsource(cache_viewer)

        self.assertNotIn("ptg.ScrollArea", source, "cache_viewer не должен использовать ptg.ScrollArea")
        self.assertNotIn("pytermgui.ScrollArea", source, "cache_viewer не должен использовать pytermgui.ScrollArea")


class TestNoTextTagInStyles(unittest.TestCase):
    """Тесты для проверки отсутствия тега [text] в стилях и коде."""

    def test_no_text_style_in_default_styles(self):
        """Проверка, что в стилях по умолчанию нет value: 'text'."""
        from parser_2gis.tui_pytermgui.styles.default import get_default_styles

        styles = get_default_styles()

        # Проверяем, что нет стиля value: "text" для Label
        self.assertNotIn('value: "text"', styles, "Стили не должны содержать value: \"text\"")
        self.assertNotIn("value: 'text'", styles, "Стили не должны содержать value: 'text'")

    def test_no_text_tag_in_main_menu(self):
        """Проверка, что main_menu не использует тег [text]."""
        from parser_2gis.tui_pytermgui.screens import main_menu
        import inspect

        source = inspect.getsource(main_menu)

        # Проверяем, что нет тега [text] в строках
        lines = source.split('\n')
        for line in lines:
            if 'ptg.Label' in line or 'Label(' in line:
                self.assertNotIn('[text]', line, "main_menu не должен использовать тег [text] в Label")

    def test_no_text_tag_in_city_selector(self):
        """Проверка, что city_selector не использует тег [text]."""
        from parser_2gis.tui_pytermgui.screens import city_selector
        import inspect

        source = inspect.getsource(city_selector)

        lines = source.split('\n')
        for line in lines:
            if 'ptg.Label' in line or 'Label(' in line:
                self.assertNotIn('[text]', line, "city_selector не должен использовать тег [text] в Label")

    def test_no_text_tag_in_category_selector(self):
        """Проверка, что category_selector не использует тег [text]."""
        from parser_2gis.tui_pytermgui.screens import category_selector
        import inspect

        source = inspect.getsource(category_selector)

        lines = source.split('\n')
        for line in lines:
            if 'ptg.Label' in line or 'Label(' in line:
                self.assertNotIn('[text]', line, "category_selector не должен использовать тег [text] в Label")


class TestWindowWidthSpecification(unittest.TestCase):
    """Тесты для проверки указания ширины окон."""

    def _check_window_has_width(self, screen_class, screen_name):
        """Проверка, что окно имеет указанную ширину."""
        import inspect

        source = inspect.getsource(screen_class.create_window)

        # Проверяем, что width= указан в вызове Window
        self.assertIn("width=", source, f"{screen_name} должен иметь указанную ширину окна")

    def test_main_menu_window_width(self):
        """Проверка, что main_menu имеет ширину окна."""
        from parser_2gis.tui_pytermgui.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = MainMenuScreen(mock_app)
        self._check_window_has_width(screen, "MainMenuScreen")

    def test_city_selector_window_width(self):
        """Проверка, что city_selector имеет ширину окна."""
        from parser_2gis.tui_pytermgui.screens.city_selector import CitySelectorScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = CitySelectorScreen(mock_app)
        self._check_window_has_width(screen, "CitySelectorScreen")

    def test_category_selector_window_width(self):
        """Проверка, что category_selector имеет ширину окна."""
        from parser_2gis.tui_pytermgui.screens.category_selector import CategorySelectorScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = CategorySelectorScreen(mock_app)
        self._check_window_has_width(screen, "CategorySelectorScreen")

    def test_about_screen_window_width(self):
        """Проверка, что about_screen имеет ширину окна."""
        from parser_2gis.tui_pytermgui.screens.about_screen import AboutScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = AboutScreen(mock_app)
        self._check_window_has_width(screen, "AboutScreen")

    def test_cache_viewer_window_width(self):
        """Проверка, что cache_viewer имеет ширину окна."""
        from parser_2gis.tui_pytermgui.screens.cache_viewer import CacheViewerScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = CacheViewerScreen(mock_app)
        self._check_window_has_width(screen, "CacheViewerScreen")


class TestAllScreensImport(unittest.TestCase):
    """Тесты для проверки импорта всех экранов."""

    def test_all_screens_import_without_error(self):
        """Проверка, что все экраны импортируются без ошибок."""
        screens_to_test = [
            "main_menu",
            "city_selector",
            "category_selector",
            "browser_settings",
            "parser_settings",
            "output_settings",
            "cache_viewer",
            "about_screen",
            "parsing_screen",
        ]

        for screen_name in screens_to_test:
            try:
                __import__(
                    f"parser_2gis.tui_pytermgui.screens.{screen_name}",
                    fromlist=[""]
                )
            except ImportError as e:
                self.fail(f"Не удалось импортировать {screen_name}: {e}")
            except AttributeError as e:
                self.fail(f"AttributeError при импорте {screen_name}: {e}")

    def test_screens_use_custom_scroll_area(self):
        """Проверка, что экраны используют кастомный ScrollArea из widgets."""
        screens_to_test = [
            ("city_selector", "CitySelectorScreen"),
            ("category_selector", "CategorySelectorScreen"),
            ("about_screen", "AboutScreen"),
            ("cache_viewer", "CacheViewerScreen"),
        ]

        for screen_module_name, screen_class_name in screens_to_test:
            module = __import__(
                f"parser_2gis.tui_pytermgui.screens.{screen_module_name}",
                fromlist=[""]
            )

            # Проверяем, что в модуле есть импорт ScrollArea
            source = inspect.getsource(module)
            self.assertIn("from ..widgets import ScrollArea", source,
                         f"{screen_module_name} должен импортировать ScrollArea из widgets")


def run_tests():
    """Запустить все тесты."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Добавляем все тесты
    suite.addTests(loader.loadTestsFromTestCase(TestScrollAreaImport))
    suite.addTests(loader.loadTestsFromTestCase(TestNoPtgScrollAreaUsage))
    suite.addTests(loader.loadTestsFromTestCase(TestNoTextTagInStyles))
    suite.addTests(loader.loadTestsFromTestCase(TestWindowWidthSpecification))
    suite.addTests(loader.loadTestsFromTestCase(TestAllScreensImport))

    # Запускаем
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import inspect
    success = run_tests()
    sys.exit(0 if success else 1)
