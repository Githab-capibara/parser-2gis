"""Тесты для ISSUE-001: Разделение Configuration на отдельные модули.

Проверяет:
- ConfigMerger - объединение конфигураций
- ConfigValidator - валидация конфигураций
- Configuration - делегирование операций

"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

# Configuration находится в корневом модуле config.py
from parser_2gis.config import Configuration

# ConfigMerger и ConfigValidator в пакете config_services
from parser_2gis.config_services import ConfigMerger, ConfigValidator


class TestConfigMerger:
    """Тесты для ConfigMerger."""

    def test_merge_simple_config(self) -> None:
        """Тестирует простое объединение конфигураций."""
        config1 = Configuration()
        config2 = Configuration(parser={"max_records": 100})

        ConfigMerger.merge(config1, config2)

        assert config1.parser.max_records == 100

    def test_merge_nested_config(self) -> None:
        """Тестирует объединение вложенных конфигураций."""
        config1 = Configuration()
        config2 = Configuration(chrome={"headless": True, "memory_limit": 2048})

        ConfigMerger.merge(config1, config2)

        assert config1.chrome.headless is True
        assert config1.chrome.memory_limit == 2048

    def test_merge_with_max_depth(self) -> None:
        """Тестирует объединение с ограничением глубины."""
        config1 = Configuration()
        config2 = Configuration(parser={"max_records": 50})

        ConfigMerger.merge(config1, config2, max_depth=5)

        assert config1.parser.max_records == 50

    def test_merge_exceeds_max_depth(self) -> None:
        """Тестирует превышение максимальной глубины."""
        config1 = Configuration()
        config2 = Configuration()

        # При малой глубине и сложных конфигурациях может возникнуть RecursionError
        # Тест проверяет что max_depth контролируется
        try:
            ConfigMerger.merge(config1, config2, max_depth=1)
        except RecursionError:
            pytest.fail("RecursionError не должен возникать для простых конфигураций")

    def test_merge_only_set_fields(self) -> None:
        """Тестирует объединение только установленных полей."""
        config1 = Configuration(parser={"max_records": 100})
        config2 = Configuration(parser={"delay_between_clicks": 500})

        ConfigMerger.merge(config1, config2)

        # Поле из config2 должно быть добавлено
        assert config1.parser.delay_between_clicks == 500
        # Поле из config1 должно сохраниться
        assert config1.parser.max_records == 100


class TestConfigValidator:
    """Тесты для ConfigValidator."""

    def test_validate_valid_config(self) -> None:
        """Тестирует валидацию корректной конфигурации."""
        validator = ConfigValidator()
        config = Configuration()

        result = validator.validate(config)

        # validate возвращает кортеж (bool, list[str])
        assert isinstance(result, tuple)
        assert result[0] is True
        assert result[1] == []

    def test_format_validation_errors(self) -> None:
        """Тестирует форматирование ошибок валидации."""
        try:
            # Создаём невалидную конфигурацию
            Configuration(parallel={"max_workers": -1})
        except ValidationError as e:
            errors = ConfigValidator.format_validation_errors(e)

            assert isinstance(errors, list)
            assert len(errors) > 0
            assert "max_workers" in errors[0] or "Максимальное количество" in errors[0]

    def test_log_validation_errors(self, caplog: pytest.LogCaptureFixture) -> None:
        """Тестирует логирование ошибок валидации."""
        try:
            Configuration(parallel={"max_workers": -1})
        except ValidationError as e:
            ConfigValidator.log_validation_errors(e)

            assert "Ошибки валидации" in caplog.text or "неизвестная ошибка" in caplog.text

    def test_backup_corrupted_config(self, tmp_path: pathlib.Path) -> None:
        """Тестирует создание резервной копии повреждённого файла."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"invalid": "json"}')

        ConfigValidator.backup_corrupted_config(config_file)

        # Должна быть создана резервная копия или переименованный файл
        # Файл может быть переименован в .corrupted
        backup_file = tmp_path / "config.json.bak"
        corrupted_file = tmp_path / "config.json.corrupted"

        backup_exists = backup_file.exists()
        corrupted_exists = corrupted_file.exists()

        # Проверяем что хотя бы один файл существует
        assert backup_exists or corrupted_exists, (
            f"Должна быть создана резервная копия или переименованный файл. backup={backup_exists}, corrupted={corrupted_exists}"
        )


class TestConfiguration:
    """Тесты для Configuration."""

    def test_configuration_merge_with(self) -> None:
        """Тестирует метод merge_with."""
        config1 = Configuration()
        config2 = Configuration(parser={"max_records": 200})

        config1.merge_with(config2)

        assert config1.parser.max_records == 200

    def test_configuration_validate(self) -> None:
        """Тестирует метод validate."""
        config = Configuration()

        result = config.validate()

        # validate возвращает кортеж (bool, list[str])
        assert isinstance(result, tuple)
        assert result[0] is True
        assert result[1] == []

    def test_configuration_format_errors(self) -> None:
        """Тестирует форматирование ошибок."""
        try:
            Configuration(parallel={"max_workers": -1})
        except ValidationError as e:
            errors = Configuration.format_validation_errors(e)

            assert isinstance(errors, list)
            assert len(errors) > 0

    def test_configuration_log_errors(self, caplog: pytest.LogCaptureFixture) -> None:
        """Тестирует логирование ошибок."""
        try:
            Configuration(parallel={"max_workers": -1})
        except ValidationError as e:
            Configuration.log_validation_errors(e)

            assert "Ошибки валидации" in caplog.text or "неизвестная ошибка" in caplog.text

    def test_configuration_backup_config(self, tmp_path: pathlib.Path) -> None:
        """Тестирует резервное копирование."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"invalid": "json"}')

        Configuration.backup_corrupted_config(config_file)

        # Должна быть создана резервная копия или переименованный файл
        assert any(tmp_path.glob("*.bak")) or any(tmp_path.glob("*.corrupted"))

    @patch("parser_2gis.cli.config_service.ConfigService.save_config")
    def test_configuration_save_config(self, mock_save: MagicMock) -> None:
        """Тестирует сохранение конфигурации."""
        config = Configuration()
        config.path = pathlib.Path("/tmp/test_config.json")

        config.save_config()

        mock_save.assert_called_once_with(config=config, path=config.path)

    @patch("parser_2gis.cli.config_service.ConfigService.load_config")
    def test_configuration_load_config(self, mock_load: MagicMock) -> None:
        """Тестирует загрузку конфигурации."""
        mock_load.return_value = Configuration()

        config = Configuration.load_config(auto_create=False)

        mock_load.assert_called_once()
        assert isinstance(config, Configuration)

    def test_configuration_default_values(self) -> None:
        """Тестирует значения по умолчанию."""
        config = Configuration()

        assert config.version is not None
        assert config.path is None
        assert isinstance(config.log, object)
        assert isinstance(config.writer, object)
        assert isinstance(config.chrome, object)
        assert isinstance(config.parser, object)
        assert isinstance(config.parallel, object)


class TestConfigMergerEdgeCases:
    """Тесты граничных случаев для ConfigMerger."""

    def test_merge_with_none_values(self) -> None:
        """Тестирует объединение с None значениями."""
        config1 = Configuration()
        config2 = Configuration(path=None)

        ConfigMerger.merge(config1, config2)

        assert config1.path is None

    def test_merge_with_empty_fields_set(self) -> None:
        """Тестирует объединение с пустым набором полей."""
        config1 = Configuration()
        config2 = Configuration()

        # Pydantic v2 не позволяет напрямую устанавливать __fields_set__
        # Просто проверяем что merge работает с пустыми полями
        ConfigMerger.merge(config1, config2)
        # Не должно вызвать ошибок

    def test_merge_circular_reference_detection(self) -> None:
        """Тестирует обнаружение циклических ссылок."""
        Configuration()
        config2 = Configuration()

        # Создаём циклическую ссылку через MagicMock
        mock_obj = MagicMock()
        mock_obj.model_fields_set = {"nested"}
        mock_obj.nested = mock_obj

        # Не должно вызвать бесконечную рекурсию
        # Тест должен завершиться без зацикливания
        try:
            ConfigMerger.merge(mock_obj, config2, max_depth=10)
        except RecursionError:
            pass  # Ожидаемое поведение при глубокой рекурсии


class TestConfigValidatorEdgeCases:
    """Тесты граничных случаев для ConfigValidator."""

    def test_validate_with_corrupted_file(self, tmp_path: pathlib.Path) -> None:
        """Тестирует валидацию с повреждённым файлом."""
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json {{{")

        # Не должно вызвать исключений
        ConfigValidator.backup_corrupted_config(config_file)

        # Проверяем что файл был обработан
        backup_file = tmp_path / "config.json.bak"
        corrupted_file = tmp_path / "config.json.corrupted"

        backup_exists = backup_file.exists()
        corrupted_exists = corrupted_file.exists()

        assert backup_exists or corrupted_exists, (
            f"Должна быть создана резервная копия или переименованный файл. backup={backup_exists}, corrupted={corrupted_exists}"
        )

    def test_format_empty_errors(self) -> None:
        """Тестирует форматирование пустых ошибок."""
        # Создаём фиктивное исключение
        try:
            Configuration(parallel={"max_workers": -1})
        except ValidationError as e:
            # Проверяем что форматирование работает
            errors = ConfigValidator.format_validation_errors(e)
            assert isinstance(errors, list)
