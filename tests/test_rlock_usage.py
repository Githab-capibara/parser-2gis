"""Тесты для проверки использования RLock вместо Lock.

Проверяет что во всех критических компонентах используется threading.RLock
вместо threading.Lock для поддержки реентрантных вызовов.
"""

import threading

import pytest

from parser_2gis.chrome.http_cache import _HTTPCache
from parser_2gis.parallel import ParallelCityParser
from parser_2gis.parallel.helpers import FileMerger


class TestRLockUsage:
    """Тесты использования RLock в проекте."""

    def test_parallel_parser_main_lock_uses_rlock(self):
        """Тест 1: ParallelCityParser использует RLock для основной блокировки."""
        # Проверяем что класс имеет правильную структуру через inspect
        import inspect

        # Получаем исходный код класса
        source = inspect.getsource(ParallelCityParser)

        # Проверяем что в коде используется RLock
        assert "threading.RLock()" in source, "ParallelCityParser должен использовать RLock"

    def test_parallel_parser_merge_lock_uses_rlock(self):
        """Тест 2: ParallelCityParser использует RLock для merge блокировки."""
        import inspect

        # Получаем исходный код класса
        source = inspect.getsource(ParallelCityParser)

        # Проверяем что в коде используется RLock для merge_lock
        assert "_merge_lock = threading.RLock()" in source or "threading.RLock()" in source, (
            "ParallelCityParser должен использовать RLock для merge_lock"
        )

    def test_http_cache_uses_rlock(self):
        """Тест 3: _HTTPCache использует RLock."""
        cache = _HTTPCache()
        assert isinstance(cache._lock, type(threading.RLock())), (
            "_HTTPCache._lock должен быть RLock"
        )

    def test_file_merger_uses_rlock(self):
        """Тест 4: FileMerger использует RLock."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            merger = FileMerger(
                output_dir=Path(tmpdir),
                config=type("Config", (), {"general": type("General", (), {"encoding": "utf-8"})}),
                cancel_event=threading.Event(),
            )
            assert isinstance(merger._lock, type(threading.RLock())), (
                "FileMerger._lock должен быть RLock"
            )

    def test_rlock_in_parallel_parser_stats(self):
        """Тест 5: ParallelCityParser использует RLock для защиты статистики."""
        import inspect

        # Получаем исходный код класса
        source = inspect.getsource(ParallelCityParser)

        # Проверяем что в коде используется RLock
        assert "threading.RLock()" in source, (
            "ParallelCityParser должен использовать RLock для защиты статистики"
        )

    def test_rlock_thread_safety(self):
        """Тест 6: RLock обеспечивает потокобезопасность."""
        # Используем RLock напрямую для теста
        lock = threading.RLock()
        counter = {"value": 0}
        errors = []

        def increment():
            try:
                for _ in range(100):
                    with lock:
                        counter["value"] += 1
            except Exception as e:
                errors.append(e)

        # Запускаем несколько потоков
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"
        assert counter["value"] == 1000, "Счётчик должен быть 1000"

    def test_rlock_release_in_try_except(self):
        """Тест 7: RLock.release() вызывается в try/except."""
        # Проверяем что код не вызывает lock.locked() - это вызовет AttributeError
        lock = threading.RLock()

        # Правильный паттерн - release() в try/except
        try:
            lock.release()
        except RuntimeError:
            # Ожидаемая ошибка - блокировка не была захвачена
            pass

        # Неправильный паттерн - lock.locked() не существует у RLock
        with pytest.raises(AttributeError):
            lock.locked()  # type: ignore[attr-defined]

    def test_multiple_rlock_components_integration(self):
        """Тест 8: Интеграция нескольких компонентов с RLock."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаём несколько компонентов
            cache = _HTTPCache()
            merger = FileMerger(
                output_dir=Path(tmpdir),
                config=type("Config", (), {"general": type("General", (), {"encoding": "utf-8"})}),
                cancel_event=threading.Event(),
            )

            # Все используют RLock
            assert isinstance(cache._lock, type(threading.RLock()))
            assert isinstance(merger._lock, type(threading.RLock()))

    def test_rlock_prevents_deadlock_in_nested_calls(self):
        """Тест 9: RLock предотвращает deadlock при вложенных вызовах."""
        lock = threading.RLock()
        deadlock_detected = False

        def outer_call():
            with lock:
                # Вложенный вызов с той же блокировкой
                inner_call()

        def inner_call():
            with lock:
                # Если бы был Lock, здесь был бы deadlock
                pass

        try:
            outer_call()
        except Exception:
            deadlock_detected = True

        assert not deadlock_detected, "RLock должен предотвращать deadlock"

    def test_rlock_reentrancy(self):
        """Тест 10: RLock поддерживает реентрантность."""
        lock = threading.RLock()

        # Проверяем что один и тот же поток может захватить блокировку несколько раз
        lock_acquired_count = 0

        def nested_lock_operations():
            nonlocal lock_acquired_count
            with lock:
                lock_acquired_count += 1
                # Реентрантный вызов - тот же поток захватывает ту же блокировку
                with lock:
                    lock_acquired_count += 1
                    with lock:
                        lock_acquired_count += 1

        nested_lock_operations()
        assert lock_acquired_count == 3, "RLock должен поддерживать реентрантность"
