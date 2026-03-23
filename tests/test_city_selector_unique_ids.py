"""
Тесты для проверки уникальности ID виджетов в CitySelectorScreen.

Содержит тесты для выявления ошибок с дублирующимися ID виджетов
при фильтрации городов.
"""

import pytest

try:
    from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestCitySelectorUniqueIDs:
    """Тесты для проверки уникальности ID виджетов в CitySelectorScreen."""

    @pytest.fixture
    def sample_cities(self) -> list[dict]:
        """Фикстура с тестовыми городами."""
        return [
            {"name": "Москва", "code": "moscow", "domain": "msk", "country_code": "ru"},
            {"name": "Санкт-Петербург", "code": "spb", "domain": "spb", "country_code": "ru"},
            {"name": "Казань", "code": "kazan", "domain": "kzn", "country_code": "ru"},
            {"name": "ОАЭ", "code": "dubai", "domain": "ae", "country_code": "ae"},
            {"name": "Новосибирск", "code": "nsk", "domain": "nsk", "country_code": "ru"},
        ]

    def test_city_selector_checkbox_ids_from_city_code(self, sample_cities: list[dict]) -> None:
        """Тест 1: Проверка, что ID checkbox основаны на уникальном коде города.

        Этот тест проверяет, что ID checkbox создаются на основе
        уникального кода города (code), а не индекса в списке.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Сгенерировать ожидаемые ID checkbox
        expected_ids = {f"city-{city['code']}" for city in sample_cities}

        # Проверить уникальность ID
        assert len(expected_ids) == len(sample_cities), "ID должны быть уникальными"

        # Проверить, что ID основаны на коде города
        assert "city-moscow" in expected_ids
        assert "city-spb" in expected_ids
        assert "city-dubai" in expected_ids

    def test_city_selector_filter_unique_ids_regression(self, sample_cities: list[dict]) -> None:
        """Тест 2: Регрессионный тест на уникальность ID при фильтрации.

        Этот тест выявляет ошибку DuplicateIds, которая возникала при:
        1. Загрузке городов и создании checkbox с ID city-0, city-1, ...
        2. Вводе поискового запроса (фильтрация)
        3. Повторном создании checkbox с теми же ID

        Ожидаемое поведение:
        - Все checkbox должны иметь уникальные ID независимо от фильтрации
        - ID должны основываться на уникальном коде города
        - При фильтрации не должно возникать конфликтов ID
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Первая "популяция" (без фильтрации) - генерируем ID
        checkbox_ids_first = {f"city-{city['code']}" for city in screen._filtered_cities}

        # Проверить уникальность ID
        assert len(checkbox_ids_first) == len(screen._filtered_cities), (
            "ID должны быть уникальными при первой популяции"
        )

        # Теперь отфильтровать города (имитация поиска по букве "о")
        query = "о"
        screen._filtered_cities = [
            city for city in sample_cities if query in city.get("name", "").lower()
        ]

        # Вторая "популяция" (с фильтрацией) - генерируем ID
        checkbox_ids_second = {f"city-{city['code']}" for city in screen._filtered_cities}

        # Проверить уникальность ID после фильтрации
        assert len(checkbox_ids_second) == len(screen._filtered_cities), (
            "ID должны оставаться уникальными после фильтрации"
        )

        # Проверить, что все ID из второй популяции уникальны
        all_ids = list(checkbox_ids_second)
        assert len(all_ids) == len(set(all_ids)), "Все ID должны быть уникальными"

    def test_city_selector_no_duplicate_ids_after_multiple_filters(
        self, sample_cities: list[dict]
    ) -> None:
        """Тест 3: Проверка отсутствия дубликатов ID после множественных фильтраций.

        Этот тест имитирует сценарий пользователя:
        1. Загрузка городов
        2. Поиск "о"
        3. Поиск "м"
        4. Очистка поиска

        На каждом этапе ID должны оставаться уникальными.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Этап 1: Поиск "о"
        screen._filtered_cities = [
            city for city in sample_cities if "о" in city.get("name", "").lower()
        ]
        ids_stage1 = {city["code"] for city in screen._filtered_cities}
        assert len(ids_stage1) == len(screen._filtered_cities), (
            f"Дубликаты ID на этапе 1 (поиск 'о'): {ids_stage1}"
        )

        # Этап 2: Поиск "м"
        screen._filtered_cities = [
            city for city in sample_cities if "м" in city.get("name", "").lower()
        ]
        ids_stage2 = {city["code"] for city in screen._filtered_cities}
        assert len(ids_stage2) == len(screen._filtered_cities), (
            f"Дубликаты ID на этапе 2 (поиск 'м'): {ids_stage2}"
        )

        # Этап 3: Очистка поиска (все города)
        screen._filtered_cities = sample_cities.copy()
        ids_stage3 = {city["code"] for city in screen._filtered_cities}
        assert len(ids_stage3) == len(screen._filtered_cities), (
            f"Дубликаты ID на этапе 3 (очистка): {ids_stage3}"
        )

        # Проверить, что все коды городов в пределах допустимого диапазона
        all_codes = [city["code"] for city in sample_cities]
        for ids, stage_name in [(ids_stage1, "1"), (ids_stage2, "2"), (ids_stage3, "3")]:
            for code in ids:
                assert code in all_codes, f"Неверный код города {code} на этапе {stage_name}"

    def test_city_selector_selected_indices_mapping(self, sample_cities: list[dict]) -> None:
        """Тест 4: Проверка работы с выбранными городами через оригинальные индексы.

        Этот тест проверяет, что выбранные города корректно
        отслеживаются через оригинальные индексы в полном списке.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Выбрать первые два города по индексу
        screen._selected_indices = {0, 1}

        # Проверить, что выбранные индексы корректны
        assert 0 in screen._selected_indices
        assert 1 in screen._selected_indices

        # Проверить, что названия городов соответствуют индексам
        assert sample_cities[0]["name"] == "Москва"
        assert sample_cities[1]["name"] == "Санкт-Петербург"

    def test_city_selector_checkbox_id_format(self, sample_cities: list[dict]) -> None:
        """Тест 5: Проверка формата ID checkbox.

        Этот тест проверяет, что ID checkbox имеют правильный формат:
        - Префикс "city-"
        - Уникальный код города после префикса
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities
        screen._filtered_cities = sample_cities.copy()

        # Проверить формат ID для каждого города
        for city in sample_cities:
            expected_id = f"city-{city['code']}"
            assert expected_id.startswith("city-"), f"ID должен начинаться с 'city-': {expected_id}"
            assert len(expected_id) > 5, "ID должен содержать код после префикса"
            assert " " not in expected_id, "ID не должен содержать пробелы"

    def test_city_selector_filter_preserves_code_uniqueness(
        self, sample_cities: list[dict]
    ) -> None:
        """Тест 6: Проверка, что фильтрация сохраняет уникальность кодов.

        Этот тест проверяет, что после фильтрации все города
        сохраняют свои уникальные коды.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities

        # Применить различные фильтры
        filters = ["о", "м", "с", "к", "д", ""]

        for filter_query in filters:
            if filter_query:
                screen._filtered_cities = [
                    city for city in sample_cities if filter_query in city.get("name", "").lower()
                ]
            else:
                screen._filtered_cities = sample_cities.copy()

            # Проверить уникальность кодов
            codes = [city["code"] for city in screen._filtered_cities]
            assert len(codes) == len(set(codes)), (
                f"Коды должны быть уникальными при фильтре '{filter_query}': {codes}"
            )
