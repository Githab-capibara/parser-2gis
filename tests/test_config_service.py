"""
Тесты на проверку ConfigService (KISS принцип).

Проверяет:
- Существование ConfigService класса
- Работу методов merge_configs, load_config, save_config
- Что Configuration — чистая Pydantic модель

KISS (Keep It Simple, Stupid):
ConfigService выделяет логику работы с конфигурацией в отдельный сервис,
упрощая модель Configuration.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel

from parser_2gis.config import Configuration
from parser_2gis.config_service import ConfigService


class TestConfigServiceExists:
    """Тесты на существование ConfigService."""

    def test_config_service_exists(self) -> None:
        """Проверяет что ConfigService существует."""
        assert ConfigService is not None, "ConfigService должен существовать"

    def test_config_service_is_class(self) -> None:
        """Проверяет что ConfigService — класс."""
        assert isinstance(ConfigService, type), "ConfigService должен быть классом"

    def test_config_service_has_required_methods(self) -> None:
        """Проверяет что ConfigService имеет требуемые методы."""
        required_methods = ["merge_configs", "load_config", "save_config"]

        for method_name in required_methods:
            assert hasattr(ConfigService, method_name), (
                f"ConfigService должен иметь метод '{method_name}'"
            )

    def test_config_service_methods_are_static(self) -> None:
        """Проверяет что методы ConfigService статические."""
        assert isinstance(ConfigService.__dict__.get("merge_configs"), staticmethod), (
            "merge_configs должен быть staticmethod"
        )

        assert isinstance(ConfigService.__dict__.get("load_config"), staticmethod), (
            "load_config должен быть staticmethod"
        )

        assert isinstance(ConfigService.__dict__.get("save_config"), staticmethod), (
            "save_config должен быть staticmethod"
        )


class TestConfigServiceMergeConfigs:
    """Тесты на проверку метода merge_configs."""

    def test_config_service_merge_configs(self) -> None:
        """Проверяет что merge_configs работает корректно."""
        # Создаём две конфигурации
        source = Configuration(chrome={"headless": True}, parser={"max_records": 100})
        target = Configuration(
            chrome={"headless": False, "memory_limit": 256}, parser={"max_records": 50}
        )

        # Объединяем
        ConfigService.merge_configs(source, target)

        # Проверяем что target обновился значениями из source
        assert target.chrome.headless is True, "headless должен обновиться из source"
        assert target.chrome.memory_limit == 256, "memory_limit должен сохраниться"
        assert target.parser.max_records == 100, "max_records должен обновиться из source"

    def test_merge_configs_with_empty_source(self) -> None:
        """Проверяет merge_configs с пустой source конфигурацией."""
        source = Configuration()
        target = Configuration(chrome={"headless": True})

        ConfigService.merge_configs(source, target)

        # target не должен измениться
        assert target.chrome.headless is True

    def test_merge_configs_with_nested_models(self) -> None:
        """Проверяет merge_configs с вложенными моделями."""
        source = Configuration(
            chrome={"headless": True, "memory_limit": 512}, writer={"encoding": "utf-8"}
        )
        target = Configuration(
            chrome={"headless": False}, writer={"encoding": "latin-1", "verbose": True}
        )

        ConfigService.merge_configs(source, target)

        assert target.chrome.headless is True
        assert target.chrome.memory_limit == 512
        assert target.writer.encoding == "utf-8"
        assert target.writer.verbose is True

    def test_merge_configs_max_depth(self) -> None:
        """Проверяет что merge_configs поддерживает max_depth параметр."""
        source = Configuration()
        target = Configuration()

        # Не должно вызывать исключений
        ConfigService.merge_configs(source, target, max_depth=50)
        ConfigService.merge_configs(source, target, max_depth=100)

    def test_merge_configs_only_set_fields(self) -> None:
        """Проверяет что merge_configs обновляет только установленные поля."""
        source = Configuration(chrome={"headless": True})
        target = Configuration(chrome={"headless": False, "memory_limit": 256})

        ConfigService.merge_configs(source, target)

        # headless должен обновиться (установлен в source)
        assert target.chrome.headless is True
        # memory_limit должен сохраниться (не установлен в source)
        assert target.chrome.memory_limit == 256


class TestConfigServiceLoadConfig:
    """Тесты на проверку метода load_config."""

    def test_config_service_load_config(self) -> None:
        """Проверяет что load_config работает корректно."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"

            # Создаём тестовую конфигурацию
            original_config = Configuration(
                chrome={"headless": True, "memory_limit": 512}, parser={"max_records": 100}
            )

            # Сохраняем
            ConfigService.save_config(original_config, config_path)

            # Загружаем
            loaded_config = ConfigService.load_config(
                config_cls=Configuration, config_path=config_path, auto_create=False
            )

            # Проверяем
            assert loaded_config.chrome.headless is True
            assert loaded_config.chrome.memory_limit == 512
            assert loaded_config.parser.max_records == 100

    def test_load_config_auto_create(self) -> None:
        """Проверяет что load_config создаёт конфиг если auto_create=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "new_config.json"

            # Файл не существует, auto_create=True
            config = ConfigService.load_config(
                config_cls=Configuration, config_path=config_path, auto_create=True
            )

            # Конфигурация должна быть создана
            assert config is not None
            assert config_path.exists(), "Файл конфигурации должен быть создан"

    def test_load_config_nonexistent_file_no_auto_create(self) -> None:
        """Проверяет load_config с несуществующим файлом и auto_create=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.json"

            config = ConfigService.load_config(
                config_cls=Configuration, config_path=config_path, auto_create=False
            )

            # Должна вернуться конфигурация по умолчанию
            assert config is not None
            assert isinstance(config, Configuration)

    def test_load_config_invalid_json(self) -> None:
        """Проверяет что load_config обрабатывает невалидный JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid.json"

            # Создаём файл с невалидным JSON
            config_path.write_text("{ invalid json }", encoding="utf-8")

            # Должна вернуться конфигурация по умолчанию
            config = ConfigService.load_config(
                config_cls=Configuration, config_path=config_path, auto_create=False
            )

            assert config is not None
            assert isinstance(config, Configuration)

    def test_load_config_validation_error(self) -> None:
        """Проверяет что load_config обрабатывает ошибки валидации."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid_data.json"

            # Создаём файл с невалидными данными
            invalid_data = {
                "chrome": {
                    "headless": "not_a_boolean",  # Должно быть bool
                    "memory_limit": "not_an_int",  # Должно быть int
                }
            }
            config_path.write_text(json.dumps(invalid_data), encoding="utf-8")

            # Должна вернуться конфигурация по умолчанию
            config = ConfigService.load_config(
                config_cls=Configuration, config_path=config_path, auto_create=False
            )

            assert config is not None
            assert isinstance(config, Configuration)


class TestConfigServiceSaveConfig:
    """Тесты на проверку метода save_config."""

    def test_config_service_save_config(self) -> None:
        """Проверяет что save_config работает корректно."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "save_test.json"

            config = Configuration(
                chrome={"headless": True, "memory_limit": 1024},
                parser={"max_records": 200},
                writer={"encoding": "utf-8-sig"},
            )

            ConfigService.save_config(config, config_path)

            # Проверяем что файл создан
            assert config_path.exists(), "Файл конфигурации должен быть создан"

            # Проверяем содержимое
            content = config_path.read_text(encoding="utf-8")
            data = json.loads(content)

            assert data["chrome"]["headless"] is True
            assert data["chrome"]["memory_limit"] == 1024
            assert data["parser"]["max_records"] == 200
            assert data["writer"]["encoding"] == "utf-8-sig"

    def test_save_config_creates_parent_directories(self) -> None:
        """Проверяет что save_config создаёт родительские директории."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "dir" / "config.json"

            config = Configuration()

            ConfigService.save_config(config, config_path)

            assert config_path.exists(), "Файл должен быть создан"
            assert config_path.parent.exists(), "Родительские директории должны быть созданы"

    def test_save_config_none_path(self) -> None:
        """Проверяет что save_config обрабатывает None путь."""
        config = Configuration()

        # Не должно вызывать исключений
        ConfigService.save_config(config, None)  # type: ignore[arg-type]

    def test_save_config_pretty_json(self) -> None:
        """Проверяет что save_config сохраняет JSON с отступами."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "pretty.json"

            config = Configuration()

            ConfigService.save_config(config, config_path)

            content = config_path.read_text(encoding="utf-8")

            # JSON должен быть отформатирован с отступами
            assert "    " in content, "JSON должен быть отформатирован с отступами"


class TestConfigurationIsPureModel:
    """Тесты на проверку что Configuration — чистая Pydantic модель."""

    def test_configuration_is_pydantic_model(self) -> None:
        """Проверяет что Configuration наследуется от BaseModel."""
        assert issubclass(Configuration, BaseModel), (
            "Configuration должен наследоваться от BaseModel"
        )

    def test_configuration_is_pure_model(self) -> None:
        """Проверяет что Configuration — чистая модель без бизнес-логики.

        Configuration должен содержать только поля и простые валидаторы.
        Бизнес-логика должна быть в ConfigService.
        """
        # Проверяем что у Configuration есть только стандартные методы BaseModel
        # и методы merge_with, save_config, load_config (для backward совместимости)
        allowed_methods = {
            "merge_with",  # Для backward совместимости
            "save_config",  # Для backward совместимости
            "load_config",  # Для backward совместимости
            "_merge_models_iterative",
            "_is_cyclic_reference",
            "_check_depth_limit",
            "_process_fields",
            "_handle_nested_model",
            "_get_fields_set",
            "_backup_corrupted_config",
            "_log_validation_errors",
        }

        # Получаем все методы Configuration
        config_methods = {
            name
            for name in dir(Configuration)
            if not name.startswith("__") and callable(getattr(Configuration, name, None))
        }

        # Проверяем что нет лишних методов (кроме разрешённых и методов BaseModel)
        base_model_methods = {
            name
            for name in dir(BaseModel)
            if not name.startswith("__") and callable(getattr(BaseModel, name, None))
        }

        extra_methods = config_methods - base_model_methods - allowed_methods

        # Допускаем только методы слияния конфигурации
        merge_methods = {
            "_merge_models_iterative",
            "_is_cyclic_reference",
            "_check_depth_limit",
            "_process_fields",
            "_handle_nested_model",
            "_get_fields_set",
            "_backup_corrupted_config",
            "_log_validation_errors",
        }

        # Проверяем что все методы относятся к слиянию или разрешены
        for method in extra_methods:
            assert method in merge_methods or method in allowed_methods, (
                f"Configuration не должен иметь метод '{method}'. "
                "Бизнес-логика должна быть в ConfigService."
            )

    def test_configuration_has_required_fields(self) -> None:
        """Проверяет что Configuration имеет требуемые поля."""
        required_fields = ["log", "writer", "chrome", "parser", "parallel", "path", "version"]

        config = Configuration()

        for field in required_fields:
            assert hasattr(config, field), f"Configuration должен иметь поле '{field}'"

    def test_configuration_fields_have_correct_types(self) -> None:
        """Проверяет что поля Configuration имеют правильные типы."""
        from parser_2gis.chrome import ChromeOptions
        from parser_2gis.logger import LogOptions
        from parser_2gis.parallel import ParallelOptions
        from parser_2gis.parser import ParserOptions
        from parser_2gis.writer import WriterOptions

        config = Configuration()

        assert isinstance(config.log, LogOptions), "log должен быть LogOptions"
        assert isinstance(config.writer, WriterOptions), "writer должен быть WriterOptions"
        assert isinstance(config.chrome, ChromeOptions), "chrome должен быть ChromeOptions"
        assert isinstance(config.parser, ParserOptions), "parser должен быть ParserOptions"
        assert isinstance(config.parallel, ParallelOptions), "parallel должен быть ParallelOptions"

    def test_configuration_validate_assignment(self) -> None:
        """Проверяет что Configuration включает validate_assignment."""
        config = Configuration()

        # model_config должен содержать validate_assignment=True
        assert config.model_config.get("validate_assignment") is True, (
            "Configuration должен иметь validate_assignment=True"
        )

    def test_configuration_cannot_set_invalid_values(self) -> None:
        """Проверяет что Configuration валидирует значения."""
        config = Configuration()

        # Пытаемся установить невалидное значение
        with pytest.raises(Exception):  # pydantic.ValidationError
            config.chrome.memory_limit = "not_an_int"  # type: ignore[assignment]


class TestConfigServiceVsConfiguration:
    """Тесты на сравнение ConfigService и Configuration."""

    def test_config_service_is_separate_from_configuration(self) -> None:
        """Проверяет что ConfigService отделён от Configuration."""
        # ConfigService не должен наследоваться от Configuration
        assert not issubclass(ConfigService, Configuration), (
            "ConfigService не должен наследоваться от Configuration"
        )

        # Configuration не должен наследоваться от ConfigService
        assert not issubclass(Configuration, ConfigService), (
            "Configuration не должен наследоваться от ConfigService"
        )

    def test_config_service_does_not_store_state(self) -> None:
        """Проверяет что ConfigService не хранит состояние."""
        # Все методы должны быть статическими
        service_methods = [
            "merge_configs",
            "load_config",
            "save_config",
            "_merge_models_iterative",
            "_is_cyclic_reference",
            "_check_depth_limit",
            "_process_fields",
            "_handle_nested_model",
            "_get_fields_set",
            "_backup_corrupted_config",
            "_log_validation_errors",
        ]

        for method_name in service_methods:
            method = getattr(ConfigService, method_name, None)
            if method is not None:
                # Проверяем что метод статический
                assert isinstance(ConfigService.__dict__.get(method_name), staticmethod), (
                    f"{method_name} должен быть staticmethod"
                )

    def test_configuration_is_data_only(self) -> None:
        """Проверяет что Configuration содержит только данные."""
        config = Configuration(chrome={"headless": True})

        # Проверяем что данные доступны через model_dump
        dump = config.model_dump()

        assert "chrome" in dump
        assert dump["chrome"]["headless"] is True


__all__ = [
    "TestConfigServiceExists",
    "TestConfigServiceMergeConfigs",
    "TestConfigServiceLoadConfig",
    "TestConfigServiceSaveConfig",
    "TestConfigurationIsPureModel",
    "TestConfigServiceVsConfiguration",
]
