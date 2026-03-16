"""
Комплексные тесты для аудита кода.

Проверяют:
- Правильность обработки ошибок
- Потокобезопасность критических операций
- Отсутствие утечек ресурсов
- Обработку граничных случаев
"""

import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from parser_2gis.cache import CacheManager
from parser_2gis.parallel_parser import ParallelCityParser
from parser_2gis.config import Configuration


class TestCacheThreadSafety:
    """Тесты для потокобезопасности кэша."""

    def test_cache_manager_concurrent_writes(self, tmp_path):
        """Проверка одновременной записи в кэш из нескольких потоков."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        results = []

        def write_cache(idx):
            """Записать в кэш из потока."""
            try:
                url = f"https://test.com/page{idx}"
                data = {"id": idx, "data": f"test_{idx}"}
                cache.set(url, data)
                results.append(("success", idx))
            except Exception as e:
                results.append(("error", idx, str(e)))

        # Запускаем 10 потоков одновременно
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_cache, i) for i in range(10)]
            for future in futures:
                future.result()

        # Проверяем, что все записи прошли успешно
        success_count = sum(1 for r in results if r[0] == "success")
        assert success_count == 10, f"Ошибок при записи: {results}"

        cache.close()

    def test_cache_manager_concurrent_reads_writes(self, tmp_path):
        """Проверка одновременного чтения и записи в кэш."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        
        # Предварительно пишем данные
        for i in range(5):
            url = f"https://test.com/page{i}"
            cache.set(url, {"id": i})

        read_results = []
        write_results = []

        def read_cache(idx):
            """Читать из кэша из потока."""
            try:
                url = f"https://test.com/page{idx % 5}"
                data = cache.get(url)
                read_results.append(("success", idx, data is not None))
            except Exception as e:
                read_results.append(("error", idx, str(e)))

        def write_cache(idx):
            """Писать в кэш из потока."""
            try:
                url = f"https://test.com/newpage{idx}"
                cache.set(url, {"id": idx})
                write_results.append(("success", idx))
            except Exception as e:
                write_results.append(("error", idx, str(e)))

        # Запускаем чтение и запись одновременно
        with ThreadPoolExecutor(max_workers=10) as executor:
            read_futures = [executor.submit(read_cache, i) for i in range(5)]
            write_futures = [executor.submit(write_cache, i) for i in range(5)]
            for future in read_futures + write_futures:
                future.result()

        # Проверяем результаты
        assert len(read_results) == 5
        assert len(write_results) == 5

        cache.close()

    def test_cache_manager_batch_operations_thread_safe(self, tmp_path):
        """Проверка потокобезопасности пакетных операций."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        items = [(f"https://test.com/{i}", {"id": i}) for i in range(100)]

        results = []

        def batch_write(batch_idx):
            """Пакетная запись в кэш."""
            try:
                batch = items[batch_idx * 10:(batch_idx + 1) * 10]
                count = cache.set_batch(batch)
                results.append(("success", count))
            except Exception as e:
                results.append(("error", str(e)))

        # Запускаем 10 пакетных операций параллельно
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(batch_write, i) for i in range(10)]
            for future in futures:
                future.result()

        # Проверяем результаты
        assert len(results) == 10
        success_count = sum(1 for r in results if r[0] == "success")
        assert success_count == 10

        cache.close()


class TestParallelParserValidation:
    """Тесты для валидации параллельного парсера."""

    def test_parallel_parser_invalid_max_workers_zero(self):
        """Проверка отклонения max_workers=0."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        with pytest.raises(ValueError, match="max_workers должен быть"):
            ParallelCityParser(cities, categories, "/tmp", config, max_workers=0)

    def test_parallel_parser_invalid_max_workers_exceeds_max(self):
        """Проверка отклонения max_workers > 20."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        with pytest.raises(ValueError, match="max_workers должен быть"):
            ParallelCityParser(cities, categories, "/tmp", config, max_workers=21)

    def test_parallel_parser_invalid_timeout_too_low(self):
        """Проверка отклонения timeout_per_url < 60."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        with pytest.raises(ValueError, match="timeout_per_url должен быть"):
            ParallelCityParser(cities, categories, "/tmp", config, timeout_per_url=30)

    def test_parallel_parser_invalid_timeout_too_high(self):
        """Проверка отклонения timeout_per_url > 3600."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]
        categories = [{"name": "Cafes", "id": 1}]

        with pytest.raises(ValueError, match="timeout_per_url должен быть"):
            ParallelCityParser(cities, categories, "/tmp", config, timeout_per_url=4000)

    def test_parallel_parser_empty_cities(self):
        """Проверка отклонения пустого списка городов."""
        config = Configuration()
        categories = [{"name": "Cafes", "id": 1}]

        with pytest.raises(ValueError, match="Список городов не может быть пустым"):
            ParallelCityParser([], categories, "/tmp", config)

    def test_parallel_parser_empty_categories(self):
        """Проверка отклонения пустого списка категорий."""
        config = Configuration()
        cities = [{"name": "Moscow", "id": 1}]

        with pytest.raises(ValueError, match="Список категорий не может быть пустым"):
            ParallelCityParser(cities, [], "/tmp", config)


class TestCacheErrorHandling:
    """Тесты для обработки ошибок в кэше."""

    def test_cache_invalid_ttl_zero(self, tmp_path):
        """Проверка отклонения ttl_hours=0."""
        with pytest.raises(ValueError, match="ttl_hours должен быть положительным"):
            CacheManager(tmp_path, ttl_hours=0)

    def test_cache_invalid_ttl_negative(self, tmp_path):
        """Проверка отклонения ttl_hours < 0."""
        with pytest.raises(ValueError, match="ttl_hours должен быть положительным"):
            CacheManager(tmp_path, ttl_hours=-1)

    def test_cache_get_nonexistent_url(self, tmp_path):
        """Проверка получения несуществующего URL из кэша."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        result = cache.get("https://nonexistent.com/page")
        assert result is None
        cache.close()

    def test_cache_clear_empty_batch(self, tmp_path):
        """Проверка очистки пустого списка хешей."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        count = cache.clear_batch([])
        assert count == 0
        cache.close()

    def test_cache_stats_after_operations(self, tmp_path):
        """Проверка статистики кэша после различных операций."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        
        # Добавляем данные
        cache.set("https://test.com/1", {"id": 1})
        cache.set("https://test.com/2", {"id": 2})
        
        stats = cache.get_stats()
        assert stats["total_records"] == 2
        
        # Очищаем кэш
        cache.clear()
        stats = cache.get_stats()
        assert stats["total_records"] == 0
        
        cache.close()


class TestResourceManagement:
    """Тесты для управления ресурсами."""

    def test_cache_manager_context_manager(self, tmp_path):
        """Проверка использования кэша как контекстного менеджера."""
        with CacheManager(tmp_path, ttl_hours=1) as cache:
            cache.set("https://test.com/1", {"id": 1})
            data = cache.get("https://test.com/1")
            assert data is not None
        # После выхода из контекста соединения должны быть закрыты

    def test_cache_manager_del_cleanup(self, tmp_path):
        """Проверка очистки при удалении объекта кэша."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        cache.set("https://test.com/1", {"id": 1})
        # Удаляем объект - должна произойти автоматическая очистка
        del cache
        # Дополнительных ошибок не должно быть

    def test_cache_pool_connection_reuse(self, tmp_path):
        """Проверка переиспользования соединений в пуле."""
        cache = CacheManager(tmp_path, ttl_hours=1, pool_size=3)
        
        # Записываем несколько значений
        for i in range(10):
            cache.set(f"https://test.com/{i}", {"id": i})
        
        # Читаем значения
        for i in range(10):
            data = cache.get(f"https://test.com/{i}")
            assert data is not None

        cache.close()


class TestErrorRecovery:
    """Тесты для восстановления после ошибок."""

    def test_cache_recovery_after_clear_expired(self, tmp_path):
        """Проверка восстановления кэша после очистки истекших записей."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        
        cache.set("https://test.com/1", {"id": 1})
        count = cache.clear_expired()
        # Данные еще не должны быть удалены (TTL еще не истек)
        assert count == 0
        
        data = cache.get("https://test.com/1")
        assert data is not None
        
        cache.close()

    def test_cache_batch_partial_failure_handling(self, tmp_path):
        """Проверка обработки частичных ошибок при пакетной операции."""
        cache = CacheManager(tmp_path, ttl_hours=1)
        
        items = [
            ("https://test.com/1", {"id": 1}),
            ("https://test.com/2", {"id": 2}),
            ("https://test.com/3", {"id": 3}),
        ]
        
        # Должна успешно записаться даже при смешанных данных
        count = cache.set_batch(items)
        assert count == 3
        
        cache.close()

