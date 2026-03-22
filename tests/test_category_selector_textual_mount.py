"""
Тест для проверки логики категорий и ID без Textual контекста.

Проверяет, что логика назначения original_index и генерации ID
работает корректно без необходимости запускать Textual приложение.
"""

import pytest


class TestCategoryIndexLogic:
    """Тесты для логики назначения original_index и генерации ID."""

    @pytest.fixture
    def sample_categories(self):
        """Фикстура с тестовыми категориями."""
        return [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
            {"name": "Бары", "query": "Бары", "rubric_code": "163"},
            {"name": "Столовые", "query": "Столовые", "rubric_code": "164"},
            {"name": "Пиццерии", "query": "Пиццерии", "rubric_code": "165"},
        ]

    def test_assign_original_index(self, sample_categories) -> None:
        """Тест: каждой категории назначается уникальный original_index."""
        categories = [cat.copy() for cat in sample_categories]

        for i, cat in enumerate(categories):
            cat["original_index"] = i

        indices = {cat["original_index"] for cat in categories}
        assert len(indices) == len(categories)
        assert indices == {0, 1, 2, 3, 4}

    def test_generate_checkbox_ids(self, sample_categories) -> None:
        """Тест: ID checkbox генерируются корректно."""
        categories = [cat.copy() for cat in sample_categories]

        for i, cat in enumerate(categories):
            cat["original_index"] = i

        checkbox_ids = [f"category-{cat['original_index']}" for cat in categories]

        assert len(checkbox_ids) == len(set(checkbox_ids))
        assert "category-0" in checkbox_ids
        assert "category-4" in checkbox_ids

    def test_filter_preserves_original_index(self, sample_categories) -> None:
        """Тест: фильтрация сохраняет уникальность original_index."""
        categories = [cat.copy() for cat in sample_categories]

        for i, cat in enumerate(categories):
            cat["original_index"] = i

        query = "а"
        filtered = [cat for cat in categories if query in cat.get("name", "").lower()]

        indices = {cat["original_index"] for cat in filtered}
        assert len(indices) == len(filtered)

    def test_multiple_filter_cycles_preserve_uniqueness(self, sample_categories) -> None:
        """Тест: множественные фильтрации сохраняют уникальность ID."""
        categories = [cat.copy() for cat in sample_categories]

        for i, cat in enumerate(categories):
            cat["original_index"] = i

        queries = ["а", "", "р", ""]

        for query in queries:
            if query:
                filtered = [cat for cat in categories if query in cat.get("name", "").lower()]
            else:
                filtered = categories.copy()

            ids = {f"category-{cat['original_index']}" for cat in filtered}
            assert len(ids) == len(filtered), f"Дубликаты при фильтрации '{query}'"

    def test_remove_children_logic(self) -> None:
        """Тест: симуляция логики remove_children для избежания DuplicateIds.

        Проверяет, что при очистке и повторном добавлении ID остаются уникальными.
        """
        categories = [
            {"name": "Item 1", "original_index": 0},
            {"name": "Item 2", "original_index": 1},
            {"name": "Item 3", "original_index": 2},
        ]

        def simulate_populate(filtered):
            ids = {f"category-{cat['original_index']}" for cat in filtered}
            return ids

        def simulate_remove_and_add():
            return simulate_populate(categories)

        ids1 = simulate_remove_and_add()
        assert len(ids1) == 3

        filtered = [c for c in categories if c["original_index"] < 2]
        ids2 = simulate_populate(filtered)
        assert len(ids2) == 2

        ids3 = simulate_remove_and_add()
        assert len(ids3) == 3

        assert ids1 == {"category-0", "category-1", "category-2"}
        assert ids2 == {"category-0", "category-1"}
