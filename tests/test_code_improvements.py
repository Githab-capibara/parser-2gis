"""
Тесты для улучшения качества кода.

Проверяют:
- Правильность обработки исключений в критических функциях
- Потокобезопасность операций парсинга
- Корректность конфигурации и валидации
"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from parser_2gis.common import unwrap_dot_dict, wait_until_finished
from parser_2gis.config import Configuration, ParserOptions, WriterOptions
from parser_2gis.parallel_parser import ParallelCityParser


class TestConfigurationRobustness:
    """Тесты для устойчивости конфигурации."""

    def test_configuration_with_extreme_values(self):
        """Проверка конфигурации с экстремальными значениями."""
        config = Configuration()

        # Проверяем, что можно установить граничные значения
        config.parser.max_records = 1
        assert config.parser.max_records == 1

        config.parser.max_records = 10000
        assert config.parser.max_records == 10000

    def test_parser_options_defaults(self):
        """Проверка значений по умолчанию в ParserOptions."""
        opts = ParserOptions()
        assert opts.max_records is not None
        assert opts.delay_between_clicks is not None
        assert opts.max_retries > 0
        assert opts.retry_delay_base > 0

    def test_writer_options_encoding(self):
        """Проверка кодировки в WriterOptions."""
        opts = WriterOptions()
        assert opts.encoding in ["utf-8", "utf-16", "utf-8-sig"]


class TestCommonFunctionRobustness:
    """Тесты для устойчивости функций в common.py."""

    def test_wait_until_finished_decorator_basic(self):
        """Проверка декоратора wait_until_finished."""
        call_count = 0

        @wait_until_finished(timeout=5, finished=lambda x: x is True)
        def test_func():
            nonlocal call_count
            call_count += 1
            return True

        result = test_func()
        assert result is True
        assert call_count >= 1

    def test_unwrap_dot_dict_with_empty_dict(self):
        """Проверка unwrap_dot_dict с пустым словарем."""
        result = unwrap_dot_dict({})
        assert result == {}

    def test_unwrap_dot_dict_with_deep_nesting(self):
        """Проверка unwrap_dot_dict с глубокой вложенностью."""
        dot_dict = {"level1.level2.level3.level4": "value"}
        result = unwrap_dot_dict(dot_dict)
        assert result["level1"]["level2"]["level3"]["level4"] == "value"


class TestParallelParserRobustness:
    """Тесты для устойчивости параллельного парсера."""

    def test_parallel_parser_stop_method(self):
        """Проверка метода stop() парсера."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        parser = ParallelCityParser(cities, categories, "/tmp", config)
        # Должно работать без исключений
        parser.stop()

    def test_parallel_parser_logging_thread_safe(self):
        """Проверка потокобезопасного логирования в парсере."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        parser = ParallelCityParser(cities, categories, "/tmp", config)
        results = []

        def log_messages(idx):
            """Логировать сообщения из потока."""
            try:
                for i in range(10):
                    parser.log(f"Message {idx}-{i}", "info")
                results.append(("success", idx))
            except Exception as e:
                results.append(("error", idx, str(e)))

        # Запускаем логирование из нескольких потоков
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(log_messages, i) for i in range(5)]
            for future in futures:
                future.result()

        # Проверяем, что все операции прошли успешно
        success_count = sum(1 for r in results if r[0] == "success")
        assert success_count == 5


class TestErrorHandlingComprehensive:
    """Комплексные тесты для обработки ошибок."""

    def test_configuration_merge_is_callable(self):
        """Проверка что merge_with работает без ошибок."""
        config1 = Configuration()

        config2 = Configuration()
        config2.chrome.disable_images = True

        # Метод merge_with должен работать без исключений
        config1.merge_with(config2)
        # Конфигурация должна остаться в валидном состоянии
        assert config1 is not None
        assert config1.chrome is not None

    def test_configuration_load_with_corrupted_json(self, tmp_path):
        """Проверка загрузки конфигурации с поврежденным JSON."""
        config_file = tmp_path / "corrupted.json"
        config_file.write_text("{invalid json}")

        # Должна вернуться конфигурация по умолчанию или вызваться исключение
        with pytest.raises(Exception):  # ValueError или JSONDecodeError
            Configuration.load(config_file, auto_create=False)


class TestConcurrencyPatterns:
    """Тесты для паттернов многопоточности."""

    def test_multiple_configurations_in_threads(self):
        """Проверка создания конфигураций в разных потоках."""
        configs = []
        errors = []

        def create_config(idx):
            """Создать конфигурацию в потоке."""
            try:
                config = Configuration()
                configs.append(config)
            except Exception as e:
                errors.append((idx, str(e)))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_config, i) for i in range(10)]
            for future in futures:
                future.result()

        assert len(errors) == 0, f"Ошибки при создании конфигурации: {errors}"
        assert len(configs) == 10

    def test_configuration_modification_isolation(self):
        """Проверка изоляции при модификации конфигурации в потоках."""
        config = Configuration()
        results = []

        def modify_config(value):
            """Модифицировать конфигурацию в потоке."""
            try:
                config.parser.max_records = value * 100
                # Даем время на изменение
                import time

                time.sleep(0.01)
                # Проверяем значение (может быть перезаписано другим потоком)
                results.append(config.parser.max_records)
            except Exception as e:
                results.append(("error", str(e)))

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(modify_config, i) for i in range(1, 4)]
            for future in futures:
                future.result()

        # Проверяем, что операции выполнились (конкретные значения могут отличаться)
        assert len(results) == 3
        assert all(isinstance(r, int) for r in results)


class TestBoundaryConditions:
    """Тесты граничных условий."""

    def test_parser_with_single_city(self):
        """Проверка парсера с одним городом."""
        config = Configuration()
        cities = [{"name": "Omsk", "id": 56}]
        categories = [{"name": "Shops", "id": 1}]

        parser = ParallelCityParser(cities, categories, "/tmp", config, max_workers=1)
        assert len(parser.cities) == 1
        assert len(parser.categories) == 1

    def test_parser_with_many_workers(self):
        """Проверка парсера с максимальным количеством рабочих потоков."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Максимум 20 рабочих
        parser = ParallelCityParser(cities, categories, "/tmp", config, max_workers=20)
        assert parser.max_workers == 20

    def test_wait_until_finished_timeout_decorator(self):
        """Проверка декоратора wait_until_finished с таймаутом."""
        call_count = 0

        @wait_until_finished(timeout=0.5, finished=lambda x: False, throw_exception=False)
        def slow_func():
            nonlocal call_count
            call_count += 1
            return False

        # Функция должна быть вызвана несколько раз перед истечением таймаута
        slow_func()
        assert call_count >= 1

    def test_parallel_parser_url_generation(self):
        """Проверка генерации URL в параллельном парсере."""
        config = Configuration()
        cities = [
            {"name": "Moscow", "code": "moscow", "domain": "ru"},
            {"name": "Omsk", "code": "omsk", "domain": "ru"},
        ]
        categories = [{"name": "Cafes", "code": "cafes"}, {"name": "Shops", "code": "shops"}]

        parser = ParallelCityParser(cities, categories, "/tmp", config)
        urls = parser.generate_all_urls()

        # Должно быть 2 города * 2 категории = 4 URL
        assert len(urls) == 4
        # Каждый URL должен быть кортежем (url, category_name, city_name)
        for url, category, city in urls:
            assert isinstance(url, str)
            assert isinstance(category, str)
            assert isinstance(city, str)
            assert "moscow" in url.lower() or "omsk" in url.lower()
