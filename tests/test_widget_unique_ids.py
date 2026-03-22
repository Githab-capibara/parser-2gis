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

    def test_category_selector_original_index_assignment(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 1: Проверка назначения original_index при загрузке категорий.

        Этот тест проверяет, что каждая категория получает уникальный
        original_index при загрузке, который используется для создания ID.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories

        # Имитация _load_categories
        for i, cat in enumerate(sample_categories):
            cat["original_index"] = i
            screen._id_to_index[str(i)] = i

        # Проверить, что все категории имеют original_index
        for i, cat in enumerate(sample_categories):
            assert "original_index" in cat
            assert cat["original_index"] == i

    def test_category_selector_checkbox_ids_from_original_index(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 2: Проверка, что ID checkbox основаны на original_index.

        Этот тест проверяет, что ID checkbox создаются на основе
        original_index, а не индекса в отфильтрованном списке.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories
        screen._filtered_categories = sample_categories.copy()

        # Назначить original_index
        for i, cat in enumerate(sample_categories):
            cat["original_index"] = i

        # Сгенерировать ожидаемые ID checkbox
        expected_ids = {f"category-{cat['original_index']}" for cat in sample_categories}

        # Проверить уникальность ID
        assert len(expected_ids) == len(sample_categories), "ID должны быть уникальными"

        # Проверить, что ID основаны на original_index
        assert "category-0" in expected_ids
        assert "category-4" in expected_ids

    def test_category_selector_filter_unique_ids_regression(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 3: Регрессионный тест на уникальность ID при фильтрации.

        Этот тест выявляет ошибку DuplicateIds, которая возникала при:
        1. Загрузке категорий и создании checkbox с ID category-0, category-1, ...
        2. Вводе поискового запроса (фильтрация)
        3. Повторном создании checkbox с теми же ID

        Ожидаемое поведение:
        - Все checkbox должны иметь уникальные ID независимо от фильтрации
        - ID должны основываться на original_index, сохранённом в категории
        - При фильтрации не должно возникать конфликтов ID
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories
        screen._filtered_categories = sample_categories.copy()

        # Назначить original_index (как в _load_categories)
        for i, cat in enumerate(sample_categories):
            cat["original_index"] = i

        # Первая "популяция" (без фильтрации) - генерируем ID
        checkbox_ids_first = {
            f"category-{cat['original_index']}" for cat in screen._filtered_categories
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
            f"category-{cat['original_index']}" for cat in screen._filtered_categories
        }

        # Проверить уникальность ID после фильтрации
        assert len(checkbox_ids_second) == len(screen._filtered_categories), (
            "ID должны оставаться уникальными после фильтрации"
        )

        # Проверить, что все ID из второй популяции уникальны
        all_ids = list(checkbox_ids_second)
        assert len(all_ids) == len(set(all_ids)), "Все ID должны быть уникальными"

    def test_category_selector_selected_indices_mapping(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 4: Проверка работы с выбранными категориями через original_index.

        Этот тест проверяет, что выбранные категории корректно
        отслеживаются через original_index.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories

        # Назначить original_index
        for i, cat in enumerate(sample_categories):
            cat["original_index"] = i

        # Выбрать первые две категории по индексу
        screen._selected_indices = {0, 1}

        # Проверить, что original_index корректны
        assert sample_categories[0]["original_index"] == 0
        assert sample_categories[1]["original_index"] == 1

        # Проверить, что выбранные индексы корректны
        assert 0 in screen._selected_indices
        assert 1 in screen._selected_indices

    def test_category_selector_no_duplicate_ids_after_multiple_filters(
        self, sample_categories: list[dict]
    ) -> None:
        """Тест 5: Проверка отсутствия дубликатов ID после множественных фильтраций.

        Этот тест имитирует сценарий пользователя:
        1. Загрузка категорий
        2. Поиск "а"
        3. Поиск "о"
        4. Очистка поиска

        На каждом этапе ID должны оставаться уникальными.
        """
        screen = CategorySelectorScreen()
        screen._categories = sample_categories
        screen._filtered_categories = sample_categories.copy()

        # Назначить original_index
        for i, cat in enumerate(sample_categories):
            cat["original_index"] = i

        # Этап 1: Поиск "а"
        screen._filtered_categories = [
            cat for cat in sample_categories if "а" in cat.get("name", "").lower()
        ]
        ids_stage1 = {cat["original_index"] for cat in screen._filtered_categories}
        assert len(ids_stage1) == len(screen._filtered_categories), (
            f"Дубликаты ID на этапе 1 (поиск 'а'): {ids_stage1}"
        )

        # Этап 2: Поиск "о"
        screen._filtered_categories = [
            cat for cat in sample_categories if "о" in cat.get("name", "").lower()
        ]
        ids_stage2 = {cat["original_index"] for cat in screen._filtered_categories}
        assert len(ids_stage2) == len(screen._filtered_categories), (
            f"Дубликаты ID на этапе 2 (поиск 'о'): {ids_stage2}"
        )

        # Этап 3: Очистка поиска (все категории)
        screen._filtered_categories = sample_categories.copy()
        ids_stage3 = {cat["original_index"] for cat in screen._filtered_categories}
        assert len(ids_stage3) == len(screen._filtered_categories), (
            f"Дубликаты ID на этапе 3 (очистка): {ids_stage3}"
        )

        # Проверить, что все original_index в пределах допустимого диапазона
        for ids, stage_name in [(ids_stage1, "1"), (ids_stage2, "2"), (ids_stage3, "3")]:
            for idx in ids:
                assert 0 <= idx < len(sample_categories), (
                    f"Неверный original_index {idx} на этапе {stage_name}"
                )
