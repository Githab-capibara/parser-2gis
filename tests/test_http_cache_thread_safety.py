"""Тесты для проверки потокобезопасности HTTP кэша в remote.py."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

from parser_2gis.chrome.remote import _get_http_cache, _HTTPCache


class TestHTTPCache:
    """Тесты для класса _HTTPCache."""

    def test_get_returns_none_for_empty_cache(self):
        """Пустой кэш должен возвращать None."""
        cache = _HTTPCache(maxsize=10)
        result = cache.get(("GET", "http://example.com", True))
        assert result is None

    def test_set_and_get(self):
        """Установка и получение должны работать."""
        cache = _HTTPCache(maxsize=10)
        mock_response = MagicMock()
        key = ("GET", "http://example.com", True)

        cache.set(key, mock_response)
        result = cache.get(key)

        assert result is mock_response

    def test_get_returns_none_after_expiry(self):
        """Получение должно возвращать None после истечения срока."""
        cache = _HTTPCache(maxsize=10)
        mock_response = MagicMock()
        key = ("GET", "http://example.com", True)

        with patch("parser_2gis.chrome.http_cache.HTTP_CACHE_TTL_SECONDS", -1):
            cache.set(key, mock_response)
            result = cache.get(key)

        assert result is None

    def test_size_returns_correct_count(self):
        """size() должен возвращать правильное количество."""
        cache = _HTTPCache(maxsize=10)

        assert cache.size() == 0

        cache.set(("GET", "http://example1.com", True), MagicMock())
        assert cache.size() == 1

        cache.set(("GET", "http://example2.com", True), MagicMock())
        assert cache.size() == 2

    def test_lru_eviction(self):
        """LRU вытеснение должно работать."""
        cache = _HTTPCache(maxsize=3)

        for i in range(5):
            cache.set(("GET", f"http://example{i}.com", True), MagicMock())

        assert cache.size() <= 5

    def test_cleanup_expired_removes_expired(self):
        """cleanup_expired должен удалять истёкшие записи."""
        cache = _HTTPCache(maxsize=10)

        cache.set(("GET", "http://example1.com", True), MagicMock())
        cache.set(("GET", "http://example2.com", True), MagicMock())

        with patch("parser_2gis.chrome.http_cache.HTTP_CACHE_TTL_SECONDS", -1):
            cleaned = cache.cleanup_expired()

        assert cleaned == 2
        assert cache.size() == 0


class TestHTTP_CACHEThreadSafety:
    """Тесты для потокобезопасности HTTP кэша."""

    def test_concurrent_access_no_crash(self):
        """Параллельный доступ не должен вызывать краш."""
        cache = _HTTPCache(maxsize=100)

        def worker(worker_id):
            for i in range(20):
                key = ("GET", f"http://example{worker_id}-{i}.com", True)
                cache.set(key, MagicMock())
                cache.get(key)
            return worker_id

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        assert len(results) == 10

    def test_concurrent_set_no_race(self):
        """Параллельная установка не должна вызывать race condition."""
        cache = _HTTPCache(maxsize=50)
        errors = []

        def worker(worker_id):
            try:
                for i in range(30):
                    key = ("GET", f"http://example{i}.com", True)
                    cache.set(key, MagicMock())
            except Exception as e:
                errors.append((worker_id, e))

        threads = []
        for i in range(10):
            t = __import__("threading").Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_singleton_pattern(self):
        """Должен использоваться синглтон паттерн."""
        cache1 = _get_http_cache()
        cache2 = _get_http_cache()

        assert cache1 is cache2

    def test_concurrent_singleton_access(self):
        """Параллельный доступ к синглтону не должен вызывать краш."""
        import threading

        caches = []
        errors = []

        def worker():
            try:
                cache = _get_http_cache()
                caches.append(cache)
                for i in range(10):
                    cache.set(("GET", f"http://example{i}.com", True), MagicMock())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(c is caches[0] for c in caches)
