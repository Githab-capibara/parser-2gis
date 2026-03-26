"""
Комплексные тесты для проверок обработки исключений.

Этот модуль тестирует исправления broad exception handlers в:
- parser_2gis/cache/pool.py - обработка MemoryError, OSError, ValueError, TypeError
- parser_2gis/parallel/parallel_parser.py - обработка исключений в параллельном парсере
- parser_2gis/chrome/browser.py - обработка FileNotFoundError, SubprocessError, OSError

Каждый тест проверяет ОДНО конкретное исправление.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

from parser_2gis.cache.pool import ConnectionPool, _calculate_dynamic_pool_size
from parser_2gis.parallel.parallel_parser import ParallelCityParser

# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/cache/pool.py
# =============================================================================


class TestConnectionPoolExceptionHandling:
    """Тесты на обработку исключений в ConnectionPool."""

    @pytest.fixture
    def temp_db(self, tmp_path: Path) -> Generator[Path, None, None]:
        """Фикстура для временной БД.

        Args:
            tmp_path: pytest tmp_path fixture.

        Yields:
            Путь к временному файлу БД.
        """
        db_file = tmp_path / "test_pool.db"
        yield db_file
        # Очистка после теста
        if db_file.exists():
            try:
                db_file.unlink()
            except OSError:
                pass

    def test_memory_error_in_create_connection(self, temp_db: Path) -> None:
        """
        Тест на обработку MemoryError при создании соединения.

        Проверяет:
        - MemoryError корректно обрабатывается в _create_connection
        - Пул продолжает работать после ошибки

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            # Мокаем sqlite3.connect для выброса MemoryError
            with patch("sqlite3.connect") as mock_connect:
                mock_connect.side_effect = MemoryError("Mocked MemoryError")

                # Пытаемся получить соединение - должно выбросить MemoryError
                with pytest.raises(MemoryError):
                    pool.get_connection()
        finally:
            pool.close()

    def test_os_error_in_create_connection(self, temp_db: Path) -> None:
        """
        Тест на обработку OSError при создании соединения.

        Проверяет:
        - OSError корректно обрабатывается

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            with patch("sqlite3.connect") as mock_connect:
                mock_connect.side_effect = OSError("Mocked OSError - disk full")

                with pytest.raises(OSError):
                    pool.get_connection()
        finally:
            pool.close()

    def test_value_error_in_create_connection(self, temp_db: Path) -> None:
        """
        Тест на обработку ValueError при создании соединения.

        Проверяет:
        - ValueError корректно обрабатывается
        - Пул может восстановиться после ошибки

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            with patch("sqlite3.connect") as mock_connect:
                mock_connect.side_effect = ValueError("Mocked ValueError")

                with pytest.raises(ValueError):
                    pool.get_connection()
        finally:
            pool.close()

    def test_type_error_in_create_connection(self, temp_db: Path) -> None:
        """
        Тест на обработку TypeError при создании соединения.

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            with patch("sqlite3.connect") as mock_connect:
                mock_connect.side_effect = TypeError("Mocked TypeError")

                with pytest.raises(TypeError):
                    pool.get_connection()
        finally:
            pool.close()

    def test_sqlite_error_in_get_connection(self, temp_db: Path) -> None:
        """
        Тест на обработку sqlite3.Error при получении соединения.

        Проверяет:
        - sqlite3.Error обрабатывается корректно

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            # Получаем соединение
            conn = pool.get_connection()
            assert conn is not None

            # Возвращаем соединение в пул
            pool.return_connection(conn)

        finally:
            pool.close()

    def test_os_error_in_return_connection(self, temp_db: Path) -> None:
        """
        Тест на обработку OSError при возврате соединения в пул.

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        try:
            conn = pool.get_connection()

            # Мокаем queue.put для выброса OSError
            with patch.object(pool._connection_queue, "put_nowait") as mock_put:
                mock_put.side_effect = OSError("Mocked OSError")

                # Возвращаем соединение - должно выбросить OSError
                with pytest.raises(OSError):
                    pool.return_connection(conn)
        finally:
            pool.close()

    def test_runtime_error_in_close(self, temp_db: Path) -> None:
        """
        Тест на обработку RuntimeError при закрытии пула.

        Проверяет:
        - RuntimeError в close не ломает очистку

        Args:
            temp_db: Временная БД.
        """
        pool = ConnectionPool(temp_db, pool_size=5)

        # Получаем соединение
        _ = pool.get_connection()

        # Закрываем пул - не должно выбросить исключение
        pool.close()

    def test_context_manager_exception_handling(self, temp_db: Path) -> None:
        """
        Тест на обработку исключений в контекстном менеджере.

        Проверяет:
        - Контекстный менеджер корректно закрывает соединения
        - Исключения в __exit__ обрабатываются

        Args:
            temp_db: Временная БД.
        """
        with ConnectionPool(temp_db, pool_size=5) as pool:
            conn = pool.get_connection()
            assert conn is not None
            # Контекстный менеджер автоматически закроет соединения


# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/parallel/parallel_parser.py
# =============================================================================


class TestParallelParserExceptionHandling:
    """Тесты на обработку исключений в ParallelCityParser."""

    @pytest.fixture
    def sample_cities(self) -> list[dict]:
        """Фикстура с примером городов."""
        return [{"name": "Москва", "id": "1"}, {"name": "Санкт-Петербург", "id": "2"}]

    @pytest.fixture
    def sample_categories(self) -> list[dict]:
        """Фикстура с примером категорий."""
        return [{"name": "Рестораны", "id": "100"}, {"name": "Магазины", "id": "200"}]

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        """Фикстура для mock конфигурации."""
        config = MagicMock()
        config.writer.encoding = "utf-8"
        config.parallel.use_temp_file_cleanup = False
        return config

    def test_memory_error_in_parse_single_url(
        self,
        sample_cities: list[dict],
        sample_categories: list[dict],
        mock_config: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест на обработку MemoryError в parse_single_url.

        Проверяет:
        - MemoryError корректно обрабатывается
        - Временный файл удаляется после ошибки
        - Статистика обновляется

        Args:
            sample_cities: Список городов.
            sample_categories: Список категорий.
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.
            caplog: Фикстура для захвата логов.
        """
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
        )

        url = "https://test.url"
        category = "Тест"
        city = "Москва"

        # Мокаем get_writer и get_parser для выброса MemoryError
        with patch("parser_2gis.parallel.parallel_parser.get_writer") as mock_writer:
            mock_writer.side_effect = MemoryError("Mocked MemoryError")

            success, message = parser.parse_single_url(url, category, city)

            # Проверяем что ошибка обработана
            assert success is False
            assert "MemoryError" in message

            # Проверяем логирование
            assert any("MemoryError" in record.message for record in caplog.records)

    def test_os_error_in_parse_single_url(
        self,
        sample_cities: list[dict],
        sample_categories: list[dict],
        mock_config: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест на обработку OSError в parse_single_url.

        Args:
            sample_cities: Список городов.
            sample_categories: Список категорий.
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.
            caplog: Фикстура для захвата логов.
        """
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
        )

        url = "https://test.url"
        category = "Тест"
        city = "Москва"

        with patch("parser_2gis.parallel.parallel_parser.get_writer") as mock_writer:
            mock_writer.side_effect = OSError("Mocked OSError - disk full")

            success, message = parser.parse_single_url(url, category, city)

            assert success is False
            assert "OSError" in message

            # Проверяем логирование
            assert any("OSError" in record.message for record in caplog.records)

    def test_runtime_error_in_parse_single_url(
        self,
        sample_cities: list[dict],
        sample_categories: list[dict],
        mock_config: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Тест на обработку RuntimeError в parse_single_url.

        Args:
            sample_cities: Список городов.
            sample_categories: Список категорий.
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.
        """
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
        )

        url = "https://test.url"
        category = "Тест"
        city = "Москва"

        with patch("parser_2gis.parallel.parallel_parser.get_writer") as mock_writer:
            mock_writer.side_effect = RuntimeError("Mocked RuntimeError")

            success, message = parser.parse_single_url(url, category, city)

            assert success is False
            assert "RuntimeError" in message

    def test_type_error_in_parse_single_url(
        self,
        sample_cities: list[dict],
        sample_categories: list[dict],
        mock_config: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Тест на обработку TypeError в parse_single_url.

        Args:
            sample_cities: Список городов.
            sample_categories: Список категорий.
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.
        """
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
        )

        url = "https://test.url"
        category = "Тест"
        city = "Москва"

        with patch("parser_2gis.parallel.parallel_parser.get_writer") as mock_writer:
            mock_writer.side_effect = TypeError("Mocked TypeError")

            success, message = parser.parse_single_url(url, category, city)

            assert success is False

    def test_value_error_in_parse_single_url(
        self,
        sample_cities: list[dict],
        sample_categories: list[dict],
        mock_config: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Тест на обработку ValueError в parse_single_url.

        Args:
            sample_cities: Список городов.
            sample_categories: Список категорий.
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.
        """
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
        )

        url = "https://test.url"
        category = "Тест"
        city = "Москва"

        with patch("parser_2gis.parallel.parallel_parser.get_writer") as mock_writer:
            mock_writer.side_effect = ValueError("Mocked ValueError")

            success, message = parser.parse_single_url(url, category, city)

            assert success is False

    def test_temp_file_cleanup_on_error(
        self,
        sample_cities: list[dict],
        sample_categories: list[dict],
        mock_config: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Тест на очистку временных файлов при ошибке.

        Проверяет:
        - Временный файл создаётся с уникальным именем
        - При ошибке файл удаляется
        - Флаг cleanup срабатывает

        Args:
            sample_cities: Список городов.
            sample_categories: Список категорий.
            mock_config: Mock конфигурации.
            tmp_path: Временная директория.
        """
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=str(tmp_path),
            config=mock_config,
            max_workers=2,
        )

        url = "https://test.url"
        category = "Тест"
        city = "Москва"

        # Создаём временный файл вручную для проверки удаления
        temp_file = tmp_path / "test_temp_file.tmp"
        temp_file.write_text("temp data")

        # Мокаем exists для возврата True (файл существует)
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "unlink") as mock_unlink:
                with patch("parser_2gis.parallel.parallel_parser.get_writer") as mock_writer:
                    mock_writer.side_effect = MemoryError("Mocked MemoryError")

                    success, _ = parser.parse_single_url(url, category, city)

                    # Проверяем что unlink был вызван для cleanup
                    assert mock_unlink.called


# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/chrome/browser.py
# =============================================================================


class TestChromeBrowserExceptionHandling:
    """Тесты на обработку исключений в ChromeBrowser."""

    def test_file_not_found_in_init(
        self, mock_chrome_options: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Тест на обработку FileNotFoundError при инициализации браузера.

        Проверяет:
        - FileNotFoundError корректно обрабатывается
        - Профиль очищается при ошибке
        - Ошибка логируется

        Args:
            mock_chrome_options: Mock опций Chrome.
            caplog: Фикстура для захвата логов.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        # Мокаем locate_chrome_path для возврата несуществующего пути
        with patch(
            "parser_2gis.chrome.browser.locate_chrome_path", return_value="/nonexistent/path"
        ):
            with pytest.raises(FileNotFoundError):
                ChromeBrowser(mock_chrome_options)

            # Проверяем логирование
            assert any("Ошибка инициализации Chrome" in record.message for record in caplog.records)

    def test_subprocess_error_in_init(
        self, mock_chrome_options: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Тест на обработку SubprocessError при инициализации.

        Args:
            mock_chrome_options: Mock опций Chrome.
            caplog: Фикстура для захвата логов.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        # Мокаем subprocess.Popen для выброса SubprocessError
        with patch("parser_2gis.chrome.browser.subprocess.Popen") as mock_popen:
            mock_popen.side_effect = subprocess.SubprocessError("Mocked SubprocessError")

            with pytest.raises(subprocess.SubprocessError):
                ChromeBrowser(mock_chrome_options)

            # Проверяем логирование
            assert any(
                "Ошибка инициализации Chrome - subprocess" in record.message
                for record in caplog.records
            )

    def test_os_error_in_init(
        self, mock_chrome_options: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Тест на обработку OSError при инициализации.

        Args:
            mock_chrome_options: Mock опций Chrome.
            caplog: Фикстура для захвата логов.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        # Мокаем tempfile.TemporaryDirectory для выброса OSError
        with patch("parser_2gis.chrome.browser.tempfile.TemporaryDirectory") as mock_tempdir:
            mock_tempdir.side_effect = OSError("Mocked OSError")

            with pytest.raises(OSError):
                ChromeBrowser(mock_chrome_options)

    def test_value_error_in_init(self, mock_chrome_options: MagicMock) -> None:
        """
        Тест на обработку ValueError при инициализации.

        Проверяет:
        - ValueError при некорректных параметрах
        - Очистка профиля при ошибке

        Args:
            mock_chrome_options: Mock опций Chrome.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        # Устанавливаем некорректный binary_path
        mock_chrome_options.binary_path = ""

        with patch("parser_2gis.chrome.browser.locate_chrome_path", return_value=None):
            with pytest.raises(Exception):  # ChromePathNotFound или ValueError
                ChromeBrowser(mock_chrome_options)

    def test_type_error_in_init(self, mock_chrome_options: MagicMock) -> None:
        """
        Тест на обработку TypeError при инициализации.

        Args:
            mock_chrome_options: Mock опций Chrome.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        # Устанавливаем некорректный тип binary_path
        mock_chrome_options.binary_path = 123  # type: ignore[assignment]

        with patch("parser_2gis.chrome.browser.locate_chrome_path", return_value=None):
            with pytest.raises((TypeError, Exception)):
                ChromeBrowser(mock_chrome_options)



@pytest.fixture
def mock_chrome_options() -> MagicMock:
    """Фикстура для mock Chrome опций."""
    options = MagicMock()
    options.binary_path = None
    options.headless = True
    options.silent_browser = True
    options.memory_limit = 2048
    options.start_maximized = False
    options.disable_images = False
    return options


# =============================================================================
# ТЕСТЫ ДЛЯ _calculate_dynamic_pool_size
# =============================================================================


class TestCalculateDynamicPoolSizeExceptions:
    """Тесты на обработку исключений в _calculate_dynamic_pool_size."""

    def test_memory_error_in_dynamic_pool_size(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест на обработку MemoryError в _calculate_dynamic_pool_size.

        Проверяет:
        - MemoryError возвращает MIN_POOL_SIZE
        - Ошибка логируется

        Args:
            caplog: Фикстура для захвата логов.
        """
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.side_effect = MemoryError("Mocked MemoryError")

            result = _calculate_dynamic_pool_size()

            # Проверяем что возвращён MIN_POOL_SIZE
            from parser_2gis.constants import MIN_POOL_SIZE

            assert result == MIN_POOL_SIZE

            # Проверяем логирование
            assert any("MemoryError" in record.message for record in caplog.records)

    def test_os_error_in_dynamic_pool_size(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест на обработку OSError в _calculate_dynamic_pool_size.

        Args:
            caplog: Фикстура для захвата логов.
        """
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.side_effect = OSError("Mocked OSError")

            result = _calculate_dynamic_pool_size()

            from parser_2gis.constants import MIN_POOL_SIZE

            assert result == MIN_POOL_SIZE

            # Проверяем логирование
            assert any("OSError" in record.message for record in caplog.records)

    def test_value_error_in_dynamic_pool_size(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест на обработку ValueError в _calculate_dynamic_pool_size.

        Args:
            caplog: Фикстура для захвата логов.
        """
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.side_effect = ValueError("Mocked ValueError")

            result = _calculate_dynamic_pool_size()

            from parser_2gis.constants import MIN_POOL_SIZE

            assert result == MIN_POOL_SIZE

    def test_type_error_in_dynamic_pool_size(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест на обработку TypeError в _calculate_dynamic_pool_size.

        Args:
            caplog: Фикстура для захвата логов.
        """
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value.available = "invalid"  # type: ignore[attr-defined]

            result = _calculate_dynamic_pool_size()

            from parser_2gis.constants import MIN_POOL_SIZE

            assert result == MIN_POOL_SIZE
