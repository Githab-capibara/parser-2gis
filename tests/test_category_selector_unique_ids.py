"""
Тест для проверки уникальности ID виджетов в CategorySelectorScreen
при фильтрации категорий.
"""

from textual.app import App
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

    # Привязываем экран к приложению
    screen.bind_app(app)

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
    # Создаем мок-событие изменения ввода
    from textual.events import Changed
    from textual.widgets import Input

    mock_input = Input()
    mock_input.id = "category-search"
    mock_input.value = "кафе"  # Должно найти "Кафе" и "Кафе-бар"

    event = Changed(mock_input, value="кафе")

    # Обрабатываем событие изменения ввода
    screen.on_input_changed(event)

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
    screen.bind_app(app)

    # Инициализируем экран
    screen._load_categories()

    # Последовательно применяем разные фильтры
    filters = ["кафе", "бар", "ресторан", ""]

    for filter_text in filters:
        from textual.events import Changed
        from textual.widgets import Input

        mock_input = Input()
        mock_input.id = "category-search"
        mock_input.value = filter_text

        event = Changed(mock_input, value=filter_text)
        screen.on_input_changed(event)

        # Проверяем уникальность ID после каждого фильтра
        current_ids = [cb.id for cb in screen._checkboxes]
        assert len(current_ids) == len(set(current_ids)), (
            f"Дублирующиеся ID после фильтра '{filter_text}': {current_ids}"
        )


if __name__ == "__main__":
    test_unique_ids_during_filtering()
    test_unique_ids_after_multiple_filters()
    print("Все тесты прошли успешно!")
