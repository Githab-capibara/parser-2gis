import pytest
from unittest.mock import Mock
from textual.app import App

from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class MockApp(App):
    def __init__(self):
        super().__init__()
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
    screen._bind_methods()  # Привязываем методы экрана

    # Имитируем монтирование экрана
    screen.app = app

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
    screen._bind_methods()

    # Имитируем монтирование экрана
    screen.app = app

    # Загружаем категории
    screen._load_categories()
    screen._populate_categories()

    # Имитируем изменение поискового запроса
    from textual.events import Changed
    from textual.widgets import Input

    # Создаем мок события изменения ввода
    mock_input = Mock(spec=Input)
    mock_input.id = "category-search"
    mock_input.value = "Кафе"

    event = Changed(mock_input)
    screen.on_input_changed(event)

    # После фильтрации должно остаться только одно совпадение
    assert len(screen._filtered_categories) == 1
    assert screen._filtered_categories[0]["name"] == "Кафе"

    # Количество чекбоксов должно соответствовать отфильтрованному списку
    assert len(screen._checkboxes) == 1


if __name__ == "__main__":
    pytest.main([__file__])
