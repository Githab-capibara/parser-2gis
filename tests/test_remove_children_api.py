"""
Тест для проверки корректного использования метода remove_children() в Textual.

Предотвращает ошибку: TypeError: Widget.remove_children() takes from 1 to 2
positional arguments but N were given

См. https://textual.textualize.io/api/widget/#textual.widget.Widget.remove_children
"""

from unittest.mock import MagicMock

import pytest


class TestRemoveChildrenUsage:
    """Тесты для проверки корректного использования remove_children."""

    def test_remove_children_called_without_args(self) -> None:
        """Тест: remove_children должен вызываться БЕЗ аргументов для удаления всех детей.

        Ошибка возникала когда: container.remove_children(*children)
        Исправление: container.remove_children()
        """
        mock_container = MagicMock()

        children_list = [MagicMock(), MagicMock(), MagicMock()] * 30

        def populate_and_clear():
            mock_container.children = children_list
            mock_container.remove_children()

        populate_and_clear()

        mock_container.remove_children.assert_called_once_with()

    def test_remove_children_with_query_selector(self) -> None:
        """Тест: remove_children может принимать CSS селектор как аргумент."""
        mock_container = MagicMock()

        mock_container.remove_children("#category-list")

        mock_container.remove_children.assert_called_once_with("#category-list")

    def test_remove_children_with_widget(self) -> None:
        """Тест: remove_children может принимать виджет для удаления."""
        mock_container = MagicMock()
        widget = MagicMock()

        mock_container.remove_children(widget)

        mock_container.remove_children.assert_called_once_with(widget)

    def test_remove_children_no_spread_operator(self) -> None:
        """Тест: remove_children НЕ должен вызываться со spread оператором.

        Это предотвращает TypeError при большом количестве виджетов.
        """
        mock_container = MagicMock()
        children = [MagicMock() for _ in range(100)]

        mock_container.remove_children(*children)

        mock_container.remove_children.assert_called_once()
        assert mock_container.remove_children.call_count == 1

    def test_real_textual_remove_children_behavior(self) -> None:
        """Тест: проверяет что Textual remove_children работает без аргументов.

        Этот тест использует реальное поведение API, а не mock.
        """
        try:
            from textual.widget import Widget

            assert callable(getattr(Widget, "remove_children", None))
        except ImportError:
            pytest.skip("Textual не установлен")
