"""
Общие фикстуры и конфигурация для тестов.

Этот файл содержит общие фикстуры, которые используются
в нескольких тестовых модулях для тестирования исправлений аудита.
"""

import asyncio
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# ФИКСТУРЫ ДЛЯ H1: OSError в _merge_csv_files()
# =============================================================================


@pytest.fixture
def mock_oserror() -> MagicMock:
    """Фикстура для mock OSError.

    Returns:
        MagicMock для имитации OSError.
    """
    with patch("builtins.OSError") as mock_error:
        mock_error.side_effect = OSError("Mocked OSError")
        yield mock_error


@pytest.fixture
def temp_csv_files(tmp_path: Path) -> Generator[List[Path], None, None]:
    """Фикстура для создания временных CSV файлов.

    Args:
        tmp_path: pytest tmp_path fixture.

    Yields:
        Список путей к CSV файлам.
    """
    import csv

    csv_files = []
    for i in range(3):
        csv_file = tmp_path / f"test_{i}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["col1", "col2", "category"])
            for j in range(10):
                writer.writerow([f"value_{i}_{j}", f"data_{i}_{j}", f"category_{i}"])
        csv_files.append(csv_file)

    yield csv_files

    # Очистка
    for csv_file in csv_files:
        if csv_file.exists():
            csv_file.unlink()


@pytest.fixture
def mock_file_open_oserror() -> Generator[MagicMock, None, None]:
    """Фикстура для mock open() с OSError.

    Yields:
        MagicMock для имитации OSError при open().
    """
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = OSError("Mocked OSError on file open")
        yield mock_open


# =============================================================================
# ФИКСТУРЫ ДЛЯ H2: shutdown() ThreadPoolExecutor
# =============================================================================


@pytest.fixture
def mock_executor() -> MagicMock:
    """Фикстура для mock ThreadPoolExecutor.

    Returns:
        MagicMock для имитации ThreadPoolExecutor.
    """
    executor = MagicMock()
    executor.submit.return_value.result.return_value = "result"
    executor.shutdown.return_value = None
    return executor


@pytest.fixture
def executor_with_exception() -> MagicMock:
    """Фикстура для mock ThreadPoolExecutor с исключением.

    Returns:
        MagicMock с исключением при submit().
    """
    executor = MagicMock()
    executor.submit.side_effect = RuntimeError("Mocked execution error")
    executor.shutdown.return_value = None
    return executor


# =============================================================================
# ФИКСТУРЫ ДЛЯ H3: Timeout для Chrome DevTools
# =============================================================================


@pytest.fixture
def mock_chrome_timeout() -> Generator[MagicMock, None, None]:
    """Фикстура для mock timeout операций Chrome.

    Yields:
        MagicMock для имитации timeout.
    """
    with patch("parser_2gis.chrome.remote.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor.__enter__ = Mock(return_value=mock_executor)
        mock_executor.__exit__ = Mock(return_value=False)

        mock_future = MagicMock()
        mock_future.result.side_effect = TimeoutError("Mocked timeout")
        mock_executor.submit.return_value = mock_future

        mock_executor_class.return_value = mock_executor
        yield mock_executor_class


@pytest.fixture
def mock_chrome_success() -> Generator[MagicMock, None, None]:
    """Фикстура для mock успешного выполнения Chrome.

    Yields:
        MagicMock для имитации успешного выполнения.
    """
    with patch("parser_2gis.chrome.remote.ThreadPoolExecutor") as mock_executor_class:
        mock_executor = MagicMock()
        mock_executor.__enter__ = Mock(return_value=mock_executor)
        mock_executor.__exit__ = Mock(return_value=False)

        mock_future = MagicMock()
        mock_future.result.return_value = {"result": "success"}
        mock_executor.submit.return_value = mock_future

        mock_executor_class.return_value = mock_executor
        yield mock_executor_class


@pytest.fixture
def mock_pychrome_browser() -> MagicMock:
    """Фикстура для mock pychrome Browser.

    Returns:
        MagicMock для имитации pychrome Browser.
    """
    browser = MagicMock()
    browser.start.return_value = None
    browser.stop.return_value = None
    browser.new_tab.return_value = MagicMock()
    return browser


# =============================================================================
# ФИКСТУРЫ ДЛЯ M1: Обработка ошибок БД в кэше
# =============================================================================


@pytest.fixture
def mock_db_connection() -> MagicMock:
    """Фикстура для mock DB соединения.

    Returns:
        MagicMock для имитации sqlite3 соединения.
    """
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    conn.commit.return_value = None
    conn.close.return_value = None
    return conn


@pytest.fixture
def mock_db_error() -> MagicMock:
    """Фикстура для mock sqlite3.Error.

    Returns:
        MagicMock для имитации sqlite3.Error.
    """
    error = MagicMock(spec=sqlite3.Error)
    error.args = ("Mocked database error",)
    return error


@pytest.fixture
def mock_database_locked_error() -> Generator[MagicMock, None, None]:
    """Фикстура для mock ошибки "database is locked".

    Yields:
        MagicMock для имитации временной ошибки БД.
    """
    with patch("parser_2gis.cache.sqlite3.Error") as mock_error_class:
        mock_error = MagicMock()
        mock_error.args = ("database is locked",)
        mock_error_class.side_effect = mock_error
        yield mock_error_class


@pytest.fixture
def mock_disk_io_error() -> Generator[MagicMock, None, None]:
    """Фикстура для mock ошибки "disk I/O error".

    Yields:
        MagicMock для имитации критической ошибки БД.
    """
    with patch("parser_2gis.cache.sqlite3.Error") as mock_error_class:
        mock_error = MagicMock()
        mock_error.args = ("disk I/O error",)
        mock_error_class.side_effect = mock_error
        yield mock_error_class


@pytest.fixture
def mock_no_such_table_error() -> Generator[MagicMock, None, None]:
    """Фикстура для mock ошибки "no such table".

    Yields:
        MagicMock для имитации ошибки отсутствия таблицы.
    """
    with patch("parser_2gis.cache.sqlite3.Error") as mock_error_class:
        mock_error = MagicMock()
        mock_error.args = ("no such table",)
        mock_error_class.side_effect = mock_error
        yield mock_error_class


# =============================================================================
# ФИКСТУРЫ ДЛЯ M2: skipped_count в cache.py
# =============================================================================


@pytest.fixture
def sample_urls() -> List[str]:
    """Фикстура для примеров URL.

    Returns:
        Список примеров URL.
    """
    return [
        "https://2gis.ru/moscow/search/Аптеки",
        "https://2gis.ru/spb/search/Рестораны",
        "https://2gis.ru/kazan/search/Магазины",
    ]


@pytest.fixture
def sample_cache_data() -> Dict[str, Any]:
    """Фикстура для примера данных кэша.

    Returns:
        Словарь с примером данных кэша.
    """
    return {
        "name": "Тестовая организация",
        "address": "г. Москва, ул. Тестовая, д. 1",
        "phones": ["+7 (495) 123-45-67"],
        "emails": ["test@example.com"],
        "website": "https://example.com",
        "rubrics": ["Тестовая рубрика"],
    }


@pytest.fixture
def mock_cache_with_serialization_error() -> Generator[MagicMock, None, None]:
    """Фикстура для mock кэша с ошибкой сериализации.

    Yields:
        MagicMock для имитации ошибки сериализации.
    """
    with patch("parser_2gis.cache._serialize_json") as mock_serialize:
        mock_serialize.side_effect = TypeError("Mocked serialization error")
        yield mock_serialize


# =============================================================================
# ФИКСТУРЫ ДЛЯ M5: LRU eviction временных файлов
# =============================================================================


@pytest.fixture
def temp_files_registry() -> Generator[set, None, None]:
    """Фикстура для реестра временных файлов.

    Yields:
        Пустой набор для реестра.
    """
    from parser_2gis.parallel_parser import _temp_files_registry

    # Сохраняем оригинальное состояние
    original_state = _temp_files_registry.copy()
    _temp_files_registry.clear()

    yield _temp_files_registry

    # Восстанавливаем оригинальное состояние
    _temp_files_registry.clear()
    _temp_files_registry.update(original_state)


@pytest.fixture
def mock_temp_file_paths(tmp_path: Path) -> List[Path]:
    """Фикстура для mock путей временных файлов.

    Args:
        tmp_path: pytest tmp_path fixture.

    Returns:
        Список путей к временным файлам.
    """
    paths = []
    for i in range(10):
        temp_file = tmp_path / f"temp_file_{i}.tmp"
        temp_file.write_text(f"temp data {i}")
        paths.append(temp_file)
    return paths


# =============================================================================
# ФИКСТУРЫ ДЛЯ M6: Code coverage настройки
# =============================================================================


@pytest.fixture
def ini_file_path() -> Path:
    """Фикстура для пути к pytest.ini.

    Returns:
        Путь к файлу pytest.ini.
    """
    return Path(__file__).parent.parent / "pytest.ini"


@pytest.fixture
def ini_file_content(ini_file_path: Path) -> str:
    """Фикстура для содержимого pytest.ini.

    Args:
        ini_file_path: Путь к файлу pytest.ini.

    Returns:
        Содержимое файла pytest.ini.
    """
    return ini_file_path.read_text(encoding="utf-8")


# =============================================================================
# ФИКСТУРЫ ДЛЯ M8: Унификация буферов
# =============================================================================


@pytest.fixture
def buffer_constants() -> Dict[str, int]:
    """Фикстура для констант буферизации.

    Returns:
        Словарь с константами буферизации.
    """
    from parser_2gis.common import (
        CSV_BATCH_SIZE,
        DEFAULT_BUFFER_SIZE,
        MERGE_BATCH_SIZE,
    )

    return {
        "DEFAULT_BUFFER_SIZE": DEFAULT_BUFFER_SIZE,
        "CSV_BATCH_SIZE": CSV_BATCH_SIZE,
        "MERGE_BATCH_SIZE": MERGE_BATCH_SIZE,
    }


# =============================================================================
# ФИКСТУРЫ ДЛЯ L3: Константы poll_interval
# =============================================================================


@pytest.fixture
def poll_constants() -> Dict[str, float]:
    """Фикстура для констант polling.

    Returns:
        Словарь с константами polling.
    """
    from parser_2gis.common import (
        DEFAULT_POLL_INTERVAL,
        EXPONENTIAL_BACKOFF_MULTIPLIER,
        MAX_POLL_INTERVAL,
    )

    return {
        "DEFAULT_POLL_INTERVAL": DEFAULT_POLL_INTERVAL,
        "MAX_POLL_INTERVAL": MAX_POLL_INTERVAL,
        "EXPONENTIAL_BACKOFF_MULTIPLIER": EXPONENTIAL_BACKOFF_MULTIPLIER,
    }


# =============================================================================
# ФИКСТУРЫ ДЛЯ L7: DeprecationWarning
# =============================================================================


@pytest.fixture
def warning_recorder() -> Generator[List[Warning], None, None]:
    """Фикстура для записи предупреждений.

    Yields:
        Список для записи предупреждений.
    """
    warnings_list: List[Warning] = []

    with patch("warnings.warn") as mock_warn:

        def record_warning(message: Warning, *args: Any, **kwargs: Any) -> None:
            warnings_list.append(message)

        mock_warn.side_effect = record_warning
        yield warnings_list


@pytest.fixture
def mock_pychrome_deprecation() -> Generator[MagicMock, None, None]:
    """Фикстура для mock DeprecationWarning от pychrome.

    Yields:
        MagicMock для имитации предупреждения.
    """
    with patch("warnings.filterwarnings") as mock_filter:
        yield mock_filter


# =============================================================================
# ФИКСТУРЫ ДЛЯ L10: async_wait_until_finished()
# =============================================================================


@pytest.fixture
def event_loop() -> Generator[Any, None, None]:
    """Фикстура для asyncio event loop.

    Yields:
        Event loop для async тестов.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    # Очистка
    loop.close()


@pytest.fixture
def async_function_success() -> Callable:
    """Фикстура для успешной async функции.

    Returns:
        Фабрика async функций.
    """

    async def success_function() -> str:
        await asyncio.sleep(0.01)
        return "success"

    return success_function


@pytest.fixture
def async_function_timeout() -> Callable:
    """Фикстура для async функции с timeout.

    Returns:
        Фабрика async функций.
    """

    async def timeout_function() -> None:
        await asyncio.sleep(10)

    return timeout_function


# =============================================================================
# ОБЩИЕ ФИКСТУРЫ
# =============================================================================


@pytest.fixture(scope="session")
def test_data_dir() -> str:
    """Фикстура для директории с тестовыми данными.

    Returns:
        Путь к директории с тестовыми данными.
    """
    return os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture
def temp_file(tmp_path: Path) -> str:
    """Фикстура для временного файла.

    Args:
        tmp_path: pytest tmp_path fixture.

    Returns:
        Путь к временному файлу.
    """
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("")
    return str(file_path)


@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Фикстура для примера конфигурации в виде словаря.

    Returns:
        Словарь с примером конфигурации.
    """
    return {
        "chrome": {
            "headless": True,
            "memory_limit": 512,
            "disable_images": True,
        },
        "parser": {
            "max_records": 10,
            "delay_between_clicks": 100,
            "skip_404_response": True,
        },
        "writer": {
            "encoding": "utf-8-sig",
            "verbose": False,
            "csv": {
                "add_rubrics": True,
                "add_comments": False,
            },
        },
    }


@pytest.fixture
def sample_org_data() -> Dict[str, Any]:
    """Фикстура для примера данных организации.

    Returns:
        Словарь с примером данных организации.
    """
    return {
        "name": "Тестовая организация",
        "address": "г. Москва, ул. Тестовая, д. 1",
        "phones": ["+7 (495) 123-45-67"],
        "emails": ["test@example.com"],
        "website": "https://example.com",
        "rubrics": ["Тестовая рубрика"],
    }


@pytest.fixture(autouse=True)
def setup_test_environment() -> Generator[None, None, None]:
    """Автоматическая фикстура для настройки тестового окружения.

    Выполняется перед каждым тестом.
    """
    # Настройка перед тестом
    os.environ["TESTING"] = "True"

    # Инициализируем logger для тестов
    import logging

    logging.getLogger("parser-2gis").setLevel(logging.DEBUG)

    yield

    # Очистка после теста
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture
def mock_response() -> Dict[str, Any]:
    """Фикстура для мок-ответа.

    Returns:
        Словарь с примером ответа.
    """
    return {"status": "success", "data": {"items": [], "total": 0}}


@pytest.fixture(params=["csv", "json", "xlsx"])
def output_format(request: pytest.FixtureRequest) -> str:
    """Фикстура для перебора форматов вывода.

    Returns:
        Формат вывода.
    """
    return request.param


@pytest.fixture(params=[True, False])
def headless_mode(request: pytest.FixtureRequest) -> bool:
    """Фикстура для перебора режимов headless.

    Returns:
        Значение headless режима.
    """
    return request.param


@pytest.fixture(params=[1, 5, 10, 50, 100])
def num_records(request: pytest.FixtureRequest) -> int:
    """Фикстура для перебора количества записей.

    Returns:
        Количество записей.
    """
    return request.param
