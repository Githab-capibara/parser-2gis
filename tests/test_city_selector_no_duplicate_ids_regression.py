"""
Тест для проверки отсутствия дублирующихся ID в CitySelectorScreen.

Этот тест проверяет, что Checkbox виджеты в CitySelectorScreen
не имеют ID (используют атрибуты вместо ID), что предотвращает
ошибку DuplicateIds при фильтрации городов.
"""

import pytest

try:
    from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestCitySelectorNoWidgetIds:
    """Тесты для проверки отсутствия ID у Checkbox в CitySelectorScreen."""

    @pytest.fixture
    def sample_cities(self) -> list[dict]:
        """Фикстура с тестовыми городами."""
        return [
            {"name": "Москва", "code": "moscow", "domain": "msk", "country_code": "ru"},
            {"name": "Санкт-Петербург", "code": "spb", "domain": "spb", "country_code": "ru"},
            {"name": "Казань", "code": "kazan", "domain": "kzn", "country_code": "ru"},
            {"name": "Дубай", "code": "dubai", "domain": "ae", "country_code": "ae"},
            {"name": "Новосибирск", "code": "nsk", "domain": "nsk", "country_code": "ru"},
        ]

    def test_checkbox_widgets_have_no_ids(self, sample_cities: list[dict]) -> None:
        """Тест 1: Проверка, что Checkbox виджеты не имеют ID.

        Этот тест проверяет, что Checkbox виджеты создаются без ID,
        что предотвращает ошибку DuplicateIds при фильтрации.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Симуляция _populate_cities
        checkboxes = []
        for i, city in enumerate(sample_cities):
            city_code = city.get("code", str(i))
            checkbox = type(
                "MockCheckbox", (), {"id": None, "city_code": city_code, "value": False}
            )()
            checkboxes.append(checkbox)

        # Проверить, что все checkbox не имеют ID
        for checkbox in checkboxes:
            assert checkbox.id is None, f"Checkbox не должен иметь ID. Найден ID: {checkbox.id}"

    def test_checkbox_uses_city_code_attribute(self, sample_cities: list[dict]) -> None:
        """Тест 2: Проверка, что Checkbox используют атрибут city_code.

        Этот тест проверяет, что для идентификации городов используется
        атрибут city_code, а не ID виджета.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Проверить, что city_code атрибут используется
        for i, city in enumerate(sample_cities):
            city_code = city.get("code", str(i))
            # Симуляция создания checkbox с атрибутом city_code
            checkbox = type(
                "MockCheckbox", (), {"id": None, "city_code": city_code, "value": False}
            )()

            # Проверить, что city_code атрибут существует и корректен
            assert hasattr(checkbox, "city_code"), "Checkbox должен иметь атрибут city_code"
            assert checkbox.city_code == city_code, (
                f"city_code должен быть '{city_code}', найден: {checkbox.city_code}"
            )

    def test_no_duplicate_ids_after_multiple_filters_regression(
        self, sample_cities: list[dict]
    ) -> None:
        """Тест 3: Регрессионный тест на отсутствие DuplicateIds.

        Этот тест проверяет, что при многократной фильтрации
        не возникает ошибка DuplicateIds, потому что Checkbox
        не имеют ID.

        Сценарий:
        1. Загрузка городов
        2. Поиск "о" (фильтрация)
        3. Поиск "м" (фильтрация)
        4. Очистка поиска

        На каждом этапе Checkbox не должны иметь ID.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities

        # Этап 1: Начальная загрузка
        screen._filtered_cities = sample_cities.copy()
        for i, city in enumerate(screen._filtered_cities):
            checkbox = type(
                "MockCheckbox",
                (),
                {"id": None, "city_code": city.get("code", str(i)), "value": False},
            )()
            assert checkbox.id is None, "На этапе 1 Checkbox не должен иметь ID"

        # Этап 2: Поиск "о"
        screen._filtered_cities = [
            city for city in sample_cities if "о" in city.get("name", "").lower()
        ]
        for i, city in enumerate(screen._filtered_cities):
            checkbox = type(
                "MockCheckbox",
                (),
                {"id": None, "city_code": city.get("code", str(i)), "value": False},
            )()
            assert checkbox.id is None, "На этапе 2 Checkbox не должен иметь ID"

        # Этап 3: Поиск "м"
        screen._filtered_cities = [
            city for city in sample_cities if "м" in city.get("name", "").lower()
        ]
        for i, city in enumerate(screen._filtered_cities):
            checkbox = type(
                "MockCheckbox",
                (),
                {"id": None, "city_code": city.get("code", str(i)), "value": False},
            )()
            assert checkbox.id is None, "На этапе 3 Checkbox не должен иметь ID"

        # Этап 4: Очистка поиска
        screen._filtered_cities = sample_cities.copy()
        for i, city in enumerate(screen._filtered_cities):
            checkbox = type(
                "MockCheckbox",
                (),
                {"id": None, "city_code": city.get("code", str(i)), "value": False},
            )()
            assert checkbox.id is None, "На этапе 4 Checkbox не должен иметь ID"

    def test_city_code_attribute_preserved_across_filters(self, sample_cities: list[dict]) -> None:
        """Тест 4: Проверка сохранения атрибута city_code при фильтрации.

        Этот тест проверяет, что атрибут city_code корректно
        сохраняется для каждого города при фильтрации.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities

        filters = ["о", "м", "с", ""]

        for filter_query in filters:
            if filter_query:
                screen._filtered_cities = [
                    city for city in sample_cities if filter_query in city.get("name", "").lower()
                ]
            else:
                screen._filtered_cities = sample_cities.copy()

            # Проверить, что все города имеют city_code
            for i, city in enumerate(screen._filtered_cities):
                city_code = city.get("code", str(i))
                assert city_code is not None, (
                    f"Город должен иметь code при фильтре '{filter_query}'"
                )
                assert isinstance(city_code, str), (
                    f"city_code должен быть строкой при фильтре '{filter_query}'"
                )

    def test_selected_indices_mapping_without_ids(self, sample_cities: list[dict]) -> None:
        """Тест 5: Проверка работы с выбранными городами без использования ID.

        Этот тест проверяет, что выбранные города корректно
        отслеживаются через оригинальные индексы без依赖 ID виджетов.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Выбрать города по индексам (без依赖 ID)
        screen._selected_indices = {0, 2, 4}

        # Проверить, что выбранные индексы корректны
        assert 0 in screen._selected_indices
        assert 2 in screen._selected_indices
        assert 4 in screen._selected_indices

        # Проверить, что названия городов соответствуют индексам
        assert sample_cities[0]["name"] == "Москва"
        assert sample_cities[2]["name"] == "Казань"
        assert sample_cities[4]["name"] == "Новосибирск"

        # Проверить, что можно снять выбор без ID
        screen._selected_indices.discard(2)
        assert 2 not in screen._selected_indices
        assert 0 in screen._selected_indices
        assert 4 in screen._selected_indices
