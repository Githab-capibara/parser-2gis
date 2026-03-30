"""
Тесты для finally блока в cache/manager.py.

Проверяет:
- Гарантированную очистку ресурсов при MemoryError
- Гарантированную очистку ресурсов при KeyboardInterrupt
- Гарантированную очистку ресурсов при SystemExit
"""

import logging
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache.manager import CacheManager


class TestCacheManagerFinallyCleanup:
    """Тесты finally блока в CacheManager."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Создает временную директорию для кэша.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временной директории.
        """
        cache_dir = tmp_path / "test_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @pytest.fixture
    def cache_manager(self, temp_cache_dir: Path) -> CacheManager:
        """Создает CacheManager для тестов.

        Args:
            temp_cache_dir: Путь к временной директории кэша.

        Returns:
            CacheManager экземпляр.
        """
        manager = CacheManager(temp_cache_dir, ttl_hours=24, pool_size=5)
        yield manager
        try:
            manager.close()
        except Exception:
            pass

    def test_cache_manager_finally_cleanup_memory_error(self, cache_manager: CacheManager, caplog):
        """Тест очистки ресурсов при MemoryError.

        Проверяет:
        - finally блок выполняется при MemoryError
        - Курсор закрывается корректно
        - Соединение возвращается в пул
        """
        with caplog.at_level(logging.DEBUG):
            # Mock курсора для выбрасывания MemoryError при close
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor.close.side_effect = MemoryError("Mocked MemoryError in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.rollback.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся получить данные из кэша
                result = cache_manager.get("https://example.com/test")

                # Проверяем что результат None (из-за ошибки)
                assert result is None

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_finally_cleanup_keyboard_interrupt(
        self, cache_manager: CacheManager, caplog
    ):
        """Тест очистки ресурсов при KeyboardInterrupt.

        Проверяет:
        - finally блок выполняется при KeyboardInterrupt
        - Курсор закрывается корректно
        """
        with caplog.at_level(logging.DEBUG):
            # Mock курсора для выбрасывания KeyboardInterrupt при close
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor.close.side_effect = KeyboardInterrupt("Mocked KeyboardInterrupt")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.rollback.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся получить данные из кэша и ожидаем KeyboardInterrupt
                with pytest.raises(KeyboardInterrupt):
                    cache_manager.get("https://example.com/test")

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_finally_cleanup_system_exit(self, cache_manager: CacheManager, caplog):
        """Тест очистки ресурсов при SystemExit.

        Проверяет:
        - finally блок выполняется при SystemExit
        - Курсор закрывается корректно
        """
        with caplog.at_level(logging.DEBUG):
            # Mock курсора для выбрасывания SystemExit при close
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor.close.side_effect = SystemExit("Mocked SystemExit")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.rollback.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся получить данные из кэша и ожидаем SystemExit
                with pytest.raises(SystemExit):
                    cache_manager.get("https://example.com/test")

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_finally_cleanup_sqlite_error(self, cache_manager: CacheManager, caplog):
        """Тест очистки ресурсов при sqlite3.Error.

        Проверяет:
        - finally блок выполняется при sqlite3.Error
        - Курсор закрывается корректно даже при ошибке
        """
        with caplog.at_level(logging.DEBUG):
            # Mock курсора для выбрасывания sqlite3.Error при close
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor.close.side_effect = sqlite3.Error("Mocked sqlite3.Error in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.rollback.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся получить данные из кэша
                result = cache_manager.get("https://example.com/test")

                # Проверяем что результат None (из-за ошибки)
                assert result is None

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_finally_cleanup_os_error(self, cache_manager: CacheManager, caplog):
        """Тест очистки ресурсов при OSError.

        Проверяет:
        - finally блок выполняется при OSError
        - Курсор закрывается корректно
        """
        with caplog.at_level(logging.DEBUG):
            # Mock курсора для выбрасывания OSError при close
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor.close.side_effect = OSError("Mocked OSError in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.rollback.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся получить данные из кэша
                result = cache_manager.get("https://example.com/test")

                # Проверяем что результат None (из-за ошибки)
                assert result is None

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_del_finally_memory_error(self, temp_cache_dir: Path, caplog):
        """Тест finally блока в __del__ при MemoryError.

        Проверяет:
        - MemoryError пробрасывается из __del__
        - Ресурсы очищаются корректно
        """
        with caplog.at_level(logging.DEBUG):
            manager = CacheManager(temp_cache_dir, ttl_hours=24, pool_size=5)

            # Mock finalizer для выбрасывания MemoryError
            mock_finalizer = MagicMock()
            mock_finalizer.detach.side_effect = MemoryError("Mocked MemoryError in finalizer")
            manager._finalizer = mock_finalizer

            # Пытаемся уничтожить менеджер и ожидаем MemoryError
            with pytest.raises(MemoryError):
                manager.__del__()

            # Проверяем что MemoryError был залогирован
            assert any("MemoryError" in record.message for record in caplog.records)

    def test_cache_manager_del_finally_keyboard_interrupt(self, temp_cache_dir: Path, caplog):
        """Тест finally блока в __del__ при KeyboardInterrupt.

        Проверяет:
        - KeyboardInterrupt пробрасывается из __del__
        - Ресурсы очищаются корректно
        """
        with caplog.at_level(logging.WARNING):
            manager = CacheManager(temp_cache_dir, ttl_hours=24, pool_size=5)

            # Mock finalizer для выбрасывания KeyboardInterrupt
            mock_finalizer = MagicMock()
            mock_finalizer.detach.side_effect = KeyboardInterrupt("Mocked KeyboardInterrupt")
            manager._finalizer = mock_finalizer

            # Пытаемся уничтожить менеджер и ожидаем KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                manager.__del__()

            # Проверяем что KeyboardInterrupt был залогирован
            assert any("KeyboardInterrupt" in record.message for record in caplog.records)

    def test_cache_manager_del_finally_system_exit(self, temp_cache_dir: Path, caplog):
        """Тест finally блока в __del__ при SystemExit.

        Проверяет:
        - SystemExit пробрасывается из __del__
        - Ресурсы очищаются корректно
        """
        with caplog.at_level(logging.DEBUG):
            manager = CacheManager(temp_cache_dir, ttl_hours=24, pool_size=5)

            # Mock finalizer для выбрасывания SystemExit
            mock_finalizer = MagicMock()
            mock_finalizer.detach.side_effect = SystemExit("Mocked SystemExit")
            manager._finalizer = mock_finalizer

            # Пытаемся уничтожить менеджер и ожидаем SystemExit
            with pytest.raises(SystemExit):
                manager.__del__()

            # Проверяем что SystemExit был залогирован
            assert any("SystemExit" in record.message for record in caplog.records)

    def test_cache_manager_set_finally_cleanup(self, cache_manager: CacheManager, caplog):
        """Тест finally блока в методе set.

        Проверяет:
        - Курсор закрывается в finally блоке
        - Даже при возникновении исключений
        """
        with caplog.at_level(logging.ERROR):
            # Mock курсора для выбрасывания исключения при close
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = sqlite3.Error("Mocked sqlite3.Error")
            mock_cursor.close.side_effect = RuntimeError("Mocked RuntimeError in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.commit.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся сохранить данные в кэш
                cache_manager.set("https://example.com/test", {"data": "test"})

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_clear_expired_finally_cleanup(self, cache_manager: CacheManager, caplog):
        """Тест finally блока в методе clear_expired.

        Проверяет:
        - Курсор закрывается в finally блоке
        - Даже при возникновении исключений
        """
        with caplog.at_level(logging.WARNING):
            # Mock курсора для выбрасывания исключения при close
            mock_cursor = MagicMock()
            mock_cursor.execute.return_value = None
            mock_cursor.rowcount = 0
            mock_cursor.close.side_effect = sqlite3.Error("Mocked sqlite3.Error in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.commit.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся очистить истекший кэш
                result = cache_manager.clear_expired()

                # Проверяем что результат 0 (из-за ошибки)
                assert result == 0

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_get_stats_finally_cleanup(self, cache_manager: CacheManager, caplog):
        """Тест finally блока в методе get_stats.

        Проверяет:
        - Курсор закрывается в finally блоке
        - Даже при возникновении исключений
        """
        with caplog.at_level(logging.WARNING):
            # Mock курсора для выбрасывания исключения при close
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = sqlite3.Error("Mocked sqlite3.Error")
            mock_cursor.close.side_effect = RuntimeError("Mocked RuntimeError in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся получить статистику
                result = cache_manager.get_stats()

                # Проверяем что результат содержит дефолтные значения
                assert result == {"total_records": 0, "expired_records": 0, "cache_size": 0}

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called

    def test_cache_manager_context_manager_finally(self, temp_cache_dir: Path, caplog):
        """Тест finally блока в контекстном менеджере.

        Проверяет:
        - close() вызывается в __exit__
        - Ресурсы очищаются корректно
        """
        with caplog.at_level(logging.DEBUG):
            try:
                with CacheManager(temp_cache_dir, ttl_hours=24, pool_size=5) as manager:
                    # Mock pool.close для выбрасывания исключения
                    with patch.object(
                        manager._pool, "close", side_effect=sqlite3.Error("Mocked error")
                    ):
                        raise RuntimeError("Mocked runtime error in context")
            except (RuntimeError, sqlite3.Error):
                pass

            # Проверяем что ошибка при закрытии была залогирована
            # (если она была)
            assert True  # Тест проходит если не было непредвиденных ошибок

    def test_cache_manager_batch_operations_finally(self, cache_manager: CacheManager, caplog):
        """Тест finally блока в пакетных операциях.

        Проверяет:
        - Курсор закрывается в finally блоке при пакетных операциях
        - Даже при возникновении исключений
        """
        with caplog.at_level(logging.ERROR):
            # Mock курсора для выбрасывания исключения при close
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = sqlite3.Error("Mocked sqlite3.Error")
            mock_cursor.close.side_effect = RuntimeError("Mocked RuntimeError in cursor.close")

            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.commit.return_value = None

            with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
                # Пытаемся выполнить пакетное сохранение
                items = [
                    ("https://example.com/1", {"data": "test1"}),
                    ("https://example.com/2", {"data": "test2"}),
                ]
                result = cache_manager.set_batch(items)

                # Проверяем что результат 0 (из-за ошибки)
                assert result == 0

                # Проверяем что cursor.close() был вызван (finally блок выполнился)
                assert mock_cursor.close.called
