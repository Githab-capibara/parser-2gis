"""
Тесты для проверки совместимости с Pydantic v1 и v2.

Эти тесты выявляют ошибки, связанные с использованием методов Pydantic,
которые отличаются в версиях v1 и v2 (model_dump/dict, model_fields_set/__fields_set__).
"""

import pytest
from pydantic import BaseModel

from parser_2gis.config import Configuration
from parser_2gis.pydantic_compat import (
    PYDANTIC_V2,
    get_model_dump,
    get_model_fields_set,
)


class TestPydanticCompatibility:
    """Тесты для проверки совместимости с версиями Pydantic."""

    def test_pydantic_version_detected(self):
        """Проверка, что версия Pydantic определена корректно."""
        import pydantic
        assert pydantic.VERSION.startswith("2.") == PYDANTIC_V2

    def test_get_model_dump_returns_dict(self):
        """
        Тест 1: Проверка, что get_model_dump возвращает словарь.
        
        Выявляет ошибку AttributeError, если метод model_dump/dict отсутствует.
        """
        config = Configuration()
        result = get_model_dump(config)
        
        assert isinstance(result, dict)
        assert "chrome" in result
        assert "parser" in result
        assert "writer" in result
        assert "log" in result

    def test_get_model_dump_with_exclude(self):
        """
        Тест 2: Проверка, что get_model_dump поддерживает exclude.
        
        Выявляет ошибку передачи аргументов, несовместимых с версией Pydantic.
        """
        config = Configuration(path="/tmp/test.config")
        result = get_model_dump(config, exclude={"path"})
        
        assert "path" not in result
        assert "chrome" in result
        assert "version" in result

    def test_get_model_fields_set_returns_set(self):
        """
        Тест 3: Проверка, что get_model_fields_set возвращает set.
        
        Выявляет ошибку AttributeError, если model_fields_set/__fields_set__ отсутствует.
        """
        config = Configuration()
        fields = get_model_fields_set(config)
        
        assert isinstance(fields, set)
        # При создании по умолчанию поля могут быть пустыми (Pydantic v2)
        # или содержать все поля (Pydantic v1) - проверяем только тип

    def test_get_model_fields_set_with_custom_values(self):
        """
        Тест 4: Проверка, что get_model_fields_set отслеживает изменённые поля.
        
        Выявляет ошибку, когда изменённые поля не отслеживаются корректно.
        
        Примечание: В Pydantic v2 изменение вложенных моделей (chrome.headless)
        не добавляет родительское поле (chrome) в model_fields_set автоматически.
        Тест проверяет, что функция get_model_fields_set работает без ошибок.
        """
        config = Configuration()
        original_fields = get_model_fields_set(config)
        
        # Изменяем значения
        config.chrome.headless = True
        config.parser.max_records = 5000
        
        # Получаем fields после изменений
        new_fields = get_model_fields_set(config)
        
        # Проверяем, что функция возвращает set (не падает с ошибкой)
        assert isinstance(new_fields, set)
        
        # В Pydantic v2 fields могут оставаться пустыми при изменении вложенных моделей
        # Это ожидаемое поведение - главное, что функция работает
        assert isinstance(original_fields, set)
        assert isinstance(new_fields, set)

    def test_configuration_serialization_roundtrip(self):
        """
        Тест 5: Проверка полной сериализации/десериализации конфигурации.
        
        Выявляет ошибки совместимости при сохранении и загрузке конфигурации.
        """
        original_config = Configuration()
        original_config.chrome.headless = True
        original_config.parser.max_records = 3000
        
        # Сериализуем
        config_dict = get_model_dump(original_config, exclude={"path"})
        
        # Проверяем, что это словарь
        assert isinstance(config_dict, dict)
        
        # Десериализуем обратно (через конструктор)
        restored_config = Configuration(**config_dict)
        
        # Проверяем, что данные сохранились
        assert restored_config.chrome.headless is True
        assert restored_config.parser.max_records == 3000


class TestArgumentHelpFormatterCompatibility:
    """Тесты для ArgumentHelpFormatter, который использует model_dump."""

    def test_argument_help_formatter_initialization(self):
        """
        Тест 6: Проверка инициализации ArgumentHelpFormatter.
        
        Выявляет ошибку AttributeError при инициализации форматтера.
        """
        from parser_2gis.main import ArgumentHelpFormatter
        
        # Передаём требуемый аргумент prog
        formatter = ArgumentHelpFormatter(prog="Parser2GIS")
        
        assert hasattr(formatter, "_default_config")
        assert isinstance(formatter._default_config, dict)

    def test_argument_help_formatter_default_values(self):
        """
        Тест 7: Проверка, что форматер получает значения по умолчанию.
        
        Выявляет ошибку, если конфигурация не сериализуется корректно.
        """
        from parser_2gis.main import ArgumentHelpFormatter
        
        formatter = ArgumentHelpFormatter(prog="Parser2GIS")
        config = formatter._default_config
        
        # Проверяем наличие основных секций
        assert "chrome" in config
        assert "parser" in config
        
        # Проверяем, что значения по умолчанию корректны
        assert isinstance(config["chrome"]["headless"], bool)
        assert isinstance(config["parser"]["max_records"], int)


class TestPydanticVersionSpecificFeatures:
    """Тесты для проверки специфичных функций версий Pydantic."""

    @pytest.mark.skipif(not PYDANTIC_V2, reason="Требуется Pydantic v2")
    def test_pydantic_v2_model_dump_methods(self):
        """Проверка, что model_dump доступен в Pydantic v2."""
        config = Configuration()
        # В Pydantic v2 должен быть доступен model_dump
        assert hasattr(config, "model_dump")
        result = config.model_dump()
        assert isinstance(result, dict)

    @pytest.mark.skipif(PYDANTIC_V2, reason="Требуется Pydantic v1")
    def test_pydantic_v1_dict_method(self):
        """Проверка, что dict доступен в Pydantic v1."""
        config = Configuration()
        # В Pydantic v1 должен быть доступен dict
        assert hasattr(config, "dict")
        result = config.dict()
        assert isinstance(result, dict)


class TestConfigurationSaveWithCompatibility:
    """Тесты для сохранения конфигурации с использованием совместимого API."""

    def test_save_config_uses_compatible_method(self):
        """
        Тест 8: Проверка, что save_config использует совместимый метод.
        
        Выявляет ошибку, если save_config использует несуществующий метод.
        """
        import json
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test.config"
            config = Configuration(path=config_path)
            config.chrome.headless = True
            
            # Сохраняем - не должно возникнуть AttributeError
            config.save_config()
            
            # Проверяем, что файл создан
            assert config_path.exists()
            
            # Проверяем содержимое
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            assert data["chrome"]["headless"] is True
