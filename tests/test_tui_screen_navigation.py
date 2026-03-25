"""
Комплексные тесты навигации TUI экранов.

Проверяют корректность переходов между экранами,
вызов on_mount(), обработку ошибок и состояние приложения.
"""

from unittest.mock import MagicMock, PropertyMock, call

import pytest


class TestScreenNavigationChain:
    """Тесты цепочки навигации между экранами."""

    def test_main_menu_to_city_selector_navigation(self) -> None:
        """Проверка перехода из главного меню в выбор городов."""
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.selected_categories = []

        screen = MainMenuScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "select-cities"

        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.push_screen.assert_called_once_with("city_selector")

    def test_city_selector_to_category_selector_navigation(self) -> None:
        """Проверка перехода из выбора городов в выбор категорий."""
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        mock_app = MagicMock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []

        screen = CitySelectorScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "next"

        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.push_screen.assert_called_once_with("category_selector")
        assert mock_app.selected_cities == ["Москва"]

    def test_category_selector_to_parsing_navigation(self) -> None:
        """Проверка перехода из выбора категорий на экран парсинга."""
        from parser_2gis.tui_textual.screens.category_selector import (
            CategorySelectorScreen,
        )

        mock_app = MagicMock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        screen = CategorySelectorScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "next"

        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.push_screen.assert_called_once_with("parsing")

    def test_full_navigation_chain(self) -> None:
        """Проверка полной цепочки навигации."""
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.selected_categories = []
        mock_app.push_screen = MagicMock()

        screen = MainMenuScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "select-cities"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert mock_app.push_screen.call_count == 1
        mock_app.push_screen.assert_called_with("city_selector")


class TestParsingScreenOnMount:
    """Тесты вызова on_mount() у экрана парсинга."""

    def test_on_mount_called_with_valid_data(self) -> None:
        """Проверка вызова on_mount() с корректными данными."""
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        mock_app = MagicMock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]
        mock_app.get_cities.return_value = [{"name": "Москва", "code": "msk"}]
        mock_app.get_categories.return_value = [{"name": "Рестораны", "code": 1}]
        mock_app.start_parsing = MagicMock()

        screen = ParsingScreen()
        screen.app = mock_app

        screen.on_mount()

        mock_app.start_parsing.assert_called_once()

    def test_on_mount_called_without_cities(self) -> None:
        """Проверка вызова on_mount() без выбранных городов."""
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]
        mock_app.pop_screen = MagicMock()

        screen = ParsingScreen()
        screen.app = mock_app

        screen.on_mount()

        mock_app.pop_screen.assert_called()

    def test_on_mount_called_without_categories(self) -> None:
        """Проверка вызова on_mount() без выбранных категорий."""
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        mock_app = MagicMock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []
        mock_app.pop_screen = MagicMock()

        screen = ParsingScreen()
        screen.app = mock_app

        screen.on_mount()

        mock_app.pop_screen.assert_called()

    def test_on_mount_resets_stopping_flag(self) -> None:
        """Проверка сброса флага _stopping при новом вызове on_mount()."""
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        mock_app = MagicMock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]
        mock_app.get_cities.return_value = [{"name": "Москва", "code": "msk"}]
        mock_app.get_categories.return_value = [{"name": "Рестораны", "code": 1}]
        mock_app.start_parsing = MagicMock()

        screen = ParsingScreen()
        screen.app = mock_app
        screen._stopping = True

        screen.on_mount()

        assert screen._stopping is False


class TestSwitchScreenVsPushScreen:
    """Тесты проверки использования push_screen вместо switch_screen."""

    def test_city_selector_uses_push_screen_not_switch(self) -> None:
        """Проверка что city_selector использует push_screen а не switch_screen."""
        import inspect

        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        source = inspect.getsource(CitySelectorScreen.on_button_pressed)

        assert "push_screen" in source
        assert 'switch_screen("category_selector")' not in source

    def test_category_selector_uses_push_screen_not_switch(self) -> None:
        """Проверка что category_selector использует push_screen а не switch_screen."""
        import inspect

        from parser_2gis.tui_textual.screens.category_selector import (
            CategorySelectorScreen,
        )

        source = inspect.getsource(CategorySelectorScreen.on_button_pressed)

        assert "push_screen" in source
        assert 'switch_screen("parsing")' not in source

    def test_main_menu_uses_push_screen_for_parsing(self) -> None:
        """Проверка что main_menu использует push_screen для parsing."""
        import inspect

        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

        source = inspect.getsource(MainMenuScreen.on_button_pressed)

        assert "push_screen" in source
        assert 'switch_screen("parsing")' not in source


class TestErrorHandling:
    """Тесты обработки ошибок."""

    def test_main_menu_prevents_parsing_without_cities(self) -> None:
        """Проверка предотвращения парсинга без городов."""
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]
        mock_app.notify = MagicMock()

        screen = MainMenuScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "start-parsing"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.notify.assert_called()
        mock_app.push_screen.assert_not_called()

    def test_main_menu_prevents_parsing_without_categories(self) -> None:
        """Проверка предотвращения парсинга без категорий."""
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

        mock_app = MagicMock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []
        mock_app.notify = MagicMock()

        screen = MainMenuScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "start-parsing"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.notify.assert_called()
        mock_app.push_screen.assert_not_called()

    def test_category_selector_prevents_parsing_without_cities(self) -> None:
        """Проверка предотвращения парсинга без городов в category_selector."""
        from parser_2gis.tui_textual.screens.category_selector import (
            CategorySelectorScreen,
        )

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]
        mock_app.notify = MagicMock()

        screen = CategorySelectorScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "next"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.notify.assert_called()
        mock_app.push_screen.assert_not_called()


class TestStatePersistence:
    """Тесты сохранения состояния между экранами."""

    def test_selected_cities_persists_across_screens(self) -> None:
        """Проверка сохранения selected_cities между экранами."""
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.get_cities.return_value = [
            {"name": "Москва", "code": "msk"},
            {"name": "СПб", "code": "spb"},
        ]

        screen = CitySelectorScreen()
        screen.app = mock_app
        screen._cities = mock_app.get_cities.return_value
        screen._selected_indices = {0}

        mock_button = MagicMock()
        mock_button.id = "next"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert mock_app.selected_cities == ["Москва"]

    def test_selected_categories_persists_across_screens(self) -> None:
        """Проверка сохранения selected_categories между экранами."""
        from parser_2gis.tui_textual.screens.category_selector import (
            CategorySelectorScreen,
        )

        mock_app = MagicMock()
        mock_app.selected_categories = []

        screen = CategorySelectorScreen()
        screen.app = mock_app
        screen._categories = [{"name": "Рестораны", "code": 1, "original_index": 0}]
        screen._filtered_categories = screen._categories
        screen._selected_indices = {0}

        mock_button = MagicMock()
        mock_button.id = "next"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen._load_categories = MagicMock()
        screen.on_button_pressed(mock_event)

        assert mock_app.selected_categories == ["Рестораны"]


class TestRapidNavigation:
    """Тесты быстрой навигации."""

    def test_rapid_stop_button_presses(self) -> None:
        """Проверка защиты от race conditions при быстрых нажатиях Стоп."""
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        mock_app = MagicMock()
        mock_app.stop_parsing = MagicMock()

        screen = ParsingScreen()
        screen.app = mock_app
        screen._parsing_started = True
        screen._stopping = False

        mock_button = MagicMock()
        mock_button.id = "stop"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.on_button_pressed(mock_event)

        mock_app.stop_parsing.assert_called_once()

    def test_home_button_during_parsing(self) -> None:
        """Проверка нажатия кнопки Домой во время парсинга."""
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        mock_app = MagicMock()
        mock_app.stop_parsing = MagicMock()
        mock_app.pop_screen = MagicMock()

        screen = ParsingScreen()
        screen.app = mock_app
        screen._parsing_started = True
        screen._stopping = False

        mock_button = MagicMock()
        mock_button.id = "home"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.stop_parsing.assert_called_once()
        mock_app.pop_screen.assert_called()


class TestNavigationIntegration:
    """Интеграционные тесты навигации."""

    def test_complete_parsing_workflow(self) -> None:
        """Тест полного рабочего процесса парсинга."""
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen
        from parser_2gis.tui_textual.screens.category_selector import (
            CategorySelectorScreen,
        )

        mock_app = MagicMock()
        mock_app.selected_cities = []
        mock_app.selected_categories = []
        mock_app.push_screen = MagicMock()

        main_menu = MainMenuScreen()
        main_menu.app = mock_app

        city_button = MagicMock()
        city_button.id = "select-cities"
        city_event = MagicMock()
        city_event.button = city_button

        main_menu.on_button_pressed(city_event)

        mock_app.push_screen.assert_called_with("city_selector")

        mock_app.selected_cities = ["Москва"]
        city_screen = CitySelectorScreen()
        city_screen.app = mock_app

        next_button = MagicMock()
        next_button.id = "next"
        next_event = MagicMock()
        next_event.button = next_button

        city_screen.on_button_pressed(next_event)

        assert mock_app.selected_cities == ["Москва"]

        mock_app.selected_categories = ["Рестораны"]
        category_screen = CategorySelectorScreen()
        category_screen.app = mock_app

        category_screen.on_button_pressed(next_event)

        assert mock_app.selected_categories == ["Рестораны"]

    def test_navigation_with_back_button(self) -> None:
        """Тест навигации с использованием кнопки Назад."""
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        mock_app = MagicMock()
        mock_app.pop_screen = MagicMock()

        screen = CitySelectorScreen()
        screen.app = mock_app

        mock_button = MagicMock()
        mock_button.id = "back"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_app.pop_screen.assert_called_once()
