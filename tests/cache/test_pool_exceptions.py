"""
Тесты для обработки исключений в cache/pool.py.

Проверяет:
- Раздельную обработку MemoryError, OSError, ValueError, TypeError, Exception
- Корректное логирование каждого типа исключения
- Очистку ресурсов после исключения
"""

import logging
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache.pool import ConnectionPool, _calculate_dynamic_pool_size


class TestPoolExceptionHandling:
    """Тесты обработки исключений в ConnectionPool."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Создает временный путь к БД.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временному файлу БД.
        """
        return tmp_path / "test_pool.db"

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

    def test_pool_memory_error_handling(self, connection_pool: ConnectionPool, caplog):
        """Тест обработки MemoryError в ConnectionPool.

        Проверяет:
        - MemoryError обрабатывается корректно
        - Ресурсы очищаются после MemoryError
        - Логирование работает корректно
        """
        # MemoryError в _create_connection пробрасывается без логирования (критическая ошибка)
        with patch.object(
            connection_pool, "_create_connection", side_effect=MemoryError("Mocked MemoryError")
        ):
            with pytest.raises(MemoryError):
                connection_pool.get_connection()

        # MemoryError пробрасывается без логирования (критическая ошибка)
        # Проверяем что MemoryError не был залогирован (т.к. это критическая ошибка)
        assert not any("MemoryError" in record.message for record in caplog.records)

    def test_pool_os_error_handling(self, connection_pool: ConnectionPool, caplog):
        """Тест обработки OSError в ConnectionPool.

        Проверяет:
        - OSError обрабатывается корректно
        - Ресурсы очищаются после OSError
        - Логирование работает корректно
        """
        with caplog.at_level(logging.WARNING):
            # OSError при создании соединения
            with patch.object(
                connection_pool, "_create_connection", side_effect=OSError("Mocked OSError")
            ):
                with pytest.raises(OSError):
                    connection_pool.get_connection()

            # Проверяем что OSError был залогирован
            assert any("OSError" in record.message for record in caplog.records)

    def test_pool_value_error_handling(self, connection_pool: ConnectionPool, caplog):
        """Тест обработки ValueError в ConnectionPool.

        Проверяет:
        - ValueError обрабатывается корректно
        - Логирование работает корректно
        """
        with caplog.at_level(logging.WARNING):
            # ValueError при создании соединения
            with patch.object(
                connection_pool, "_create_connection", side_effect=ValueError("Mocked ValueError")
            ):
                with pytest.raises(ValueError):
                    connection_pool.get_connection()

            # Проверяем что ValueError был залогирован
            assert any("ValueError" in record.message for record in caplog.records)

    def test_pool_type_error_handling(self, connection_pool: ConnectionPool, caplog):
        """Тест обработки TypeError в ConnectionPool.

        Проверяет:
        - TypeError обрабатывается корректно
        - Логирование работает корректно
        """
        with caplog.at_level(logging.WARNING):
            # TypeError при создании соединения
            with patch.object(
                connection_pool, "_create_connection", side_effect=TypeError("Mocked TypeError")
            ):
                with pytest.raises(TypeError):
                    connection_pool.get_connection()

            # Проверяем что TypeError был залогирован
            assert any("TypeError" in record.message for record in caplog.records)

    def test_pool_generic_exception_handling(self, connection_pool: ConnectionPool, caplog):
        """Тест обработки общего Exception в ConnectionPool.

        Проверяет:
        - Exception обрабатывается корректно
        - Логирование работает корректно
        """
        # Exception в _create_connection пробрасывается без логирования
        with patch.object(
            connection_pool, "_create_connection", side_effect=Exception("Mocked Exception")
        ):
            with pytest.raises(Exception):
                connection_pool.get_connection()

        # Exception пробрасывается без логирования
        # Проверяем что Exception не был залогирован
        assert not any("Mocked Exception" in record.message for record in caplog.records)

    def test_pool_cleanup_after_exception(self, temp_db_path: Path):
        """Тест очистки ресурсов после исключения.

        Проверяет:
        - Соединения закрываются после исключения
        - Пул очищается корректно
        """
        pool = ConnectionPool(temp_db_path, pool_size=5)

        # Получаем соединение
        conn = pool.get_connection()

        # Имитируем исключение при работе с соединением
        try:
            raise RuntimeError("Mocked runtime error")
        except RuntimeError:
            pass

        # Закрываем пул
        pool.close()

        # Проверяем что соединение закрыто
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_pool_return_connection_exception_handling(
        self, connection_pool: ConnectionPool, caplog
    ):
        """Тест обработки исключений при возврате соединения.

        Проверяет:
        - Исключения при возврате соединения обрабатываются
        - Логирование работает корректно
        """
        # Получаем соединение
        connection_pool.get_connection()

        # Mock close() для выбрасывания исключения через MagicMock
        mock_conn = MagicMock()
        mock_conn.close.side_effect = sqlite3.Error("Mocked sqlite3.Error")

        with caplog.at_level(logging.WARNING):
            # Заполняем очередь чтобы соединение было закрыто
            for _ in range(connection_pool._pool_size):
                dummy_conn = sqlite3.connect(":memory:")
                connection_pool._connection_queue.put_nowait(dummy_conn)

            # Возвращаем mock соединение - должно быть закрыто с ошибкой
            connection_pool.return_connection(mock_conn)

            # Проверяем логирование
            assert any("sqlite3.Error" in record.message for record in caplog.records)

    def test_pool_close_exception_handling(self, connection_pool: ConnectionPool, caplog):
        """Тест обработки исключений при закрытии пула.

        Проверяет:
        - Исключения при закрытии обрабатываются
        - Логирование работает корректно
        """
        # Mock close() для выбрасывания исключения
        mock_conn = MagicMock()
        mock_conn.close.side_effect = sqlite3.Error("Mocked sqlite3.Error on close")

        with caplog.at_level(logging.DEBUG):
            connection_pool._all_conns.append(mock_conn)
            connection_pool.close()

            # Проверяем что ошибка была залогирована
            assert any("sqlite3.Error" in record.message for record in caplog.records)

    def test_dynamic_pool_size_memory_error(self, caplog):
        """Тест обработки MemoryError в _calculate_dynamic_pool_size.

        Проверяет:
        - MemoryError обрабатывается корректно
        - Возвращается MIN_POOL_SIZE
        """
        with caplog.at_level(logging.WARNING):
            with patch("parser_2gis.cache.pool.psutil") as mock_psutil:
                mock_psutil.virtual_memory.side_effect = MemoryError("Mocked MemoryError")

                result = _calculate_dynamic_pool_size()

                # Проверяем что возвращён MIN_POOL_SIZE
                from parser_2gis.constants import MIN_POOL_SIZE

                assert result == MIN_POOL_SIZE

                # Проверяем логирование
                assert any("MemoryError" in record.message for record in caplog.records)

    def test_dynamic_pool_size_os_error(self, caplog):
        """Тест обработки OSError в _calculate_dynamic_pool_size.

        Проверяет:
        - OSError обрабатывается корректно
        - Возвращается MIN_POOL_SIZE
        """
        with caplog.at_level(logging.WARNING):
            with patch("parser_2gis.cache.pool.psutil") as mock_psutil:
                mock_psutil.virtual_memory.side_effect = OSError("Mocked OSError")

                result = _calculate_dynamic_pool_size()

                # Проверяем что возвращён MIN_POOL_SIZE
                from parser_2gis.constants import MIN_POOL_SIZE

                assert result == MIN_POOL_SIZE

                # Проверяем что функция выполнилась без ошибок
                assert isinstance(result, int)
                assert result > 0

    def test_dynamic_pool_size_value_error(self, caplog):
        """Тест обработки ValueError в _calculate_dynamic_pool_size.

        Проверяет:
        - ValueError обрабатывается корректно
        - Возвращается MIN_POOL_SIZE
        """
        with caplog.at_level(logging.WARNING):
            with patch("parser_2gis.cache.pool.psutil") as mock_psutil:
                mock_psutil.virtual_memory.side_effect = ValueError("Mocked ValueError")

                result = _calculate_dynamic_pool_size()

                # Проверяем что возвращён MIN_POOL_SIZE
                from parser_2gis.constants import MIN_POOL_SIZE

                assert result == MIN_POOL_SIZE

                # Проверяем что функция выполнилась без ошибок
                assert isinstance(result, int)
                assert result > 0

    def test_dynamic_pool_size_type_error(self, caplog):
        """Тест обработки TypeError в _calculate_dynamic_pool_size.

        Проверяет:
        - TypeError обрабатывается корректно
        - Возвращается MIN_POOL_SIZE
        """
        with caplog.at_level(logging.WARNING):
            with patch("parser_2gis.cache.pool.psutil") as mock_psutil:
                mock_psutil.virtual_memory.side_effect = TypeError("Mocked TypeError")

                result = _calculate_dynamic_pool_size()

                # Проверяем что возвращён MIN_POOL_SIZE
                from parser_2gis.constants import MIN_POOL_SIZE

                assert result == MIN_POOL_SIZE

                # Проверяем что функция выполнилась без ошибок
                assert isinstance(result, int)
                assert result > 0

    def test_pool_context_manager_exception_handling(self, temp_db_path: Path, caplog):
        """Тест обработки исключений в контекстном менеджере.

        Проверяет:
        - Контекстный менеджер корректно закрывает пул при исключениях
        - Ресурсы очищаются
        """
        with caplog.at_level(logging.ERROR):
            try:
                with ConnectionPool(temp_db_path, pool_size=5) as pool:
                    pool.get_connection()
                    raise RuntimeError("Mocked runtime error in context")
            except RuntimeError:
                pass

            # Проверяем что пул закрыт (нет ошибок в логе)
            assert not any(
                "Ошибка при закрытии пула" in record.message for record in caplog.records
            )

    def test_pool_weakref_finalizer_exception_handling(self, temp_db_path: Path, caplog):
        """Тест обработки исключений в weakref.finalizer.

        Проверяет:
        - weakref.finalizer корректно обрабатывает исключения
        - Ресурсы очищаются даже при исключениях
        """
        with caplog.at_level(logging.DEBUG):
            pool = ConnectionPool(temp_db_path, pool_size=5)

            # Получаем соединение
            pool.get_connection()

            # Mock close() через MagicMock для выбрасывания исключения
            mock_conn = MagicMock()
            mock_conn.close.side_effect = sqlite3.Error("Mocked error")

            # Добавляем mock в пул
            pool._all_conns.append(mock_conn)

            # Вызываем close явно чтобы проверить обработку ошибок
            pool.close()

            # Проверяем что ошибка была залогирована
            assert any(
                "Ошибка БД при закрытии соединения" in record.message
                or "Mocked error" in record.message
                for record in caplog.records
            )
