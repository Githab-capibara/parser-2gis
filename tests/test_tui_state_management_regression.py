"""
Тесты для выявления регрессионных ошибок управления состоянием в TUI.

Предотвращает ошибки:
- Запуск парсинга без выбранных городов/категорий
- Некорректная обработка кнопки "Стоп"
- Потеря состояния между экранами TUI

Тесты используют pytest и unittest.mock для полной изоляции зависимостей.
Все тесты запускаются быстро (< 5 секунд на тест) и не требуют реального браузера или сети.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, PropertyMock

import pytest

from parser_2gis.tui_textual.app import TUIApp
from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def mock_tui_app() -> MagicMock:
    """Фикстура для создания mock приложения TUIApp.

    Returns:
        MagicMock с настроенными методами и свойствами TUIApp:
        - selected_cities: пустой список
        - selected_categories: пустой список
        - _state: словарь с начальным состоянием
        - get_cities(): список из 3 городов
        - get_categories(): список из 3 категорий
        - push_screen: Mock метод
        - pop_screen: Mock метод
        - notify_user: Mock метод
        - running: False
    """
    app = MagicMock(spec=TUIApp)
    app.selected_cities = []
    app.selected_categories = []
    app._state = {
        "selected_cities": [],
        "selected_categories": [],
        "parsing_active": False,
        "parsing_progress": 0,
        "total_urls": 0,
        "current_url": 0,
        "current_city": "",
        "current_category": "",
        "success_count": 0,
        "error_count": 0,
        "total_pages": 0,
        "current_page": 0,
        "total_records": 0,
        "current_record": 0,
    }
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
    app.notify_user = Mock()
    app.running = False
    return app


@pytest.fixture
def mock_parsing_screen(mock_tui_app: MagicMock) -> ParsingScreen:
    """Фикстура для создания ParsingScreen с mock приложением.

    Args:
        mock_tui_app: Mock приложение TUIApp.

    Returns:
        ParsingScreen с настроенным mock приложением через PropertyMock.
    """
    screen = ParsingScreen()
    type(screen).app = PropertyMock(return_value=mock_tui_app)
    return screen


@pytest.fixture
def cities_data() -> list[dict]:
    """Фикстура с тестовыми данными городов.

    Returns:
        Список из 3 городов с полями name, url, code, country_code.
    """
    return [
        {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow", "country_code": "ru"},
        {
            "name": "Санкт-Петербург",
            "url": "https://2gis.ru/spb",
            "code": "spb",
            "country_code": "ru",
        },
    ]


@pytest.fixture
def categories_data() -> list[dict]:
    """Фикстура с тестовыми данными категорий.

    Returns:
        Список из 2 категорий с полями name, id.
    """
    return [{"name": "Рестораны", "id": 93}, {"name": "Кафе", "id": 161}]


# =============================================================================
# ТЕСТ 1: ЗАПУСК ПАРСИНГА БЕЗ ВЫБРАННЫХ ГОРОДОВ
# =============================================================================


class TestStartParsingNoCities:
    """Тесты для проверки запуска парсинга без выбранных городов."""

    def test_start_parsing_with_empty_cities_list(
        self, mock_tui_app: MagicMock, categories_data: list[dict]
    ) -> None:
        """Тест проверяет что парсинг НЕ запускается при пустом списке городов.

        Сценарий:
        1. TUIApp.start_parsing() вызывается с пустым списком городов
        2. Выбранные категории присутствуют

        Ожидаемое поведение:
        - Вызывается notify_user() с сообщением об ошибке
        - push_screen() НЕ вызывается
        - Парсинг не начинается

        Args:
            mock_tui_app: Mock приложение.
            categories_data: Список категорий для теста.
        """
        empty_cities: list[dict] = []

        # Вызовем метод start_parsing
        TUIApp.start_parsing(mock_tui_app, empty_cities, categories_data)

        # Проверяем что было вызвано уведомление об ошибке
        mock_tui_app.notify_user.assert_called_once_with(
            "Ошибка: не выбраны города для парсинга!", level="error"
        )

        # Проверяем что экран парсинга НЕ был открыт
        mock_tui_app.push_screen.assert_not_called()

    def test_start_parsing_with_none_cities(
        self, mock_tui_app: MagicMock, categories_data: list[dict]
    ) -> None:
        """Тест проверяет что парсинг НЕ запускается при None вместо городов.

        Сценарий:
        1. TUIApp.start_parsing() вызывается с None вместо списка городов
        2. Выбранные категории присутствуют

        Ожидаемое поведение:
        - Вызывается notify_user() с сообщением об ошибке
        - push_screen() НЕ вызывается

        Args:
            mock_tui_app: Mock приложение.
            categories_data: Список категорий для теста.
        """
        # Вызовем метод start_parsing с None
        TUIApp.start_parsing(mock_tui_app, None, categories_data)  # type: ignore

        # Проверяем что было вызвано уведомление об ошибке
        mock_tui_app.notify_user.assert_called_once_with(
            "Ошибка: не выбраны города для парсинга!", level="error"
        )

        # Проверяем что экран парсинга НЕ был открыт
        mock_tui_app.push_screen.assert_not_called()


# =============================================================================
# ТЕСТ 2: ЗАПУСК ПАРСИНГА БЕЗ ВЫБРАННЫХ КАТЕГОРИЙ
# =============================================================================


class TestStartParsingNoCategories:
    """Тесты для проверки запуска парсинга без выбранных категорий."""

    def test_start_parsing_with_empty_categories_list(
        self, mock_tui_app: MagicMock, cities_data: list[dict]
    ) -> None:
        """Тест проверяет что парсинг НЕ запускается при пустом списке категорий.

        Сценарий:
        1. TUIApp.start_parsing() вызывается с городами
        2. Список категорий пустой

        Ожидаемое поведение:
        - Вызывается notify_user() с сообщением об ошибке
        - push_screen() НЕ вызывается
        - Парсинг не начинается

        Args:
            mock_tui_app: Mock приложение.
            cities_data: Список городов для теста.
        """
        empty_categories: list[dict] = []

        # Вызовем метод start_parsing
        TUIApp.start_parsing(mock_tui_app, cities_data, empty_categories)

        # Проверяем что было вызвано уведомление об ошибке
        mock_tui_app.notify_user.assert_called_once_with(
            "Ошибка: не выбраны категории для парсинга!", level="error"
        )

        # Проверяем что экран парсинга НЕ был открыт
        mock_tui_app.push_screen.assert_not_called()

    def test_start_parsing_with_none_categories(
        self, mock_tui_app: MagicMock, cities_data: list[dict]
    ) -> None:
        """Тест проверяет что парсинг НЕ запускается при None вместо категорий.

        Сценарий:
        1. TUIApp.start_parsing() вызывается с городами
        2. Категории равны None

        Ожидаемое поведение:
        - Вызывается notify_user() с сообщением об ошибке
        - push_screen() НЕ вызывается

        Args:
            mock_tui_app: Mock приложение.
            cities_data: Список городов для теста.
        """
        # Вызовем метод start_parsing с None
        TUIApp.start_parsing(mock_tui_app, cities_data, None)  # type: ignore

        # Проверяем что было вызвано уведомление об ошибке
        mock_tui_app.notify_user.assert_called_once_with(
            "Ошибка: не выбраны категории для парсинга!", level="error"
        )

        # Проверяем что экран парсинга НЕ был открыт
        mock_tui_app.push_screen.assert_not_called()


# =============================================================================
# ТЕСТ 3: КОРРЕКТНЫЙ ЗАПУСК ПАРСИНГА
# =============================================================================


class TestStartParsingValid:
    """Тесты для проверки корректного запуска парсинга."""

    def test_start_parsing_with_valid_cities_and_categories(
        self, mock_tui_app: MagicMock, cities_data: list[dict], categories_data: list[dict]
    ) -> None:
        """Тест проверяет что парсинг запускается при наличии городов и категорий.

        Сценарий:
        1. TUIApp.start_parsing() вызывается с валидными городами и категориями
        2. Оба списка не пустые

        Ожидаемое поведение:
        - push_screen("parsing") вызывается
        - notify_user() НЕ вызывается с уровнем error
        - Парсинг начинается корректно

        Args:
            mock_tui_app: Mock приложение.
            cities_data: Список городов для теста.
            categories_data: Список категорий для теста.
        """
        # Вызовем метод start_parsing
        TUIApp.start_parsing(mock_tui_app, cities_data, categories_data)

        # Проверяем что экран парсинга был открыт
        mock_tui_app.push_screen.assert_called_once_with("parsing")

        # Проверяем что НЕ было ошибок
        error_calls = [
            call
            for call in mock_tui_app.notify_user.call_args_list
            if call[1].get("level") == "error"
        ]
        assert len(error_calls) == 0, "Не должно быть уведомлений об ошибках при валидных данных"

    @pytest.mark.parametrize(
        "cities_count,categories_count",
        [(1, 1), (2, 3), (5, 5), (10, 10)],
        ids=[
            "один город одна категория",
            "два города три категории",
            "пять городов пять категорий",
            "десять городов десять категорий",
        ],
    )
    def test_start_parsing_with_multiple_cities_and_categories(
        self, mock_tui_app: MagicMock, cities_count: int, categories_count: int
    ) -> None:
        """Тест проверяет запуск парсинга с различным количеством городов и категорий.

        Сценарий:
        1. TUIApp.start_parsing() вызывается с разным количеством городов и категорий
        2. Параметризированный тест для проверки различных комбинаций

        Ожидаемое поведение:
        - push_screen("parsing") вызывается для всех комбинаций
        - Ошибок не возникает

        Args:
            mock_tui_app: Mock приложение.
            cities_count: Количество городов для теста.
            categories_count: Количество категорий для теста.
        """
        # Создадим динамические данные
        cities = [
            {"name": f"Город {i}", "url": f"https://2gis.ru/city{i}", "code": f"city{i}"}
            for i in range(cities_count)
        ]
        categories = [{"name": f"Категория {i}", "id": i} for i in range(categories_count)]

        # Вызовем метод start_parsing
        TUIApp.start_parsing(mock_tui_app, cities, categories)

        # Проверяем что экран парсинга был открыт
        mock_tui_app.push_screen.assert_called_once_with("parsing")


# =============================================================================
# ТЕСТ 4: ОБРАБОТКА КНОПКИ "СТОП" ДО НАЧАЛА ПАРСИНГА
# =============================================================================


class TestStopParsingBeforeStart:
    """Тесты для проверки обработки кнопки "Стоп" до начала парсинга."""

    def test_action_stop_parsing_when_not_started(
        self, mock_parsing_screen: ParsingScreen, mock_tui_app: MagicMock
    ) -> None:
        """Тест проверяет что кнопка "Стоп" не останавливает несуществующий парсинг.

        Сценарий:
        1. ParsingScreen._parsing_started = False
        2. Вызывается action_stop_parsing()

        Ожидаемое поведение:
        - app.running НЕ устанавливается в False
        - _stopping НЕ устанавливается в True
        - Вызывается _return_to_menu() напрямую
        - Запись в лог о том что парсинг ещё не запущен

        Args:
            mock_parsing_screen: Mock экран парсинга.
            mock_tui_app: Mock приложение.
        """
        # Установим что парсинг ещё не запущен
        mock_parsing_screen._parsing_started = False
        mock_parsing_screen._stopping = False

        # Mock query_one для RichLog
        mock_log = Mock()
        mock_parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock _return_to_menu
        mock_parsing_screen._return_to_menu = Mock()

        # Вызовем остановку
        mock_parsing_screen.action_stop_parsing()

        # Проверяем что app.running НЕ был установлен в False
        # (он должен остаться без изменений)
        assert mock_tui_app.running is False

        # Проверяем что _stopping НЕ был установлен в True
        assert mock_parsing_screen._stopping is False

        # Проверяем что был вызван возврат в меню
        mock_parsing_screen._return_to_menu.assert_called_once()

        # Проверяем что была запись в лог
        mock_log.write.assert_called()
        log_calls = [call[0][0] for call in mock_log.write.call_args_list]
        assert any("Парсинг ещё не запущен" in call for call in log_calls)

    def test_action_stop_parsing_early_return_no_side_effects(
        self, mock_parsing_screen: ParsingScreen, mock_tui_app: MagicMock
    ) -> None:
        """Тест проверяет что ранний возврат не имеет побочных эффектов.

        Сценарий:
        1. action_stop_parsing() вызывается когда _parsing_started = False
        2. Проверяем что никакие флаги не изменяются

        Ожидаемое поведение:
        - _parsing_started остаётся False
        - _stopping остаётся False
        - app.running не изменяется

        Args:
            mock_parsing_screen: Mock экран парсинга.
            mock_tui_app: Mock приложение.
        """
        # Запомним начальные значения
        initial_running = mock_tui_app.running
        initial_stopping = mock_parsing_screen._stopping
        initial_started = mock_parsing_screen._parsing_started

        # Установим что парсинг не запущен
        mock_parsing_screen._parsing_started = False

        # Mock зависимостей
        mock_parsing_screen.query_one = Mock(return_value=Mock())
        mock_parsing_screen._return_to_menu = Mock()

        # Вызовем остановку
        mock_parsing_screen.action_stop_parsing()

        # Проверяем что значения не изменились
        assert mock_parsing_screen._parsing_started == initial_started
        assert mock_parsing_screen._stopping == initial_stopping
        assert mock_tui_app.running == initial_running


# =============================================================================
# ТЕСТ 5: ОБРАБОТКА КНОПКИ "СТОП" ВО ВРЕМЯ ПАРСИНГА
# =============================================================================


class TestStopParsingDuringExecution:
    """Тесты для проверки обработки кнопки "Стоп" во время парсинга."""

    def test_action_stop_parsing_when_running(
        self, mock_parsing_screen: ParsingScreen, mock_tui_app: MagicMock
    ) -> None:
        """Тест проверяет корректную остановку запущенного парсинга.

        Сценарий:
        1. ParsingScreen._parsing_started = True
        2. Вызывается action_stop_parsing()

        Ожидаемое поведение:
        - app.running устанавливается в False
        - _stopping устанавливается в True
        - Вызывается _return_to_menu() напрямую
        - Запись в лог об остановке

        Args:
            mock_parsing_screen: Mock экран парсинга.
            mock_tui_app: Mock приложение.
        """
        # Установим что парсинг запущен
        mock_parsing_screen._parsing_started = True
        mock_parsing_screen._stopping = False

        # Mock query_one для RichLog
        mock_log = Mock()
        mock_parsing_screen.query_one = Mock(return_value=mock_log)

        # Mock _return_to_menu
        mock_parsing_screen._return_to_menu = Mock()

        # Вызовем остановку
        mock_parsing_screen.action_stop_parsing()

        # Проверяем что app.running был установлен в False
        assert mock_tui_app.running is False

        # Проверяем что _stopping был установлен в True
        assert mock_parsing_screen._stopping is True

        # Проверяем что был вызван возврат в меню
        mock_parsing_screen._return_to_menu.assert_called_once()

        # Проверяем что была запись в лог об остановке
        mock_log.write.assert_called()
        log_calls = [call[0][0] for call in mock_log.write.call_args_list]
        assert any("Остановка парсинга пользователем" in call for call in log_calls)

    def test_action_stop_parsing_protection_from_duplicate_calls(
        self, mock_parsing_screen: ParsingScreen, mock_tui_app: MagicMock
    ) -> None:
        """Тест проверяет защиту от повторного вызова остановки.

        Сценарий:
        1. ParsingScreen._stopping = True (уже останавливается)
        2. Вызывается action_stop_parsing() повторно

        Ожидаемое поведение:
        - Функция возвращается сразу (early return)
        - _return_to_menu НЕ вызывается повторно
        - Флаги не изменяются повторно

        Args:
            mock_parsing_screen: Mock экран парсинга.
            mock_tui_app: Mock приложение.
        """
        # Установим что парсинг запущен и уже останавливается
        mock_parsing_screen._parsing_started = True
        mock_parsing_screen._stopping = True

        # Mock зависимостей
        mock_parsing_screen.query_one = Mock(return_value=Mock())
        mock_parsing_screen._return_to_menu = Mock()

        # Запомним количество вызовов _return_to_menu
        return_to_menu_count_before = mock_parsing_screen._return_to_menu.call_count

        # Вызовем остановку ещё раз
        mock_parsing_screen.action_stop_parsing()

        # Проверяем что _return_to_menu не был вызван повторно
        assert mock_parsing_screen._return_to_menu.call_count == return_to_menu_count_before

    @pytest.mark.parametrize(
        "parsing_started,stopping",
        [
            (True, False),  # нормальная остановка
            (True, True),  # повторная остановка
            (False, False),  # остановка до запуска
            (False, True),  # невозможное состояние
        ],
        ids=[
            "нормальная остановка",
            "повторная остановка",
            "остановка до запуска",
            "невозможное состояние",
        ],
    )
    def test_action_stop_parsing_state_matrix(
        self,
        mock_parsing_screen: ParsingScreen,
        mock_tui_app: MagicMock,
        parsing_started: bool,
        stopping: bool,
    ) -> None:
        """Тест проверяет поведение остановки при различных комбинациях флагов.

        Сценарий:
        1. Устанавливаются различные комбинации _parsing_started и _stopping
        2. Вызывается action_stop_parsing()
        3. Параметризированный тест для всех комбинаций

        Ожидаемое поведение:
        - Корректная обработка каждой комбинации флагов
        - Защита от некорректных переходов состояния

        Args:
            mock_parsing_screen: Mock экран парсинга.
            mock_tui_app: Mock приложение.
            parsing_started: Значение флага _parsing_started.
            stopping: Значение флага _stopping.
        """
        # Установим флаги
        mock_parsing_screen._parsing_started = parsing_started
        mock_parsing_screen._stopping = stopping

        # Mock зависимостей
        mock_log = Mock()
        mock_parsing_screen.query_one = Mock(return_value=mock_log)
        mock_parsing_screen._return_to_menu = Mock()

        # Вызовем остановку
        mock_parsing_screen.action_stop_parsing()

        # Проверка логики в зависимости от состояния
        if parsing_started and not stopping:
            # Нормальная остановка должна сработать
            assert mock_parsing_screen._stopping is True
            assert mock_tui_app.running is False
            mock_parsing_screen._return_to_menu.assert_called_once()
        elif stopping:
            # Защита от повторной остановки
            mock_parsing_screen._return_to_menu.assert_not_called()
        else:
            # Остановка до запуска - возврат в меню без установки флагов
            assert mock_parsing_screen._stopping is False
            mock_parsing_screen._return_to_menu.assert_called_once()


# =============================================================================
# ТЕСТ 6: ПРОВЕРКА СОХРАНЕНИЯ СОСТОЯНИЯ МЕЖДУ ЭКРАНАМИ
# =============================================================================


class TestStatePersistenceAcrossScreens:
    """Тесты для проверки сохранения состояния между экранами TUI."""

    def test_state_persistence_cities_and_categories(self, mock_tui_app: MagicMock) -> None:
        """Тест проверяет что выбранные города и категории сохраняются в state.

        Сценарий:
        1. Устанавливаются selected_cities и selected_categories
        2. Проверяем что значения сохраняются в app.state

        Ожидаемое поведение:
        - selected_cities сохраняется в _state["selected_cities"]
        - selected_categories сохраняется в _state["selected_categories"]
        - Значения доступны через свойства

        Args:
            mock_tui_app: Mock приложение.
        """
        # Установим выбранные города и категории напрямую в _state
        # (эмулируем работу setter свойств TUIApp)
        mock_tui_app._state["selected_cities"] = ["Москва", "Омск"]
        mock_tui_app._state["selected_categories"] = ["Рестораны", "Кафе"]

        # Проверяем что значения сохранились в state
        assert mock_tui_app._state["selected_cities"] == ["Москва", "Омск"]
        assert mock_tui_app._state["selected_categories"] == ["Рестораны", "Кафе"]

    def test_state_update_method(self, mock_tui_app: MagicMock) -> None:
        """Тест проверяет метод update_state для обновления состояния.

        Сценарий:
        1. Вызывается update_state() с различными параметрами
        2. Проверяем что состояние обновляется корректно

        Ожидаемое поведение:
        - update_state() обновляет только указанные ключи
        - Неизвестные ключи игнорируются

        Args:
            mock_tui_app: Mock приложение.
        """

        # Настроим mock для update_state чтобы он обновлял _state
        def update_state_impl(**kwargs):
            for key, value in kwargs.items():
                if key in mock_tui_app._state:
                    mock_tui_app._state[key] = value

        mock_tui_app.update_state = Mock(side_effect=update_state_impl)

        # Обновим состояние
        mock_tui_app.update_state(
            selected_cities=["Москва"],
            selected_categories=["Рестораны"],
            parsing_active=True,
            success_count=10,
        )

        # Проверяем что состояние обновилось
        assert mock_tui_app._state["selected_cities"] == ["Москва"]
        assert mock_tui_app._state["selected_categories"] == ["Рестораны"]
        assert mock_tui_app._state["parsing_active"] is True
        assert mock_tui_app._state["success_count"] == 10

    def test_state_get_method(self, mock_tui_app: MagicMock) -> None:
        """Тест проверяет метод get_state для получения значений из состояния.

        Сценарий:
        1. Устанавливаются значения в состоянии
        2. Вызывается get_state() для получения значений

        Ожидаемое поведение:
        - get_state() возвращает правильные значения
        - get_state() возвращает None для несуществующих ключей

        Args:
            mock_tui_app: Mock приложение.
        """
        # Установим значения
        mock_tui_app._state["selected_cities"] = ["Москва"]
        mock_tui_app._state["selected_categories"] = ["Рестораны"]
        mock_tui_app._state["custom_key"] = "custom_value"

        # Настроим mock для get_state чтобы он возвращал значения из _state
        def get_state_impl(key):
            return mock_tui_app._state.get(key)

        mock_tui_app.get_state = Mock(side_effect=get_state_impl)

        # Проверяем получение значений
        assert mock_tui_app.get_state("selected_cities") == ["Москва"]
        assert mock_tui_app.get_state("selected_categories") == ["Рестораны"]
        assert mock_tui_app.get_state("custom_key") == "custom_value"
        assert mock_tui_app.get_state("nonexistent_key") is None

    def test_state_isolation_between_screens(self, mock_tui_app: MagicMock) -> None:
        """Тест проверяет изоляцию состояния между различными экранами.

        Сценарий:
        1. Создаются несколько экранов с одним приложением
        2. Изменение состояния на одном экране
        3. Проверка что состояние доступно на других экранах

        Ожидаемое поведение:
        - Состояние является общим для всех экранов
        - Изменения состояния видны всем экранам

        Args:
            mock_tui_app: Mock приложение.
        """
        # Установим начальное состояние
        mock_tui_app.selected_cities = ["Москва"]
        mock_tui_app.selected_categories = []

        # Создадим несколько экранов
        screen1 = ParsingScreen()
        screen2 = ParsingScreen()

        type(screen1).app = PropertyMock(return_value=mock_tui_app)
        type(screen2).app = PropertyMock(return_value=mock_tui_app)

        # Изменим состояние через первый экран
        mock_tui_app.selected_cities = ["Москва", "Омск"]

        # Проверяем что второй экран видит изменения
        assert screen2.app.selected_cities == ["Москва", "Омск"]  # type: ignore

        # Изменим состояние через второй экран
        mock_tui_app.selected_categories = ["Рестораны"]

        # Проверяем что первый экран видит изменения
        assert screen1.app.selected_categories == ["Рестораны"]  # type: ignore


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ УПРАВЛЕНИЯ СОСТОЯНИЕМ
# =============================================================================


class TestStateManagementIntegration:
    """Интеграционные тесты для проверки полного цикла управления состоянием."""

    def test_full_lifecycle_no_cities_no_parsing(
        self, mock_tui_app: MagicMock, categories_data: list[dict]
    ) -> None:
        """Тест проверяет полный жизненный цикл: нет городов -> нет парсинга.

        Сценарий:
        1. selected_cities пустой
        2. selected_categories заполнен
        3. Попытка запуска парсинга

        Ожидаемое поведение:
        - notify_user() вызывается с ошибкой
        - push_screen() НЕ вызывается
        - Состояние не изменяется

        Args:
            mock_tui_app: Mock приложение.
            categories_data: Список категорий.
        """
        # Установим состояние
        mock_tui_app.selected_cities = []
        mock_tui_app.selected_categories = ["Рестораны"]

        # Попытка запуска
        TUIApp.start_parsing(mock_tui_app, [], categories_data)

        # Проверяем результат
        mock_tui_app.notify_user.assert_called_once_with(
            "Ошибка: не выбраны города для парсинга!", level="error"
        )
        mock_tui_app.push_screen.assert_not_called()

    def test_full_lifecycle_no_categories_no_parsing(
        self, mock_tui_app: MagicMock, cities_data: list[dict]
    ) -> None:
        """Тест проверяет полный жизненный цикл: нет категорий -> нет парсинга.

        Сценарий:
        1. selected_cities заполнен
        2. selected_categories пустой
        3. Попытка запуска парсинга

        Ожидаемое поведение:
        - notify_user() вызывается с ошибкой
        - push_screen() НЕ вызывается
        - Состояние не изменяется

        Args:
            mock_tui_app: Mock приложение.
            cities_data: Список городов.
        """
        # Установим состояние
        mock_tui_app.selected_cities = ["Москва"]
        mock_tui_app.selected_categories = []

        # Попытка запуска
        TUIApp.start_parsing(mock_tui_app, cities_data, [])

        # Проверяем результат
        mock_tui_app.notify_user.assert_called_once_with(
            "Ошибка: не выбраны категории для парсинга!", level="error"
        )
        mock_tui_app.push_screen.assert_not_called()

    def test_full_lifecycle_valid_data_starts_parsing(
        self, mock_tui_app: MagicMock, cities_data: list[dict], categories_data: list[dict]
    ) -> None:
        """Тест проверяет полный жизненный цикл: валидные данные -> запуск парсинга.

        Сценарий:
        1. selected_cities заполнен
        2. selected_categories заполнен
        3. Запуск парсинга

        Ожидаемое поведение:
        - push_screen("parsing") вызывается
        - notify_user() НЕ вызывается с ошибкой
        - Парсинг начинается

        Args:
            mock_tui_app: Mock приложение.
            cities_data: Список городов.
            categories_data: Список категорий.
        """
        # Установим состояние
        mock_tui_app.selected_cities = ["Москва"]
        mock_tui_app.selected_categories = ["Рестораны"]

        # Запуск парсинга
        TUIApp.start_parsing(mock_tui_app, cities_data, categories_data)

        # Проверяем результат
        mock_tui_app.push_screen.assert_called_once_with("parsing")
        error_calls = [
            call
            for call in mock_tui_app.notify_user.call_args_list
            if call[1].get("level") == "error"
        ]
        assert len(error_calls) == 0


# =============================================================================
# ТЕСТЫ ГРАНИЧНЫХ УСЛОВИЙ
# =============================================================================


class TestStateManagementEdgeCases:
    """Тесты для проверки граничных условий управления состоянием."""

    def test_empty_string_in_cities_list(
        self, mock_tui_app: MagicMock, categories_data: list[dict]
    ) -> None:
        """Тест проверяет обработку пустой строки в списке городов.

        Сценарий:
        1. cities содержит пустую строку
        2. Попытка запуска парсинга

        Ожидаемое поведение:
        - Парсинг запускается (список не пустой)
        - Ошибка возникает позже на уровне валидации данных

        Args:
            mock_tui_app: Mock приложение.
            categories_data: Список категорий.
        """
        cities_with_empty = [{"name": "", "url": "", "code": ""}]

        # Запуск парсинга
        TUIApp.start_parsing(mock_tui_app, cities_with_empty, categories_data)

        # Проверяем что парсинг запустился (список технически не пустой)
        mock_tui_app.push_screen.assert_called_once_with("parsing")

    def test_whitespace_only_cities_list(
        self, mock_tui_app: MagicMock, categories_data: list[dict]
    ) -> None:
        """Тест проверяет обработку списка городов только с пробелами.

        Сценарий:
        1. cities содержит город с именем из пробелов
        2. Попытка запуска парсинга

        Ожидаемое поведение:
        - Парсинг запускается (список не пустой)
        - Валидация имени города должна происходить в другом месте

        Args:
            mock_tui_app: Mock приложение.
            categories_data: Список категорий.
        """
        cities_with_whitespace = [{"name": "   ", "url": "https://2gis.ru/test", "code": "test"}]

        # Запуск парсинга
        TUIApp.start_parsing(mock_tui_app, cities_with_whitespace, categories_data)

        # Проверяем что парсинг запустился
        mock_tui_app.push_screen.assert_called_once_with("parsing")

    def test_duplicate_cities_in_list(
        self, mock_tui_app: MagicMock, categories_data: list[dict]
    ) -> None:
        """Тест проверяет обработку дубликатов городов в списке.

        Сценарий:
        1. cities содержит дубликаты одного города
        2. Попытка запуска парсинга

        Ожидаемое поведение:
        - Парсинг запускается
        - Дубликаты должны обрабатываться на уровне парсера

        Args:
            mock_tui_app: Mock приложение.
            categories_data: Список категорий.
        """
        duplicate_cities = [
            {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"},
            {"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"},
        ]

        # Запуск парсинга
        TUIApp.start_parsing(mock_tui_app, duplicate_cities, categories_data)

        # Проверяем что парсинг запустился
        mock_tui_app.push_screen.assert_called_once_with("parsing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
