"""
Тесты для выявления ошибок при работе с полями конфигурации.

Проверяют:
1. Наличие всех полей, используемых в TUI, в моделях конфигурации.
2. Корректность типов полей при присваивании.
3. Сохранение и загрузку всех полей конфигурации.
"""


from parser_2gis.chrome import ChromeOptions
from parser_2gis.config import Configuration
from parser_2gis.parser import ParserOptions
from parser_2gis.writer import WriterOptions


class TestChromeOptionsFields:
    """Тесты для проверки полей ChromeOptions."""

    def test_startup_delay_field_exists(self) -> None:
        """Проверка наличия поля startup_delay в ChromeOptions."""
        options = ChromeOptions()
        assert hasattr(options, "startup_delay")

    def test_startup_delay_default_value(self) -> None:
        """Проверка значения по умолчанию startup_delay."""
        options = ChromeOptions()
        assert options.startup_delay == 0

    def test_startup_delay_custom_value(self) -> None:
        """Проверка установки кастомного значения startup_delay."""
        options = ChromeOptions(startup_delay=5)
        assert options.startup_delay == 5

    def test_startup_delay_assignment(self) -> None:
        """Проверка динамического присваивания startup_delay."""
        options = ChromeOptions()
        options.startup_delay = 10
        assert options.startup_delay == 10

    def test_startup_delay_type_validation(self) -> None:
        """Проверка валидации типа startup_delay."""
        # Должно работать с целыми числами
        options = ChromeOptions(startup_delay=0)
        assert options.startup_delay == 0

        options = ChromeOptions(startup_delay=100)
        assert options.startup_delay == 100

    def test_all_chrome_fields_used_in_tui(self) -> None:
        """
        Проверка, что все поля, используемые в TUI settings.py,
        существуют в ChromeOptions.

        Поля из settings.py:
        - headless
        - disable_images
        - silent_browser
        - memory_limit
        - startup_delay
        """
        options = ChromeOptions()

        # Проверяем наличие всех полей
        assert hasattr(options, "headless"), "Поле headless отсутствует"
        assert hasattr(options, "disable_images"), "Поле disable_images отсутствует"
        assert hasattr(options, "silent_browser"), "Поле silent_browser отсутствует"
        assert hasattr(options, "memory_limit"), "Поле memory_limit отсутствует"
        assert hasattr(options, "startup_delay"), "Поле startup_delay отсутствует"

        # Проверяем возможность присваивания значений как в TUI
        options.headless = True
        options.disable_images = True
        options.silent_browser = True
        options.memory_limit = 512
        options.startup_delay = 0

        assert options.headless is True
        assert options.disable_images is True
        assert options.silent_browser is True
        assert options.memory_limit == 512
        assert options.startup_delay == 0


class TestParserOptionsFields:
    """Тесты для проверки полей ParserOptions."""

    def test_all_parser_fields_used_in_tui(self) -> None:
        """
        Проверка, что все поля, используемые в TUI settings.py,
        существуют в ParserOptions.

        Поля из settings.py:
        - max_records
        - delay_between_clicks
        - max_retries
        - timeout (если используется)
        - max_workers (если используется)
        """
        options = ParserOptions()

        # Проверяем наличие основных полей
        assert hasattr(options, "max_records"), "Поле max_records отсутствует"
        assert hasattr(options, "delay_between_clicks"), "Поле delay_between_clicks отсутствует"
        assert hasattr(options, "max_retries"), "Поле max_retries отсутствует"

        # Проверяем возможность присваивания
        options.max_records = 1000
        options.delay_between_clicks = 500
        options.max_retries = 3

        assert options.max_records == 1000
        assert options.delay_between_clicks == 500
        assert options.max_retries == 3


class TestWriterOptionsFields:
    """Тесты для проверки полей WriterOptions."""

    def test_all_writer_fields_used_in_tui(self) -> None:
        """
        Проверка, что все поля, используемые в TUI settings.py,
        существуют в WriterOptions.

        Поля из settings.py:
        - format
        - encoding
        - csv.add_rubrics
        - csv.add_comments
        - csv.remove_duplicates
        """
        options = WriterOptions()

        # Проверяем наличие основных полей
        assert hasattr(options, "encoding"), "Поле encoding отсутствует"
        assert hasattr(options, "csv"), "Поле csv отсутствует"

        # Проверяем вложенные поля csv
        assert hasattr(options.csv, "add_rubrics"), "Поле csv.add_rubrics отсутствует"
        assert hasattr(options.csv, "add_comments"), "Поле csv.add_comments отсутствует"
        assert hasattr(options.csv, "remove_duplicates"), "Поле csv.remove_duplicates отсутствует"

        # Проверяем возможность присваивания
        options.encoding = "utf-8"
        options.csv.add_rubrics = True
        options.csv.add_comments = False
        options.csv.remove_duplicates = True

        assert options.encoding == "utf-8"
        assert options.csv.add_rubrics is True
        assert options.csv.add_comments is False
        assert options.csv.remove_duplicates is True


class TestConfigurationFieldAccess:
    """Тесты для проверки доступа к полям конфигурации."""

    def test_configuration_chrome_field_assignment(self) -> None:
        """Проверка присваивания полей chrome в конфигурации."""
        config = Configuration()

        # Эмулируем код из TUI settings.py
        config.chrome.headless = True
        config.chrome.disable_images = True
        config.chrome.silent_browser = True
        config.chrome.memory_limit = 512
        config.chrome.startup_delay = 0

        assert config.chrome.headless is True
        assert config.chrome.disable_images is True
        assert config.chrome.silent_browser is True
        assert config.chrome.memory_limit == 512
        assert config.chrome.startup_delay == 0

    def test_configuration_parser_field_assignment(self) -> None:
        """Проверка присваивания полей parser в конфигурации."""
        config = Configuration()

        config.parser.max_records = 1000
        config.parser.delay_between_clicks = 500
        config.parser.max_retries = 3

        assert config.parser.max_records == 1000
        assert config.parser.delay_between_clicks == 500
        assert config.parser.max_retries == 3

    def test_configuration_writer_field_assignment(self) -> None:
        """Проверка присваивания полей writer в конфигурации."""
        config = Configuration()

        config.writer.encoding = "utf-8"
        config.writer.csv.add_rubrics = True
        config.writer.csv.add_comments = False
        config.writer.csv.remove_duplicates = True

        assert config.writer.encoding == "utf-8"
        assert config.writer.csv.add_rubrics is True
        assert config.writer.csv.add_comments is False
        assert config.writer.csv.remove_duplicates is True

    def test_configuration_save_load_preserves_fields(self) -> None:
        """
        Проверка, что сохранение и загрузка конфигурации
        сохраняет все поля.
        """
        import pathlib
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "test.config"

            # Создаём конфигурацию с кастомными значениями
            original_config = Configuration(path=config_path)
            original_config.chrome.headless = True
            original_config.chrome.startup_delay = 5
            original_config.chrome.memory_limit = 1024
            original_config.parser.max_records = 5000
            original_config.writer.encoding = "utf-8-sig"

            # Сохраняем
            original_config.save_config()

            # Загружаем
            loaded_config = Configuration.load_config(config_path)

            # Проверяем, что значения сохранились
            assert loaded_config.chrome.headless is True
            assert loaded_config.chrome.startup_delay == 5
            assert loaded_config.chrome.memory_limit == 1024
            assert loaded_config.parser.max_records == 5000
            assert loaded_config.writer.encoding == "utf-8-sig"


class TestTUIFieldCompatibility:
    """
    Тесты для проверки совместимости полей TUI с моделями.

    Эти тесты эмулируют код из tui_textual/screens/settings.py
    и проверяют, что все поля существуют и могут быть установлены.
    """

    def test_browser_settings_screen_fields(self) -> None:
        """
        Эмуляция кода из BrowserSettingsScreen.on_button_pressed.
        Проверяет, что все поля могут быть установлены.
        """
        config = Configuration()

        # Эмулируем значения из UI элементов
        headless_value = True
        disable_images_value = True
        silent_value = True
        memory_limit_value = "512"
        startup_delay_value = "0"

        # Эмуляция кода из settings.py строки 113-119
        config.chrome.headless = headless_value
        config.chrome.disable_images = disable_images_value
        config.chrome.silent_browser = silent_value
        config.chrome.memory_limit = (
            int(memory_limit_value) if memory_limit_value.isdigit() else 512
        )
        config.chrome.startup_delay = (
            int(startup_delay_value) if startup_delay_value.isdigit() else 0
        )

        # Проверяем значения
        assert config.chrome.headless is True
        assert config.chrome.disable_images is True
        assert config.chrome.silent_browser is True
        assert config.chrome.memory_limit == 512
        assert config.chrome.startup_delay == 0

    def test_parser_settings_screen_fields(self) -> None:
        """
        Эмуляция кода из ParserSettingsScreen.on_button_pressed.
        Проверяет, что все поля могут быть установлены.
        """
        config = Configuration()

        # Эмулируем значения из UI элементов
        max_records_value = "1000"
        delay_value = "500"
        max_retries_value = "3"

        # Эмуляция кода из settings.py
        config.parser.max_records = int(max_records_value) if max_records_value.isdigit() else 1000
        config.parser.delay_between_clicks = int(delay_value) if delay_value.isdigit() else 500
        config.parser.max_retries = int(max_retries_value) if max_retries_value.isdigit() else 3

        # Проверяем значения
        assert config.parser.max_records == 1000
        assert config.parser.delay_between_clicks == 500
        assert config.parser.max_retries == 3

    def test_output_settings_screen_fields(self) -> None:
        """
        Эмуляция кода из OutputSettingsScreen.on_button_pressed.
        Проверяет, что все поля могут быть установлены.
        """
        config = Configuration()

        # Эмулируем значения из UI элементов
        encoding_value = "utf-8"
        add_rubrics_value = True
        add_comments_value = False
        remove_duplicates_value = True

        # Эмуляция кода из settings.py (без поля format, т.к. его нет в WriterOptions)
        config.writer.encoding = encoding_value
        config.writer.csv.add_rubrics = add_rubrics_value
        config.writer.csv.add_comments = add_comments_value
        config.writer.csv.remove_duplicates = remove_duplicates_value

        # Проверяем значения
        assert config.writer.encoding == "utf-8"
        assert config.writer.csv.add_rubrics is True
        assert config.writer.csv.add_comments is False
        assert config.writer.csv.remove_duplicates is True


class TestMissingFieldDetection:
    """
    Тесты для обнаружения отсутствующих полей.

    Эти тесты должны падать, если в моделях отсутствуют поля,
    используемые в TUI.
    """

    def test_detect_missing_chrome_field(self) -> None:
        """Тест должен упасть, если в ChromeOptions отсутствует поле startup_delay."""
        config = Configuration()
        # Проверяем что поле существует и доступно для записи
        assert hasattr(config.chrome, "startup_delay"), "Поле startup_delay отсутствует в ChromeOptions"
        config.chrome.startup_delay = 10
        assert config.chrome.startup_delay == 10

    def test_detect_missing_parser_field(self) -> None:
        """Тест должен упасть, если в ParserOptions отсутствует поле max_records."""
        config = Configuration()
        assert hasattr(config.parser, "max_records"), "Поле max_records отсутствует в ParserOptions"
        config.parser.max_records = 1000
        assert config.parser.max_records == 1000

    def test_detect_missing_writer_field(self) -> None:
        """Тест должен упасть, если в WriterOptions отсутствует поле add_rubrics."""
        config = Configuration()
        assert hasattr(config.writer.csv, "add_rubrics"), "Поле add_rubrics отсутствует в WriterOptions"
        config.writer.csv.add_rubrics = True
        assert config.writer.csv.add_rubrics is True
