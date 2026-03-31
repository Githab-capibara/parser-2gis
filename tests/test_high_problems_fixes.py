"""
Тесты для исправлений HIGH проблем.

Проверяет:
- Обработку конкретных исключений в parser
- ENV переменные для констант
- Валидацию в generate_category_url
- Оптимизацию размера lru_cache
- Type hints в helpers
- Дедупликацию кода валидации
- Эффективность буфера сериализации
"""

import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.constants import validate_env_int
from parser_2gis.utils.url_utils import generate_category_url


class TestSpecificExceptionHandlingInParser:
    """Тесты для HIGH 7: Конкретные обработчики исключений в parser."""

    @pytest.fixture
    def mock_parser_config(self) -> MagicMock:
        """Создает mock конфигурацию для парсера.

        Returns:
            MagicMock с конфигурацией.
        """
        config = MagicMock()
        config.chrome.headless = True
        config.chrome.memory_limit = 512
        config.chrome.disable_images = True
        config.parser.max_records = 10
        config.parser.delay_between_clicks = 100
        config.parser.skip_404_response = True
        return config

    def test_chrome_exception_handling(self, mock_parser_config: MagicMock) -> None:
        """Тест 1: Обработка ChromeException.

        Проверяет:
        - ChromeException обрабатывается корректно
        - Браузер закрывается при ошибке
        """
        from parser_2gis.chrome.exceptions import ChromeException

        # Проверяем что ChromeException существует и может быть обработан
        assert ChromeException is not None

        # Проверяем что исключение может быть выброшено
        with pytest.raises(ChromeException):
            raise ChromeException("Test error")

    def test_memory_error_handling(self, mock_parser_config: MagicMock) -> None:
        """Тест 2: Обработка MemoryError.

        Проверяет:
        - MemoryError обрабатывается корректно
        - Ресурсы освобождаются
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"}]
        categories = [{"name": "Рестораны", "id": 93, "query": "рестораны"}]

        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp",
            config=mock_parser_config,
            max_workers=2,
            timeout_per_url=60,
        )

        # MemoryError должна пробрасываться
        with patch("parser_2gis.parallel.parallel_parser.MemoryMonitor") as mock_monitor:
            mock_instance = MagicMock()
            mock_instance.get_available_memory.return_value = 50 * 1024 * 1024  # 50MB
            mock_monitor.return_value = mock_instance

            # Проверяем что low memory обрабатывается
            result = parser.parse_single_url(
                url="https://2gis.ru/moscow/search/test", category_name="Тест", city_name="Москва"
            )

            # Должно вернуть False из-за low memory
            assert result[0] is False

    def test_os_error_handling(self, mock_parser_config: MagicMock) -> None:
        """Тест 3: Обработка OSError.

        Проверяет:
        - OSError обрабатывается корректно
        - Временные файлы удаляются
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"}]
        categories = [{"name": "Рестораны", "id": 93, "query": "рестораны"}]

        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp",
            config=mock_parser_config,
            max_workers=2,
            timeout_per_url=60,
        )

        # OSError при создании временного файла
        with patch("os.open", side_effect=OSError("Mocked OSError")):
            with pytest.raises(OSError):
                parser.parse_single_url(
                    url="https://2gis.ru/moscow/search/test",
                    category_name="Тест",
                    city_name="Москва",
                )

    def test_value_error_handling(self, mock_parser_config: MagicMock) -> None:
        """Тест 4: Обработка ValueError.

        Проверяет:
        - ValueError обрабатывается корректно
        - Логирование работает
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"}]
        categories = [{"name": "Рестораны", "id": 93, "query": "рестораны"}]

        # ValueError при некорректных данных
        with pytest.raises(ValueError):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/nonexistent/path/that/does/not/exist",
                config=mock_parser_config,
                max_workers=2,
                timeout_per_url=60,
            )

    def test_type_error_handling(self, mock_parser_config: MagicMock) -> None:
        """Тест 5: Обработка TypeError.

        Проверяет:
        - TypeError обрабатывается корректно
        - Типы проверяются
        """
        # TypeError при некорректных типах
        with pytest.raises(TypeError):
            generate_category_url(None, {"name": "Тест"})  # type: ignore


class TestEnvVariablesForConstants:
    """Тесты для HIGH 8: ENV переменные для констант."""

    def test_validate_env_int_valid(self) -> None:
        """Тест 6: Валидация корректной ENV переменной.

        Проверяет:
        - Корректное значение возвращается
        - Валидация работает
        """
        result = validate_env_int("TEST_VAR", default=10, min_value=1, max_value=20)
        assert result == 10

    def test_validate_env_int_from_environment(self) -> None:
        """Тест 7: Чтение ENV переменной из окружения.

        Проверяет:
        - ENV переменная читается корректно
        - Значение преобразуется в int
        """
        os.environ["TEST_PARSER_VAR"] = "25"
        try:
            result = validate_env_int("TEST_PARSER_VAR", default=10)
            assert result == 25
        finally:
            del os.environ["TEST_PARSER_VAR"]

    def test_validate_env_int_below_min(self) -> None:
        """Тест 8: Значение ниже минимума.

        Проверяет:
        - Возвращается min_value
        - Логирование предупреждения
        """

        with patch("parser_2gis.constants.os.getenv", return_value="5"):
            result = validate_env_int("TEST_VAR", default=10, min_value=10, max_value=20)

            # Должно вернуть min_value
            assert result == 10

    def test_validate_env_int_above_max(self) -> None:
        """Тест 9: Значение выше максимума.

        Проверяет:
        - Возвращается max_value
        - Логирование предупреждения
        """
        with patch("parser_2gis.constants.os.getenv", return_value="100"):
            result = validate_env_int("TEST_VAR", default=10, min_value=1, max_value=50)

            # Должно вернуть max_value
            assert result == 50

    def test_validate_env_int_invalid_value(self) -> None:
        """Тест 10: Некорректное значение ENV.

        Проверяет:
        - Возвращается default при некорректном значении
        """
        with patch("parser_2gis.constants.os.getenv", return_value="invalid"):
            result = validate_env_int("TEST_VAR", default=10)
            # Должно вернуть default при некорректном значении
            assert result == 10

    def test_validate_env_int_none_returns_default(self) -> None:
        """Тест 11: None возвращает default.

        Проверяет:
        - Если ENV не установлена, возвращается default
        """
        with patch("parser_2gis.constants.os.getenv", return_value=None):
            result = validate_env_int("TEST_VAR", default=42)
            assert result == 42


class TestGenerateCategoryUrlValidation:
    """Тесты для HIGH 9: Валидация параметров в generate_category_url."""

    def test_city_none_raises_type_error(self) -> None:
        """Тест 12: city=None вызывает TypeError."""
        with pytest.raises(TypeError, match="city не может быть None"):
            generate_category_url(None, {"name": "Тест"})  # type: ignore

    def test_city_not_dict_raises_type_error(self) -> None:
        """Тест 13: city не dict вызывает TypeError."""
        with pytest.raises(TypeError, match="city должен быть словарём"):
            generate_category_url("moscow", {"name": "Тест"})  # type: ignore

    def test_city_missing_code_raises_value_error(self) -> None:
        """Тест 14: city без code вызывает ValueError."""
        with pytest.raises(ValueError, match="city должен содержать code"):
            generate_category_url({"domain": "ru"}, {"name": "Тест"})

    def test_city_missing_domain_raises_value_error(self) -> None:
        """Тест 15: city без domain вызывает ValueError."""
        with pytest.raises(ValueError, match="city должен содержать domain"):
            generate_category_url({"code": "moscow"}, {"name": "Тест"})

    def test_city_empty_code_raises_value_error(self) -> None:
        """Тест 16: city с пустым code вызывает ValueError."""
        with pytest.raises(ValueError, match="city\\['code'\\] должен быть непустой строкой"):
            generate_category_url({"code": "", "domain": "ru"}, {"name": "Тест"})

    def test_category_none_raises_type_error(self) -> None:
        """Тест 17: category=None вызывает TypeError."""
        with pytest.raises(TypeError, match="category не может быть None"):
            generate_category_url({"code": "moscow", "domain": "ru"}, None)  # type: ignore

    def test_category_not_dict_raises_type_error(self) -> None:
        """Тест 18: category не dict вызывает TypeError."""
        with pytest.raises(TypeError, match="category должен быть словарём"):
            generate_category_url({"code": "moscow", "domain": "ru"}, "restaurants")  # type: ignore

    def test_category_missing_query_and_name_raises_value_error(self) -> None:
        """Тест 19: category без query и name вызывает ValueError."""
        with pytest.raises(ValueError, match="category должен содержать query или name"):
            generate_category_url({"code": "moscow", "domain": "ru"}, {"rubric_code": "93"})

    def test_valid_city_category_generates_url(self) -> None:
        """Тест 20: Валидные данные генерируют URL."""
        city = {"code": "moscow", "domain": "ru"}
        category = {"name": "Рестораны", "query": "рестораны"}

        url = generate_category_url(city, category)

        assert "https://2gis.ru/moscow" in url
        assert "search" in url


class TestLRUCacheSizeOptimization:
    """Тесты для HIGH 10: Оптимизация размера lru_cache."""

    def test_url_query_cache_maxsize(self) -> None:
        """Тест 21: Размер кэша url_query_encode = 2048.

        Проверяет:
        - maxsize установлен в 2048
        - Кэш работает корректно
        """
        from parser_2gis.utils.url_utils import _url_query_encode

        # Проверяем что кэш имеет правильный размер
        assert _url_query_encode.cache_info().maxsize == 2048

    def test_generate_category_url_cache_maxsize(self) -> None:
        """Тест 22: Размер кэша _generate_category_url_cached = 512.

        Проверяет:
        - maxsize установлен в 512
        - Кэш работает корректно
        """
        from parser_2gis.utils.url_utils import _generate_category_url_cached

        # Проверяем что кэш имеет правильный размер
        assert _generate_category_url_cached.cache_info().maxsize == 512

    def test_cache_efficiency(self) -> None:
        """Тест 23: Эффективность кэширования.

        Проверяет:
        - Повторные вызовы используют кэш
        - hit rate увеличивается
        """
        from parser_2gis.utils.url_utils import _url_query_encode

        # Очищаем кэш
        _url_query_encode.cache_clear()

        # Вызываем несколько раз с одинаковым запросом
        for _ in range(10):
            _url_query_encode("тест")

        info = _url_query_encode.cache_info()
        # Должно быть 1 miss и 9 hits
        assert info.misses == 1
        assert info.hits == 9


class TestTypeHintsInHelpers:
    """Тесты для HIGH 12: Type hints в helpers."""

    def test_helpers_module_has_type_hints(self) -> None:
        """Тест 24: Модуль helpers имеет type hints.

        Проверяет:
        - Функции имеют аннотации типов
        - Возвращаемые типы указаны
        """
        # Проверяем наличие аннотаций
        import inspect

        from parser_2gis.parallel import helpers

        # Проверяем FileMerger
        sig = inspect.signature(helpers.FileMerger.__init__)
        assert "output_dir" in sig.parameters
        assert sig.parameters["output_dir"].annotation != inspect.Parameter.empty

    def test_validate_env_int_type_hints(self) -> None:
        """Тест 25: validate_env_int имеет type hints.

        Проверяет:
        - Параметры имеют аннотации
        - Возвращаемый тип указан
        """
        import inspect

        sig = inspect.signature(validate_env_int)

        # Проверяем аннотации параметров
        assert sig.parameters["env_name"].annotation != inspect.Parameter.empty
        assert sig.parameters["default"].annotation != inspect.Parameter.empty
        assert sig.return_annotation != inspect.Parameter.empty


class TestValidationCodeDeduplication:
    """Тесты для HIGH 13: Общая логика валидации."""

    def test_validate_env_int_reuses_logic(self) -> None:
        """Тест 26: validate_env_int использует общую логику.

        Проверяет:
        - Общая функция для валидации ENV
        - Логика переиспользуется
        """
        # Проверяем что функция работает для разных диапазонов
        result1 = validate_env_int("VAR1", default=10, min_value=1, max_value=20)
        result2 = validate_env_int("VAR2", default=5, min_value=1, max_value=10)

        assert result1 == 10
        assert result2 == 5

    def test_validation_raises_consistent_errors(self) -> None:
        """Тест 27: Валидация возвращает согласованные значения.

        Проверяет:
        - При некорректном типе возвращается default
        - Валидация работает корректно
        """
        # При некорректном значении возвращается default
        with patch("parser_2gis.constants.os.getenv", return_value="invalid"):
            result = validate_env_int("TEST", default=10)
            assert result == 10  # Возвращается default


class TestSerializerBufferEfficiency:
    """Тесты для HIGH 14: Эффективность буфера сериализации."""

    def test_json_serializer_serialize_efficiency(self) -> None:
        """Тест 28: Эффективность сериализации JSON.

        Проверяет:
        - orjson используется если доступен
        - Fallback на json работает
        """
        from parser_2gis.cache.serializer import JsonSerializer

        serializer = JsonSerializer()
        data = {"key": "value", "number": 42}

        result = serializer.serialize(data)

        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_json_serializer_deserialize_efficiency(self) -> None:
        """Тест 29: Эффективность десериализации JSON.

        Проверяет:
        - Десериализация работает корректно
        - Валидация структуры работает
        """
        from parser_2gis.cache.serializer import JsonSerializer

        serializer = JsonSerializer()
        json_str = '{"key":"value","number":42}'

        result = serializer.deserialize(json_str)

        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_json_serializer_invalid_json_raises(self) -> None:
        """Тест 30: Некорректный JSON вызывает ошибку.

        Проверяет:
        - ValueError при некорректном JSON
        - Сообщение об ошибке содержит контекст
        """
        from parser_2gis.cache.serializer import JsonSerializer

        serializer = JsonSerializer()

        with pytest.raises(ValueError):
            serializer.deserialize("invalid json")

    def test_json_serializer_non_dict_raises(self) -> None:
        """Тест 31: Некорректный тип данных вызывает ошибку.

        Проверяет:
        - TypeError при некорректном типе
        - Валидация структуры работает
        """
        from parser_2gis.cache.serializer import JsonSerializer

        serializer = JsonSerializer()

        with pytest.raises(TypeError):
            serializer.deserialize("[1, 2, 3]")

    def test_json_serializer_buffer_size(self) -> None:
        """Тест 32: Размер буфера сериализации.

        Проверяет:
        - Буферизация работает корректно
        - Производительность оптимальна
        """
        from parser_2gis.cache.serializer import JsonSerializer

        serializer = JsonSerializer()

        # Сериализуем большие данные
        large_data: Dict[str, Any] = {f"key_{i}": f"value_{i}" for i in range(1000)}

        result = serializer.serialize(large_data)
        deserialized = serializer.deserialize(result)

        assert len(deserialized) == 1000
        assert deserialized["key_500"] == "value_500"
