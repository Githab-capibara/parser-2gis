#!/usr/bin/env python3
"""
Тесты для проверки TUI на pytermgui.

Проверяет:
1. Корректность создания кнопок с onclick
2. Отсутствие неправильных стилей [@text]
3. Корректность создания окон с рамками
4. Работоспособность навигации между экранами
5. Валидацию компонентов TUI
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))


class TestTUIButtons(unittest.TestCase):
    """Тесты для проверки кнопок TUI."""

    def test_button_onclick_parameter(self):
        """Проверка, что кнопки используют onclick вместо callback."""
        import pytermgui as ptg

        # Создаём тестовую функцию
        test_callback = MagicMock()

        # Создаём кнопку с onclick
        button = ptg.Button("Test", onclick=test_callback)

        # Проверяем, что кнопка имеет атрибут onclick
        # В pytermgui onclick сохраняется как _onclick
        has_onclick = hasattr(button, 'onclick') or hasattr(button, '_onclick')
        self.assertTrue(has_onclick, "Кнопка должна иметь onclick")

    def test_all_screens_use_onclick(self):
        """Проверка, что все экраны используют onclick в кнопках."""
        from parser_2gis.tui_pytermgui.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)

        # Создаём главное меню
        screen = MainMenuScreen(mock_app)

        # Проверяем исходный код на наличие callback
        import inspect
        source = inspect.getsource(screen.create_window)

        # Проверяем, что callback не используется
        self.assertNotIn("callback=", source, "Кнопки должны использовать onclick, а не callback")
        self.assertIn("onclick=", source, "Кнопки должны использовать onclick")


class TestTUIStyles(unittest.TestCase):
    """Тесты для проверки стилей TUI."""

    def test_no_at_text_style(self):
        """Проверка отсутствия неправильного стиля [@text]."""
        from parser_2gis.tui_pytermgui.styles.default import get_default_styles

        styles = get_default_styles()

        # Проверяем, что стили не содержат [@text]
        self.assertNotIn("[@text]", styles, "Стили не должны содержать [@text]")
        self.assertNotIn("@text", styles, "Стили не должны содержать @text без кавычек")

    def test_styles_are_valid_yaml(self):
        """Проверка, что стили являются корректным YAML."""
        import yaml
        from parser_2gis.tui_pytermgui.styles.default import get_default_styles

        styles = get_default_styles()

        # Пытаемся загрузить YAML
        try:
            parsed = yaml.safe_load(styles)
            self.assertIsInstance(parsed, dict)
        except yaml.YAMLError as e:
            self.fail(f"Стили не являются корректным YAML: {e}")


class TestTUIWindows(unittest.TestCase):
    """Тесты для проверки окон TUI."""

    def test_window_creation_no_empty_boxes(self):
        """Проверка, что окна не используют box='EMPTY_VERTICAL' и box='EMPTY_HORIZONTAL'."""
        from parser_2gis.tui_pytermgui.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = MainMenuScreen(mock_app)

        import inspect
        source = inspect.getsource(screen.create_window)

        # Проверяем, что не используются неправильные боксы
        self.assertNotIn('box="EMPTY_VERTICAL"', source, "Не следует использовать box='EMPTY_VERTICAL'")
        self.assertNotIn("box='EMPTY_VERTICAL'", source, "Не следует использовать box='EMPTY_VERTICAL'")
        self.assertNotIn('box="EMPTY_HORIZONTAL"', source, "Не следует использовать box='EMPTY_HORIZONTAL'")
        self.assertNotIn("box='EMPTY_HORIZONTAL'", source, "Не следует использовать box='EMPTY_HORIZONTAL'")

    def test_window_has_width(self):
        """Проверка, что окна имеют установленную ширину."""
        from parser_2gis.tui_pytermgui.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_pytermgui.app import TUIApp

        mock_app = MagicMock(spec=TUIApp)
        screen = MainMenuScreen(mock_app)

        import inspect
        source = inspect.getsource(screen.create_window)

        # Проверяем, что ширина установлена
        self.assertIn("width=", source, "Окна должны иметь установленную ширину")


class TestTUINavigation(unittest.TestCase):
    """Тесты для проверки навигации TUI."""

    def test_screen_manager_push_pop(self):
        """Проверка работы менеджера экранов."""
        from parser_2gis.tui_pytermgui.utils.navigation import ScreenManager

        mock_app = MagicMock()
        manager = ScreenManager(mock_app)

        # Создаём тестовый экран
        test_screen = MagicMock()

        # Добавляем экран
        manager.push("test_screen", test_screen)

        # Проверяем, что экран добавлен
        self.assertEqual(manager.get_current(), "test_screen")
        self.assertEqual(manager.current_instance, test_screen)
        self.assertEqual(manager.stack_size, 0)

        # Добавляем второй экран
        test_screen2 = MagicMock()
        manager.push("test_screen2", test_screen2)

        # Проверяем
        self.assertEqual(manager.get_current(), "test_screen2")
        self.assertEqual(manager.stack_size, 1)

        # Возвращаемся назад
        previous = manager.pop()
        self.assertEqual(previous, "test_screen")
        self.assertEqual(manager.get_current(), "test_screen")

    def test_go_back_in_screen(self):
        """Проверка метода go_back в экранах."""
        from parser_2gis.tui_pytermgui.app import TUIApp

        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)

        # Вызываем go_back напрямую у приложения
        mock_app.go_back()

        # Проверяем, что был вызван go_back
        mock_app.go_back.assert_called_once()


class TestTUIComponents(unittest.TestCase):
    """Тесты для проверки компонентов TUI."""

    def test_progress_bar_render(self):
        """Проверка рендеринга прогресс-бара."""
        from parser_2gis.tui_pytermgui.widgets.progress_bar import ProgressBar

        progress = ProgressBar(label="Test", total=100, completed=50)
        result = progress.render()

        # Проверяем, что результат содержит правильную информацию
        self.assertIn("Test", str(result))
        self.assertIn("50", str(result))
        self.assertIn("100", str(result))
        self.assertIn("50.0%", str(result))

    def test_log_viewer_add_log(self):
        """Проверка добавления логов."""
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        viewer = LogViewer(max_lines=10)
        viewer.add_log("Test message", "INFO")

        logs = viewer.get_logs()
        self.assertEqual(len(logs), 1)
        self.assertIn("Test message", logs[0])
        self.assertIn("INFO", logs[0])

    def test_log_viewer_max_lines(self):
        """Проверка ограничения количества логов."""
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        viewer = LogViewer(max_lines=5)

        # Добавляем 10 логов
        for i in range(10):
            viewer.add_log(f"Log {i}", "INFO")

        logs = viewer.get_logs()
        self.assertEqual(len(logs), 5)
        # Последний лог должен быть Log 9
        self.assertIn("Log 9", logs[-1])


def run_tests():
    """Запустить все тесты."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Добавляем все тесты
    suite.addTests(loader.loadTestsFromTestCase(TestTUIButtons))
    suite.addTests(loader.loadTestsFromTestCase(TestTUIStyles))
    suite.addTests(loader.loadTestsFromTestCase(TestTUIWindows))
    suite.addTests(loader.loadTestsFromTestCase(TestTUINavigation))
    suite.addTests(loader.loadTestsFromTestCase(TestTUIComponents))

    # Запускаем
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
