"""
Тесты для специфичных исключений в cache.py.

Проверяет обработку:
- sqlite3.Error (database is locked, disk I/O error, no such table)
- OSError при доступе к файлу
- TypeError при некорректных данных
- ValueError при некорректном TTL
- Ошибки сериализации/десериализации JSON
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache import CacheManager
from parser_2gis.cache.serializer import _deserialize_json, _serialize_json

# =============================================================================
# ТЕСТЫ ДЛЯ СПЕЦИФИЧНЫХ ИСКЛЮЧЕНИЙ В CACHE.PY
# =============================================================================


@pytest.mark.unit
class TestCacheSpecificExceptions:
    """Тесты для специфичных исключений в cache.py."""

    def test_sqlite_error_database_locked(self, tmp_path: Path, temp_cache_manager: CacheManager) -> None:
        """
        Тест 1.1: Проверка обработки sqlite3.Error "database is locked".

        Проверяет что ошибка "database is locked"
        обрабатывается специфично а не через broad Exception.

        Args:
            tmp_path: pytest tmp_path fixture.
            temp_cache_manager: Временный CacheManager.
        """
        cache = temp_cache_manager

        # Mock sqlite3.Error для имитации "database is locked"
        with patch.object(cache._pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = sqlite3.Error("database is locked")
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            # Пытаемся получить данные - код обрабатывает ошибку
            result = cache.get("https://example.com/test")

            # Проверяем что вернул None (ошибка обработана)
            assert result is None, "Ожидался None при database is locked"

    def test_sqlite_error_disk_io(self, tmp_path: Path, temp_cache_manager: CacheManager) -> None:
        """
        Тест 1.2: Проверка обработки sqlite3.Error "disk I/O error".

        Проверяет что ошибка "disk I/O error"
        пробрасывается дальше как sqlite3.Error.

        Args:
            tmp_path: pytest tmp_path fixture.
            temp_cache_manager: Временный CacheManager.
        """
        cache = temp_cache_manager

        # Mock execute для имитации "disk I/O error"
        with patch.object(cache._pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = sqlite3.Error("disk I/O error")
            mock_conn.cursor.return_value.fetchone.return_value = None
            mock_get_conn.return_value = mock_conn

            # Пытаемся получить данные - должна произойти ошибка
            with pytest.raises(sqlite3.Error) as exc_info:
                cache.get("https://example.com/test")

            # Проверяем что это именно sqlite3.Error
            assert isinstance(exc_info.value, sqlite3.Error)
            assert "disk I/O" in str(exc_info.value)

    def test_sqlite_error_no_such_table(self, tmp_path: Path, temp_cache_manager: CacheManager) -> None:
        """
        Тест 1.3: Проверка обработки sqlite3.Error "no such table".

        Проверяет что ошибка "no such table"
        пробрасывается дальше как sqlite3.Error.

        Args:
            tmp_path: pytest tmp_path fixture.
            temp_cache_manager: Временный CacheManager.
        """
        cache = temp_cache_manager

        # Mock execute для имитации "no such table"
        with patch.object(cache._pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = sqlite3.Error("no such table: cache")
            mock_conn.cursor.return_value.fetchone.return_value = None
            mock_get_conn.return_value = mock_conn

            # Пытаемся получить данные - должна произойти ошибка
            with pytest.raises(sqlite3.Error) as exc_info:
                cache.get("https://example.com/test")

            # Проверяем что это именно sqlite3.Error
            assert isinstance(exc_info.value, sqlite3.Error)
            assert "no such table" in str(exc_info.value)

    def test_os_error_file_access(self, tmp_path: Path, temp_cache_manager: CacheManager) -> None:
        """
        Тест 1.4: Проверка обработки OSError при доступе к файлу.

        Проверяет что OSError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
            temp_cache_manager: Временный CacheManager.
        """
        cache = temp_cache_manager

        # Mock OSError при доступе к файлу
        with patch.object(cache._pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = OSError("Permission denied")
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            # Пытаемся получить данные - код обрабатывает ошибку
            result = cache.get("https://example.com/test")

            # Проверяем что вернул None (ошибка обработана)
            assert result is None, "Ожидался None при OSError"

    def test_type_error_invalid_data(self, tmp_path: Path, temp_cache_manager: CacheManager) -> None:
        """
        Тест 1.5: Проверка обработки TypeError при некорректных данных.

        Проверяет что TypeError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
            temp_cache_manager: Временный CacheManager.
        """
        cache = temp_cache_manager

        # Пытаемся сохранить некорректные данные
        with pytest.raises(TypeError):
            cache.set("https://example.com/test", None)  # type: ignore

    def test_value_error_invalid_ttl(self, tmp_path: Path) -> None:
        """
        Тест 1.6: Проверка обработки ValueError при некорректном TTL.

        Проверяет что ValueError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_dir = tmp_path / "cache"

        # Пытаемся создать CacheManager с некорректным TTL
        with pytest.raises(ValueError) as exc_info:
            CacheManager(cache_dir, ttl_hours=-1)

        # Проверяем что это именно ValueError
        assert isinstance(exc_info.value, ValueError)
        assert "положительным" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        "invalid_data,expected_error",
        [
            ({"key": object()}, TypeError),  # Не сериализуемый объект
            ({"key": lambda x: x}, TypeError),  # Lambda функция
        ],
    )
    def test_serialize_json_error(self, invalid_data: dict, expected_error: type) -> None:
        """
        Тест 1.7: Проверка обработки ошибки сериализации JSON.

        Проверяет что TypeError при сериализации обрабатывается специфично.

        Args:
            invalid_data: Данные которые нельзя сериализовать.
            expected_error: Ожидаемый тип ошибки.
        """
        # Пытаемся сериализовать - должна произойти ошибка
        with pytest.raises(expected_error):
            _serialize_json(invalid_data)

    def test_deserialize_json_error(self) -> None:
        """
        Тест 1.8: Проверка обработки ошибки десериализации JSON.

        Проверяет что ValueError при десериализации обрабатывается специфично.
        """
        # Некорректная JSON строка
        invalid_json = '{"key": invalid_json}'

        # Пытаемся десериализовать - должна произойти ошибка
        with pytest.raises(ValueError) as exc_info:
            _deserialize_json(invalid_json)

        # Проверяем что это именно ValueError
        assert isinstance(exc_info.value, ValueError)

    @pytest.mark.parametrize(
        "error_msg,should_be_handled",
        [
            ("database is locked", True),  # Временная ошибка
            ("disk I/O error", False),  # Критическая ошибка
            ("no such table", False),  # Критическая ошибка
            ("corrupt database", False),  # Критическая ошибка
        ],
    )
    def test_exception_hierarchy_sqlite(
        self,
        tmp_path: Path,
        error_msg: str,
        should_be_handled: bool,
        temp_cache_manager: CacheManager,
    ) -> None:
        """
        Тест 1.9: Проверка иерархии исключений SQLite.

        Проверяет что различные sqlite3.Error обрабатываются корректно.

        Args:
            tmp_path: pytest tmp_path fixture.
            error_msg: Сообщение ошибки.
            should_be_handled: Должна ли быть обработана.
            temp_cache_manager: Временный CacheManager.
        """
        cache = temp_cache_manager

        with patch.object(cache._pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = sqlite3.Error(error_msg)
            mock_conn.cursor.return_value.fetchone.return_value = None
            mock_get_conn.return_value = mock_conn

            if should_be_handled:
                # Ошибка должна быть обработана и возвращён None
                result = cache.get("https://example.com/test")
                assert result is None, f"Ошибка '{error_msg}' должна быть обработана"
            else:
                # Ошибка должна быть проброшена
                with pytest.raises(sqlite3.Error):
                    cache.get("https://example.com/test")
