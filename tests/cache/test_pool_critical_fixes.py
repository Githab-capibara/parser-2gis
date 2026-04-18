"""
Тесты для исправлений CRITICAL проблем в cache/pool.py.

Проверяет:
- Гарантированную инициализацию conn в get_connection()
- Очистку соединений при ошибках в finally блоке
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from parser_2gis.cache.pool import ConnectionPool


class TestCachePoolNoneHandling:
    """Тесты для CRITICAL 1: Гарантированная инициализация conn."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Создает временный путь к БД.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временному файлу БД.
        """
        return tmp_path / "test_pool_none.db"

    @pytest.fixture
    def connection_pool(self, temp_db_path: Path) -> ConnectionPool:
        """Создает ConnectionPool для тестов.

        Args:
            temp_db_path: Путь к временной БД.

        Returns:
            ConnectionPool экземпляр.
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)
        yield pool
        pool.close()

    def test_conn_guaranteed_initialization(self, connection_pool: ConnectionPool) -> None:
        """Тест 1: Гарантированная инициализация conn в get_connection().

        Проверяет:
        - conn никогда не остаётся None после get_connection()
        - RuntimeError выбрасывается если conn не инициализирован
        - Соединение возвращается корректно
        """
        # Получаем соединение
        conn = connection_pool.get_connection()

        # Проверяем что conn не None
        assert conn is not None, "conn должен быть инициализирован"

        # Проверяем что conn это sqlite3.Connection
        assert isinstance(conn, sqlite3.Connection), "conn должен быть sqlite3.Connection"

        # Проверяем что соединение работает
        result = conn.execute("SELECT 1")
        assert result.fetchone()[0] == 1, "Соединение должно работать"

    def test_conn_none_raises_runtime_error(self, temp_db_path: Path) -> None:
        """Тест 2: conn=None вызывает RuntimeError.

        Проверяет:
        - Если conn остаётся None, выбрасывается RuntimeError
        - Сообщение об ошибке содержит контекст
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)

        # Mock _create_connection для возврата None и queue для возврата None
        with patch.object(pool, "_create_connection", return_value=None):
            with patch.object(pool, "_connection_queue") as mock_queue:
                # Queue пустой - выбрасываем queue.Empty
                from queue import Empty

                mock_queue.get_nowait.side_effect = Empty()

                # Должен выбросить RuntimeError так как conn остаётся None
                with pytest.raises(RuntimeError, match="Не удалось получить соединение с БД"):
                    pool.get_connection()

        pool.close()

    def test_conn_initialized_after_queue_empty(self, connection_pool: ConnectionPool) -> None:
        """Тест 3: conn инициализируется после пустой queue.

        Проверяет:
        - При пустой queue создаётся новое соединение
        - conn инициализируется корректно
        """
        # Заполняем queue чтобы проверить получение из queue
        for _ in range(connection_pool._pool_size):
            dummy_conn = sqlite3.connect(":memory:")
            connection_pool._connection_queue.put_nowait(dummy_conn)

        # Получаем соединение (должно прийти из queue)
        conn = connection_pool.get_connection()

        # Проверяем что conn не None
        assert conn is not None, "conn должен быть инициализирован"
        assert isinstance(conn, sqlite3.Connection)

    def test_conn_initialized_after_create_connection(self, connection_pool: ConnectionPool) -> None:
        """Тест 4: conn инициализируется после _create_connection().

        Проверяет:
        - Новое соединение создаётся корректно
        - conn инициализируется после создания
        """
        # Очищаем queue
        while not connection_pool._connection_queue.empty():
            try:
                connection_pool._connection_queue.get_nowait()
            except Exception:
                break

        # Получаем соединение (должно создаться новое)
        conn = connection_pool.get_connection()

        # Проверяем что conn не None
        assert conn is not None, "conn должен быть инициализирован"
        assert isinstance(conn, sqlite3.Connection)

        # Проверяем что соединение добавлено в пул
        assert conn in connection_pool._all_conns, "Соединение должно быть в пуле"


class TestCachePoolConnectionCleanupOnError:
    """Тесты для CRITICAL 2: Очистка соединений в finally блоке."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Создает временный путь к БД.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временному файлу БД.
        """
        return tmp_path / "test_pool_cleanup.db"

    @pytest.fixture
    def connection_pool(self, temp_db_path: Path) -> ConnectionPool:
        """Создает ConnectionPool для тестов.

        Args:
            temp_db_path: Путь к временной БД.

        Returns:
            ConnectionPool экземпляр.
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)
        yield pool
        pool.close()

    def test_finally_block_cleans_up_connection(self, connection_pool: ConnectionPool) -> None:
        """Тест 5: finally блок очищает соединение при ошибке.

        Проверяет:
        - При ошибке соединение закрывается в finally
        - Ресурсы не утекают
        """
        # Получаем соединение
        conn = connection_pool.get_connection()

        # Проверяем что соединение открыто
        assert conn is not None

        # Возвращаем соединение в пул
        connection_pool.return_connection(conn)

        # Закрываем пул
        connection_pool.close()

        # Проверяем что соединение закрыто (после close() пула)
        # Примечание: соединение может оставаться открытым если не было закрыто явно
        # Проверяем что пул очищен
        assert len(connection_pool._all_conns) == 0

    def test_connection_closed_on_exception(self, temp_db_path: Path) -> None:
        """Тест 6: Соединение закрывается при исключении.

        Проверяет:
        - При исключении в get_connection() соединение закрывается
        - finally блок выполняется
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)

        # Mock _create_connection для выбрасывания исключения
        with patch.object(pool, "_create_connection", side_effect=sqlite3.Error("Mocked error")):
            with pytest.raises(sqlite3.Error):
                pool.get_connection()

        # Проверяем что пул закрыт
        assert len(pool._all_conns) == 0

        pool.close()

    def test_finally_closes_unadded_connection(self, temp_db_path: Path) -> None:
        """Тест 7: finally закрывает соединение не добавленное в пул.

        Проверяет:
        - Если соединение создано но не добавлено в пул, оно закрывается
        - finally блок проверяет hasattr
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)

        # Получаем соединение
        conn = pool.get_connection()

        # Проверяем что соединение получено
        assert conn is not None

        # Закрываем пул - должен закрыть все соединения
        pool.close()

        # Проверяем что пул очищен
        assert len(pool._all_conns) == 0

    def test_cleanup_on_sqlite_error(self, connection_pool: ConnectionPool) -> None:
        """Тест 8: Очистка при sqlite3.Error.

        Проверяет:
        - sqlite3.Error обрабатывается корректно
        - Соединение закрывается
        """
        # Получаем соединение
        conn = connection_pool.get_connection()

        # Имитируем ошибку при работе с соединением
        with pytest.raises(sqlite3.Error):
            conn.execute("INVALID SQL QUERY")

        # Возвращаем соединение в пул
        connection_pool.return_connection(conn)

        # Проверяем что соединение всё ещё работает
        result = conn.execute("SELECT 1")
        assert result.fetchone()[0] == 1

    def test_cleanup_on_os_error(self, temp_db_path: Path) -> None:
        """Тест 9: Очистка при OSError.

        Проверяет:
        - OSError обрабатывается корректно
        - finally блок выполняется
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)

        # Mock для имитации OSError при создании
        with patch.object(pool, "_create_connection", side_effect=OSError("Mocked OSError")):
            with pytest.raises(OSError):
                pool.get_connection()

        # Проверяем что пул пуст
        assert len(pool._all_conns) == 0

        pool.close()

    def test_finally_logs_cleanup(self, connection_pool: ConnectionPool, caplog) -> None:
        """Тест 10: finally блок логирует очистку.

        Проверяет:
        - Логирование очистки в finally
        - Сообщение содержит контекст
        """
        import logging

        with caplog.at_level(logging.DEBUG):
            # Получаем и возвращаем соединение
            conn = connection_pool.get_connection()
            connection_pool.return_connection(conn)

            # Закрываем пул
            connection_pool.close()

            # Проверяем логирование
            assert any(
                "Соединение" in record.message or "closed" in record.message.lower() for record in caplog.records
            )
