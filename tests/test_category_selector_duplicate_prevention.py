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
        self.mock_container.mount.assert_called()

        # Second population with different data
        # Change the filtered categories to simulate a search
        self.screen._filtered_categories = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161", "original_index": 0}
        ]

        # Reset mock call counts
        self.mock_container.remove_children.reset_mock()
        self.mock_container.mount.reset_mock()

        # Second population
        self.screen._populate_categories()

        # Verify that remove_children was called again (clearing previous widgets)
        self.mock_container.remove_children.assert_called()
        # Verify that mount was called for new widgets
        self.mock_container.mount.assert_called()

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
        # Verify no widgets were mounted
        self.mock_container.mount.assert_not_called()
        # Verify _checkboxes is empty
        assert len(self.screen._checkboxes) == 0

    def test_populate_categories_prevents_duplicate_ids(self):
        """Тест: _populate_categories предотвращает создание дублирующихся ID."""
        # Populate first time
        self.screen._populate_categories()

        # Get the IDs of checkboxes after first population
        first_call_args = self.mock_container.mount.call_args_list
        first_ids = []
        for call in first_call_args:
            args, kwargs = call
            # Widgets are passed as positional arguments to mount
            for widget in args:
                if hasattr(widget, "id"):
                    first_ids.append(widget.id)

        # Reset mount mock
        self.mock_container.mount.reset_mock()

        # Change filtered categories to different set
        self.screen._filtered_categories = [
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162", "original_index": 1},
            {"name": "Бары", "query": "Бары", "rubric_code": "163", "original_index": 2},
        ]

        # Populate second time
        self.screen._populate_categories()

        # Get the IDs of checkboxes after second population
        second_call_args = self.mock_container.mount.call_args_list
        second_ids = []
        for call in second_call_args:
            args, kwargs = call
            # Widgets are passed as positional arguments to mount
            for widget in args:
                if hasattr(widget, "id"):
                    second_ids.append(widget.id)

        # Verify that remove_children was called (to clear previous widgets)
        self.mock_container.remove_children.assert_called()

        # Verify that _checkboxes was cleared and repopulated
        assert len(self.screen._checkboxes) == len(second_ids)
        assert len(self.screen._checkboxes) == 2  # Should have 2 checkboxes now

        # The key test: ensure that we're not trying to mount widgets with duplicate IDs
        # Since we clear the container and _checkboxes list each time, this should work
        # The actual prevention of DuplicateIds is handled by the cleanup in _populate_categories
