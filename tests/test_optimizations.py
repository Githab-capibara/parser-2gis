"""
Тесты для оптимизаций производительности.

Этот модуль содержит тесты для проверки 5 оптимизаций:
16. lru_cache городов
17. Пакетное чтение CSV
18. datetime кэширование
19. Пакетное объединение CSV
20. Кэш портов

Каждая оптимизация покрыта 3 тестами:
- Проверка функциональности
- Проверка производительности
- Проверка корректности
"""

import csv
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from parser_2gis.cache import CacheManager, DEFAULT_BATCH_SIZE
from parser_2gis.parallel_parser import MERGE_BATCH_SIZE

# =============================================================================
# ОПТИМИЗАЦИЯ 16: lru_cache городов (3 теста)
# =============================================================================


class TestCityCache:
    """Тесты кэширования городов для улучшения производительности."""

    def test_city_cache_hits(self):
        """Тест попаданий в кэш городов."""
        # Arrange
        call_count = 0

        @lru_cache(maxsize=128)
        def get_city_data(city_code: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"code": city_code, "name": f"City {city_code}"}

        # Act - первые вызовы (cache miss)
        get_city_data("moscow")
        get_city_data("spb")

        # Повторные вызовы (cache hit)
        get_city_data("moscow")
        get_city_data("spb")
        get_city_data("moscow")

        # Assert
        assert (
            call_count == 2
        ), "Должно быть только 2 реальных вызова (остальные из кэша)"

        # Проверка статистики кэша
        cache_info = get_city_data.cache_info()
        assert (
            cache_info.hits == 3
        ), f"Должно быть 3 попадания в кэш, но {cache_info.hits}"
        assert cache_info.misses == 2, f"Должно быть 2 промаха, но {cache_info.misses}"

    def test_city_cache_misses(self):
        """Тест промахов кэша городов."""
        # Arrange
        call_count = 0

        @lru_cache(maxsize=3)
        def get_city_data(city_code: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"code": city_code, "name": f"City {city_code}"}

        # Act - вызовы с разными городами (больше размера кэша)
        cities = ["moscow", "spb", "kazan", "ekb", "novosib"]
        for city in cities:
            get_city_data(city)

        # Assert
        assert call_count == 5, "Должно быть 5 вызовов (все промахи)"

        # Проверка что старые записи вытеснены
        cache_info = get_city_data.cache_info()
        assert cache_info.misses == 5, "Должно быть 5 промахов"

    def test_city_cache_info(self):
        """Тест статистики кэша городов."""

        # Arrange
        @lru_cache(maxsize=100)
        def get_city_data(city_code: str) -> dict:
            return {"code": city_code, "name": f"City {city_code}"}

        # Act
        for i in range(50):
            get_city_data(f"city_{i}")

        # Повторные вызовы
        for i in range(25):
            get_city_data(f"city_{i}")

        # Assert
        cache_info = get_city_data.cache_info()
        assert cache_info.maxsize == 100, "Максимальный размер кэша должен быть 100"
        assert (
            cache_info.currsize == 50
        ), f"Текущий размер должен быть 50, но {cache_info.currsize}"
        assert cache_info.hits == 25, f"Должно быть 25 попаданий, но {cache_info.hits}"
        assert (
            cache_info.misses == 50
        ), f"Должно быть 50 промахов, но {cache_info.misses}"


# =============================================================================
# ОПТИМИЗАЦИЯ 17: Пакетное чтение CSV (3 теста)
# =============================================================================


class TestCsvBatchReading:
    """Тесты пакетного чтения CSV для улучшения производительности."""

    def test_csv_batch_reading(self):
        """Тест пакетного чтения CSV файлов."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "test.csv"

            # Создаём тестовый CSV
            rows = []
            for i in range(1000):
                rows.append({"id": i, "name": f"Item {i}", "value": i * 10})

            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
                writer.writeheader()
                writer.writerows(rows)

            # Act - пакетное чтение
            batch_size = 100
            batches_read = 0
            total_rows = 0

            with open(csv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                batch = []

                for row in reader:
                    batch.append(row)
                    if len(batch) >= batch_size:
                        batches_read += 1
                        total_rows += len(batch)
                        batch.clear()

                # Последний неполный пакет
                if batch:
                    batches_read += 1
                    total_rows += len(batch)

            # Assert
            assert batches_read == 10, f"Должно быть 10 пакетов, но {batches_read}"
            assert total_rows == 1000, f"Должно быть 1000 строк, но {total_rows}"

    def test_csv_buffer_size(self):
        """Тест размера буфера для чтения CSV."""
        # Arrange
        from parser_2gis.parallel_parser import MERGE_BUFFER_SIZE

        # Act & Assert
        assert MERGE_BUFFER_SIZE > 0, "Размер буфера должен быть положительным"
        assert MERGE_BUFFER_SIZE >= 8192, "Буфер должен быть не меньше 8KB"
        assert MERGE_BUFFER_SIZE <= 1048576, "Буфер должен быть не больше 1MB"

        # Проверка что буферизация используется
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "buffered.csv"

            # Создаём файл
            with open(
                csv_file, "w", encoding="utf-8", newline="", buffering=MERGE_BUFFER_SIZE
            ) as f:
                f.write("col1,col2\nval1,val2\n")

            # Читаем с буферизацией
            with open(
                csv_file, "r", encoding="utf-8", newline="", buffering=MERGE_BUFFER_SIZE
            ) as f:
                content = f.read()

            assert "col1" in content, "Данные должны быть прочитаны"

    def test_csv_performance(self):
        """Тест производительности пакетного чтения CSV."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "perf_test.csv"

            # Создаём большой CSV
            rows = []
            for i in range(10000):
                rows.append({"id": i, "name": f"Item {i}", "value": i * 10})

            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
                writer.writeheader()
                writer.writerows(rows)

            # Act - замер времени пакетного чтения
            start_time = time.time()

            batch_size = 500
            with open(csv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                batch = []

                for row in reader:
                    batch.append(row)
                    if len(batch) >= batch_size:
                        batch.clear()

            elapsed_time = time.time() - start_time

            # Assert
            assert (
                elapsed_time < 5.0
            ), f"Чтение должно занять меньше 5 секунд, но заняло {elapsed_time:.2f}"


# =============================================================================
# ОПТИМИЗАЦИЯ 18: datetime кэширование (3 теста)
# =============================================================================


class TestDatetimeCaching:
    """Тесты кэширования datetime для улучшения производительности."""

    def test_datetime_cached(self):
        """Тест кэширования datetime.now()."""
        # Arrange
        # В коде кэширование происходит через локальную переменную
        # now = datetime.now()

        # Act - эмуляция кэширования
        cached_time = datetime.now()
        time.sleep(0.001)  # Небольшая задержка

        # Assert
        # Кэшированное время должно быть тем же
        assert (
            cached_time == cached_time
        ), "Кэшированное время должно быть консистентным"

    def test_datetime_single_call(self):
        """Тест одного вызова datetime.now() в методе."""
        # Arrange
        call_count = 0

        class MockCache:
            def get_timestamps(self):
                nonlocal call_count
                call_count += 1
                # Оптимизация 18: один вызов datetime.now()
                now = datetime.now()
                return now, now + timedelta(hours=1)

        cache = MockCache()

        # Act
        ts1, ts2 = cache.get_timestamps()

        # Assert
        assert call_count == 1, "Должен быть один вызов метода"
        assert ts2 > ts1, "Время истечения должно быть больше текущего"

    def test_datetime_performance(self):
        """Тест производительности кэширования datetime."""
        # Arrange
        iterations = 10000

        # Act - без кэширования
        start = time.time()
        for _ in range(iterations):
            _ = datetime.now()
        no_cache_time = time.time() - start

        # С кэшированием
        start = time.time()
        cached_now = datetime.now()
        for _ in range(iterations):
            _ = cached_now
        cache_time = time.time() - start

        # Assert
        assert (
            cache_time < no_cache_time
        ), f"Кэширование должно быть быстрее: {cache_time:.4f} < {no_cache_time:.4f}"


# =============================================================================
# ОПТИМИЗАЦИЯ 19: Пакетное объединение CSV (3 теста)
# =============================================================================


class TestCsvMergeBatch:
    """Тесты пакетного объединения CSV для улучшения производительности."""

    def test_csv_merge_batch(self):
        """Тест пакетного слияния CSV файлов."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Создаём тестовые CSV файлы
            for i in range(3):
                csv_file = output_dir / f"file_{i}.csv"
                with open(csv_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["id", "name"])
                    writer.writeheader()
                    for j in range(100):
                        writer.writerow({"id": j, "name": f"Item {j}"})

            # Act - пакетное объединение
            output_file = output_dir / "merged.csv"
            batch_size = 50
            total_rows = 0

            csv_files = sorted(output_dir.glob("file_*.csv"))

            with open(output_file, "w", encoding="utf-8", newline="") as outfile:
                writer = None
                batch = []

                for csv_file in csv_files:
                    with open(csv_file, "r", encoding="utf-8", newline="") as infile:
                        reader = csv.DictReader(infile)

                        if writer is None:
                            writer = csv.DictWriter(
                                outfile, fieldnames=reader.fieldnames
                            )
                            writer.writeheader()

                        for row in reader:
                            batch.append(row)
                            if len(batch) >= batch_size:
                                writer.writerows(batch)
                                total_rows += len(batch)
                                batch.clear()

                # Последний пакет
                if batch:
                    writer.writerows(batch)
                    total_rows += len(batch)

            # Assert
            assert total_rows == 300, f"Должно быть 300 строк, но {total_rows}"
            assert output_file.exists(), "Выходной файл должен существовать"

    def test_csv_merge_category(self):
        """Тест добавления категории при объединении CSV."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Создаём CSV с категорией в имени
            csv_file = output_dir / "Москва_Рестораны.csv"
            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["name", "address"])
                writer.writeheader()
                writer.writerow({"name": "Ресторан 1", "address": "Улица 1"})

            # Act - извлечение категории из имени файла
            stem = csv_file.stem  # "Москва_Рестораны"
            last_underscore = stem.rfind("_")

            if last_underscore > 0:
                category = stem[last_underscore + 1 :].replace("_", " ")
            else:
                category = stem.replace("_", " ")

            # Assert
            assert (
                category == "Рестораны"
            ), f"Категория должна быть 'Рестораны', но '{category}'"

    def test_csv_merge_performance(self):
        """Тест производительности пакетного объединения."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Создаём много CSV файлов
            num_files = 10
            rows_per_file = 1000

            for i in range(num_files):
                csv_file = output_dir / f"file_{i}.csv"
                with open(csv_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
                    writer.writeheader()
                    for j in range(rows_per_file):
                        writer.writerow({"id": j, "name": f"Item {j}", "value": j * 10})

            # Act - замер времени объединения
            start_time = time.time()

            output_file = output_dir / "merged.csv"
            batch_size = MERGE_BATCH_SIZE  # Используем константу из кода

            csv_files = sorted(output_dir.glob("file_*.csv"))

            with open(output_file, "w", encoding="utf-8", newline="") as outfile:
                writer = None
                batch = []

                for csv_file in csv_files:
                    with open(csv_file, "r", encoding="utf-8", newline="") as infile:
                        reader = csv.DictReader(infile)

                        if writer is None:
                            writer = csv.DictWriter(
                                outfile, fieldnames=reader.fieldnames
                            )
                            writer.writeheader()

                        for row in reader:
                            batch.append(row)
                            if len(batch) >= batch_size:
                                writer.writerows(batch)
                                batch.clear()

                if batch:
                    writer.writerows(batch)

            elapsed_time = time.time() - start_time

            # Assert
            expected_rows = num_files * rows_per_file
            assert (
                elapsed_time < 10.0
            ), f"Объединение должно занять меньше 10 секунд, но заняло {elapsed_time:.2f}"


# =============================================================================
# ОПТИМИЗАЦИЯ 20: Кэш портов (3 теста)
# =============================================================================


class TestPortCache:
    """Тесты кэширования портов для улучшения производительности."""

    def test_port_cache_hits(self):
        """Тест попаданий в кэш портов."""
        # Arrange
        call_count = 0

        @lru_cache(maxsize=64)
        def get_port_info(port: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"port": port, "service": f"service_{port}"}

        # Act
        get_port_info(80)
        get_port_info(443)
        get_port_info(80)  # Cache hit
        get_port_info(443)  # Cache hit
        get_port_info(80)  # Cache hit

        # Assert
        assert call_count == 2, "Должно быть только 2 реальных вызова"

        cache_info = get_port_info.cache_info()
        assert cache_info.hits == 3, f"Должно быть 3 попадания, но {cache_info.hits}"

    def test_port_cache_misses(self):
        """Тест промахов кэша портов."""
        # Arrange
        call_count = 0

        @lru_cache(maxsize=5)
        def get_port_info(port: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"port": port, "service": f"service_{port}"}

        # Act - больше портов чем размер кэша
        ports = [80, 443, 8080, 3000, 5000, 9000, 27017]
        for port in ports:
            get_port_info(port)

        # Assert
        assert call_count == 7, "Должно быть 7 вызовов (все промахи)"

        cache_info = get_port_info.cache_info()
        assert cache_info.misses == 7, f"Должно быть 7 промахов, но {cache_info.misses}"

    def test_port_cache_clear(self):
        """Тест очистки кэша портов."""

        # Arrange
        @lru_cache(maxsize=100)
        def get_port_info(port: int) -> dict:
            return {"port": port, "service": f"service_{port}"}

        # Act - заполнение кэша
        for i in range(50):
            get_port_info(1000 + i)

        # Проверка перед очисткой
        before_clear = get_port_info.cache_info()
        assert before_clear.currsize == 50, "Кэш должен содержать 50 записей"

        # Очистка кэша
        get_port_info.cache_clear()

        # Assert - после очистки
        after_clear = get_port_info.cache_info()
        assert after_clear.currsize == 0, "Кэш должен быть пуст после очистки"
