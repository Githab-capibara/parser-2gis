"""
Бенчмарки производительности для критических функций парсера.

Исправление L5:
- Добавлены тесты производительности для часто вызываемых функций
- Используется pytest-benchmark для измерения времени выполнения
- Помогает выявлять регрессии производительности

Пример запуска:
    pytest tests/test_benchmarks.py --benchmark-only

Пример сравнения с предыдущими результатами:
    pytest tests/test_benchmarks.py --benchmark-compare=0001
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

import pytest

from parser_2gis.cache import Cache
from parser_2gis.common import (
    _validate_category_cached,
    _validate_city_cached,
    generate_city_urls,
    get_cache_stats,
    log_cache_stats,
    url_query_encode,
)
from parser_2gis.validator import DataValidator

# =============================================================================
# БЕНЧМАРКИ КЭШИРОВАНИЯ (M3)
# =============================================================================


class TestCacheBenchmarks:
    """Бенчмарки для функций кэширования."""

    @pytest.mark.benchmark(group="cache-city-validation")
    def test_validate_city_cached_performance(self, benchmark: Any) -> None:
        """Бенчмарк производительности валидации города.

        Ожидаемое время: < 1μs для кэшированных значений
        """
        city_data = {"code": "msk", "domain": "moscow.2gis.ru"}

        # Прогрев кэша
        _validate_city_cached("msk", "moscow.2gis.ru")

        result = benchmark(_validate_city_cached, "msk", "moscow.2gis.ru")
        assert result == city_data

    @pytest.mark.benchmark(group="cache-category-validation")
    def test_validate_category_cached_performance(self, benchmark: Any) -> None:
        """Бенчмарк производительности валидации категории.

        Ожидаемое время: < 1μs для кэшированных значений
        """
        category_data = {"id": 93, "name": "Рестораны"}

        # Прогрев кэша
        _validate_category_cached(93, "Рестораны")

        result = benchmark(_validate_category_cached, 93, "Рестораны")
        assert result == category_data

    @pytest.mark.benchmark(group="cache-url-encoding")
    def test_url_query_encode_performance(self, benchmark: Any) -> None:
        """Бенчмарк производительности кодирования URL.

        Ожидаемое время: < 0.5μs для кэшированных значений
        """
        query = "рестораны москва"

        # Прогрев кэша
        url_query_encode(query)

        result = benchmark(url_query_encode, query)
        assert "%D1%80" in result  # Проверка кодировки UTF-8

    @pytest.mark.benchmark(group="cache-stats")
    def test_get_cache_stats_performance(self, benchmark: Any) -> None:
        """Бенчмарк получения статистики кэшей.

        Ожидаемое время: < 10μs
        """
        result = benchmark(get_cache_stats)
        assert isinstance(result, dict)
        assert len(result) >= 5  # Минимум 5 кэшей

    @pytest.mark.benchmark(group="cache-logging")
    def test_log_cache_stats_performance(self, benchmark: Any) -> None:
        """Бенчмарк логирования статистики кэшей.

        Ожидаемое время: < 100μs
        """
        benchmark(log_cache_stats)


# =============================================================================
# БЕНЧМАРКИ ВАЛИДАЦИИ (M4)
# =============================================================================


class TestValidationBenchmarks:
    """Бенчмарки для функций валидации."""

    @pytest.fixture
    def validator(self) -> DataValidator:
        """Фикстура для DataValidator."""
        return DataValidator()

    @pytest.mark.benchmark(group="validation-phone")
    def test_validate_phone_performance(
        self, validator: DataValidator, benchmark: Any
    ) -> None:
        """Бенчмарк валидации телефонного номера.

        Ожидаемое время: < 50μs
        """
        phone = "+7 (999) 123-45-67"

        result = benchmark(validator.validate_phone, phone)
        assert result.is_valid
        assert result.value == "8 (999) 123-45-67"

    @pytest.mark.benchmark(group="validation-phone-unicode")
    def test_validate_phone_unicode_performance(
        self, validator: DataValidator, benchmark: Any
    ) -> None:
        """Бенчмарк валидации телефона с Unicode символами.

        Ожидаемое время: < 100μs
        """
        # Арабские цифры
        phone = "+٧ (٩٩٩) ١٢٣-٤٥-٦٧"

        result = benchmark(validator.validate_phone, phone)
        assert result.is_valid

    @pytest.mark.benchmark(group="validation-email")
    def test_validate_email_performance(
        self, validator: DataValidator, benchmark: Any
    ) -> None:
        """Бенчмарк валидации email.

        Ожидаемое время: < 20μs
        """
        email = "test@example.com"

        result = benchmark(validator.validate_email, email)
        assert result.is_valid


# =============================================================================
# БЕНЧМАРКИ РАБОТЫ С КЭШЕМ (L8)
# =============================================================================


class TestCacheOperationsBenchmarks:
    """Бенчмарки для операций с кэшем."""

    @pytest.fixture
    def cache(self, tmp_path: Path) -> Cache:
        """Фикстура для Cache."""
        cache_dir = tmp_path / "test_cache"
        return Cache(cache_dir=cache_dir, db_name="test_cache.db")

    @pytest.mark.benchmark(group="cache-operations-get")
    def test_cache_get_performance(self, cache: Cache, benchmark: Any) -> None:
        """Бенчмарк получения данных из кэша.

        Ожидаемое время: < 1ms для SQLite кэша
        """
        url = "https://2gis.ru/moscow"
        data = {"test": "data"}

        # Запись в кэш
        cache.set(url, data)

        result = benchmark(cache.get, url)
        assert result == data

    @pytest.mark.benchmark(group="cache-operations-set")
    def test_cache_set_performance(self, cache: Cache, benchmark: Any) -> None:
        """Бенчмарк записи данных в кэш.

        Ожидаемое время: < 2ms для SQLite кэша
        """
        url = "https://2gis.ru/spb"
        data = {"test": "data"}

        benchmark(cache.set, url, data)
        assert cache.get(url) == data

    @pytest.mark.benchmark(group="cache-operations-delete")
    def test_cache_delete_performance(self, cache: Cache, benchmark: Any) -> None:
        """Бенчмарк удаления данных из кэша.

        Ожидаемое время: < 1ms
        """
        url = "https://2gis.ru/kazan"
        data = {"test": "data"}

        cache.set(url, data)
        benchmark(cache.delete, url)
        assert cache.get(url) is None


# =============================================================================
# БЕНЧМАРКИ ГЕНЕРАЦИИ URL (L8)
# =============================================================================


class TestURLGenerationBenchmarks:
    """Бенчмарки для генерации URL."""

    @pytest.mark.benchmark(group="url-generation")
    def test_generate_city_urls_performance(self, benchmark: Any) -> None:
        """Бенчмарк генерации URL городов.

        Ожидаемое время: < 10ms для 10 городов
        """
        cities = [
            {"code": "msk", "domain": "moscow.2gis.ru"},
            {"code": "spb", "domain": "spb.2gis.ru"},
            {"code": "ekb", "domain": "ekb.2gis.ru"},
        ]
        categories = [{"id": 93, "name": "Рестораны"}]

        result = benchmark(generate_city_urls, cities, categories)
        assert len(result) == 3  # 3 города

    @pytest.mark.benchmark(group="url-generation-large")
    def test_generate_city_urls_large_performance(self, benchmark: Any) -> None:
        """Бенчмарк генерации URL для большого количества городов.

        Ожидаемое время: < 100ms для 100 городов
        """
        cities = [
            {"code": f"city{i}", "domain": f"city{i}.2gis.ru"} for i in range(100)
        ]
        categories = [{"id": 93, "name": "Рестораны"}]

        result = benchmark(generate_city_urls, cities, categories)
        assert len(result) == 100


# =============================================================================
# БЕНЧМАРКИ СЛИЯНИЯ CSV (L8)
# =============================================================================


class TestCSVMergeBenchmarks:
    """Бенчмарки для слияния CSV файлов."""

    @pytest.mark.benchmark(group="csv-merge")
    def test_merge_small_files(self, benchmark: Any, tmp_path: Path) -> None:
        """Бенчмарк слияния небольших CSV файлов.

        Ожидаемое время: < 50ms
        """
        # Создаём тестовые файлы
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        for i in range(5):
            file = output_dir / f"test_{i}.csv"
            with open(file, "w", encoding="utf-8") as f:
                f.write("id,name\n")
                for j in range(100):
                    f.write(f"{i * 100 + j},name{j}\n")

        output_file = tmp_path / "merged.csv"

        # Импортируем функцию слияния
        from parser_2gis.parallel_parser import _merge_csv_files

        benchmark(_merge_csv_files, output_dir, output_file)
        assert output_file.exists()


# =============================================================================
# БЕНЧМАРКИ ОБРАБОТКИ БОЛЬШИХ ДАННЫХ (L8)
# =============================================================================


class TestLargeDataBenchmarks:
    """Бенчмарки для обработки больших данных."""

    @pytest.mark.benchmark(group="large-data")
    def test_cache_large_dataset(self, benchmark: Any, tmp_path: Path) -> None:
        """Бенчмарк работы с большим набором данных.

        Ожидаемое время: < 500ms для 1000 записей
        """
        cache_dir = tmp_path / "test_cache"
        cache = Cache(cache_dir=cache_dir, db_name="test_cache.db")

        # Генерируем данные
        data = {f"url{i}": {"id": i, "name": f"item{i}"} for i in range(1000)}

        def cache_operations() -> None:
            for url, item in data.items():
                cache.set(url, item)
                cache.get(url)

        benchmark(cache_operations)

        cache.close()


# =============================================================================
# КОНФИГУРАЦИЯ PYTEST-BENCHMARK
# =============================================================================


def pytest_configure(config: Any) -> None:
    """Настройка pytest-benchmark."""
    config.addinivalue_line(
        "markers",
        "benchmark: mark test as benchmark (требует pytest-benchmark)",
    )


if __name__ == "__main__":
    # Запуск бенчмарков напрямую
    pytest.main([__file__, "-v", "--benchmark-only"])
