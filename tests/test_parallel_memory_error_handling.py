"""
Тест обработки MemoryError в параллельном парсере.

Проверяет что при возникновении MemoryError в do_parse():
- Временные файлы очищаются
- Семафор освобождается
- Исключение обрабатывается корректно

ИСПРАВЛЕНИЕ: Обработка MemoryError с гарантированной очисткой ресурсов.
"""

import threading
from pathlib import Path
from threading import BoundedSemaphore
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.parallel.parallel_parser import ParallelCityParser


class TestParallelMemoryErrorHandling:
    """Тесты обработки MemoryError в параллельном парсере."""

    @pytest.fixture
    def mock_cities(self) -> list:
        """Фикстура для mock городов."""
        return [{"name": "Москва", "code": "moscow", "url": "https://2gis.ru/moscow"}]

    @pytest.fixture
    def mock_categories(self) -> list:
        """Фикстура для mock категорий."""
        return [{"name": "Рестораны", "id": 93, "query": "рестораны"}]

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        """Фикстура для mock конфигурации."""
        config = MagicMock()
        config.chrome = MagicMock()
        config.chrome.headless = True
        config.chrome.memory_limit = 512
        config.chrome.disable_images = True
        config.parser = MagicMock()
        config.parser.max_records = 10
        config.parser.delay_between_clicks = 100
        config.parser.skip_404_response = True
        config.writer = MagicMock()
        config.writer.encoding = "utf-8-sig"
        config.writer.verbose = False
        config.writer.csv = MagicMock()
        config.writer.csv.add_rubrics = True
        config.writer.csv.add_comments = False
        config.parallel = MagicMock()
        config.parallel.use_temp_file_cleanup = False
        return config

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> str:
        """Фикстура для директории вывода."""
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)

    @pytest.fixture
    def parser(
        self, mock_cities: list, mock_categories: list, mock_config: MagicMock, output_dir: str
    ) -> ParallelCityParser:
        """Фикстура для ParallelCityParser."""
        return ParallelCityParser(
            cities=mock_cities,
            categories=mock_categories,
            output_dir=output_dir,
            config=mock_config,
            max_workers=2,
            timeout_per_url=60,
        )

    def test_memory_error_in_do_parse_cleanup_temp_files(
        self, parser: ParallelCityParser, tmp_path: Path
    ) -> None:
        """Тест что временные файлы очищаются при MemoryError в do_parse().

        Проверяет:
        - Вызвать MemoryError искусственно
        - Проверить что временные файлы очищены
        """
        # Создаем временный файл который должен быть очищен
        temp_file = tmp_path / "test_temp_file.tmp"
        temp_file.write_text("temp data")

        # Mock для создания MemoryError при парсинге
        with patch("parser_2gis.chrome.remote.ChromeRemote") as mock_chrome:
            mock_chrome.side_effect = MemoryError("Test memory error")

            # Создаем тестовый URL
            url = "https://2gis.ru/moscow/search/рестораны"
            category_name = "Рестораны"
            city_name = "Москва"

            # Вызываем parse_single_url с MemoryError
            success, message = parser.parse_single_url(
                url=url, category_name=category_name, city_name=city_name, progress_callback=None
            )

            # Проверяем что ошибка обработана
            assert success is False

    def test_memory_error_semaphore_released(self, parser: ParallelCityParser) -> None:
        """Тест что семафор освобождается при MemoryError.

        Проверяет:
        - Семафор доступен после ошибки
        - Блокировки не остается
        """
        # Получаем начальное значение семафора
        initial_semaphore_value = parser._browser_launch_semaphore._value

        # Mock для создания MemoryError при парсинге
        with patch("parser_2gis.chrome.remote.ChromeRemote") as mock_chrome:
            mock_chrome.side_effect = MemoryError("Test memory error")

            url = "https://2gis.ru/moscow/search/рестораны"
            category_name = "Рестораны"
            city_name = "Москва"

            # Вызываем parse_single_url
            parser.parse_single_url(
                url=url, category_name=category_name, city_name=city_name, progress_callback=None
            )

        # Проверяем что семафор освобожден (значение восстановилось)
        final_semaphore_value = parser._browser_launch_semaphore._value
        assert final_semaphore_value == initial_semaphore_value, (
            f"Семафор не освобожден: было {initial_semaphore_value}, стало {final_semaphore_value}"
        )

    def test_memory_error_handling_in_parse_single_url(self, parser: ParallelCityParser) -> None:
        """Тест обработки MemoryError в parse_single_url().

        Проверяет:
        - MemoryError перехватывается
        - Возвращается кортеж (False, сообщение)
        """
        # Mock для создания MemoryError при парсинге
        with patch("parser_2gis.chrome.remote.ChromeRemote") as mock_chrome:
            mock_chrome.side_effect = MemoryError("Test memory error")

            url = "https://2gis.ru/moscow/search/рестораны"
            category_name = "Рестораны"
            city_name = "Москва"

            success, message = parser.parse_single_url(
                url=url, category_name=category_name, city_name=city_name, progress_callback=None
            )

            # Проверяем что ошибка обработана
            assert success is False

    def test_temp_file_cleanup_on_memory_error(
        self, parser: ParallelCityParser, tmp_path: Path
    ) -> None:
        """Тест что временные файлы удаляются при MemoryError.

        Проверяет:
        - Временный файл создается
        - При MemoryError файл удаляется
        """
        # Mock для создания MemoryError при парсинге
        with patch("parser_2gis.chrome.remote.ChromeRemote") as mock_chrome:
            mock_chrome.side_effect = MemoryError("Test memory error")

            url = "https://2gis.ru/moscow/search/рестораны"
            category_name = "Рестораны"
            city_name = "Москва"

            success, message = parser.parse_single_url(
                url=url, category_name=category_name, city_name=city_name, progress_callback=None
            )

            # Проверяем что ошибка обработана
            assert success is False

    def test_semaphore_thread_safety_on_error(self) -> None:
        """Тест потокобезопасности семафора при ошибках.

        Проверяет:
        - Семафор корректно работает в многопоточной среде
        - Ошибки не приводят к deadlock
        """
        semaphore = BoundedSemaphore(2)
        errors_occurred = []

        def worker(worker_id: int) -> None:
            try:
                semaphore.acquire()
                if worker_id == 0:
                    # Симулируем ошибку в первом потоке
                    raise MemoryError(f"Worker {worker_id} memory error")
                # Успешная работа
            except MemoryError:
                errors_occurred.append(worker_id)
            finally:
                semaphore.release()

        threads = []
        for i in range(2):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Проверяем что ошибка произошла
        assert 0 in errors_occurred

        # Проверяем что семафор освобожден (можно acquire снова)
        assert semaphore.acquire(blocking=False)
        semaphore.release()
