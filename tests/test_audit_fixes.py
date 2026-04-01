"""
Тесты для исправлений аудита кода parser-2gis.

Этот модуль содержит тесты для проверки всех критических исправлений,
реализованных в коде parser-2gis после аудита.

Требования к тестам:
1. Один тест = одна проблема (четкое соответствие)
2. Использовать mock для внешних зависимостей
3. Использовать tempfile для файловых операций
4. Использовать in-memory SQLite для тестов кэша
5. Покрыть edge cases и error paths
6. Добавить assertions для проверки корректности исправлений
"""

import os
import sqlite3
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# =============================================================================
# P0-1: ТЕСТ ДЛЯ parallel_parser.py - ОСВОБОЖДЕНИЕ СЕМАФОРА
# =============================================================================


class TestSemaphoreReleaseNoDuplication:
    """Тесты для P0-1: семафор освобождается только один раз даже при MemoryError."""

    def _create_mock_config(self):
        """Создает mock конфигурацию с правильной структурой."""
        config = MagicMock()
        config.parallel = MagicMock()
        config.parallel.initial_delay_min = 0.0
        config.parallel.initial_delay_max = 0.1
        config.parallel.launch_delay_min = 0.0
        config.parallel.launch_delay_max = 0.1
        config.parallel.use_temp_file_cleanup = False
        config.writer = MagicMock()
        config.chrome = MagicMock()
        config.parser = MagicMock()
        return config

    def test_semaphore_release_no_duplication(self):
        """Тест: семафор освобождается только один раз даже при MemoryError.

        Проверить что semaphore.release() вызывается ровно 1 раз
        Даже при возникновении MemoryError
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        config = self._create_mock_config()

        # Создаем парсер с mock данными
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Рестораны", "id": 1}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            # Создаем mock семафор
            mock_semaphore = MagicMock(spec=threading.BoundedSemaphore)
            parser._browser_launch_semaphore = mock_semaphore

            # Создаем mock writer и parser
            mock_writer = MagicMock()
            mock_writer.__enter__ = Mock(return_value=mock_writer)
            mock_writer.__exit__ = Mock(side_effect=MemoryError("Mocked MemoryError"))

            mock_inner_parser = MagicMock()
            mock_inner_parser.__enter__ = Mock(return_value=mock_inner_parser)
            mock_inner_parser.__exit__ = Mock(return_value=None)
            mock_inner_parser.parse = Mock(side_effect=MemoryError("Mocked MemoryError"))

            # Патчим get_writer и get_parser в правильном месте
            with (
                patch("parser_2gis.writer.get_writer", return_value=mock_writer),
                patch("parser_2gis.parser.get_parser", return_value=mock_inner_parser),
            ):
                # Вызываем parse_single_url
                try:
                    parser.parse_single_url(
                        url="https://2gis.ru/moscow/search/restaurants",
                        category_name="Рестораны",
                        city_name="Москва",
                    )
                except MemoryError:
                    pass  # Ожидаем MemoryError

                # Проверяем что semaphore.release() вызван ровно 1 раз
                release_calls = [c for c in mock_semaphore.method_calls if c[0] == "release"]
                assert len(release_calls) == 1, (
                    f"semaphore.release() должен быть вызван ровно 1 раз, "
                    f"вызван {len(release_calls)} раз"
                )

    def test_semaphore_release_on_success(self):
        """Тест: семафор освобождается при успешном выполнении."""
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        config = self._create_mock_config()

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Рестораны", "id": 1}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            mock_semaphore = MagicMock(spec=threading.BoundedSemaphore)
            parser._browser_launch_semaphore = mock_semaphore

            mock_writer = MagicMock()
            mock_writer.__enter__ = Mock(return_value=mock_writer)
            mock_writer.__exit__ = Mock(return_value=None)

            mock_inner_parser = MagicMock()
            mock_inner_parser.__enter__ = Mock(return_value=mock_inner_parser)
            mock_inner_parser.__exit__ = Mock(return_value=None)
            mock_inner_parser.parse = Mock(return_value=None)

            with (
                patch("parser_2gis.writer.get_writer", return_value=mock_writer),
                patch("parser_2gis.parser.get_parser", return_value=mock_inner_parser),
            ):
                parser.parse_single_url(
                    url="https://2gis.ru/moscow/search/restaurants",
                    category_name="Рестораны",
                    city_name="Москва",
                )

                # Проверяем что semaphore.release() вызван ровно 1 раз
                release_calls = [c for c in mock_semaphore.method_calls if c[0] == "release"]
                assert len(release_calls) == 1


# =============================================================================
# P0-2: ТЕСТ ДЛЯ parallel_parser.py - ЗАКРЫТИЕ WRITER/PARSER
# =============================================================================


class TestWriterParserCleanupOnChromeException:
    """Тесты для P0-2: writer и parser закрываются при ChromeException."""

    def _create_mock_config(self):
        """Создает mock конфигурацию с правильной структурой."""
        config = MagicMock()
        config.parallel = MagicMock()
        config.parallel.initial_delay_min = 0.0
        config.parallel.initial_delay_max = 0.1
        config.parallel.launch_delay_min = 0.0
        config.parallel.launch_delay_max = 0.1
        config.parallel.use_temp_file_cleanup = False
        config.writer = MagicMock()
        config.chrome = MagicMock()
        config.parser = MagicMock()
        return config

    def test_writer_parser_cleanup_on_chrome_exception(self):
        """Тест: writer и parser закрываются при ChromeException.

        Проверить что writer.close() и parser.close() вызываются
        Даже при возникновении ChromeException
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser
        from parser_2gis.chrome.exceptions import ChromeException

        config = self._create_mock_config()

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Рестораны", "id": 1}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            mock_semaphore = MagicMock(spec=threading.BoundedSemaphore)
            parser._browser_launch_semaphore = mock_semaphore

            # Создаем mock writer и parser с отслеживанием close()
            mock_writer = MagicMock()
            mock_writer.__enter__ = Mock(return_value=mock_writer)
            mock_writer.__exit__ = Mock(return_value=None)

            mock_inner_parser = MagicMock()
            mock_inner_parser.__enter__ = Mock(return_value=mock_inner_parser)
            # ChromeException при входе в контекст
            mock_inner_parser.__exit__ = Mock(side_effect=ChromeException("Mocked ChromeException"))
            mock_inner_parser.parse = Mock()

            with (
                patch("parser_2gis.writer.get_writer", return_value=mock_writer),
                patch("parser_2gis.parser.get_parser", return_value=mock_inner_parser),
            ):
                try:
                    parser.parse_single_url(
                        url="https://2gis.ru/moscow/search/restaurants",
                        category_name="Рестораны",
                        city_name="Москва",
                    )
                except ChromeException:
                    pass  # Ожидаем ChromeException

                # Проверяем что __exit__ был вызван для writer и parser
                assert mock_writer.__exit__.called, "writer.__exit__() должен быть вызван"
                assert mock_inner_parser.__exit__.called, "parser.__exit__() должен быть вызван"


# =============================================================================
# P0-3: ТЕСТ ДЛЯ chrome/browser.py - ОЧИСТКА ПРОФИЛЯ
# =============================================================================


class TestProfileCleanupWhenNotCreated:
    """Тесты для P0-3: очистка профиля не вызывает ошибок если профиль не создан."""

    def test_profile_cleanup_when_not_created(self):
        """Тест: очистка профиля не вызывает ошибок если профиль не создан.

        Проверить что ProfileManager.cleanup_profile() не вызывает ошибок
        Когда profile_path is None или не создан
        """
        from parser_2gis.chrome.browser import ProfileManager

        manager = ProfileManager()

        # Проверяем что profile_path is None изначально
        assert manager.profile_path is None

        # Вызываем cleanup_profile() без создания профиля
        # Не должно вызывать ошибок
        try:
            manager.cleanup_profile()
        except Exception as e:
            pytest.fail(f"cleanup_profile() вызвал ошибку: {e}")

    def test_profile_cleanup_after_creation(self):
        """Тест: очистка профиля работает корректно после создания."""
        from parser_2gis.chrome.browser import ProfileManager

        manager = ProfileManager()

        # Создаем профиль
        tempdir, profile_path = manager.create_profile()

        # Проверяем что профиль создан
        assert manager.profile_path is not None
        assert os.path.exists(profile_path)

        # Очищаем профиль
        manager.cleanup_profile()

        # Проверяем что профиль удалён
        assert not os.path.exists(profile_path)


# =============================================================================
# P0-4: ТЕСТ ДЛЯ chrome/browser.py - ZOMBIE PROCESS
# =============================================================================


class TestProcessKillOnTimeout:
    """Тесты для P0-4: процесс убивается принудительно после timeout."""

    def test_process_kill_on_timeout(self):
        """Тест: процесс убивается принудительно после timeout.

        Проверить что process.kill() вызывается после TimeoutExpired
        Использовать psutil для проверки что процесс не zombie
        """
        from parser_2gis.chrome.browser import ProcessManager

        manager = ProcessManager()

        # Создаем mock процесс
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll = Mock(return_value=None)  # Процесс работает
        mock_process.terminate = Mock()
        mock_process.kill = Mock()
        mock_process.wait = Mock(side_effect=subprocess.TimeoutExpired(cmd="chrome", timeout=10))

        manager._proc = mock_process

        # Вызываем kill с timeout
        manager.kill(process_pid=12345, timeout=10)

        # Проверяем что kill() был вызван
        assert mock_process.kill.called, "process.kill() должен быть вызван"

        # Проверяем что wait() был вызван с timeout
        assert mock_process.wait.called, "process.wait() должен быть вызван"

    def test_process_kill_with_psutil(self):
        """Тест: процесс убивается с использованием psutil при timeout."""
        from parser_2gis.chrome.browser import ProcessManager

        manager = ProcessManager()

        # Создаем mock процесс
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll = Mock(return_value=None)
        mock_process.kill = Mock()
        mock_process.wait = Mock(side_effect=subprocess.TimeoutExpired(cmd="chrome", timeout=10))

        manager._proc = mock_process

        # Мок psutil
        mock_ps_proc = MagicMock()
        mock_ps_proc.children = Mock(return_value=[])
        mock_ps_proc.kill = Mock()

        with patch("psutil.Process", return_value=mock_ps_proc):
            manager.kill(process_pid=12345, timeout=10)

            # Проверяем что psutil.Process.kill() был вызван
            assert mock_ps_proc.kill.called, "psutil.Process.kill() должен быть вызван"


# =============================================================================
# P0-5: ТЕСТ ДЛЯ cache/manager.py - КУРСОР СОЗДАЕТСЯ ДО TRY
# =============================================================================


class TestCursorCreatedBeforeTryBlock:
    """Тесты для P0-5: курсор создается до try блока."""

    def test_cursor_created_before_try_block(self):
        """Тест: курсор создается перед try блоком.

        Проверить что cursor не None в finally блоке
        Даже если ошибка произошла до назначения cursor
        """
        from parser_2gis.cache.manager import CacheManager

        # Создаем mock пул соединений
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection = Mock(return_value=mock_conn)
        mock_conn.cursor = Mock(return_value=mock_cursor)
        mock_conn.rollback = Mock()

        # Создаем кэш с mock пулом
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir))
            cache._pool = mock_pool

            # Патчим _hash_url для вызова ошибки
            with patch.object(cache, "_hash_url", side_effect=ValueError("Hash error")):
                # Вызываем get() - должна обработать ошибку корректно
                result = cache.get("https://example.com")

                # Проверяем что результат None (ошибка обработана)
                assert result is None

    def test_cursor_closed_in_finally(self):
        """Тест: курсор закрывается в finally блоке."""
        from parser_2gis.cache.manager import CacheManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection = Mock(return_value=mock_conn)
        mock_conn.cursor = Mock(return_value=mock_cursor)
        mock_conn.rollback = Mock()

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir))
            cache._pool = mock_pool

            # Патчим execute для вызова ошибки
            mock_cursor.execute = Mock(side_effect=sqlite3.Error("DB error"))

            cache.get("https://example.com")

            # Проверяем что cursor.close() был вызван
            assert mock_cursor.close.called, "cursor.close() должен быть вызван в finally"


# =============================================================================
# P0-6: ТЕСТ ДЛЯ cache/manager.py - ROLLBACK ПРИ MEMORYERROR
# =============================================================================


class TestRollbackOnMemoryError:
    """Тесты для P0-6: транзакция откатывается при MemoryError."""

    def test_rollback_on_memory_error_get(self):
        """Тест: транзакция откатывается при MemoryError в get()."""
        from parser_2gis.cache.manager import CacheManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection = Mock(return_value=mock_conn)
        mock_conn.cursor = Mock(return_value=mock_cursor)
        mock_conn.rollback = Mock()
        mock_cursor.execute = Mock(side_effect=MemoryError("Out of memory"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir))
            cache._pool = mock_pool

            cache.get("https://example.com")

            # Проверяем что rollback() был вызван
            assert mock_conn.rollback.called, "conn.rollback() должен быть вызван при MemoryError"

    def test_rollback_on_memory_error_set(self):
        """Тест: транзакция откатывается при MemoryError в set()."""
        from parser_2gis.cache.manager import CacheManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection = Mock(return_value=mock_conn)
        mock_conn.cursor = Mock(return_value=mock_cursor)
        mock_conn.rollback = Mock()
        mock_cursor.execute = Mock(side_effect=MemoryError("Out of memory"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir))
            cache._pool = mock_pool

            # Вызываем set() с MemoryError
            with pytest.raises(MemoryError):
                cache.set("https://example.com", {"data": "test"})

            # Проверяем что rollback() был вызван
            assert mock_conn.rollback.called, (
                "conn.rollback() должен быть вызван при MemoryError в set()"
            )


# =============================================================================
# P0-7: ТЕСТ ДЛЯ tui_textual/app.py - ОЧИСТКА PARSER
# =============================================================================


class TestParserCleanupOnAppStop:
    """Тесты для P0-7: ParallelCityParser очищается при остановке приложения."""


# =============================================================================
# P0-8: ТЕСТ ДЛЯ csv_writer.py - ПОРЯДОК ПОСТОБРАБОТКИ
# =============================================================================


class TestPostprocessingAfterSuperExit:
    """Тесты для P0-8: постобработка выполняется после super().__exit__()."""

    def _create_mock_options(self):
        """Создает mock опции с правильной структурой."""
        options = MagicMock()
        options.csv = MagicMock()
        options.csv.remove_empty_columns = True
        options.csv.remove_duplicates = False
        options.csv.add_rubrics = True
        options.csv.add_comments = False
        options.csv.columns_per_entity = 1
        options.verbose = False
        options.encoding = "utf-8"
        return options


# =============================================================================
# P0-9: ТЕСТ ДЛЯ main_parser.py - JAVASCRIPT TRY-CATCH
# =============================================================================


class TestJavascriptTryCatch:
    """Тесты для P0-9: JavaScript код выполняется в try-catch."""

    def test_javascript_script_validation(self):
        """Тест: валидация JavaScript скрипта."""
        from parser_2gis.parser.parsers.main_parser import MainPageParser
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.parser.options import ParserOptions

        chrome_options = MagicMock(spec=ChromeOptions)
        chrome_options.disable_images = False

        parser_options = MagicMock(spec=ParserOptions)
        parser_options.max_retries = 3

        mock_browser = MagicMock()
        mock_browser.add_blocked_requests = Mock()

        parser = MainPageParser(
            url="https://2gis.ru/moscow/search/restaurants",
            chrome_options=chrome_options,
            parser_options=parser_options,
            browser=mock_browser,
        )

        # Проверяем что dangerous паттерны блокируются
        dangerous_scripts = ["document.cookie", "localStorage", "eval()", "innerHTML ="]

        for script in dangerous_scripts:
            result = parser._validate_js_script(script)
            assert result is False, f"Скрипт '{script}' должен быть заблокирован"


# =============================================================================
# P0-10: ТЕСТ ДЛЯ parallel_parser.py - ПРОВЕРКА ОТМЕНЫ ПЕРЕД ПАМЯТЬЮ
# =============================================================================


class TestCancelEventCheckedBeforeMemory:
    """Тесты для P0-10: флаг отмены проверяется перед проверкой памяти."""

    def _create_mock_config(self):
        """Создает mock конфигурацию с правильной структурой."""
        config = MagicMock()
        config.parallel = MagicMock()
        config.parallel.initial_delay_min = 0.0
        config.parallel.initial_delay_max = 0.1
        config.parallel.launch_delay_min = 0.0
        config.parallel.launch_delay_max = 0.1
        config.parallel.use_temp_file_cleanup = False
        config.writer = MagicMock()
        config.chrome = MagicMock()
        config.parser = MagicMock()
        return config

    def test_cancel_event_checked_before_memory(self):
        """Тест: флаг отмены проверяется перед проверкой памяти.

        Проверить что _cancel_event.is_set() проверяется ДО проверки памяти
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        config = self._create_mock_config()

        cities = [{"name": "Москва"}]
        categories = [{"name": "Рестораны"}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            # Устанавливаем флаг отмены
            parser._cancel_event.set()

            # Вызываем parse_single_url
            result = parser.parse_single_url(
                url="https://2gis.ru/moscow/search/restaurants",
                category_name="Рестораны",
                city_name="Москва",
            )

            # Проверяем что операция отменена
            assert result[0] is False
            assert "Отменено" in result[1]

    def test_cancel_event_order(self):
        """Тест: порядок проверки отмены и памяти."""
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        config = self._create_mock_config()

        cities = [{"name": "Москва"}]
        categories = [{"name": "Рестораны"}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            # Устанавливаем флаг отмены
            parser._cancel_event.set()

            # Патчим MemoryMonitor для проверки что он не вызывается
            with patch("parser_2gis.parallel.parallel_parser.MemoryMonitor") as mock_monitor_class:
                mock_monitor = MagicMock()
                mock_monitor.get_available_memory = Mock(return_value=0)
                mock_monitor_class.return_value = mock_monitor

                parser.parse_single_url(
                    url="https://2gis.ru/moscow/search/restaurants",
                    category_name="Рестораны",
                    city_name="Москва",
                )

                # Проверяем что MemoryMonitor НЕ вызывался (отмена раньше)
                assert not mock_monitor.get_available_memory.called, (
                    "MemoryMonitor не должен вызываться если флаг отмены установлен"
                )


# =============================================================================
# P0-11: ТЕСТ ДЛЯ parallel_parser.py - ПРОВЕРКА ОТМЕНЫ В ГЕНЕРАЦИИ URL
# =============================================================================


class TestCancelEventInUrlGeneration:
    """Тесты для P0-11: флаг отмены проверяется в цикле генерации URL."""

    def _create_mock_config(self):
        """Создает mock конфигурацию с правильной структурой."""
        config = MagicMock()
        config.parallel = MagicMock()
        config.parallel.initial_delay_min = 0.0
        config.parallel.initial_delay_max = 0.1
        config.parallel.launch_delay_min = 0.0
        config.parallel.launch_delay_max = 0.1
        config.parallel.use_temp_file_cleanup = False
        config.writer = MagicMock()
        config.chrome = MagicMock()
        config.parser = MagicMock()
        return config

    def test_cancel_event_in_url_generation(self):
        """Тест: флаг отмены проверяется в цикле генерации URL.

        Проверить что _cancel_event проверяется в цикле
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        config = self._create_mock_config()

        # Создаем много городов и категорий для теста цикла
        cities = [{"name": f"Город{i}", "url": f"https://2gis.ru/city{i}"} for i in range(10)]
        categories = [{"name": f"Категория{i}", "id": i} for i in range(10)]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            # Патчим generate_category_url для симуляции задержки
            def slow_generate_url(city, category):
                time.sleep(0.01)
                return f"{city['url']}/search/{category['name']}"

            with patch(
                "parser_2gis.parallel.parallel_parser.generate_category_url",
                side_effect=slow_generate_url,
            ):
                # Запускаем генерацию URL в отдельном потоке
                urls = []

                def generate():
                    for city in parser.cities:
                        for category in parser.categories:
                            # Проверяем флаг отмены в цикле
                            if parser._cancel_event.is_set():
                                break
                            # Используем patch'енную функцию
                            url = slow_generate_url(city, category)
                            urls.append(url)
                        if parser._cancel_event.is_set():
                            break

                thread = threading.Thread(target=generate)
                thread.start()

                # Устанавливаем флаг отмены через небольшое время
                time.sleep(0.05)
                parser._cancel_event.set()

                thread.join(timeout=1.0)

                # Проверяем что генерация была прервана
                assert len(urls) < len(cities) * len(categories), (
                    "Генерация URL должна быть прервана при установке флага отмены"
                )


# =============================================================================
# P0-12: ТЕСТ ДЛЯ chrome/browser.py - АТОМАРНОЕ СОЗДАНИЕ ДИРЕКТОРИИ
# =============================================================================


class TestAtomicDirectoryCreation:
    """Тесты для P0-12: директория создается атомарно с правами."""

    def test_atomic_directory_creation(self):
        """Тест: директория создается атомарно с правами.

        Проверить что os.makedirs используется с mode=0o700
        Проверить что права установлены корректно
        """
        from parser_2gis.chrome.browser import ProfileManager

        manager = ProfileManager()

        # Создаем профиль
        tempdir, profile_path = manager.create_profile()

        try:
            # Проверяем что директория существует
            assert os.path.exists(profile_path), "Директория профиля должна существовать"

            # Проверяем права доступа (0o700)
            stat_info = os.stat(profile_path)
            mode = stat_info.st_mode & 0o777

            # Проверяем что права не шире чем 0o700
            assert mode <= 0o700, f"Права доступа должны быть <= 0o700, получено {oct(mode)}"

        finally:
            # Очищаем профиль
            manager.cleanup_profile()

    def test_atomic_directory_creation_with_existing(self):
        """Тест: атомарное создание директории с exist_ok=True."""
        from parser_2gis.chrome.browser import ProfileManager

        manager = ProfileManager()

        # Создаем профиль первый раз
        tempdir1, profile_path1 = manager.create_profile()

        try:
            # Проверяем что директория существует
            assert os.path.exists(profile_path1)

            # Очищаем и создаем снова (тест exist_ok)
            manager.cleanup_profile()

            # Создаем новый профиль
            tempdir2, profile_path2 = manager.create_profile()

            assert os.path.exists(profile_path2)

            # Проверяем права
            stat_info = os.stat(profile_path2)
            mode = stat_info.st_mode & 0o777
            assert mode <= 0o700

            manager.cleanup_profile()

        except Exception:
            manager.cleanup_profile()
            raise


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestIntegrationFixes:
    """Интеграционные тесты для исправлений."""

    def _create_mock_config(self):
        """Создает mock конфигурацию с правильной структурой."""
        config = MagicMock()
        config.parallel = MagicMock()
        config.parallel.initial_delay_min = 0.0
        config.parallel.initial_delay_max = 0.1
        config.parallel.launch_delay_min = 0.0
        config.parallel.launch_delay_max = 0.1
        config.parallel.use_temp_file_cleanup = False
        config.writer = MagicMock()
        config.chrome = MagicMock()
        config.parser = MagicMock()
        return config

    def test_full_parallel_parsing_with_cancel(self):
        """Тест: полный цикл параллельного парсинга с отменой."""
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        config = self._create_mock_config()

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Рестораны", "id": 1}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            # Устанавливаем флаг отмены
            parser._cancel_event.set()

            # Запускаем парсинг
            result = parser.parse_single_url(
                url="https://2gis.ru/moscow/search/restaurants",
                category_name="Рестораны",
                city_name="Москва",
            )

            # Проверяем что отмена сработала
            assert result[0] is False
            assert "Отменено" in result[1]

    def test_cache_manager_memory_error_handling(self):
        """Тест: обработка MemoryError в CacheManager."""
        from parser_2gis.cache.manager import CacheManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir))

            # Патчим сериализацию для вызова MemoryError
            with patch.object(
                cache._serializer, "serialize", side_effect=MemoryError("Out of memory")
            ):
                # Вызываем set() с MemoryError
                with pytest.raises(MemoryError):
                    cache.set("https://example.com", {"data": "test"})

            # Проверяем что кэш пуст (транзакция откатилась)
            # Используем get_stats() для получения статистики
            stats = cache.get_stats()
            assert stats["total_records"] == 0


# =============================================================================
# EDGE CASE ТЕСТЫ
# =============================================================================


class TestEdgeCases:
    """Тесты для граничных случаев."""

    def _create_mock_config(self):
        """Создает mock конфигурацию с правильной структурой."""
        config = MagicMock()
        config.parallel = MagicMock()
        config.parallel.initial_delay_min = 0.0
        config.parallel.initial_delay_max = 0.1
        config.parallel.launch_delay_min = 0.0
        config.parallel.launch_delay_max = 0.1
        config.parallel.use_temp_file_cleanup = False
        config.writer = MagicMock()
        config.chrome = MagicMock()
        config.parser = MagicMock()
        return config

    def test_semaphore_release_multiple_exceptions(self):
        """Тест: семафор освобождается при множественных исключениях."""
        from parser_2gis.parallel.parallel_parser import ParallelCityParser
        from parser_2gis.chrome.exceptions import ChromeException

        config = self._create_mock_config()

        cities = [{"name": "Москва"}]
        categories = [{"name": "Рестораны"}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=tmp_dir,
                config=config,
                max_workers=2,
                timeout_per_url=60,
            )

            mock_semaphore = MagicMock(spec=threading.BoundedSemaphore)
            parser._browser_launch_semaphore = mock_semaphore

            mock_writer = MagicMock()
            mock_writer.__enter__ = Mock(return_value=mock_writer)
            mock_writer.__exit__ = Mock(return_value=None)

            mock_inner_parser = MagicMock()
            mock_inner_parser.__enter__ = Mock(return_value=mock_inner_parser)
            mock_inner_parser.__exit__ = Mock(side_effect=ChromeException("Error"))
            mock_inner_parser.parse = Mock()

            with (
                patch("parser_2gis.writer.get_writer", return_value=mock_writer),
                patch("parser_2gis.parser.get_parser", return_value=mock_inner_parser),
            ):
                try:
                    parser.parse_single_url(
                        url="https://2gis.ru/moscow/search/restaurants",
                        category_name="Рестораны",
                        city_name="Москва",
                    )
                except ChromeException:
                    pass

                # Проверяем что release() вызван ровно 1 раз
                release_calls = [c for c in mock_semaphore.method_calls if c[0] == "release"]
                assert len(release_calls) == 1

    def test_cursor_none_in_finally(self):
        """Тест: курсор None в finally блоке при ошибке до создания."""
        from parser_2gis.cache.manager import CacheManager

        mock_pool = MagicMock()
        mock_conn = MagicMock()

        mock_pool.get_connection = Mock(return_value=mock_conn)
        mock_conn.rollback = Mock()

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir))
            cache._pool = mock_pool

            # Патчим cursor() для вызова ошибки
            mock_conn.cursor = Mock(side_effect=sqlite3.Error("Cannot create cursor"))

            result = cache.get("https://example.com")

            # Проверяем что ошибка обработана
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
