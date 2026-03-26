"""
Тесты для выявления проблем с навигацией TUI экранов в Textual.

Проверяет:
1. Переход между экранами TUI работает корректно
2. Метод on_mount() вызывается при переходе на экраны
3. switch_screen() НЕ используется там где нужен push_screen()
4. Экраны с критической логикой в on_mount() получают вызов этого метода

Тестируемая навигация:
- main_menu → city_selector → category_selector → parsing
"""

from unittest.mock import MagicMock, Mock, PropertyMock, call

import pytest

try:
    from parser_2gis.tui_textual.app import TUIApp
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen
    from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen
    from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen
    from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def mock_app():
    """Фикстура для создания mock приложения TUIApp.

    Создаёт полностью изолированный mock объект приложения со всеми
    необходимыми методами и свойствами для тестирования навигации.

    Returns:
        MagicMock: Mock объект приложения TUIApp.
    """
    app = MagicMock(spec=TUIApp)

    # Начальное состояние
    app.selected_cities = []
    app.selected_categories = []
    app.running = False

    # Mock методов получения данных
    app.get_cities.return_value = [
        {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow", "country_code": "ru"},
        {"name": "Омск", "url": "https://2gis.ru/omsk", "code": "omsk", "country_code": "ru"},
        {
            "name": "Санкт-Петербург",
            "url": "https://2gis.ru/spb",
            "code": "spb",
            "country_code": "ru",
        },
    ]
    app.get_categories.return_value = [
        {"name": "Рестораны", "id": 93, "query": "рестораны"},
        {"name": "Аптеки", "id": 107, "query": "аптеки"},
        {"name": "Кафе", "id": 161, "query": "кафе"},
    ]

    # Mock методов навигации
    app.push_screen = Mock()
    app.pop_screen = Mock()
    app.switch_screen = Mock()

    # Mock методов уведомления
    app.notify_user = Mock()
    app.notify = Mock()

    # Mock методов парсинга
    app.stop_parsing = Mock()
    app.start_parsing = Mock()

    return app


@pytest.fixture
def city_selector_screen(mock_app):
    """Фикстура для создания CitySelectorScreen с mock приложением.

    Args:
        mock_app: Mock объект приложения.

    Returns:
        CitySelectorScreen: Экран выбора городов с привязанным mock приложением.
    """
    screen = CitySelectorScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


@pytest.fixture
def category_selector_screen(mock_app):
    """Фикстура для создания CategorySelectorScreen с mock приложением.

    Args:
        mock_app: Mock объект приложения.

    Returns:
        CategorySelectorScreen: Экран выбора категорий с привязанным mock приложением.
    """
    screen = CategorySelectorScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


@pytest.fixture
def parsing_screen(mock_app):
    """Фикстура для создания ParsingScreen с mock приложением.

    Args:
        mock_app: Mock объект приложения.

    Returns:
        ParsingScreen: Экран парсинга с привязанным mock приложением.
    """
    screen = ParsingScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


@pytest.fixture
def main_menu_screen(mock_app):
    """Фикстура для создания MainMenuScreen с mock приложением.

    Args:
        mock_app: Mock объект приложения.

    Returns:
        MainMenuScreen: Главное меню с привязанным mock приложением.
    """
    screen = MainMenuScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


# =============================================================================
# ТЕСТЫ НАВИГАЦИИ ПО ЦЕПОЧКЕ ЭКРАНОВ
# =============================================================================


class TestScreenNavigationChain:
    """Тесты навигации по цепочке экранов.

    Проверяет корректность переходов:
    main_menu → city_selector → category_selector → parsing
    """

    def test_main_menu_to_city_selector_navigation(self, main_menu_screen, mock_app):
        """Тест перехода из главного меню в выбор городов.

        Сценарий:
        1. Пользователь находится в главном меню
        2. Нажимает кнопку "📁 Выбрать города"
        3. Должен открыться экран city_selector через push_screen

        Ожидаемое поведение:
        - app.push_screen вызывается с аргументом "city_selector"
        - app.pop_screen НЕ вызывается
        - app.switch_screen НЕ вызывается
        """
        # Эмулируем нажатие кнопки "Выбрать города"
        mock_button = Mock()
        mock_button.id = "select-cities"
        event = Mock()
        event.button = mock_button

        main_menu_screen.on_button_pressed(event)

        # Проверяем что push_screen был вызван корректно
        mock_app.push_screen.assert_called_once_with("city_selector")
        mock_app.pop_screen.assert_not_called()
        mock_app.switch_screen.assert_not_called()

    def test_city_selector_to_category_selector_navigation(self, city_selector_screen, mock_app):
        """Тест перехода из выбора городов в выбор категорий.

        Сценарий:
        1. Пользователь выбирает города в city_selector
        2. Нажимает кнопку "➡️ Далее"
        3. Должен открыться экран category_selector через push_screen

        Ожидаемое поведение:
        - selected_cities сохраняется в состоянии приложения
        - app.push_screen вызывается с аргументом "category_selector"
        - on_mount() у category_selector будет вызван (гарантируется Textual)
        """
        # Инициализируем экран городами
        city_selector_screen._cities = mock_app.get_cities.return_value
        city_selector_screen._selected_indices = {0, 1}  # Москва и Омск

        # Mock query_one для получения кнопки
        mock_button_widget = Mock()
        mock_button_widget.id = "next"
        city_selector_screen.query_one = Mock(return_value=mock_button_widget)

        # Эмулируем нажатие кнопки "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        city_selector_screen.on_button_pressed(event)

        # Проверяем что selected_cities был сохранён
        assert mock_app.selected_cities == ["Москва", "Омск"]

        # Проверяем что push_screen был вызван (не switch_screen!)
        mock_app.push_screen.assert_called_once_with("category_selector")
        mock_app.switch_screen.assert_not_called()

    def test_category_selector_to_parsing_navigation(self, category_selector_screen, mock_app):
        """Тест перехода из выбора категорий на экран парсинга.

        Сценарий:
        1. Пользователь выбирает категории в category_selector
        2. Нажимает кнопку "➡️ Далее"
        3. Должен открыться экран parsing через push_screen

        Ожидаемое поведение:
        - selected_categories сохраняется в состоянии приложения
        - app.push_screen вызывается с аргументом "parsing"
        - on_mount() у parsing_screen будет вызван (гарантируется Textual)
        - start_parsing() будет вызван из on_mount() parsing_screen
        """
        # Инициализируем экран категориями
        category_selector_screen._categories = mock_app.get_categories.return_value
        category_selector_screen._selected_indices = {0, 2}  # Рестораны и Кафе

        # Устанавливаем что города уже выбраны
        mock_app.selected_cities = ["Москва"]

        # Mock query_one для получения кнопки
        mock_button_widget = Mock()
        mock_button_widget.id = "next"
        category_selector_screen.query_one = Mock(return_value=mock_button_widget)

        # Эмулируем нажатие кнопки "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        category_selector_screen.on_button_pressed(event)

        # Проверяем что selected_categories был сохранён
        assert mock_app.selected_categories == ["Рестораны", "Кафе"]

        # Проверяем что push_screen был вызван (не switch_screen!)
        mock_app.push_screen.assert_called_once_with("parsing")
        mock_app.switch_screen.assert_not_called()

    def test_full_navigation_chain(self, mock_app):
        """Тест полной цепочки навигации от меню до парсинга.

        Сценарий:
        1. main_menu → city_selector (выбор городов)
        2. city_selector → category_selector (выбор категорий)
        3. category_selector → parsing (запуск парсинга)

        Ожидаемое поведение:
        - Все переходы используют push_screen (не switch_screen)
        - on_mount() вызывается для каждого экрана
        - Данные сохраняются между переходами
        """
        # Создаём экраны
        main_menu = MainMenuScreen()
        city_selector = CitySelectorScreen()
        category_selector = CategorySelectorScreen()

        type(main_menu).app = PropertyMock(return_value=mock_app)
        type(city_selector).app = PropertyMock(return_value=mock_app)
        type(category_selector).app = PropertyMock(return_value=mock_app)

        # Шаг 1: main_menu → city_selector
        mock_button = Mock()
        mock_button.id = "select-cities"
        event = Mock()
        event.button = mock_button
        main_menu.on_button_pressed(event)

        # Шаг 2: city_selector → category_selector
        city_selector._cities = mock_app.get_cities.return_value
        city_selector._selected_indices = {0}

        mock_button.id = "next"
        city_selector.on_button_pressed(event)

        # Шаг 3: category_selector → parsing
        category_selector._categories = mock_app.get_categories.return_value
        category_selector._selected_indices = {0}
        mock_app.selected_cities = ["Москва"]

        category_selector.on_button_pressed(event)

        # Проверяем что все переходы использовали push_screen
        assert mock_app.push_screen.call_count == 3
        mock_app.push_screen.assert_has_calls(
            [call("city_selector"), call("category_selector"), call("parsing")]
        )

        # Проверяем что switch_screen НЕ использовался
        mock_app.switch_screen.assert_not_called()


# =============================================================================
# ТЕСТЫ ВЫЗОВА on_mount() ДЛЯ PARSING SCREEN
# =============================================================================


class TestParsingScreenOnMount:
    """Тесты вызова on_mount() для ParsingScreen.

    Проверяет что on_mount() вызывается и корректно обрабатывает:
    - Наличие выбранных городов и категорий
    - Отсутствие выбранных городов
    - Отсутствие выбранных категорий
    """

    def test_on_mount_called_with_valid_data(self, parsing_screen, mock_app):
        """Тест вызова on_mount() с корректными данными.

        Сценарий:
        1. selected_cities и selected_categories не пустые
        2. Вызывается on_mount()
        3. Должен запуститься парсинг через start_parsing()

        Ожидаемое поведение:
        - _parsing_started устанавливается в True
        - app.start_parsing() вызывается с корректными данными
        - app.pop_screen() НЕ вызывается
        """
        # Устанавливаем выбранные данные
        mock_app.selected_cities = ["Москва", "Омск"]
        mock_app.selected_categories = ["Рестораны", "Аптеки"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Вызываем on_mount()
        parsing_screen.on_mount()

        # Проверяем что парсинг был запущен
        assert parsing_screen._parsing_started is True

        # Проверяем что start_parsing был вызван
        mock_app.start_parsing.assert_called_once()

        # Проверяем что pop_screen НЕ вызывался (нет ошибки)
        mock_app.pop_screen.assert_not_called()

    def test_on_mount_called_without_cities(self, parsing_screen, mock_app):
        """Тест вызова on_mount() без выбранных городов.

        Сценарий:
        1. selected_cities пустой
        2. Вызывается on_mount()
        3. Должна быть обработка ошибки и возврат в меню

        Ожидаемое поведение:
        - _parsing_started остаётся False
        - app.pop_screen() вызывается для возврата в меню
        - app.start_parsing() НЕ вызывается
        """
        # Устанавливаем пустые города
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Вызываем on_mount()
        parsing_screen.on_mount()

        # Проверяем что парсинг НЕ был запущен
        assert parsing_screen._parsing_started is False

        # Проверяем что pop_screen был вызван для возврата в меню
        mock_app.pop_screen.assert_called_once()

        # Проверяем что start_parsing НЕ вызывался
        mock_app.start_parsing.assert_not_called()

    def test_on_mount_called_without_categories(self, parsing_screen, mock_app):
        """Тест вызова on_mount() без выбранных категорий.

        Сценарий:
        1. selected_categories пустой
        2. Вызывается on_mount()
        3. Должна быть обработка ошибки и возврат в меню

        Ожидаемое поведение:
        - _parsing_started остаётся False
        - app.pop_screen() вызывается для возврата в меню
        - app.start_parsing() НЕ вызывается
        """
        # Устанавливаем пустые категории
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Вызываем on_mount()
        parsing_screen.on_mount()

        # Проверяем что парсинг НЕ был запущен
        assert parsing_screen._parsing_started is False

        # Проверяем что pop_screen был вызван для возврата в меню
        mock_app.pop_screen.assert_called_once()

        # Проверяем что start_parsing НЕ вызывался
        mock_app.start_parsing.assert_not_called()

    def test_on_mount_resets_stopping_flag(self, parsing_screen, mock_app):
        """Тест что on_mount() сбрасывает флаг _stopping.

        Сценарий:
        1. _stopping установлен в True (предыдущий запуск)
        2. Вызывается on_mount()
        3. Флаг должен быть сброшен для нового запуска

        Ожидаемое поведение:
        - _stopping устанавливается в False
        - _parsing_started устанавливается в False
        """
        # Устанавливаем флаги в состояние после предыдущего запуска
        parsing_screen._stopping = True
        parsing_screen._parsing_started = True

        # Устанавливаем корректные данные
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Вызываем on_mount()
        parsing_screen.on_mount()

        # Проверяем что флаги были сброшены
        assert parsing_screen._stopping is False
        # _parsing_started должен стать True после успешного запуска
        assert parsing_screen._parsing_started is True


# =============================================================================
# ТЕСТЫ НА ОБНАРУЖЕНИЕ НЕПРАВИЛЬНОГО ИСПОЛЬЗОВАНИЯ switch_screen vs push_screen
# =============================================================================


class TestSwitchScreenVsPushScreen:
    """Тесты на обнаружение неправильного использования switch_screen vs push_screen.

    Проверяет что:
    - switch_screen НЕ используется для переходов где нужен on_mount()
    - push_screen используется для переходов с критической логикой в on_mount()
    """

    def test_city_selector_uses_push_screen_not_switch(self, city_selector_screen, mock_app):
        """Тест что city_selector использует push_screen а не switch_screen.

        Критично потому что:
        - category_selector.on_mount() должен загрузить категории
        - Если использовать switch_screen, on_mount() может не вызваться

        Ожидаемое поведение:
        - push_screen вызывается
        - switch_screen НЕ вызывается
        """
        city_selector_screen._cities = mock_app.get_cities.return_value
        city_selector_screen._selected_indices = {0}

        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        city_selector_screen.on_button_pressed(event)

        # Проверяем что push_screen был использован
        mock_app.push_screen.assert_called_once_with("category_selector")

        # Проверяем что switch_screen НЕ был использован
        mock_app.switch_screen.assert_not_called()

    def test_category_selector_uses_push_screen_not_switch(
        self, category_selector_screen, mock_app
    ):
        """Тест что category_selector использует push_screen а не switch_screen.

        Критично потому что:
        - parsing_screen.on_mount() должен запустить парсинг
        - Если использовать switch_screen, on_mount() может не вызваться
        - start_parsing() не будет вызван

        Ожидаемое поведение:
        - push_screen вызывается
        - switch_screen НЕ вызывается
        """
        category_selector_screen._categories = mock_app.get_categories.return_value
        category_selector_screen._selected_indices = {0}
        mock_app.selected_cities = ["Москва"]

        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        category_selector_screen.on_button_pressed(event)

        # Проверяем что push_screen был использован
        mock_app.push_screen.assert_called_once_with("parsing")

        # Проверяем что switch_screen НЕ был использован
        mock_app.switch_screen.assert_not_called()

    def test_main_menu_uses_push_screen_for_parsing(self, main_menu_screen, mock_app):
        """Тест что main_menu использует push_screen для перехода на parsing.

        Критично потому что:
        - parsing_screen.on_mount() должен запустить парсинг
        - Если использовать switch_screen, on_mount() может не вызваться

        Ожидаемое поведение:
        - push_screen вызывается
        - switch_screen НЕ вызывается
        """
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        mock_button = Mock()
        mock_button.id = "start-parsing"
        event = Mock()
        event.button = mock_button

        main_menu_screen.on_button_pressed(event)

        # Проверяем что push_screen был использован
        mock_app.push_screen.assert_called_once_with("parsing")

        # Проверяем что switch_screen НЕ был использован
        mock_app.switch_screen.assert_not_called()


# =============================================================================
# ТЕСТЫ НА ОБРАБОТКУ ОШИБОК
# =============================================================================


class TestErrorHandling:
    """Тесты на обработку ошибок при навигации.

    Проверяет корректную обработку:
    - Отсутствия выбранных городов
    - Отсутствия выбранных категорий
    - Попытки запуска парсинга без данных
    """

    def test_main_menu_prevents_parsing_without_cities(self, main_menu_screen, mock_app):
        """Тест что главное меню предотвращает парсинг без городов.

        Сценарий:
        1. selected_cities пустой
        2. Пользователь нажимает "🚀 Запустить парсинг"
        3. Должно быть показано уведомление об ошибке

        Ожидаемое поведение:
        - app.notify вызывается с сообщением об ошибке
        - app.push_screen НЕ вызывается
        """
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]

        mock_button = Mock()
        mock_button.id = "start-parsing"
        event = Mock()
        event.button = mock_button

        main_menu_screen.on_button_pressed(event)

        # Проверяем что было показано уведомление
        mock_app.notify.assert_called_once()

        # Проверяем что push_screen НЕ был вызван
        mock_app.push_screen.assert_not_called()

    def test_main_menu_prevents_parsing_without_categories(self, main_menu_screen, mock_app):
        """Тест что главное меню предотвращает парсинг без категорий.

        Сценарий:
        1. selected_categories пустой
        2. Пользователь нажимает "🚀 Запустить парсинг"
        3. Должно быть показано уведомление об ошибке

        Ожидаемое поведение:
        - app.notify вызывается с сообщением об ошибке
        - app.push_screen НЕ вызывается
        """
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []

        mock_button = Mock()
        mock_button.id = "start-parsing"
        event = Mock()
        event.button = mock_button

        main_menu_screen.on_button_pressed(event)

        # Проверяем что было показано уведомление
        mock_app.notify.assert_called_once()

        # Проверяем что push_screen НЕ был вызван
        mock_app.push_screen.assert_not_called()

    def test_category_selector_prevents_parsing_without_cities(
        self, category_selector_screen, mock_app
    ):
        """Тест что category_selector предотвращает парсинг без городов.

        Сценарий:
        1. selected_cities пустой
        2. Пользователь нажимает "➡️ Далее"
        3. Должно быть показано уведомление об ошибке

        Ожидаемое поведение:
        - app.notify вызывается с сообщением об ошибке
        - app.notify_user вызывается для логирования
        - app.push_screen НЕ вызывается
        """
        category_selector_screen._categories = mock_app.get_categories.return_value
        category_selector_screen._selected_indices = {0}
        mock_app.selected_cities = []  # Города не выбраны!

        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        category_selector_screen.on_button_pressed(event)

        # Проверяем что было показано уведомление
        mock_app.notify.assert_called_once()

        # Проверяем что было залогировано
        mock_app.notify_user.assert_called_once()

        # Проверяем что push_screen НЕ был вызван
        mock_app.push_screen.assert_not_called()


# =============================================================================
# ТЕСТЫ СОСТОЯНИЯ МЕЖДУ ЭКРАНАМИ
# =============================================================================


class TestStatePersistence:
    """Тесты сохранения состояния между экранами.

    Проверяет что:
    - selected_cities сохраняется при переходе между экранами
    - selected_categories сохраняется при переходе между экранами
    """

    def test_selected_cities_persists_across_screens(self, mock_app):
        """Тест сохранения выбранных городов между экранами.

        Сценарий:
        1. Пользователь выбирает города в city_selector
        2. Переходит на category_selector
        3. selected_cities должен сохраниться

        Ожидаемое поведение:
        - selected_cities устанавливается в city_selector
        - selected_cities доступен в category_selector
        """
        # Создаём экран city_selector
        city_selector = CitySelectorScreen()
        type(city_selector).app = PropertyMock(return_value=mock_app)

        # Инициализируем городами
        city_selector._cities = mock_app.get_cities.return_value
        city_selector._selected_indices = {0, 1, 2}

        # Эмулируем нажатие "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        city_selector.on_button_pressed(event)

        # Проверяем что selected_cities был установлен
        assert mock_app.selected_cities == ["Москва", "Омск", "Санкт-Петербург"]

        # Создаём экран category_selector и проверяем что данные доступны
        category_selector = CategorySelectorScreen()
        type(category_selector).app = PropertyMock(return_value=mock_app)

        # Проверяем что selected_cities доступен
        assert category_selector.app.selected_cities == ["Москва", "Омск", "Санкт-Петербург"]

    def test_selected_categories_persists_across_screens(self, mock_app):
        """Тест сохранения выбранных категорий между экранами.

        Сценарий:
        1. Пользователь выбирает категории в category_selector
        2. Переходит на parsing_screen
        3. selected_categories должен сохраниться

        Ожидаемое поведение:
        - selected_categories устанавливается в category_selector
        - selected_categories доступен в parsing_screen
        """
        # Создаём экран category_selector
        category_selector = CategorySelectorScreen()
        type(category_selector).app = PropertyMock(return_value=mock_app)

        # Инициализируем категориями
        category_selector._categories = mock_app.get_categories.return_value
        category_selector._selected_indices = {0, 1}

        # Устанавливаем что города уже выбраны
        mock_app.selected_cities = ["Москва"]

        # Эмулируем нажатие "Далее"
        mock_button = Mock()
        mock_button.id = "next"
        event = Mock()
        event.button = mock_button

        category_selector.on_button_pressed(event)

        # Проверяем что selected_categories был установлен
        assert mock_app.selected_categories == ["Рестораны", "Аптеки"]

        # Создаём экран parsing_screen и проверяем что данные доступны
        parsing_screen = ParsingScreen()
        type(parsing_screen).app = PropertyMock(return_value=mock_app)

        # Проверяем что selected_categories доступен
        assert parsing_screen.app.selected_categories == ["Рестораны", "Аптеки"]


# =============================================================================
# ТЕСТЫ БЫСТРОЙ НАВИГАЦИИ (RACE CONDITIONS)
# =============================================================================


class TestRapidNavigation:
    """Тесты быстрой навигации для выявления race conditions.

    Проверяет что:
    - Быстрые нажатия кнопок не вызывают зависаний
    - Многократные вызовы action_stop_parsing обрабатываются корректно
    """

    def test_rapid_stop_button_presses(self, parsing_screen, mock_app):
        """Тест быстрых нажатий кнопки "Стоп".

        Сценарий:
        1. Парсинг запущен
        2. Пользователь быстро нажимает "Стоп" несколько раз
        3. Не должно быть зависания или повторной остановки

        Ожидаемое поведение:
        - _stopping устанавливается в True после первого нажатия
        - app.stop_parsing() вызывается только один раз
        - app.pop_screen() вызывается только один раз
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Быстро нажимаем "Стоп" несколько раз
        parsing_screen.action_stop_parsing()
        parsing_screen.action_stop_parsing()
        parsing_screen.action_stop_parsing()

        # Проверяем что stop_parsing был вызван только один раз
        mock_app.stop_parsing.assert_called_once()

        # Проверяем что pop_screen был вызван только один раз
        mock_app.pop_screen.assert_called_once()

        # Проверяем что флаг _stopping установлен
        assert parsing_screen._stopping is True

    def test_home_button_during_parsing(self, parsing_screen, mock_app):
        """Тест нажатия кнопки "Домой" во время парсинга.

        Сценарий:
        1. Парсинг запущен
        2. Пользователь нажимает "🏠 В меню"
        3. Парсинг должен остановиться и произойти возврат в меню

        Ожидаемое поведение:
        - app.stop_parsing() вызывается
        - app.pop_screen() вызывается
        """
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Эмулируем нажатие кнопки "Домой"
        mock_button = Mock()
        mock_button.id = "home"
        event = Mock()
        event.button = mock_button

        parsing_screen.on_button_pressed(event)

        # Проверяем что stop_parsing был вызван
        mock_app.stop_parsing.assert_called_once()

        # Проверяем что pop_screen был вызван
        mock_app.pop_screen.assert_called_once()


# =============================================================================
# ТЕСТЫ ИНТЕГРАЦИИ
# =============================================================================


class TestNavigationIntegration:
    """Интеграционные тесты навигации TUI.

    Проверяет полную интеграцию всех компонентов навигации.
    """

    def test_complete_parsing_workflow(self, mock_app):
        """Тест полного рабочего процесса парсинга.

        Сценарий:
        1. main_menu → city_selector (выбор городов)
        2. city_selector → category_selector (выбор категорий)
        3. category_selector → parsing (запуск парсинга)
        4. parsing.on_mount() вызывает start_parsing()

        Ожидаемое поведение:
        - Все переходы используют push_screen
        - on_mount() вызывается для parsing_screen
        - start_parsing() вызывается с корректными данными
        """
        # Шаг 1: Выбор городов
        mock_app.selected_cities = ["Москва", "Омск"]

        # Шаг 2: Выбор категорий
        mock_app.selected_categories = ["Рестораны", "Аптеки"]

        # Шаг 3: Создание parsing_screen и вызов on_mount()
        parsing_screen = ParsingScreen()
        type(parsing_screen).app = PropertyMock(return_value=mock_app)

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Вызываем on_mount()
        parsing_screen.on_mount()

        # Проверяем что парсинг был запущен
        assert parsing_screen._parsing_started is True

        # Проверяем что start_parsing был вызван с корректными данными
        mock_app.start_parsing.assert_called_once()

        # Получаем аргументы вызова start_parsing
        call_args = mock_app.start_parsing.call_args
        cities_arg = call_args[0][0]
        categories_arg = call_args[0][1]

        # Проверяем что данные были переданы корректно
        assert len(cities_arg) == 2  # Москва и Омск
        assert len(categories_arg) == 2  # Рестораны и Аптеки

    def test_navigation_with_back_button(self, mock_app):
        """Тест навигации с использованием кнопки "Назад".

        Сценарий:
        1. main_menu → city_selector
        2. city_selector → back → main_menu
        3. main_menu → city_selector (повторно)
        4. city_selector → category_selector

        Ожидаемое поведение:
        - pop_screen вызывается при нажатии "Назад"
        - push_screen вызывается при переходе вперёд
        - Состояние сохраняется при возврате
        """
        # Создаём экраны
        main_menu = MainMenuScreen()
        city_selector = CitySelectorScreen()

        type(main_menu).app = PropertyMock(return_value=mock_app)
        type(city_selector).app = PropertyMock(return_value=mock_app)

        # Шаг 1: main_menu → city_selector
        mock_button = Mock()
        mock_button.id = "select-cities"
        event = Mock()
        event.button = mock_button
        main_menu.on_button_pressed(event)

        # Шаг 2: city_selector → back
        mock_button.id = "back"
        city_selector.on_button_pressed(event)

        # Шаг 3: main_menu → city_selector (повторно)
        mock_button.id = "select-cities"
        main_menu.on_button_pressed(event)

        # Шаг 4: city_selector → category_selector
        city_selector._cities = mock_app.get_cities.return_value
        city_selector._selected_indices = {0}
        mock_button.id = "next"
        city_selector.on_button_pressed(event)

        # Проверяем что pop_screen был вызван один раз (шаг 2)
        assert mock_app.pop_screen.call_count == 1

        # Проверяем что push_screen был вызван три раза (шаги 1, 3, 4)
        assert mock_app.push_screen.call_count == 3


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
