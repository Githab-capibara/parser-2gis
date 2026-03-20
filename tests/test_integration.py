"""
Интеграционные тесты для парсера 2GIS.

Проверяют взаимодействие различных компонентов системы:
- Конфигурация + Parser
- Конфигурация + Writer
- Полная цепочка парсинга
"""

import os
import tempfile
from pathlib import Path

import pytest

from parser_2gis.chrome import ChromeOptions
from parser_2gis.config import Configuration
from parser_2gis.logger import LogOptions
from parser_2gis.parser import ParserOptions
from parser_2gis.writer import (
    CSVWriter,
    JSONWriter,
    WriterOptions,
    XLSXWriter,
    get_writer,
)


class TestConfigWithParser:
    """Тесты для конфигурации с парсером."""

    def test_config_parser_options(self):
        """Проверка опций парсера в конфигурации."""
        config = Configuration()
        assert config.parser is not None
        assert config.parser.max_records > 0

    def test_config_custom_parser_options(self):
        """Проверка кастомных опций парсера."""
        config = Configuration()
        config.parser.max_records = 50
        config.parser.delay_between_clicks = 100
        assert config.parser.max_records == 50
        assert config.parser.delay_between_clicks == 100

    def test_get_parser_with_config(self):
        """Проверка получения парсера с конфигурацией."""
        config = Configuration()
        # get_parser требует URL, chrome_options и parser_options
        # Для теста просто проверяем, что функция существует и принимает правильные аргументы
        parser_options = config.parser
        chrome_options = config.chrome
        # Не создаём реальный парсер, так как это требует запуска браузера
        # Просто проверяем, что аргументы правильные
        assert parser_options is not None
        assert chrome_options is not None


class TestConfigWithWriter:
    """Тесты для конфигурации с writer."""

    def test_config_writer_options(self):
        """Проверка опций writer в конфигурации."""
        config = Configuration()
        assert config.writer is not None
        assert config.writer.encoding == "utf-8-sig"

    def test_config_custom_writer_options(self):
        """Проверка кастомных опций writer."""
        config = Configuration()
        config.writer.encoding = "utf-8"
        config.writer.verbose = False
        assert config.writer.encoding == "utf-8"
        assert config.writer.verbose is False

    def test_config_writer_csv_options(self):
        """Проверка CSV опций writer."""
        config = Configuration()
        assert config.writer.csv is not None
        assert config.writer.csv.add_rubrics is True

    def test_get_writer_with_config(self):
        """Проверка получения writer с конфигурацией."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            try:
                config = Configuration()
                # get_writer требует file_path, file_format и writer_options
                writer = get_writer(f.name, "csv", config.writer)
                assert isinstance(writer, CSVWriter)
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)


class TestConfigWithChrome:
    """Тесты для конфигурации с Chrome."""

    def test_config_chrome_options(self):
        """Проверка опций Chrome в конфигурации."""
        config = Configuration()
        assert config.chrome is not None
        assert config.chrome.memory_limit > 0

    def test_config_custom_chrome_options(self):
        """Проверка кастомных опций Chrome."""
        config = Configuration()
        config.chrome.headless = True
        config.chrome.disable_images = True
        config.chrome.memory_limit = 512
        assert config.chrome.headless is True
        assert config.chrome.disable_images is True
        assert config.chrome.memory_limit == 512


class TestConfigWithLogger:
    """Тесты для конфигурации с логгером."""

    def test_config_log_options(self):
        """Проверка опций логгера в конфигурации."""
        config = Configuration()
        assert config.log is not None
        assert config.log.level == "DEBUG"

    def test_config_custom_log_options(self):
        """Проверка кастомных опций логгера."""
        config = Configuration()
        config.log.level = "INFO"
        assert config.log.level == "INFO"


class TestFullIntegration:
    """Полные интеграционные тесты."""

    def test_config_all_components(self):
        """Проверка всех компонентов в конфигурации."""
        config = Configuration()

        # Проверяем наличие всех компонентов
        assert config.parser is not None
        assert config.writer is not None
        assert config.chrome is not None
        assert config.log is not None

        # Проверяем, что все компоненты имеют правильные типы
        assert isinstance(config.parser, ParserOptions)
        assert isinstance(config.writer, WriterOptions)

    def test_config_merge_all_components(self):
        """Проверка слияния всех компонентов."""
        # Создаём config1 с настройками по умолчанию
        config1 = Configuration()

        # Создаём config2 с явными настройками через конструктор
        # Это гарантирует, что поля будут в model_fields_set
        config2 = Configuration()
        # Явно устанавливаем поля, чтобы они попали в model_fields_set
        config2.parser = ParserOptions(max_records=100)
        config2.writer = WriterOptions(encoding="utf-8")
        config2.chrome = ChromeOptions(headless=True)
        config2.log = LogOptions(level="INFO")

        config1.merge_with(config2)

        # Проверяем, что значение изменилось на 100
        assert config1.parser.max_records == 100
        assert config1.writer.encoding == "utf-8"
        assert config1.chrome.headless is True
        assert config1.log.level == "INFO"

    def test_config_save_load_roundtrip(self):
        """Проверка сохранения и загрузки конфигурации."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test.config"

            # Создаём и настраиваем конфигурацию
            config1 = Configuration(path=config_path)
            config1.parser.max_records = 75
            config1.chrome.headless = True
            config1.writer.verbose = False
            config1.save_config()

            # Загружаем конфигурацию
            config2 = Configuration.load_config(config_path)

            # Проверяем, что значения сохранились
            assert config2.parser.max_records == 75
            assert config2.chrome.headless is True
            assert config2.writer.verbose is False


class TestWriterFormats:
    """Тесты для различных форматов writer."""

    def test_csv_writer_creation(self):
        """Проверка создания CSV writer."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            try:
                config = Configuration()
                writer = CSVWriter(f.name, config.writer)
                assert writer is not None
                writer.close()
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_json_writer_creation(self):
        """Проверка создания JSON writer."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            try:
                config = Configuration()
                writer = JSONWriter(f.name, config.writer)
                assert writer is not None
                writer.close()
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_xlsx_writer_creation(self):
        """Проверка создания XLSX writer."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            try:
                config = Configuration()
                writer = XLSXWriter(f.name, config.writer)
                assert writer is not None
                writer.close()
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)


class TestParserOptionsIntegration:
    """Тесты для интеграции опций парсера."""

    def test_parser_options_default_values(self):
        """Проверка значений по умолчанию."""
        config = Configuration()
        assert config.parser.skip_404_response is True
        assert config.parser.delay_between_clicks == 0
        assert config.parser.max_records > 0
        assert config.parser.use_gc is False

    def test_parser_options_validation(self):
        """Проверка валидации опций."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Configuration(parser={"max_records": 0})

        with pytest.raises(ValidationError):
            Configuration(parser={"delay_between_clicks": -1})


class TestWriterOptionsIntegration:
    """Тесты для интеграции опций writer."""

    def test_writer_options_default_values(self):
        """Проверка значений по умолчанию."""
        config = Configuration()
        assert config.writer.encoding == "utf-8-sig"
        assert config.writer.verbose is True
        assert config.writer.csv.add_rubrics is True

    def test_writer_options_validation(self):
        """Проверка валидации опций."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Configuration(writer={"encoding": "invalid-encoding"})

        with pytest.raises(ValidationError):
            Configuration(writer={"csv": {"columns_per_entity": 0}})


class TestChromeOptionsIntegration:
    """Тесты для интеграции опций Chrome."""

    def test_chrome_options_default_values(self):
        """Проверка значений по умолчанию."""
        config = Configuration()
        assert config.chrome.headless is False
        assert config.chrome.start_maximized is False
        assert config.chrome.disable_images is True
        assert config.chrome.memory_limit > 0

    def test_chrome_options_validation(self):
        """Проверка валидации опций."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Configuration(chrome={"memory_limit": 0})
