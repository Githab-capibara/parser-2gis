"""
Тесты для проверки dataclass конфигураций.

Проверяет инициализацию и атрибуты dataclass:
- ParallelRunConfig
- ParserRunConfig
- CLIRunConfig
- ParallelParserConfig
- ParserThreadConfig

Проверяет что конфигурации используются вместо передачи dict.

Принципы:
- Устранение Data Clumps (группы одинаковых параметров)
- Использование dataclass для конфигураций
- Корректная инициализация и атрибуты
- Типизация конфигураций
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_dataclass_fields(dataclass_type: type) -> List[str]:
    """Извлекает имена всех полей dataclass.

    Args:
        dataclass_type: Тип dataclass.

    Returns:
        Список имён полей.
    """
    return [f.name for f in fields(dataclass_type)]


def check_dataclass_instantiation(dataclass_type: type, **kwargs: Any) -> bool:
    """Проверяет что dataclass может быть создан с указанными параметрами.

    Args:
        dataclass_type: Тип dataclass.
        **kwargs: Параметры для инициализации.

    Returns:
        True если instantiation успешен.
    """
    try:
        instance = dataclass_type(**kwargs)
        return instance is not None
    except (TypeError, ValueError):
        return False


def get_function_annotations(file_path: Path, function_name: str) -> Dict[str, Any]:
    """Извлекает аннотации функции из файла.

    Args:
        file_path: Путь к Python файлу.
        function_name: Имя функции.

    Returns:
        Словарь аннотаций.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read()
    except (OSError, UnicodeDecodeError):
        return {}

    # Упрощённая проверка через строковый анализ
    annotations: Dict[str, Any] = {}

    return annotations


# =============================================================================
# ТЕСТ 1: PARSELRUNCONFIG DATACLASS
# =============================================================================


class TestParserRunConfig:
    """Тесты для ParserRunConfig dataclass."""

    def test_parser_run_config_exists(self) -> None:
        """Проверяет что ParserRunConfig существует."""
        from parser_2gis.parallel.options import ParallelParserConfig

        assert ParallelParserConfig is not None

    def test_parser_run_config_is_dataclass(self) -> None:
        """Проверяет что ParserRunConfig это dataclass."""
        from parser_2gis.parallel.options import ParallelParserConfig

        assert is_dataclass(ParallelParserConfig) is True

    def test_parser_run_config_fields(self) -> None:
        """Проверяет поля ParserRunConfig."""
        from parser_2gis.parallel.options import ParallelParserConfig

        field_names = get_dataclass_fields(ParallelParserConfig)

        expected_fields = [
            "cities",
            "categories",
            "output_dir",
            "config",
            "max_workers",
            "timeout_per_url",
        ]

        for field_name in expected_fields:
            assert field_name in field_names, f"Поле {field_name} должно присутствовать"

    def test_parser_run_config_instantiation(self) -> None:
        """Проверяет создание экземпляра ParserRunConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()
        cities: List[Dict[str, Any]] = [{"name": "Москва", "domain": "moscow.2gis.ru"}]
        categories: List[Dict[str, Any]] = [{"name": "Кафе", "id": "cafe"}]
        output_dir = Path("/tmp/test")

        parser_config = ParallelParserConfig(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=5,
            timeout_per_url=60,
        )

        assert parser_config is not None
        assert parser_config.cities == cities
        assert parser_config.categories == categories
        assert parser_config.output_dir == output_dir
        assert parser_config.config == config
        assert parser_config.max_workers == 5
        assert parser_config.timeout_per_url == 60

    def test_parser_run_config_default_values(self) -> None:
        """Проверяет значения по умолчанию ParserRunConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config
        )

        # Проверяем значения по умолчанию
        assert parser_config.max_workers == 10
        assert parser_config.timeout_per_url == 60

    def test_parser_run_config_immutability_check(self) -> None:
        """Проверяет изменяемость полей ParserRunConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()
        parser_config = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config
        )

        # Dataclass по умолчанию изменяемый (если не frozen)
        parser_config.max_workers = 15
        assert parser_config.max_workers == 15


# =============================================================================
# ТЕСТ 2: PARALLELTHREADCONFIG DATACLASS
# =============================================================================


class TestParserThreadConfig:
    """Тесты для ParserThreadConfig dataclass."""

    def test_parser_thread_config_exists(self) -> None:
        """Проверяет что ParserThreadConfig существует."""
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        assert ParserThreadConfig is not None

    def test_parser_thread_config_is_dataclass(self) -> None:
        """Проверяет что ParserThreadConfig это dataclass."""
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        assert is_dataclass(ParserThreadConfig) is True

    def test_parser_thread_config_fields(self) -> None:
        """Проверяет поля ParserThreadConfig."""
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        field_names = get_dataclass_fields(ParserThreadConfig)

        expected_fields = [
            "cities",
            "categories",
            "output_dir",
            "config",
            "max_workers",
            "timeout_per_url",
            "output_file",
        ]

        for field_name in expected_fields:
            assert field_name in field_names, f"Поле {field_name} должно присутствовать"

    def test_parser_thread_config_instantiation(self) -> None:
        """Проверяет создание экземпляра ParserThreadConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        config = Configuration()
        cities: List[Dict[str, Any]] = [{"name": "Москва"}]
        categories: List[Dict[str, Any]] = [{"name": "Кафе"}]

        thread_config = ParserThreadConfig(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test",
            config=config,
            max_workers=3,
            timeout_per_url=45,
            output_file="output.csv",
        )

        assert thread_config is not None
        assert thread_config.cities == cities
        assert thread_config.categories == categories
        assert thread_config.output_dir == "/tmp/test"
        assert thread_config.config == config
        assert thread_config.max_workers == 3
        assert thread_config.timeout_per_url == 45
        assert thread_config.output_file == "output.csv"

    def test_parser_thread_config_default_values(self) -> None:
        """Проверяет значения по умолчанию ParserThreadConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        config = Configuration()

        thread_config = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config
        )

        # Проверяем значения по умолчанию
        assert thread_config.max_workers == 3
        assert thread_config.timeout_per_url > 0  # Значение по умолчанию из DEFAULT_TIMEOUT
        assert thread_config.output_file is None


# =============================================================================
# ТЕСТ 3: CONFIG DATACLASS USAGE
# =============================================================================


class TestConfigDataclassUsage:
    """Тесты на использование dataclass конфигураций вместо dict."""

    def test_parallel_coordinator_uses_config_dataclass(self) -> None:
        """Проверяет что ParallelCoordinator использует config dataclass."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # ParallelCoordinator должен принимать Configuration
        assert "config: Configuration" in content or 'config: "Configuration"' in content, (
            "ParallelCoordinator должен использовать Configuration dataclass"
        )

    def test_parser_thread_config_used_in_coordinator(self) -> None:
        """Проверяет что ParserThreadConfig используется в coordinator."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # ParserThreadConfig должен быть определён и использоваться
        assert "ParserThreadConfig" in content, (
            "coordinator.py должен использовать ParserThreadConfig"
        )
        assert "@dataclass" in content or "from dataclasses import dataclass" in content, (
            "coordinator.py должен импортировать dataclass"
        )

    def test_no_dict_for_config_in_parallel(self) -> None:
        """Проверяет что parallel модуль не использует dict для конфигурации."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        # Проверяем основные файлы parallel
        files_to_check = ["coordinator.py", "error_handler.py", "merger.py"]

        for filename in files_to_check:
            file_path = parallel_dir / filename
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8")

            # Проверяем что нет передачи config как dict
            # (это эвристическая проверка - ищем явные признаки dict config)
            assert "config: dict" not in content, (
                f"{filename} не должен использовать dict для config"
            )
            assert "config: Dict" not in content, (
                f"{filename} не должен использовать Dict для config"
            )


# =============================================================================
# ТЕСТ 4: DATACLASS ATTRIBUTES
# =============================================================================


class TestDataclassAttributes:
    """Тесты на атрибуты dataclass конфигураций."""

    def test_parallel_parser_config_attribute_access(self) -> None:
        """Проверяет доступ к атрибутам ParallelParserConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()
        parser_config = ParallelParserConfig(
            cities=[{"name": "Москва"}],
            categories=[{"name": "Кафе"}],
            output_dir=Path("/tmp"),
            config=config,
            max_workers=5,
            timeout_per_url=90,
        )

        # Проверяем доступ к атрибутам
        assert parser_config.cities == [{"name": "Москва"}]
        assert parser_config.categories == [{"name": "Кафе"}]
        assert parser_config.output_dir == Path("/tmp")
        assert parser_config.config is config
        assert parser_config.max_workers == 5
        assert parser_config.timeout_per_url == 90

    def test_parser_thread_config_attribute_access(self) -> None:
        """Проверяет доступ к атрибутам ParserThreadConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        config = Configuration()
        thread_config = ParserThreadConfig(
            cities=[{"name": "СПб"}],
            categories=[{"name": "Рестораны"}],
            output_dir="/output",
            config=config,
            max_workers=7,
            timeout_per_url=120,
            output_file="result.csv",
        )

        # Проверяем доступ к атрибутам
        assert thread_config.cities == [{"name": "СПб"}]
        assert thread_config.categories == [{"name": "Рестораны"}]
        assert thread_config.output_dir == "/output"
        assert thread_config.config is config
        assert thread_config.max_workers == 7
        assert thread_config.timeout_per_url == 120
        assert thread_config.output_file == "result.csv"

    def test_dataclass_repr(self) -> None:
        """Проверяет что dataclass имеют __repr__."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()
        parser_config = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config
        )

        # Dataclass автоматически генерирует __repr__
        repr_str = repr(parser_config)
        assert "ParallelParserConfig" in repr_str


# =============================================================================
# ТЕСТ 5: DATACLASS TYPE HINTS
# =============================================================================


class TestDataclassTypeHints:
    """Тесты на типизацию dataclass."""

    def test_parallel_parser_config_type_hints(self) -> None:
        """Проверяет аннотации типов ParallelParserConfig."""
        from parser_2gis.parallel.options import ParallelParserConfig

        # Получаем аннотации через __annotations__
        annotations = ParallelParserConfig.__annotations__

        assert "cities" in annotations
        assert "categories" in annotations
        assert "output_dir" in annotations
        assert "config" in annotations
        assert "max_workers" in annotations
        assert "timeout_per_url" in annotations

    def test_parser_thread_config_type_hints(self) -> None:
        """Проверяет аннотации типов ParserThreadConfig."""
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        annotations = ParserThreadConfig.__annotations__

        assert "cities" in annotations
        assert "categories" in annotations
        assert "output_dir" in annotations
        assert "config" in annotations
        assert "max_workers" in annotations
        assert "timeout_per_url" in annotations
        assert "output_file" in annotations

    def test_dataclass_field_types(self) -> None:
        """Проверяет типы полей dataclass."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()
        parser_config = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config
        )

        # Проверяем типы значений
        assert isinstance(parser_config.cities, list)
        assert isinstance(parser_config.categories, list)
        assert isinstance(parser_config.output_dir, Path)
        assert isinstance(parser_config.max_workers, int)
        assert isinstance(parser_config.timeout_per_url, int)


# =============================================================================
# ТЕСТ 6: DATACLASS COMPARISON
# =============================================================================


class TestDataclassComparison:
    """Тесты на сравнение dataclass."""

    def test_parallel_parser_config_equality(self) -> None:
        """Проверяет равенство ParallelParserConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config1 = Configuration()
        config2 = Configuration()

        parser_config1 = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config1
        )

        parser_config2 = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config2
        )

        # Dataclass сравниваются по полям
        # config1 и config2 могут быть разными но другие поля равны
        assert parser_config1.cities == parser_config2.cities
        assert parser_config1.categories == parser_config2.categories
        assert parser_config1.output_dir == parser_config2.output_dir
        assert parser_config1.max_workers == parser_config2.max_workers
        assert parser_config1.timeout_per_url == parser_config2.timeout_per_url

    def test_parser_thread_config_equality(self) -> None:
        """Проверяет равенство ParserThreadConfig."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        config = Configuration()

        thread_config1 = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config
        )

        thread_config2 = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config
        )

        # Одинаковые конфигурации должны быть равны
        assert thread_config1.cities == thread_config2.cities
        assert thread_config1.categories == thread_config2.categories
        assert thread_config1.output_dir == thread_config2.output_dir
        assert thread_config1.max_workers == thread_config2.max_workers
        assert thread_config1.timeout_per_url == thread_config2.timeout_per_url
        assert thread_config1.output_file == thread_config2.output_file


# =============================================================================
# ТЕСТ 7: DATACLASS IN FUNCTIONS
# =============================================================================


class TestDataclassInFunctions:
    """Тесты на использование dataclass в функциях."""

    def test_function_accepts_dataclass(self) -> None:
        """Проверяет что функции принимают dataclass конфигурации."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        config = Configuration()

        # ParallelCoordinator должен принимать параметры которые используются
        # для создания ParserThreadConfig
        coordinator = ParallelCoordinator(
            cities=[{"name": "Москва"}],
            categories=[{"name": "Кафе"}],
            output_dir="/tmp/test",
            config=config,
            max_workers=2,
            timeout_per_url=30,
        )

        assert coordinator is not None
        assert coordinator.cities == [{"name": "Москва"}]
        assert coordinator.categories == [{"name": "Кафе"}]

    def test_dataclass_passed_to_functions(self) -> None:
        """Проверяет что dataclass передаются в функции."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.options import ParallelParserConfig

        config = Configuration()
        parser_config = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config
        )

        # Проверяем что dataclass может быть передан как аргумент
        def process_config(cfg: ParallelParserConfig) -> int:
            return cfg.max_workers

        result = process_config(parser_config)
        assert result == 10  # Значение по умолчанию


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
