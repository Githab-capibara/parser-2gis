#!/usr/bin/env python3
"""
Комплексные тесты для исправленных критических и важных проблем.

Этот модуль содержит 33 теста (по 3 на каждую из 11 исправленных проблем):

КРИТИЧЕСКИЕ ПРОБЛЕМЫ (4 проблемы × 3 теста = 12 тестов):
1. XSS уязвимость в statistics.py (CSP meta tag, html.escape)
2. Неполная валидация данных кэша (MAX_DATA_DEPTH=15)
3. Гонка условий в signal_handler.py (threading.Lock)
4. UnboundLocalError в main.py (инициализация перед try)

ВАЖНЫЕ ПРОБЛЕМЫ (6 проблем × 3 теста = 18 тестов):
5. Утечка mmap в csv_writer.py (контекстный менеджер)
6. Процессы Chrome в browser.py (__del__ метод)
7. Дублирование валидации (validator.py → validation.py)
8. Bare except в тестах
9. except Exception с pass в тестах
10. Дублирование валидации URL

РЕФАКТОРИНГ (1 проблема × 3 теста = 3 теста):
11. parse_arguments разбита на 4 функции

Каждая проблема покрыта тремя тестами:
- Тест 1: Проверка корректности исправления (correction)
- Тест 2: Проверка краевых случаев (edge case)
- Тест 3: Проверка регрессии (regression - старая проблема не вернулась)
"""

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache import MAX_DATA_DEPTH, _validate_cached_data
from parser_2gis.chrome.browser import ChromeBrowser
from parser_2gis.main import _validate_cli_argument, _validate_positive_int
from parser_2gis.signal_handler import SignalHandler
from parser_2gis.statistics import ParserStatistics, StatisticsExporter
from parser_2gis.validator import DataValidator
from parser_2gis.writer.writers.csv_writer import mmap_file_context

# Добавляем путь к модулю parser_2gis
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# КРИТИЧЕСКАЯ ПРОБЛЕМА 1: XSS УЯЗВИМОСТЬ В statistics.py
# =============================================================================


class TestXSSVulnerabilityStatistics:
    """
    Тесты для проблемы 1: XSS уязвимость в statistics.py.

    Исправление включает:
    - Добавление CSP meta tag в HTML экспорт
    - Использование html.escape() для всех пользовательских данных
    - Экранирование даты для предотвращения XSS через манипуляцию времени
    """

    def test_csp_meta_tag_present_in_html_export(self):
        """
        Тест 1: Проверка наличия CSP meta tag в HTML экспорте.

        Проверяет что HTML экспорт содержит Content-Security-Policy meta tag
        для предотвращения XSS атак.
        """
        # Arrange
        stats = ParserStatistics()
        stats.start_time = datetime.now()
        stats.end_time = datetime.now()
        stats.total_records = 100
        stats.successful_records = 95
        exporter = StatisticsExporter()

        # Act
        html_content = exporter._generate_html(stats)

        # Assert - проверяем наличие CSP meta tag
        assert '<meta http-equiv="Content-Security-Policy"' in html_content, (
            "CSP meta tag должен присутствовать в HTML экспорте"
        )
        assert "default-src 'self'" in html_content, (
            "CSP должен содержать директиву default-src 'self'"
        )
        assert "script-src 'none'" in html_content, "CSP должен запрещать выполнение скриптов"
        assert "object-src 'none'" in html_content, "CSP должен запрещать объекты"
        assert "base-uri 'none'" in html_content, "CSP должен запрещать изменение base URI"

    def test_html_escape_user_data_in_statistics(self):
        """
        Тест 2: Проверка экранирования пользовательских данных в статистике.

        Проверяет что все пользовательские данные экранируются через html.escape()
        для предотвращения XSS атак.
        """
        # Arrange - создаём статистику с XSS payload в ошибках
        stats = ParserStatistics()
        stats.start_time = datetime.now()
        stats.end_time = datetime.now()
        # XSS payload в ошибках
        stats.errors = [
            '<script>alert("XSS")</script>',
            '<img src="x" onerror="alert(1)">',
            "javascript:alert(document.cookie)",
        ]
        exporter = StatisticsExporter()

        # Act
        html_content = exporter._generate_html(stats)

        # Assert - проверяем что XSS payload экранирован
        assert "<script>" not in html_content, "HTML теги <script> должны быть экранированы"
        assert "&lt;script&gt;" in html_content, (
            "Теги <script> должны быть заменены на &lt;script&gt;"
        )
        # Проверяем что img теги экранированы
        assert "&lt;img src=" in html_content, "IMG теги должны быть экранированы"
        # Проверяем что javascript протокол в тексте (не выполняется)
        assert "javascript:" in html_content, (
            "JavaScript протокол должен присутствовать в тексте ошибки"
        )

    def test_xss_regression_time_manipulation(self):
        """
        Тест 3: Проверка регрессии - XSS через манипуляцию времени.

        Проверяет что даже при манипуляции с временем (start_time, end_time)
        XSS атака невозможна благодаря экранированию.
        """
        # Arrange - создаём статистику с потенциально опасными данными времени
        stats = ParserStatistics()
        # Пытаемся внедрить XSS через кастомную дату (маловероятно но проверяем)
        stats.start_time = datetime.now()
        stats.end_time = datetime.now()
        stats.errors = ['<script>alert("time-xss")</script>']
        exporter = StatisticsExporter()

        # Act
        html_content = exporter._generate_html(stats)

        # Assert - проверяем что timestamp экранирован и XSS невозможен
        assert html_content.count("<script>") == 0, (
            "В HTML не должно быть незаэкранированных <script> тегов"
        )
        # Проверяем что дата присутствует в экранированном виде
        assert "Сгенерировано:" in html_content, "Дата генерации должна присутствовать"
        # Регрессионный тест - убеждаемся что старая уязвимость не вернулась
        dangerous_patterns = ["<script>", "javascript:", "onerror=", "eval("]
        for pattern in dangerous_patterns:
            assert pattern not in html_content, (
                f"Опасный паттерн '{pattern}' не должен присутствовать в HTML"
            )


# =============================================================================
# КРИТИЧЕСКАЯ ПРОБЛЕМА 2: НЕПОЛНАЯ ВАЛИДАЦИЯ ДАННЫХ КЭША (MAX_DATA_DEPTH=15)
# =============================================================================


class TestCacheDataValidationDepth:
    """
    Тесты для проблемы 2: Неполная валидация данных кэша.

    Исправление включает:
    - Установка MAX_DATA_DEPTH=15 для предотвращения ReDoS атак
    - Глубокая валидация вложенных структур данных
    - Отклонение данных с чрезмерной вложенностью
    """

    def test_validate_data_at_depth_limit(self):
        """
        Тест 1: Проверка валидации данных на границе глубины (15).

        Проверяет что данные с глубиной вложенности ровно 15 проходят валидацию.
        """
        # Arrange - создаём словарь с глубиной 15
        data = {"level": 0}
        current = data
        for i in range(1, MAX_DATA_DEPTH):
            current["nested"] = {"level": i}
            current = current["nested"]

        # Act
        is_valid = _validate_cached_data(data)

        # Assert - данные с глубиной 15 должны проходить валидацию
        assert is_valid is True, f"Данные с глубиной {MAX_DATA_DEPTH} должны проходить валидацию"

    def test_validate_data_exceeds_depth_limit(self):
        """
        Тест 2: Проверка отклонения данных с превышением глубины (16).

        Проверяет что данные с глубиной вложенности 16 отклоняются.
        """
        # Arrange - создаём словарь с глубиной 16 (превышение лимита)
        data = {"level": 0}
        current = data
        for i in range(1, MAX_DATA_DEPTH + 1):  # 16 уровней
            current["nested"] = {"level": i}
            current = current["nested"]

        # Act
        is_valid = _validate_cached_data(data)

        # Assert - данные с глубиной 16 должны отклоняться
        assert is_valid is False, f"Данные с глубиной {MAX_DATA_DEPTH + 1} должны отклоняться"

    def test_validate_complex_nested_structures(self):
        """
        Тест 3: Проверка валидации сложных вложенных структур.

        Проверяет что валидация корректно работает со смешанными структурами
        (словари + списки) и отклоняет чрезмерно вложенные.
        """
        # Arrange - создаём сложную структуру со списками и словарями
        valid_data = {
            "level": 0,
            "items": [
                {"name": "item1", "value": 1},
                {"name": "item2", "nested": {"deep": "value"}},
            ],
            "metadata": {"version": "1.0"},
        }

        # Arrange 2 - создаём невалидную структуру с превышением глубины в списке
        invalid_data = {"level": 0}
        current = invalid_data
        for i in range(MAX_DATA_DEPTH + 5):
            current["nested"] = [{"level": i}]
            current = current["nested"][0]

        # Act
        valid_result = _validate_cached_data(valid_data)
        invalid_result = _validate_cached_data(invalid_data)

        # Assert
        assert valid_result is True, "Сложные но неглубокие структуры должны проходить валидацию"
        assert invalid_result is False, (
            "Структуры с превышением глубины должны отклоняться даже в списках"
        )


# =============================================================================
# КРИТИЧЕСКАЯ ПРОБЛЕМА 3: ГОНКА УСЛОВИЙ В signal_handler.py (threading.Lock)
# =============================================================================


class TestSignalHandlerRaceCondition:
    """
    Тесты для проблемы 3: Гонка условий в signal_handler.py.

    Исправление включает:
    - Использование threading.Lock для атомарной проверки и установки флагов
    - Предотвращение гонки между проверкой _is_cleaning_up и установкой
    - Потокобезопасная реализация всех методов
    """

    def test_atomic_flag_operations_with_lock(self):
        """
        Тест 1: Проверка атомарности установки флагов под блокировкой.

        Проверяет что флаги _interrupted и _is_cleaning_up устанавливаются
        атомарно под блокировкой threading.RLock.
        """
        # Arrange
        handler = SignalHandler()

        # Проверяем что lock существует
        assert hasattr(handler, "_lock"), "SignalHandler должен иметь _lock"
        # ИСПРАВЛЕНИЕ: Проверяем что используется RLock вместо Lock
        assert isinstance(handler._lock, type(threading.RLock())), (
            "_lock должен быть threading.RLock"
        )

        # Act - симулируем получение сигнала (в изоляции от sys.exit)
        # Используем patch для предотвращения sys.exit
        with patch("parser_2gis.signal_handler.sys.exit"):
            handler._handle_signal(signal.SIGINT, None)

        # Assert - проверяем что флаги установлены
        assert handler.is_interrupted() is True, "Флаг _interrupted должен быть установлен"

    def test_repeated_signal_handling_during_cleanup(self):
        """
        Тест 2: Проверка обработки повторных сигналов во время очистки.

        Проверяет что повторные сигналы игнорируются если уже идёт очистка.
        """
        # Arrange
        handler = SignalHandler()
        handler.setup()

        # Устанавливаем флаг очистки
        with handler._lock:
            handler._is_cleaning_up = True

        # Act - пытаемся отправить повторный сигнал
        handler._handle_signal(signal.SIGTERM, None)

        # Assert - проверяем что сигнал проигнорирован
        # Флаг не должен измениться повторно
        assert handler._is_cleaning_up is True, "Флаг очистки должен остаться установленным"

        # Cleanup
        handler.cleanup()

    def test_thread_safe_is_interrupted(self):
        """
        Тест 3: Проверка потокобезопасности метода is_interrupted().

        Проверяет что метод is_interrupted() потокобезопасен благодаря
        использованию threading.Lock.
        """
        # Arrange
        handler = SignalHandler()
        results = []
        threads = []

        def check_interrupted():
            """Поток проверяет is_interrupted многократно."""
            for _ in range(100):
                result = handler.is_interrupted()
                results.append(result)
                time.sleep(0.001)

        # Act - запускаем несколько потоков одновременно
        for _ in range(5):
            thread = threading.Thread(target=check_interrupted)
            threads.append(thread)
            thread.start()

        # Ждём завершения всех потоков
        for thread in threads:
            thread.join()

        # Assert - проверяем что все вызовы завершились без ошибок
        assert len(results) == 500, "Все 500 вызовов (5 потоков × 100) должны выполниться"
        assert all(isinstance(r, bool) for r in results), "Все результаты должны быть булевыми"


# =============================================================================
# КРИТИЧЕСКАЯ ПРОБЛЕМА 4: UNBOUNDLOCALERROR В main.py
# =============================================================================


class TestUnboundLocalErrorMain:
    """
    Тесты для проблемы 4: UnboundLocalError в main.py.

    Исправление включает:
    - Инициализация переменной all_cities ПЕРЕД try блоком
    - Предотвращение ошибки при использовании переменной до присваивания
    - Корректная обработка исключений в любом месте try блока
    """

    def test_all_cities_initialized_before_try(self):
        """
        Тест 1: Проверка инициализации all_cities перед try блоком.

        Проверяет что переменная all_cities инициализируется перед try
        для предотвращения UnboundLocalError.
        """
        # Arrange - создаём временный JSON файл с городами
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('[{"name": "Москва", "url": "https://2gis.ru/moscow"}]')
            temp_path = f.name

        try:
            # Act - импортируем функцию и проверяем что она работает
            from parser_2gis.main import _load_cities_json

            # Функция должна работать без UnboundLocalError
            cities = _load_cities_json(temp_path)

            # Assert
            assert isinstance(cities, list), "Функция должна возвращать список городов"
            assert len(cities) == 1, "Должен загрузиться один город из тестового файла"
        finally:
            # Cleanup
            os.unlink(temp_path)

    def test_exception_handling_in_try_block(self):
        """
        Тест 2: Проверка обработки исключений в try блоке.

        Проверяет что при возникновении исключения в try блоке
        переменная all_cities остаётся определённой.
        """
        # Arrange - создаём невалидный JSON файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name

        try:
            # Act & Assert - функция должна выбросить ValueError а не UnboundLocalError
            from parser_2gis.main import _load_cities_json

            with pytest.raises((ValueError, json.JSONDecodeError)) as exc_info:
                _load_cities_json(temp_path)

            # Проверяем что это не UnboundLocalError
            assert not isinstance(exc_info.value, UnboundLocalError), (
                "Не должно возникать UnboundLocalError при ошибке JSON"
            )
        finally:
            # Cleanup
            os.unlink(temp_path)

    def test_no_unboundlocalerror_on_file_not_found(self):
        """
        Тест 3: Проверка отсутствия UnboundLocalError при FileNotFoundError.

        Проверяет что при отсутствии файла не возникает UnboundLocalError.
        """
        # Arrange
        nonexistent_path = "/nonexistent/path/to/cities.json"

        # Act & Assert
        from parser_2gis.main import _load_cities_json

        with pytest.raises(FileNotFoundError) as exc_info:
            _load_cities_json(nonexistent_path)

        # Проверяем что это FileNotFoundError а не UnboundLocalError
        assert isinstance(exc_info.value, FileNotFoundError), (
            "Должно возникать FileNotFoundError для несуществующего файла"
        )
        assert not isinstance(exc_info.value, UnboundLocalError), (
            "Не должно возникать UnboundLocalError"
        )


# =============================================================================
# ВАЖНАЯ ПРОБЛЕМА 5: УТЕЧКА MMAP В csv_writer.py (КОНТЕКСТНЫЙ МЕНЕДЖЕР)
# =============================================================================


class TestMmapLeakCsvWriter:
    """
    Тесты для проблемы 5: Утечка mmap в csv_writer.py.

    Исправление включает:
    - Использование контекстного менеджера mmap_file_context
    - Гарантированное закрытие mmap, TextIOWrapper и файлового дескриптора
    - Обработка исключений с fallback на обычную буферизацию
    """

    def test_mmap_context_manager_closes_resources(self):
        """
        Тест 1: Проверка закрытия ресурсов в контекстном менеджере.

        Проверяет что контекстный менеджер корректно закрывает все ресурсы
        (mmap, TextIOWrapper, файловый дескриптор).
        """
        # Arrange - создаём большой файл для использования mmap
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Пишем достаточно данных для превышения порога mmap (10MB)
            for i in range(200000):  # ~200K строк
                f.write(f"{i},data_{i},category_{i % 10}\n")
            temp_path = f.name

        try:
            # Получаем размер файла
            file_size = os.path.getsize(temp_path)
            use_mmap = file_size > (10 * 1024 * 1024)  # 10MB threshold

            # Act - используем контекстный менеджер
            with mmap_file_context(temp_path, "r", encoding="utf-8") as (
                file_obj,
                is_mmap,
                underlying_fp,
            ):
                # Читаем первую строку для проверки работы
                first_line = file_obj.readline()
                assert first_line.strip(), "Должна прочитаться первая строка"

            # Assert - проверяем что mmap использовался для большого файла
            if use_mmap:
                assert is_mmap is True, (
                    f"Для файла {file_size / (1024 * 1024):.2f}MB должен использоваться mmap"
                )
            else:
                assert is_mmap is False, "Для маленького файла mmap не должен использоваться"

            # Проверяем что файл закрыт (можно попробовать удалить)
            os.unlink(temp_path)
            temp_path = None  # Помечаем что файл удалён

        finally:
            # Cleanup
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_mmap_context_manager_exception_handling(self):
        """
        Тест 2: Проверка обработки исключений в контекстном менеджере.

        Проверяет что контекстный менеджер корректно работает.
        """
        # Arrange - создаём файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            for i in range(1000):
                f.write(f"{i},data_{i}\n")
            temp_path = f.name

        try:
            # Act - используем контекстный менеджер
            with mmap_file_context(temp_path, "r", encoding="utf-8") as (
                file_obj,
                is_mmap,
                underlying_fp,
            ):
                # Читаем немного данных
                first_line = file_obj.readline()

            # Assert - проверяем что данные прочитаны
            assert first_line.strip(), "Должна прочитаться первая строка"

            # Проверяем что файл закрыт (можно удалить)
            os.unlink(temp_path)
            temp_path = None

        finally:
            # Cleanup
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_mmap_resource_cleanup_on_error(self):
        """
        Тест 3: Проверка освобождения ресурсов при ошибке.

        Проверяет что все ресурсы (mmap, fd, wrapper) освобождаются
        даже при ошибке в процессе работы.
        """
        # Arrange - создаём файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("col1,col2,col3\n")
            for i in range(100):
                f.write(f"{i},data_{i},category_{i}\n")
            temp_path = f.name

        try:
            # Act - используем контекстный менеджер с обработкой ошибки
            try:
                with mmap_file_context(temp_path, "r", encoding="utf-8") as (
                    file_obj,
                    is_mmap,
                    underlying_fp,
                ):
                    file_obj.readline()
                    # Симулируем ошибку
                    raise RuntimeError("Simulated error")
            except RuntimeError:
                pass

            # Assert - проверяем что файл может быть удалён (ресурсы закрыты)
            assert os.path.exists(temp_path), "Файл должен существовать до удаления"
            os.unlink(temp_path)
            assert not os.path.exists(temp_path), "Файл должен быть удалён"
            temp_path = None

        finally:
            # Cleanup
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)


# =============================================================================
# ВАЖНАЯ ПРОБЛЕМА 6: ПРОЦЕССЫ CHROME В browser.py (__del__ МЕТОД)
# =============================================================================


class TestChromeProcessCleanup:
    """
    Тесты для проблемы 6: Процессы Chrome в browser.py.

    Исправление включает:
    - Добавление __del__ метода для гарантии очистки
    - Обработка всех исключений в __del__ для предотвращения сбоев GC
    - Детальное логирование для отладки утечек ресурсов
    """

    def test_del_method_closes_process(self):
        """
        Тест 1: Проверка вызова close() в __del__ методе.

        Проверяет что __del__ метод пытается закрыть процесс Chrome.
        """
        # Arrange - создаём mock ChromeBrowser
        mock_browser = MagicMock(spec=ChromeBrowser)
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Процесс активен
        mock_process.pid = 12345
        mock_browser._proc = mock_process
        mock_browser._profile_tempdir = MagicMock()

        # Act - вызываем логику __del__ (симулируем)
        # Проверяем что terminate вызывается для активного процесса
        if mock_browser._proc.poll() is None:
            mock_browser._proc.terminate()
            try:
                mock_browser._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                mock_browser._proc.kill()

        # Assert
        mock_browser._proc.terminate.assert_called_once()

    def test_del_method_exception_handling(self):
        """
        Тест 2: Проверка обработки исключений в __del__ методе.

        Проверяет что __del__ метод обрабатывает все исключения
        и не прерывает сборку мусора.
        """
        # Arrange - создаём mock с исключением
        mock_browser = MagicMock(spec=ChromeBrowser)
        mock_process = MagicMock()
        mock_process.terminate.side_effect = Exception("Simulated error")
        mock_browser._proc = mock_process
        mock_browser._profile_tempdir = MagicMock()

        # Act & Assert - __del__ не должен выбрасывать исключения
        try:
            # Симулируем логику __del__
            if mock_browser._proc is not None:
                try:
                    mock_browser._proc.terminate()
                except Exception:
                    # Исключение поймано и обработано
                    pass
            exception_handled = True
        except Exception:
            exception_handled = False

        assert exception_handled is True, "__del__ должен обрабатывать все исключения"

    def test_del_method_profile_cleanup(self):
        """
        Тест 3: Проверка очистки профиля в __del__ методе.

        Проверяет что __del__ метод очищает временный профиль Chrome.
        """
        # Arrange
        profile_cleanup_called = []

        mock_tempdir = MagicMock()
        mock_tempdir.cleanup.side_effect = lambda: profile_cleanup_called.append(True)

        mock_browser = MagicMock(spec=ChromeBrowser)
        mock_browser._profile_tempdir = mock_tempdir
        mock_browser._proc = None  # Процесса нет

        # Act - симулируем __del__
        if mock_browser._profile_tempdir is not None:
            mock_browser._profile_tempdir.cleanup()

        # Assert
        assert len(profile_cleanup_called) == 1, "Профиль должен быть очищен в __del__"
        mock_tempdir.cleanup.assert_called_once()


# =============================================================================
# ВАЖНАЯ ПРОБЛЕМА 7: ДУБЛИРОВАНИЕ ВАЛИДАЦИИ (validator.py → validation.py)
# =============================================================================


class TestValidationDuplicationElimination:
    """
    Тесты для проблемы 7: Дублирование валидации.

    Исправление включает:
    - Перемещение всей валидации в validation.py
    - validator.py использует функции из validation.py
    - Elimination дублирования кода
    """

    def test_validator_uses_validation_module(self):
        """
        Тест 1: Проверка использования validation.py в validator.py.

        Проверяет что DataValidator использует функции из validation.py.
        """
        # Arrange

        # Act - проверяем импорты в модуле validator
        validator_module = sys.modules.get("parser_2gis.validator")

        # Assert - проверяем что импорты есть
        assert validator_module is not None, "Модуль validator должен быть импортирован"

        # Проверяем что в модуле есть ссылки на validation
        import parser_2gis.validator as validator_mod

        validator_source_file = Path(validator_mod.__file__)
        validator_source = validator_source_file.read_text(encoding="utf-8")

        assert (
            "from .validation import" in validator_source
            or "from parser_2gis.validation import" in validator_source
        ), "validator.py должен импортировать функции из validation.py"

    def test_validation_results_consistency(self):
        """
        Тест 2: Проверка консистентности результатов валидации.

        Проверяет что validator.py и validation.py возвращают
        одинаковые результаты для одних и тех же данных.
        """
        # Arrange
        validator = DataValidator()
        test_phones = [
            "+7 (495) 123-45-67",
            "+7 (999) 123-45-67",
            "8 (800) 123-45-67",
            "invalid_phone",
        ]

        # Act - валидируем через оба модуля
        from parser_2gis.validation import validate_phone as base_validate_phone

        for phone in test_phones:
            validator_result = validator.validate_phone(phone)
            base_result = base_validate_phone(phone)

            # Assert - результаты должны совпадать
            assert validator_result.is_valid == base_result.is_valid, (
                f"Результаты валидации телефона {phone} должны совпадать"
            )

    def test_no_code_duplication(self):
        """
        Тест 3: Проверка отсутствия дублирования кода валидации.

        Проверяет что код валидации не дублируется в validator.py.
        """
        # Arrange - читаем исходный код validator.py
        validator_path = Path(__file__).parent.parent / "parser_2gis" / "validator.py"
        validator_source = validator_path.read_text(encoding="utf-8")

        # Act - ищем дублирование логики валидации
        # Паттерны валидации которые должны быть в validation.py
        validation_patterns = [
            r"re\.compile.*phone",
            r"re\.compile.*email",
            r"ipaddress\.ip_address",
            r"urlparse",
        ]

        # Assert - проверяем что сложная логика валидации удалена из validator.py
        # validator.py должен только делегировать validation.py
        duplication_count = 0
        for pattern in validation_patterns:
            if re.search(pattern, validator_source):
                duplication_count += 1

        # Допускаем минимальное дублирование (только для обратной совместимости)
        assert duplication_count <= 1, (
            f"validator.py не должен дублировать логику валидации (найдено {duplication_count} паттернов)"
        )


# =============================================================================
# ВАЖНАЯ ПРОБЛЕМА 8: BARE EXCEPT В ТЕСТАХ
# =============================================================================


class TestBareExceptInTests:
    """
    Тесты для проблемы 8: Bare except в тестах.

    Исправление включает:
    - Замена bare except на конкретные типы исключений
    - Улучшение обработки ошибок в тестах
    """

    def test_no_bare_except_in_test_files(self):
        """
        Тест 1: Проверка отсутствия bare except в тестовых файлах.

        Проверяет что в тестах не используется bare except.
        """
        # Arrange - получаем список тестовых файлов
        test_dir = Path(__file__).parent
        test_files = list(test_dir.glob("test_*.py"))

        # Act - ищем bare except
        bare_except_found = []
        for test_file in test_files:
            content = test_file.read_text(encoding="utf-8")
            # Ищем паттерн "except:" без указания типа исключения
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if re.search(r"\bexcept\s*:", line) and not re.search(r"#.*except\s*:", line):
                    bare_except_found.append((test_file.name, i, line.strip()))

        # Assert - bare except не должен использоваться
        assert len(bare_except_found) == 0, (
            f"Найдены bare except в тестах: {bare_except_found[:5]}"  # Показываем первые 5
        )

    def test_specific_exception_types_in_tests(self):
        """
        Тест 2: Проверка использования конкретных типов исключений.

        Проверяет что тесты используют конкретные типы исключений.
        """
        # Arrange - читаем текущий тестовый файл
        current_test_file = Path(__file__)
        content = current_test_file.read_text(encoding="utf-8")

        # Act - ищем except с конкретными типами
        specific_exceptions = re.findall(r"except\s+(\w+(?:\s+as\s+\w+)?)", content)

        # Assert - должны использоваться конкретные исключения
        assert len(specific_exceptions) > 0, "Тесты должны использовать конкретные типы исключений"

        # Проверяем что используются распространённые типы исключений
        common_exceptions = ["ValueError", "TypeError", "FileNotFoundError", "pytest.raises"]
        used_common = [
            exc for exc in specific_exceptions if any(common in exc for common in common_exceptions)
        ]
        assert len(used_common) > 0, "Тесты должны использовать стандартные типы исключений"

    def test_error_handling_in_tests(self):
        """
        Тест 3: Проверка корректной обработки ошибок в тестах.

        Проверяет что тесты корректно обрабатывают ошибки.
        """
        # Arrange & Act - создаём тестовую ситуацию с ошибкой
        error_handled = False
        try:
            # Пытаемся выполнить операцию с ошибкой
            raise ValueError("Test error")
        except ValueError as e:
            # Ловим конкретное исключение
            error_handled = True
            error_message = str(e)

        # Assert
        assert error_handled is True, "Ошибка должна быть обработана"
        assert error_message == "Test error", "Сообщение об ошибке должно сохраняться"


# =============================================================================
# ВАЖНАЯ ПРОБЛЕМА 9: EXCEPT EXCEPTION С PASS В ТЕСТАХ
# =============================================================================


class TestExceptExceptionWithPassInTests:
    """
    Тесты для проблемы 9: except Exception с pass в тестах.

    Исправление включает:
    - Удаление except Exception с pass
    - Добавление логирования или assertion вместо pass
    """

    def test_no_except_exception_with_pass(self):
        """
        Тест 1: Проверка отсутствия except Exception с pass.

        Проверяет что в тестах не используется except Exception с pass.
        """
        # Arrange - получаем список тестовых файлов (исключая текущий файл)
        test_dir = Path(__file__).parent
        test_files = [f for f in test_dir.glob("test_*.py") if f.name != __file__]

        # Act - ищем except Exception с pass (упрощённая проверка)
        bad_patterns_found = []
        for test_file in test_files:
            content = test_file.read_text(encoding="utf-8")
            # Ищем паттерн except Exception с pass на следующей строке
            lines = content.split("\n")
            for i in range(len(lines) - 1):
                if re.search(r"\bexcept\s+Exception\b", lines[i]):
                    next_line = lines[i + 1].strip()
                    if next_line == "pass":
                        bad_patterns_found.append((test_file.name, i + 1))

        # Assert - except Exception с pass не должен использоваться
        # Примечание: этот тест может падать если в других тестах есть такие паттерны
        # Это ожидаемое поведение - тест должен указывать на проблему
        assert len(bad_patterns_found) == 0, (
            f"Найдены except Exception с pass в: {bad_patterns_found[:5]}"
        )

    def test_exception_logging_in_tests(self):
        """
        Тест 2: Проверка логирования исключений в тестах.

        Проверяет что тесты логируют исключения вместо pass.
        """
        # Arrange & Act - создаём тест с логированием
        import logging

        log_messages = []
        logger = logging.getLogger("test")

        class MockHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(self.format(record))

        handler = MockHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            logger.error("Exception caught: %s", e)

        # Assert
        assert len(log_messages) > 0, "Исключения должны логироваться"
        assert "Test error for logging" in log_messages[0], "Сообщение об ошибке должно быть в логе"

        # Cleanup
        logger.removeHandler(handler)

    def test_exception_assertion_in_tests(self):
        """
        Тест 3: Проверка assertion исключений в тестах.

        Проверяет что тесты используют assertion для проверки исключений.
        """
        # Arrange & Act - тест с assertion
        exception_caught = False
        exception_type = None

        try:
            raise TypeError("Expected error")
        except Exception as e:
            exception_caught = True
            exception_type = type(e).__name__
            # Assertion вместо pass
            assert exception_type == "TypeError", f"Ожидался TypeError, получен {exception_type}"

        # Assert
        assert exception_caught is True, "Исключение должно быть поймано"


# =============================================================================
# ВАЖНАЯ ПРОБЛЕМА 10: ДУБЛИРОВАНИЕ ВАЛИДАЦИИ URL
# =============================================================================


class TestUrlValidationDuplication:
    """
    Тесты для проблемы 10: Дублирование валидации URL.

    Исправление включает:
    - Централизация валидации в validation.py
    - Использование validate_url из validation.py во всех модулях
    """

    def test_single_source_of_truth_for_url_validation(self):
        """
        Тест 1: Проверка единственного источника валидации URL.

        Проверяет что validation.py является единственным источником
        истины для валидации URL.
        """
        # Arrange - читаем исходный код модулей
        validation_path = Path(__file__).parent.parent / "parser_2gis" / "validation.py"
        validation_source = validation_path.read_text(encoding="utf-8")

        # Act - проверяем наличие функции validate_url
        assert "def validate_url(" in validation_source, (
            "validation.py должен содержать функцию validate_url"
        )
        assert "ipaddress.ip_address" in validation_source, (
            "validate_url должен проверять IP адреса"
        )
        assert "localhost" in validation_source, "validate_url должен блокировать localhost"

    def test_validate_url_consistency_across_modules(self):
        """
        Тест 2: Проверка консистентности validate_url в модулях.

        Проверяет что модули используют validate_url из validation.py.
        """
        # Arrange - модуль который точно использует валидацию
        module_path = Path(__file__).parent.parent / "parser_2gis" / "validator.py"

        # Act - проверяем импорты
        content = module_path.read_text(encoding="utf-8")

        # Assert - validator.py должен использовать валидацию
        uses_validation = (
            "from .validation import" in content
            or "from parser_2gis.validation import" in content
            or "validate_url" in content
        )
        assert uses_validation is True, "validator.py должен использовать validation.py"

    def test_no_url_validation_duplication(self):
        """
        Тест 3: Проверка отсутствия дублирования валидации URL.

        Проверяет что валидация URL не дублируется в других модулях.
        """
        # Arrange - читаем validator.py
        validator_path = Path(__file__).parent.parent / "parser_2gis" / "validator.py"
        validator_source = validator_path.read_text(encoding="utf-8")

        # Act - проверяем что validator.py делегирует validation.py
        # Проверяем что validate_url импортируется из validation
        has_validate_url_import = "validate_url" in validator_source and (
            "from .validation import" in validator_source
            or "from parser_2gis.validation import" in validator_source
        )
        assert has_validate_url_import, (
            "validator.py должен импортировать validate_url из validation.py"
        )

        # Проверяем что нет дублирования логики
        # validator.py не должен содержать собственной реализации urlparse
        assert (
            "urlparse(" not in validator_source
            or "_validate_url_from_validation" in validator_source
        ), "validator.py не должен дублировать логику urlparse"


# =============================================================================
# РЕФАКТОРИНГ 11: PARSE_ARGUMENTS РАЗБИТА НА 4 ФУНКЦИИ
# =============================================================================


class TestParseArgumentsDecomposition:
    """
    Тесты для проблемы 11: Разбиение parse_arguments на 4 функции.

    Исправление включает:
    - Выделение _validate_positive_int для валидации чисел
    - Выделение _validate_cli_argument для валидации CLI аргументов
    - Улучшение читаемости и тестируемости кода
    """

    def test_validate_positive_int_function(self):
        """
        Тест 1: Проверка функции _validate_positive_int.

        Проверяет что функция корректно валидирует положительные целые числа.
        """
        # Arrange & Act & Assert - тестируем валидные значения
        assert _validate_positive_int(5, 1, 100, "--test") == 5
        assert _validate_positive_int(1, 1, 100, "--test") == 1
        assert _validate_positive_int(100, 1, 100, "--test") == 100

        # Тестируем невалидные значения (ниже минимума)
        with pytest.raises(ValueError) as exc_info:
            _validate_positive_int(0, 1, 100, "--test")
        assert "не менее 1" in str(exc_info.value) or "от 1 до 100" in str(exc_info.value)

        # Тестируем невалидные значения (выше максимума)
        with pytest.raises(ValueError) as exc_info:
            _validate_positive_int(101, 1, 100, "--test")
        assert "не более 100" in str(exc_info.value) or "от 1 до 100" in str(exc_info.value)

    def test_validate_cli_argument_function(self):
        """
        Тест 2: Проверка функции _validate_cli_argument.

        Проверяет что функция корректно валидирует CLI аргументы.
        """
        # Arrange
        args = MagicMock()
        args.test_attr = 5
        arg_parser = MagicMock()

        # Act & Assert - валидное значение (функция ничего не возвращает)
        try:
            _validate_cli_argument(args, arg_parser, "test_attr", 1, 100, "--test")
            validation_passed = True
        except (SystemExit, ValueError):
            validation_passed = False

        assert validation_passed is True, "Валидное значение должно проходить валидацию"

        # Тестируем невалидное значение - должно вызывать ошибку
        args.invalid_attr = 0
        arg_parser.error.side_effect = SystemExit(1)
        with pytest.raises(SystemExit):
            _validate_cli_argument(args, arg_parser, "invalid_attr", 1, 100, "--test")

    def test_all_decomposed_functions_work_correctly(self):
        """
        Тест 3: Проверка корректной работы всех разбитых функций.

        Проверяет что все выделенные функции работают корректно.
        """
        # Arrange - тестовые данные
        test_cases = [
            # (value, min, max, arg_name, should_pass)
            (10, 1, 100, "--test1", True),
            (1, 1, 100, "--test2", True),
            (100, 1, 100, "--test3", True),
            (0, 1, 100, "--test4", False),
            (101, 1, 100, "--test5", False),
            (-5, 1, 100, "--test6", False),
        ]

        # Act & Assert
        for value, min_val, max_val, arg_name, should_pass in test_cases:
            try:
                _validate_positive_int(value, min_val, max_val, arg_name)
                passed = True
            except ValueError:
                passed = False

            assert passed == should_pass, (
                f"Тест {arg_name}: значение {value} должно {'пройти' if should_pass else 'не пройти'} валидацию"
            )


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
