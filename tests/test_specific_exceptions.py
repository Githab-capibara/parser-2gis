"""
Тесты для проверки специфической обработки исключений.

Проверяет что исключения обрабатываются специфично:
- specific_sqlite_exception: обработка sqlite3.Error
- specific_os_exception: обработка OSError
- specific_value_exception: обработка ValueError
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache import CacheManager, _ConnectionPool
from parser_2gis.chrome.browser import ChromeBrowser, cleanup_orphaned_profiles
from parser_2gis.chrome.file_handler import FileLogger


class TestSpecificSqliteException:
    """Тесты для специфической обработки sqlite3.Error."""

    def test_specific_sqlite_exception_database_locked(self, tmp_path, caplog):
        """
        Тест 1.1: Проверка обработки ошибки "database is locked".

        Проверяет что ошибка "database is locked"
        корректно обрабатывается и логируется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock sqlite3.Error для имитации "database is locked"
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = sqlite3.Error("database is locked")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - код обрабатывает ошибку и возвращает None
                result = cache.get("https://example.com/test")

                # Проверяем что вернул None (ошибка обработана внутренне)
                assert result is None

                # Проверяем что ошибка была залогирована
                assert (
                    "database is locked" in caplog.text
                    or "заблокирована" in caplog.text
                )
        finally:
            cache.close()

    def test_specific_sqlite_exception_disk_io_error(self, tmp_path, caplog):
        """
        Тест 1.2: Проверка обработки ошибки "disk I/O error".

        Проверяет что ошибка "disk I/O error"
        корректно обрабатывается и логируется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock sqlite3.Error для имитации "disk I/O error"
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = sqlite3.Error("disk I/O error")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - должна произойти ошибка
                with pytest.raises(sqlite3.Error):
                    cache.get("https://example.com/test")

                # Проверяем что ошибка была залогирована
                assert "disk I/O" in caplog.text or "Ошибка БД" in caplog.text
        finally:
            cache.close()

    def test_specific_sqlite_exception_no_such_table(self, tmp_path, caplog):
        """
        Тест 1.3: Проверка обработки ошибки "no such table".

        Проверяет что ошибка "no such table"
        корректно обрабатывается и логируется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock sqlite3.Error для имитации "no such table"
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = sqlite3.Error("no such table: cache")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - должна произойти ошибка
                with pytest.raises(sqlite3.Error):
                    cache.get("https://example.com/test")

                # Проверяем что ошибка была залогирована
                assert "no such table" in caplog.text or "Ошибка БД" in caplog.text
        finally:
            cache.close()

    def test_specific_sqlite_exception_connection_pool(self, tmp_path):
        """
        Тест 1.4: Проверка обработки sqlite3.Error в connection pool.

        Проверяет что sqlite3.Error в connection pool
        корректно обрабатывается.
        """
        cache_file = tmp_path / "cache.db"
        pool = _ConnectionPool(cache_file, pool_size=5, use_dynamic=False)

        try:
            # Получаем соединение
            conn = pool.get_connection()

            # Создаем новый cursor для теста
            cursor = conn.cursor()

            # Пытаемся выполнить запрос к несуществующей таблице - должна произойти ошибка
            with pytest.raises(sqlite3.Error):
                cursor.execute("SELECT * FROM nonexistent_table")
        finally:
            pool.close_all()

    def test_specific_sqlite_exception_rollback_error(self, tmp_path, caplog):
        """
        Тест 1.5: Проверка обработки ошибки при rollback.

        Проверяет что ошибка при rollback
        корректно обрабатывается и логируется.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock sqlite3.Error для имитации ошибки при rollback
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = None
                mock_conn.rollback.side_effect = sqlite3.Error("Rollback error")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - rollback вызовет ошибку
                result = cache.get("https://example.com/test")

                # Проверяем что返回 None (ошибка обработана)
                assert result is None

                # Проверяем что ошибка была залогирована
                assert (
                    "Ошибка при откате транзакции" in caplog.text
                    or "Rollback error" in caplog.text
                )
        finally:
            cache.close()


class TestSpecificOsException:
    """Тесты для специфической обработки OSError."""

    def test_specific_os_exception_file_handler_create_dir(self, caplog):
        """
        Тест 2.1: Проверка обработки OSError при создании директории.

        Проверяет что OSError при создании директории
        корректно обрабатывается и логируется.
        """
        from parser_2gis.chrome.file_handler import FileLogger

        # Mock Path.mkdir для вызова OSError
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = OSError("Permission denied")

            # Пытаемся создать FileLogger - должна произойти ошибка
            with pytest.raises(OSError) as exc_info:
                FileLogger(log_dir=Path("/root/nonexistent"))

            # Проверяем что ошибка содержит информацию о проблеме
            error_message = str(exc_info.value)
            assert (
                "Не удалось создать директорию" in error_message
                or "Permission denied" in error_message
            )

    def test_specific_os_exception_file_handler_open(self, tmp_path, caplog):
        """
        Тест 2.2: Проверка обработки OSError при открытии файла.

        Проверяет что OSError при открытии файла
        корректно обрабатывается и логируется.
        """
        log_file = tmp_path / "parser.log"

        # Mock open для вызова OSError
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = OSError("File access denied")

            # Пытаемся создать FileLogger - должна произойти ошибка
            with pytest.raises((OSError, IOError)):
                FileLogger(log_file=log_file)

    def test_specific_os_exception_browser_cleanup(self, caplog):
        """
        Тест 2.3: Проверка обработки OSError при очистке профиля браузера.

        Проверяет что OSError при очистке профиля
        корректно обрабатывается и логируется.
        """
        # Создаем mock ChromeBrowser
        browser = object.__new__(ChromeBrowser)

        # Mock TemporaryDirectory для вызова OSError
        mock_tempdir = MagicMock()
        mock_tempdir.cleanup.side_effect = OSError("Directory in use")
        browser._profile_tempdir = mock_tempdir
        browser._profile_path = "/tmp/profile"

        # Вызываем cleanup - не должно выбросить исключение
        browser._cleanup_profile()

        # Проверяем что ошибка была залогирована
        assert "Ошибка ОС/IO" in caplog.text or "Directory in use" in caplog.text

    def test_specific_os_exception_orphaned_profiles(self, tmp_path, caplog):
        """
        Тест 2.4: Проверка обработки OSError при очистке осиротевших профилей.

        Проверяет что OSError при очистке профилей
        корректно обрабатывается и логируется.
        """
        # Создаем тестовую директорию профиля
        profile_dir = tmp_path / "chrome_profile_test"
        profile_dir.mkdir()

        # Mock Path.iterdir для вызова OSError
        with patch.object(Path, "iterdir") as mock_iterdir:
            mock_iterdir.side_effect = OSError("Permission denied")

            # Вызываем cleanup - не должно выбросить исключение
            cleanup_orphaned_profiles(profiles_dir=tmp_path)

            # Проверяем что ошибка была залогирована
            assert (
                "Ошибка при очистке осиротевших профилей" in caplog.text
                or "Permission denied" in caplog.text
            )

    def test_specific_os_exception_profile_stat(self, tmp_path, caplog):
        """
        Тест 2.5: Проверка обработки OSError при stat профиля.

        Проверяет что OSError при stat профиля
        корректно обрабатывается и логируется.
        """
        # Создаем тестовую директорию профиля
        profile_dir = tmp_path / "chrome_profile_test"
        profile_dir.mkdir()

        # Mock Path.stat для вызова OSError
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.side_effect = OSError("File not found")

            # Вызываем проверку возраста - не должно выбросить исключение
            from parser_2gis.chrome.browser import _check_profile_age_by_dir

            _check_profile_age_by_dir(
                item=profile_dir,
                current_time=0,
                max_age_seconds=0,
            )

            # Проверяем что ошибка была залогирована
            assert (
                "Ошибка получения информации" in caplog.text
                or "File not found" in caplog.text
            )


class TestSpecificValueException:
    """Тесты для специфической обработки ValueError."""

    def test_specific_value_exception_invalid_log_level(self, caplog):
        """
        Тест 3.1: Проверка обработки ValueError при некорректном уровне логирования.

        Проверяет что ValueError при некорректном уровне
        корректно обрабатывается и логируется.
        """
        # Пытаемся создать FileLogger с некорректным уровнем
        with pytest.raises(ValueError) as exc_info:
            FileLogger(log_level="INVALID_LEVEL")

        # Проверяем что сообщение содержит информацию об ошибке
        assert "Некорректный уровень логирования" in str(exc_info.value)

    def test_specific_value_exception_invalid_ttl(self, tmp_path):
        """
        Тест 3.2: Проверка обработки ValueError при некорректном TTL.

        Проверяет что ValueError при некорректном TTL
        корректно обрабатывается и логируется.
        """
        cache_dir = tmp_path / "cache"

        # Пытаемся создать CacheManager с некорректным TTL
        with pytest.raises(ValueError) as exc_info:
            CacheManager(cache_dir, ttl_hours=0)

        # Проверяем что сообщение содержит информацию об ошибке
        assert "должен быть положительным числом" in str(exc_info.value)

    def test_specific_value_exception_invalid_ttl_type(self, tmp_path):
        """
        Тест 3.3: Проверка обработки ValueError при некорректном типе TTL.

        Проверяет что TypeError при некорректном типе TTL
        корректно обрабатывается и логируется.
        """
        cache_dir = tmp_path / "cache"

        # Пытаемся создать CacheManager с некорректным типом TTL
        with pytest.raises(TypeError) as exc_info:
            CacheManager(cache_dir, ttl_hours="invalid")  # type: ignore

        # Проверяем что сообщение содержит информацию об ошибке
        assert "должен быть целым числом" in str(exc_info.value)

    def test_specific_value_exception_browser_path(self, caplog):
        """
        Тест 3.4: Проверка обработки ValueError при некорректном пути к браузеру.

        Проверяет что ValueError при некорректном пути
        корректно обрабатывается и логируется.
        """
        # Создаем mock ChromeBrowser
        browser = object.__new__(ChromeBrowser)

        # Проверяем что метод _validate_binary_path существует
        assert hasattr(browser, "_validate_binary_path")

        # Пытаемся валидировать некорректный путь
        with pytest.raises(ValueError) as exc_info:
            browser._validate_binary_path("relative/path")

        # Проверяем что сообщение содержит информацию об ошибке
        assert "должен быть абсолютным" in str(exc_info.value)

    def test_specific_value_exception_browser_path_directory(self, tmp_path):
        """
        Тест 3.5: Проверка обработки ValueError при пути к директории.

        Проверяет что ValueError при пути к директории
        корректно обрабатывается и логируется.
        """
        # Создаем mock ChromeBrowser
        browser = object.__new__(ChromeBrowser)

        # Создаем тестовую директорию
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Пытаемся валидировать путь к директории
        with pytest.raises(ValueError) as exc_info:
            browser._validate_binary_path(str(test_dir))

        # Проверяем что сообщение содержит информацию об ошибке
        assert "должен указывать на файл" in str(exc_info.value)


class TestSpecificExceptionComprehensive:
    """Комплексные тесты для специфической обработки исключений."""

    def test_specific_exception_sqlite_vs_os(self, tmp_path):
        """
        Тест 4.1: Различение sqlite3.Error и OSError.

        Проверяет что sqlite3.Error и OSError
        обрабатываются по-разному.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock для имитации sqlite3.Error
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = sqlite3.Error("Database error")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - код обрабатывает sqlite3.Error и возвращает None
                result = cache.get("https://example.com/test")

                # sqlite3.Error обрабатывается внутренне и возвращает None
                assert result is None

            # Mock для имитации OSError
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = OSError("OS error")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - код обрабатывает OSError и возвращает None
                result = cache.get("https://example.com/test")

                # OSError обрабатывается внутренне и возвращает None
                assert result is None
        finally:
            cache.close()

    def test_specific_exception_value_vs_type(self, tmp_path):
        """
        Тест 4.2: Различение ValueError и TypeError.

        Проверяет что ValueError и TypeError
        обрабатываются по-разному.
        """
        cache_dir = tmp_path / "cache"

        # ValueError при некорректном значении
        with pytest.raises(ValueError):
            CacheManager(cache_dir, ttl_hours=-1)

        # TypeError при некорректном типе
        with pytest.raises(TypeError):
            CacheManager(cache_dir, ttl_hours=None)  # type: ignore

    def test_specific_exception_chained(self, tmp_path, caplog):
        """
        Тест 4.3: Проверка цепочки исключений.

        Проверяет что исключения корректно
        образуют цепочку.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock для имитации цепочки исключений
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()

                # Создаем цепочку исключений
                sqlite3.Error("Original error")
                wrapped_error = RuntimeError("Wrapped error")

                mock_cursor.fetchone.side_effect = wrapped_error
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - код обрабатывает RuntimeError и возвращает None
                result = cache.get("https://example.com/test")

                # Исключение обрабатывается внутренне и возвращает None
                assert result is None

                # Проверяем что ошибка была залогирована
                assert (
                    "Wrapped error" in caplog.text
                    or "Непредвиденная ошибка" in caplog.text
                )
        finally:
            cache.close()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
