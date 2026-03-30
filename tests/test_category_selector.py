"""
Тесты для CategorySelectorScreen.

Объединённый файл тестов, проверяющих:
- Загрузку и фильтрацию категорий
- Уникальность original_index
- Предотвращение дубликатов ID
- Работу с глобальной константой CATEGORIES_93
- Очистку виджетов при повторном заполнении
"""

from unittest.mock import Mock, PropertyMock

import pytest
from textual.containers import ScrollableContainer

from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

try:
    from parser_2gis.data.categories_93 import CATEGORIES_93

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_app_basic():
    """Создаёт мок приложения с базовыми категориями."""
    mock_app = Mock()
    mock_app.get_categories.return_value = [
        {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
        {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
        {"name": "Бары", "query": "Бары", "rubric_code": "163"},
    ]
    mock_app.selected_categories = set()
    return mock_app


@pytest.fixture
def mock_app_extended():
    """Создаёт мок приложения с расширенным списком категорий."""
    mock_app = Mock()
    mock_app.get_categories.return_value = [
        {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
        {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
        {"name": "Бары", "query": "Бары", "rubric_code": "163"},
        {"name": "Столовые", "query": "Столовые", "rubric_code": "164"},
        {"name": "Пиццерии", "query": "Пиццерии", "rubric_code": "165"},
    ]
    mock_app.selected_categories = set()
    return mock_app


@pytest.fixture
def category_screen(mock_app_basic):
    """Создаёт CategorySelectorScreen с моком приложения."""
    screen = CategorySelectorScreen()
    type(screen).app = PropertyMock(return_value=mock_app_basic)
    mock_container = Mock(spec=ScrollableContainer)
    screen.query_one = Mock(return_value=mock_container)
    screen._load_categories()
    return screen


@pytest.fixture
def category_screen_extended(mock_app_extended):
    """Создаёт CategorySelectorScreen с расширенным списком категорий."""
    screen = CategorySelectorScreen()
    type(screen).app = PropertyMock(return_value=mock_app_extended)
    mock_container = Mock(spec=ScrollableContainer)
    screen.query_one = Mock(return_value=mock_container)
    screen._load_categories()
    return screen


# =============================================================================
# CLASS 1: БАЗОВЫЕ ТЕСТЫ
# =============================================================================


class TestCategorySelectorBasic:
    """Базовые тесты загрузки и фильтрации категорий."""

    def test_populate_categories_no_duplicate_ids(self, category_screen):
        """
        Проверяет, что повторный вызов _populate_categories не создаёт дубликатов ID.

        Сценарий:
        1. Первый вызов _populate_categories
        2. Второй вызов _populate_categories (как при фильтрации)
        3. Проверка уникальности original_index
        """
        # Первый вызов
        category_screen._populate_categories()

        # Второй вызов (как при фильтрации поиска)
        category_screen._populate_categories()

        # Проверяем количество чекбоксов
        assert len(category_screen._checkboxes) == 3

        # Проверяем уникальность original_index
        checkbox_original_indices = [
            getattr(cb, "original_index", None) for cb in category_screen._checkboxes
        ]
        assert len(checkbox_original_indices) == len(set(checkbox_original_indices)), (
            "Обнаружены дубликаты original_index!"
        )

    def test_populate_categories_after_search_filter(self, category_screen):
        """
        Проверяет работу фильтрации поиска и повторного заполнения.

        Сценарий:
        1. Загрузка категорий
        2. Фильтрация по запросу "Кафе"
        3. Проверка что осталась только одна категория
        """
        # Загружаем категории
        category_screen._populate_categories()

        # Имитируем фильтрацию по запросу "кафе"
        query = "кафе"
        category_screen._filtered_categories = [
            cat for cat in category_screen._categories if query in cat.get("name", "").lower()
        ]
        category_screen._populate_categories()

        # После фильтрации должно остаться только одно совпадение
        assert len(category_screen._filtered_categories) == 1
        assert category_screen._filtered_categories[0]["name"] == "Кафе"

        # Количество чекбоксов должно соответствовать отфильтрованному списку
        assert len(category_screen._checkboxes) == 1


# =============================================================================
# CLASS 2: ТЕСТЫ ГЛОБАЛЬНОЙ КОНСТАНТЫ CATEGORIES_93
# =============================================================================


class TestCategorySelectorGlobalConstant:
    """Тесты для проверки работы с глобальной константой CATEGORIES_93."""

    def test_categories_93_no_original_index_initially(self):
        """
        Проверяет, что CATEGORIES_93 не содержит original_index изначально.

        Глобальная константа должна оставаться неизменной.
        """
        for cat in CATEGORIES_93:
            assert "original_index" not in cat, (
                f"Категория '{cat.get('name')}' уже содержит original_index в глобальной константе!"
            )

    def test_categories_copy_preserves_original_index_uniqueness(self):
        """
        Проверяет, что копирование категорий сохраняет уникальность original_index.

        Имитирует поведение _load_categories с правильным копированием.
        """
        # Имитация правильного копирования
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

    def test_filter_preserves_original_index_uniqueness(self):
        """
        Проверяет, что фильтрация сохраняет уникальность original_index.

        Имитирует фильтрацию категорий и проверяет уникальность ID.
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

    @pytest.mark.parametrize(
        "query", ["а", "о", "р", "к"], ids=["letter_a", "letter_o", "letter_r", "letter_k"]
    )
    def test_multiple_filters_no_duplicate_ids(self, query):
        """
        Проверяет отсутствие дубликатов ID при множественных фильтрациях.

        Параметризованный тест для разных поисковых запросов.
        """
        # Создать копию с original_index
        categories = [cat.copy() for cat in CATEGORIES_93]
        for i, cat in enumerate(categories):
            cat["original_index"] = i

        # Фильтрация по запросу
        filtered = [cat for cat in categories if query in cat.get("name", "").lower()]
        ids = {cat["original_index"] for cat in filtered}

        # Проверить уникальность
        assert len(ids) == len(filtered), f"Дубликаты ID при фильтрации '{query}': {ids}"

    def test_checkbox_ids_generation_from_original_index(self):
        """
        Проверяет генерацию ID checkbox из original_index.

        Проверяет, что ID checkbox создаются корректно на основе
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

    def test_all_93_categories_have_unique_original_index(self):
        """
        Проверяет уникальность original_index для всех 93 категорий.

        Гарантирует, что все 93 категории имеют уникальные original_index.
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

    def test_shallow_copy_causes_mutation_bug(self):
        """
        Демонстрирует баг с поверхностным копированием.

        Показывает, почему shallow copy приводит к мутации
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

    def test_deep_copy_prevents_mutation_bug(self):
        """
        Проверяет, что глубокое копирование предотвращает мутацию.

        Показывает, что правильное копирование предотвращает
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


# =============================================================================
# CLASS 3: ТЕСТЫ ПРЕДОТВРАЩЕНИЯ ДУБЛИКАТОВ UI
# =============================================================================


class TestCategorySelectorDuplicatePrevention:
    """Тесты для предотвращения DuplicateIds ошибки в UI."""

    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.screen = CategorySelectorScreen()
        mock_app = Mock()
        mock_app.get_categories.return_value = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
            {"name": "Бары", "query": "Бары", "rubric_code": "163"},
        ]
        mock_app.selected_categories = set()

        type(self.screen).app = PropertyMock(return_value=mock_app)
        self.mock_container = Mock(spec=ScrollableContainer)
        self.screen.query_one = Mock(return_value=self.mock_container)
        self.screen._load_categories()

    def test_populate_categories_clears_previous_widgets(self):
        """
        Проверяет, что _populate_categories очищает предыдущие чекбоксы
        перед добавлением новых.
        """
        # First population
        self.screen._populate_categories()

        # Verify that remove_children was called on the container
        self.mock_container.remove_children.assert_called()
        self.mock_container.mount_all.assert_called()

        # Second population with different data
        self.screen._filtered_categories = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161", "original_index": 0}
        ]

        # Reset mock call counts
        self.mock_container.remove_children.reset_mock()
        self.mock_container.mount_all.reset_mock()

        # Second population
        self.screen._populate_categories()

        # Verify that remove_children was called again
        self.mock_container.remove_children.assert_called()
        self.mock_container.mount_all.assert_called()

        # Ensure _checkboxes list was cleared and repopulated
        assert len(self.screen._checkboxes) == 1

    def test_populate_categories_with_empty_filter(self):
        """
        Проверяет, что _populate_categories работает корректно с пустым фильтром.
        """
        # Set empty filtered categories
        self.screen._filtered_categories = []

        # This should not raise any exceptions
        self.screen._populate_categories()

        # Verify container was cleared
        self.mock_container.remove_children.assert_called()
        # Verify no widgets were mounted
        self.mock_container.mount_all.assert_not_called()
        # Verify _checkboxes is empty
        assert len(self.screen._checkboxes) == 0

    def test_populate_categories_prevents_duplicate_ids(self):
        """
        Проверяет, что _populate_categories предотвращает создание дублирующихся ID.
        """
        # Populate first time
        self.screen._populate_categories()

        # Get the original_index values after first population
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

        # Get the original_index values after second population
        second_original_indices = [
            getattr(cb, "original_index", None) for cb in self.screen._checkboxes
        ]

        # Verify that remove_children was called
        self.mock_container.remove_children.assert_called()

        # Verify that _checkboxes was cleared and repopulated
        assert len(self.screen._checkboxes) == len(second_original_indices)
        assert len(self.screen._checkboxes) == 2

        # Verify all original_index values are unique within each population
        assert len(first_original_indices) == len(set(first_original_indices))
        assert len(second_original_indices) == len(set(second_original_indices))


# =============================================================================
# CLASS 4: ТЕСТЫ СЦЕНАРИЕВ ФИЛЬТРАЦИИ
# =============================================================================


class TestCategorySelectorFilterScenarios:
    """Тесты сценариев фильтрации категорий."""

    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.screen = CategorySelectorScreen()
        mock_app = Mock()
        mock_app.get_categories.return_value = [
            {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
            {"name": "Рестораны", "query": "Рестораны", "rubric_code": "162"},
            {"name": "Бары", "query": "Бары", "rubric_code": "163"},
            {"name": "Столовые", "query": "Столовые", "rubric_code": "164"},
            {"name": "Пиццерии", "query": "Пиццерии", "rubric_code": "165"},
        ]
        mock_app.selected_categories = set()

        type(self.screen).app = PropertyMock(return_value=mock_app)
        self.mock_container = Mock(spec=ScrollableContainer)
        self.screen.query_one = Mock(return_value=self.mock_container)
        self.screen._load_categories()

    def test_initial_populate_no_duplicate_original_index(self):
        """
        Проверяет, что начальная загрузка не создаёт дубликатов original_index.
        """
        self.screen._populate_categories()

        # Проверить, что все original_index уникальны
        original_indices = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(original_indices) == len(set(original_indices))
        assert len(original_indices) == 5  # 5 категорий

    def test_filter_then_populate_no_duplicates(self):
        """
        Проверяет, что фильтрация с последующим _populate_categories
        не создаёт дубликатов.
        """
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
        """
        Проверяет, что многократная фильтрация не создаёт дубликатов.

        Сценарий:
        1. Фильтрация по "а"
        2. Очистка фильтра
        3. Фильтрация по "р"
        """
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

    @pytest.mark.parametrize(
        "letter,expected_count",
        [
            ("к", 1),  # Только "Кафе"
            ("а", 3),  # "Кафе", "Рестораны", "Бары"
            ("о", 2),  # "Рестораны", "Столовые"
            ("р", 3),  # "Рестораны", "Бары", "Пиццерии"
            ("и", 1),  # "Пиццерии"
        ],
        ids=["letter_k", "letter_a", "letter_o", "letter_r", "letter_i"],
    )
    def test_filter_by_letter(self, letter, expected_count):
        """
        Проверяет фильтрацию по различным буквам.

        Параметризованный тест для разных букв русского алфавита.
        """
        self.screen._filtered_categories = [
            cat for cat in self.screen._categories if letter in cat.get("name", "").lower()
        ]
        self.screen._populate_categories()

        # Проверить количество
        assert len(self.screen._checkboxes) == expected_count

        # Проверить уникальность original_index
        indices = [getattr(cb, "original_index", None) for cb in self.screen._checkboxes]
        assert len(indices) == len(set(indices))

        # Проверить, что original_index соответствуют отфильтрованным категориям
        expected_indices = {cat["original_index"] for cat in self.screen._filtered_categories}
        assert set(indices) == expected_indices

    def test_clear_filter_restores_all_categories(self):
        """
        Проверяет, что очистка фильтра восстанавливает все категории.

        Сценарий:
        1. Фильтрация по "о" (Рестораны, Столовые)
        2. Очистка фильтра
        3. Проверка что все 5 категорий восстановлены
        """
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


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__])
