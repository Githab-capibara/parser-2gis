"""
Тесты для семафора в parallel/parallel_parser.py.

Проверяет:
- Семафор создаётся с размером max_workers + 2
- Валидация max_workers работает корректно
- Семафор ограничивает количество одновременных запусков
"""

from threading import BoundedSemaphore
from unittest.mock import patch

import pytest

from parser_2gis.config import Configuration
from parser_2gis.parallel.options import ParallelOptions
from parser_2gis.parallel.parallel_parser import ParallelCityParser


class TestBrowserLaunchSemaphore:
    """Тесты семафора запуска браузеров."""

    def _create_config(self) -> Configuration:
        """Вспомогательная функция для создания конфигурации."""
        parallel_options = ParallelOptions()
        config = Configuration(parallel=parallel_options)
        return config

    def test_semaphore_size_equals_max_workers_plus_two(self) -> None:
        """Тест 1: Семафор имеет размер max_workers + 2."""
        max_workers = 4
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        expected_size = max_workers + 2
        actual_value = parser._browser_launch_semaphore._value
        assert actual_value == expected_size, (
            f"Семафор должен иметь размер {expected_size}, но имеет {actual_value}"
        )

    def test_semaphore_size_with_max_workers_1(self) -> None:
        """Тест 2: Семафор с max_workers=1 имеет размер 3."""
        max_workers = 1
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        assert parser._browser_launch_semaphore._value == 3

    def test_semaphore_size_with_max_workers_10(self) -> None:
        """Тест 3: Семафор с max_workers=10 имеет размер 12."""
        max_workers = 10
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        assert parser._browser_launch_semaphore._value == 12

    def test_semaphore_is_bounded_semaphore(self) -> None:
        """Тест 4: Семафор является BoundedSemaphore."""
        max_workers = 5
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        assert isinstance(parser._browser_launch_semaphore, BoundedSemaphore)

    def test_semaphore_releases_correctly(self) -> None:
        """Тест 5: Семафор корректно освобождается."""
        max_workers = 2
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        semaphore = parser._browser_launch_semaphore
        initial_value = semaphore._value

        # Acquire и release
        semaphore.acquire()
        assert semaphore._value == initial_value - 1

        semaphore.release()
        assert semaphore._value == initial_value

    def test_max_workers_below_min_raises_error(self) -> None:
        """Тест 6: max_workers ниже минимума вызывает ошибку."""
        from parser_2gis.constants import MIN_WORKERS

        config = self._create_config()
        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with pytest.raises(ValueError):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=MIN_WORKERS - 1,
            )

    def test_semaphore_passed_to_parse_strategy(self) -> None:
        """Тест 7: Семафор передаётся в ParseStrategy."""
        max_workers = 3
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        # ParseStrategy должен получить тот же семафор
        assert parser._parse_strategy._browser_semaphore is parser._browser_launch_semaphore

    def test_semaphore_concurrent_acquires(self) -> None:
        """Тест 8: Семафор ограничивает конкурентные захваты."""
        max_workers = 2
        config = self._create_config()

        cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Кафе"}]

        with patch("parser_2gis.parallel.strategies.time.sleep"):
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="/tmp/test_output",
                config=config,
                max_workers=max_workers,
            )

        semaphore = parser._browser_launch_semaphore
        expected_max = max_workers + 2  # 4

        # Захватываем все слоты
        for _ in range(expected_max):
            semaphore.acquire()

        # Значение должно быть 0
        assert semaphore._value == 0

        # Освобождаем
        for _ in range(expected_max):
            semaphore.release()

        assert semaphore._value == expected_max
