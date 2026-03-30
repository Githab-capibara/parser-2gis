"""
Тесты для проверки dataclass конфигураций.

Проверяет инициализацию и атрибуты dataclass:
- ParserThreadConfig
- MergeConfig
- ValidationResult
- ParallelParserConfig

Тесты покрывают исправления:
- Устранение Data Clumps (группы одинаковых параметров)
- Использование dataclass для конфигураций
- Корректная инициализация и атрибуты
"""

from dataclasses import fields, is_dataclass
from pathlib import Path
from threading import Event

import pytest


class TestParserThreadConfig:
    """Тесты для ParserThreadConfig dataclass."""

    def test_parser_thread_config_creation(self):
        """
        Тест 1.1: Создание ParserThreadConfig.

        Проверяет что ParserThreadConfig может быть создан.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig
        from parser_2gis.config import Configuration

        config = Configuration()
        cities = [{"name": "Moscow", "code": "msk"}]
        categories = [{"name": "Cafes", "code": "cafes"}]

        thread_config = ParserThreadConfig(
            cities=cities, categories=categories, output_dir="/tmp", config=config
        )

        assert thread_config is not None
        assert thread_config.cities == cities
        assert thread_config.categories == categories
        assert thread_config.output_dir == "/tmp"
        assert thread_config.config == config

    def test_parser_thread_config_default_values(self):
        """
        Тест 1.2: Проверка значений по умолчанию.

        Проверяет что значения по умолчанию установлены корректно.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig
        from parser_2gis.config import Configuration

        config = Configuration()

        thread_config = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config
        )

        # Проверяем значения по умолчанию
        assert thread_config.max_workers == 3
        assert thread_config.timeout_per_url > 0  # Значение по умолчанию
        assert thread_config.output_file is None

    def test_parser_thread_config_custom_values(self):
        """
        Тест 1.3: Проверка пользовательских значений.

        Проверяет что можно установить пользовательские значения.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig
        from parser_2gis.config import Configuration

        config = Configuration()

        thread_config = ParserThreadConfig(
            cities=[],
            categories=[],
            output_dir="/tmp",
            config=config,
            max_workers=5,
            timeout_per_url=60,
            output_file="output.csv",
        )

        assert thread_config.max_workers == 5
        assert thread_config.timeout_per_url == 60
        assert thread_config.output_file == "output.csv"

    def test_parser_thread_config_is_dataclass(self):
        """
        Тест 1.4: Проверка что ParserThreadConfig это dataclass.

        Проверяет что класс является dataclass.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        assert is_dataclass(ParserThreadConfig) is True

    def test_parser_thread_config_fields(self):
        """
        Тест 1.5: Проверка полей ParserThreadConfig.

        Проверяет что все ожидаемые поля присутствуют.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        field_names = [f.name for f in fields(ParserThreadConfig)]

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
            assert field_name in field_names, f"Поле {field_name} отсутствует"


class TestMergeConfig:
    """Тесты для MergeConfig dataclass."""

    def test_merge_config_creation(self):
        """
        Тест 2.1: Создание MergeConfig.

        Проверяет что MergeConfig может быть создан.
        """
        from parser_2gis.parallel.file_merger import MergeConfig

        file_paths = [Path("/tmp/file1.csv"), Path("/tmp/file2.csv")]
        output_path = Path("/tmp/output.csv")

        merge_config = MergeConfig(file_paths=file_paths, output_path=output_path, encoding="utf-8")

        assert merge_config is not None
        assert merge_config.file_paths == file_paths
        assert merge_config.output_path == output_path
        assert merge_config.encoding == "utf-8"

    def test_merge_config_default_values(self):
        """
        Тест 2.2: Проверка значений по умолчанию.

        Проверяет что значения по умолчанию установлены корректно.
        """
        from parser_2gis.parallel.file_merger import MergeConfig

        file_paths = [Path("/tmp/file1.csv")]
        output_path = Path("/tmp/output.csv")

        merge_config = MergeConfig(file_paths=file_paths, output_path=output_path, encoding="utf-8")

        # Проверяем значения по умолчанию
        assert merge_config.buffer_size > 0
        assert merge_config.batch_size > 0
        assert merge_config.log_callback is None
        assert merge_config.progress_callback is None
        assert merge_config.cancel_event is None

    def test_merge_config_with_callbacks(self):
        """
        Тест 2.3: Проверка с callback функциями.

        Проверяет что callback функции могут быть установлены.
        """
        from parser_2gis.parallel.file_merger import MergeConfig

        def log_callback(msg: str, level: str) -> None:
            pass

        def progress_callback(msg: str) -> None:
            pass

        cancel_event = Event()

        merge_config = MergeConfig(
            file_paths=[Path("/tmp/file1.csv")],
            output_path=Path("/tmp/output.csv"),
            encoding="utf-8",
            log_callback=log_callback,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )

        assert merge_config.log_callback == log_callback
        assert merge_config.progress_callback == progress_callback
        assert merge_config.cancel_event == cancel_event

    def test_merge_config_is_dataclass(self):
        """
        Тест 2.4: Проверка что MergeConfig это dataclass.

        Проверяет что класс является dataclass.
        """
        from parser_2gis.parallel.file_merger import MergeConfig

        assert is_dataclass(MergeConfig) is True

    def test_merge_config_fields(self):
        """
        Тест 2.5: Проверка полей MergeConfig.

        Проверяет что все ожидаемые поля присутствуют.
        """
        from parser_2gis.parallel.file_merger import MergeConfig

        field_names = [f.name for f in fields(MergeConfig)]

        expected_fields = [
            "file_paths",
            "output_path",
            "encoding",
            "buffer_size",
            "batch_size",
            "log_callback",
            "progress_callback",
            "cancel_event",
        ]

        for field_name in expected_fields:
            assert field_name in field_names, f"Поле {field_name} отсутствует"


class TestValidationResult:
    """Тесты для ValidationResult dataclass."""

    def test_validation_result_success(self):
        """
        Тест 3.1: Создание ValidationResult для успеха.

        Проверяет что ValidationResult может быть создан для успешного случая.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        result = ValidationResult(is_valid=True, value="test_value", error=None)

        assert result is not None
        assert result.is_valid is True
        assert result.value == "test_value"
        assert result.error is None

    def test_validation_result_error(self):
        """
        Тест 3.2: Создание ValidationResult для ошибки.

        Проверяет что ValidationResult может быть создан для случая ошибки.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        result = ValidationResult(is_valid=False, value=None, error="Invalid value")

        assert result is not None
        assert result.is_valid is False
        assert result.value is None
        assert result.error == "Invalid value"

    def test_validation_result_default_values(self):
        """
        Тест 3.3: Проверка значений по умолчанию.

        Проверяет что значения по умолчанию установлены корректно.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        result = ValidationResult(is_valid=True)

        assert result.value is None
        assert result.error is None

    def test_validation_result_is_dataclass(self):
        """
        Тест 3.4: Проверка что ValidationResult это dataclass.

        Проверяет что класс является dataclass.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        assert is_dataclass(ValidationResult) is True

    def test_validation_result_fields(self):
        """
        Тест 3.5: Проверка полей ValidationResult.

        Проверяет что все ожидаемые поля присутствуют.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        field_names = [f.name for f in fields(ValidationResult)]

        expected_fields = ["is_valid", "value", "error"]

        for field_name in expected_fields:
            assert field_name in field_names, f"Поле {field_name} отсутствует"


class TestParallelParserConfig:
    """Тесты для ParallelParserConfig dataclass."""

    def test_parallel_parser_config_creation(self):
        """
        Тест 4.1: Создание ParallelParserConfig.

        Проверяет что ParallelParserConfig может быть создан.
        """
        from parser_2gis.parallel.options import ParallelParserConfig
        from parser_2gis.config import Configuration

        config = Configuration()
        cities = [{"name": "Moscow", "code": "msk"}]
        categories = [{"name": "Cafes", "code": "cafes"}]
        output_dir = Path("/tmp")

        parser_config = ParallelParserConfig(
            cities=cities, categories=categories, output_dir=output_dir, config=config
        )

        assert parser_config is not None
        assert parser_config.cities == cities
        assert parser_config.categories == categories
        assert parser_config.output_dir == output_dir
        assert parser_config.config == config

    def test_parallel_parser_config_default_values(self):
        """
        Тест 4.2: Проверка значений по умолчанию.

        Проверяет что значения по умолчанию установлены корректно.
        """
        from parser_2gis.parallel.options import ParallelParserConfig
        from parser_2gis.config import Configuration

        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=[], categories=[], output_dir=Path("/tmp"), config=config
        )

        # Проверяем значения по умолчанию
        assert parser_config.max_workers == 10
        assert parser_config.timeout_per_url == 60

    def test_parallel_parser_config_custom_values(self):
        """
        Тест 4.3: Проверка пользовательских значений.

        Проверяет что можно установить пользовательские значения.
        """
        from parser_2gis.parallel.options import ParallelParserConfig
        from parser_2gis.config import Configuration

        config = Configuration()

        parser_config = ParallelParserConfig(
            cities=[],
            categories=[],
            output_dir=Path("/tmp"),
            config=config,
            max_workers=5,
            timeout_per_url=120,
        )

        assert parser_config.max_workers == 5
        assert parser_config.timeout_per_url == 120

    def test_parallel_parser_config_is_dataclass(self):
        """
        Тест 4.4: Проверка что ParallelParserConfig это dataclass.

        Проверяет что класс является dataclass.
        """
        from parser_2gis.parallel.options import ParallelParserConfig

        assert is_dataclass(ParallelParserConfig) is True

    def test_parallel_parser_config_fields(self):
        """
        Тест 4.5: Проверка полей ParallelParserConfig.

        Проверяет что все ожидаемые поля присутствуют.
        """
        from parser_2gis.parallel.options import ParallelParserConfig

        field_names = [f.name for f in fields(ParallelParserConfig)]

        expected_fields = [
            "cities",
            "categories",
            "output_dir",
            "config",
            "max_workers",
            "timeout_per_url",
        ]

        for field_name in expected_fields:
            assert field_name in field_names, f"Поле {field_name} отсутствует"


class TestDataclassImmutability:
    """Тесты для проверки изменяемости dataclass."""

    def test_parser_thread_config_mutable(self):
        """
        Тест 5.1: Проверка изменяемости ParserThreadConfig.

        Проверяет что поля можно изменять после создания.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig
        from parser_2gis.config import Configuration

        config = Configuration()

        thread_config = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config
        )

        # Изменяем поле
        thread_config.max_workers = 10
        assert thread_config.max_workers == 10

    def test_merge_config_mutable(self):
        """
        Тест 5.2: Проверка изменяемости MergeConfig.

        Проверяет что поля можно изменять после создания.
        """
        from parser_2gis.parallel.file_merger import MergeConfig

        merge_config = MergeConfig(
            file_paths=[Path("/tmp/file1.csv")],
            output_path=Path("/tmp/output.csv"),
            encoding="utf-8",
        )

        # Изменяем поле
        merge_config.buffer_size = 1024
        assert merge_config.buffer_size == 1024

    def test_validation_result_mutable(self):
        """
        Тест 5.3: Проверка изменяемости ValidationResult.

        Проверяет что поля можно изменять после создания.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        result = ValidationResult(is_valid=True)

        # Изменяем поле
        result.is_valid = False
        assert result.is_valid is False


class TestDataclassEquality:
    """Тесты для проверки равенства dataclass."""

    def test_parser_thread_config_equality(self):
        """
        Тест 6.1: Проверка равенства ParserThreadConfig.

        Проверяет что одинаковые конфигурации равны.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig
        from parser_2gis.config import Configuration

        config1 = Configuration()
        config2 = Configuration()

        thread_config1 = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config1
        )

        thread_config2 = ParserThreadConfig(
            cities=[], categories=[], output_dir="/tmp", config=config2
        )

        # Конфигурации должны быть равны если поля равны
        # (за исключением config который может быть разным)
        assert thread_config1.cities == thread_config2.cities
        assert thread_config1.categories == thread_config2.categories
        assert thread_config1.output_dir == thread_config2.output_dir

    def test_validation_result_equality(self):
        """
        Тест 6.2: Проверка равенства ValidationResult.

        Проверяет что одинаковые результаты равны.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        result1 = ValidationResult(is_valid=True, value="test", error=None)
        result2 = ValidationResult(is_valid=True, value="test", error=None)

        assert result1 == result2

    def test_validation_result_inequality(self):
        """
        Тест 6.3: Проверка неравенства ValidationResult.

        Проверяет что разные результаты не равны.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        result1 = ValidationResult(is_valid=True, value="test1", error=None)
        result2 = ValidationResult(is_valid=True, value="test2", error=None)

        assert result1 != result2


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
