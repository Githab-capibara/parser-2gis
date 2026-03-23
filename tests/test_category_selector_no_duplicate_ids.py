"""
Unit тест для проверки отсутствия DuplicateIds ошибки в CategorySelectorScreen.

Проверяет, что при фильтрации категорий не возникает дубликатов original_index
у Checkbox виджетов. Это предотвращает ошибку DuplicateIds в Textual.
"""

from unittest.mock import Mock, PropertyMock

from textual.containers import ScrollableContainer

from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class MockApp:
    def __init__(self):
        self.selected_categories = []

    def get_categories(self):
        return [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
            {"name": "Бары", "query": "Бары", "rubric_code": "163"},
            {"name": "Столовые", "query": "Столовые", "rubric_code": "164"},
            {"name": "Пиццерии", "query": "Пиццерии", "rubric_code": "165"},
        ]


class TestCategorySelectorNoDuplicateIds:
    """Тесты для предотвращения DuplicateIds ошибки."""

    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.screen = CategorySelectorScreen()
        # Create a mock app object
        mock_app = Mock()
        mock_app.get_categories.return_value = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
            {"name": "Бары", "query": "Бары", "rubric_code": "163"},
            {"name": "Столовые", "query": "Столовые", "rubric_code": "164"},
            {"name": "Пиццерии", "query": "Пиццерии", "rubric_code": "165"},
        ]
        mock_app.selected_categories = set()

        # Mock the app property using PropertyMock
        type(self.screen).app = PropertyMock(return_value=mock_app)

        # Mock the query_one method to return a mock container
        self.mock_container = Mock(spec=ScrollableContainer)
        self.screen.query_one = Mock(return_value=self.mock_container)

        # Initialize categories
        self.screen._load_categories()

    def test_initial_populate_no_duplicate_original_index(self):
        """Тест: начальная загрузка не создаёт дубликатов original_index."""
        self.screen._populate_categories()

        # Проверить, что все original_index уникальны
        original_indices = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(original_indices) == len(set(original_indices))
        assert len(original_indices) == 5  # 5 категорий

    def test_filter_then_populate_no_duplicates(self):
        """Тест: фильтрация с последующим _populate_categories не создаёт дубликатов."""
        # Первая загрузка
        self.screen._populate_categories()

        # Фильтрация (только "Кафе")
        self.screen._filtered_categories = [
            cat for cat in self.screen._categories if "кафе" in cat.get("name", "").lower()
        ]

        # Вторая загрузка
        self.screen._populate_categories()
        second_indices = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]

        # Проверить уникальность
        assert len(second_indices) == len(set(second_indices))
        assert len(second_indices) == 1  # Только "Кафе"

        # Проверить, что original_index сохранился корректно
        assert second_indices[0] == 0  # "Кафе" имеет original_index = 0

    def test_multiple_filter_cycles_no_duplicates(self):
        """Тест: многократная фильтрация не создаёт дубликатов."""
        # Цикл 1: Фильтрация по "а"
        self.screen._filtered_categories = [
            cat for cat in self.screen._categories if "а" in cat.get("name", "").lower()
        ]
        self.screen._populate_categories()
        indices_1 = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(indices_1) == len(set(indices_1))

        # Цикл 2: Очистка фильтра
        self.screen._filtered_categories = self.screen._categories.copy()
        self.screen._populate_categories()
        indices_2 = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(indices_2) == len(set(indices_2))
        assert len(indices_2) == 5

        # Цикл 3: Фильтрация по "р"
        self.screen._filtered_categories = [
            cat for cat in self.screen._categories if "р" in cat.get("name", "").lower()
        ]
        self.screen._populate_categories()
        indices_3 = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(indices_3) == len(set(indices_3))

    def test_filter_by_letter_k(self):
        """Тест: фильтрация по букве "к" работает корректно."""
        self.screen._filtered_categories = [
            cat for cat in self.screen._categories if "к" in cat.get("name", "").lower()
        ]
        self.screen._populate_categories()

        # Проверить количество (только "Кафе" содержит "к")
        assert len(self.screen._checkboxes) == 1

        # Проверить уникальность original_index
        indices = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(indices) == len(set(indices))

        # Проверить, что original_index соответствуют отфильтрованным категориям
        expected_indices = {cat["original_index"] for cat in self.screen._filtered_categories}
        assert set(indices) == expected_indices

    def test_clear_filter_restores_all_categories(self):
        """Тест: очистка фильтра восстанавливает все категории."""
        # Фильтрация по "о" (Рестораны, Столовые)
        self.screen._filtered_categories = [
            cat for cat in self.screen._categories if "о" in cat.get("name", "").lower()
        ]
        self.screen._populate_categories()
        assert len(self.screen._checkboxes) == 2

        # Очистка
        self.screen._filtered_categories = self.screen._categories.copy()
        self.screen._populate_categories()

        # Проверить количество
        assert len(self.screen._checkboxes) == 5

        # Проверить уникальность
        indices = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(indices) == len(set(indices))
        assert set(indices) == {0, 1, 2, 3, 4}
