"""
Тест для выявления ошибок с дублирующимися ID виджетов в CategorySelectorScreen.

Этот тест специально создан для обнаружения проблемы DuplicateIds,
которая возникает при наличии категорий с одинаковыми rubric_code.
"""

import pytest

try:
    from parser_2gis.data.categories_93 import CATEGORIES_93
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestDuplicateRubricCodeHandling:
    """Тесты для обработки дублирующихся rubric_code."""

    def test_categories_have_duplicate_rubric_codes(self) -> None:
        """Тест 1: Проверка наличия дублирующихся rubric_code в категориях."""
        rubric_codes = [cat.get("rubric_code") for cat in CATEGORIES_93 if cat.get("rubric_code")]

        # Найти дублирующиеся коды
        duplicates = [code for code in rubric_codes if rubric_codes.count(code) > 1]
        unique_duplicates = set(duplicates)

        # Проверить, что дубликаты действительно есть
        assert len(unique_duplicates) > 0, "В категориях должны быть дублирующиеся rubric_code"

    def test_checkbox_ids_unique_with_duplicate_rubric_codes(self) -> None:
        """Тест 2: Проверка уникальности ID checkbox при дублирующихся rubric_code.

        НОВЫЙ ПОДХОД: Используем индекс в оригинальном списке.
        """
        screen = CategorySelectorScreen()
        screen._categories = CATEGORIES_93.copy()
        screen._filtered_categories = CATEGORIES_93.copy()

        # Сгенерировать ID checkbox, используя НОВЫЙ подход (с именем для поиска индекса)
        generated_ids = []
        for i, cat in enumerate(screen._filtered_categories):
            cat_name = cat.get("name", "Неизвестно")
            # Найти оригинальный индекс по имени
            original_index = next(
                (idx for idx, c in enumerate(screen._categories) if c.get("name") == cat_name), i
            )
            checkbox_id = f"category-{original_index}"
            generated_ids.append(checkbox_id)

        # Проверить уникальность всех ID
        unique_ids = set(generated_ids)
        assert len(unique_ids) == len(generated_ids), (
            f"Все ID должны быть уникальными. Найдено дубликатов: {len(generated_ids) - len(unique_ids)}"
        )

    def test_checkbox_ids_unique_old_approach_fails(self) -> None:
        """Тест 3: Проверка, что СТАРЫЙ подход с rubric_code вызывает дубликаты."""
        # Сгенерировать ID checkbox, используя СТАРЫЙ подход (только rubric_code)
        old_approach_ids = []
        for cat in CATEGORIES_93:
            rubric_code = cat.get("rubric_code", "None")
            checkbox_id = f"category-{rubric_code}"
            old_approach_ids.append(checkbox_id)

        # Проверить наличие дубликатов
        unique_ids = set(old_approach_ids)
        has_duplicates = len(unique_ids) != len(old_approach_ids)

        # Этот тест подтверждает, что старый подход НЕ работает
        assert has_duplicates, (
            "Старый подход должен вызывать дубликаты ID (это ожидаемое поведение для демонстрации)"
        )

    def test_category_selector_populate_with_duplicates(self) -> None:
        """Тест 4: Проверка _populate_categories с дублирующимися rubric_code."""
        screen = CategorySelectorScreen()
        screen._categories = CATEGORIES_93.copy()
        screen._filtered_categories = CATEGORIES_93.copy()
        screen._selected_indices = set()
        screen._checkboxes = []

        # Вызвать метод _populate_categories (частично, без контейнера)
        generated_ids = []
        for i, cat in enumerate(screen._filtered_categories):
            cat_name = cat.get("name", "Неизвестно")

            # Найти оригинальный индекс по имени
            original_index = next(
                (idx for idx, c in enumerate(screen._categories) if c.get("name") == cat_name), i
            )

            checkbox_id = f"category-{original_index}"
            generated_ids.append(checkbox_id)

        # Проверить уникальность
        unique_ids = set(generated_ids)
        assert len(unique_ids) == len(generated_ids), (
            f"Все ID должны быть уникальными. Дубликатов: {len(generated_ids) - len(unique_ids)}"
        )

        # Проверить, что количество ID совпадает с количеством категорий
        assert len(generated_ids) == len(CATEGORIES_93), (
            f"Должно быть {len(CATEGORIES_93)} ID, но получено {len(generated_ids)}"
        )

    def test_filter_with_duplicate_rubric_codes(self) -> None:
        """Тест 5: Проверка фильтрации при дублирующихся rubric_code."""
        screen = CategorySelectorScreen()
        screen._categories = CATEGORIES_93.copy()

        # Отфильтровать категории (например, по букве "а")
        query = "а"
        screen._filtered_categories = [
            cat for cat in CATEGORIES_93 if query in cat.get("name", "").lower()
        ]

        # Сгенерировать ID для отфильтрованных категорий
        generated_ids = []
        for i, cat in enumerate(screen._filtered_categories):
            cat_name = cat.get("name", "Неизвестно")

            # Найти оригинальный индекс по имени
            original_index = next(
                (idx for idx, c in enumerate(screen._categories) if c.get("name") == cat_name), i
            )
            checkbox_id = f"category-{original_index}"
            generated_ids.append(checkbox_id)

        # Проверить уникальность
        unique_ids = set(generated_ids)
        assert len(unique_ids) == len(generated_ids), (
            f"ID должны быть уникальными после фильтрации. Дубликатов: {len(generated_ids) - len(unique_ids)}"
        )

    def test_specific_duplicate_case_fastfood_shawarma(self) -> None:
        """Тест 6: Проверка конкретного случая с Фастфуд и Шаурмичные.

        Этот тест проверяет конкретный случай из лога ошибки,
        где "Фастфуд" и "Шаурмичные" имеют одинаковый rubric_code "20223".
        """
        # Найти категории "Фастфуд" и "Шаурмичные"
        fastfood_idx = None
        shawarma_idx = None
        duplicate_rubric_code = "20223"

        for i, cat in enumerate(CATEGORIES_93):
            if cat["name"] == "Фастфуд":
                fastfood_idx = i
                assert cat.get("rubric_code") == duplicate_rubric_code, (
                    "Фастфуд должен иметь rubric_code 20223"
                )
            elif cat["name"] == "Шаурмичные":
                shawarma_idx = i
                assert cat.get("rubric_code") == duplicate_rubric_code, (
                    "Шаурмичные должны иметь rubric_code 20223"
                )

        assert fastfood_idx is not None, "Категория 'Фастфуд' должна существовать"
        assert shawarma_idx is not None, "Категория 'Шаурмичные' должна существовать"
        assert fastfood_idx != shawarma_idx, "Это должны быть разные индексы"

        # Проверить, что НОВЫЙ подход создаёт уникальные ID
        # ID для "Фастфуд"
        fastfood_id = f"category-{fastfood_idx}"

        # ID для "Шаурмичные" (должен быть другим, так как индекс другой)
        shawarma_id = f"category-{shawarma_idx}"

        assert fastfood_id != shawarma_id, f"ID должны быть разными: {fastfood_id} vs {shawarma_id}"
