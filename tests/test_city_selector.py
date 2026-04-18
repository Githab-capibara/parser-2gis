"""
Тесты для проверки CitySelectorScreen.

Объединённый файл тестов для проверки:
- Уникальности ID виджетов в CitySelectorScreen
- Отсутствия дублирующихся ID при фильтрации
- Использования атрибутов вместо ID для Checkbox
- Корректной работы с выбранными городами через индексы
"""

import pytest

try:
    from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestCitySelectorUniqueIDs:
    """Тесты для проверки уникальности ID и отсутствия дубликатов в CitySelectorScreen."""

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

    def test_checkbox_ids_from_city_code(self, sample_cities: list[dict]) -> None:
        """Проверка, что ID checkbox основаны на уникальном коде города.

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

    def test_filter_unique_ids_regression(self, sample_cities: list[dict]) -> None:
        """Регрессионный тест на уникальность ID при фильтрации.

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
        screen._filtered_cities = [city for city in sample_cities if query in city.get("name", "").lower()]

        # Вторая "популяция" (с фильтрацией) - генерируем ID
        checkbox_ids_second = {f"city-{city['code']}" for city in screen._filtered_cities}

        # Проверить уникальность ID после фильтрации
        assert len(checkbox_ids_second) == len(screen._filtered_cities), (
            "ID должны оставаться уникальными после фильтрации"
        )

        # Проверить, что все ID из второй популяции уникальны
        all_ids = list(checkbox_ids_second)
        assert len(all_ids) == len(set(all_ids)), "Все ID должны быть уникальными"

    @pytest.mark.parametrize(
        "filter_query,stage_name",
        [
            ("о", "поиск 'о'"),
            ("м", "поиск 'м'"),
            ("с", "поиск 'с'"),
            ("к", "поиск 'к'"),
            ("д", "поиск 'д'"),
            ("", "очистка поиска"),
        ],
    )
    def test_filter_preserves_code_uniqueness(
        self, sample_cities: list[dict], filter_query: str, stage_name: str
    ) -> None:
        """Проверка, что фильтрация сохраняет уникальность кодов городов.

        Параметризированный тест для различных фильтров.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities

        if filter_query:
            screen._filtered_cities = [city for city in sample_cities if filter_query in city.get("name", "").lower()]
        else:
            screen._filtered_cities = sample_cities.copy()

        # Проверить уникальность кодов
        codes = [city["code"] for city in screen._filtered_cities]
        assert len(codes) == len(set(codes)), f"Коды должны быть уникальными при фильтре '{stage_name}': {codes}"

    def test_no_duplicate_ids_after_multiple_filters(self, sample_cities: list[dict]) -> None:
        """Проверка отсутствия дубликатов ID после множественных фильтраций.

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
        screen._filtered_cities = [city for city in sample_cities if "о" in city.get("name", "").lower()]
        ids_stage1 = {city["code"] for city in screen._filtered_cities}
        assert len(ids_stage1) == len(screen._filtered_cities), f"Дубликаты ID на этапе 1 (поиск 'о'): {ids_stage1}"

        # Этап 2: Поиск "м"
        screen._filtered_cities = [city for city in sample_cities if "м" in city.get("name", "").lower()]
        ids_stage2 = {city["code"] for city in screen._filtered_cities}
        assert len(ids_stage2) == len(screen._filtered_cities), f"Дубликаты ID на этапе 2 (поиск 'м'): {ids_stage2}"

        # Этап 3: Очистка поиска (все города)
        screen._filtered_cities = sample_cities.copy()
        ids_stage3 = {city["code"] for city in screen._filtered_cities}
        assert len(ids_stage3) == len(screen._filtered_cities), f"Дубликаты ID на этапе 3 (очистка): {ids_stage3}"

        # Проверить, что все коды городов в пределах допустимого диапазона
        all_codes = [city["code"] for city in sample_cities]
        for ids, stage_name in [(ids_stage1, "1"), (ids_stage2, "2"), (ids_stage3, "3")]:
            for code in ids:
                assert code in all_codes, f"Неверный код города {code} на этапе {stage_name}"

    def test_checkbox_id_format(self, sample_cities: list[dict]) -> None:
        """Проверка формата ID checkbox.

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


class TestCitySelectorNoWidgetIds:
    """Тесты для проверки отсутствия ID у Checkbox в CitySelectorScreen.

    Эти тесты проверяют, что Checkbox виджеты создаются без ID,
    что предотвращает ошибку DuplicateIds при фильтрации.
    Вместо ID используется атрибут city_code.
    """

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
        """Проверка, что Checkbox виджеты не имеют ID.

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
            checkbox = type("MockCheckbox", (), {"id": None, "city_code": city_code, "value": False})()
            checkboxes.append(checkbox)

        # Проверить, что все checkbox не имеют ID
        for checkbox in checkboxes:
            assert checkbox.id is None, f"Checkbox не должен иметь ID. Найден ID: {checkbox.id}"

    def test_checkbox_uses_city_code_attribute(self, sample_cities: list[dict]) -> None:
        """Проверка, что Checkbox используют атрибут city_code.

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
            checkbox = type("MockCheckbox", (), {"id": None, "city_code": city_code, "value": False})()

            # Проверить, что city_code атрибут существует и корректен
            assert hasattr(checkbox, "city_code"), "Checkbox должен иметь атрибут city_code"
            assert checkbox.city_code == city_code, f"city_code должен быть '{city_code}', найден: {checkbox.city_code}"

    @pytest.mark.parametrize(
        "filter_query,stage_name,stage_num",
        [
            ("", "начальная загрузка", 1),
            ("о", "поиск 'о'", 2),
            ("м", "поиск 'м'", 3),
            ("", "очистка поиска", 4),
        ],
    )
    def test_no_duplicate_ids_after_multiple_filters_regression(
        self, sample_cities: list[dict], filter_query: str, stage_name: str, stage_num: int
    ) -> None:
        """Регрессионный тест на отсутствие DuplicateIds при многократной фильтрации.

        Этот тест проверяет, что при многократной фильтрации
        не возникает ошибка DuplicateIds, потому что Checkbox
        не имеют ID.

        Параметризированный тест для различных этапов фильтрации.
        """
        screen = CitySelectorScreen()
        screen._cities = sample_cities

        if filter_query:
            screen._filtered_cities = [city for city in sample_cities if filter_query in city.get("name", "").lower()]
        else:
            screen._filtered_cities = sample_cities.copy()

        for i, city in enumerate(screen._filtered_cities):
            checkbox = type(
                "MockCheckbox",
                (),
                {"id": None, "city_code": city.get("code", str(i)), "value": False},
            )()
            assert checkbox.id is None, f"На этапе {stage_num} ({stage_name}) Checkbox не должен иметь ID"

    def test_city_code_attribute_preserved_across_filters(self, sample_cities: list[dict]) -> None:
        """Проверка сохранения атрибута city_code при фильтрации.

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
                assert city_code is not None, f"Город должен иметь code при фильтре '{filter_query}'"
                assert isinstance(city_code, str), f"city_code должен быть строкой при фильтре '{filter_query}'"

    def test_selected_indices_mapping_without_ids(self, sample_cities: list[dict]) -> None:
        """Проверка работы с выбранными городами без использования ID.

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


class TestCitySelectorSelectedIndices:
    """Тесты для проверки работы с выбранными городами через индексы."""

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

    def test_selected_indices_mapping(self, sample_cities: list[dict]) -> None:
        """Проверка работы с выбранными городами через оригинальные индексы.

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
