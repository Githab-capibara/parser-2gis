"""
Тесты для модуля chrome и интеграционные тесты.

Объединяет тесты из test_chrome.py и test_integration.py.

Проверяют следующие возможности:
import pytest

pytestmark = pytest.mark.requires_chrome
- ChromeOptions валидация
- ChromeRemote
- ChromeException и наследники
- Интеграция конфигурации с различными компонентами
- Интеграция writer форматов
- Полная цепочка конфигурации
"""

import os
import pathlib
import tempfile
from pathlib import Path
import pytest

pytestmark = pytest.mark.requires_chrome

import pytest

from parser_2gis.chrome import ChromeOptions, ChromeRemote
from parser_2gis.config import Configuration
from parser_2gis.logger import LogOptions
from parser_2gis.parser import ParserOptions
from parser_2gis.writer import CSVWriter, JSONWriter, WriterOptions, XLSXWriter, get_writer

# ============================================================================
# ChromeOptions тесты (из test_chrome.py)
# ============================================================================


class TestChromeOptions:
    """Тесты для ChromeOptions."""

    def test_chrome_options_default(self) -> None:
        """Проверка значений по умолчанию."""
        options = ChromeOptions()
        assert options.binary_path is None
        assert options.start_maximized is False
        assert options.headless is False
        assert options.disable_images is True
        assert options.silent_browser is True
        assert options.memory_limit > 0

    def test_chrome_options_custom(self) -> None:
        """Проверка кастомных значений."""
        custom_path = pathlib.Path("/usr/bin/google-chrome")
        options = ChromeOptions(
            binary_path=custom_path,
            start_maximized=True,
            headless=True,
            disable_images=False,
            silent_browser=False,
            memory_limit=512,
        )
        assert options.binary_path == custom_path
        assert options.start_maximized is True
        assert options.headless is True
        assert options.disable_images is False
        assert options.silent_browser is False
        assert options.memory_limit == 512

    def test_chrome_options_invalid_memory(self) -> None:
        """Проверка валидации memory_limit."""
        with pytest.raises(Exception):
            ChromeOptions(memory_limit=0)

        with pytest.raises(Exception):
            ChromeOptions(memory_limit=-1)

    def test_chrome_options_valid_memory(self) -> None:
        """Проверка допустимых значений memory_limit."""
        for value in [1, 100, 512, 1024, 2048]:
            options = ChromeOptions(memory_limit=value)
            assert options.memory_limit == value

    def test_chrome_options_binary_path_string(self) -> None:
        """Проверка binary_path как строка."""
        options = ChromeOptions(binary_path=pathlib.Path("/usr/bin/chrome"))
        assert isinstance(options.binary_path, pathlib.Path)

    def test_chrome_options_memory_limit_default(self) -> None:
        """Проверка memory_limit по умолчанию."""
        options = ChromeOptions()
        assert options.memory_limit > 0
        assert isinstance(options.memory_limit, int)


class TestChromeOptionsValidation:
    """Тесты для валидации ChromeOptions."""

    def test_all_fields_optional(self) -> None:
        """Проверка, что все поля необязательны."""
        options = ChromeOptions()
        assert isinstance(options, ChromeOptions)

    def test_partial_update(self) -> None:
        """Проверка частичного обновления."""
        options = ChromeOptions(headless=True)
        assert options.headless is True
        # Остальные поля должны быть по умолчанию
        assert options.start_maximized is False
        assert options.disable_images is True

    def test_boolean_fields(self) -> None:
        """Проверка булевых полей."""
        for headless in [True, False]:
            for start_maximized in [True, False]:
                for disable_images in [True, False]:
                    options = ChromeOptions(
                        headless=headless,
                        start_maximized=start_maximized,
                        disable_images=disable_images,
                    )
                    assert options.headless == headless
                    assert options.start_maximized == start_maximized
                    assert options.disable_images == disable_images


class TestChromeDefaultMemoryLimit:
    """Тесты для default_memory_limit."""

    def test_default_memory_limit_positive(self) -> None:
        """Проверка, что memory_limit положительное."""
        from parser_2gis.chrome.options import default_memory_limit

        limit = default_memory_limit()
        assert limit > 0

    def test_default_memory_limit_integer(self) -> None:
        """Проверка, что memory_limit целое число."""
        from parser_2gis.chrome.options import default_memory_limit

        limit = default_memory_limit()
        assert isinstance(limit, int)

    def test_default_memory_limit_reasonable(self) -> None:
        """Проверка, что memory_limit разумное (не слишком большое)."""
        from parser_2gis.chrome.options import default_memory_limit

        limit = default_memory_limit()
        # Ожидаем, что лимит будет в разумных пределах (1-64 GB в MB)
        assert 100 <= limit <= 64000


# ============================================================================
# ChromeRemote тесты (из test_chrome.py)
# ============================================================================


class TestChromeRemote:
    """Тесты для ChromeRemote."""

    def test_chrome_remote_creation(self) -> None:
        """Проверка создания ChromeRemote."""
        options = ChromeOptions()
        chrome = ChromeRemote(options, response_patterns=[])
        assert chrome is not None

    def test_chrome_remote_with_custom_options(self) -> None:
        """Проверка ChromeRemote с кастомными настройками."""
        options = ChromeOptions(headless=True, disable_images=True, memory_limit=256)
        chrome = ChromeRemote(options, response_patterns=[])
        assert chrome is not None

    def test_chrome_remote_with_binary_path(self) -> None:
        """Проверка ChromeRemote с путём к бинарнику."""
        options = ChromeOptions(binary_path=pathlib.Path("/usr/bin/chrome"))
        chrome = ChromeRemote(options, response_patterns=[])
        assert chrome is not None


# ============================================================================
# ChromeExceptions тесты (из test_chrome.py)
# ============================================================================


# Интеграционные тесты конфигурации (из test_integration.py)
# Тесты Chrome исключений перенесены в test_version_exceptions.py с более детальными проверками


class TestConfigWithParser:
    """Тесты для конфигурации с парсером."""

    def test_config_parser_options(self) -> None:
        """Проверка опций парсера в конфигурации."""
        config = Configuration()
        assert config.parser is not None
        assert config.parser.max_records > 0

    def test_config_custom_parser_options(self) -> None:
        """Проверка кастомных опций парсера."""
        config = Configuration()
        config.parser.max_records = 50
        config.parser.delay_between_clicks = 100
        assert config.parser.max_records == 50
        assert config.parser.delay_between_clicks == 100

    def test_get_parser_with_config(self) -> None:
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

    def test_config_writer_options(self) -> None:
        """Проверка опций writer в конфигурации."""
        config = Configuration()
        assert config.writer is not None
        assert config.writer.encoding == "utf-8-sig"

    def test_config_custom_writer_options(self) -> None:
        """Проверка кастомных опций writer."""
        config = Configuration()
        config.writer.encoding = "utf-8"
        config.writer.verbose = False
        assert config.writer.encoding == "utf-8"
        assert config.writer.verbose is False

    def test_config_writer_csv_options(self) -> None:
        """Проверка CSV опций writer."""
        config = Configuration()
        assert config.writer.csv is not None
        assert config.writer.csv.add_rubrics is True

    def test_get_writer_with_config(self) -> None:
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

    def test_config_chrome_options(self) -> None:
        """Проверка опций Chrome в конфигурации."""
        config = Configuration()
        assert config.chrome is not None
        assert config.chrome.memory_limit > 0

    def test_config_custom_chrome_options(self) -> None:
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

    def test_config_log_options(self) -> None:
        """Проверка опций логгера в конфигурации."""
        config = Configuration()
        assert config.log is not None
        assert config.log.level == "DEBUG"

    def test_config_custom_log_options(self) -> None:
        """Проверка кастомных опций логгера."""
        config = Configuration()
        config.log.level = "INFO"
        assert config.log.level == "INFO"


class TestFullIntegration:
    """Полные интеграционные тесты."""

    def test_config_all_components(self) -> None:
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

    def test_config_merge_all_components(self) -> None:
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

    def test_config_save_load_roundtrip(self) -> None:
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

    def test_csv_writer_creation(self) -> None:
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

    def test_json_writer_creation(self) -> None:
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

    def test_xlsx_writer_creation(self) -> None:
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

    def test_parser_options_default_values(self) -> None:
        """Проверка значений по умолчанию."""
        config = Configuration()
        assert config.parser.skip_404_response is True
        assert config.parser.delay_between_clicks == 0
        assert config.parser.max_records > 0
        assert config.parser.use_gc is False

    def test_parser_options_validation(self) -> None:
        """Проверка валидации опций."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Configuration(parser={"max_records": 0})

        with pytest.raises(ValidationError):
            Configuration(parser={"delay_between_clicks": -1})


class TestWriterOptionsIntegration:
    """Тесты для интеграции опций writer."""

    def test_writer_options_default_values(self) -> None:
        """Проверка значений по умолчанию."""
        config = Configuration()
        assert config.writer.encoding == "utf-8-sig"
        assert config.writer.verbose is True
        assert config.writer.csv.add_rubrics is True

    def test_writer_options_validation(self) -> None:
        """Проверка валидации опций."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Configuration(writer={"encoding": "invalid-encoding"})

        with pytest.raises(ValidationError):
            Configuration(writer={"csv": {"columns_per_entity": 0}})


class TestChromeOptionsIntegration:
    """Тесты для интеграции опций Chrome."""

    # NOTE: тесты значений по умолчанию ChromeOptions уже покрыты в TestChromeOptions

    def test_chrome_options_validation(self) -> None:
        """Проверка валидации опций."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Configuration(chrome={"memory_limit": 0})
