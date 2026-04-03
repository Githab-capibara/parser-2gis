"""
Тесты для метода _handle_db_error() в cache/manager.py.

Проверяет:
- Retry логику при "database is locked"
- Обработку "busy" ошибок
- Критические ошибки (disk i/o, no such table, corrupt)
- Обычные ошибки — возврат None
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache.manager import CacheManager


class TestHandleDbErrorRetry:
    """Тесты retry логики в _handle_db_error()."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Создаёт временную директорию для кэша."""
        cache_dir = tmp_path / "test_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @pytest.fixture
    def cache_manager(self, temp_cache_dir: Path) -> CacheManager:
        """Создаёт CacheManager для тестов."""
        manager = CacheManager(temp_cache_dir, ttl_hours=24, pool_size=2)
        yield manager
        try:
            manager.close()
        except Exception:
            pass

    def test_database_is_locked_triggers_retry(self, cache_manager: CacheManager) -> None:
        """Тест 1: 'database is locked' вызывает retry."""
        error = sqlite3.OperationalError("database is locked")
        url = "https://example.com/test"
        url_hash = "abc123"

        # Мокаем пул и time.sleep
        mock_retry_conn = MagicMock()
        mock_retry_conn.execute.return_value.fetchone.return_value = None
        mock_retry_conn.close.return_value = None

        with patch("parser_2gis.cache.manager.time.sleep") as mock_sleep:
            with patch.object(cache_manager, "_pool") as mock_pool:
                mock_pool.get_connection.return_value = mock_retry_conn

                result = cache_manager._handle_db_error(error, url, url_hash)

        # Sleep должен быть вызван для retry
        mock_sleep.assert_called()
        # Результат должен быть None (retry не нашёл данных)
        assert result is None
        # Соединение должно быть возвращено в пул
        mock_pool.return_connection.assert_called()

    def test_busy_triggers_retry(self, cache_manager: CacheManager) -> None:
        """Тест 2: 'busy' вызывает retry."""
        error = sqlite3.OperationalError("database is busy")
        url = "https://example.com/test"
        url_hash = "abc123"

        mock_retry_conn = MagicMock()
        mock_retry_conn.execute.return_value.fetchone.return_value = None
        mock_retry_conn.close.return_value = None

        with patch("parser_2gis.cache.manager.time.sleep") as mock_sleep:
            with patch.object(cache_manager, "_pool") as mock_pool:
                mock_pool.get_connection.return_value = mock_retry_conn

                result = cache_manager._handle_db_error(error, url, url_hash)

        mock_sleep.assert_called()
        assert result is None
        mock_pool.return_connection.assert_called()

    def test_retry_finds_cached_data(self, cache_manager: CacheManager) -> None:
        """Тест 3: Retry находит данные в кэше."""
        import json
        from datetime import datetime, timedelta

        error = sqlite3.OperationalError("database is locked")
        url = "https://example.com/test"
        url_hash = "abc123"

        future_expires = (datetime.now() + timedelta(hours=1)).isoformat()
        test_data = json.dumps({"result": "found"})
        mock_retry_conn = MagicMock()
        mock_retry_conn.execute.return_value.fetchone.return_value = (
            test_data,
            future_expires,
        )
        mock_retry_conn.close.return_value = None

        with patch("parser_2gis.cache.manager.time.sleep"):
            with patch.object(cache_manager, "_pool") as mock_pool:
                mock_pool.get_connection.return_value = mock_retry_conn
                with patch.object(cache_manager._serializer, "deserialize", return_value={"result": "found"}):
                    result = cache_manager._handle_db_error(error, url, url_hash)

        assert result == {"result": "found"}
        mock_pool.return_connection.assert_called()

    def test_retry_fails_returns_none(self, cache_manager: CacheManager) -> None:
        """Тест 4: Retry не удался — возвращается None."""
        error = sqlite3.OperationalError("database is locked")
        url = "https://example.com/test"
        url_hash = "abc123"

        with patch("parser_2gis.cache.manager.time.sleep"):
            with patch.object(cache_manager, "_pool") as mock_pool:
                mock_pool.get_connection.return_value = None  # Пул не дал соединение

                result = cache_manager._handle_db_error(error, url, url_hash)

        assert result is None

    def test_retry_raises_error_returns_none(self, cache_manager: CacheManager) -> None:
        """Тест 5: Retry выбросил ошибку — возвращается None."""
        error = sqlite3.OperationalError("database is locked")
        url = "https://example.com/test"
        url_hash = "abc123"

        with patch("parser_2gis.cache.manager.time.sleep"):
            with patch.object(cache_manager, "_pool") as mock_pool:
                mock_pool.get_connection.side_effect = sqlite3.OperationalError("retry failed")

                result = cache_manager._handle_db_error(error, url, url_hash)

        assert result is None

    def test_disk_io_error_is_reraised(self, cache_manager: CacheManager) -> None:
        """Тест 6: 'disk i/o error' пробрасывается дальше."""
        error = sqlite3.OperationalError("disk i/o error")
        url = "https://example.com/test"
        url_hash = "abc123"

        with pytest.raises(sqlite3.OperationalError):
            cache_manager._handle_db_error(error, url, url_hash)

    def test_no_such_table_error_is_reraised(self, cache_manager: CacheManager) -> None:
        """Тест 7: 'no such table' пробрасывается дальше."""
        error = sqlite3.OperationalError("no such table: cache")
        url = "https://example.com/test"
        url_hash = "abc123"

        with pytest.raises(sqlite3.OperationalError):
            cache_manager._handle_db_error(error, url, url_hash)

    def test_corrupt_error_is_reraised(self, cache_manager: CacheManager) -> None:
        """Тест 8: 'corrupt' пробрасывается дальше."""
        error = sqlite3.OperationalError("database disk image is malformed")
        url = "https://example.com/test"
        url_hash = "abc123"

        with pytest.raises(sqlite3.OperationalError):
            cache_manager._handle_db_error(error, url, url_hash)

    def test_malformed_error_is_reraised(self, cache_manager: CacheManager) -> None:
        """Тест 9: 'malformed' пробрасывается дальше."""
        error = sqlite3.OperationalError("malformed database schema")
        url = "https://example.com/test"
        url_hash = "abc123"

        with pytest.raises(sqlite3.OperationalError):
            cache_manager._handle_db_error(error, url, url_hash)

    def test_generic_error_returns_none(self, cache_manager: CacheManager) -> None:
        """Тест 10: Обычная ошибка — возврат None."""
        error = sqlite3.OperationalError("some generic sqlite error")
        url = "https://example.com/test"
        url_hash = "abc123"

        result = cache_manager._handle_db_error(error, url, url_hash)

        assert result is None

    def test_database_locked_retry_expired_data(self, cache_manager: CacheManager) -> None:
        """Тест 11: Retry нашёл данные но они истекли."""
        from datetime import datetime, timedelta

        error = sqlite3.OperationalError("database is locked")
        url = "https://example.com/test"
        url_hash = "abc123"

        past_expires = (datetime.now() - timedelta(hours=1)).isoformat()
        test_data = '{"old": "data"}'
        mock_retry_conn = MagicMock()
        mock_retry_conn.execute.return_value.fetchone.return_value = (
            test_data,
            past_expires,
        )

        with patch("parser_2gis.cache.manager.time.sleep"):
            with patch.object(cache_manager, "_pool") as mock_pool:
                mock_pool.get_connection.return_value = mock_retry_conn

                result = cache_manager._handle_db_error(error, url, url_hash)

        # Данные истекли — должен вернуть None
        assert result is None
