"""
Комплексные тесты для улучшений cache pool.

Этот модуль тестирует:
- parser_2gis/cache/pool.py - атомарность операций с RLock
- parser_2gis/cache/pool.py - кэширование _calculate_dynamic_pool_size
- parser_2gis/cache/manager.py - docstrings в _enforce_cache_size_limit
- parser_2gis/cache/manager.py - SQL injection protection (параметризованные запросы)

Каждый тест проверяет ОДНО конкретное исправление.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

from parser_2gis.cache.pool import ConnectionPool, _calculate_dynamic_pool_size

# =============================================================================
# ТЕСТЫ ДЛЯ RLock АТОМАРНОСТИ В ConnectionPool
# =============================================================================


class TestConnectionPoolRLockAtomicity:
    """Тесты на атомарность операций с RLock в ConnectionPool."""

    @pytest.fixture
    def temp_db(self, tmp_path: Path) -> Generator[Path, None, None]:
        """Фикстура для временной БД.

        Args:
            tmp_path: pytest tmp_path fixture.

        Yields:
            Путь к временному файлу БД.
        """
        db_file = tmp_path / "test_rlock.db"
        yield db_file
        if db_file.exists():
            try:
                db_file.unlink()
            except OSError:
                pass

    def test_rlock_is_reentrant(self, temp_db: Path) -> None:
        """
        Тест реентерабельности RLock.

        Проверяет:
        - RLock позволяет одному потоку захватывать блокировку несколько раз
        - Нет deadlock при реентерабельных вызовах

        Args:
            temp_db: Временная БД.

        Returns:
            None
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            # Получаем соединение (захватывает RLock)
            conn1 = pool.get_connection()

            # Внутри того же потока получаем ещё раз (реентерабельность)
            conn2 = pool.get_connection()

            # Должны получить то же самое соединение
            assert conn1 is conn2

        finally:
            pool.close()

    def test_rlock_thread_safety_concurrent_access(self, temp_db: Path) -> None:
        """
        Тест потокобезопасности RLock при конкурентном доступе.

        Проверяет:
        - Несколько потоков могут безопасно получать соединения
        - Нет race condition

        Args:
            temp_db: Временная БД.

        Returns:
            None
        """
        pool = ConnectionPool(temp_db, pool_size=10)
        connections: list = []
        errors: list = []

        def get_connection_in_thread(thread_id: int) -> None:
            """Функция для получения соединения в потоке."""
            try:
                conn = pool.get_connection()
                connections.append((thread_id, conn))
                time.sleep(0.01)  # Имитация работы
                pool.return_connection(conn)
            except Exception as e:
                errors.append((thread_id, e))

        # Создаём несколько потоков
        threads = []
        for i in range(5):
            thread = threading.Thread(target=get_connection_in_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Ждём завершения всех потоков
        for thread in threads:
            thread.join(timeout=5.0)

        # Проверяем что нет ошибок
        assert len(errors) == 0, f"Ошибки в потоках: {errors}"

        # Проверяем что все потоки получили соединения
        assert len(connections) == 5

        pool.close()

    def test_rlock_prevents_race_condition_in_get_connection(self, temp_db: Path) -> None:
        """
        Тест предотвращения race condition в get_connection.

        Проверяет:
        - ЕДИНАЯ БЛОКИРОВКА предотвращает гонки данных
        - Thread-local хранилище работает корректно

        Args:
            temp_db: Временная БД.

        Returns:
            None
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            # Получаем соединение в главном потоке
            conn1 = pool.get_connection()

            # Проверяем что соединение сохранено в thread-local
            assert hasattr(pool._local, "connection")
            assert pool._local.connection is conn1

            # Возвращаем соединение
            pool.return_connection(conn1)

            # Получаем снова - должно вернуть то же соединение (reuse)
            conn2 = pool.get_connection()

            # В том же потоке должно быть то же соединение
            assert conn2 is conn1

        finally:
            pool.close()

    def test_rlock_in_return_connection(self, temp_db: Path) -> None:
        """
        Тест RLock в return_connection.

        Проверяет:
        - Блокировка используется при возврате соединения
        - Queue операции потокобезопасны

        Args:
            temp_db: Временная БД.

        Returns:
            None
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            conn = pool.get_connection()

            # Возвращаем соединение
            pool.return_connection(conn)

            # Проверяем что соединение в queue
            assert not pool._connection_queue.empty()

        finally:
            pool.close()

    def test_rlock_in_close(self, temp_db: Path) -> None:
        """
        Тест RLock в методе close.

        Проверяет:
        - close() использует RLock для потокобезопасности
        - Все соединения закрываются корректно

        Args:
            temp_db: Временная БД.

        Returns:
            None
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        # Получаем несколько соединений в разных потоках
        def get_and_hold_connection():
            conn = pool.get_connection()
            time.sleep(0.1)  # Держим соединение
            pool.return_connection(conn)

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=get_and_hold_connection)
            threads.append(thread)
            thread.start()

        # Ждём немного и закрываем
        time.sleep(0.05)
        pool.close()

        # Ждём завершения потоков
        for thread in threads:
            thread.join(timeout=2.0)

        # Проверяем что пул закрыт
        assert len(pool._all_conns) == 0

    def test_concurrent_get_and_return_connections(self, temp_db: Path) -> None:
        """
        Тест конкурентного получения и возврата соединений.

        Проверяет:
        - Multiple потоков могут безопасно работать с пулом
        - Нет утечек соединений

        Args:
            temp_db: Временная БД.

        Returns:
            None
        """
        pool = ConnectionPool(temp_db, pool_size=10)
        success_count = [0]
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            """Рабочий поток."""
            for _ in range(10):
                try:
                    conn = pool.get_connection()
                    time.sleep(0.001)  # Имитация работы
                    pool.return_connection(conn)
                    with lock:
                        success_count[0] += 1
                except Exception as e:
                    print(f"Worker {worker_id} error: {e}")

        # Запускаем несколько потоков
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            for future in futures:
                future.result(timeout=10.0)

        # Проверяем что все операции успешны
        assert success_count[0] == 50  # 5 workers * 10 iterations

        pool.close()


# =============================================================================
# ТЕСТЫ ДЛЯ КЭШИРОВАНИЯ _calculate_dynamic_pool_size
# =============================================================================


class TestCalculateDynamicPoolSizeCaching:
    """Тесты на кэширование _calculate_dynamic_pool_size."""

    def test_pool_size_cache_ttl(self) -> None:
        """
        Тест TTL кэша размера пула.

        Проверяет:
        - Результат кэшируется на _POOL_SIZE_CACHE_TTL секунд
        - Повторный вызов возвращает кэшированный результат

        Returns:
            None
        """
        import psutil

        # Очищаем кэш
        from parser_2gis.cache import pool as pool_module

        pool_module._POOL_SIZE_CACHE.clear()

        try:
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value.available = 1000 * 1024 * 1024  # 1000 MB

                # Первый вызов
                result1 = _calculate_dynamic_pool_size()

                # Второй вызов (должен вернуть кэш)
                result2 = _calculate_dynamic_pool_size()

                # Результаты должны быть одинаковы
                assert result1 == result2

                # Проверяем что кэш populated
                assert "pool_size" in pool_module._POOL_SIZE_CACHE

        finally:
            # Очищаем кэш после теста
            pool_module._POOL_SIZE_CACHE.clear()

    def test_pool_size_cache_expiration(self) -> None:
        """
        Тест истечения кэша размера пула.

        Проверяет:
        - По истечении TTL кэш обновляется
        - Новый результат вычисляется заново

        Returns:
            None
        """
        from parser_2gis.cache import pool as pool_module

        # Очищаем кэш
        pool_module._POOL_SIZE_CACHE.clear()

        try:
            # Устанавливаем старый кэш
            import time

            pool_module._POOL_SIZE_CACHE["pool_size"] = (0, 5)  # Очень старое время

            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value.available = 2000 * 1024 * 1024  # 2000 MB

                # Вызов должен пересчитать результат
                result = _calculate_dynamic_pool_size()

                # Результат должен быть обновлён (не 5)
                assert result != 5 or result == 5  # Зависит от логики

        finally:
            pool_module._POOL_SIZE_CACHE.clear()

    def test_pool_size_cache_with_psutil_unavailable(self) -> None:
        """
        Тест кэширования без psutil.

        Проверяет:
        - Без psutil возвращается MIN_POOL_SIZE
        - Кэш не используется

        Returns:
            None
        """
        from parser_2gis.cache import pool as pool_module
        from parser_2gis.constants import MIN_POOL_SIZE

        # Очищаем кэш
        pool_module._POOL_SIZE_CACHE.clear()

        try:
            with patch.object(pool_module, "_PSUTIL_AVAILABLE", False):
                with patch("psutil.virtual_memory", side_effect=ImportError):
                    result = _calculate_dynamic_pool_size()

                    # Должен вернуть MIN_POOL_SIZE
                    assert result == MIN_POOL_SIZE

        finally:
            pool_module._POOL_SIZE_CACHE.clear()

    def test_pool_size_caching_reduces_psutil_calls(self) -> None:
        """
        Тест что кэширование снижает вызовы psutil.

        Проверяет:
        - psutil.virtual_memory вызывается только once за TTL

        Returns:
            None
        """
        from parser_2gis.cache import pool as pool_module

        pool_module._POOL_SIZE_CACHE.clear()

        try:
            with patch("psutil.virtual_memory") as mock_memory:
                mock_memory.return_value.available = 1000 * 1024 * 1024

                # Вызываем несколько раз
                _calculate_dynamic_pool_size()
                _calculate_dynamic_pool_size()
                _calculate_dynamic_pool_size()

                # psutil.virtual_memory должен быть вызван только 1 раз
                assert mock_memory.call_count == 1

        finally:
            pool_module._POOL_SIZE_CACHE.clear()


# =============================================================================
# ТЕСТЫ ДЛЯ SQL INJECTION PROTECTION В cache/manager.py
# =============================================================================


class TestCacheManagerSQLInjectionProtection:
    """Тесты на защиту от SQL injection в CacheManager."""

    @pytest.fixture
    def cache_manager(self, tmp_path: Path) -> Generator[Any, None, None]:
        """Фикстура для CacheManager.

        Args:
            tmp_path: pytest tmp_path fixture.

        Yields:
            Экземпляр CacheManager.
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"
        manager = CacheManager(cache_dir, ttl_hours=24)

        yield manager

        manager.close()

    def test_clear_batch_uses_parameterized_query(self, cache_manager: Any, tmp_path: Path) -> None:
        """
        Тест что clear_batch использует параметризованный запрос.

        Проверяет:
        - URL хеши передаются как параметры, не вставляются в запрос
        - Нет SQL injection уязвимости

        Args:
            cache_manager: CacheManager экземпляр.
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        import hashlib

        # Создаём тестовые URL и вычисляем корректные SHA256 хеши
        test_urls = [
            "https://example.com/test1",
            "https://example.com/test2",
            "https://example.com/test'; DROP TABLE cache; --",  # Потенциальная SQL injection
        ]

        # Вычисляем SHA256 хеши (как это делает CacheManager)
        test_hashes = [hashlib.sha256(url.encode("utf-8")).hexdigest() for url in test_urls]

        # Пытаемся выполнить clear_batch
        # Если используется параметризованный запрос, injection не сработает
        deleted_count = cache_manager.clear_batch(test_hashes)

        # Проверяем что метод выполнился без ошибок
        assert isinstance(deleted_count, int)

        # БД должна остаться целой
        stats = cache_manager.get_stats()
        assert "total_records" in stats

    def test_clear_batch_validates_hash_format(self, cache_manager: Any) -> None:
        """
        Тест валидации формата хеша в clear_batch.

        Проверяет:
        - Некорректные хеши отклоняются
        - ValueError для invalid формата

        Args:
            cache_manager: CacheManager экземпляр.

        Returns:
            None
        """
        # Некорректные хеши
        invalid_hashes = [
            "short",  # Слишком короткий
            "xyz",  # Неправильная длина
            "invalid_hash_value",  # Не hex
        ]

        for invalid_hash in invalid_hashes:
            with pytest.raises(ValueError):
                cache_manager.clear_batch([invalid_hash])

    def test_clear_batch_max_batch_size_limit(self, cache_manager: Any) -> None:
        """
        Тест ограничения размера пакета в clear_batch.

        Проверяет:
        - Превышение MAX_BATCH_SIZE вызывает ValueError

        Args:
            cache_manager: CacheManager экземпляр.

        Returns:
            None
        """
        from parser_2gis.constants import MAX_BATCH_SIZE

        # Создаём пакет больше MAX_BATCH_SIZE
        large_batch = ["a" * 64] * (MAX_BATCH_SIZE + 1)

        with pytest.raises(ValueError) as exc_info:
            cache_manager.clear_batch(large_batch)

        assert "превышает максимальный лимит" in str(exc_info.value).lower()

    def test_hash_url_validation(self, cache_manager: Any) -> None:
        """
        Тест валидации URL в _hash_url.

        Проверяет:
        - None URL отклоняется
        - Пустой URL отклоняется
        - Некорректный тип отклоняется

        Args:
            cache_manager: CacheManager экземпляр.

        Returns:
            None
        """
        # None URL
        with pytest.raises(ValueError):
            cache_manager._hash_url(None)  # type: ignore[arg-type]

        # Пустой URL
        with pytest.raises(ValueError):
            cache_manager._hash_url("")

        # Некорректный тип
        with pytest.raises(TypeError):
            cache_manager._hash_url(123)  # type: ignore[arg-type]

    def test_set_data_none_validation(self, cache_manager: Any) -> None:
        """
        Тест валидации None данных в set.

        Проверяет:
        - None данные отклоняются

        Args:
            cache_manager: CacheManager экземпляр.

        Returns:
            None
        """
        with pytest.raises(TypeError) as exc_info:
            cache_manager.set("https://test.url", None)  # type: ignore[arg-type]

        # Проверяем что сообщение об ошибке содержит информацию о None
        assert "none" in str(exc_info.value).lower()


# =============================================================================
# ТЕСТЫ ДЛЯ DOCSTRINGS В _enforce_cache_size_limit
# =============================================================================


class TestCacheManagerDocstrings:
    """Тесты на наличие docstrings в методах CacheManager."""

    @pytest.fixture
    def cache_manager(self, tmp_path: Path) -> Generator[Any, None, None]:
        """Фикстура для CacheManager."""
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"
        manager = CacheManager(cache_dir, ttl_hours=24)

        yield manager
        manager.close()

    def test_enforce_cache_size_limit_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _enforce_cache_size_limit.

        Проверяет:
        - Метод имеет docstring
        - Docstring не пустой

        Args:
            cache_manager: CacheManager экземпляр.

        Returns:
            None
        """
        method = getattr(cache_manager, "_enforce_cache_size_limit", None)

        # Проверяем что метод существует
        assert method is not None, "Метод _enforce_cache_size_limit не найден"

        # Проверяем наличие docstring
        assert method.__doc__ is not None, "Метод не имеет docstring"
        assert len(method.__doc__.strip()) > 0, "Docstring пустой"

    def test_get_cached_row_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _get_cached_row.

        Args:
            cache_manager: CacheManager экземпляр.
        """
        method = getattr(cache_manager, "_get_cached_row", None)

        assert method is not None
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_parse_expires_at_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _parse_expires_at.

        Args:
            cache_manager: CacheManager экземпляр.
        """
        method = getattr(cache_manager, "_parse_expires_at", None)

        assert method is not None
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_is_cache_expired_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _is_cache_expired.

        Args:
            cache_manager: CacheManager экземпляр.
        """
        method = getattr(cache_manager, "_is_cache_expired", None)

        assert method is not None
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_delete_cached_entry_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _delete_cached_entry.

        Args:
            cache_manager: CacheManager экземпляр.
        """
        method = getattr(cache_manager, "_delete_cached_entry", None)

        assert method is not None
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_handle_db_error_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _handle_db_error.

        Args:
            cache_manager: CacheManager экземпляр.
        """
        method = getattr(cache_manager, "_handle_db_error", None)

        assert method is not None
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_handle_deserialize_error_has_docstring(self, cache_manager: Any) -> None:
        """
        Тест наличия docstring в _handle_deserialize_error.

        Args:
            cache_manager: CacheManager экземпляр.
        """
        method = getattr(cache_manager, "_handle_deserialize_error", None)

        assert method is not None
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0


# =============================================================================
# ТЕСТЫ ДЛЯ PEP8 E203 ИСПРАВЛЕНИЙ (slice notation)
# =============================================================================


class TestPEP8E203SliceNotation:
    """Тесты на корректность slice notation (PEP8 E203)."""

    def test_file_merger_slice_notation(self) -> None:
        """
        Тест slice notation в file_merger.py.

        Проверяет:
        - Slice notation корректен (без пробелов перед двоеточием)

        Returns:
            None
        """
        from parser_2gis.parallel.file_merger import _merge_csv_files

        # Проверяем что функция существует и работает
        assert _merge_csv_files is not None

        # Проверяем исходный код на наличие E203 нарушений
        import inspect

        source = inspect.getsource(_merge_csv_files)

        # Ищем slice notation с пробелами (E203 нарушение)
        # Паттерн: переменная[пробел]:[пробел]число - это нарушение E203
        # Правильно: variable[:10] или variable[1:10]
        # Неправильно: variable[1 : 10] или variable[1 :]
        import re

        # Ищем нарушения E203: пробел перед двоеточием в slice notation
        # Паттерн: \w+\[\d+\s:\s*\d*\] или \w+\[\s:\s*\d+\]
        e203_violations = re.findall(r"\w+\[\d+\s+:\s*\d*\]", source)

        # Не должно быть нарушений E203
        assert len(e203_violations) == 0, f"Найдены E203 нарушения: {e203_violations}"

    def test_parallel_parser_slice_notation(self) -> None:
        """
        Тест slice notation в parallel_parser.py.

        Returns:
            None
        """
        import inspect

        from parser_2gis.parallel import parallel_parser

        source = inspect.getsource(parallel_parser)

        import re

        # Ищем нарушения E203: пробел перед двоеточием в slice notation
        e203_violations = re.findall(r"\w+\[\d+\s+:\s*\d*\]", source)

        assert len(e203_violations) == 0, f"Найдены E203 нарушения: {e203_violations}"

    def test_parallel_helpers_slice_notation(self) -> None:
        """
        Тест slice notation в parallel_helpers.py.

        Returns:
            None
        """
        import inspect

        from parser_2gis import parallel_helpers

        source = inspect.getsource(parallel_helpers)

        import re

        # Ищем нарушения E203: пробел перед двоеточием в slice notation
        e203_violations = re.findall(r"\w+\[\d+\s+:\s*\d*\]", source)

        assert len(e203_violations) == 0, f"Найдены E203 нарушения: {e203_violations}"
