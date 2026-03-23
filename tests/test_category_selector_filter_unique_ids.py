"""
Тесты для проверки уникальности ID в CategorySelectorScreen при фильтрации.

Этот модуль тестирует критическую функциональность:
- Уникальность ID checkbox при фильтрации категорий
- Отсутствие дубликатов ID при быстром вводе текста
- Корректность формата ID "category-{original_index}"
- Работа без полноценного Textual контекста (mock approach)

Тесты используют mock-объекты для изоляции от Textual runtime и не требуют
Chrome или сетевого подключения.
"""

from typing import Any, Dict, List
from unittest.mock import Mock, PropertyMock

import pytest

try:
    from textual.containers import ScrollableContainer
    from textual.widgets import Checkbox
except ImportError:
    # Mock для среды без textual
    ScrollableContainer = Mock  # type: ignore
    Checkbox = Mock  # type: ignore

from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen


class MockTextualApp:
    """Мок-приложение для имитации Textual App.

    Attributes:
        selected_categories: Список выбранных пользователем категорий.
        categories_data: Тестовые данные категорий.
    """

    def __init__(self) -> None:
        """Инициализация мок-приложения."""
        self.selected_categories: List[str] = []
        self.categories_data: List[Dict[str, Any]] = [
            {"name": "Кафе", "rubric_code": "161"},
            {"name": "Ресторан", "rubric_code": "162"},
            {"name": "Бар", "rubric_code": "163"},
            {"name": "Кафе-бар", "rubric_code": "164"},
            {"name": "Ресторан быстрого питания", "rubric_code": "165"},
            {"name": "Столовая", "rubric_code": "166"},
            {"name": "Закусочная", "rubric_code": "167"},
            {"name": "Кофейня", "rubric_code": "168"},
            {"name": "Чайная", "rubric_code": "169"},
            {"name": "Пиццерия", "rubric_code": "170"},
        ]

    def get_categories(self) -> List[Dict[str, Any]]:
        """Возвращает тестовые данные категорий.

        Returns:
            Список словарей с данными категорий.
        """
        return self.categories_data


class TestCategorySelectorFilterUniqueIds:
    """Тесты для проверки уникальности ID при фильтрации категорий.

    Эти тесты проверяют, что при фильтрации категорий в CategorySelectorScreen
    все ID checkbox остаются уникальными и соответствуют формату "category-{original_index}".

    Тесты используют mock-подход и работают без полноценного Textual контекста.
    """

    @pytest.fixture
    def mock_app(self) -> MockTextualApp:
        """Создаёт мок-приложение для тестирования.

        Returns:
            Экземпляр MockTextualApp с тестовыми данными.
        """
        return MockTextualApp()

    @pytest.fixture
    def screen_with_mocks(self, mock_app: MockTextualApp) -> CategorySelectorScreen:
        """Создаёт экран с настроенными mock-объектами.

        Args:
            mock_app: Мок-приложение для тестирования.

        Returns:
            Настроенный экземпляр CategorySelectorScreen.
        """
        screen = CategorySelectorScreen()

        # Привязываем экран к приложению через PropertyMock
        type(screen).app = PropertyMock(return_value=mock_app)

        # Mock для query_one, возвращающий mock container
        mock_container = Mock(spec=ScrollableContainer)
        screen.query_one = Mock(return_value=mock_container)

        return screen

    def test_all_checkbox_ids_unique_after_initial_load(
        self, mock_app: MockTextualApp, screen_with_mocks: CategorySelectorScreen
    ) -> None:
        """Тест 1: Проверка уникальности всех ID после начальной загрузки.

        Проверяет, что при первоначальной загрузке категорий все ID checkbox
        уникальны и соответствуют формату "category-{original_index}".

        Args:
            mock_app: Мок-приложение для тестирования.
            screen_with_mocks: Настроенный экран с mock-объектами.
        """
        screen = screen_with_mocks

        # Имитируем монтирование экрана
        screen._load_categories()
        screen._populate_categories()

        # Получаем список всех ID checkbox
        checkbox_ids = [cb.id for cb in screen._checkboxes]

        # Проверяем, что все ID уникальны
        assert len(checkbox_ids) == len(set(checkbox_ids)), (
            f"Обнаружены дублирующиеся ID после начальной загрузки: {checkbox_ids}"
        )

        # Проверяем формат ID
        for checkbox_id in checkbox_ids:
            assert checkbox_id.startswith("category-"), (
                f"ID не соответствует формату 'category-{{index}}': {checkbox_id}"
            )

        # Проверяем количество чекбоксов
        assert len(screen._checkboxes) == len(mock_app.categories_data), (
            f"Ожидалось {len(mock_app.categories_data)} чекбоксов, "
            f"получено {len(screen._checkboxes)}"
        )

    def test_unique_ids_preserved_during_filtering(
        self, screen_with_mocks: CategorySelectorScreen
    ) -> None:
        """Тест 2: Проверка сохранения уникальности ID при фильтрации.

        Проверяет, что при фильтрации категорий (поиске) все ID checkbox
        остаются уникальными, даже если количество результатов меняется.

        Args:
            screen_with_mocks: Настроенный экран с mock-объектами.
        """
        screen = screen_with_mocks

        # Инициализируем экран
        screen._load_categories()

        # Симулируем поиск по тексту "кафе" (должно найти "Кафе" и "Кафе-бар")
        query = "кафе"
        screen._filtered_categories = [
            cat for cat in screen._categories if query in cat.get("name", "").lower()
        ]
        screen._populate_categories()

        # Получаем ID после фильтрации
        filtered_ids = [cb.id for cb in screen._checkboxes]

        # Проверяем уникальность ID
        assert len(filtered_ids) == len(set(filtered_ids)), (
            f"Дублирующиеся ID после фильтрации '{query}': {filtered_ids}"
        )

        # Проверяем, что количество чекбоксов соответствует ожидаемому
        # Должно быть 2: "Кафе" (original_index=0) и "Кафе-бар" (original_index=3)
        expected_count = 2
        assert len(screen._checkboxes) == expected_count, (
            f"Ожидалось {expected_count} чекбоксов после фильтрации, "
            f"получено {len(screen._checkboxes)}"
        )

        # Проверяем, что ID соответствуют оригинальным индексам
        expected_indices = {0, 3}  # "Кафе" и "Кафе-бар"
        actual_indices = {
            int(cb.id.split("-", 1)[1])
            for cb in screen._checkboxes
            if cb.id and cb.id.startswith("category-")
        }
        assert actual_indices == expected_indices, (
            f"Ожидались индексы {expected_indices}, получены {actual_indices}"
        )

    def test_rapid_input_no_duplicate_ids(self, screen_with_mocks: CategorySelectorScreen) -> None:
        """Тест 3: Проверка отсутствия дубликатов при быстром вводе текста.

        Проверяет, что при быстрой смене поисковых запросов (симуляция
        on_input_changed) не возникает дубликатов ID на любом этапе.

        Args:
            screen_with_mocks: Настроенный экран с mock-объектами.
        """
        screen = screen_with_mocks

        # Инициализируем экран
        screen._load_categories()

        # Симулируем быстрый ввод текста (серия поисковых запросов)
        rapid_queries = ["а", "о", "кафе", "ресторан", "бар", ""]

        for query in rapid_queries:
            # Применяем фильтр
            if not query:
                screen._filtered_categories = screen._categories.copy()
            else:
                screen._filtered_categories = [
                    cat for cat in screen._categories if query in cat.get("name", "").lower()
                ]

            # Обновляем интерфейс
            screen._populate_categories()

            # Проверяем уникальность ID на каждом этапе
            current_ids = [cb.id for cb in screen._checkboxes]
            assert len(current_ids) == len(set(current_ids)), (
                f"Дублирующиеся ID после быстрого ввода '{query}': {current_ids}"
            )

            # Проверяем формат всех ID
            for checkbox_id in current_ids:
                assert checkbox_id.startswith("category-"), (
                    f"ID не соответствует формату: {checkbox_id}"
                )

    def test_original_index_format_guarantees_uniqueness(
        self, screen_with_mocks: CategorySelectorScreen
    ) -> None:
        """Тест 4: Проверка, что формат ID гарантирует уникальность.

        Проверяет, что формат ID "category-{original_index}" гарантирует
        уникальность независимо от фильтрации, потому что original_index
        назначается один раз при загрузке и не меняется.

        Args:
            screen_with_mocks: Настроенный экран с mock-объектами.
        """
        screen = screen_with_mocks

        # Инициализируем экран
        screen._load_categories()

        # Собираем все original_index из категорий
        original_indices = [cat["original_index"] for cat in screen._categories]

        # Проверяем, что все original_index уникальны
        assert len(original_indices) == len(set(original_indices)), (
            f"Дублирующиеся original_index: {original_indices}"
        )

        # Проверяем, что original_index находятся в допустимом диапазоне
        assert min(original_indices) == 0, (
            f"Минимальный original_index должен быть 0, получено {min(original_indices)}"
        )
        assert max(original_indices) == len(screen._categories) - 1, (
            f"Максимальный original_index должен быть {len(screen._categories) - 1}, "
            f"получено {max(original_indices)}"
        )

        # Проверяем, что ID checkbox соответствуют original_index
        screen._populate_categories()
        checkbox_ids = [cb.id for cb in screen._checkboxes]

        for checkbox_id in checkbox_ids:
            # Извлекаем индекс из ID
            parts = checkbox_id.split("-", 1)
            assert len(parts) == 2, f"Неверный формат ID: {checkbox_id}"

            try:
                index = int(parts[1])
            except ValueError:
                pytest.fail(f"Индекс в ID не является числом: {checkbox_id}")

            # Проверяем, что индекс существует в original_indices
            assert index in original_indices, (
                f"Индекс {index} из ID {checkbox_id} не найден в original_indices"
            )

    def test_filter_then_clear_maintains_uniqueness(
        self, screen_with_mocks: CategorySelectorScreen
    ) -> None:
        """Тест 5: Проверка уникальности после фильтрации и очистки.

        Проверяет полный цикл: загрузка -> фильтрация -> очистка фильтра.
        На всех этапах ID должны оставаться уникальными.

        Args:
            screen_with_mocks: Настроенный экран с mock-объектами.
        """
        screen = screen_with_mocks

        # Этап 1: Начальная загрузка
        screen._load_categories()
        screen._populate_categories()

        initial_ids = [cb.id for cb in screen._checkboxes]
        assert len(initial_ids) == len(set(initial_ids)), (
            f"Дубликаты ID при начальной загрузке: {initial_ids}"
        )

        # Этап 2: Применение фильтра
        screen._filtered_categories = [
            cat for cat in screen._categories if "кафе" in cat.get("name", "").lower()
        ]
        screen._populate_categories()

        filtered_ids = [cb.id for cb in screen._checkboxes]
        assert len(filtered_ids) == len(set(filtered_ids)), (
            f"Дубликаты ID после фильтрации: {filtered_ids}"
        )

        # Этап 3: Очистка фильтра (возврат к полным данным)
        screen._filtered_categories = screen._categories.copy()
        screen._populate_categories()

        cleared_ids = [cb.id for cb in screen._checkboxes]
        assert len(cleared_ids) == len(set(cleared_ids)), (
            f"Дубликаты ID после очистки фильтра: {cleared_ids}"
        )

        # Проверяем, что после очистки количество совпадает с начальным
        assert len(cleared_ids) == len(initial_ids), (
            f"Количество ID после очистки ({len(cleared_ids)}) "
            f"не совпадает с начальным ({len(initial_ids)})"
        )

    def test_empty_filter_result_no_duplicates(
        self, screen_with_mocks: CategorySelectorScreen
    ) -> None:
        """Тест 6: Проверка отсутствия дубликатов при пустом результате фильтра.

        Проверяет, что когда фильтр не находит совпадений,
        система корректно обрабатывает пустой список без ошибок.

        Args:
            screen_with_mocks: Настроенный экран с mock-объектами.
        """
        screen = screen_with_mocks

        # Инициализируем экран
        screen._load_categories()

        # Применяем фильтр, который не найдёт совпадений
        query = "несуществующая_категория_xyz123"
        screen._filtered_categories = [
            cat for cat in screen._categories if query in cat.get("name", "").lower()
        ]
        screen._populate_categories()

        # Проверяем, что список чекбоксов пуст
        assert len(screen._checkboxes) == 0, (
            f"Ожидался пустой список чекбоксов, получено {len(screen._checkboxes)}"
        )

        # Проверяем, что ID отсутствуют (нет дубликатов в пустом списке)
        checkbox_ids = [cb.id for cb in screen._checkboxes]
        assert len(checkbox_ids) == 0, f"Ожидался пустой список ID, получено {checkbox_ids}"


class TestCategorySelectorMockIsolation:
    """Тесты для проверки корректности mock-подхода.

    Эти тесты гарантируют, что mock-объекты правильно изолируют тесты
    от Textual runtime и позволяют тестировать логику без GUI.
    """

    def test_mock_app_returns_correct_categories(self) -> None:
        """Тест: Мок-приложение возвращает корректные данные категорий.

        Проверяет, что MockTextualApp правильно реализует метод get_categories()
        и возвращает ожидаемую структуру данных.
        """
        mock_app = MockTextualApp()
        categories = mock_app.get_categories()

        # Проверяем тип возвращаемого значения
        assert isinstance(categories, list), (
            f"get_categories() должен возвращать список, получено {type(categories)}"
        )

        # Проверяем структуру каждой категории
        for cat in categories:
            assert isinstance(cat, dict), f"Каждая категория должна быть dict, получено {type(cat)}"
            assert "name" in cat, "Категория должна содержать ключ 'name'"
            assert "rubric_code" in cat, "Категория должна содержать ключ 'rubric_code'"

    def test_screen_loads_categories_from_mock_app(self) -> None:
        """Тест: Экран загружает категории из мок-приложения.

        Проверяет, что метод _load_categories() корректно получает данные
        из mock-приложения и создаёт копии категорий.
        """
        mock_app = MockTextualApp()
        screen = CategorySelectorScreen()

        # Привязываем mock-приложение
        type(screen).app = PropertyMock(return_value=mock_app)

        # Mock query_one для _populate_categories()
        mock_container = Mock(spec=ScrollableContainer)
        screen.query_one = Mock(return_value=mock_container)

        # Загружаем категории
        screen._load_categories()

        # Проверяем, что категории загружены
        assert len(screen._categories) > 0, "Категории не загружены"

        # Проверяем, что созданы копии (не те же самые объекты)
        original_categories = mock_app.get_categories()
        for i, cat in enumerate(screen._categories):
            assert cat is not original_categories[i], (
                f"Категория {i} должна быть копией, а не ссылкой на оригинал"
            )

        # Проверяем, что original_index назначены
        for i, cat in enumerate(screen._categories):
            assert "original_index" in cat, f"Категория {i} должна содержать original_index"
            assert cat["original_index"] == i, (
                f"original_index должен быть {i}, получено {cat['original_index']}"
            )

    def test_mock_container_methods_called(self) -> None:
        """Тест: Мок-контейнер вызывает ожидаемые методы.

        Проверяет, что при populate_categories() вызываются методы
        remove_children() и mount() на mock-контейнере.
        """
        mock_app = MockTextualApp()
        screen = CategorySelectorScreen()
        type(screen).app = PropertyMock(return_value=mock_app)

        # Создаём mock-контейнер
        mock_container = Mock(spec=ScrollableContainer)
        screen.query_one = Mock(return_value=mock_container)

        # Инициализируем экран
        screen._load_categories()
        screen._populate_categories()

        # Проверяем, что remove_children был вызван (очистка перед добавлением)
        mock_container.remove_children.assert_called_once()

        # Проверяем, что mount был вызван для каждого чекбокса
        assert mock_container.mount.call_count == len(mock_app.categories_data), (
            f"mount() должен быть вызван {len(mock_app.categories_data)} раз, "
            f"вызван {mock_container.mount.call_count} раз"
        )


# Запуск тестов при прямом вызове скрипта
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
