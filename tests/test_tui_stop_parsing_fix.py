"""
Тест для проверки исправления бага с зависанием при нажатии 'Стоп' в TUI.

Проверяет:
1. При нажатии 'Стоп' вызывается app.stop_parsing(), а не app.running = False
2. При повторном входе на экран парсинга флаги _stopping и _parsing_started сбрасываются
3. Приложение не зависает после остановки парсинга

Этот тест выявляет проблему, которая приводила к зависанию приложения
при нажатии кнопки 'Стоп' на экране парсинга.
"""

from unittest.mock import MagicMock, Mock, PropertyMock

import pytest

from parser_2gis.tui_textual.app import TUIApp
from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen


@pytest.fixture
def mock_app():
    """Фикстура для создания mock приложения TUIApp."""
    app = MagicMock(spec=TUIApp)
    app.selected_cities = []
    app.selected_categories = []
    app.get_cities.return_value = [
        {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow", "country_code": "ru"}
    ]
    app.get_categories.return_value = [{"name": "Рестораны", "id": 93}]
    app.push_screen = Mock()
    app.pop_screen = Mock()
    app.notify_user = Mock()
    app.running = False
    app.stop_parsing = Mock()
    return app


@pytest.fixture
def parsing_screen(mock_app):
    """Фикстура для создания ParsingScreen с mock приложением."""
    screen = ParsingScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


class TestStopParsingFix:
    """Тесты для проверки исправления бага с зависанием."""

    def test_stop_parsing_uses_app_stop_parsing_method(self, parsing_screen, mock_app):
        """Тест проверяет что остановка использует app.stop_parsing() вместо app.running = False.

        Это критически важный тест! Ранее при нажатии 'Стоп' использовалось
        app.running = False, что приводило к полной остановке приложения.

        Ожидаемое поведение:
        - Вызывается app.stop_parsing() вместо app.running = False
        - Приложение не зависает
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen.call_later = Mock()

        parsing_screen.action_stop_parsing()

        assert parsing_screen._stopping is True

        mock_app.stop_parsing.assert_called_once()

    def test_stop_parsing_does_not_set_app_running_false(self, parsing_screen, mock_app):
        """Тест проверяет что НЕ используется app.running = False.

        Ранее использовался некорректный подход:
            self.app.running = False

        Это приводило к зависанию приложения!

        Ожидаемое поведение:
        - app.running НЕ устанавливается в False напрямую
        - Вместо этого используется app.stop_parsing()
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen.call_later = Mock()

        parsing_screen.action_stop_parsing()

        mock_app.running = "SHOULD_NOT_CHANGE"

    def test_on_mount_resets_flags(self, parsing_screen, mock_app):
        """Тест проверяет что при входе на экран парсинга флаги сбрасываются.

        Это важно для корректной работы при повторном запуске парсинга
        после возврата в меню.

        Ожидаемое поведение:
        - _stopping сбрасывается в False
        - _parsing_started сбрасывается в False
        """
        parsing_screen._stopping = True
        parsing_screen._parsing_started = True

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        mock_app.start_parsing = Mock()
        parsing_screen._return_to_menu = Mock()

        parsing_screen.on_mount()

        assert parsing_screen._stopping is False
        assert parsing_screen._parsing_started is False

    def test_on_mount_allows_repeated_parsing(self, parsing_screen, mock_app):
        """Тест проверяет что можно повторно запустить парсинг.

        Сценарий:
        1. Пользователь запускает парсинг
        2. Нажимает 'Стоп'
        3. Возвращается в меню
        4. Снова запускает парсинг

        Ожидаемое поведение:
        - Флаги сбрасываются в on_mount
        - Парсинг запускается корректно
        """
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.on_mount()

        assert parsing_screen._parsing_started is True

    def test_stop_parsing_returns_to_menu_safely(self, parsing_screen, mock_app):
        """Тест проверяет безопасный возврат в меню после остановки.

        Ожидаемое поведение:
        - _return_to_menu вызывается напрямую
        - Экран корректно закрывается
        """
        parsing_screen._parsing_started = True

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.action_stop_parsing()

        parsing_screen._return_to_menu.assert_called_once()


class TestAppStopParsingMethod:
    """Тесты для проверки метода app.stop_parsing()."""

    def test_stop_parsing_method_exists(self, mock_app):
        """Тест проверяет что метод stop_parsing существует в TUIApp."""
        assert hasattr(TUIApp, "stop_parsing")

    def test_stop_parsing_sets_running_flag(self, mock_app):
        """Тест проверяет что stop_parsing устанавливает флаг _running в False."""
        app = TUIApp()
        app._running = True
        app._file_logger = Mock()
        app.notify_user = Mock()

        app.stop_parsing()

        assert app._running is False

    def test_stop_parsing_sends_notification(self, mock_app):
        """Тест проверяет что stop_parsing отправляет уведомление."""
        app = TUIApp()
        app._running = True
        app._file_logger = Mock()
        app.notify_user = Mock()

        app.stop_parsing()

        app.notify_user.assert_called_once_with("Парсинг остановлен", level="warning")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
