"""
Тесты для проверки потокобезопасности Connection Pool.

ИСПРАВЛЕНИЕ P0-3: Исправление race condition в _ConnectionPool
Файлы: parser_2gis/cache.py

Тестируют:
- Double-checked locking
- Потокобезопасность
- Конкурентный доступ к соединениям
"""

import os
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, List
from unittest.mock import patch

import pytest

from parser_2gis.cache import _ConnectionPool

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestConnectionPoolThreadSafety:
    """Тесты для потокобезопасности Connection Pool."""

    def test_connection_pool_single_thread(self, tmp_path: Path) -> None:
        """Тест работы connection pool в одном потоке."""
        cache_dir = tmp_path / "cache_single"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)

        # Получаем соединение
        conn1 = pool.get_connection()
        assert conn1 is not None

        # Проверяем, что это sqlite3.Connection
        assert isinstance(conn1, sqlite3.Connection)

        # Возвращаем соединение
        pool.return_connection(conn1)

        # Закрываем пул
        pool.close_all()

    def test_connection_pool_multiple_threads(self, tmp_path: Path) -> None:
        """Тест работы connection pool в нескольких потоках."""
        cache_dir = tmp_path / "cache_multi"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=10)
        connections: List[sqlite3.Connection] = []
        lock = threading.Lock()

        def get_connection_worker() -> None:
            """Работник для получения соединения."""
            conn = pool.get_connection()
            with lock:
                connections.append(conn)
            time.sleep(0.01)  # Имитация работы
            pool.return_connection(conn)

        # Запускаем 10 потоков
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_connection_worker)
            threads.append(thread)
            thread.start()

        # Ждём завершения всех потоков
        for thread in threads:
            thread.join()

        # Проверяем, что все соединения получены
        assert len(connections) == 10

        # Закрываем пул
        pool.close_all()

    def test_connection_pool_concurrent_access(self, tmp_path: Path) -> None:
        """Тест конкурентного доступа к connection pool."""
        cache_dir = tmp_path / "cache_concurrent"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)
        results: List[Any] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            """Работник для конкурентного доступа."""
            try:
                conn = pool.get_connection()
                # Выполняем простую операцию
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                with lock:
                    results.append((worker_id, result))
                pool.return_connection(conn)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Запускаем 20 работников с ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for future in futures:
                future.result()

        # Проверяем результаты
        assert len(errors) == 0, f"Ошибки: {errors}"
        assert len(results) == 20

        # Все результаты должны быть [(1,)]
        for worker_id, result in results:
            assert result == (1,), f"Работник {worker_id} получил неверный результат"

        # Закрываем пул
        pool.close_all()


class TestConnectionPoolDoubleCheckedLocking:
    """Тесты для double-checked locking."""

    def test_double_checked_locking_simulation(self, tmp_path: Path) -> None:
        """Тест симуляции double-checked locking."""
        cache_dir = tmp_path / "cache_dcl"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)

        # Получаем первое соединение
        conn1 = pool.get_connection()
        assert conn1 is not None

        # Получаем второе соединение (должно быть тем же самым в том же потоке)
        conn2 = pool.get_connection()

        # В том же потоке должно вернуться то же соединение
        # (благодаря threading.local())
        assert conn1 is conn2

        # Возвращаем соединение
        pool.return_connection(conn1)

        # Закрываем пул
        pool.close_all()

    def test_double_check_after_lock(self, tmp_path: Path) -> None:
        """Тест двойной проверки после блокировки."""
        cache_dir = tmp_path / "cache_double_check"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)
        created_connections: List[sqlite3.Connection] = []
        original_create = pool._create_connection

        def mock_create_connection() -> sqlite3.Connection:
            """Mock для отслеживания создания соединений."""
            conn = original_create()
            created_connections.append(conn)
            return conn

        with patch.object(pool, "_create_connection", side_effect=mock_create_connection):
            # Запускаем несколько потоков одновременно
            def worker() -> sqlite3.Connection:
                return pool.get_connection()

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker) for _ in range(10)]
                [f.result() for f in futures]

            # Проверяем, что соединения были созданы
            assert len(created_connections) > 0
            # Но не больше чем max_size
            assert len(created_connections) <= pool._max_size

        # Закрываем пул
        pool.close_all()


class TestConnectionPoolConcurrentAccess:
    """Тесты для конкурентного доступа."""

    def test_pool_size_limit(self, tmp_path: Path) -> None:
        """Тест ограничения размера пула."""
        cache_dir = tmp_path / "cache_limit"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=3)
        active_connections: List[sqlite3.Connection] = []
        lock = threading.Lock()
        max_observed = 0

        def worker() -> None:
            """Работник для проверки ограничения размера."""
            nonlocal max_observed
            conn = pool.get_connection()
            with lock:
                active_connections.append(conn)
                max_observed = max(max_observed, len(active_connections))
            time.sleep(0.05)  # Имитация работы
            with lock:
                active_connections.remove(conn)
            pool.return_connection(conn)

        # Запускаем 10 работников
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for future in futures:
                future.result()

        # Максимальное количество активных соединений не должно превышать max_size
        assert max_observed <= pool._max_size

        # Закрываем пул
        pool.close_all()

    def test_pool_reuse_connections(self, tmp_path: Path) -> None:
        """Тест повторного использования соединений."""
        cache_dir = tmp_path / "cache_reuse"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)
        all_connections: List[sqlite3.Connection] = []

        # Получаем и возвращаем соединения несколько раз
        for i in range(10):
            conn = pool.get_connection()
            all_connections.append(conn)
            pool.return_connection(conn)

        # Проверяем, что соединения переиспользовались
        # (должно быть меньше уникальных соединений чем запросов)
        unique_connections = set(id(conn) for conn in all_connections)
        assert len(unique_connections) <= pool._max_size

        # Закрываем пул
        pool.close_all()


class TestConnectionPoolEdgeCases:
    """Тесты для граничных случаев."""

    def test_pool_zero_max_size(self, tmp_path: Path) -> None:
        """Тест пула с pool_size=0."""
        cache_dir = tmp_path / "cache_zero"
        cache_dir.mkdir()

        # Должен использоваться дефолтный размер
        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=0)

        conn = pool.get_connection()
        assert conn is not None

        pool.return_connection(conn)
        pool.close_all()

    def test_pool_large_max_size(self, tmp_path: Path) -> None:
        """Тест пула с большим max_size."""
        cache_dir = tmp_path / "cache_large"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=100)

        # Получаем несколько соединений
        connections = []
        for i in range(10):
            conn = pool.get_connection()
            connections.append(conn)

        assert len(connections) == 10

        # Возвращаем соединения
        for conn in connections:
            pool.return_connection(conn)

        pool.close_all()

    def test_pool_rapid_acquire_release(self, tmp_path: Path) -> None:
        """Тест быстрого получения/возврата соединений."""
        cache_dir = tmp_path / "cache_rapid"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)

        # Быстрое получение и возврат
        for i in range(100):
            conn = pool.get_connection()
            pool.return_connection(conn)

        # Закрываем пул
        pool.close_all()


class TestConnectionPoolStress:
    """Стресс-тесты для Connection Pool."""

    def test_pool_stress_test(self, tmp_path: Path) -> None:
        """Стресс-тест connection pool."""
        cache_dir = tmp_path / "cache_stress"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=2, use_dynamic=False)

        # Выполняем несколько операций
        for i in range(5):
            conn = pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ?", (i,))
            assert cursor.fetchone() == (i,)
            pool.return_connection(conn)

        # Закрываем пул
        pool.close_all()


class TestConnectionPoolCleanup:
    """Тесты для очистки Connection Pool."""

    def test_pool_close_cleanup(self, tmp_path: Path) -> None:
        """Тест очистки при закрытии пула."""
        cache_dir = tmp_path / "cache_cleanup"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)

        # Получаем несколько соединений
        connections = []
        for i in range(5):
            conn = pool.get_connection()
            connections.append(conn)

        # Закрываем пул (должен закрыть все соединения)
        pool.close_all()

        # Проверяем, что соединения закрыты
        for conn in connections:
            # Попытка выполнить операцию на закрытом соединении
            # должна вызвать исключение
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_pool_return_closed_connection(self, tmp_path: Path) -> None:
        """Тест возврата закрытого соединения."""
        cache_dir = tmp_path / "cache_return_closed"
        cache_dir.mkdir()

        pool = _ConnectionPool(cache_dir / "cache.db", pool_size=5)

        conn = pool.get_connection()
        conn.close()  # Закрываем соединение

        # Возвращаем закрытое соединение
        pool.return_connection(conn)

        # Получаем новое соединение (должно работать)
        new_conn = pool.get_connection()
        assert new_conn is not None

        pool.close_all()
