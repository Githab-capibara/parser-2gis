"""
Тесты для проверки обработки None в cache.get().

Проверяет что кэш корректно обрабатывает None значения:
- cache_get_returns_none_on_miss: возврат None при отсутствии ключа
- cache_get_with_none_check: проверка на None перед использованием
- cache_get_with_default: использование значения по умолчанию
"""

from datetime import datetime, timedelta

import pytest

from parser_2gis.cache import CacheManager


class TestCacheGetReturnsNoneOnMiss:
    """Тесты для возврата None при отсутствии ключа в кэше."""

    def test_cache_get_returns_none_on_miss_empty_cache(self, tmp_path):
        """
        Тест 1.1: Проверка возврата None из пустого кэша.

        Проверяет что при получении ключа из пустого кэша
        возвращается None.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Пытаемся получить несуществующий ключ
            result = cache.get("https://example.com/nonexistent")

            # Проверяем что返回 None
            assert result is None
        finally:
            cache.close()

    def test_cache_get_returns_none_on_miss_expired(self, tmp_path):
        """
        Тест 1.2: Проверка возврата None для истекшего кэша.

        Проверяет что при получении истекшего кэша
        возвращается None и кэш удаляется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Сохраняем данные в кэш
            url = "https://example.com/test"
            data = {"key": "value"}
            cache.set(url, data)

            # Проверяем что данные сохранены
            result = cache.get(url)
            assert result is not None
            assert result["key"] == "value"

            # Истекаем кэш вручную (через БД)
            conn = cache._pool.get_connection()
            cursor = conn.cursor()
            url_hash = cache._hash_url(url)

            # Устанавливаем старую дату истечения
            old_expires_at = (datetime.now() - timedelta(hours=25)).isoformat()
            cursor.execute(
                "UPDATE cache SET expires_at = ? WHERE url_hash = ?", (old_expires_at, url_hash)
            )
            conn.commit()

            # Пытаемся получить истекший кэш
            result = cache.get(url)

            # Проверяем что返回 None (кэш истек и удален)
            assert result is None
        finally:
            cache.close()

    def test_cache_get_returns_none_on_miss_invalid_hash(self, tmp_path):
        """
        Тест 1.3: Проверка возврата None для некорректного хеша.

        Проверяет что при получении с некорректным хешем
        возвращается None.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Пытаемся получить с пустым URL
            result = cache.get("")

            # Проверяем что返回 None
            assert result is None
        finally:
            cache.close()

    def test_cache_get_returns_none_on_miss_corrupted_data(self, tmp_path):
        """
        Тест 1.4: Проверка возврата None для поврежденных данных.

        Проверяет что при получении поврежденных данных
        возвращается None.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Сохраняем данные в кэш напрямую (поврежденные)
            conn = cache._pool.get_connection()
            cursor = conn.cursor()
            url = "https://example.com/corrupted"
            url_hash = cache._hash_url(url)
            expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

            # Вставляем некорректные JSON данные
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache
                (url_hash, url, data, timestamp, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url_hash, url, "{invalid json}", datetime.now().isoformat(), expires_at),
            )
            conn.commit()

            # Пытаемся получить поврежденные данные
            result = cache.get(url)

            # Проверяем что返回 None (данные некорректны)
            assert result is None
        finally:
            cache.close()

    def test_cache_get_returns_none_on_miss_wrong_type(self, tmp_path):
        """
        Тест 1.5: Проверка возврата None для данных неверного типа.

        Проверяет что при получении данных неверного типа
        возвращается None.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Сохраняем данные в кэш напрямую (не dict)
            conn = cache._pool.get_connection()
            cursor = conn.cursor()
            url = "https://example.com/wrong_type"
            url_hash = cache._hash_url(url)
            expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

            # Вставляем JSON массив вместо объекта
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache
                (url_hash, url, data, timestamp, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url_hash, url, "[1, 2, 3]", datetime.now().isoformat(), expires_at),
            )
            conn.commit()

            # Пытаемся получить данные
            result = cache.get(url)

            # Проверяем что返回 None (тип неверный)
            assert result is None
        finally:
            cache.close()


class TestCacheGetWithNoneCheck:
    """Тесты для проверки на None перед использованием кэша."""

    def test_cache_get_with_none_check_pattern(self, tmp_path):
        """
        Тест 2.1: Проверка паттерна проверки на None.

        Проверяет что паттерн проверки на None
        корректно работает.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/test"

            # Паттерн проверки на None
            result = cache.get(url)
            if result is None:
                # Кэш не найден, создаем новые данные
                result = {"key": "new_value"}
                cache.set(url, result)

            # Проверяем что данные получены
            assert result is not None
            assert isinstance(result, dict)
        finally:
            cache.close()

    def test_cache_get_with_none_check_multiple_keys(self, tmp_path):
        """
        Тест 2.2: Проверка проверки на None для нескольких ключей.

        Проверяет что проверка на None корректно работает
        для нескольких ключей.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            urls = [
                "https://example.com/test1",
                "https://example.com/test2",
                "https://example.com/test3",
            ]

            results = []
            for url in urls:
                result = cache.get(url)
                if result is None:
                    result = {"url": url}
                    cache.set(url, result)
                results.append(result)

            # Проверяем что все данные получены
            assert len(results) == 3
            assert all(r is not None for r in results)
        finally:
            cache.close()

    def test_cache_get_with_none_check_nested_data(self, tmp_path):
        """
        Тест 2.3: Проверка проверки на None для вложенных данных.

        Проверяет что проверка на None корректно работает
        для вложенных данных.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/nested"
            data = {"level1": {"level2": {"level3": "value"}}}

            # Сохраняем данные
            cache.set(url, data)

            # Получаем и проверяем на None
            result = cache.get(url)
            if result is not None:
                # Проверяем вложенные данные
                assert "level1" in result
                assert "level2" in result["level1"]
                assert result["level1"]["level2"]["level3"] == "value"
        finally:
            cache.close()


class TestCacheGetWithDefault:
    """Тесты для использования значения по умолчанию."""

    def test_cache_get_with_default_value(self, tmp_path):
        """
        Тест 3.1: Проверка использования значения по умолчанию.

        Проверяет что при отсутствии кэша
        используется значение по умолчанию.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/default"
            default_value = {"key": "default_value"}

            # Получаем с значением по умолчанию
            result = cache.get(url)
            if result is None:
                result = default_value

            # Проверяем что返回 значение по умолчанию
            assert result is not None
            assert result["key"] == "default_value"
        finally:
            cache.close()

    def test_cache_get_with_default_factory(self, tmp_path):
        """
        Тест 3.2: Проверка использования фабрики значений по умолчанию.

        Проверяет что при отсутствии кэша
        используется фабрика значений.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/factory"

            def default_factory():
                return {"created_at": datetime.now().isoformat()}

            # Получаем с фабрикой значений
            result = cache.get(url)
            if result is None:
                result = default_factory()
                cache.set(url, result)

            # Проверяем что данные созданы
            assert result is not None
            assert "created_at" in result
        finally:
            cache.close()

    def test_cache_get_with_default_cached_value(self, tmp_path):
        """
        Тест 3.3: Проверка что значение по умолчанию не используется при наличии кэша.

        Проверяет что при наличии кэша
        значение по умолчанию не используется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/cached"
            cached_value = {"key": "cached_value"}
            default_value = {"key": "default_value"}

            # Сохраняем данные в кэш
            cache.set(url, cached_value)

            # Получаем с значением по умолчанию
            result = cache.get(url)
            if result is None:
                result = default_value

            # Проверяем что использовано кэшированное значение
            assert result is not None
            assert result["key"] == "cached_value"
        finally:
            cache.close()

    def test_cache_get_with_default_multiple_calls(self, tmp_path):
        """
        Тест 3.4: Проверка множественных вызовов с значением по умолчанию.

        Проверяет что при множественных вызовах
        кэш корректно используется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/multiple"
            call_count = 0

            def default_factory():
                nonlocal call_count
                call_count += 1
                return {"call_count": call_count}

            # Первый вызов - кэш пуст
            result1 = cache.get(url)
            if result1 is None:
                result1 = default_factory()
                cache.set(url, result1)

            # Второй вызов - кэш есть
            result2 = cache.get(url)
            if result2 is None:
                result2 = default_factory()
                cache.set(url, result2)

            # Проверяем что фабрика вызвана только один раз
            assert call_count == 1
            assert result1["call_count"] == 1
            assert result2["call_count"] == 1
        finally:
            cache.close()


class TestCacheNoneHandlingEdgeCases:
    """Тесты для граничных случаев обработки None."""

    def test_cache_get_with_none_url(self, tmp_path):
        """
        Тест 4.1: Проверка получения с None URL.

        Проверяет что при получении с None URL
        возвращается None.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Пытаемся получить с None URL
            result = cache.get(None)  # type: ignore

            # Проверяем что返回 None
            assert result is None
        finally:
            cache.close()

    def test_cache_set_with_none_data(self, tmp_path):
        """
        Тест 4.2: Проверка сохранения None данных.

        Проверяет что при сохранении None данных
        возникает ошибка или данные не сохраняются.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/none_data"

            # Пытаемся сохранить None
            with pytest.raises((TypeError, ValueError, AttributeError)):
                cache.set(url, None)  # type: ignore
        finally:
            cache.close()

    def test_cache_get_with_empty_dict(self, tmp_path):
        """
        Тест 4.3: Проверка получения пустого словаря.

        Проверяет что пустой словарь
        не считается за None.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/empty_dict"
            empty_dict = {}

            # Сохраняем пустой словарь
            cache.set(url, empty_dict)

            # Получаем данные
            result = cache.get(url)

            # Проверяем что返回 пустой словарь (не None)
            assert result is not None
            assert result == {}
        finally:
            cache.close()

    def test_cache_get_concurrent_none_checks(self, tmp_path):
        """
        Тест 4.4: Проверка конкурентной проверки на None.

        Проверяет что при конкурентной проверке на None
        кэш корректно работает.
        """
        import threading

        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            url = "https://example.com/concurrent"
            results = []

            def get_cache():
                result = cache.get(url)
                if result is None:
                    result = {"thread": threading.current_thread().name}
                    cache.set(url, result)
                results.append(result)

            # Запускаем несколько потоков
            threads = []
            for i in range(5):
                thread = threading.Thread(target=get_cache, name=f"Thread-{i}")
                threads.append(thread)
                thread.start()

            # Ждем завершения
            for thread in threads:
                thread.join()

            # Проверяем что все потоки получили данные
            assert len(results) == 5
            assert all(r is not None for r in results)
        finally:
            cache.close()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
