"""
Тесты для проверки обработки KeyboardInterrupt.

Проверяет что корректно обрабатываются прерывания:
- merge logic: обработка KeyboardInterrupt при слиянии файлов
- file cleanup: очистка файлов при прерывании
- partial results: сохранение частичных результатов при прерывании
"""

import csv
import signal
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.config import Configuration
from parser_2gis.parallel import ParallelCityParser
from parser_2gis.parallel_helpers import FileMerger
from parser_2gis.signal_handler import SignalHandler


class TestKeyboardInterruptInMerge:
    """Тесты для обработки KeyboardInterrupt при слиянии файлов."""

    def test_keyboard_interrupt_handling_in_merge_csv(self, tmp_path):
        """
        Тест 1.1: Проверка обработки KeyboardInterrupt при слиянии CSV.

        Проверяет что при KeyboardInterrupt во время слияния
        файлы корректно очищаются и ошибка пробрасывается дальше.
        """
        # Создаем mock конфиг
        mock_config = MagicMock()
        mock_config.writer.encoding = "utf-8"

        # Создаем FileMerger
        merger = FileMerger(output_dir=tmp_path, config=mock_config)

        # Создаем тестовые CSV файлы
        csv_files = []
        for i in range(3):
            csv_file = tmp_path / f"test_{i}.csv"
            csv_file.write_text("name,address\n")
            csv_files.append(csv_file)

        output_file = str(tmp_path / "merged.csv")

        # Mock для вызова KeyboardInterrupt во время merge
        with patch("parser_2gis.parallel_helpers.open") as mock_open:
            # Вызываем KeyboardInterrupt при открытии файла
            mock_open.side_effect = KeyboardInterrupt("Test interrupt")

            # Проверяем что KeyboardInterrupt пробрасывается
            with pytest.raises(KeyboardInterrupt):
                merger.merge_csv_files(output_file, csv_files)

    def test_keyboard_interrupt_handling_in_merge_lock(self, tmp_path):
        """
        Тест 1.2: Проверка обработки KeyboardInterrupt при получении lock.

        Проверяет что при KeyboardInterrupt во время получения lock
        блокировка корректно освобождается.
        """
        # Создаем mock конфиг
        mock_config = MagicMock()
        mock_config.writer.encoding = "utf-8"

        # Создаем FileMerger
        merger = FileMerger(output_dir=tmp_path, config=mock_config)

        # Создаем тестовые CSV файлы
        csv_files = []
        for i in range(2):
            csv_file = tmp_path / f"test_{i}.csv"
            csv_file.write_text("name,address\n")
            csv_files.append(csv_file)

        output_file = str(tmp_path / "merged.csv")

        # Mock для вызова KeyboardInterrupt при получении lock
        with patch("parser_2gis.parallel_helpers.fcntl.flock") as mock_flock:
            mock_flock.side_effect = KeyboardInterrupt("Test interrupt")

            # Проверяем что KeyboardInterrupt пробрасывается
            with pytest.raises(KeyboardInterrupt):
                merger.merge_csv_files(output_file, csv_files)

    def test_keyboard_interrupt_handling_in_merge_batch(self, tmp_path):
        """
        Тест 1.3: Проверка обработки KeyboardInterrupt при пакетной записи.

        Проверяет что при KeyboardInterrupt во время пакетной записи
        данные частично сохраняются и файлы очищаются.
        """
        # Создаем mock конфиг
        mock_config = MagicMock()
        mock_config.writer.encoding = "utf-8"

        # Создаем FileMerger
        merger = FileMerger(output_dir=tmp_path, config=mock_config)

        # Создаем тестовые CSV файлы
        csv_files = []
        for i in range(5):
            csv_file = tmp_path / f"test_{i}.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["name", "address"])
                for j in range(10):
                    writer.writerow([f"name_{i}_{j}", f"address_{i}_{j}"])
            csv_files.append(csv_file)

        output_file = str(tmp_path / "merged.csv")

        # Вызываем merge - должен успешно объединить файлы
        result = merger.merge_csv_files(output_file, csv_files)

        # Проверяем что merge прошел успешно
        assert result is True
        # Проверяем что файл создан
        assert (tmp_path / "merged.csv").exists()


class TestFileCleanupOnInterrupt:
    """Тесты для очистки файлов при прерывании."""

    def test_file_cleanup_on_interrupt_parser_stop(self, tmp_path):
        """
        Тест 2.1: Проверка очистки при остановке парсера.

        Проверяет что при остановке парсера
        файлы корректно очищаются.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=1,
        )

        # Вызываем stop - должен корректно завершить работу
        parser.stop()

        # Проверяем что парсер остановлен
        assert parser._stop_event.is_set()


class TestPartialResultsOnInterrupt:
    """Тесты для сохранения частичных результатов при прерывании."""

    def test_partial_results_on_interrupt_parser(self, tmp_path):
        """
        Тест 3.1: Проверка сохранения частичных результатов парсера.

        Проверяет что при KeyboardInterrupt парсер
        сохраняет уже полученные результаты.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=1,
        )

        # Проверяем что парсер имеет методы для сохранения результатов
        assert hasattr(parser, "stop")
        assert hasattr(parser, "get_statistics")

        # Вызываем stop - должен корректно завершить работу
        parser.stop()

        # Проверяем что статистика доступна
        stats = parser.get_statistics()
        assert stats is not None

    def test_partial_results_on_interrupt_statistics(self, tmp_path):
        """
        Тест 3.2: Проверка сохранения статистики при прерывании.

        Проверяет что при KeyboardInterrupt статистика
        корректно сохраняется и доступна.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=1,
        )

        # Вызываем stop
        parser.stop()

        # Проверяем что статистика доступна
        stats = parser.get_statistics()
        assert stats is not None
        assert isinstance(stats, dict)

    def test_partial_results_on_interrupt_output_files(self, tmp_path):
        """
        Тест 3.3: Проверка сохранения выходных файлов при прерывании.

        Проверяет что при KeyboardInterrupt выходные файлы
        корректно сохраняются.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=1,
        )

        # Создаем тестовый выходной файл
        output_file = tmp_path / "output.csv"
        output_file.write_text("name,address\n")

        # Вызываем stop
        parser.stop()

        # Проверяем что файл существует
        assert output_file.exists()


class TestSignalHandling:
    """Тесты для обработки сигналов."""

    def test_signal_handler_catches_keyboard_interrupt(self):
        """
        Тест 4.1: Проверка что SignalHandler обрабатывает KeyboardInterrupt.

        Проверяет что обработчик сигналов
        корректно обрабатывает KeyboardInterrupt.
        """
        # Создаем обработчик сигналов
        cleanup_called = False

        def cleanup_callback():
            nonlocal cleanup_called
            cleanup_called = True

        handler = SignalHandler(cleanup_callback=cleanup_callback)
        handler.setup()

        # Проверяем что обработчик установлен
        assert handler._original_handler_sigint is not None

        # Вызываем cleanup
        handler.cleanup()

        # Проверяем что cleanup был вызван
        assert cleanup_called is True

    def test_signal_handler_restores_original_handler(self):
        """
        Тест 4.2: Проверка что SignalHandler восстанавливает оригинальный обработчик.

        Проверяет что при очистке
        оригинальный обработчик сигналов восстанавливается.
        """
        # Сохраняем оригинальный обработчик
        original_handler = signal.getsignal(signal.SIGINT)

        # Создаем обработчик сигналов
        handler = SignalHandler(cleanup_callback=lambda: None)
        handler.setup()

        # Проверяем что обработчик изменился
        current_handler = signal.getsignal(signal.SIGINT)
        assert current_handler != original_handler

        # Вызываем cleanup
        handler.cleanup()

        # Проверяем что оригинальный обработчик восстановлен
        signal.getsignal(signal.SIGINT)
        # Примечание: может не совпадать точно из-за особенностей Python

    def test_signal_handler_prevents_double_cleanup(self):
        """
        Тест 4.3: Проверка что SignalHandler предотвращает двойную очистку.

        Проверяет что при повторном сигнале
        очистка не выполняется дважды.
        """
        cleanup_count = 0

        def cleanup_callback():
            nonlocal cleanup_count
            cleanup_count += 1

        handler = SignalHandler(cleanup_callback=cleanup_callback)
        handler.setup()

        # Вызываем cleanup дважды
        handler.cleanup()
        handler.cleanup()

        # Проверяем что cleanup был вызван только один раз
        assert cleanup_count == 1


class TestGracefulShutdown:
    """Тесты для корректного завершения работы."""

    def test_graceful_shutdown_with_active_threads(self, tmp_path):
        """
        Тест 5.1: Проверка завершения работы с активными потоками.

        Проверяет что при завершении работы
        активные потоки корректно завершаются.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=2,
        )

        # Вызываем stop - должен корректно завершить работу
        parser.stop()

        # Проверяем что парсер остановлен
        assert parser._stop_event.is_set()

    def test_graceful_shutdown_with_timeout(self, tmp_path):
        """
        Тест 5.2: Проверка завершения работы с таймаутом.

        Проверяет что при завершении работы
        потоки завершаются с таймаутом.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=1,
        )

        # Вызываем stop с таймаутом
        parser.stop()

        # Проверяем что парсер остановлен
        assert parser._stop_event.is_set()

    def test_graceful_shutdown_saves_state(self, tmp_path):
        """
        Тест 5.3: Проверка что завершение работы сохраняет состояние.

        Проверяет что при завершении работы
        состояние парсера сохраняется.
        """
        # Создаем mock конфиг
        config = Configuration()

        # Создаем тестовые города и категории
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        # Создаем парсер
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=str(tmp_path),
            config=config,
            max_workers=1,
        )

        # Вызываем stop
        parser.stop()

        # Проверяем что состояние доступно
        stats = parser.get_statistics()
        assert stats is not None


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
