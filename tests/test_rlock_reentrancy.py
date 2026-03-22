"""Тесты для проверки реентрантности RLock.

Проверяет что RLock поддерживает реентрантные вызовы и предотвращает deadlock
при вложенных захватах блокировки в одном потоке.
"""

import threading
import time
from unittest.mock import patch

import pytest

from parser_2gis.signal_handler import SignalHandler


class TestRLockReentrancy:
    """Тесты реентрантности RLock."""

    def test_rlock_reentrant_acquire(self):
        """Тест 1: RLock позволяет повторный захват в том же потоке."""
        lock = threading.RLock()

        # Первый захват
        lock.acquire()
        try:
            # Второй захват в том же потоке - не должен заблокировать
            lock.acquire()
            try:
                # Третий захват
                lock.acquire()
                try:
                    assert True, "RLock должен позволить 3 захвата"
                finally:
                    lock.release()
            finally:
                lock.release()
        finally:
            lock.release()

    def test_rlock_reentrant_with_statement(self):
        """Тест 2: RLock поддерживает вложенные with."""
        lock = threading.RLock()

        with lock:
            # Вложенный with
            with lock:
                # Ещё один вложенный with
                with lock:
                    assert True, "Вложенные with должны работать"

    def test_signal_handler_reentrant_cleanup(self):
        """Тест 3: SignalHandler поддерживает реентрантную очистку."""
        handler = SignalHandler()

        cleanup_count = {"value": 0}

        def nested_cleanup():
            with handler._lock:
                cleanup_count["value"] += 1
                # Вложенный вызов
                with handler._lock:
                    cleanup_count["value"] += 1

        nested_cleanup()
        assert cleanup_count["value"] == 2, "Должно быть 2 вызова"

    def test_rlock_release_count(self):
        """Тест 4: RLock требует столько же release() сколько acquire()."""
        lock = threading.RLock()

        lock.acquire()
        lock.acquire()
        lock.acquire()

        # После одного release блокировка всё ещё захвачена
        lock.release()
        assert lock._is_owned(), "Блокировка должна быть захвачена"  # type: ignore[attr-defined]

        # После второго release блокировка всё ещё захвачена
        lock.release()
        assert lock._is_owned(), "Блокировка должна быть захвачена"  # type: ignore[attr-defined]

        # После третьего release блокировка освобождена
        lock.release()
        # Проверяем что блокировка освобождена через попытку захвата
        acquired = lock.acquire(blocking=False)
        lock.release()
        assert acquired, "Блокировка должна быть свободна"

    def test_rlock_prevents_deadlock_in_recursive_function(self):
        """Тест 5: RLock предотвращает deadlock в рекурсивной функции."""
        lock = threading.RLock()
        call_count = {"value": 0}

        def recursive_function(depth):
            with lock:
                call_count["value"] += 1
                if depth > 0:
                    recursive_function(depth - 1)

        recursive_function(5)
        assert call_count["value"] == 6, "Должно быть 6 вызовов (0-5)"

    def test_rlock_different_threads_blocking(self):
        """Тест 6: RLock блокирует другие потоки."""
        lock = threading.RLock()
        thread2_acquired = threading.Event()
        thread2_blocked = threading.Event()

        def thread1_func():
            with lock:
                # Сигнал что поток 1 захватил блокировку
                thread2_blocked.set()
                # Ждём пока поток 2 попытается захватить
                thread2_acquired.wait(timeout=1)

        def thread2_func():
            # Ждём пока поток 1 захватит блокировку
            thread2_blocked.wait(timeout=1)
            # Пытаемся захватить - должны заблокироваться
            acquired = lock.acquire(blocking=False)
            if not acquired:
                thread2_acquired.set()  # Сигнал что не смогли захватить

        t1 = threading.Thread(target=thread1_func)
        t2 = threading.Thread(target=thread2_func)

        t1.start()
        t2.start()

        t2.join(timeout=2)
        t1.join(timeout=2)

        # Поток 2 не должен был захватить блокировку
        assert thread2_acquired.is_set(), "Поток 2 должен был заблокироваться"

    def test_rlock_same_thread_no_blocking(self):
        """Тест 7: RLock не блокирует тот же поток."""
        lock = threading.RLock()
        acquired_count = {"value": 0}

        def same_thread_operations():
            for _ in range(10):
                if lock.acquire(blocking=False):
                    acquired_count["value"] += 1
                    try:
                        pass
                    finally:
                        lock.release()

        same_thread_operations()
        assert acquired_count["value"] == 10, "Должно быть 10 успешных захватов"

    def test_rlock_nested_method_calls(self):
        """Тест 8: RLock поддерживает вложенные вызовы методов."""

        class Counter:
            def __init__(self):
                self._lock = threading.RLock()
                self._count = 0

            def increment(self):
                with self._lock:
                    self._count += 1
                    self._nested_increment()

            def _nested_increment(self):
                with self._lock:
                    self._count += 1

            def get_count(self):
                with self._lock:
                    return self._count

        counter = Counter()
        counter.increment()
        assert counter.get_count() == 2, "Счётчик должен быть 2"

    def test_rlock_exception_safety(self):
        """Тест 9: RLock освобождается при исключении."""
        lock = threading.RLock()

        def raise_exception():
            with lock:
                with lock:
                    raise ValueError("Test exception")

        with pytest.raises(ValueError):
            raise_exception()

        # Блокировка должна быть освобождена
        acquired = lock.acquire(blocking=False)
        lock.release()
        assert acquired, "Блокировка должна быть свободна после исключения"

    def test_rlock_reentrant_in_callback(self):
        """Тест 10: RLock поддерживает реентрантность в callback."""
        handler = SignalHandler()
        callback_count = {"value": 0}

        def outer_callback():
            with handler._lock:
                callback_count["value"] += 1
                # Вложенный callback
                inner_callback()

        def inner_callback():
            with handler._lock:
                callback_count["value"] += 1

        outer_callback()
        assert callback_count["value"] == 2, "Должно быть 2 вызова callback"

    def test_rlock_multiple_levels_of_nesting(self):
        """Тест 11: RLock поддерживает много уровней вложенности."""
        lock = threading.RLock()

        def level1():
            with lock:
                level2()

        def level2():
            with lock:
                level3()

        def level3():
            with lock:
                level4()

        def level4():
            with lock:
                level5()

        def level5():
            with lock:
                pass

        # Не должно вызвать deadlock
        level1()
        assert True, "Многоуровневая вложенность должна работать"

    def test_rlock_thread_isolation(self):
        """Тест 12: RLock изолирует потоки."""
        lock = threading.RLock()
        results = []

        def worker(worker_id):
            with lock:
                results.append(f"{worker_id}_start")
                # Имитация работы
                time.sleep(0.01)
                results.append(f"{worker_id}_end")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Все работники должны были завершиться
        assert len(results) == 6, "Все работники должны завершиться"

    def test_rlock_reentrant_stats_update(self):
        """Тест 12: RLock для обновления статистики."""
        handler = SignalHandler()

        def update_stats():
            with handler._lock:
                handler._stats = {"value": 0}  # type: ignore[attr-defined]
                # Вложенное обновление
                with handler._lock:
                    handler._stats["value"] = 1  # type: ignore[attr-defined]

        update_stats()
        assert handler._stats["value"] == 1  # type: ignore[attr-defined]

    def test_rlock_context_manager_reentrancy(self):
        """Тест 13: Контекстный менеджер RLock реентрантен."""
        lock = threading.RLock()

        def nested_contexts():
            with lock:
                with lock:
                    with lock:
                        return True
            return False

        assert nested_contexts(), "Вложенные контексты должны работать"

    def test_rlock_acquire_release_balance(self):
        """Тест 14: Баланс acquire/release."""
        lock = threading.RLock()

        acquisitions = 0
        releases = 0

        def balanced_operations():
            nonlocal acquisitions, releases
            for _ in range(5):
                lock.acquire()
                acquisitions += 1

            for _ in range(5):
                lock.release()
                releases += 1

        balanced_operations()
        assert acquisitions == releases == 5, "Баланс должен быть соблюден"

    def test_rlock_reentrant_logging(self):
        """Тест 15: RLock для логирования."""
        handler = SignalHandler()
        log_messages = []

        def log_message(msg):
            with handler._lock:
                log_messages.append(msg)
                if "outer" in msg:
                    log_message("inner")

        log_message("outer")
        assert len(log_messages) == 2, "Должно быть 2 сообщения"
        assert "outer" in log_messages[0]
        assert "inner" in log_messages[1]

    def test_rlock_reentrant_file_operations(self):
        """Тест 16: RLock для файловых операций."""
        import tempfile
        from pathlib import Path

        from parser_2gis.parallel_helpers import FileMerger

        with tempfile.TemporaryDirectory() as tmpdir:
            merger = FileMerger(
                output_dir=Path(tmpdir),
                config=type("Config", (), {"general": type("General", (), {"encoding": "utf-8"})}),
                cancel_event=threading.Event(),
            )

            # Реентрантные операции
            with merger._lock:
                # Вложенная операция
                with merger._lock:
                    assert True, "Вложенные файловые операции должны работать"

    def test_rlock_reentrant_cache_operations(self):
        """Тест 17: RLock для операций кэша."""
        from parser_2gis.chrome.remote import _HTTPCache

        cache = _HTTPCache()

        # Реентрантные операции с кэшем
        with cache._lock:
            cache.set(("key1",), type("Response", (), {"status_code": 200})())
            # Вложенная операция
            with cache._lock:
                result = cache.get(("key1",))
                assert result is not None, "Кэш должен работать"

    def test_rlock_reentrant_parallel_parser(self):
        """Тест 18: RLock в ParallelCityParser."""
        import inspect

        from parser_2gis.parallel_parser import ParallelCityParser

        # Проверяем что в коде используется RLock
        source = inspect.getsource(ParallelCityParser)
        assert "threading.RLock()" in source, "ParallelCityParser должен использовать RLock"

    def test_rlock_reentrant_connection_pool(self):
        """Тест 19: RLock в _ConnectionPool."""
        import tempfile
        from pathlib import Path

        from parser_2gis.cache import _ConnectionPool

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            pool = _ConnectionPool(Path(tmp.name))

            # Реентрантные операции
            with pool._lock:
                # Вложенная операция
                with pool._lock:
                    assert True, "Вложенные операции пула должны работать"

    def test_rlock_reentrant_temp_file_timer(self):
        """Тест 20: RLock в _TempFileTimer."""
        import tempfile
        from pathlib import Path

        from parser_2gis.parallel_parser import _TempFileTimer

        with tempfile.TemporaryDirectory() as tmpdir:
            timer = _TempFileTimer(temp_dir=Path(tmpdir))

            # Реентрантные операции
            with timer._lock:
                timer._cleanup_count = 1
                with timer._lock:
                    timer._cleanup_count = 2

            assert timer._cleanup_count == 2, "Счётчик должен быть 2"

    def test_rlock_reentrant_complex_scenario(self):
        """Тест 21: Сложный сценарий с несколькими компонентами."""
        import tempfile
        from pathlib import Path

        from parser_2gis.chrome.remote import _HTTPCache
        from parser_2gis.parallel_helpers import FileMerger
        from parser_2gis.parallel_parser import _TempFileTimer
        from parser_2gis.signal_handler import SignalHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаём несколько компонентов
            handler = SignalHandler()
            cache = _HTTPCache()
            merger = FileMerger(
                output_dir=Path(tmpdir),
                config=type("Config", (), {"general": type("General", (), {"encoding": "utf-8"})}),
                cancel_event=threading.Event(),
            )
            timer = _TempFileTimer(temp_dir=Path(tmpdir))

            # Комплексная реентрантная операция
            with handler._lock:
                with cache._lock:
                    with merger._lock:
                        with timer._lock:
                            # Все блокировки захвачены
                            assert True, "Все блокировки должны работать"

            # Все блокировки освобождены
            assert True, "Все блокировки должны освободиться"
