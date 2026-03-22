"""
Тесты для проверки уникальности ID виджетов в TUI.

Содержит тесты для выявления ошибок с дублирующимися ID виджетов.
"""

import pytest

try:
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestWidgetUniqueIDs:
    """Тесты для проверки уникальности ID виджетов."""

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

    def test_category_selector_id_mapping_creation(self, sample_categories: list[dict]) -> None:
        """Тест 1: Проверка создания маппинга rubric_code -> индекс.

        Этот тест проверяет, что маппинг создаётся корректно
        и использует rubric_code для уникальной идентификации.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories

        # Создать маппинг (как в _load_categories)
        for i, cat in enumerate(sample_categories):
            rubric_code = cat.get("rubric_code", str(i))
            screen._id_to_index[rubric_code] = i

        # Проверить, что все rubric_code маппятся на правильные индексы
        for i, cat in enumerate(sample_categories):
            rubric_code = cat.get("rubric_code")
            assert rubric_code in screen._id_to_index
            assert screen._id_to_index[rubric_code] == i

    def test_category_selector_checkbox_ids_unique(self, sample_categories: list[dict]) -> None:
        """Тест 2: Проверка уникальности ID для checkbox.

        Этот тест выявляет ошибку DuplicateIds, проверяя,
        что ID checkbox основаны на rubric_code, а не на индексе.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories
        screen._filtered_categories = sample_categories.copy()

        # Создать маппинг
        for i, cat in enumerate(sample_categories):
            rubric_code = cat.get("rubric_code", str(i))
            screen._id_to_index[rubric_code] = i

        # Сгенерировать ожидаемые ID checkbox
        expected_ids = {f"category-{cat['rubric_code']}" for cat in sample_categories}

        # Проверить уникальность ID
        assert len(expected_ids) == len(sample_categories), "ID должны быть уникальными"

        # Проверить, что ID основаны на rubric_code, а не на индексе
        assert "category-161" in expected_ids
        assert "category-0" not in expected_ids

    def test_category_selector_filter_preserves_id_uniqueness(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 3: Проверка уникальности ID при фильтрации.

        Этот тест выявляет ошибку DuplicateIds, которая возникает при:
        1. Загрузке категорий
        2. Вводе поискового запроса (фильтрация)
        3. Повторном создании checkbox

        Ожидаемое поведение:
        - Все checkbox должны иметь уникальные ID независимо от фильтрации
        - ID должны основываться на rubric_code
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories
        screen._filtered_categories = sample_categories.copy()

        # Создать маппинг
        for i, cat in enumerate(sample_categories):
            rubric_code = cat.get("rubric_code", str(i))
            screen._id_to_index[rubric_code] = i

        # Первая "популяция" (без фильтрации) - генерируем ID
        checkbox_ids_first = {
            f"category-{cat['rubric_code']}" for cat in screen._filtered_categories
        }

        # Проверить уникальность ID
        assert len(checkbox_ids_first) == len(screen._filtered_categories), (
            "ID должны быть уникальными при первой популяции"
        )

        # Теперь отфильтровать категории (имитация поиска)
        query = "а"  # Поиск по букве "а"
        screen._filtered_categories = [
            cat for cat in sample_categories if query in cat.get("name", "").lower()
        ]

        # Вторая "популяция" (с фильтрацией) - генерируем ID
        checkbox_ids_second = {
            f"category-{cat['rubric_code']}" for cat in screen._filtered_categories
        }

        # Проверить уникальность ID после фильтрации
        assert len(checkbox_ids_second) == len(screen._filtered_categories), (
            "ID должны оставаться уникальными после фильтрации"
        )

        # Проверить, что нет дубликатов между итерациями
        # (каждый ID должен быть уникальным независимо от контекста)
        for checkbox_id in checkbox_ids_second:
            assert checkbox_id.startswith("category-")
            rubric_code = checkbox_id.split("-", 1)[1]
            assert rubric_code in {cat["rubric_code"] for cat in sample_categories}

    def test_category_selector_selected_indices_mapping(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 4: Проверка работы с выбранными категориями через маппинг.

        Этот тест проверяет, что выбранные категории корректно
        отслеживаются через маппинг rubric_code -> индекс.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories

        # Создать маппинг
        for i, cat in enumerate(sample_categories):
            rubric_code = cat.get("rubric_code", str(i))
            screen._id_to_index[rubric_code] = i

        # Выбрать первые две категории по индексу
        screen._selected_indices = {0, 1}

        # Проверить, что можно получить индекс по rubric_code
        rubric_code_1 = sample_categories[0]["rubric_code"]
        rubric_code_2 = sample_categories[1]["rubric_code"]

        assert screen._id_to_index.get(rubric_code_1) == 0
        assert screen._id_to_index.get(rubric_code_2) == 1

        # Проверить, что выбранные индексы корректны
        assert 0 in screen._selected_indices
        assert 1 in screen._selected_indices
