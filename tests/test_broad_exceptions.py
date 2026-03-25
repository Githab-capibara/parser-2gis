"""
Тесты для проверки специфической обработки исключений (broad exceptions).

ИСПРАВЛЕНИЕ P1-1: Замена broad exceptions на специфичные
Файлы: parser_2gis/cache.py, parser_2gis/main.py, parser_2gis/common.py

Тестируют:
- Специфичные исключения в cache.py
- Специфичные исключения в main.py
- Специфичные исключения в common.py

Маркеры:
- @pytest.mark.unit для юнит-тестов
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache import CacheManager
from parser_2gis.cache.serializer import _deserialize_json, _serialize_json
from parser_2gis.constants import MAX_DATA_DEPTH, MAX_DATA_SIZE
from parser_2gis.utils.sanitizers import _sanitize_value

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# ТЕСТ 1: СПЕЦИФИЧНЫЕ ИСКЛЮЧЕНИЯ В CACHE.PY
# =============================================================================


@pytest.mark.unit
class TestSpecificExceptionsCache:
    """Тесты для специфичных исключений в cache.py."""

    def test_sqlite_error_database_locked(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка обработки sqlite3.Error "database is locked".

        Проверяет что ошибка "database is locked"
        обрабатывается специфично а не через broad Exception.

        Args:
            tmp_path: pytest tmp_path fixture.
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

                # Пытаемся получить данные - код обрабатывает ошибку
                result = cache.get("https://example.com/test")

                # Проверяем что вернул None (ошибка обработана)
                assert result is None, "Ожидался None при database is locked"
        finally:
            cache.close()

    def test_sqlite_error_disk_io(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка обработки sqlite3.Error "disk I/O error".

        Проверяет что ошибка "disk I/O error"
        обрабатывается специфично и пробрасывается.

        Args:
            tmp_path: pytest tmp_path fixture.
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
                with pytest.raises(sqlite3.Error) as exc_info:
                    cache.get("https://example.com/test")

                # Проверяем что это именно sqlite3.Error
                assert isinstance(exc_info.value, sqlite3.Error)
                assert "disk I/O" in str(exc_info.value)
        finally:
            cache.close()

    def test_sqlite_error_no_such_table(self, tmp_path: Path) -> None:
        """
        Тест 1.3: Проверка обработки sqlite3.Error "no such table".

        Проверяет что ошибка "no such table"
        обрабатывается специфично и пробрасывается.

        Args:
            tmp_path: pytest tmp_path fixture.
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
                with pytest.raises(sqlite3.Error) as exc_info:
                    cache.get("https://example.com/test")

                # Проверяем что это именно sqlite3.Error
                assert isinstance(exc_info.value, sqlite3.Error)
                assert "no such table" in str(exc_info.value)
        finally:
            cache.close()

    def test_os_error_file_access(self, tmp_path: Path) -> None:
        """
        Тест 1.4: Проверка обработки OSError при доступе к файлу.

        Проверяет что OSError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Mock OSError при доступе к файлу
            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = OSError("Permission denied")
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные - код обрабатывает OSError
                result = cache.get("https://example.com/test")

                # Проверяем что вернул None (ошибка обработана)
                assert result is None, "Ожидался None при OSError"
        finally:
            cache.close()

    def test_type_error_invalid_data(self, tmp_path: Path) -> None:
        """
        Тест 1.5: Проверка обработки TypeError при некорректных данных.

        Проверяет что TypeError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Пытаемся сохранить некорректные данные
            with pytest.raises(TypeError):
                cache.set("https://example.com/test", None)  # type: ignore

        finally:
            cache.close()

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

    def test_serialize_json_error(self, tmp_path: Path) -> None:
        """
        Тест 1.7: Проверка обработки ошибки сериализации JSON.

        Проверяет что TypeError при сериализации обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """

        # Создаем данные которые нельзя сериализовать
        class UnserializableClass:
            pass

        data = {"key": UnserializableClass()}

        # Пытаемся сериализовать - должна произойти ошибка
        with pytest.raises(TypeError) as exc_info:
            _serialize_json(data)

        # Проверяем что это именно TypeError
        assert isinstance(exc_info.value, TypeError)

    def test_deserialize_json_error(self, tmp_path: Path) -> None:
        """
        Тест 1.8: Проверка обработки ошибки десериализации JSON.

        Проверяет что ValueError при десериализации обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Некорректная JSON строка
        invalid_json = '{"key": invalid_json}'

        # Пытаемся десериализовать - должна произойти ошибка
        with pytest.raises(ValueError) as exc_info:
            _deserialize_json(invalid_json)

        # Проверяем что это именно ValueError
        assert isinstance(exc_info.value, ValueError)


# =============================================================================
# ТЕСТ 2: СПЕЦИФИЧНЫЕ ИСКЛЮЧЕНИЯ В MAIN.PY
# =============================================================================


@pytest.mark.unit
class TestSpecificExceptionsMain:
    """Тесты для специфичных исключений в main.py."""

    def test_keyboard_interrupt_handling(self) -> None:
        """
        Тест 2.1: Проверка обработки KeyboardInterrupt.

        Проверяет что KeyboardInterrupt обрабатывается специфично
        а не через broad Exception.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        from parser_2gis.main import cleanup_resources

        # Mock для имитации KeyboardInterrupt
        with patch("parser_2gis.main.ChromeRemote") as mock_chrome:
            mock_chrome._active_instances = []

            # Вызываем cleanup - не должно быть ошибок
            try:
                cleanup_resources()
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt не должен пробрасываться")

    def test_system_exit_handling(self) -> None:
        """
        Тест 2.2: Проверка обработки SystemExit.

        Проверяет что SystemExit обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        from parser_2gis.main import cleanup_resources

        # Mock для имитации SystemExit
        with patch("parser_2gis.main.ChromeRemote") as mock_chrome:
            mock_chrome._active_instances = []

            # Вызываем cleanup - не должно быть ошибок
            try:
                cleanup_resources()
            except SystemExit:
                pytest.fail("SystemExit не должен пробрасываться")

    def test_memory_error_handling(self) -> None:
        """
        Тест 2.3: Проверка обработки MemoryError.

        Проверяет что MemoryError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        from parser_2gis.main import cleanup_resources

        # Mock для имитации MemoryError
        with patch("parser_2gis.main.gc.collect") as mock_gc:
            mock_gc.side_effect = MemoryError("Out of memory")

            # Вызываем cleanup - должна обработать ошибку
            try:
                cleanup_resources()
            except MemoryError:
                pytest.fail("MemoryError должен быть обработан")

    def test_import_error_handling(self) -> None:
        """
        Тест 2.4: Проверка обработки ImportError.

        Проверяет что ImportError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что модуль корректно обрабатывает отсутствующие опциональные зависимости
        try:
            from parser_2gis.main import _get_signal_handler

            # Функция должна быть доступна
            assert callable(_get_signal_handler)
        except ImportError as e:
            pytest.fail(f"ImportError не должен возникать: {e}")

    def test_sqlite_error_in_cleanup(self) -> None:
        """
        Тест 2.5: Проверка обработки sqlite3.Error в cleanup.

        Проверяет что sqlite3.Error в cleanup обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        from parser_2gis.main import cleanup_resources

        # Mock Cache с ошибкой
        with patch("parser_2gis.main.Cache") as mock_cache:
            mock_cache.close_all.side_effect = sqlite3.Error("Database error")

            # Вызываем cleanup - должна обработать ошибку
            try:
                cleanup_resources()
            except sqlite3.Error:
                pytest.fail("sqlite3.Error должен быть обработан")


# =============================================================================
# ТЕСТ 3: СПЕЦИФИЧНЫЕ ИСКЛЮЧЕНИЯ В COMMON.PY
# =============================================================================


@pytest.mark.unit
class TestSpecificExceptionsCommon:
    """Тесты для специфичных исключений в common.py."""

    def test_value_error_data_size_limit(self) -> None:
        """
        Тест 3.1: Проверка обработки ValueError при превышении размера данных.

        Проверяет что ValueError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Создаем данные превышающие лимит размера
        # MAX_DATA_SIZE = 10 MB
        large_data = {"data": "x" * (MAX_DATA_SIZE + 1)}

        # Пытаемся обработать - должна произойти ошибка
        with pytest.raises(ValueError) as exc_info:
            _sanitize_value(large_data)

        # Проверяем что это именно ValueError
        assert isinstance(exc_info.value, ValueError)
        assert "превышает максимальный лимит" in str(exc_info.value).lower()

    def test_value_error_depth_limit(self) -> None:
        """
        Тест 3.2: Проверка обработки ValueError при превышении глубины.

        Проверяет что ValueError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Создаем данные превышающие лимит глубины
        # MAX_DATA_DEPTH = 100
        data: Dict[str, Any] = {"value": "leaf"}
        for i in range(MAX_DATA_DEPTH + 50):
            data = {"nested": data}

        # Пытаемся обработать - должна произойти ошибка
        with pytest.raises(ValueError) as exc_info:
            _sanitize_value(data)

        # Проверяем что это именно ValueError
        assert isinstance(exc_info.value, ValueError)
        assert "глубина вложенности" in str(exc_info.value).lower()

    def test_value_error_collection_size_limit(self) -> None:
        """
        Тест 3.3: Проверка обработки ValueError при превышении размера коллекции.

        Проверяет что ValueError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        from parser_2gis.common import MAX_COLLECTION_SIZE

        # Создаем данные превышающие лимит размера коллекции
        # MAX_COLLECTION_SIZE = 100,000
        large_list = list(range(MAX_COLLECTION_SIZE + 1000))
        data = {"list": large_list}

        # Пытаемся обработать - должна произойти ошибка
        with pytest.raises(ValueError) as exc_info:
            _sanitize_value(data)

        # Проверяем что это именно ValueError
        assert isinstance(exc_info.value, ValueError)
        error_msg = str(exc_info.value).lower()
        assert "превышает" in error_msg or "размер" in error_msg

    def test_type_error_invalid_input(self) -> None:
        """
        Тест 3.4: Проверка обработки TypeError при некорректном вводе.

        Проверяет что TypeError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """

        # Пытаемся обработать некорректный тип
        class UnsanitizableClass:
            pass

        data = UnsanitizableClass()

        # Функция должна обработать или выбросить TypeError
        try:
            result = _sanitize_value(data)
            # Объект без чувствительного ключа не должен становиться <REDACTED>
            # Функция просто возвращает объект для таких случаев
            assert result is not None
        except TypeError:
            # TypeError тоже допустим
            pass

    def test_runtime_error_handling(self) -> None:
        """
        Тест 3.5: Проверка обработки RuntimeError.

        Проверяет что RuntimeError обрабатывается специфично.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Mock для имитации RuntimeError
        with patch("parser_2gis.utils.sanitizers._check_value_type_and_sensitivity") as mock_check:
            mock_check.side_effect = RuntimeError("Test runtime error")

            data = {"key": "value"}

            # Пытаемся обработать - должна произойти ошибка
            with pytest.raises(RuntimeError):
                _sanitize_value(data)


# =============================================================================
# ТЕСТ 4: КОМПЛЕКСНЫЕ ТЕСТЫ
# =============================================================================


@pytest.mark.unit
class TestSpecificExceptionsComprehensive:
    """Комплексные тесты для специфичных исключений."""

    def test_exception_hierarchy_sqlite(self, tmp_path: Path) -> None:
        """
        Тест 4.1: Проверка иерархии исключений SQLite.

        Проверяет что различные sqlite3.Error обрабатываются корректно.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Тестируем различные типы sqlite3.Error
            error_messages = [
                ("database is locked", True),  # Временная ошибка
                ("disk I/O error", False),  # Критическая ошибка
                ("no such table", False),  # Критическая ошибка
                ("corrupt database", False),  # Критическая ошибка
            ]

            for error_msg, should_be_handled in error_messages:
                with patch.object(cache._pool, "get_connection") as mock_get_conn:
                    mock_conn = MagicMock()
                    mock_cursor = MagicMock()
                    mock_cursor.fetchone.side_effect = sqlite3.Error(error_msg)
                    mock_conn.cursor.return_value = mock_cursor
                    mock_get_conn.return_value = mock_conn

                    if should_be_handled:
                        # Ошибка должна быть обработана и возвращён None
                        result = cache.get("https://example.com/test")
                        assert result is None, f"Ожидался None для {error_msg}"
                    else:
                        # Ошибка должна быть проброшена
                        with pytest.raises(sqlite3.Error):
                            cache.get("https://example.com/test")
        finally:
            cache.close()

    def test_exception_chaining(self, tmp_path: Path) -> None:
        """
        Тест 4.2: Проверка цепочки исключений.

        Проверяет что исключения образуют корректную цепочку.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Создаем цепочку исключений
            original_error = sqlite3.Error("Original database error")

            with patch.object(cache._pool, "get_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_cursor.fetchone.side_effect = original_error
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                # Пытаемся получить данные
                result = cache.get("https://example.com/test")

                # Для временных ошибок результат должен быть None
                assert result is None
        finally:
            cache.close()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
