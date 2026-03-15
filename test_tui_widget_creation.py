#!/usr/bin/env python3
"""
Тесты для выявления ошибок при создании TUI виджетов pytermgui.

Эти тесты проверяют:
1. Создание ParsingScreen и создание окна - проверка что нет ошибок при создании Label для прогресс-баров
2. Создание ProgressBar и вызов render() - проверка что render() возвращает корректный тип
3. Создание LogViewer и вызов render() - проверка что render() возвращает корректный тип
4. Проверка что _render_text() метод существует и возвращает строку у ProgressBar
5. Проверка что _render_text() метод существует и возвращает строку у LogViewer

Каждый тест:
- Независимый
- Имеет понятное название
- Проверяет конкретную проблему
- Использует pytest
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))


class TestParsingScreenCreateWindow:
    """Тесты для проверки создания окна ParsingScreen."""

    def test_parsing_screen_create_window_no_label_error(self):
        """
        Проверка что создание окна парсинга не вызывает TypeError с Label.

        Эта ошибка возникала когда render() возвращал Label, а не строку,
        и затем этот Label передавался в конструктор Label().
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        from parser_2gis.tui_pytermgui.screens.parsing_screen import ParsingScreen

        # Создаём мок приложения
        mock_app = MagicMock(spec=TUIApp)

        # Создаём экран парсинга
        screen = ParsingScreen(mock_app)

        # Не должно быть TypeError при создании окна
        try:
            window = screen.create_window()
            assert window is not None, "Окно должно быть создано"
        except TypeError as e:
            if "expected string or bytes-like object" in str(e):
                pytest.fail(f"TypeError с Label при создании окна: {e}")
            raise


class TestProgressBarRender:
    """Тесты для проверки рендеринга ProgressBar."""

    def test_progress_bar_render_returns_label_not_string(self):
        """
        Проверка что render() возвращает Label, а не строку.

        Это важно для корректной работы с pytermgui.
        """
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets.progress_bar import ProgressBar

        progress_bar = ProgressBar(label="Тест", total=100, completed=50)

        # Вызываем render()
        result = progress_bar.render()

        # Проверяем что это Label
        assert isinstance(result, ptg.Label), (
            f"render() должен возвращать Label, а не {type(result).__name__}"
        )

    def test_progress_bar_render_no_type_error(self):
        """
        Проверка что при использовании render() нет TypeError.

        Проверяем что Label созданный render() может быть использован корректно.
        """
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets.progress_bar import ProgressBar

        progress_bar = ProgressBar(label="Тест", total=100, completed=50)

        # Получаем Label из render()
        label = progress_bar.render()

        # Проверяем что Label имеет корректное значение
        assert hasattr(label, 'value'), "Label должен иметь атрибут value"
        assert label.value is not None, "Значение Label не должно быть None"

        # Проверяем что значение - строка
        assert isinstance(label.value, str), (
            f"Значение Label должно быть строкой, а не {type(label.value).__name__}"
        )


class TestLogViewerRender:
    """Тесты для проверки рендеринга LogViewer."""

    def test_log_viewer_render_returns_container(self):
        """
        Проверка что render() возвращает Container.

        LogViewer должен возвращать Container с логами.
        """
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        log_viewer = LogViewer(max_lines=100)
        log_viewer.add_log("Тестовое сообщение", "INFO")

        # Вызываем render()
        result = log_viewer.render()

        # Проверяем что это Container
        assert isinstance(result, ptg.Container), (
            f"render() должен возвращать Container, а не {type(result).__name__}"
        )

    def test_log_viewer_render_empty_logs(self):
        """
        Проверка что render() корректно работает с пустыми логами.

        При пустых логах должен возвращаться Container с сообщением.
        """
        import pytermgui as ptg
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        log_viewer = LogViewer(max_lines=100)

        # Вызываем render() без добавления логов
        result = log_viewer.render()

        # Проверяем что это Container
        assert isinstance(result, ptg.Container), (
            f"render() должен возвращать Container, а не {type(result).__name__}"
        )


class TestProgressBarRenderText:
    """Тесты для проверки метода _render_text() у ProgressBar."""

    def test_progress_bar_render_text_exists(self):
        """
        Проверка что метод _render_text() существует у ProgressBar.
        """
        from parser_2gis.tui_pytermgui.widgets.progress_bar import ProgressBar

        progress_bar = ProgressBar(label="Тест", total=100, completed=50)

        # Проверяем что метод существует
        assert hasattr(progress_bar, '_render_text'), (
            "ProgressBar должен иметь метод _render_text()"
        )
        assert callable(getattr(progress_bar, '_render_text')), (
            "_render_text() должен быть вызываемым"
        )

    def test_progress_bar_render_text_returns_string(self):
        """
        Проверка что _render_text() возвращает строку.

        Это критично для предотвращения TypeError при создании Label.
        """
        from parser_2gis.tui_pytermgui.widgets.progress_bar import ProgressBar

        progress_bar = ProgressBar(label="Тест", total=100, completed=50)

        # Вызываем _render_text()
        result = progress_bar._render_text()

        # Проверяем что это строка
        assert isinstance(result, str), (
            f"_render_text() должен возвращать строку, а не {type(result).__name__}"
        )

    def test_progress_bar_render_text_content(self):
        """
        Проверка что _render_text() возвращает корректное содержимое.

        Строка должна содержать метку, прогресс-бар и процент.
        """
        from parser_2gis.tui_pytermgui.widgets.progress_bar import ProgressBar

        progress_bar = ProgressBar(label="URL", total=100, completed=50)
        result = progress_bar._render_text()

        # Проверяем содержимое
        assert "URL" in result, "Строка должна содержать метку"
        assert "50.0%" in result, "Строка должна содержать процент"
        assert "(50/100)" in result, "Строка должна содержать прогресс"


class TestLogViewerRenderText:
    """Тесты для проверки метода _render_text() у LogViewer."""

    def test_log_viewer_render_text_exists(self):
        """
        Проверка что метод _render_text() существует у LogViewer.
        """
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        log_viewer = LogViewer(max_lines=100)

        # Проверяем что метод существует
        assert hasattr(log_viewer, '_render_text'), (
            "LogViewer должен иметь метод _render_text()"
        )
        assert callable(getattr(log_viewer, '_render_text')), (
            "_render_text() должен быть вызываемым"
        )

    def test_log_viewer_render_text_returns_string(self):
        """
        Проверка что _render_text() возвращает строку.

        Это критично для предотвращения TypeError при создании Label.
        """
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        log_viewer = LogViewer(max_lines=100)
        log_viewer.add_log("Тестовое сообщение", "INFO")

        # Вызываем _render_text()
        result = log_viewer._render_text()

        # Проверяем что это строка
        assert isinstance(result, str), (
            f"_render_text() должен возвращать строку, а не {type(result).__name__}"
        )

    def test_log_viewer_render_text_empty(self):
        """
        Проверка что _render_text() возвращает строку при пустых логах.
        """
        from parser_2gis.tui_pytermgui.widgets.log_viewer import LogViewer

        log_viewer = LogViewer(max_lines=100)

        # Вызываем _render_text() без добавления логов
        result = log_viewer._render_text()

        # Проверяем что это строка
        assert isinstance(result, str), (
            f"_render_text() должен возвращать строку даже при пустых логах"
        )
        assert "Нет логов" in result, "Строка должна содержать сообщение об отсутствии логов"


def run_tests():
    """Запустить все тесты через pytest."""
    sys.exit(pytest.main([__file__, "-v"]))


if __name__ == "__main__":
    run_tests()
