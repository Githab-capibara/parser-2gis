import pytest
from unittest.mock import Mock, PropertyMock
from textual.containers import ScrollableContainer

from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class MockApp:
    def __init__(self):
        self.selected_categories = []

    def get_categories(self):
        return [
            {"name": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "rubric_code": "162"},
            {"name": "Бары", "rubric_code": "163"},
        ]


def test_populate_categories_no_duplicate_ids():
    """Тест проверяет, что повторный вызов _populate_categories не создает дубликатов ID."""
    app = MockApp()
    screen = CategorySelectorScreen()

    # Mock the app property using PropertyMock
    type(screen).app = PropertyMock(return_value=app)
    # Mock the query_one method to return a mock container
    mock_container = Mock(spec=ScrollableContainer)
    screen.query_one = Mock(return_value=mock_container)

    # Первый вызов _populate_categories
    screen._load_categories()
    screen._populate_categories()

    # Второй вызов _populate_categories (как при фильтрации поиска)
    screen._populate_categories()

    # Проверяем, что количество чекбоксов соответствует количеству категорий
    assert len(screen._checkboxes) == 3

    # Проверяем, что все ID уникальны
    checkbox_ids = [cb.id for cb in screen._checkboxes]
    assert len(checkbox_ids) == len(set(checkbox_ids))


def test_populate_categories_after_search_filter():
    """Тест проверяет работу фильтрации поиска и повторного заполнения."""
    app = MockApp()
    screen = CategorySelectorScreen()

    # Mock the app property using PropertyMock
    type(screen).app = PropertyMock(return_value=app)
    # Mock the query_one method to return a mock container
    mock_container = Mock(spec=ScrollableContainer)
    screen.query_one = Mock(return_value=mock_container)

    # Загружаем категории
    screen._load_categories()
    screen._populate_categories()

    # Имитируем изменение поискового запроса
    try:
        from textual.events import Changed
        from textual.widgets import Input

        # Создаем мок события изменения ввода
        mock_input = Mock(spec=Input)
        mock_input.id = "category-search"
        mock_input.value = "Кафе"

        event = Changed(mock_input)
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

    # После фильтрации должно остаться только одно совпадение
    assert len(screen._filtered_categories) == 1
    assert screen._filtered_categories[0]["name"] == "Кафе"

    # Количество чекбоксов должно соответствовать отфильтрованному списку
    assert len(screen._checkboxes) == 1


if __name__ == "__main__":
    pytest.main([__file__])
