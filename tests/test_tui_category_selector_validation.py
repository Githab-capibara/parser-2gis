"""
Тест для проверки обработки ошибки при нажатии "Далее" без выбранных городов.

Проверяет:
1. CategorySelectorScreen.on_button_pressed("next") - проверка что города выбраны
2. При отсутствии выбранных городов - показ уведомления и возврат в меню
3. Отсутствие зависания интерфейса при ошибке
"""

from unittest.mock import Mock, PropertyMock

import pytest

from parser_2gis.tui_textual.app import TUIApp
from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class MockAppForCategorySelector:
    """Mock приложение для тестирования CategorySelectorScreen."""

    def __init__(
        self, selected_cities: list | None = None, selected_categories: list | None = None
    ):
        self.selected_cities = selected_cities or []
        self.selected_categories = selected_categories or []
        self._notifications = []

    def get_categories(self):
        """Получить список категорий."""
        return [
            {"name": "Кафе", "rubric_code": "161", "id": 161},
            {"name": "Рестораны", "rubric_code": "162", "id": 162},
            {"name": "Бары", "rubric_code": "163", "id": 163},
        ]

    def notify(self, message: str, timeout: int = 5) -> None:
        """Mock метод notify."""
        self._notifications.append({"message": message, "timeout": timeout})

    def notify_user(self, message: str, level: str = "info") -> None:
        """Mock метод notify_user."""
        self._notifications.append({"message": message, "level": level})

    def push_screen(self, screen_name: str) -> None:
        """Mock метод push_screen."""
        pass

    def pop_screen(self) -> None:
        """Mock метод pop_screen."""
        pass


def test_category_selector_next_button_without_cities():
    """Тест проверяет, что нажатие 'Далее' без выбранных городов не вызывает зависания.

    Ожидается:
    1. Показ уведомления об ошибке
    2. Логирование ошибки
    3. Отсутствие перехода на экран парсинга
    """
    # Создать приложение БЕЗ выбранных городов
    app = MockAppForCategorySelector(selected_cities=[], selected_categories=[])
    screen = CategorySelectorScreen()

    # Настроить mock для app через PropertyMock
    type(screen).app = PropertyMock(return_value=app)

    # Mock query_one для предотвращения ошибок
    mock_query_result = Mock()
    screen.query_one = Mock(return_value=mock_query_result)

    # Загрузить категории (теперь будет использовать mock app)
    # Пропускаем _load_categories так как он требует активный app контекст
    screen._categories = app.get_categories()
    screen._filtered_categories = screen._categories.copy()
    screen._id_to_index = {str(i): i for i in range(len(screen._categories))}

    # Создать mock для кнопки
    mock_button = Mock()
    mock_button.id = "next"

    # Создать mock события
    mock_event = Mock()
    mock_event.button = mock_button

    # Вызвать обработчик нажатия кнопки
    screen.on_button_pressed(mock_event)

    # Проверить что было показано уведомление об ошибке
    error_notifications = [
        n for n in app._notifications if "Сначала выберите города" in n.get("message", "")
    ]
    assert len(error_notifications) > 0, (
        "Должно быть показано уведомление о необходимости выбрать города"
    )

    # Проверить что было записано в лог
    error_logs = [
        n
        for n in app._notifications
        if "Попытка запуска без выбранных городов" in n.get("message", "")
    ]
    assert len(error_logs) > 0, "Должна быть запись в лог об ошибке"


def test_category_selector_next_button_with_cities():
    """Тест проверяет, что нажатие 'Далее' с выбранными городами работает корректно.

    Ожидается:
    1. Сохранение выбранных категорий
    2. Переход на экран парсинга
    """
    # Создать приложение С выбранными городами
    app = MockAppForCategorySelector(
        selected_cities=[{"name": "Омск", "code": "omsk"}], selected_categories=[]
    )
    screen = CategorySelectorScreen()

    # Настроить mock для app через PropertyMock
    type(screen).app = PropertyMock(return_value=app)

    # Mock query_one для предотвращения ошибок
    mock_query_result = Mock()
    screen.query_one = Mock(return_value=mock_query_result)

    # Загрузить категории (теперь будет использовать mock app)
    screen._categories = app.get_categories()
    screen._filtered_categories = screen._categories.copy()
    screen._id_to_index = {str(i): i for i in range(len(screen._categories))}

    # Выбрать категорию
    screen._selected_indices.add(0)  # Выбрать первую категорию

    # Создать mock для кнопки
    mock_button = Mock()
    mock_button.id = "next"

    # Создать mock события
    mock_event = Mock()
    mock_event.button = mock_button

    # Mock push_screen для отслеживания вызова
    app.push_screen = Mock()

    # Вызвать обработчик нажатия кнопки
    screen.on_button_pressed(mock_event)

    # Проверить что категории были сохранены
    assert len(app.selected_categories) > 0, "Категории должны быть сохранены"

    # Проверить что был вызван переход на экран парсинга
    app.push_screen.assert_called_once_with("parsing")

    # Проверить что уведомление об ошибке НЕ было показано
    error_notifications = [
        n for n in app._notifications if "Сначала выберите города" in n.get("message", "")
    ]
    assert len(error_notifications) == 0, "Не должно быть уведомления об ошибке"


def test_tui_app_start_parsing_without_cities():
    """Тест проверяет, что TUIApp.start_parsing без городов возвращает в меню.

    Ожидается:
    1. Показ уведомления об ошибке
    2. Вызов switch_to_main_menu
    """
    # Создать mock приложение
    app = Mock(spec=TUIApp)
    app._running = False
    app._started_at = None
    app._parser = None
    app._file_logger = None
    app._log_file = None
    app._last_notification = None
    app._state = {"selected_cities": [], "selected_categories": [], "parsing_active": False}
    app.notify_user = Mock()
    app.call_from_thread = Mock()
    app.switch_to_main_menu = Mock()

    # Вызвать start_parsing с пустым списком городов
    TUIApp.start_parsing(app, cities=[], categories=[{"name": "Кафе"}])

    # Проверить что было показано уведомление об ошибке
    app.notify_user.assert_called_once_with(
        "Ошибка: не выбраны города для парсинга!", level="error"
    )

    # Проверить что был вызван возврат в главное меню
    app.call_from_thread.assert_called_with(app.switch_to_main_menu)


def test_tui_app_start_parsing_without_categories():
    """Тест проверяет, что TUIApp.start_parsing без категорий возвращает в меню.

    Ожидается:
    1. Показ уведомления об ошибке
    2. Вызов switch_to_main_menu
    """
    # Создать mock приложение
    app = Mock(spec=TUIApp)
    app._running = False
    app._started_at = None
    app._parser = None
    app._file_logger = None
    app._log_file = None
    app._last_notification = None
    app._state = {
        "selected_cities": [{"name": "Омск"}],
        "selected_categories": [],
        "parsing_active": False,
    }
    app.notify_user = Mock()
    app.call_from_thread = Mock()
    app.switch_to_main_menu = Mock()

    # Вызвать start_parsing с пустым списком категорий
    TUIApp.start_parsing(app, cities=[{"name": "Омск"}], categories=[])

    # Проверить что было показано уведомление об ошибке
    app.notify_user.assert_called_once_with(
        "Ошибка: не выбраны категории для парсинга!", level="error"
    )

    # Проверить что был вызван возврат в главное меню
    app.call_from_thread.assert_called_with(app.switch_to_main_menu)


if __name__ == "__main__":
    pytest.main([__file__])
