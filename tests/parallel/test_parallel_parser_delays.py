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
        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

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
        with patch("parser_2gis.parallel.strategies.time.sleep"):
            with patch("parser_2gis.parallel.strategies.random.uniform") as mock_uniform:
                # Устанавливаем возвращаемое значение для random.uniform
                mock_uniform.return_value = 0.15

                # Мокаем остальные части метода, которые могут вызвать ошибки
                with patch.object(mock_parallel_parser, "_browser_launch_semaphore") as mock_sem:
                    mock_sem.acquire.return_value = None
                    mock_sem._value = 1

                    with patch("parser_2gis.writer.factory.get_writer"):
                        with patch("parser_2gis.parser.factory.get_parser"):
                            # Запускаем метод, который содержит задержку
                            try:
                                mock_parallel_parser.parse_single_url(
                                    url="https://example.com",
                                    category_name="Кафе",
                                    city_name="Москва",
                                )
                            except Exception:
                                pass  # Игнорируем ошибки, нас интересуют только вызовы задержек

                # Проверяем, что random.uniform вызывался
                assert mock_uniform.call_count >= 1, (
                    "random.uniform должен быть вызван хотя бы один раз"
                )

                # Проверяем что первый вызов использует initial_delay диапазон из конфига
                first_call_args = mock_uniform.call_args_list[0][0]
                # Ожидаем (initial_delay_min, initial_delay_max) = (0.1, 0.2)
                assert first_call_args[0] == 0.1, (
                    f"initial_delay_min должен быть 0.1, получен {first_call_args[0]}"
                )
                assert first_call_args[1] == 0.2, (
                    f"initial_delay_max должен быть 0.2, получен {first_call_args[1]}"
                )

    def test_launch_delay_uses_configured_range(self, mock_parallel_parser: ParallelCityParser):
        """Тест, что задержка запуска использует настроенный диапазон.

        Проверяет:
        - random.uniform вызывается с правильными аргументами из конфига
        """
        with patch("parser_2gis.parallel.strategies.time.sleep"):
            with patch("parser_2gis.parallel.strategies.random.uniform") as mock_uniform:
                # Устанавливаем возвращаемое значение для random.uniform
                mock_uniform.return_value = 0.07

                # Мокаем остальные части метода
                with patch.object(mock_parallel_parser, "_browser_launch_semaphore") as mock_sem:
                    mock_sem.acquire.return_value = None
                    mock_sem._value = 1

                    with patch("parser_2gis.writer.factory.get_writer"):
                        with patch("parser_2gis.parser.factory.get_parser"):
                            try:
                                mock_parallel_parser.parse_single_url(
                                    url="https://example.com",
                                    category_name="Кафе",
                                    city_name="Москва",
                                )
                            except Exception:
                                pass

                # Проверяем вызовы random.uniform - должно быть хотя бы 2 вызова
                # (initial_delay и launch_delay)
                assert mock_uniform.call_count >= 2, (
                    f"random.uniform должен быть вызван хотя бы 2 раза, вызван {mock_uniform.call_count} раз"
                )

                # Второй вызов должен быть для launch_delay
                second_call_args = mock_uniform.call_args_list[1][0]
                # Ожидаем (launch_delay_min, launch_delay_max) = (0.05, 0.1)
                assert second_call_args[0] == 0.05, (
                    f"launch_delay_min должен быть 0.05, получен {second_call_args[0]}"
                )
                assert second_call_args[1] == 0.1, (
                    f"launch_delay_max должен быть 0.1, получен {second_call_args[1]}"
                )
