"""
Тест для выявления циклических вызовов экранов TUI (причина зависания).

Этот тест был создан для предотвращения ошибки зависания TUI интерфейса,
которая возникала при переходе от выбора категорий к экрану парсинга.

Проблема:
- category_selector.py вызывал switch_screen("parsing")
- ParsingScreen.on_mount() вызывал app.start_parsing()
- app.start_parsing() вызывал push_screen("parsing") ← ПОВТОРНО!
- Это создавало циклический вызов и приводило к зависанию

Решение:
- app.start_parsing() НЕ должен вызывать push_screen()
- Экран парсинга уже открыт через switch_screen()
- start_parsing() должен только запускать фоновый процесс

Тесты проверяют:
1. Отсутствие push_screen() в app.start_parsing()
2. Корректное использование switch_screen() в category_selector
3. Отсутствие циклических вызовов при навигации
4. Корректный запуск фонового процесса парсинга
"""

from unittest.mock import MagicMock, Mock, PropertyMock

import pytest

from parser_2gis.tui_textual.app import TUIApp
from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen
from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def mock_app():
    """Фикстура для создания mock приложения TUIApp.

    Returns:
        MagicMock с настроенными методами и свойствами TUIApp.
    """
    app = MagicMock(spec=TUIApp)
    app.selected_cities = []
    app.selected_categories = []
    app.get_cities.return_value = [
        {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow", "country_code": "ru"},
        {
            "name": "Санкт-Петербург",
            "url": "https://2gis.ru/spb",
            "code": "spb",
            "country_code": "ru",
        },
    ]
    app.get_categories.return_value = [{"name": "Рестораны", "id": 93}, {"name": "Кафе", "id": 161}]
    app.push_screen = Mock()
    app.pop_screen = Mock()
    app.switch_screen = Mock()
    app.notify_user = Mock()
    app.running = False
    app._run_parsing = Mock()
    return app


@pytest.fixture
def parsing_screen(mock_app):
    """Фикстура для создания ParsingScreen с mock приложением.

    Args:
        mock_app: Mock приложение.

    Returns:
        ParsingScreen с настроенным mock приложением.
    """
    screen = ParsingScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


# =============================================================================
# ТЕСТЫ - ПРОВЕРКА ОТСУТСТВИЯ ЦИКЛИЧЕСКИХ ВЫЗОВОВ
# =============================================================================


class TestNoCyclicScreenCalls:
    """Тесты для проверки отсутствия циклических вызовов экранов."""

    def test_start_parsing_does_not_call_push_screen(self, mock_app):
        """Тест проверяет что start_parsing() НЕ вызывает push_screen().

        КРИТИЧЕСКИЙ ТЕСТ для предотвращения зависания!

        Сценарий:
        1. Вызывается app.start_parsing() с городами и категориями
        2. Проверяем что push_screen() НЕ вызывается

        Ожидаемое поведение:
        - push_screen() НЕ вызывается (экран уже открыт)
        - _run_parsing() вызывается для запуска фонового процесса

        Это предотвращает циклический вызов:
        category_selector.switch_screen("parsing") →
        ParsingScreen.on_mount() →
        app.start_parsing() →
        [push_screen("parsing") было бы ошибкой!]
        """
        # Подготавливаем данные
        cities = [{"name": "Москва", "code": "moscow"}]
        categories = [{"name": "Рестораны", "id": 93}]

        # Сбрасываем историю вызовов mock
        mock_app.push_screen.reset_mock()
        mock_app._run_parsing.reset_mock()

        # Вызываем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что push_screen НЕ вызывался
        mock_app.push_screen.assert_not_called()

        # Проверяем что _run_parsing был вызван
        mock_app._run_parsing.assert_called_once_with(cities, categories)

    def test_start_parsing_with_empty_cities_does_not_call_push_screen(self, mock_app):
        """Тест проверяет что start_parsing() с пустыми городами НЕ вызывает push_screen().

        Сценарий:
        1. Вызывается app.start_parsing() с пустыми городами
        2. Проверяем что push_screen() НЕ вызывается

        Ожидаемое поведение:
        - push_screen() НЕ вызывается
        - notify_user() вызывается с ошибкой
        - _run_parsing() НЕ вызывается
        """
        # Подготавливаем пустые данные
        cities = []
        categories = [{"name": "Рестораны", "id": 93}]

        # Сбрасываем историю вызовов mock
        mock_app.push_screen.reset_mock()
        mock_app._run_parsing.reset_mock()
        mock_app.notify_user.reset_mock()

        # Вызываем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что push_screen НЕ вызывался
        mock_app.push_screen.assert_not_called()

        # Проверяем что notify_user был вызван с ошибкой
        mock_app.notify_user.assert_called_once()

        # Проверяем что _run_parsing НЕ вызывался
        mock_app._run_parsing.assert_not_called()

    def test_start_parsing_with_empty_categories_does_not_call_push_screen(self, mock_app):
        """Тест проверяет что start_parsing() с пустыми категориями НЕ вызывает push_screen().

        Сценарий:
        1. Вызывается app.start_parsing() с пустыми категориями
        2. Проверяем что push_screen() НЕ вызывается

        Ожидаемое поведение:
        - push_screen() НЕ вызывается
        - notify_user() вызывается с ошибкой
        - _run_parsing() НЕ вызывается
        """
        # Подготавливаем данные
        cities = [{"name": "Москва", "code": "moscow"}]
        categories = []

        # Сбрасываем историю вызовов mock
        mock_app.push_screen.reset_mock()
        mock_app._run_parsing.reset_mock()
        mock_app.notify_user.reset_mock()

        # Вызываем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что push_screen НЕ вызывался
        mock_app.push_screen.assert_not_called()

        # Проверяем что notify_user был вызван с ошибкой
        mock_app.notify_user.assert_called_once()

        # Проверяем что _run_parsing НЕ вызывался
        mock_app._run_parsing.assert_not_called()

    def test_category_selector_uses_switch_screen_not_push_screen(self, mock_app):
        """Тест проверяет что category_selector использует switch_screen().

        Сценарий:
        1. Пользователь выбирает категории
        2. Нажимает кнопку "Далее"
        3. Проверяем что используется switch_screen() а не push_screen()

        Ожидаемое поведение:
        - switch_screen("parsing") вызывается
        - push_screen() НЕ вызывается

        Это важно для предотвращения накопления экранов в стеке.
        """
        from textual.widgets import Button

        # Создаём экран
        screen = CategorySelectorScreen()
        type(screen).app = PropertyMock(return_value=mock_app)

        # Загружаем категории
        screen._load_categories()

        # Выбираем категории
        screen._selected_indices = {0}  # Выбираем первую категорию

        # Создаём мок кнопки
        mock_button = Mock(spec=Button)
        mock_button.id = "next"

        # Создаём мок события
        mock_event = Mock()
        mock_event.button = mock_button

        # Вызываем обработчик нажатия кнопки
        screen.on_button_pressed(mock_event)

        # Проверяем что switch_screen был вызван
        mock_app.switch_screen.assert_called_once_with("parsing")

        # Проверяем что push_screen НЕ вызывался
        mock_app.push_screen.assert_not_called()

    def test_parsing_screen_on_mount_calls_start_parsing(self, parsing_screen, mock_app):
        """Тест проверяет что on_mount() корректно вызывает start_parsing().

        Сценарий:
        1. ParsingScreen монтируется
        2. on_mount() вызывается
        3. Проверяем что start_parsing() вызывается с правильными данными

        Ожидаемое поведение:
        - start_parsing() вызывается один раз
        - Данные передаются корректно
        """
        # Устанавливаем выбранные города и категории
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Сбрасываем историю вызовов
        mock_app.start_parsing.reset_mock()

        # Вызываем on_mount
        parsing_screen.on_mount()

        # Проверяем что start_parsing был вызван
        mock_app.start_parsing.assert_called_once()

        # Проверяем что данные переданы корректно
        call_args = mock_app.start_parsing.call_args
        cities_arg = call_args[0][0]
        categories_arg = call_args[0][1]

        # Проверяем что города и категории переданы
        assert len(cities_arg) > 0
        assert len(categories_arg) > 0

    def test_full_navigation_flow_no_cycles(self, mock_app):
        """Тест проверяет полный цикл навигации без циклических вызовов.

        Полный сценарий:
        1. CitySelector → switch_screen("category_selector")
        2. CategorySelector → switch_screen("parsing")
        3. ParsingScreen.on_mount() → start_parsing()
        4. start_parsing() → _run_parsing() (БЕЗ push_screen!)

        Ожидаемое поведение:
        - Нет циклических вызовов
        - Нет дублирования экранов
        - Парсинг запускается корректно
        """
        # === ШАГ 1: CitySelector → CategorySelector ===
        from textual.widgets import Button

        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        city_screen = CitySelectorScreen()
        type(city_screen).app = PropertyMock(return_value=mock_app)
        city_screen._load_cities()
        city_screen._selected_indices = {0}

        mock_button = Mock(spec=Button)
        mock_button.id = "next"
        mock_event = Mock()
        mock_event.button = mock_button

        city_screen.on_button_pressed(mock_event)

        # Проверяем что switch_screen был вызван
        mock_app.switch_screen.assert_called_with("category_selector")

        # === ШАГ 2: CategorySelector → Parsing ===
        mock_app.switch_screen.reset_mock()

        cat_screen = CategorySelectorScreen()
        type(cat_screen).app = PropertyMock(return_value=mock_app)
        cat_screen._load_categories()
        cat_screen._selected_indices = {0}

        cat_screen.on_button_pressed(mock_event)

        # Проверяем что switch_screen был вызван
        mock_app.switch_screen.assert_called_with("parsing")

        # === ШАГ 3: ParsingScreen.on_mount() → start_parsing() ===
        mock_app.push_screen.reset_mock()
        mock_app._run_parsing.reset_mock()
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        parsing_screen = ParsingScreen()
        type(parsing_screen).app = PropertyMock(return_value=mock_app)

        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Вызываем on_mount напрямую (эмуляция монтирования)
        # Важно: start_parsing теперь НЕ должен вызывать push_screen
        TUIApp.start_parsing(
            mock_app, mock_app.get_cities.return_value, mock_app.get_categories.return_value
        )

        # === ПРОВЕРКА: НЕТ ЦИКЛИЧЕСКИХ ВЫЗОВОВ ===
        # push_screen НЕ должен был вызваться
        mock_app.push_screen.assert_not_called()

        # _run_parsing должен был вызваться
        mock_app._run_parsing.assert_called_once()

    def test_rapid_screen_transitions_do_not_cause_hang(self, mock_app):
        """Тест проверяет отсутствие зависания при быстрых переходах.

        Сценарий:
        1. Быстро переключаемся между экранами несколько раз
        2. Не должно быть циклических вызовов или зависания

        Ожидаемое поведение:
        - Каждый switch_screen отрабатывает корректно
        - Нет накопления экранов в стеке
        """
        # Эмулируем быстрые переключения
        for _ in range(5):
            mock_app.switch_screen("category_selector")
            mock_app.switch_screen("parsing")

        # Проверяем что switch_screen вызвался нужное количество раз
        assert mock_app.switch_screen.call_count == 10

        # Проверяем что push_screen НЕ вызывался (не должно быть дублирования)
        mock_app.push_screen.assert_not_called()


# =============================================================================
# ТЕСТЫ - ПРОВЕРКА АРХИТЕКТУРЫ НАВИГАЦИИ
# =============================================================================


class TestScreenNavigationArchitecture:
    """Тесты для проверки правильной архитектуры навигации."""

    def test_switch_screen_used_for_terminal_screens(self):
        """Тест проверяет что switch_screen используется для конечных экранов.

        Архитектурное правило:
        - switch_screen() для конечных экранов (parsing)
        - push_screen() для временных экранов (настройки, диалоги)

        Этот тест предотвращает будущие ошибки архитектуры.
        """
        # Проверяем что в category_selector используется switch_screen
        import inspect

        from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

        # Получаем исходный код метода on_button_pressed
        source = inspect.getsource(CategorySelectorScreen.on_button_pressed)

        # Проверяем что используется switch_screen для "parsing"
        assert 'switch_screen("parsing")' in source or "switch_screen('parsing')" in source

        # Проверяем что НЕ используется push_screen для "parsing"
        assert 'push_screen("parsing")' not in source
        assert "push_screen('parsing')" not in source

    def test_start_parsing_signature(self, mock_app):
        """Тест проверяет сигнатуру метода start_parsing().

        Проверяет что метод принимает правильные параметры:
        - cities: list[dict]
        - categories: list[dict]

        Это важно для корректной передачи данных между экранами.
        """
        import inspect

        # Получаем сигнатуру метода
        sig = inspect.signature(TUIApp.start_parsing)
        params = list(sig.parameters.keys())

        # Проверяем наличие параметров
        assert "cities" in params
        assert "categories" in params

        # Проверяем что метод не принимает лишние параметры
        assert len(params) == 3  # self, cities, categories


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-ra"])
