"""
Тесты для опций задержек в parallel/parallel_parser.py.

Проверяет:
- Корректное использование настроек задержек из ParallelOptions
"""

from unittest.mock import patch

import pytest

from parser_2gis.config import Configuration
from parser_2gis.parallel.options import ParallelOptions
from parser_2gis.parallel.parallel_parser import ParallelCityParser


class TestParallelParserDelays:
    """Тесты задержек в ParallelCityParser."""

    @pytest.fixture
    def mock_config(self) -> Configuration:
        """Создает mock конфигурации с настройками задержек.

        Returns:
            Configuration с настроенными задержками.
        """
        parallel_options = ParallelOptions(
            initial_delay_min=0.1,
            initial_delay_max=0.2,
            launch_delay_min=0.05,
            launch_delay_max=0.1,
        )
        config = Configuration(parallel=parallel_options)
        return config

    @pytest.fixture
    def mock_parallel_parser(self, mock_config: Configuration) -> ParallelCityParser:
        """Создает ParallelCityParser для тестов.

        Args:
            mock_config: Mock конфигурации.

        Returns:
            ParallelCityParser экземпляр.
        """
        cities = [{"code": "msk", "domain": "moscow.2gis.ru"}]
        categories = [{"name": "Кафе", "query": "cafe"}]

        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test_output",
            config=mock_config,
            max_workers=1,
        )
        return parser

    def test_initial_delay_uses_configured_range(self, mock_parallel_parser: ParallelCityParser):
        """Тест, что начальная задержка использует настроенный диапазон.

        Проверяет:
        - random.uniform вызывается с правильными аргументами из конфига
        """
        with patch("parser_2gis.parallel.parallel_parser.time.sleep"):
            with patch("parser_2gis.parallel.parallel_parser.random.uniform") as mock_uniform:
                # Устанавливаем возвращаемое значение для random.uniform
                mock_uniform.return_value = 0.15

                # Мокаем остальные части метода, которые могут вызвать ошибки
                with patch.object(mock_parallel_parser, "_browser_launch_semaphore") as mock_sem:
                    mock_sem.acquire.return_value = None
                    mock_sem._value = 1

                    with patch("parser_2gis.parallel.parallel_parser.get_writer"):
                        with patch("parser_2gis.parallel.parallel_parser.get_parser"):
                            # Запускаем метод, который содержит задержку
                            try:
                                mock_parallel_parser.parse_single_url(
                                    url="https://example.com",
                                    category_name="Кафе",
                                    city_name="Москва",
                                )
                            except Exception:
                                pass  # Игнорируем ошибки, нас интересуют только вызовы задержек

                # Проверяем, что random.uniform вызван с правильными аргументами
                # Первый вызов должен быть для initial_delay
                assert mock_uniform.call_count >= 1
                first_call_args = mock_uniform.call_args_list[0][0]
                assert first_call_args == (0.1, 0.2)  # initial_delay_min, initial_delay_max

    def test_launch_delay_uses_configured_range(self, mock_parallel_parser: ParallelCityParser):
        """Тест, что задержка запуска использует настроенный диапазон.

        Проверяет:
        - random.uniform вызывается с правильными аргументами из конфига
        """
        with patch("parser_2gis.parallel.parallel_parser.time.sleep"):
            with patch("parser_2gis.parallel.parallel_parser.random.uniform") as mock_uniform:
                # Устанавливаем возвращаемое значение для random.uniform
                mock_uniform.return_value = 0.07

                # Мокаем остальные части метода
                with patch.object(mock_parallel_parser, "_browser_launch_semaphore") as mock_sem:
                    mock_sem.acquire.return_value = None
                    mock_sem._value = 1

                    with patch("parser_2gis.parallel.parallel_parser.get_writer"):
                        with patch("parser_2gis.parallel.parallel_parser.get_parser"):
                            try:
                                mock_parallel_parser.parse_single_url(
                                    url="https://example.com",
                                    category_name="Кафе",
                                    city_name="Москва",
                                )
                            except Exception:
                                pass

                # Проверяем вызовы random.uniform
                # Второй вызов должен быть для launch_delay
                assert mock_uniform.call_count >= 2
                second_call_args = mock_uniform.call_args_list[1][0]
                assert second_call_args == (0.05, 0.1)  # launch_delay_min, launch_delay_max
