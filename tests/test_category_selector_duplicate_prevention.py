"""
Тест для предотвращения DuplicateIds ошибки в CategorySelectorScreen.
Проверяет, что метод _populate_categories правильно очищает старые виджеты
перед добавлением новых, чтобы избежать дублирования ID.
"""

from unittest.mock import Mock, PropertyMock

from textual.containers import ScrollableContainer

# Import the screen class
try:
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen
except ImportError:
    # Fallback for testing environment
    import sys

    sys.path.insert(0, "/home/d/parser-2gis")
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class TestDuplicateIdPrevention:
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
        ]
        mock_app.selected_categories = set()

        # Mock the app property using PropertyMock
        type(self.screen).app = PropertyMock(return_value=mock_app)

        # Mock the query_one method to return a mock container
        self.mock_container = Mock(spec=ScrollableContainer)
        self.screen.query_one = Mock(return_value=self.mock_container)

        # Initialize categories
        self.screen._load_categories()

    def test_populate_categories_clears_previous_widgets(self):
        """Тест: _populate_categories очищает предыдущие чекбоксы перед добавлением новых."""
        # First population
        self.screen._populate_categories()

        # Verify that remove_children was called on the container
        self.mock_container.remove_children.assert_called()
        self.mock_container.mount_all.assert_called()

        # Second population with different data
        # Change the filtered categories to simulate a search
        self.screen._filtered_categories = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161", "original_index": 0}
        ]

        # Reset mock call counts
        self.mock_container.remove_children.reset_mock()
        self.mock_container.mount_all.reset_mock()

        # Second population
        self.screen._populate_categories()

        # Verify that remove_children was called again (clearing previous widgets)
        self.mock_container.remove_children.assert_called()
        # Verify that mount_all was called for new widgets
        self.mock_container.mount_all.assert_called()

        # Ensure _checkboxes list was cleared and repopulated
        assert len(self.screen._checkboxes) == 1

    def test_populate_categories_with_empty_filter(self):
        """Тест: _populate_categories работает корректно с пустым фильтром."""
        # Set empty filtered categories
        self.screen._filtered_categories = []

        # This should not raise any exceptions
        self.screen._populate_categories()

        # Verify container was cleared
        self.mock_container.remove_children.assert_called()
        # Verify no widgets were mounted (mount_all not called with empty list)
        self.mock_container.mount_all.assert_not_called()
        # Verify _checkboxes is empty
        assert len(self.screen._checkboxes) == 0

    def test_populate_categories_prevents_duplicate_ids(self):
        """Тест: _populate_categories предотвращает создание дублирующихся ID."""
        # Populate first time
        self.screen._populate_categories()

        # Get the original_index values of checkboxes after first population
        first_original_indices = [
            getattr(cb, "original_index", None) for cb in self.screen._checkboxes
        ]

        # Reset mock call counts
        self.mock_container.remove_children.reset_mock()
        self.mock_container.mount_all.reset_mock()

        # Change filtered categories to different set
        self.screen._filtered_categories = [
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162", "original_index": 1},
            {"name": "Бары", "query": "Бары", "rubric_code": "163", "original_index": 2},
        ]

        # Populate second time
        self.screen._populate_categories()

        # Get the original_index values of checkboxes after second population
        second_original_indices = [
            getattr(cb, "original_index", None) for cb in self.screen._checkboxes
        ]

        # Verify that remove_children was called (to clear previous widgets)
        self.mock_container.remove_children.assert_called()

        # Verify that _checkboxes was cleared and repopulated
        assert len(self.screen._checkboxes) == len(second_original_indices)
        assert len(self.screen._checkboxes) == 2  # Should have 2 checkboxes now

        # Verify all original_index values are unique within each population
        assert len(first_original_indices) == len(set(first_original_indices))
        assert len(second_original_indices) == len(set(second_original_indices))
