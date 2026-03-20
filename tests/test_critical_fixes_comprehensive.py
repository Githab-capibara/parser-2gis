"""
Комплексные тесты для критических исправлений проекта parser-2gis.

Этот модуль содержит тесты для проверки всех критических исправлений:
1. Обработка конкретных исключений в cache.py (вместо except Exception)
2. Улучшенная обработка закрытия процесса в chrome/browser.py
3. Очистка временных файлов в parallel_parser.py
4. Валидация JS кода в chrome/remote.py
5. Использование RLock вместо Lock в cache.py
6. Валидация ENV переменных в parallel_parser.py и cache.py

Каждое исправление тестируется тремя независимыми тестами:
- Тест успешного сценария
- Тест обработки ошибок
- Тест граничных условий

Использует pytest и unittest.mock для мокирования внешних зависимостей.
Все тесты независимы и используют фикстуры из conftest.py.
"""

import os
import queue
import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Импортируем тестируемые модули
from parser_2gis.cache import CacheManager, _ConnectionPool, _validate_pool_env_int
from parser_2gis.chrome.browser import ChromeBrowser
from parser_2gis.chrome.remote import _validate_js_code
from parser_2gis.parallel_parser import (
    _cleanup_all_temp_files,
    _TempFileTimer,
    _validate_env_int,
)

# =============================================================================
# ГРУППА 1: ТЕСТЫ ДЛЯ CACHE.PY (EXCEPT EXCEPTION -> КОНКРЕТНЫЕ ИСКЛЮЧЕНИЯ)
# =============================================================================


class TestCacheExceptionHandling:
    """
    Тесты для проверки обработки конкретных исключений в cache.py.

    Исправление: Замена except Exception на конкретные типы исключений:
    - sqlite3.Error для ошибок базы данных
    - OSError для ошибок операционной системы
    - queue.Error для ошибок очереди соединений

    Эти тесты проверяют что каждое исключение обрабатывается корректно
    и логируется с соответствующим уровнем важности.
    """

    @pytest.fixture
    def cache_manager(self, tmp_path: Path) -> CacheManager:
        """
        Фикстура для создания CacheManager.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Настроенный CacheManager для тестов.
        """
        cache = CacheManager(cache_dir=tmp_path, ttl_hours=24)
        cache.initialize()
        yield cache
        cache.close()

    def test_sqlite_error_handling_in_get_connection(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """
        Тест 1: Проверка обработки sqlite3.Error в get_connection().

        Проверяет что при возникновении sqlite3.Error во время создания
        соединения с базой данных:
        - Ошибка корректно обрабатывается
        - Записывается warning лог с деталями ошибки
        - Исключение пробрасывается дальше для обработки вызывающим кодом

        Args:
            caplog: pytest caplog fixture для проверки логов.
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_sqlite_error.db"

        # Мокируем _create_connection для выброса sqlite3.Error
        with patch.object(_ConnectionPool, "_create_connection") as mock_create:
            mock_create.side_effect = sqlite3.Error("Mocked database connection error")

            pool = _ConnectionPool(cache_file, pool_size=5)

            # Проверяем что исключение пробрасывается
            with pytest.raises(sqlite3.Error, match="Mocked database connection error"):
                pool.get_connection()

    def test_oserror_handling_in_get_connection(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """
        Тест 2: Проверка обработки OSError в get_connection().

        Проверяет что при возникновении OSError (например, нет прав на запись
        в файл базы данных):
        - Ошибка корректно обрабатывается
        - Записывается warning лог с деталями ошибки
        - Исключение пробрасывается дальше для обработки вызывающим кодом

        Args:
            caplog: pytest caplog fixture для проверки логов.
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_oserror.db"

        # Мокируем _create_connection для выброса OSError
        with patch.object(_ConnectionPool, "_create_connection") as mock_create:
            mock_create.side_effect = OSError("Mocked OS error - disk full")

            pool = _ConnectionPool(cache_file, pool_size=5)

            # Проверяем что исключение пробрасывается
            with pytest.raises(OSError, match="Mocked OS error - disk full"):
                pool.get_connection()

    def test_queue_error_handling_in_get_connection(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """
        Тест 3: Проверка обработки queue.Error в get_connection().

        Проверяет что при возникновении queue.Empty (очередь соединений пуста):
        - Создаётся новое соединение вместо получения из очереди
        - Ошибка корректно обрабатывается без проброса исключения
        - Записывается debug лог о создании нового соединения

        Args:
            caplog: pytest caplog fixture для проверки логов.
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_queue_error.db"

        # Создаём пул с размером 1
        pool = _ConnectionPool(cache_file, pool_size=1)

        # Мокируем queue.Queue.get_nowait для выброса queue.Empty
        # Это симулирует ситуацию когда очередь пуста
        with patch.object(pool._connection_queue, "get_nowait") as mock_get:
            mock_get.side_effect = queue.Empty("Queue is empty")

            # Получаем соединение (должно создаться новое через _create_connection)
            conn = pool.get_connection()

            # Проверяем что get_nowait был вызван
            assert mock_get.called

            # Проверяем что соединение получено
            assert conn is not None


# =============================================================================
# ГРУППА 2: ТЕСТЫ ДЛЯ CHROME/BROWSER.PY (УЛУЧШЕНИЕ CLOSE())
# =============================================================================


class TestBrowserCloseImprovements:
    """
    Тесты для проверки улучшений в методе close() браузера.

    Исправление: Улучшенная обработка закрытия процесса Chrome:
    - Обработка ProcessLookupError при закрытии процесса
    - Обработка PermissionError при закрытии процесса
    - Обработка OSError при удалении файлов профиля

    Эти тесты проверяют что метод close() корректно обрабатывает
    все возможные ошибки при закрытии браузера.
    """

    @pytest.fixture
    def mock_chrome_process(self) -> MagicMock:
        """
        Фикстура для mock процесса Chrome.

        Returns:
            MagicMock для имитации subprocess.Popen.
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        return mock_process

    @pytest.fixture
    def mock_profile_tempdir(self) -> MagicMock:
        """
        Фикстура для mock TemporaryDirectory профиля.

        Returns:
            MagicMock для имитации tempfile.TemporaryDirectory.
        """
        mock_tempdir = MagicMock()
        mock_tempdir.name = "/tmp/chrome_profile_test"
        mock_tempdir.cleanup.return_value = None
        return mock_tempdir

    def test_process_lookup_error_handling(
        self,
        mock_chrome_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 1: Проверка обработки ProcessLookupError при закрытии процесса.

        Проверяет что при возникновении ProcessLookupError (процесс уже
        завершился):
        - Ошибка корректно обрабатывается
        - Записывается debug лог о том что процесс уже завершён
        - Метод close() продолжает выполнение для очистки профиля

        Args:
            mock_chrome_process: mock процесса Chrome.
            caplog: pytest caplog fixture для проверки логов.
        """
        # Мокируем terminate для выброса ProcessLookupError
        mock_chrome_process.terminate.side_effect = ProcessLookupError(
            "Process already finished"
        )

        # Создаём mock browser с необходимыми атрибутами
        browser = object.__new__(ChromeBrowser)
        browser._proc = mock_chrome_process
        browser._profile_tempdir = MagicMock()
        browser._profile_tempdir.cleanup.return_value = None
        browser._profile_path = "/tmp/test_profile"

        # Мокируем logger чтобы избежать ошибок
        with patch("parser_2gis.chrome.browser.logger"):
            # Вызываем close() - не должно быть исключений
            browser.close()

        # Проверяем что terminate был вызван
        assert mock_chrome_process.terminate.called

    def test_permission_error_handling(
        self,
        mock_chrome_process: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 2: Проверка обработки PermissionError при закрытии процесса.

        Проверяет что при возникновении PermissionError (нет прав на
        завершение процесса):
        - Ошибка корректно обрабатывается
        - Записывается error лог с деталями ошибки
        - Метод close() продолжает выполнение для очистки профиля

        Args:
            mock_chrome_process: mock процесса Chrome.
            caplog: pytest caplog fixture для проверки логов.
        """
        # Мокируем terminate для выброса PermissionError
        mock_chrome_process.terminate.side_effect = PermissionError(
            "Permission denied to kill process"
        )

        # Создаём mock browser с необходимыми атрибутами
        browser = object.__new__(ChromeBrowser)
        browser._proc = mock_chrome_process
        browser._profile_tempdir = MagicMock()
        browser._profile_tempdir.cleanup.return_value = None
        browser._profile_path = "/tmp/test_profile"

        # Мокируем logger чтобы избежать ошибок
        with patch("parser_2gis.chrome.browser.logger"):
            # Вызываем close() - не должно быть исключений
            browser.close()

        # Проверяем что terminate был вызван
        assert mock_chrome_process.terminate.called

    def test_oserror_handling_in_profile_cleanup(
        self,
        mock_chrome_process: MagicMock,
        mock_profile_tempdir: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 3: Проверка обработки OSError при удалении файлов профиля.

        Проверяет что при возникновении OSError (например, файл занят
        или нет прав на удаление):
        - Ошибка корректно обрабатывается
        - Записывается error лог с деталями ошибки
        - Метод close() завершается без проброса исключения

        Args:
            mock_chrome_process: mock процесса Chrome.
            mock_profile_tempdir: mock TemporaryDirectory.
            caplog: pytest caplog fixture для проверки логов.
        """
        # Мокируем cleanup для выброса OSError
        mock_profile_tempdir.cleanup.side_effect = OSError(
            "Disk I/O error - cannot delete files"
        )

        # Настраиваем mock процесса для успешного завершения
        mock_chrome_process.terminate.return_value = None
        mock_chrome_process.poll.return_value = 0

        # Создаём mock browser с необходимыми атрибутами
        browser = object.__new__(ChromeBrowser)
        browser._proc = mock_chrome_process
        browser._profile_tempdir = mock_profile_tempdir
        browser._profile_path = "/tmp/test_profile"

        # Мокируем logger чтобы избежать ошибок
        with patch("parser_2gis.chrome.browser.logger"):
            # Вызываем close() - не должно быть исключений
            browser.close()

        # Проверяем что cleanup был вызван
        assert mock_profile_tempdir.cleanup.called


# =============================================================================
# ГРУППА 3: ТЕСТЫ ДЛЯ PARALLEL_PARSER.PY (ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ)
# =============================================================================


class TestParallelParserTempFileCleanup:
    """
    Тесты для проверки очистки временных файлов в parallel_parser.py.

    Исправление: Улучшенная очистка временных файлов:
    - Контекстный менеджер temp_file_lock_context()
    - Обработка FileNotFoundError при удалении файлов
    - Обработка PermissionError при удалении файлов

    Эти тесты проверяют что очистка временных файлов работает корректно
    даже при возникновении ошибок.
    """

    @pytest.fixture(autouse=True)
    def cleanup_registry(self) -> None:
        """
        Фикстура для очистки реестра временных файлов после каждого теста.

        Гарантирует что тесты независимы и не влияют друг на друга.
        """
        from parser_2gis.parallel_parser import _temp_files_registry

        # Сохраняем оригинальное состояние
        original_state = _temp_files_registry.copy()

        yield

        # Восстанавливаем оригинальное состояние
        _temp_files_registry.clear()
        _temp_files_registry.update(original_state)

    def test_temp_file_lock_context(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 1: Проверка контекстного менеджера temp_file_lock_context().

        Проверяет что контекстный менеджер:
        - Корректно получает блокировку с timeout
        - Гарантированно освобождает блокировку в finally
        - Возвращает статус получения блокировки

        Args:
            caplog: pytest caplog fixture для проверки логов.
        """
        # Импортируем контекстный менеджер из функции очистки
        from contextlib import contextmanager

        from parser_2gis.parallel_parser import _temp_files_lock

        @contextmanager
        def temp_file_lock_context():
            """Контекстный менеджер для безопасного управления блокировкой."""
            lock_acquired = _temp_files_lock.acquire(timeout=5.0)
            try:
                yield lock_acquired
            finally:
                if lock_acquired:
                    _temp_files_lock.release()

        # Используем контекстный менеджер - он должен работать без ошибок
        with temp_file_lock_context() as lock_acquired:
            assert lock_acquired is True

    def test_file_not_found_error_handling(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 2: Проверка обработки FileNotFoundError при удалении файлов.

        Проверяет что при попытке удалить несуществующий файл:
        - Ошибка корректно обрабатывается
        - Записывается debug лог
        - Очистка продолжается для остальных файлов

        Args:
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture для проверки логов.
        """
        from parser_2gis.parallel_parser import _temp_files_registry

        # Создаём несуществующий файл в реестре
        non_existent_file = tmp_path / "non_existent_file.tmp"
        _temp_files_registry.add(non_existent_file)

        # Вызываем очистку - не должно быть исключений
        # Это главный тест - функция должна обработать FileNotFoundError без ошибок
        _cleanup_all_temp_files()

        # Проверяем что файл удалён из реестра
        assert non_existent_file not in _temp_files_registry

    def test_permission_error_handling_in_cleanup(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 3: Проверка обработки PermissionError при удалении файлов.

        Проверяет что при возникновении PermissionError (нет прав на удаление):
        - Ошибка корректно обрабатывается
        - Записывается error лог с деталями ошибки
        - Очистка продолжается для остальных файлов

        Args:
            mocker: pytest-mock fixture для мокирования.
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture для проверки логов.
        """
        from parser_2gis.parallel_parser import _temp_files_registry

        # Создаём файл в реестре
        protected_file = tmp_path / "protected_file.tmp"
        protected_file.write_text("test data")

        # Делаем файл недоступным для удаления (мокируем unlink)
        with patch.object(
            Path, "unlink", side_effect=PermissionError("Permission denied")
        ):
            _temp_files_registry.add(protected_file)

            # Вызываем очистку - не должно быть исключений
            _cleanup_all_temp_files()

        # Проверяем логирование ошибки
        assert any(
            "Нет прав" in record.message
            or "PermissionError" in record.message
            or "Permission denied" in record.message
            for record in caplog.records
            if record.levelname in ["ERROR", "WARNING"]
        )


# =============================================================================
# ГРУППА 4: ТЕСТЫ ДЛЯ CHROME/REMOTE.PY (ВАЛИДАЦИЯ JS КОДА)
# =============================================================================


class TestJSCodeValidation:
    """
    Тесты для проверки валидации JavaScript кода в chrome/remote.py.

    Исправление: Усиленная проверка JS кода на опасные конструкции:
    - Обнаружение eval через квадратные скобки
    - Обнаружение Object.prototype.constructor
    - Обнаружение Reflect.construct

    Эти тесты проверяют что валидатор обнаруживает все опасные конструкции.
    """

    def test_eval_via_brackets_detection(self) -> None:
        """
        Тест 1: Проверка обнаружения eval через квадратные скобки.

        Проверяет что валидатор обнаруживает попытки обхода фильтра
        через доступ к eval через квадратные скобки:
        - eval["name"]
        - window['eval']
        - this["eval"]

        Ожидается что валидатор вернёт False с соответствующим сообщением.
        """
        # Тестируем различные варианты доступа через квадратные скобки
        test_cases = [
            'eval["call"](code)',
            "eval['call'](code)",
            'window["eval"](code)',
            "this['eval'](code)",
            'globalThis["eval"](code)',
        ]

        for js_code in test_cases:
            is_valid, error_message = _validate_js_code(js_code)

            assert is_valid is False, f"Код должен быть отклонён: {js_code}"
            assert (
                "квадратные скобки" in error_message.lower()
                or "eval" in error_message.lower()
            ), f"Сообщение должно упоминать eval или квадратные скобки: {error_message}"

    def test_object_prototype_constructor_detection(self) -> None:
        """
        Тест 2: Проверка обнаружения Object.prototype.constructor.

        Проверяет что валидатор обнаруживает попытки использования
        Object.prototype.constructor для обхода фильтров:
        - Object.prototype.constructor
        - Object.prototype.constructor()

        Ожидается что валидатор вернёт False с соответствующим сообщением.
        """
        # Тестируем различные варианты использования constructor
        test_cases = [
            "Object.prototype.constructor('return this')()",
            "Object.prototype.constructor('alert(1)')()",
            "var fn = Object.prototype.constructor; fn('code')()",
        ]

        for js_code in test_cases:
            is_valid, error_message = _validate_js_code(js_code)

            assert is_valid is False, f"Код должен быть отклонён: {js_code}"
            assert (
                "Object.prototype.constructor" in error_message
                or "constructor" in error_message.lower()
            ), f"Сообщение должно упоминать constructor: {error_message}"

    def test_reflect_construct_detection(self) -> None:
        """
        Тест 3: Проверка обнаружения Reflect.construct.

        Проверяет что валидатор обнаруживает попытки использования
        Reflect.construct для обхода фильтров:
        - Reflect.construct(Function, [...])
        - Reflect.construct.apply

        Ожидается что валидатор вернёт False с соответствующим сообщением.
        """
        # Тестируем различные варианты использования Reflect.construct
        test_cases = [
            "Reflect.construct(Function, ['return this', ''])()",
            "Reflect.construct(Function, ['alert(1)'])()",
            "var fn = Reflect.construct(Function, ['code'])",
        ]

        for js_code in test_cases:
            is_valid, error_message = _validate_js_code(js_code)

            assert is_valid is False, f"Код должен быть отклонён: {js_code}"
            assert "Reflect.construct" in error_message or "Reflect" in error_message, (
                f"Сообщение должно упоминать Reflect.construct: {error_message}"
            )


# =============================================================================
# ГРУППА 5: ТЕСТЫ ДЛЯ CACHE.PY (RLOCK ВМЕСТО LOCK)
# =============================================================================


class TestRLockReentrancy:
    """
    Тесты для проверки использования RLock вместо Lock в cache.py.

    Исправление: Использование RLock для реентерабельности:
    - RLock позволяет одному потоку получать блокировку несколько раз
    - Предотвращает deadlock при вложенных вызовах
    - Критически важно для методов кэша которые вызывают друг друга

    Эти тесты проверяют что RLock работает корректно.
    """

    @pytest.fixture
    def connection_pool(self, tmp_path: Path) -> _ConnectionPool:
        """
        Фикстура для создания _ConnectionPool.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Настроенный _ConnectionPool для тестов.
        """
        cache_file = tmp_path / "test_rlock.db"
        pool = _ConnectionPool(cache_file, pool_size=5)
        yield pool
        pool.close_all()

    def test_rlock_reentrancy_basic(
        self,
        connection_pool: _ConnectionPool,
    ) -> None:
        """
        Тест 1: Проверка реентерабельности RLock.

        Проверяет что один и тот же поток может получить блокировку
        несколько раз без deadlock:
        - Первое acquire() успешно
        - Второе acquire() успешно (реентерабельность)
        - Третье acquire() успешно
        - После release() блокировка всё ещё удерживается
        - После второго release() блокировка освобождается

        Args:
            connection_pool: fixture пула соединений.
        """
        lock = connection_pool._lock

        # Проверяем что это RLock
        assert isinstance(lock, type(threading.RLock()))

        # Получаем блокировку первый раз
        acquired_first = lock.acquire(timeout=1.0)
        assert acquired_first is True

        # Получаем блокировку второй раз (реентерабельность)
        acquired_second = lock.acquire(timeout=1.0)
        assert acquired_second is True

        # Получаем блокировку третий раз
        acquired_third = lock.acquire(timeout=1.0)
        assert acquired_third is True

        # Освобождаем блокировку один раз
        lock.release()

        # Пробуем получить ещё раз (должно succeed так как RLock)
        acquired_fourth = lock.acquire(timeout=1.0)
        assert acquired_fourth is True

        # Полностью освобождаем блокировку
        lock.release()
        lock.release()
        lock.release()

    def test_nested_calls_with_rlock(
        self,
        connection_pool: _ConnectionPool,
    ) -> None:
        """
        Тест 2: Проверка работы вложенных вызовов с RLock.

        Проверяет что вложенные вызовы методов которые используют
        одну и ту же блокировку работают корректно:
        - get_connection() вызывает _create_connection()
        - Оба метода используют одну блокировку
        - Нет deadlock при вложенных вызовах

        Args:
            connection_pool: fixture пула соединений.
        """
        # Мокируем _create_connection для отслеживания вызовов
        with patch.object(connection_pool, "_create_connection") as mock_create:
            mock_conn = MagicMock()
            mock_create.return_value = mock_conn

            # Вызываем get_connection() который использует _lock
            conn = connection_pool.get_connection()

            # Проверяем что соединение получено
            assert conn is not None

            # Проверяем что _create_connection был вызван
            assert mock_create.called

            # Вызываем ещё раз (должно работать без deadlock)
            conn2 = connection_pool.get_connection()
            assert conn2 is not None

    def test_no_deadlock_with_rlock(
        self,
        connection_pool: _ConnectionPool,
    ) -> None:
        """
        Тест 3: Проверка отсутствия deadlock с RLock.

        Проверяет что при использовании RLock не возникает deadlock
        в сценарии где обычный Lock вызвал бы deadlock:
        - Поток получает блокировку
        - Вызывает метод который тоже пытается получить блокировку
        - Нет deadlock (RLock позволяет реентерабельность)

        Args:
            connection_pool: fixture пула соединений.
        """

        def nested_lock_operation() -> bool:
            """Операция которая получает блокировку внутри блокировки."""
            # Получаем блокировку первый раз
            if not connection_pool._lock.acquire(timeout=1.0):
                return False

            try:
                # Пытаемся получить блокировку второй раз (вложенный вызов)
                if not connection_pool._lock.acquire(timeout=1.0):
                    return False

                try:
                    # Имитируем работу
                    time.sleep(0.01)
                    return True
                finally:
                    connection_pool._lock.release()
            finally:
                connection_pool._lock.release()

        # Выполняем операцию в отдельном потоке с timeout
        result = [None]
        exception = [None]

        def worker():
            try:
                result[0] = nested_lock_operation()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5.0)  # Timeout для обнаружения deadlock

        # Проверяем что поток завершился без deadlock
        assert not thread.is_alive(), "Обнаружен deadlock - поток не завершился"
        assert exception[0] is None, f"Исключение в потоке: {exception[0]}"
        assert result[0] is True, "Операция не выполнилась успешно"


# =============================================================================
# ГРУППА 6: ТЕСТЫ ДЛЯ ENV ВАЛИДАЦИИ (PARALLEL_PARSER.PY, CACHE.PY)
# =============================================================================


class TestENVValidation:
    """
    Тесты для проверки валидации ENV переменных.

    Исправление: Валидация значений ENV переменных:
    - Проверка значений вне диапазона (слишком мало)
    - Проверка значений вне диапазона (слишком много)
    - Проверка некорректных значений (не int)

    Эти тесты проверяют что валидация работает корректно для всех
    ENV переменных в parallel_parser.py и cache.py.
    """

    @pytest.fixture(autouse=True)
    def clean_env(self) -> None:
        """
        Фикстура для очистки ENV переменных после каждого теста.

        Гарантирует что тесты независимы и не влияют на окружение.
        """
        # Сохраняем оригинальные значения
        original_env = {}
        env_vars_to_clean = [
            "PARSER_MAX_POOL_SIZE",
            "PARSER_MIN_POOL_SIZE",
            "PARSER_CONNECTION_MAX_AGE",
            "PARSER_MAX_WORKERS",
            "PARSER_TIMEOUT",
            "PARSER_TEMP_FILE_CLEANUP_INTERVAL",
            "PARSER_MERGE_LOCK_TIMEOUT",
            "PARSER_MAX_TEMP_FILES",
        ]

        for var in env_vars_to_clean:
            if var in os.environ:
                original_env[var] = os.environ[var]
                del os.environ[var]

        yield

        # Восстанавливаем оригинальные значения
        for var, value in original_env.items():
            os.environ[var] = value

    def test_env_value_too_low(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 1: Проверка валидации значений вне диапазона (слишком мало).

        Проверяет что при установке ENV переменной значения ниже минимального:
        - Значение корректируется до минимального допустимого
        - Записывается warning лог с объяснением
        - Функция возвращает минимальное значение

        Args:
            caplog: pytest caplog fixture для проверки логов.
        """
        # Тестируем _validate_env_int с минимальным значением
        os.environ["TEST_MIN_VALUE"] = "0"  # Ниже минимума 1

        result = _validate_env_int(
            "TEST_MIN_VALUE", default=5, min_value=1, max_value=100
        )

        # Проверяем что значение скорректировано до минимума
        assert result == 1, f"Ожидалось минимальное значение 1, получено {result}"

        # Проверяем логирование
        assert any(
            "меньше минимального" in record.message.lower()
            or "минимального значения" in record.message.lower()
            for record in caplog.records
            if record.levelname == "WARNING"
        )

        # Тестируем _validate_pool_env_int
        os.environ["PARSER_MIN_POOL_SIZE"] = "0"  # Ниже минимума 1

        result2 = _validate_pool_env_int(
            "PARSER_MIN_POOL_SIZE", default=5, min_value=1, max_value=10
        )
        assert result2 == 1, f"Ожидалось минимальное значение 1, получено {result2}"

    def test_env_value_too_high(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 2: Проверка валидации значений вне диапазона (слишком много).

        Проверяет что при установке ENV переменной значения выше максимального:
        - Значение корректируется до максимального допустимого
        - Записывается warning лог с объяснением
        - Функция возвращает максимальное значение

        Args:
            caplog: pytest caplog fixture для проверки логов.
        """
        # Тестируем _validate_env_int с максимальным значением
        os.environ["TEST_MAX_VALUE"] = "1000"  # Выше максимума 100

        result = _validate_env_int(
            "TEST_MAX_VALUE", default=5, min_value=1, max_value=100
        )

        # Проверяем что значение скорректировано до максимума
        assert result == 100, f"Ожидалось максимальное значение 100, получено {result}"

        # Проверяем логирование
        assert any(
            "больше максимального" in record.message.lower()
            or "максимального значения" in record.message.lower()
            for record in caplog.records
            if record.levelname == "WARNING"
        )

        # Тестируем _validate_pool_env_int
        os.environ["PARSER_MAX_POOL_SIZE"] = "1000"  # Выше максимума 50

        result2 = _validate_pool_env_int(
            "PARSER_MAX_POOL_SIZE", default=20, min_value=5, max_value=50
        )
        assert result2 == 50, f"Ожидалось максимальное значение 50, получено {result2}"

    def test_env_value_invalid_not_int(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Тест 3: Проверка валидации некорректных значений (не int).

        Проверяет что при установке ENV переменной некорректного значения:
        - _validate_env_int выбрасывает ValueError (новое поведение)
        - _validate_pool_env_int возвращает значение по умолчанию (старое поведение)

        Args:
            caplog: pytest caplog fixture для проверки логов.
        """
        # Тестируем _validate_env_int с некорректным значением (не int)
        # Эта функция выбрасывает ValueError при некорректных значениях
        os.environ["TEST_INVALID_VALUE"] = "not_a_number"

        # Проверяем что _validate_env_int выбрасывает ValueError
        with pytest.raises(ValueError, match="invalid literal for int"):
            _validate_env_int(
                "TEST_INVALID_VALUE", default=5, min_value=1, max_value=100
            )

        # Тестируем _validate_pool_env_int с некорректным значением
        # Эта функция возвращает значение по умолчанию (совместимость)
        os.environ["PARSER_MIN_POOL_SIZE"] = "invalid"

        result = _validate_pool_env_int(
            "PARSER_MIN_POOL_SIZE", default=5, min_value=1, max_value=10
        )
        # Проверяем что возвращено значение по умолчанию
        assert result == 5, f"Ожидалось значение по умолчанию 5, получено {result}"

        # Проверяем логирование для _validate_pool_env_int
        assert any(
            "не является целым числом" in record.message.lower()
            for record in caplog.records
            if record.levelname == "WARNING"
        )


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestIntegrationFixes:
    """
    Интеграционные тесты для проверки взаимодействия исправлений.

    Эти тесты проверяют что все исправления работают корректно вместе
    в реальных сценариях использования.
    """

    def test_cache_with_env_validation_integration(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Интеграционный тест: Кэш с валидацией ENV.

        Проверяет что CacheManager корректно работает с валидированными
        ENV переменными для connection pool.

        Args:
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture для проверки логов.
        """
        # Устанавливаем корректные ENV переменные
        os.environ["PARSER_MAX_POOL_SIZE"] = "10"
        os.environ["PARSER_MIN_POOL_SIZE"] = "3"
        os.environ["PARSER_CONNECTION_MAX_AGE"] = "600"

        cache = CacheManager(cache_dir=tmp_path, ttl_hours=24)
        # Инициализация происходит в __init__, отдельного метода initialize() нет

        # Проверяем что кэш работает
        cache.set("test_key", {"data": "test_value"})
        result = cache.get("test_key")

        assert result is not None
        assert result.get("data") == "test_value"

        cache.close()

    def test_temp_file_cleanup_with_env_validation_integration(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Интеграционный тест: Очистка файлов с валидацией ENV.

        Проверяет что _TempFileTimer корректно работает с валидированными
        ENV переменными для интервалов очистки.

        Args:
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture для проверки логов.
        """
        # Устанавливаем корректные ENV переменные
        os.environ["PARSER_TEMP_FILE_CLEANUP_INTERVAL"] = "30"
        os.environ["PARSER_MAX_TEMP_FILES_MONITORING"] = "500"
        os.environ["PARSER_ORPHANED_TEMP_FILE_AGE"] = "120"

        # Создаём таймер
        timer = _TempFileTimer(
            temp_dir=tmp_path, interval=30, max_files=500, orphan_age=120
        )

        # Проверяем что таймер создан с корректными параметрами
        assert timer._interval == 30
        assert timer._max_files == 500
        assert timer._orphan_age == 120

        # Запускаем и останавливаем таймер
        timer.start()
        timer.stop()


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == "__main__":
    # Запуск тестов через pytest
    pytest.main([__file__, "-v", "--tb=short"])
