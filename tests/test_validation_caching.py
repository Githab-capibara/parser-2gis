"""
Тесты для кэширования валидации URL.

ИСПРАВЛЕНИЕ P2-4: Кэширование валидации URL
Файлы: parser_2gis/validation.py

Тестируют:
- lru_cache для validate_url()
- Размер кэша
- Производительность кэширования
"""

import os
import sys
import time
from typing import List

from parser_2gis.validation import validate_url

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestValidateUrlCaching:
    """Тесты для кэширования валидации URL."""

    def test_validate_url_caching_basic(self) -> None:
        """Базовый тест кэширования валидации URL."""
        url = "https://2gis.ru/moscow/search/Аптеки"

        # Первый вызов (кэш miss)
        result1 = validate_url(url)
        assert result1.is_valid is True

        # Второй вызов (кэш hit)
        result2 = validate_url(url)
        assert result2.is_valid is True

        # Результаты должны быть одинаковыми
        assert result1.is_valid == result2.is_valid

    def test_validate_url_caching_multiple_urls(self) -> None:
        """Тест кэширования нескольких URL."""
        urls = [
            "https://2gis.ru/moscow/search/Аптеки",
            "https://2gis.ru/spb/search/Рестораны",
            "https://2gis.ru/kazan/search/Магазины",
        ]

        # Валидируем все URL
        results = [validate_url(url) for url in urls]
        assert all(r.is_valid for r in results)

        # Валидируем повторно (должно работать из кэша)
        results_cached = [validate_url(url) for url in urls]
        assert results_cached == results

    def test_validate_url_caching_invalid_urls(self) -> None:
        """Тест кэширования невалидных URL."""
        invalid_urls = ["", "not_a_url", "ftp://invalid.protocol", "javascript:alert(1)"]

        # Валидируем невалидные URL
        results = [validate_url(url) for url in invalid_urls]
        assert not any(r.is_valid for r in results)

        # Валидируем повторно (должно работать из кэша)
        results_cached = [validate_url(url) for url in invalid_urls]
        assert results_cached == results

    def test_validate_url_cache_with_different_protocols(self) -> None:
        """Тест кэширования URL с разными протоколами."""
        urls = [
            "https://2gis.ru/moscow",
            "http://2gis.ru/moscow",  # HTTP тоже допустим
        ]

        results = [validate_url(url) for url in urls]
        # HTTP и HTTPS должны быть валидными
        assert all(r.is_valid for r in results)

    """Тесты для размера кэша URL."""

    def test_validate_url_cache_maxsize(self) -> None:
        """Тест максимального размера кэша."""
        # Создаём 1024 URL (максимальный размер кэша)
        urls = [f"https://2gis.ru/city{i}/search/test" for i in range(1024)]

        # Валидируем все URL
        for url in urls:
            validate_url(url)

        # Проверяем, что кэш работает
        result = validate_url(urls[0])
        assert result.is_valid is True

    def test_validate_url_cache_eviction(self) -> None:
        """Тест вытеснения из кэша."""
        # Создаём больше URL чем размер кэша
        urls = [f"https://2gis.ru/city{i}/search/test" for i in range(1100)]

        # Валидируем все URL
        for url in urls:
            validate_url(url)

        # Первые URL могли быть вытеснены, но кэш должен работать
        # Проверяем последние URL (они точно в кэше)
        result = validate_url(urls[-1])
        assert result.is_valid is True

    def test_validate_url_cache_info(self) -> None:
        """Тест информации о кэше."""
        # Проверяем, что у функции есть cache_info
        assert hasattr(validate_url, "cache_info")

        # Получаем информацию о кэше
        info = validate_url.cache_info()

        # Проверяем структуру
        assert hasattr(info, "hits")
        assert hasattr(info, "misses")
        assert hasattr(info, "maxsize")
        assert hasattr(info, "currsize")

        # Проверяем maxsize
        assert info.maxsize == 1024


class TestValidateUrlPerformance:
    """Тесты производительности кэширования."""

    def test_validate_url_performance_cached(self) -> None:
        """Тест производительности кэшированных URL."""
        url = "https://2gis.ru/moscow/search/Аптеки"

        # Первый вызов (кэш miss)
        start1 = time.time()
        validate_url(url)
        elapsed1 = time.time() - start1

        # Второй вызов (кэш hit)
        start2 = time.time()
        validate_url(url)
        elapsed2 = time.time() - start2

        # Кэшированный вызов должен быть быстрее
        # (или хотя бы не медленнее)
        assert elapsed2 <= elapsed1 + 0.1  # Небольшой допуск

    def test_validate_url_performance_many_urls(self) -> None:
        """Тест производительности многих URL."""
        urls = [f"https://2gis.ru/city{i}/search/test" for i in range(100)]

        start = time.time()
        for url in urls:
            validate_url(url)
        elapsed = time.time() - start

        # Должно выполниться за разумное время
        assert elapsed < 5.0  # 5 секунд на 100 URL


class TestValidateUrlEdgeCases:
    """Тесты для граничных случаев."""

    def test_validate_url_with_unicode(self) -> None:
        """Тест URL с Unicode символами."""
        urls = [
            "https://2gis.ru/москва/search/Аптеки",
            "https://2gis.ru/санкт-петербург/search/Рестораны",
        ]

        results = [validate_url(url) for url in urls]
        assert all(r.is_valid for r in results)

        # Проверяем кэширование
        results_cached = [validate_url(url) for url in urls]
        assert results_cached == results

    def test_validate_url_with_special_characters(self) -> None:
        """Тест URL со специальными символами."""
        urls = [
            "https://2gis.ru/moscow/search/Аптеки?query=test",
            "https://2gis.ru/moscow/search/Аптеки#anchor",
        ]

        results = [validate_url(url) for url in urls]
        assert all(r.is_valid for r in results)

    def test_validate_url_with_ports(self) -> None:
        """Тест URL с портами."""
        urls = ["https://2gis.ru:443/moscow", "http://2gis.ru:80/moscow"]

        results = [validate_url(url) for url in urls]
        assert all(r.is_valid for r in results)

    def test_validate_url_with_query_params(self) -> None:
        """Тест URL с query параметрами."""
        urls = [
            "https://2gis.ru/moscow/search?query=Аптеки&limit=10",
            "https://2gis.ru/moscow/search?query=Рестораны&sort=rating",
        ]

        results = [validate_url(url) for url in urls]
        assert all(r.is_valid for r in results)


class TestValidateUrlCachedFunction:
    """Тесты для декорированной функции."""

    def test_validate_url_cached_decorator(self) -> None:
        """Тест наличия lru_cache декоратора."""
        # Проверяем, что функция имеет атрибуты lru_cache
        assert hasattr(validate_url, "cache_info")
        assert hasattr(validate_url, "cache_clear")

    def test_validate_url_cached_wraps_correctly(self) -> None:
        """Тест корректной обёртки."""
        url = "https://2gis.ru/moscow"

        # Вызываем функцию
        result = validate_url(url)

        # Проверяем результат
        assert result.is_valid is True

        # Проверяем, что кэш обновился
        info = validate_url.cache_info()
        assert info.misses > 0

        # Вызываем снова
        result2 = validate_url(url)
        assert result2.is_valid is True

        # Проверяем, что hits увеличился
        info2 = validate_url.cache_info()
        assert info2.hits > info.hits


class TestValidateUrlIntegration:
    """Интеграционные тесты."""

    def test_validate_url_integration_real_urls(self) -> None:
        """Интеграционный тест с реальными URL."""
        # Очищаем кэш перед тестом
        validate_url.cache_clear()

        real_urls = [
            "https://2gis.ru/moscow/search/Аптеки",
            "https://2gis.ru/spb/search/Рестораны",
            "https://2gis.ru/kazan/search/Магазины",
            "https://2gis.ru/ekb/search/Услуги",
            "https://2gis.ru/nn/search/Организации",
        ]

        # Валидируем все URL
        results = [validate_url(url) for url in real_urls]
        assert all(r.is_valid for r in results)

        # Валидируем повторно (кэш)
        results_cached = [validate_url(url) for url in real_urls]
        assert results_cached == results

        # Проверяем статистику кэша
        info = validate_url.cache_info()
        assert info.hits == len(real_urls)  # Все вторые вызовы - hits
        assert info.misses == len(real_urls)  # Все первые вызовы - misses

    def test_validate_url_integration_mixed(self) -> None:
        """Интеграционный тест со смешанными URL."""
        urls = [
            ("https://2gis.ru/moscow", True),
            ("https://2gis.ru/spb", True),
            ("", False),
            ("not_a_url", False),
            ("https://2gis.ru/kazan", True),
        ]

        # Валидируем все URL
        for url, expected in urls:
            result = validate_url(url)
            assert result.is_valid == expected, f"URL: {url}"

        # Валидируем повторно
        for url, expected in urls:
            result = validate_url(url)
            assert result.is_valid == expected, f"URL: {url} (cached)"


class TestValidateUrlConcurrency:
    """Тесты конкурентного доступа."""

    def test_validate_url_concurrent_access(self) -> None:
        """Тест конкурентного доступа к кэшу."""
        import threading

        url = "https://2gis.ru/moscow/search/Аптеки"
        results: List[bool] = []
        lock = threading.Lock()

        def worker() -> None:
            """Работник для валидации."""
            result = validate_url(url)
            with lock:
                results.append(result)

        # Запускаем 10 потоков
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Ждём завершения
        for thread in threads:
            thread.join()

        # Все результаты должны быть True
        assert all(r.is_valid for r in results)
        assert len(results) == 10

    def test_validate_url_concurrent_different_urls(self) -> None:
        """Тест конкурентного доступа к разным URL."""
        import threading

        urls = [f"https://2gis.ru/city{i}/search/test" for i in range(100)]
        results: List[bool] = []
        lock = threading.Lock()

        def worker(url: str) -> None:
            """Работник для валидации."""
            result = validate_url(url)
            with lock:
                results.append(result)

        # Запускаем 100 потоков
        threads = []
        for url in urls:
            thread = threading.Thread(target=worker, args=(url,))
            threads.append(thread)
            thread.start()

        # Ждём завершения
        for thread in threads:
            thread.join()

        # Все результаты должны быть True
        assert all(r.is_valid for r in results)
        assert len(results) == 100
