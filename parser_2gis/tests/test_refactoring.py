"""Тесты для рефакторинга God Class проблем (ISSUE-002, ISSUE-003, ISSUE-004).

Этот модуль тестирует выделенные классы и функции:
- strategies.py (ISSUE-002: ParallelCityParser)
- request_interceptor.py (ISSUE-003: ChromeRemote)
- cache_utils.py (ISSUE-004: CacheManager)
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ISSUE-002: Тесты для strategies.py
# =============================================================================


class TestUrlGenerationStrategy:
    """Тесты для UrlGenerationStrategy."""

    def test_generate_all_urls(self):
        """Тестирует генерацию всех URL."""
        from parser_2gis.parallel.strategies import UrlGenerationStrategy

        cities = [
            {"code": "msk", "domain": "2gis.ru", "name": "Москва"},
            {"code": "spb", "domain": "2gis.ru", "name": "Санкт-Петербург"},
        ]
        categories = [{"id": "1", "name": "Аптеки"}, {"id": "2", "name": "Рестораны"}]

        stats_lock = threading.RLock()
        stats = {"total": 0}

        strategy = UrlGenerationStrategy(cities, categories, stats_lock)
        urls = strategy.generate_all_urls(stats)

        assert len(urls) == 4  # 2 города × 2 категории
        assert stats["total"] == 4

        # Проверяем структуру URL
        for url, category_name, city_name in urls:
            assert isinstance(url, str)
            assert "2gis.ru" in url
            assert city_name in ["Москва", "Санкт-Петербург"]
            assert category_name in ["Аптеки", "Рестораны"]

    def test_generate_all_urls_lazy(self):
        """Тестирует ленивую генерацию URL."""
        from parser_2gis.parallel.strategies import UrlGenerationStrategy

        cities = [{"code": "msk", "domain": "2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Аптеки"}]

        stats_lock = threading.RLock()
        strategy = UrlGenerationStrategy(cities, categories, stats_lock)

        urls = list(strategy.generate_all_urls_lazy())

        assert len(urls) == 1
        assert urls[0][1] == "Аптеки"
        assert urls[0][2] == "Москва"


class TestMemoryCheckStrategy:
    """Тесты для MemoryCheckStrategy."""

    def test_check_memory(self):
        """Тестирует проверку памяти."""
        from parser_2gis.parallel.strategies import MemoryCheckStrategy

        strategy = MemoryCheckStrategy(memory_threshold_mb=100)
        is_enough, available_mb = strategy.check_memory()

        assert isinstance(is_enough, bool)
        assert isinstance(available_mb, int)
        assert available_mb >= 0

    def test_is_memory_low(self):
        """Тестирует проверку низкой памяти."""
        from parser_2gis.parallel.strategies import MemoryCheckStrategy

        strategy = MemoryCheckStrategy(memory_threshold_mb=100)
        is_low = strategy.is_memory_low()

        assert isinstance(is_low, bool)


class TestParseStrategy:
    """Тесты для ParseStrategy."""

    def test_init(self):
        """Тестирует инициализацию ParseStrategy."""
        from parser_2gis.parallel.strategies import ParseStrategy

        config = MagicMock()
        output_dir = Path("/tmp/test")

        strategy = ParseStrategy(output_dir=output_dir, config=config, timeout_per_url=300)

        assert strategy.output_dir == output_dir
        assert strategy.timeout_per_url == 300

    def test_create_temp_filename(self):
        """Тестирует создание имени временного файла."""
        from parser_2gis.parallel.strategies import ParseStrategy

        config = MagicMock()
        output_dir = Path("/tmp/test")

        strategy = ParseStrategy(output_dir=output_dir, config=config)
        temp_filename, temp_filepath = strategy._create_temp_filename("msk", "apteki")

        assert "msk" in temp_filename
        assert "apteki" in temp_filename
        assert temp_filename.endswith(".tmp")
        assert temp_filepath.parent == output_dir


# =============================================================================
# ISSUE-003: Тесты для request_interceptor.py
# =============================================================================


class TestRequestInterceptor:
    """Тесты для RequestInterceptor."""

    def test_init(self):
        """Тестирует инициализацию RequestInterceptor."""
        from parser_2gis.chrome.request_interceptor import RequestInterceptor

        interceptor = RequestInterceptor()

        assert interceptor._requests == {}
        assert interceptor._response_patterns == []
        assert interceptor._response_queues == {}

    def test_register_response_pattern(self):
        """Тестирует регистрацию паттерна ответа."""
        from parser_2gis.chrome.request_interceptor import RequestInterceptor

        interceptor = RequestInterceptor()
        interceptor.register_response_pattern(r".*2gis\.ru.*")

        assert r".*2gis\.ru.*" in interceptor._response_patterns
        assert r".*2gis\.ru.*" in interceptor._response_queues

    def test_unregister_response_pattern(self):
        """Тестирует удаление паттерна ответа."""
        from parser_2gis.chrome.request_interceptor import RequestInterceptor

        interceptor = RequestInterceptor()
        interceptor.register_response_pattern(r".*2gis\.ru.*")
        interceptor.unregister_response_pattern(r".*2gis\.ru.*")

        assert r".*2gis\.ru.*" not in interceptor._response_patterns
        assert r".*2gis\.ru.*" not in interceptor._response_queues

    def test_clear_requests(self):
        """Тестирует очистку запросов."""
        from parser_2gis.chrome.request_interceptor import RequestInterceptor

        interceptor = RequestInterceptor()
        interceptor.register_response_pattern(r".*test.*")
        interceptor._requests["test_id"] = {"url": "http://test.com"}

        interceptor.clear_requests()

        assert interceptor._requests == {}

    def test_get_stats(self):
        """Тестирует получение статистики."""
        from parser_2gis.chrome.request_interceptor import RequestInterceptor

        interceptor = RequestInterceptor()
        interceptor.register_response_pattern(r".*test.*")
        interceptor._requests["test_id"] = {"url": "http://test.com"}

        stats = interceptor.get_stats()

        assert "pending_requests" in stats
        assert "registered_patterns" in stats
        assert "response_queues" in stats
        assert stats["pending_requests"] == 1
        assert stats["registered_patterns"] == 1


# =============================================================================
# ISSUE-004: Тесты для cache_utils.py
# =============================================================================


class TestCacheUtils:
    """Тесты для вспомогательных функций кэширования."""

    def test_hash_url(self):
        """Тестирует хеширование URL."""
        from parser_2gis.cache.cache_utils import hash_url

        url = "https://2gis.ru/moscow/search/Аптеки"
        hash_result = hash_url(url)

        assert len(hash_result) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in hash_result)

        # Одинаковые URL дают одинаковый хеш
        assert hash_url(url) == hash_url(url)

        # Разные URL дают разные хеши
        assert hash_url(url) != hash_url("https://2gis.ru/spb/search/Аптеки")

    def test_hash_url_errors(self):
        """Тестирует ошибки хеширования URL."""
        from parser_2gis.cache.cache_utils import hash_url

        with pytest.raises(ValueError, match="URL не может быть None"):
            hash_url(None)  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="URL должен быть строкой"):
            hash_url(123)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="URL не может быть пустой строкой"):
            hash_url("")

    def test_validate_hash(self):
        """Тестирует валидацию хеша."""
        from parser_2gis.cache.cache_utils import validate_hash

        # Валидный хеш
        valid_hash = "a" * 64
        assert validate_hash(valid_hash) is True

        # Невалидная длина
        assert validate_hash("a" * 63) is False
        assert validate_hash("a" * 65) is False

        # Невалидные символы
        assert validate_hash("g" * 64) is False
        assert validate_hash("!" * 64) is False

    def test_compute_crc32_cached(self):
        """Тестирует вычисление CRC32 с кэшированием."""
        from parser_2gis.cache.cache_utils import compute_crc32_cached

        data_json = '{"key": "value"}'
        data_json_hash = "a" * 64

        crc1 = compute_crc32_cached(data_json_hash, data_json)
        crc2 = compute_crc32_cached(data_json_hash, data_json)

        assert isinstance(crc1, int)
        assert crc1 == crc2  # Кэширование

    def test_compute_data_json_hash(self):
        """Тестирует вычисление хеша данных."""
        from parser_2gis.cache.cache_utils import compute_data_json_hash

        data_json = '{"key": "value"}'
        hash1 = compute_data_json_hash(data_json)
        hash2 = compute_data_json_hash(data_json)

        assert len(hash1) == 64
        assert hash1 == hash2  # Одинаковые данные = одинаковый хеш

    def test_parse_expires_at(self):
        """Тестирует парсинг даты истечения."""
        from parser_2gis.cache.cache_utils import parse_expires_at

        # Валидная дата
        expires_str = "2024-12-31T23:59:59"
        expires_at = parse_expires_at(expires_str)

        assert expires_at is not None
        assert expires_at.year == 2024
        assert expires_at.month == 12
        assert expires_at.day == 31

        # Невалидная дата
        assert parse_expires_at("invalid") is None

    def test_is_cache_expired(self):
        """Тестирует проверку истечения кэша."""
        from datetime import datetime, timedelta

        from parser_2gis.cache.cache_utils import is_cache_expired

        # Истёкший кэш
        past = datetime.now() - timedelta(hours=1)
        assert is_cache_expired(past) is True

        # Будущий кэш
        future = datetime.now() + timedelta(hours=1)
        assert is_cache_expired(future) is False

        # None
        assert is_cache_expired(None) is True


# =============================================================================
# Интеграционные тесты
# =============================================================================


class TestIntegration:
    """Интеграционные тесты для рефакторинга."""

    def test_strategies_integration(self):
        """Тестирует интеграцию стратегий."""
        from parser_2gis.parallel.strategies import MemoryCheckStrategy, UrlGenerationStrategy

        cities = [{"code": "msk", "domain": "2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Аптеки"}]

        stats_lock = threading.RLock()
        stats = {"total": 0, "success": 0, "failed": 0}

        url_strategy = UrlGenerationStrategy(cities, categories, stats_lock)
        memory_strategy = MemoryCheckStrategy()

        # Проверяем что стратегии работают вместе
        urls = url_strategy.generate_all_urls(stats)
        assert len(urls) > 0

        is_enough, _ = memory_strategy.check_memory()
        assert isinstance(is_enough, bool)

    def test_request_interceptor_integration(self):
        """Тестирует интеграцию RequestInterceptor."""
        from parser_2gis.chrome.request_interceptor import RequestInterceptor

        interceptor = RequestInterceptor()

        # Регистрируем паттерн
        interceptor.register_response_pattern(r".*api\.test\.com.*")

        # Проверяем статистику
        stats = interceptor.get_stats()
        assert stats["registered_patterns"] == 1

        # Очищаем
        interceptor.clear_requests()
        stats = interceptor.get_stats()
        assert stats["pending_requests"] == 0

    def test_cache_utils_integration(self):
        """Тестирует интеграцию cache_utils."""
        from parser_2gis.cache.cache_utils import (
            compute_crc32_cached,
            compute_data_json_hash,
            hash_url,
            is_cache_expired,
            validate_hash,
        )

        url = "https://2gis.ru/test"
        data_json = '{"key":"value"}'

        # Цепочка вычислений
        url_hash = hash_url(url)
        assert validate_hash(url_hash) is True

        data_hash = compute_data_json_hash(data_json)
        assert validate_hash(data_hash) is True

        crc = compute_crc32_cached(data_hash, data_json)
        assert isinstance(crc, int)

        # Проверка времени
        from datetime import datetime, timedelta

        future = datetime.now() + timedelta(hours=1)
        assert not is_cache_expired(future)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
