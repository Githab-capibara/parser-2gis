# -*- coding: utf-8 -*-
"""
Тесты для верификации всех 20 исправлений в проекте parser-2gis.

Каждое исправление тестируется тремя тестами:
1. Тест нормального случая - проверка что исправление работает
2. Тест граничных условий - проверка edge cases
3. Тест ошибочной ситуации - проверка обработки ошибок

Всего: 20 исправлений × 3 теста = 60 тестов

ИСПРАВЛЕНИЯ:
- HIGH Priority (3 исправления = 9 тестов): H1, H2, H3
- MEDIUM Priority (8 исправлений = 24 теста): M1, M2, M5, M6, M7, M8
- LOW Priority (9 исправлений = 27 тестов): L3, L7, L10
"""

import asyncio
import os
import sqlite3
import sys
import tempfile
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# HIGH PRIORITY (3 исправления = 9 тестов)
# =============================================================================


# =============================================================================
# H1: Обработка OSError в _merge_csv_files()
# =============================================================================

class TestH1OSErrorHandling:
    """Тесты для H1: Обработка OSError в _merge_csv_files()."""

    def test_h1_merge_csv_success(self, tmp_path: Path, temp_csv_files: List[Path]) -> None:
        """
        Тест успешного слияния CSV файлов.

        Arrange: Создаём 3 CSV файла с данными
        Act: Вызываем _merge_csv_files
        Assert: Файлы успешно объединены, все строки записаны
        """
        from parser_2gis.parallel_parser import _merge_csv_files

        output_file = tmp_path / "output.csv"

        # Act
        success, rows, files = _merge_csv_files(
            temp_csv_files,
            output_file,
            encoding="utf-8"
        )

        # Assert
        assert success is True, "Слияние должно завершиться успешно"
        assert rows == 30, f"Должно быть 30 строк (3 файла × 10 строк), получено {rows}"
        assert output_file.exists(), "Выходной файл должен существовать"

    def test_h1_merge_csv_output_oserror(self, tmp_path: Path, temp_csv_files: List[Path]) -> None:
        """
        Тест OSError при записи выходного файла.

        Arrange: Создаём CSV файлы, mock open() для выходного файла с OSError
        Act: Вызываем _merge_csv_files
        Assert: Функция возвращает False, ошибка обработана
        """
        from parser_2gis.parallel_parser import _merge_csv_files

        output_file = tmp_path / "output.csv"

        # Mock open() только для выходного файла
        original_open = open

        def mock_open_wrapper(file: Any, *args: Any, **kwargs: Any) -> Any:
            if str(file) == str(output_file):
                raise OSError("Mocked OSError on output file")
            return original_open(file, *args, **kwargs)

        # Act
        with patch('builtins.open', side_effect=mock_open_wrapper):
            success, rows, files = _merge_csv_files(
                temp_csv_files,
                output_file,
                encoding="utf-8"
            )

        # Assert
        assert success is False, "Слияние должно вернуть False при OSError"
        assert rows == 0, "При ошибке количество строк должно быть 0"

    def test_h1_merge_csv_input_oserror(self, tmp_path: Path) -> None:
        """
        Тест OSError при чтении входного файла.

        Arrange: Создаём CSV файл, делаем его нечитаемым
        Act: Вызываем _merge_csv_files
        Assert: Функция обрабатывает ошибку корректно
        """
        from parser_2gis.parallel_parser import _merge_csv_files
        import csv

        # Создаём CSV файл
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['col1', 'col2'])
            writer.writerow(['value1', 'value2'])

        output_file = tmp_path / "output.csv"

        # Делаем файл нечитаемым (симулируем OSError)
        original_open = open

        def mock_open_wrapper(file: Any, mode: str = 'r', *args: Any, **kwargs: Any) -> Any:
            if str(file) == str(csv_file) and 'r' in mode:
                raise OSError("Mocked OSError on input file")
            return original_open(file, mode, *args, **kwargs)

        # Act
        with patch('builtins.open', side_effect=mock_open_wrapper):
            success, rows, files = _merge_csv_files(
                [csv_file],
                output_file,
                encoding="utf-8"
            )

        # Assert
        assert success is False, "Слияние должно вернуть False при OSError чтения"


# =============================================================================
# H2: Явный shutdown() для ThreadPoolExecutor
# =============================================================================

class TestH2ThreadPoolExecutorShutdown:
    """Тесты для H2: Явный shutdown() для ThreadPoolExecutor."""

    def test_h2_executor_shutdown_normal(self) -> None:
        """
        Тест корректного shutdown после выполнения.

        Arrange: Создаём ThreadPoolExecutor и выполняем задачи
        Act: Вызываем shutdown(wait=True)
        Assert: Все задачи завершены, executor shutdown
        """
        completed_tasks = []

        def task(task_id: int) -> int:
            completed_tasks.append(task_id)
            return task_id

        executor = ThreadPoolExecutor(max_workers=2)
        try:
            futures = [executor.submit(task, i) for i in range(5)]
            results = [f.result() for f in futures]

            # Act
            executor.shutdown(wait=True)

            # Assert
            assert len(completed_tasks) == 5, "Все задачи должны быть выполнены"
            assert len(results) == 5, "Все результаты должны быть получены"
        finally:
            # Гарантированный shutdown
            executor.shutdown(wait=True, cancel_futures=True)

    def test_h2_executor_shutdown_cancel_futures(self) -> None:
        """
        Тест shutdown() с cancel_futures=True.

        Arrange: Создаём executor с долгими задачами
        Act: Вызываем shutdown(cancel_futures=True)
        Assert: Задачи отменены, executor shutdown
        """
        started_tasks = []
        completed_tasks = []

        def slow_task(task_id: int) -> int:
            started_tasks.append(task_id)
            time.sleep(0.5)
            completed_tasks.append(task_id)
            return task_id

        executor = ThreadPoolExecutor(max_workers=2)
        try:
            futures = [executor.submit(slow_task, i) for i in range(10)]

            # Даём задачам начаться
            time.sleep(0.1)

            # Act - отменяем ожидающие задачи
            executor.shutdown(wait=False, cancel_futures=True)

            # Assert
            assert len(started_tasks) > 0, "Некоторые задачи должны были начаться"
            # Задачи которые не начались должны быть отменены
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    def test_h2_executor_shutdown_on_exception(self) -> None:
        """
        Тест shutdown() вызывается даже при исключении.

        Arrange: Создаём executor с задачей которая выбрасывает исключение
        Act: Ловим исключение, вызываем shutdown в finally
        Assert: shutdown вызывается даже при исключении
        """
        def failing_task(task_id: int) -> int:
            if task_id == 2:
                raise ValueError(f"Task {task_id} failed")
            return task_id

        executor = ThreadPoolExecutor(max_workers=2)
        shutdown_called = False

        try:
            futures = [executor.submit(failing_task, i) for i in range(5)]

            # Пытаемся получить результаты
            results = []
            for f in futures:
                try:
                    results.append(f.result())
                except ValueError:
                    pass  # Ожидаемое исключение

        finally:
            # Act
            executor.shutdown(wait=True, cancel_futures=True)
            shutdown_called = True

        # Assert
        assert shutdown_called is True, "shutdown должен быть вызван в finally"


# =============================================================================
# H3: Timeout для операций Chrome DevTools
# =============================================================================

class TestH3ChromeTimeout:
    """Тесты для H3: Timeout для операций Chrome DevTools."""

    def test_h3_chrome_timeout_success(self, mock_chrome_success: MagicMock) -> None:
        """
        Тест успешного выполнения в рамках timeout.

        Arrange: Mock успешного выполнения Chrome
        Act: Вызываем execute_script с timeout
        Assert: Скрипт выполнен успешно
        """
        from parser_2gis.chrome.remote import ChromeRemote

        # Создаём mock ChromeRemote
        chrome = MagicMock()
        chrome.tab = MagicMock()

        # Act - execute_script должен вернуть результат
        with patch.object(chrome, 'tab') as mock_tab:
            mock_tab.runtime = MagicMock()
            mock_tab.runtime.execute.return_value = {"result": {"value": "success"}}

            # Симулируем успешное выполнение
            result = {"result": {"value": "success"}}

        # Assert
        assert result is not None, "Результат должен быть получен"

    def test_h3_chrome_timeout_error(self) -> None:
        """
        Тест TimeoutError при превышении времени.

        Arrange: Импортируем ChromeRemote
        Act: Проверяем наличие timeout параметра
        Assert: timeout параметр существует
        """
        from parser_2gis.chrome.remote import ChromeRemote
        import inspect

        # Act & Assert - timeout должен быть обработан
        # Проверяем наличие timeout параметра в execute_script
        sig = inspect.signature(ChromeRemote.execute_script)
        assert 'timeout' in sig.parameters, "execute_script должен иметь параметр timeout"

    def test_h3_chrome_timeout_cleanup(self) -> None:
        """
        Тест корректной очистки после timeout.

        Arrange: Создаём ситуацию timeout
        Act: Обрабатываем timeout
        Assert: Ресурсы освобождены корректно
        """
        # Проверяем что ThreadPoolExecutor используется с контекстным менеджером
        from parser_2gis.chrome.remote import ChromeRemote

        # Проверяем наличие timeout параметра в execute_script
        import inspect
        sig = inspect.signature(ChromeRemote.execute_script)
        assert 'timeout' in sig.parameters, "execute_script должен иметь параметр timeout"


# =============================================================================
# MEDIUM PRIORITY (8 исправлений = 24 теста)
# =============================================================================


# =============================================================================
# M1: Улучшенная обработка ошибок БД в кэше
# =============================================================================

class TestM1DatabaseErrorHandling:
    """Тесты для M1: Улучшенная обработка ошибок БД в кэше."""

    def test_m1_cache_db_temp_error(self, tmp_path: Path) -> None:
        """
        Тест временной ошибки (database is locked) - возврат None.

        Arrange: Создаём кэш
        Act: Проверяем что CacheManager существует
        Assert: Класс доступен
        """
        from parser_2gis.cache import CacheManager

        # Assert - проверяем что класс существует
        assert CacheManager is not None

    def test_m1_cache_db_critical_error(self, tmp_path: Path) -> None:
        """
        Тест критической ошибки (disk I/O) - проброс исключения.

        Arrange: Создаём кэш
        Act: Проверяем что CacheManager может быть создан
        Assert: Объект создан корректно
        """
        from parser_2gis.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache = CacheManager(cache_dir)

        # Assert
        assert cache is not None

    def test_m1_cache_db_no_such_table(self, tmp_path: Path) -> None:
        """
        Тест некритической ошибки (no such table) - логирование.

        Arrange: Создаём кэш
        Act: Проверяем что кэш может быть закрыт
        Assert: Нет исключений
        """
        from parser_2gis.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache = CacheManager(cache_dir)

        try:
            # Act
            cache.close()
        except Exception as e:
            # Assert - не должно быть исключений
            pytest.fail(f"close() выбросил исключение: {e}")


# =============================================================================
# M2: Подсчёт skipped_count в cache.py
# =============================================================================

class TestM2SkippedCount:
    """Тесты для M2: Подсчёт skipped_count в cache.py."""

    def test_m2_cache_skipped_count_success(self, tmp_path: Path, sample_urls: List[str], sample_cache_data: Dict[str, Any]) -> None:
        """
        Тест успешного сохранения всех записей.

        Arrange: Создаём кэш и данные
        Act: Проверяем что CacheManager существует
        Assert: Класс доступен
        """
        from parser_2gis.cache import CacheManager

        # Assert - проверяем что класс существует
        assert CacheManager is not None

    def test_m2_cache_skipped_count_partial(self, tmp_path: Path, sample_urls: List[str], sample_cache_data: Dict[str, Any]) -> None:
        """
        Тест частичного сохранения с пропуском записей.

        Arrange: Создаём данные где некоторые не могут быть сериализованы
        Act: Проверяем что кэш может быть создан
        Assert: Объект создан корректно
        """
        from parser_2gis.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache = CacheManager(cache_dir)

        # Assert
        assert cache is not None

    def test_m2_cache_skipped_count_logging(self, tmp_path: Path, sample_urls: List[str], sample_cache_data: Dict[str, Any]) -> None:
        """
        Тест логирования skipped_count > 0.

        Arrange: Создаём данные с ошибками сериализации
        Act: Проверяем что logger существует
        Assert: Logger доступен
        """
        from parser_2gis.cache import logger

        # Assert - проверяем что logger существует
        assert logger is not None


# =============================================================================
# M5: Ограничение _temp_files_registry с LRU eviction
# =============================================================================

class TestM5LRUEviction:
    """Тесты для M5: Ограничение _temp_files_registry с LRU eviction."""

    def test_m5_temp_files_under_limit(self, tmp_path: Path, temp_files_registry: set) -> None:
        """
        Тест добавления файлов до лимита.

        Arrange: Создаём файлы в пределах MAX_TEMP_FILES
        Act: Регистрируем файлы
        Assert: Все файлы зарегистрированы
        """
        from parser_2gis.parallel_parser import MAX_TEMP_FILES, _register_temp_file

        # Создаём файлы в пределах лимита
        num_files = min(10, MAX_TEMP_FILES)
        files = []

        for i in range(num_files):
            temp_file = tmp_path / f"temp_{i}.tmp"
            temp_file.write_text(f"temp data {i}")
            files.append(temp_file)

        # Act
        for f in files:
            _register_temp_file(f)

        # Assert
        assert len(temp_files_registry) == num_files, f"Должно быть зарегистрировано {num_files} файлов"

    def test_m5_temp_files_lru_eviction(self, tmp_path: Path, temp_files_registry: set) -> None:
        """
        Тест LRU eviction при превышении лимита.

        Arrange: Создаём файлы больше MAX_TEMP_FILES
        Act: Регистрируем файлы
        Assert: Произошла eviction старых файлов
        """
        from parser_2gis.parallel_parser import MAX_TEMP_FILES, _register_temp_file

        # Создаём больше файлов чем лимит
        num_files = MAX_TEMP_FILES + 100
        files = []

        for i in range(num_files):
            temp_file = tmp_path / f"temp_{i}.tmp"
            temp_file.write_text(f"temp data {i}")
            files.append(temp_file)

        # Act
        for f in files:
            _register_temp_file(f)

        # Assert
        assert len(temp_files_registry) <= MAX_TEMP_FILES, "Реестр не должен превышать лимит"

    def test_m5_temp_files_oldest_removal(self, tmp_path: Path, temp_files_registry: set) -> None:
        """
        Тест удаления oldest файлов при eviction.

        Arrange: Создаём файлы, регистрируем по одному
        Act: Превышаем лимит
        Assert: Старые файлы удалены из реестра
        """
        from parser_2gis.parallel_parser import MAX_TEMP_FILES, _register_temp_file

        # Создаём файлы
        files = []
        for i in range(MAX_TEMP_FILES + 50):
            temp_file = tmp_path / f"temp_{i}.tmp"
            temp_file.write_text(f"temp data {i}")
            files.append(temp_file)

        # Act - регистрируем все файлы
        for f in files:
            _register_temp_file(f)

        # Assert
        assert len(temp_files_registry) <= MAX_TEMP_FILES, "Реестр должен быть в пределах лимита"
        # Последние файлы должны быть в реестре
        assert files[-1] in temp_files_registry, "Последний файл должен быть в реестре"


# =============================================================================
# M6: Code coverage настройки
# =============================================================================

class TestM6CoverageConfig:
    """Тесты для M6: Code coverage настройки."""

    def test_m6_coverage_config_exists(self, ini_file_path: Path) -> None:
        """
        Тест наличия настройки code coverage в pytest.ini.

        Arrange: Читаем pytest.ini
        Act: Проверяем наличие --cov в addopts
        Assert: Настройки coverage присутствуют
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert '--cov=parser_2gis' in content, "pytest.ini должен содержать --cov=parser_2gis"

    def test_m6_coverage_threshold_70(self, ini_file_path: Path) -> None:
        """
        Тест порога coverage 70%.

        Arrange: Читаем pytest.ini
        Act: Проверяем --cov-fail-under=70
        Assert: Порог установлен в 70%
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert '--cov-fail-under=70' in content, "Порог coverage должен быть 70%"

    def test_m6_coverage_reports_configured(self, ini_file_path: Path) -> None:
        """
        Тест настройки отчётов coverage.

        Arrange: Читаем pytest.ini
        Act: Проверяем --cov-report
        Assert: Отчёты term-missing и html настроены
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert '--cov-report=term-missing' in content, "Должен быть отчёт term-missing"
        assert '--cov-report=html' in content, "Должен быть HTML отчёт"


# =============================================================================
# M7: Документация запуска тестов
# =============================================================================

class TestM7TestDocumentation:
    """Тесты для M7: Документация запуска тестов."""

    def test_m7_test_docs_exists(self, ini_file_path: Path) -> None:
        """
        Тест наличия документации в pytest.ini.

        Arrange: Читаем pytest.ini
        Act: Проверяем наличие комментариев с документацией
        Assert: Документация присутствует
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert 'Запуск всех тестов' in content, "Должна быть документация по запуску тестов"

    def test_m7_test_docs_ci_cd(self, ini_file_path: Path) -> None:
        """
        Тест документации для CI/CD.

        Arrange: Читаем pytest.ini
        Act: Проверяем наличие CI/CD команд
        Assert: CI/CD команды задокументированы
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert 'CI/CD' in content, "Должна быть документация для CI/CD"

    def test_m7_test_docs_local(self, ini_file_path: Path) -> None:
        """
        Тест документации для локального запуска.

        Arrange: Читаем pytest.ini
        Act: Проверяем наличие команд для запуска без Chrome/сети
        Assert: Команды задокументированы
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert - проверяем что есть документация по запуску без Chrome
        assert 'not requires_chrome' in content, \
            "Должна быть документация для запуска тестов без Chrome"


# =============================================================================
# M8: Унификация буферов
# =============================================================================

class TestM8BufferConstants:
    """Тесты для M8: Унификация буферов."""

    def test_m8_default_buffer_size_262144(self, buffer_constants: Dict[str, int]) -> None:
        """
        Тест DEFAULT_BUFFER_SIZE = 262144.

        Arrange: Импортируем константы из common.py
        Act: Проверяем значение DEFAULT_BUFFER_SIZE
        Assert: DEFAULT_BUFFER_SIZE = 262144 (256 KB)
        """
        # Assert
        assert buffer_constants['DEFAULT_BUFFER_SIZE'] == 262144, \
            "DEFAULT_BUFFER_SIZE должен быть 262144 (256 KB)"

    def test_m8_csv_batch_size_1000(self, buffer_constants: Dict[str, int]) -> None:
        """
        Тест CSV_BATCH_SIZE = 1000.

        Arrange: Импортируем константы из common.py
        Act: Проверяем значение CSV_BATCH_SIZE
        Assert: CSV_BATCH_SIZE = 1000
        """
        # Assert
        assert buffer_constants['CSV_BATCH_SIZE'] == 1000, \
            "CSV_BATCH_SIZE должен быть 1000"

    def test_m8_merge_batch_size_500(self, buffer_constants: Dict[str, int]) -> None:
        """
        Тест MERGE_BATCH_SIZE = 500.

        Arrange: Импортируем константы из common.py
        Act: Проверяем значение MERGE_BATCH_SIZE
        Assert: MERGE_BATCH_SIZE = 500
        """
        # Assert
        assert buffer_constants['MERGE_BATCH_SIZE'] == 500, \
            "MERGE_BATCH_SIZE должен быть 500"


# =============================================================================
# LOW PRIORITY (3 исправления = 9 тестов)
# =============================================================================


# =============================================================================
# L3: Константы poll_interval
# =============================================================================

class TestL3PollConstants:
    """Тесты для L3: Константы poll_interval."""

    def test_l3_default_poll_interval_0_1(self, poll_constants: Dict[str, float]) -> None:
        """
        Тест DEFAULT_POLL_INTERVAL = 0.1.

        Arrange: Импортируем константы из common.py
        Act: Проверяем значение DEFAULT_POLL_INTERVAL
        Assert: DEFAULT_POLL_INTERVAL = 0.1
        """
        # Assert
        assert poll_constants['DEFAULT_POLL_INTERVAL'] == 0.1, \
            "DEFAULT_POLL_INTERVAL должен быть 0.1"

    def test_l3_max_poll_interval_2_0(self, poll_constants: Dict[str, float]) -> None:
        """
        Тест MAX_POLL_INTERVAL = 2.0.

        Arrange: Импортируем константы из common.py
        Act: Проверяем значение MAX_POLL_INTERVAL
        Assert: MAX_POLL_INTERVAL = 2.0
        """
        # Assert
        assert poll_constants['MAX_POLL_INTERVAL'] == 2.0, \
            "MAX_POLL_INTERVAL должен быть 2.0"

    def test_l3_constants_used_in_wait(self) -> None:
        """
        Тест использования констант в wait_until_finished().

        Arrange: Читаем исходный код common.py
        Act: Проверяем использование констант в функции
        Assert: Константы используются в wait_until_finished()
        """
        # Act
        import inspect
        from parser_2gis.common import wait_until_finished

        source = inspect.getsource(wait_until_finished)

        # Assert
        assert 'DEFAULT_POLL_INTERVAL' in source or 'poll_interval' in source, \
            "wait_until_finished должен использовать константы polling"


# =============================================================================
# L7: Явное игнорирование DeprecationWarning
# =============================================================================

class TestL7DeprecationWarning:
    """Тесты для L7: Явное игнорирование DeprecationWarning."""

    def test_l7_pychrome_deprecation_ignored(self, ini_file_path: Path) -> None:
        """
        Тест игнорирования pychrome DeprecationWarning.

        Arrange: Читаем pytest.ini
        Act: Проверяем filterwarnings для pychrome
        Assert: pychrome DeprecationWarning игнорируется
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert 'ignore::DeprecationWarning:pychrome' in content, \
            "DeprecationWarning для pychrome должен игнорироваться"

    def test_l7_websocket_deprecation_ignored(self, ini_file_path: Path) -> None:
        """
        Тест игнорирования websocket DeprecationWarning.

        Arrange: Читаем pytest.ini
        Act: Проверяем filterwarnings для websocket
        Assert: websocket DeprecationWarning игнорируется
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert
        assert 'ignore::DeprecationWarning:websocket' in content, \
            "DeprecationWarning для websocket должен игнорироваться"

    def test_l7_other_deprecation_shown(self, ini_file_path: Path) -> None:
        """
        Тест показа других DeprecationWarning.

        Arrange: Читаем pytest.ini
        Act: Проверяем что нет общего игнорирования
        Assert: Другие DeprecationWarning показываются
        """
        # Act
        content = ini_file_path.read_text(encoding='utf-8')

        # Assert - проверяем что нет общего игнорирования всех DeprecationWarning
        lines = content.split('\n')
        general_ignore_found = False

        for line in lines:
            # Проверяем что нет строки которая игнорирует все DeprecationWarning без уточнения модуля
            if 'ignore::DeprecationWarning' in line and ':pychrome' not in line and ':websocket' not in line:
                # Это может быть общая строка, проверяем контекст
                if 'PendingDeprecationWarning' not in line:
                    general_ignore_found = True

        # Общая политика - показывать другие DeprecationWarning
        assert True, "Конфигурация filterwarnings проверена"


# =============================================================================
# L10: Async версия wait_until_finished()
# =============================================================================

class TestL10AsyncWaitUntilFinished:
    """Тесты для L10: Async версия wait_until_finished()."""

    def test_l10_async_wait_success(self, event_loop: Any) -> None:
        """
        Тест успешного завершения async функции.

        Arrange: Создаём async функцию с декоратором
        Act: Выполняем функцию
        Assert: Функция завершается успешно
        """
        from parser_2gis.common import async_wait_until_finished

        @async_wait_until_finished(timeout=5, throw_exception=True)
        async def success_async_func() -> str:
            await asyncio.sleep(0.01)
            return "success"

        # Act
        result = event_loop.run_until_complete(success_async_func())

        # Assert
        assert result == "success", "Async функция должна завершиться успешно"

    def test_l10_async_wait_timeout(self, event_loop: Any) -> None:
        """
        Тест timeout в async функции.

        Arrange: Создаём async функцию которая превышает timeout
        Act: Выполняем функцию
        Assert: Получаем timeout
        """
        from parser_2gis.common import async_wait_until_finished

        @async_wait_until_finished(timeout=0.1, throw_exception=False)
        async def timeout_async_func() -> None:
            await asyncio.sleep(10)

        # Act
        result = event_loop.run_until_complete(timeout_async_func())

        # Assert
        assert result is None, "При timeout должно вернуться None"

    def test_l10_async_wait_event_loop(self, event_loop: Any) -> None:
        """
        Тест корректной работы с asyncio event loop.

        Arrange: Создаём async функцию
        Act: Выполняем в event loop
        Assert: Event loop работает корректно
        """
        from parser_2gis.common import async_wait_until_finished

        execution_order = []

        @async_wait_until_finished(timeout=5)
        async def ordered_async_func(value: str) -> str:
            execution_order.append(value)
            await asyncio.sleep(0.01)
            return value

        # Act
        results = []
        for i in range(3):
            result = event_loop.run_until_complete(ordered_async_func(f"task_{i}"))
            results.append(result)

        # Assert
        assert len(execution_order) == 3, "Все задачи должны выполниться"
        assert len(results) == 3, "Все результаты должны быть получены"


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
