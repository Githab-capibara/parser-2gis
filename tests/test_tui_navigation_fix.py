"""
Тесты для проверки навигации между экранами TUI.

Проверяет:
1. Корректный возврат в меню при нажатии "Стоп" без запущенного парсинга
2. Корректный возврат в меню при ошибке "не выбраны города/категории"
3. Корректная работа кнопки "Домой" на экране парсинга
4. Корректное переключение между экранами через switch_screen
5. Отсутствие зависаний при быстрой навигации между экранами

Этот тест выявляет проблемы, которые приводили к зависанию приложения
при навигации между экранами TUI.
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
    app.switch_screen = Mock()
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


class TestTUINavigationFix:
    """Тесты для проверки навигации между экранами TUI."""

    def test_stop_parsing_without_started_parsing_returns_to_menu(self, parsing_screen, mock_app):
        """Тест проверяет возврат в меню при нажатии "Стоп" без запущенного парсинга.

        Сценарий:
        1. Пользователь открывает экран парсинга без выбранных городов/категорий
        2. Нажимает "Стоп"
        3. Должен вернуться в меню без зависания

        Ожидаемое поведение:
        - _return_to_menu вызывается напрямую
        - _stopping не устанавливается в True
        - Приложение не зависает
        """
        parsing_screen._parsing_started = False
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.action_stop_parsing()

        parsing_screen._return_to_menu.assert_called_once()
        assert parsing_screen._stopping is False
        mock_app.stop_parsing.assert_not_called()

    def test_stop_parsing_with_started_parsing_stops_and_returns(self, parsing_screen, mock_app):
        """Тест проверяет остановку парсинга и возврат в меню.

        Сценарий:
        1. Парсинг запущен
        2. Пользователь нажимает "Стоп"
        3. Парсинг останавливается и происходит возврат в меню

        Ожидаемое поведение:
        - _stopping устанавливается в True
        - app.stop_parsing вызывается
        - _return_to_menu вызывается
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.action_stop_parsing()

        assert parsing_screen._stopping is True
        mock_app.stop_parsing.assert_called_once()
        parsing_screen._return_to_menu.assert_called_once()

    def test_home_button_returns_to_menu_without_parsing(self, parsing_screen, mock_app):
        """Тест проверяет работу кнопки "Домой" без запущенного парсинга.

        Сценарий:
        1. Парсинг не запущен
        2. Пользователь нажимает "Домой"
        3. Должен вернуться в меню

        Ожидаемое поведение:
        - _return_to_menu вызывается
        - Приложение не зависает
        """
        parsing_screen._parsing_started = False
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        # Эмулируем нажатие кнопки "Домой"
        mock_button = Mock()
        mock_button.id = "home"
        event = Mock()
        event.button = mock_button

        parsing_screen.on_button_pressed(event)

        parsing_screen._return_to_menu.assert_called_once()

    def test_home_button_stops_parsing_and_returns(self, parsing_screen, mock_app):
        """Тест проверяет работу кнопки "Домой" с запущенным парсингом.

        Сценарий:
        1. Парсинг запущен
        2. Пользователь нажимает "Домой"
        3. Парсинг останавливается и происходит возврат в меню

        Ожидаемое поведение:
        - _stopping устанавливается в True
        - app.stop_parsing вызывается
        - _return_to_menu вызывается
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        # Эмулируем нажатие кнопки "Домой"
        mock_button = Mock()
        mock_button.id = "home"
        event = Mock()
        event.button = mock_button

        parsing_screen.on_button_pressed(event)

        assert parsing_screen._stopping is True
        mock_app.stop_parsing.assert_called_once()
        parsing_screen._return_to_menu.assert_called_once()

    def test_on_mount_with_no_cities_returns_to_menu(self, parsing_screen, mock_app):
        """Тест проверяет возврат в меню при отсутствии выбранных городов.

        Сценарий:
        1. selected_cities пустой
        2. on_mount вызывается
        3. Должен вернуться в меню с сообщением об ошибке

        Ожидаемое поведение:
        - _return_to_menu вызывается
        - _parsing_started остаётся False
        """
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.on_mount()

        parsing_screen._return_to_menu.assert_called_once()
        assert parsing_screen._parsing_started is False

    def test_on_mount_with_no_categories_returns_to_menu(self, parsing_screen, mock_app):
        """Тест проверяет возврат в меню при отсутствии выбранных категорий.

        Сценарий:
        1. selected_categories пустой
        2. on_mount вызывается
        3. Должен вернуться в меню с сообщением об ошибке

        Ожидаемое поведение:
        - _return_to_menu вызывается
        - _parsing_started остаётся False
        """
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.on_mount()

        parsing_screen._return_to_menu.assert_called_once()
        assert parsing_screen._parsing_started is False

    def test_on_mount_with_valid_data_starts_parsing(self, parsing_screen, mock_app):
        """Тест проверяет запуск парсинга при наличии выбранных городов и категорий.

        Сценарий:
        1. selected_cities и selected_categories не пустые
        2. on_mount вызывается
        3. Парсинг запускается

        Ожидаемое поведение:
        - _parsing_started устанавливается в True
        - _return_to_menu не вызывается
        """
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        parsing_screen.on_mount()

        assert parsing_screen._parsing_started is True
        parsing_screen._return_to_menu.assert_not_called()

    def test_rapid_navigation_does_not_cause_hang(self, parsing_screen, mock_app):
        """Тест проверяет отсутствие зависания при быстрой навигации.

        Сценарий:
        1. Быстро нажимаем "Стоп" несколько раз
        2. Не должно быть зависания

        Ожидаемое поведение:
        - _return_to_menu вызывается только один раз
        - Защита от повторного вызова работает
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)
        parsing_screen._return_to_menu = Mock()

        # Быстро нажимаем "Стоп" несколько раз
        parsing_screen.action_stop_parsing()
        parsing_screen.action_stop_parsing()
        parsing_screen.action_stop_parsing()

        # _return_to_menu должен быть вызван только один раз
        parsing_screen._return_to_menu.assert_called_once()
        assert parsing_screen._stopping is True

    def test_return_to_menu_with_exception_handling(self, parsing_screen, mock_app):
        """Тест проверяет обработку исключений при возврате в меню.

        Сценарий:
        1. При возврате в меню возникает исключение
        2. Исключение должно быть обработано

        Ожидаемое поведение:
        - Исключение не прерывает работу приложения
        - Приложение продолжает работу
        """
        parsing_screen._parsing_started = False
        parsing_screen._stopping = False

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Эмулируем исключение при вызове pop_screen
        mock_app.pop_screen.side_effect = Exception("Test exception")

        # Не должно быть исключения
        parsing_screen._return_to_menu()

        # Приложение продолжает работу
        assert True


class TestSwitchScreenNavigation:
    """Тесты для проверки навигации через switch_screen."""

    def test_city_selector_uses_switch_screen(self):
        """Тест проверяет что city_selector использует switch_screen.

        Сценарий:
        1. Пользователь выбирает города
        2. Нажимает "Далее"
        3. Должен переключиться на category_selector через switch_screen

        Ожидаемое поведение:
        - switch_screen вызывается вместо push_screen
        - Навигация работает корректно
        """
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        mock_app = MagicMock()
        mock_app.get_cities.return_value = [
            {"name": "Москва", "code": "moscow", "country_code": "ru"}
        ]
        mock_app.selected_cities = []
        mock_app.switch_screen = Mock()

        screen = CitySelectorScreen()
        type(screen).app = PropertyMock(return_value=mock_app)

        # Эмулируем выбор города
        screen._cities = mock_app.get_cities.return_value
        screen._selected_indices = {0}

        # Эмулируем нажатие "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        screen.on_button_pressed(event)

        # Проверяем что switch_screen был вызван
        mock_app.switch_screen.assert_called_once_with("category_selector")

    def test_category_selector_uses_switch_screen(self):
        """Тест проверяет что category_selector использует switch_screen.

        Сценарий:
        1. Пользователь выбирает категории
        2. Нажимает "Далее"
        3. Должен переключиться на parsing через switch_screen

        Ожидаемое поведение:
        - switch_screen вызывается вместо push_screen
        - Навигация работает корректно
        """
        from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

        mock_app = MagicMock()
        mock_app.get_categories.return_value = [{"name": "Рестораны", "id": 93}]
        mock_app.selected_categories = []
        mock_app.switch_screen = Mock()

        screen = CategorySelectorScreen()
        type(screen).app = PropertyMock(return_value=mock_app)

        # Эмулируем выбор категории
        screen._categories = mock_app.get_categories.return_value
        screen._categories[0]["original_index"] = 0
        screen._selected_indices = {0}

        # Эмулируем нажатие "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        screen.on_button_pressed(event)

        # Проверяем что switch_screen был вызван
        mock_app.switch_screen.assert_called_once_with("parsing")


class TestStateConsistency:
    """Тесты для проверки согласованности состояния между экранами."""

    def test_selected_cities_persists_across_screens(self):
        """Тест проверяет сохранение выбранных городов между экранами.

        Сценарий:
        1. Пользователь выбирает города в city_selector
        2. Переходит на category_selector
        3. selected_cities должен сохраниться

        Ожидаемое поведение:
        - selected_cities сохраняется в состоянии приложения
        - Доступен на всех экранах
        """
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        mock_app = MagicMock()
        mock_app.get_cities.return_value = [
            {"name": "Москва", "code": "moscow", "country_code": "ru"},
            {"name": "Омск", "code": "omsk", "country_code": "ru"},
        ]
        mock_app.selected_cities = []
        mock_app.switch_screen = Mock()

        screen = CitySelectorScreen()
        type(screen).app = PropertyMock(return_value=mock_app)

        # Эмулируем выбор городов
        screen._cities = mock_app.get_cities.return_value
        screen._selected_indices = {0, 1}

        # Эмулируем нажатие "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        screen.on_button_pressed(event)

        # Проверяем что selected_cities был обновлён
        assert mock_app.selected_cities == ["Москва", "Омск"]

    def test_selected_categories_persists_across_screens(self):
        """Тест проверяет сохранение выбранных категорий между экранами.

        Сценарий:
        1. Пользователь выбирает категории в category_selector
        2. Переходит на parsing_screen
        3. selected_categories должен сохраниться

        Ожидаемое поведение:
        - selected_categories сохраняется в состоянии приложения
        - Доступен на всех экранах
        """
        from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

        mock_app = MagicMock()
        mock_app.get_categories.return_value = [
            {"name": "Рестораны", "id": 93},
            {"name": "Кафе", "id": 161},
        ]
        mock_app.selected_categories = []
        mock_app.switch_screen = Mock()

        screen = CategorySelectorScreen()
        type(screen).app = PropertyMock(return_value=mock_app)

        # Эмулируем выбор категорий
        screen._categories = mock_app.get_categories.return_value
        screen._categories[0]["original_index"] = 0
        screen._categories[1]["original_index"] = 1
        screen._selected_indices = {0, 1}

        # Эмулируем нажатие "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        screen.on_button_pressed(event)

        # Проверяем что selected_categories был обновлён
        assert mock_app.selected_categories == ["Рестораны", "Кафе"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
