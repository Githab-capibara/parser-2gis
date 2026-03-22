"""
Тест для проверки уникальности ID виджетов в CategorySelectorScreen
при фильтрации категорий.
"""

from unittest.mock import Mock, PropertyMock

from textual.app import App
from textual.containers import ScrollableContainer

from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class MockApp(App):
    """Мок-приложение для тестирования."""

    def __init__(self):
        super().__init__()
        self.selected_categories = []
        self.categories_data = [
            {"name": "Кафе", "rubric_code": "161"},
            {"name": "Ресторан", "rubric_code": "162"},
            {"name": "Бар", "rubric_code": "163"},
            {"name": "Кафе-бар", "rubric_code": "164"},
            {"name": "Ресторан быстрого питания", "rubric_code": "165"},
        ]

    def get_categories(self):
        """Возвращает тестовые данные категорий."""
        return self.categories_data


def test_unique_ids_during_filtering():
    """Проверяет, что ID виджетов остаются уникальными при фильтрации."""
    app = MockApp()
    screen = CategorySelectorScreen()

    # Привязываем экран к приложению через PropertyMock
    type(screen).app = PropertyMock(return_value=app)
    # Mock the query_one method to return a mock container
    mock_container = Mock(spec=ScrollableContainer)
    screen.query_one = Mock(return_value=mock_container)

    # Имитируем монтирование экрана
    screen._load_categories()
    screen._populate_categories()

    # Получаем список чекбоксов и их ID
    initial_checkboxes = screen._checkboxes.copy()
    initial_ids = [cb.id for cb in initial_checkboxes]

    # Проверяем, что все ID уникальны в начальном состоянии
    assert len(initial_ids) == len(set(initial_ids)), (
        f"Дублирующиеся ID в начальном состоянии: {initial_ids}"
    )

    # Имитируем изменение поискового запроса (фильтрация)
    try:
        from textual.events import Changed
        from textual.widgets import Input

        mock_input = Input()
        mock_input.id = "category-search"
        mock_input.value = "кафе"  # Должно найти "Кафе" и "Кафе-бар"

        event = Changed(mock_input, value="кафе")

        # Обрабатываем событие изменения ввода
        screen.on_input_changed(event)
    except ImportError:
        # Если textual не доступен, имитируем эффект фильтрации напрямую
        query = "кафе"
        if not query:
            screen._filtered_categories = screen._categories.copy()
        else:
            screen._filtered_categories = [
                cat for cat in screen._categories if query in cat.get("name", "").lower()
            ]
        # Обновляем интерфейс после фильтрации
        screen._populate_categories()

    # Получаем список чекбоксов после фильтрации
    filtered_checkboxes = screen._checkboxes.copy()
    filtered_ids = [cb.id for cb in filtered_checkboxes]

    # Проверяем, что все ID уникальны после фильтрации
    assert len(filtered_ids) == len(set(filtered_ids)), (
        f"Дублирующиеся ID после фильтрации: {filtered_ids}"
    )

    # Проверяем, что количество чекбоксов соответствует ожидаемому
    # Должно быть 2: "Кафе" и "Кафе-бар"
    assert len(filtered_checkboxes) == 2, (
        f"Ожидалось 2 чекбокса после фильтрации, получено {len(filtered_checkboxes)}"
    )


def test_unique_ids_after_multiple_filters():
    """Проверяет уникальность ID после множественных фильтраций."""
    app = MockApp()
    screen = CategorySelectorScreen()
    type(screen).app = PropertyMock(return_value=app)
    # Mock the query_one method to return a mock container
    mock_container = Mock(spec=ScrollableContainer)
    screen.query_one = Mock(return_value=mock_container)

    # Инициализируем экран
    screen._load_categories()

    # Последовательно применяем разные фильтры
    filters = ["кафе", "бар", "ресторан", ""]

    for filter_text in filters:
        try:
            from textual.events import Changed
            from textual.widgets import Input

            mock_input = Input()
            mock_input.id = "category-search"
            mock_input.value = filter_text

            event = Changed(mock_input, value=filter_text)
            screen.on_input_changed(event)
        except ImportError:
            # Если textual не доступен, имитируем эффект фильтрации напрямую
            query = filter_text
            if not query:
                screen._filtered_categories = screen._categories.copy()
            else:
                screen._filtered_categories = [
                    cat for cat in screen._categories if query in cat.get("name", "").lower()
                ]
            # Обновляем интерфейс после фильтрации
            screen._populate_categories()

        # Проверяем уникальность ID после каждого фильтра
        current_ids = [cb.id for cb in screen._checkboxes]
        assert len(current_ids) == len(set(current_ids)), (
            f"Дублирующиеся ID после фильтра '{filter_text}': {current_ids}"
        )


if __name__ == "__main__":
    test_unique_ids_during_filtering()
    test_unique_ids_after_multiple_filters()
    print("Все тесты прошли успешно!")
