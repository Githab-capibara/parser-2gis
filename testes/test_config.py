"""
Тесты для модуля config.py.

Проверяют следующие возможности:
- Создание конфигурации
- Загрузка конфигурации
- Сохранение конфигурации
- Слияние конфигураций
- Валидация конфигурации
"""

import json
import pathlib
import tempfile

import pytest
from pydantic import ValidationError

from parser_2gis.config import Configuration


class TestConfigurationCreation:
    """Тесты для создания конфигурации."""

    def test_create_default_config(self):
        """Проверка создания конфигурации по умолчанию."""
        config = Configuration()
        assert config.log is not None
        assert config.writer is not None
        assert config.chrome is not None
        assert config.parser is not None
        assert config.version == '0.1'

    def test_config_path_is_none_by_default(self):
        """Проверка, что path=None по умолчанию."""
        config = Configuration()
        assert config.path is None

    def test_config_with_custom_path(self):
        """Проверка создания конфигурации с указанным путём."""
        custom_path = pathlib.Path('/tmp/test.config')
        config = Configuration(path=custom_path)
        assert config.path == custom_path


class TestConfigurationSaveLoad:
    """Тесты для сохранения и загрузки конфигурации."""

    def test_save_config(self):
        """Проверка сохранения конфигурации."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'test.config'
            config = Configuration(path=config_path)
            config.save_config()

            assert config_path.exists()
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert 'version' in data
            assert 'log' in data
            assert 'writer' in data

    def test_load_config_auto_create(self):
        """Проверка автоматического создания конфигурации."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'test.config'
            config = Configuration.load_config(config_path, auto_create=True)

            assert config_path.exists()
            assert config.path == config_path

    def test_load_config_existing(self):
        """Проверка загрузки существующей конфигурации."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'test.config'

            # Создаём и сохраняем конфигурацию
            original_config = Configuration(path=config_path)
            original_config.chrome.headless = True
            original_config.save_config()

            # Загружаем конфигурацию
            loaded_config = Configuration.load_config(config_path)

            assert loaded_config.chrome.headless is True
            assert loaded_config.path == config_path

    def test_load_config_invalid_json(self):
        """Проверка загрузки с невалидным JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'test.config'

            # Создаём невалидный JSON
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write('{ invalid json }')

            # Должна загрузиться конфигурация по умолчанию
            config = Configuration.load_config(config_path)
            assert isinstance(config, Configuration)

    def test_load_config_invalid_validation(self):
        """Проверка загрузки с ошибкой валидации."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'test.config'

            # Создаём JSON с невалидными данными
            invalid_data = {
                'chrome': {
                    'headless': 'not_a_boolean',  # Должно быть True/False
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(invalid_data, f)

            # Должна загрузиться конфигурация по умолчанию
            config = Configuration.load_config(config_path)
            assert isinstance(config, Configuration)


class TestConfigurationMerge:
    """Тесты для слияния конфигураций."""

    def test_merge_simple_values(self):
        """Проверка слияния простых значений."""
        config1 = Configuration()
        config2 = Configuration()
        config2.chrome.headless = True

        # Используем model_dump() для Pydantic v2 или dict() для v1
        if hasattr(config1, 'model_dump'):
            config1_dict = config1.model_dump()
        else:
            config1_dict = config1.dict()
        config1_dict['chrome']['headless'] = True

        config_merged = Configuration(**config1_dict)
        assert config_merged.chrome.headless is True

    def test_merge_nested_values(self):
        """Проверка слияния вложенных значений."""
        config1 = Configuration()
        if hasattr(config1, 'model_dump'):
            config1_dict = config1.model_dump()
        else:
            config1_dict = config1.dict()
        config1_dict['parser']['max_records'] = 100
        config1_dict['parser']['delay_between_clicks'] = 500

        config_merged = Configuration(**config1_dict)
        assert config_merged.parser.max_records == 100
        assert config_merged.parser.delay_between_clicks == 500

    def test_merge_preserves_original(self):
        """Проверка, что слияние не меняет исходную конфигурацию."""
        config1 = Configuration()
        config2 = Configuration()
        config2.chrome.headless = True

        original_headless = config1.chrome.headless
        if hasattr(config1, 'model_dump'):
            config1_dict = config1.model_dump()
        else:
            config1_dict = config1.dict()
        config1_dict['chrome']['headless'] = True
        config_merged = Configuration(**config1_dict)

        # config1 не должен измениться
        assert config1.chrome.headless == original_headless
        # config_merged должен иметь новое значение
        assert config_merged.chrome.headless is True


class TestConfigurationValidation:
    """Тесты для валидации конфигурации."""

    def test_validation_invalid_headless(self):
        """Проверка валидации невалидного headless."""
        with pytest.raises(ValidationError):
            Configuration(chrome={'headless': 'invalid'})

    def test_validation_invalid_memory_limit(self):
        """Проверка валидации невалидного memory_limit."""
        with pytest.raises(ValidationError):
            Configuration(chrome={'memory_limit': -1})

    def test_validation_invalid_max_records(self):
        """Проверка валидации невалидного max_records."""
        with pytest.raises(ValidationError):
            Configuration(parser={'max_records': 0})

    def test_validation_valid_config(self):
        """Проверка валидации корректной конфигурации."""
        config = Configuration(
            chrome={
                'headless': True,
                'memory_limit': 512,
                'disable_images': True,
                'start_maximized': False,
            },
            parser={
                'max_records': 100,
                'delay_between_clicks': 500,
                'skip_404_response': True,
            }
        )
        assert config.chrome.headless is True
        assert config.chrome.memory_limit == 512
        assert config.parser.max_records == 100


class TestConfigurationAutoCreate:
    """Тесты для автоматического создания конфигурации."""

    def test_load_nonexistent_with_auto_create(self):
        """Проверка загрузки с авто-созданием."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'nonexistent.config'
            config = Configuration.load_config(config_path, auto_create=True)

            assert config_path.exists()
            assert config.path == config_path

    def test_load_nonexistent_without_auto_create(self):
        """Проверка загрузки без авто-создания."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'nonexistent.config'
            config = Configuration.load_config(config_path, auto_create=False)

            assert not config_path.exists()
            assert config.path is None


class TestConfigurationVersion:
    """Тесты для версии конфигурации."""

    def test_config_version(self):
        """Проверка версии конфигурации."""
        config = Configuration()
        assert config.version == '0.1'

    def test_config_version_in_json(self):
        """Проверка версии в JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / 'test.config'
            config = Configuration(path=config_path)
            config.save_config()

            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert data['version'] == '0.1'
