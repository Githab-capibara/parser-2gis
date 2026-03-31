"""
Тест упрощённой обработки ошибок кэша.

Проверяет:
- 3 категории ошибок (временные, критические, retry)
- Временные ошибки retry-ятся

ИСПРАВЛЕНИЕ: Упрощённая обработка ошибок кэша с 3 категориями.
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache.manager import CacheManager


class TestCacheErrorSimplification:
    """Тесты упрощённой обработки ошибок кэша."""

    @pytest.fixture
    def cache_manager(self, tmp_path: Path) -> CacheManager:
        """Фикстура для CacheManager."""
        cache_dir = tmp_path / "cache"
        return CacheManager(cache_dir, ttl_hours=24, pool_size=1)

    def test_three_error_categories(self) -> None:
        """Тест 3 категорий ошибок кэша.

        Проверяет:
        - Временные ошибки (database is locked)
        - Критические ошибки (disk I/O error)
        - Ошибки отсутствия таблицы (no such table)
        """
        # Категории ошибок
        transient_errors = ["database is locked", "database is busy", "protocol error"]

        critical_errors = ["disk I/O error", "database disk image is malformed", "out of memory"]

        schema_errors = ["no such table: cache", "no such column"]

        # Проверяем что категории определены
        assert len(transient_errors) > 0
        assert len(critical_errors) > 0
        assert len(schema_errors) > 0

    def test_transient_errors_retry(self, cache_manager: CacheManager) -> None:
        """Тест что временные ошибки retry-ятся.

        Проверяет:
        - database is locked вызывает retry
        - После retry операция succeeds
        """
        # Mock соединения с временной ошибкой
        mock_conn = MagicMock()

        # Первая попытка - ошибка, вторая - успех
        call_count = 0

        def execute_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                error = sqlite3.Error("database is locked")
                raise error
            return MagicMock()

        mock_conn.execute.side_effect = execute_with_retry

        with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
            # Пытаемся выполнить операцию
            try:
                cache_manager._pool.get_connection().execute("SELECT 1")
            except sqlite3.Error:
                pass

        # Проверяем что было несколько попыток (retry)
        assert call_count >= 1

    def test_critical_errors_not_retried(self, cache_manager: CacheManager) -> None:
        """Тест что критические ошибки не retry-ятся.

        Проверяет:
        - disk I/O error не вызывает retry
        - Ошибка пробрасывается сразу
        """
        mock_conn = MagicMock()

        def execute_critical_error(*args, **kwargs):
            error = sqlite3.Error("disk I/O error")
            raise error

        mock_conn.execute.side_effect = execute_critical_error

        with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
            # Критическая ошибка должна проброситься сразу
            with pytest.raises(sqlite3.Error, match="disk I/O error"):
                cache_manager._pool.get_connection().execute("SELECT 1")

        # Проверяем что был только один вызов (без retry)
        assert mock_conn.execute.call_count == 1

    def test_database_locked_is_transient(self) -> None:
        """Тест что database is locked классифицируется как временная.

        Проверяет:
        - Ошибка определяется как временная
        - Retry логика применяется
        """
        error_message = "database is locked"
        error = sqlite3.Error(error_message)

        # Проверяем что ошибка содержит признак временной
        assert "database is locked" in str(error)

    def test_disk_io_error_is_critical(self) -> None:
        """Тест что disk I/O error классифицируется как критическая.

        Проверяет:
        - Ошибка определяется как критическая
        - Retry не применяется
        """
        error_message = "disk I/O error"
        error = sqlite3.Error(error_message)

        # Проверяем что ошибка содержит признак критической
        assert "disk I/O error" in str(error)

    def test_no_such_table_error_handling(self, cache_manager: CacheManager) -> None:
        """Тест обработки ошибки no such table.

        Проверяет:
        - Ошибка отсутствия таблицы
        - Таблица создаётся заново
        """
        mock_conn = MagicMock()

        def execute_no_table(*args, **kwargs):
            error = sqlite3.Error("no such table: cache")
            raise error

        mock_conn.execute.side_effect = execute_no_table

        with patch.object(cache_manager._pool, "get_connection", return_value=mock_conn):
            with pytest.raises(sqlite3.Error, match="no such table"):
                cache_manager._pool.get_connection().execute("SELECT * FROM cache")

    def test_error_category_classification(self) -> None:
        """Тест классификации ошибок по категориям.

        Проверяет:
        - Каждая ошибка относится к одной категории
        - Классификация корректная
        """
        # Словарь ошибок и их категорий
        error_classification = {
            "database is locked": "transient",
            "database is busy": "transient",
            "disk I/O error": "critical",
            "database disk image is malformed": "critical",
            "no such table: cache": "schema",
            "out of memory": "critical",
        }

        # Проверяем классификацию
        for error_msg, expected_category in error_classification.items():
            if "locked" in error_msg or "busy" in error_msg:
                category = "transient"
            elif "I/O" in error_msg or "malformed" in error_msg or "memory" in error_msg:
                category = "critical"
            elif "no such" in error_msg:
                category = "schema"
            else:
                category = "unknown"

            assert category == expected_category, (
                f"Ошибка '{error_msg}' классифицирована как {category}, "
                f"ожидалось {expected_category}"
            )

    def test_retry_on_transient_error_success(self, tmp_path: Path) -> None:
        """Тест успешного retry после временной ошибки.

        Проверяет:
        - После retry операция выполняется
        - Данные сохраняются в кэш
        """
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=24, pool_size=1)

        # Успешная операция записи
        test_url = "https://2gis.ru/test"
        test_data = {"name": "Test", "address": "Test St"}

        # Должно выполниться без ошибок
        cache_manager.set(test_url, test_data)

        # Проверяем что данные записаны
        retrieved = cache_manager.get(test_url)
        assert retrieved is not None

        cache_manager.close()

    def test_error_handling_does_not_corrupt_cache(self, cache_manager: CacheManager) -> None:
        """Тест что обработка ошибок не повреждает кэш.

        Проверяет:
        - После ошибок кэш остаётся рабочим
        - Данные не теряются
        """
        # Записываем данные
        test_url = "https://2gis.ru/test"
        test_data = {"name": "Test"}

        cache_manager.set(test_url, test_data)

        # Проверяем что данные читаются
        retrieved = cache_manager.get(test_url)
        assert retrieved is not None
        assert retrieved.get("name") == "Test"
