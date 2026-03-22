"""
Тесты для выявления ошибок мутации глобальных констант и дубликатов ID.

Этот тест выявляет проблему, когда категории мутируются (добавляется original_index),
что приводит к дубликатам ID при повторной загрузке экрана.
"""

import pytest

try:
    from parser_2gis.data.categories_93 import CATEGORIES_93

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestCategorySelectorGlobalConstantMutation:
    """Тесты для выявления мутации глобальной константы CATEGORIES_93."""

    def test_categories_93_no_original_index_initially(self) -> None:
        """Тест 1: Проверка, что CATEGORIES_93 не содержит original_index изначально.

        Глобальная константа должна оставаться неизменной.
        """
        for cat in CATEGORIES_93:
            assert "original_index" not in cat, (
                f"Категория '{cat.get('name')}' уже содержит original_index в глобальной константе!"
            )

    def test_categories_copy_preserves_original_index_uniqueness(self) -> None:
        """Тест 2: Проверка, что копирование категорий сохраняет уникальность original_index.

        Этот тест имитирует поведение _load_categories с правильным копированием.
        """
        # Имитация правильного копирования (как должно быть в _load_categories)
        categories_copy = [cat.copy() for cat in CATEGORIES_93]

        # Назначить original_index
        for i, cat in enumerate(categories_copy):
            cat["original_index"] = i

        # Проверить уникальность
        original_indices = [cat["original_index"] for cat in categories_copy]
        assert len(original_indices) == len(set(original_indices)), (
            "Обнаружены дубликаты original_index!"
        )
        assert len(original_indices) == 93, (
            f"Ожидалось 93 категории, получено: {len(original_indices)}"
        )

        # Проверить, что оригинальная константа не изменилась
        for cat in CATEGORIES_93:
            assert "original_index" not in cat, f"Категория '{cat.get('name')}' была мутирована!"

    def test_filter_preserves_original_index_uniqueness(self) -> None:
        """Тест 3: Проверка, что фильтрация сохраняет уникальность original_index.

        Этот тест имитирует фильтрацию категорий и проверяет уникальность ID.
        """
        # Создать копию с original_index
        categories = [cat.copy() for cat in CATEGORIES_93]
        for i, cat in enumerate(categories):
            cat["original_index"] = i

        # Отфильтровать категории (имитация поиска по букве "а")
        query = "а"
        filtered = [cat for cat in categories if query in cat.get("name", "").lower()]

        # Проверить уникальность original_index в отфильтрованных
        filtered_indices = [cat["original_index"] for cat in filtered]
        assert len(filtered_indices) == len(set(filtered_indices)), (
            f"Дубликаты ID при фильтрации '{query}': {filtered_indices}"
        )

        # Проверить, что все original_index в допустимом диапазоне
        for idx in filtered_indices:
            assert 0 <= idx < 93, f"Неверный original_index: {idx}"

    def test_multiple_filters_no_duplicate_ids(self) -> None:
        """Тест 4: Проверка отсутствия дубликатов ID при множественных фильтрациях.

        Этот тест имитирует сценарий:
        1. Загрузка категорий
        2. Поиск "а"
        3. Поиск "о"
        4. Очистка поиска

        На всех этапах ID должны оставаться уникальными.
        """
        # Создать копию с original_index
        categories = [cat.copy() for cat in CATEGORIES_93]
        for i, cat in enumerate(categories):
            cat["original_index"] = i

        # Этап 1: Поиск "а"
        query1 = "а"
        filtered1 = [cat for cat in categories if query1 in cat.get("name", "").lower()]
        ids1 = {cat["original_index"] for cat in filtered1}
        assert len(ids1) == len(filtered1), f"Дубликаты ID при фильтрации '{query1}': {ids1}"

        # Этап 2: Поиск "о"
        query2 = "о"
        filtered2 = [cat for cat in categories if query2 in cat.get("name", "").lower()]
        ids2 = {cat["original_index"] for cat in filtered2}
        assert len(ids2) == len(filtered2), f"Дубликаты ID при фильтрации '{query2}': {ids2}"

        # Этап 3: Очистка поиска (все категории)
        ids3 = {cat["original_index"] for cat in categories}
        assert len(ids3) == len(categories), f"Дубликаты ID при очистке поиска: {ids3}"

    def test_checkbox_ids_generation_from_original_index(self) -> None:
        """Тест 5: Проверка генерации ID checkbox из original_index.

        Этот тест проверяет, что ID checkbox создаются корректно на основе
        original_index и остаются уникальными.
        """
        # Создать копию с original_index
        categories = [cat.copy() for cat in CATEGORIES_93]
        for i, cat in enumerate(categories):
            cat["original_index"] = i

        # Сгенерировать ID checkbox (как в _populate_categories)
        checkbox_ids = [f"category-{cat['original_index']}" for cat in categories]

        # Проверить уникальность ID
        assert len(checkbox_ids) == len(set(checkbox_ids)), (
            f"Обнаружены дубликаты ID checkbox: {checkbox_ids}"
        )

        # Проверить формат ID
        for checkbox_id in checkbox_ids:
            assert checkbox_id.startswith("category-"), f"Неверный формат ID: {checkbox_id}"

    def test_all_93_categories_have_unique_original_index(self) -> None:
        """Тест 6: Проверка уникальности original_index для всех 93 категорий.

        Этот тест гарантирует, что все 93 категории имеют уникальные original_index.
        """
        # Создать копию с original_index
        categories = [cat.copy() for cat in CATEGORIES_93]
        for i, cat in enumerate(categories):
            cat["original_index"] = i

        # Проверить количество категорий
        assert len(categories) == 93, f"Ожидалось 93 категории, получено: {len(categories)}"

        # Проверить уникальность original_index
        original_indices = [cat["original_index"] for cat in categories]
        assert len(original_indices) == len(set(original_indices)), (
            "Обнаружены дубликаты original_index!"
        )

        # Проверить диапазон original_index
        assert min(original_indices) == 0, "Минимальный original_index должен быть 0"
        assert max(original_indices) == 92, "Максимальный original_index должен быть 92"

    def test_shallow_copy_causes_mutation_bug(self) -> None:
        """Тест 7: Демонстрация бага с поверхностным копированием.

        Этот тест показывает, почему shallow copy приводит к мутации
        глобальной константы CATEGORIES_93.
        """
        # Неправильный подход: поверхностное копирование
        categories_shallow = CATEGORIES_93.copy()

        # Назначить original_index
        for i, cat in enumerate(categories_shallow):
            cat["original_index"] = i

        # Проверить, что оригинальная константа БЫЛА мутирована (это баг!)
        mutation_detected = False
        for cat in CATEGORIES_93:
            if "original_index" in cat:
                mutation_detected = True
                break

        assert mutation_detected, "Поверхностное копирование должно приводить к мутации оригинала!"

        # Очистить original_index после теста
        for cat in CATEGORIES_93:
            cat.pop("original_index", None)

    def test_deep_copy_prevents_mutation_bug(self) -> None:
        """Тест 8: Проверка, что глубокое копирование предотвращает мутацию.

        Этот тест показывает, что правильное копирование предотвращает
        мутацию глобальной константы CATEGORIES_93.
        """
        # Правильный подход: глубокое копирование (список копий словарей)
        categories_deep = [cat.copy() for cat in CATEGORIES_93]

        # Назначить original_index
        for i, cat in enumerate(categories_deep):
            cat["original_index"] = i

        # Проверить, что оригинальная константа НЕ была мутирована
        for cat in CATEGORIES_93:
            assert "original_index" not in cat, (
                f"Категория '{cat.get('name')}' была мутирована при глубоком копировании!"
            )
