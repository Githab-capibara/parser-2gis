"""
Тесты для проверки управления состоянием городов/категорий и TUI.

Проверяет:
1. CitySelectorScreen → сохранение selected_cities в app.state
2. CategorySelectorScreen → сохранение selected_categories в app.state
3. ParsingScreen.on_mount() → проверка что города/категории выбраны перед запуском
4. ParsingScreen.action_stop_parsing() → корректная остановка и возврат в меню
5. TUIApp.start_parsing() → проверка что не запускается без данных

Тесты используют pytest и mock для изоляции зависимостей.
"""

from unittest.mock import MagicMock, Mock, PropertyMock

import pytest

from parser_2gis.tui_textual.app import TUIApp
from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen
from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen
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
    app.selected_cities = [{"name": "Омск", "code": "omsk"}]  # Города по умолчанию для валидации
    app.selected_categories = []
    app.get_cities.return_value = [
        {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow", "country_code": "ru"},
        {
            "name": "Санкт-Петербург",
            "url": "https://2gis.ru/spb",
            "code": "spb",
            "country_code": "ru",
        },
        {"name": "Омск", "url": "https://2gis.ru/omsk", "code": "omsk", "country_code": "ru"},
    ]
    app.get_categories.return_value = [
        {"name": "Рестораны", "id": 93},
        {"name": "Кафе", "id": 161},
        {"name": "Бары", "id": 162},
    ]
    app.push_screen = Mock()
    app.pop_screen = Mock()
    app.switch_screen = Mock()
    app.notify_user = Mock()
    app.running = False
    return app


@pytest.fixture
def city_selector_screen(mock_app):
    """Фикстура для создания CitySelectorScreen с mock приложением.

    Args:
        mock_app: Mock приложение.

    Returns:
        CitySelectorScreen с настроенным mock приложением.
    """
    screen = CitySelectorScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


@pytest.fixture
def category_selector_screen(mock_app):
    """Фикстура для создания CategorySelectorScreen с mock приложением.

    Args:
        mock_app: Mock приложение.

    Returns:
        CategorySelectorScreen с настроенным mock приложением.
    """
    screen = CategorySelectorScreen()
    type(screen).app = PropertyMock(return_value=mock_app)
    return screen


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
# ТЕСТЫ ДЛЯ CITYSELECTORSCREEN
# =============================================================================


class TestCitySelectorScreenStateManagement:
    """Тесты для проверки управления состоянием в CitySelectorScreen."""

    def test_selected_cities_saved_to_app_state(self, city_selector_screen, mock_app):
        """Тест проверяет сохранение выбранных городов в app.selected_cities.

        Сценарий:
        1. Пользователь выбирает города
        2. Нажимает кнопку "Далее"
        3. Выбранные города сохраняются в app.selected_cities

        Ожидаемое поведение:
        - app.selected_cities содержит названия выбранных городов
        - Вызывается app.push_screen для перехода к выбору категорий
        """
        # Установим начальные выбранные города
        mock_app.selected_cities = ["Москва", "Омск"]

        # Эмулируем загрузку городов
        city_selector_screen._load_cities()

        # Проверяем что города загружены
        assert len(city_selector_screen._cities) == 3

        # Проверяем что выбранные города восстановлены
        # Индексы 0 (Москва) и 2 (Омск) должны быть в selected_indices
        assert 0 in city_selector_screen._selected_indices
        assert 2 in city_selector_screen._selected_indices

    def test_city_selector_next_button_saves_state(self, city_selector_screen, mock_app):
        """Тест проверяет что кнопка 'Далее' сохраняет состояние в app.

        Сценарий:
        1. Пользователь выбирает города через Checkbox
        2. Нажимает кнопку "Далее"
        3. Состояние сохраняется в app.selected_cities

        Ожидаемое поведение:
        - app.selected_cities устанавливается в выбранные значения
        - Вызывается app.switch_screen("category_selector")
        """
        from textual.widgets import Button

        # Загрузим города чтобы _cities был инициализирован
        city_selector_screen._load_cities()

        # Выберем города вручную через индексы
        city_selector_screen._selected_indices = {0, 2}  # Москва и Омск

        # Создадим мок кнопки
        mock_button = Mock(spec=Button)
        mock_button.id = "next"

        # Создадим мок события
        mock_event = Mock()
        mock_event.button = mock_button

        # Вызовем обработчик нажатия кнопки
        city_selector_screen.on_button_pressed(mock_event)

        # Проверяем что app.selected_cities был установлен
        assert mock_app.selected_cities == ["Москва", "Омск"]

        # Проверяем что был вызван переход к экрану выбора категорий через switch_screen
        mock_app.switch_screen.assert_called_once_with("category_selector")

    def test_city_selector_back_button_pops_screen(self, city_selector_screen, mock_app):
        """Тест проверяет что кнопка 'Назад' возвращает к предыдущему экрану.

        Сценарий:
        1. Пользователь нажимает кнопку "Назад"
        2. Экран закрывается через pop_screen()

        Ожидаемое поведение:
        - Вызывается app.pop_screen()
        - Состояние не изменяется
        """
        from textual.widgets import Button

        # Создадим мок кнопки
        mock_button = Mock(spec=Button)
        mock_button.id = "back"

        # Создадим мок события
        mock_event = Mock()
        mock_event.button = mock_button

        # Вызовем обработчик нажатия кнопки
        city_selector_screen.on_button_pressed(mock_event)

        # Проверяем что был вызван pop_screen
        mock_app.pop_screen.assert_called_once()

        # Проверяем что selected_cities не изменился
        assert mock_app.selected_cities == []

    def test_city_selector_select_all(self, city_selector_screen, mock_app):
        """Тест проверяет функцию 'Выбрать все' города.

        Сценарий:
        1. Пользователь нажимает "Выбрать все"
        2. Все города из отфильтрованного списка выбираются

        Ожидаемое поведение:
        - Все индексы городов добавляются в _selected_indices
        """
        # Загрузим города
        city_selector_screen._load_cities()
        city_selector_screen._filtered_cities = city_selector_screen._cities.copy()

        # Создадим мок checkbox для эмуляции
        mock_checkbox1 = Mock()
        mock_checkbox1.value = False
        mock_checkbox1.city_code = "moscow"
        mock_checkbox2 = Mock()
        mock_checkbox2.value = False
        mock_checkbox2.city_code = "spb"
        mock_checkbox3 = Mock()
        mock_checkbox3.value = False
        mock_checkbox3.city_code = "omsk"
        city_selector_screen._checkboxes = [mock_checkbox1, mock_checkbox2, mock_checkbox3]

        # Выберем все города
        city_selector_screen.action_select_all()

        # Проверяем что checkbox.value установлен в True
        assert mock_checkbox1.value is True
        assert mock_checkbox2.value is True
        assert mock_checkbox3.value is True

    def test_city_selector_deselect_all(self, city_selector_screen, mock_app):
        """Тест проверяет функцию 'Снять все' с городов.

        Сценарий:
        1. Пользователь выбирает несколько городов
        2. Нажимает "Снять все"
        3. Выбор снимается со всех городов

        Ожидаемое поведение:
        - Checkbox value устанавливается в False
        """
        # Загрузим города
        city_selector_screen._load_cities()
        city_selector_screen._filtered_cities = city_selector_screen._cities.copy()

        # Создадим мок checkbox для эмуляции
        mock_checkbox1 = Mock()
        mock_checkbox1.value = True
        mock_checkbox1.city_code = "moscow"
        mock_checkbox2 = Mock()
        mock_checkbox2.value = True
        mock_checkbox2.city_code = "spb"
        mock_checkbox3 = Mock()
        mock_checkbox3.value = False
        mock_checkbox3.city_code = "omsk"
        city_selector_screen._checkboxes = [mock_checkbox1, mock_checkbox2, mock_checkbox3]

        # Снимем все
        city_selector_screen.action_deselect_all()

        # Проверяем что checkbox.value установлен в False
        assert mock_checkbox1.value is False
        assert mock_checkbox2.value is False
        assert mock_checkbox3.value is False


# =============================================================================
# ТЕСТЫ ДЛЯ CATEGORYSELECTORSCREEN
# =============================================================================


class TestCategorySelectorScreenStateManagement:
    """Тесты для проверки управления состоянием в CategorySelectorScreen."""

    def test_selected_categories_saved_to_app_state(self, category_selector_screen, mock_app):
        """Тест проверяет сохранение выбранных категорий в app.selected_categories.

        Сценарий:
        1. Пользователь выбирает категории
        2. Выбранные категории сохраняются в app.selected_categories

        Ожидаемое поведение:
        - app.selected_categories содержит названия выбранных категорий
        """
        # Установим начальные выбранные категории
        mock_app.selected_categories = ["Рестораны", "Бары"]

        # Эмулируем загрузку категорий
        category_selector_screen._load_categories()

        # Проверяем что категории загружены
        assert len(category_selector_screen._categories) == 3

        # Проверяем что выбранные категории восстановлены
        # Индексы 0 (Рестораны) и 2 (Бары) должны быть в selected_indices
        assert 0 in category_selector_screen._selected_indices
        assert 2 in category_selector_screen._selected_indices

    def test_category_selector_next_button_saves_state(self, category_selector_screen, mock_app):
        """Тест проверяет что кнопка 'Далее' сохраняет состояние в app.

        Сценарий:
        1. Пользователь выбирает категории через Checkbox
        2. Нажимает кнопку "Далее"
        3. Состояние сохраняется в app.selected_categories

        Ожидаемое поведение:
        - app.selected_categories устанавливается в выбранные значения
        - Вызывается app.switch_screen("parsing")
        """
        from textual.widgets import Button

        # Загрузим категории чтобы _categories был инициализирован
        category_selector_screen._load_categories()

        # Выберем категории вручную через индексы
        category_selector_screen._selected_indices = {0, 1}  # Рестораны и Кафе

        # Создадим мок кнопки
        mock_button = Mock(spec=Button)
        mock_button.id = "next"

        # Создадим мок события
        mock_event = Mock()
        mock_event.button = mock_button

        # Вызовем обработчик нажатия кнопки
        category_selector_screen.on_button_pressed(mock_event)

        # Проверяем что app.selected_categories был установлен
        assert mock_app.selected_categories == ["Рестораны", "Кафе"]

        # Проверяем что был вызван переход к экрану парсинга через switch_screen
        mock_app.switch_screen.assert_called_once_with("parsing")

    def test_category_selector_back_button_pops_screen(self, category_selector_screen, mock_app):
        """Тест проверяет что кнопка 'Назад' возвращает к предыдущему экрану.

        Сценарий:
        1. Пользователь нажимает кнопку "Назад"
        2. Экран закрывается через pop_screen()

        Ожидаемое поведение:
        - Вызывается app.pop_screen()
        - Состояние не изменяется
        """
        from textual.widgets import Button

        # Создадим мок кнопки
        mock_button = Mock(spec=Button)
        mock_button.id = "back"

        # Создадим мок события
        mock_event = Mock()
        mock_event.button = mock_button

        # Вызовем обработчик нажатия кнопки
        category_selector_screen.on_button_pressed(mock_event)

        # Проверяем что был вызван pop_screen
        mock_app.pop_screen.assert_called_once()

        # Проверяем что selected_categories не изменился
        assert mock_app.selected_categories == []

    def test_category_selector_select_all(self, category_selector_screen, mock_app):
        """Тест проверяет функцию 'Выбрать все' категории.

        Сценарий:
        1. Пользователь нажимает "Выбрать все"
        2. Все категории из отфильтрованного списка выбираются

        Ожидаемое поведение:
        - Checkbox value устанавливается в True
        """
        # Загрузим категории
        category_selector_screen._load_categories()
        category_selector_screen._filtered_categories = category_selector_screen._categories.copy()

        # Создадим мок checkbox для эмуляции
        mock_checkbox1 = Mock()
        mock_checkbox1.value = False
        mock_checkbox1.original_index = 0
        mock_checkbox2 = Mock()
        mock_checkbox2.value = False
        mock_checkbox2.original_index = 1
        mock_checkbox3 = Mock()
        mock_checkbox3.value = False
        mock_checkbox3.original_index = 2
        category_selector_screen._checkboxes = [mock_checkbox1, mock_checkbox2, mock_checkbox3]

        # Выберем все категории
        category_selector_screen.action_select_all()

        # Проверяем что checkbox.value установлен в True
        assert mock_checkbox1.value is True
        assert mock_checkbox2.value is True
        assert mock_checkbox3.value is True

    def test_category_selector_deselect_all(self, category_selector_screen, mock_app):
        """Тест проверяет функцию 'Снять все' с категорий.

        Сценарий:
        1. Пользователь выбирает несколько категорий
        2. Нажимает "Снять все"
        3. Выбор снимается со всех категорий

        Ожидаемое поведение:
        - Checkbox value устанавливается в False
        """
        # Загрузим категории
        category_selector_screen._load_categories()
        category_selector_screen._filtered_categories = category_selector_screen._categories.copy()

        # Создадим мок checkbox для эмуляции
        mock_checkbox1 = Mock()
        mock_checkbox1.value = True
        mock_checkbox1.original_index = 0
        mock_checkbox2 = Mock()
        mock_checkbox2.value = True
        mock_checkbox2.original_index = 1
        mock_checkbox3 = Mock()
        mock_checkbox3.value = False
        mock_checkbox3.original_index = 2
        category_selector_screen._checkboxes = [mock_checkbox1, mock_checkbox2, mock_checkbox3]

        # Снимем все
        category_selector_screen.action_deselect_all()

        # Проверяем что checkbox.value установлен в False
        assert mock_checkbox1.value is False
        assert mock_checkbox2.value is False
        assert mock_checkbox3.value is False


# =============================================================================
# ТЕСТЫ ДЛЯ PARSINGSCREEN.ON_MOUNT()
# =============================================================================


class TestParsingScreenOnMount:
    """Тесты для проверки поведения ParsingScreen.on_mount()."""

    def test_on_mount_with_no_selected_cities(self, parsing_screen, mock_app):
        """Тест проверяет обработку ситуации когда города не выбраны.

        Сценарий:
        1. Пользователь переходит к экрану парсинга без выбора городов
        2. on_mount() проверяет наличие выбранных городов
        3. Парсинг не запускается, возвращается в меню

        Ожидаемое поведение:
        - Запись в лог об ошибке
        - Вызывается _return_to_menu напрямую для возврата в меню
        - start_parsing() не вызывается
        """
        # Установим пустые списки
        mock_app.selected_cities = []
        mock_app.selected_categories = ["Рестораны"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock _return_to_menu
        parsing_screen._return_to_menu = Mock()

        # Вызовем on_mount
        parsing_screen.on_mount()

        # Проверяем что была запись в лог об ошибке
        # Ищем вызовы write с сообщением об ошибке
        write_calls = [call[0][0] for call in mock_log.write.call_args_list]
        assert any("Ошибка: не выбраны города для парсинга!" in call for call in write_calls)

        # Проверяем что был вызван возврат в меню
        parsing_screen._return_to_menu.assert_called_once()

    def test_on_mount_with_no_selected_categories(self, parsing_screen, mock_app):
        """Тест проверяет обработку ситуации когда категории не выбраны.

        Сценарий:
        1. Пользователь переходит к экрану парсинга без выбора категорий
        2. on_mount() проверяет наличие выбранных категорий
        3. Парсинг не запускается, возвращается в меню

        Ожидаемое поведение:
        - Запись в лог об ошибке
        - Вызывается _return_to_menu напрямую для возврата в меню
        - start_parsing() не вызывается
        """
        # Установим города но пустые категории
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock _return_to_menu
        parsing_screen._return_to_menu = Mock()

        # Вызовем on_mount
        parsing_screen.on_mount()

        # Проверяем что была запись в лог об ошибке
        write_calls = [call[0][0] for call in mock_log.write.call_args_list]
        assert any("Ошибка: не выбраны категории для парсинга!" in call for call in write_calls)

        # Проверяем что был вызван возврат в меню
        parsing_screen._return_to_menu.assert_called_once()

    def test_on_mount_with_selected_cities_and_categories(self, parsing_screen, mock_app):
        """Тест проверяет запуск парсинга когда города и категории выбраны.

        Сценарий:
        1. Пользователь выбирает города и категории
        2. Переходит к экрану парсинга
        3. on_mount() запускает парсинг

        Ожидаемое поведение:
        - start_parsing() вызывается с правильными данными
        - _parsing_started устанавливается в True
        """
        # Установим выбранные города и категории
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = ["Рестораны"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock start_parsing
        mock_app.start_parsing = Mock()

        # Вызовем on_mount
        parsing_screen.on_mount()

        # Проверяем что start_parsing был вызван
        assert mock_app.start_parsing.called

        # Проверяем что флаг запуска установлен
        assert parsing_screen._parsing_started is True

    def test_on_mount_logs_debug_info(self, parsing_screen, mock_app):
        """Тест проверяет что on_mount записывает отладочную информацию в лог.

        Сценарий:
        1. on_mount() вызывается
        2. Записывает информацию о количестве выбранных городов/категорий

        Ожидаемое поведение:
        - В лог записывается количество выбранных городов
        - В лог записывается количество выбранных категорий
        """
        # Установим выбранные города и категории
        mock_app.selected_cities = ["Москва", "Омск"]
        mock_app.selected_categories = ["Рестораны"]

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock call_later чтобы избежать реального вызова
        parsing_screen.call_later = Mock()

        # Вызовем on_mount
        parsing_screen.on_mount()

        # Проверяем что были записи в лог о количестве
        # Ищем вызовы write с информацией о количестве
        write_calls = [call[0][0] for call in mock_log.write.call_args_list]

        # Проверяем что есть записи о количестве городов и категорий
        assert any("Выбрано городов: 2" in call for call in write_calls)
        assert any("Выбрано категорий: 1" in call for call in write_calls)


# =============================================================================
# ТЕСТЫ ДЛЯ PARSINGSCREEN.ACTION_STOP_PARSING()
# =============================================================================


class TestParsingScreenStopParsing:
    """Тесты для проверки остановки парсинга."""

    def test_action_stop_parsing_sets_flags(self, parsing_screen, mock_app):
        """Тест проверяет что action_stop_parsing устанавливает флаги остановки.

        Сценарий:
        1. Пользователь нажимает кнопку "Стоп"
        2. action_stop_parsing() вызывается
        3. Флаги _stopping и app.running устанавливаются

        Ожидаемое поведение:
        - _stopping устанавливается в True
        - app.running устанавливается в False
        - Запись в лог об остановке
        """
        # Установим что парсинг запущен
        parsing_screen._parsing_started = True
        parsing_screen._stopping = False

        # Mock query_one для RichLog
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock call_later
        parsing_screen.call_later = Mock()

        # Вызовем остановку
        parsing_screen.action_stop_parsing()

        # Проверяем что флаг _stopping установлен
        assert parsing_screen._stopping is True

        # Проверяем что app.running установлен в False
        assert mock_app.running is False

    def test_action_stop_parsing_prevents_duplicate_calls(self, parsing_screen, mock_app):
        """Тест проверяет защиту от повторного вызова остановки.

        Сценарий:
        1. Пользователь нажимает "Стоп" дважды
        2. Второй вызов игнорируется

        Ожидаемое поведение:
        - При повторном вызове функция возвращается сразу
        - Флаги не изменяются повторно
        """
        # Установим что парсинг запущен и уже останавливается
        parsing_screen._parsing_started = True
        parsing_screen._stopping = True

        # Mock query_one
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock call_later
        parsing_screen.call_later = Mock()

        # Запомним количество вызовов call_later
        call_later_count_before = parsing_screen.call_later.call_count

        # Вызовем остановку ещё раз
        parsing_screen.action_stop_parsing()

        # Проверяем что call_later не был вызван повторно
        assert parsing_screen.call_later.call_count == call_later_count_before

    def test_action_stop_parsing_returns_to_menu(self, parsing_screen, mock_app):
        """Тест проверяет что после остановки возвращается в меню.

        Сценарий:
        1. Пользователь нажимает "Стоп"
        2. Парсинг останавливается
        3. Экран закрывается через _return_to_menu()

        Ожидаемое поведение:
        - _return_to_menu вызывается напрямую
        """
        # Установим что парсинг запущен
        parsing_screen._parsing_started = True

        # Mock query_one
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock _return_to_menu
        parsing_screen._return_to_menu = Mock()

        # Вызовем остановку
        parsing_screen.action_stop_parsing()

        # Проверяем что _return_to_menu был вызван
        parsing_screen._return_to_menu.assert_called_once()

    def test_action_stop_parsing_not_started_yet(self, parsing_screen, mock_app):
        """Тест проверяет остановку когда парсинг ещё не запущен.

        Сценарий:
        1. Пользователь нажимает "Стоп" до запуска парсинга
        2. Функция ничего не делает

        Ожидаемое поведение:
        - Флаги не устанавливаются
        - Запись в лог что парсинг ещё не запущен
        """
        # Установим что парсинг не запущен
        parsing_screen._parsing_started = False

        # Mock query_one
        mock_log = Mock()
        parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock call_later
        parsing_screen.call_later = Mock()

        # Вызовем остановку
        parsing_screen.action_stop_parsing()

        # Проверяем что флаг _stopping не установлен
        assert parsing_screen._stopping is False

        # Проверяем что app.running не изменился
        # (не проверяем mock_app.running так как он не должен был быть установлен)


# =============================================================================
# ТЕСТЫ ДЛЯ TUIAPP.START_PARSING()
# =============================================================================


class TestTUIAppStartParsing:
    """Тесты для проверки TUIApp.start_parsing()."""

    def test_start_parsing_with_no_cities(self, mock_app):
        """Тест проверяет что start_parsing не запускается без городов.

        Сценарий:
        1. start_parsing вызывается с пустым списком городов
        2. Парсинг не запускается

        Ожидаемое поведение:
        - Вызывается notify_user с ошибкой
        - push_screen не вызывается
        """
        cities = []
        categories = [{"name": "Рестораны", "id": 93}]

        # Вызовем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что было уведомление об ошибке
        mock_app.notify_user.assert_called_with(
            "Ошибка: не выбраны города для парсинга!", level="error"
        )

        # Проверяем что push_screen не был вызван
        mock_app.push_screen.assert_not_called()

    def test_start_parsing_with_no_categories(self, mock_app):
        """Тест проверяет что start_parsing не запускается без категорий.

        Сценарий:
        1. start_parsing вызывается с пустым списком категорий
        2. Парсинг не запускается

        Ожидаемое поведение:
        - Вызывается notify_user с ошибкой
        - push_screen не вызывается
        """
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = []

        # Вызовем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что было уведомление об ошибке
        mock_app.notify_user.assert_called_with(
            "Ошибка: не выбраны категории для парсинга!", level="error"
        )

        # Проверяем что push_screen не был вызван
        mock_app.push_screen.assert_not_called()

    def test_start_parsing_with_valid_data(self, mock_app):
        """Тест проверяет запуск start_parsing с валидными данными.

        Сценарий:
        1. start_parsing вызывается с городами и категориями
        2. Парсинг запускается корректно

        Ожидаемое поведение:
        - push_screen НЕ вызывается (экран уже открыт через switch_screen)
        - _run_parsing вызывается в фоне
        """
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Рестораны", "id": 93}]

        # Вызовем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что push_screen НЕ вызывался (экран уже открыт)
        mock_app.push_screen.assert_not_called()

        # Проверяем что notify_user не вызывался с ошибкой
        error_calls = [
            call for call in mock_app.notify_user.call_args_list if call[1].get("level") == "error"
        ]
        assert len(error_calls) == 0

    def test_start_parsing_early_return_prevents_execution(self, mock_app):
        """Тест проверяет что early return предотвращает выполнение.

        Сценарий:
        1. start_parsing вызывается без городов
        2. Early return срабатывает
        3. Остальной код не выполняется

        Ожидаемое поведение:
        - notify_user вызывается
        - push_screen не вызывается
        - _run_parsing не вызывается
        """
        cities = []
        categories = []

        # Вызовем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что notify_user был вызван (первая проверка - города)
        assert mock_app.notify_user.called

        # Проверяем что push_screen не был вызван
        mock_app.push_screen.assert_not_called()


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestTUIStateManagementIntegration:
    """Интеграционные тесты для проверки полного цикла управления состоянием."""

    def test_full_selection_flow(self, mock_app):
        """Тест проверяет полный цикл выбора городов и категорий.

        Сценарий:
        1. Пользователь выбирает города в CitySelectorScreen
        2. Переходит к CategorySelectorScreen
        3. Выбирает категории
        4. Переходит к ParsingScreen

        Ожидаемое поведение:
        - selected_cities сохраняется после выбора городов
        - selected_categories сохраняется после выбора категорий
        - ParsingScreen получает оба списка
        """
        # Создадим экраны
        city_screen = CitySelectorScreen()
        category_screen = CategorySelectorScreen()

        # Настроим mock приложения
        type(city_screen).app = PropertyMock(return_value=mock_app)
        type(category_screen).app = PropertyMock(return_value=mock_app)

        # Шаг 1: Выбор городов
        city_screen._load_cities()
        city_screen._selected_indices = {0, 2}  # Москва и Омск

        # Эмулируем нажатие "Далее"
        from textual.widgets import Button

        mock_button = Mock(spec=Button)
        mock_button.id = "next"
        mock_event = Mock()
        mock_event.button = mock_button

        city_screen.on_button_pressed(mock_event)

        # Проверяем что города сохранены
        assert mock_app.selected_cities == ["Москва", "Омск"]
        mock_app.switch_screen.assert_called_with("category_selector")

        # Шаг 2: Выбор категорий
        category_screen._load_categories()
        category_screen._selected_indices = {0}  # Рестораны

        mock_event.button.id = "next"
        category_screen.on_button_pressed(mock_event)

        # Проверяем что категории сохранены
        assert mock_app.selected_categories == ["Рестораны"]
        mock_app.switch_screen.assert_called_with("parsing")

    def test_state_persistence_across_screens(self, mock_app):
        """Тест проверяет сохранение состояния при переходе между экранами.

        Сценарий:
        1. Пользователь выбирает города
        2. Переходит к категориям
        3. Возвращается назад
        4. Выбор городов сохраняется

        Ожидаемое поведение:
        - selected_cities сохраняется при переходе между экранами
        - При возврате назад выбор восстанавливается
        """
        # Установим начальный выбор
        mock_app.selected_cities = ["Москва"]
        mock_app.selected_categories = []

        # Создадим экран выбора городов
        city_screen = CitySelectorScreen()
        type(city_screen).app = PropertyMock(return_value=mock_app)

        # Загрузим города
        city_screen._load_cities()

        # Проверяем что выбор восстановлен
        assert 0 in city_screen._selected_indices  # Москва

        # Добавим ещё город
        city_screen._selected_indices.add(1)  # Санкт-Петербург

        # Эмулируем сохранение
        selected_names = [
            city_screen._cities[i].get("name", "") for i in sorted(city_screen._selected_indices)
        ]
        mock_app.selected_cities = selected_names

        # Проверяем что оба города сохранены
        assert mock_app.selected_cities == ["Москва", "Санкт-Петербург"]


# =============================================================================
# ТЕСТЫ ДЛЯ ПРОВЕРКИ БЕЗОПАСНОСТИ
# =============================================================================


class TestTUIStateSafety:
    """Тесты для проверки безопасности управления состоянием."""

    def test_empty_state_handling(self, mock_app):
        """Тест проверяет обработку пустого состояния.

        Сценарий:
        1. app.selected_cities и app.selected_categories пустые
        2. Попытка запуска парсинга

        Ожидаемое поведение:
        - Early return срабатывает
        - Ошибка не возникает
        """
        mock_app.selected_cities = []
        mock_app.selected_categories = []

        # Вызовем start_parsing
        TUIApp.start_parsing(mock_app, [], [])

        # Проверяем что была вызвана ошибка
        assert mock_app.notify_user.called

    def test_none_state_handling(self, mock_app):
        """Тест проверяет обработку None состояния.

        Сценарий:
        1. app.selected_cities или app.selected_categories равны None
        2. Попытка запуска парсинга

        Ожидаемое поведение:
        - Обработка без ошибок
        """
        mock_app.selected_cities = None
        mock_app.selected_categories = None

        # Вызовем start_parsing с None
        # Это должно обработаться корректно
        try:
            TUIApp.start_parsing(mock_app, None, None)
        except (TypeError, AttributeError):
            pytest.fail("start_parsing должен обрабатывать None значения")

    def test_large_selection_handling(self, mock_app):
        """Тест проверяет обработку большого количества выбранных элементов.

        Сценарий:
        1. Выбирается большое количество городов и категорий
        2. Запускается парсинг

        Ожидаемое поведение:
        - Парсинг запускается корректно
        - Нет утечек памяти или производительности
        """
        # Создадим большой список городов
        cities = [{"name": f"Город {i}", "url": f"https://2gis.ru/city{i}"} for i in range(100)]
        categories = [{"name": f"Категория {i}", "id": i} for i in range(50)]

        mock_app.selected_cities = [city["name"] for city in cities]
        mock_app.selected_categories = [cat["name"] for cat in categories]

        # Вызовем start_parsing
        TUIApp.start_parsing(mock_app, cities, categories)

        # Проверяем что push_screen НЕ вызывался (экран уже открыт)
        mock_app.push_screen.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
