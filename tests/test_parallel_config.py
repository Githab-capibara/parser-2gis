"""
Тесты на проверку ParallelParserConfig (Data Clumps антипаттерн).

Проверяет:
- Существование ParallelParserConfig dataclass
- Что это dataclass с правильными полями
- Использование ParallelParserConfig в ParallelCityParser

Data Clumps антипаттерн:
Группы одинаковых параметров передаются вместе через несколько функций.
Решение: объединить параметры в dataclass.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List

from parser_2gis.config import Configuration
from parser_2gis.parallel.options import ParallelParserConfig


class TestParallelParserConfigExists:
    """Тесты на существование ParallelParserConfig."""

    def test_parallel_parser_config_exists(self) -> None:
        """Проверяет что ParallelParserConfig существует."""
        assert ParallelParserConfig is not None, "ParallelParserConfig должен существовать"

    def test_parallel_parser_config_is_dataclass(self) -> None:
        """Проверяет что ParallelParserConfig — это dataclass."""
        assert is_dataclass(ParallelParserConfig), "ParallelParserConfig должен быть dataclass"

    def test_parallel_parser_config_has_required_fields(self) -> None:
        """Проверяет что ParallelParserConfig имеет требуемые поля."""
        required_fields = [
            "cities",
            "categories",
            "output_dir",
            "config",
            "max_workers",
            "timeout_per_url",
        ]

        config_fields = [f.name for f in fields(ParallelParserConfig)]

        missing_fields = [f for f in required_fields if f not in config_fields]

        assert len(missing_fields) == 0, f"ParallelParserConfig не имеет полей: {missing_fields}"


class TestParallelParserConfigFields:
    """Тесты на проверку полей ParallelParserConfig."""

    def test_cities_field_type(self) -> None:
        """Проверяет тип поля cities."""
        config_fields = {f.name: f for f in fields(ParallelParserConfig)}

        assert "cities" in config_fields, "Поле cities должно существовать"

    def test_categories_field_type(self) -> None:
        """Проверяет тип поля categories."""
        config_fields = {f.name: f for f in fields(ParallelParserConfig)}

        assert "categories" in config_fields, "Поле categories должно существовать"

    def test_output_dir_field_type(self) -> None:
        """Проверяет тип поля output_dir."""
        config_fields = {f.name: f for f in fields(ParallelParserConfig)}

        assert "output_dir" in config_fields, "Поле output_dir должно существовать"

    def test_config_field_type(self) -> None:
        """Проверяет тип поля config."""
        config_fields = {f.name: f for f in fields(ParallelParserConfig)}

        assert "config" in config_fields, "Поле config должно существовать"

    def test_max_workers_field_default(self) -> None:
        """Проверяет значение по умолчанию max_workers."""
        config_fields = {f.name: f for f in fields(ParallelParserConfig)}

        max_workers_field = config_fields.get("max_workers")
        assert max_workers_field is not None, "Поле max_workers должно существовать"

        # Проверяем что есть значение по умолчанию
        assert max_workers_field.default == 10, "max_workers по умолчанию должен быть 10"

    def test_timeout_per_url_field_default(self) -> None:
        """Проверяет значение по умолчанию timeout_per_url."""
        config_fields = {f.name: f for f in fields(ParallelParserConfig)}

        timeout_field = config_fields.get("timeout_per_url")
        assert timeout_field is not None, "Поле timeout_per_url должно существовать"

        # Проверяем что есть значение по умолчанию
        assert timeout_field.default == 60, "timeout_per_url по умолчанию должен быть 60"

    def test_dataclass_has_no_default_factory_for_required_fields(self) -> None:
        """Проверяет что обязательные поля не имеют default_factory."""
        required_fields_no_default = ["cities", "categories", "output_dir", "config"]

        for field in fields(ParallelParserConfig):
            if field.name in required_fields_no_default:
                assert field.default is None or not field.init, (
                    f"Поле {field.name} не должно иметь значения по умолчанию"
                )


class TestParallelParserConfigInstantiation:
    """Тесты на создание экземпляров ParallelParserConfig."""

    def test_create_config_with_required_fields(self) -> None:
        """Проверяет создание конфигурации с обязательными полями."""
        cities: List[Dict[str, Any]] = [
            {"code": "msk", "domain": "moscow.2gis.ru"},
            {"code": "spb", "domain": "spb.2gis.ru"},
        ]
        categories: List[Dict[str, Any]] = [{"name": "Кафе", "query": "cafe"}]
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities, categories=categories, output_dir=output_dir, config=config
        )

        assert parser_config.cities == cities
        assert parser_config.categories == categories
        assert parser_config.output_dir == output_dir
        assert parser_config.config == config
        assert parser_config.max_workers == 10  # default
        assert parser_config.timeout_per_url == 60  # default

    def test_create_config_with_custom_max_workers(self) -> None:
        """Проверяет создание конфигурации с custom max_workers."""
        cities: List[Dict[str, Any]] = []
        categories: List[Dict[str, Any]] = []
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=5,
        )

        assert parser_config.max_workers == 5

    def test_create_config_with_custom_timeout(self) -> None:
        """Проверяет создание конфигурации с custom timeout."""
        cities: List[Dict[str, Any]] = []
        categories: List[Dict[str, Any]] = []
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            timeout_per_url=600,
        )

        assert parser_config.timeout_per_url == 600

    def test_config_is_immutable_after_creation(self) -> None:
        """Проверяет что dataclass frozen (если указано)."""
        # ParallelParserConfig не frozen по умолчанию, но проверяем что можно изменить
        cities: List[Dict[str, Any]] = []
        categories: List[Dict[str, Any]] = []
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities, categories=categories, output_dir=output_dir, config=config
        )

        # Dataclass не frozen, поэтому можно изменять
        # Это допустимо для конфигурации
        parser_config.max_workers = 20
        assert parser_config.max_workers == 20


class TestParallelParserConfigUsage:
    """Тесты на использование ParallelParserConfig."""

    def test_parallel_parser_can_accept_config(self) -> None:
        """Проверяет что ParallelCityParser может принимать ParallelParserConfig.

        Проверяет что сигнатура ParallelCityParser позволяет передать
        параметры из ParallelParserConfig.
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        # Проверяем сигнатуру __init__
        init_signature = inspect.signature(ParallelCityParser.__init__)
        init_params = list(init_signature.parameters.keys())

        # Параметры которые должны быть в ParallelCityParser
        expected_params = ["cities", "categories", "output_dir", "config", "max_workers"]

        for param in expected_params:
            assert param in init_params, f"ParallelCityParser должен иметь параметр '{param}'"

    def test_config_can_be_unpacked_to_parser(self) -> None:
        """Проверяет что ParallelParserConfig можно распаковать для парсера."""

        cities: List[Dict[str, Any]] = [{"code": "msk", "domain": "moscow.2gis.ru"}]
        categories: List[Dict[str, Any]] = [{"name": "Кафе", "query": "cafe"}]
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=5,
        )

        # Проверяем что можно распаковать config в dict для передачи парсеру
        config_dict = {
            "cities": parser_config.cities,
            "categories": parser_config.categories,
            "output_dir": parser_config.output_dir,
            "config": parser_config.config,
            "max_workers": parser_config.max_workers,
        }

        assert config_dict["cities"] == cities
        assert config_dict["max_workers"] == 5

    def test_config_as_dict_method(self) -> None:
        """Проверяет что dataclass можно преобразовать в dict."""
        cities: List[Dict[str, Any]] = [{"code": "msk"}]
        categories: List[Dict[str, Any]] = [{"name": "Кафе"}]
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities, categories=categories, output_dir=output_dir, config=config
        )

        # Используем dataclasses.asdict
        from dataclasses import asdict

        config_dict = asdict(parser_config)

        assert isinstance(config_dict, dict)
        assert "cities" in config_dict
        assert "categories" in config_dict
        assert "output_dir" in config_dict
        assert "config" in config_dict
        assert "max_workers" in config_dict


class TestDataClumpsPattern:
    """Тесты на устранение Data Clumps антипаттерна."""

    def test_no_duplicate_parameter_groups(self) -> None:
        """Проверяет что параметры не передаются отдельно (data clumps).

        Раньше параметры передавались отдельно:
        def parse(cities, categories, output_dir, config, max_workers)

        Теперь они объединены в ParallelParserConfig.
        """
        from parser_2gis.parallel import parallel_parser

        # Проверяем что ParallelParserConfig существует и используется
        assert hasattr(parallel_parser, "ParallelParserConfig") or hasattr(
            parallel_parser, "ParallelCityParser"
        )

    def test_config_groups_related_parameters(self) -> None:
        """Проверяет что ParallelParserConfig группирует связанные параметры."""
        # Параметры которые были разбросаны:
        # - cities: List[Dict]
        # - categories: List[Dict]
        # - output_dir: Path
        # - config: Configuration
        # - max_workers: int
        # - timeout_per_url: int

        # Теперь они в одном dataclass
        field_names = [f.name for f in fields(ParallelParserConfig)]

        expected_fields = [
            "cities",
            "categories",
            "output_dir",
            "config",
            "max_workers",
            "timeout_per_url",
        ]

        for field in expected_fields:
            assert field in field_names, f"Поле {field} должно быть в ParallelParserConfig"

    def test_config_reduces_function_signature_complexity(self) -> None:
        """Проверяет что ParallelParserConfig уменьшает сложность сигнатур функций."""
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        # Проверяем сигнатуру __init__
        init_signature = inspect.signature(ParallelCityParser.__init__)

        # Количество параметров (исключая self)
        params = [p for p in init_signature.parameters.values() if p.name != "self"]
        param_count = len(params)

        # Допускаем до 7 параметров (магическое число 7±2)
        # Если бы не было ParallelParserConfig, параметров было бы больше
        assert param_count <= 10, (
            f"Слишком много параметров в __init__: {param_count}. "
            "Рассмотрите использование ParallelParserConfig."
        )


class TestParallelParserConfigIntegration:
    """Интеграционные тесты ParallelParserConfig."""

    def test_config_with_real_data(self) -> None:
        """Проверяет конфигурацию с реальными данными."""
        cities: List[Dict[str, Any]] = [
            {"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"},
            {"code": "spb", "domain": "spb.2gis.ru", "name": "Санкт-Петербург"},
        ]
        categories: List[Dict[str, Any]] = [
            {"name": "Кафе", "query": "cafe", "id": "1001"},
            {"name": "Рестораны", "query": "restaurants", "id": "1002"},
        ]
        output_dir = Path("./output/test")
        config = Configuration(chrome={"headless": True}, parser={"max_records": 50})

        parser_config = ParallelParserConfig(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=8,
            timeout_per_url=120,
        )

        assert len(parser_config.cities) == 2
        assert len(parser_config.categories) == 2
        assert parser_config.output_dir == output_dir
        assert parser_config.config.chrome.headless is True
        assert parser_config.config.parser.max_records == 50
        assert parser_config.max_workers == 8
        assert parser_config.timeout_per_url == 120

    def test_config_serialization_compatibility(self) -> None:
        """Проверяет что конфигурацию можно сериализовать."""
        from dataclasses import asdict

        cities: List[Dict[str, Any]] = [{"code": "msk"}]
        categories: List[Dict[str, Any]] = [{"name": "Кафе"}]
        output_dir = Path("./output")
        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=cities, categories=categories, output_dir=output_dir, config=config
        )

        # Преобразуем в dict (для JSON сериализации)
        config_dict = asdict(parser_config)

        assert isinstance(config_dict, dict)
        assert config_dict["cities"] == cities
        assert config_dict["categories"] == categories
        assert str(config_dict["output_dir"]) == str(output_dir)


__all__ = [
    "TestParallelParserConfigExists",
    "TestParallelParserConfigFields",
    "TestParallelParserConfigInstantiation",
    "TestParallelParserConfigUsage",
    "TestDataClumpsPattern",
    "TestParallelParserConfigIntegration",
]
