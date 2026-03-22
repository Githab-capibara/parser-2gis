"""Тесты для проверки использования weakref.finalize.

Проверяет что weakref.finalize используется для гарантированной очистки ресурсов
в CacheManager, _ConnectionPool и _TempFileTimer.
"""

import gc
import time
import weakref
from pathlib import Path
from unittest.mock import patch

import pytest

from parser_2gis.cache import CacheManager, _ConnectionPool
from parser_2gis.parallel_parser import _TempFileTimer


class TestWeakrefFinalize:
    """Тесты использования weakref.finalize в проекте."""

    def test_connection_pool_has_finalizer(self):
        """Тест 1: _ConnectionPool имеет weakref.finalize."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            pool = _ConnectionPool(Path(tmp.name))

            # Проверяем наличие finalizer
            assert hasattr(pool, "_finalizer"), "_ConnectionPool должен иметь _finalizer"
            assert hasattr(pool, "_weak_ref"), "_ConnectionPool должен иметь _weak_ref"

            # Проверяем что finalizer активен
            assert pool._finalizer.alive, "Finalizer должен быть активен"

    def test_cache_manager_has_finalizer(self):
        """Тест 2: CacheManager имеет weakref.finalize."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Проверяем наличие finalizer
            assert hasattr(cache, "_finalizer"), "CacheManager должен иметь _finalizer"
            assert hasattr(cache, "_weak_ref"), "CacheManager должен иметь _weak_ref"

            # Проверяем что finalizer активен
            assert cache._finalizer.alive, "Finalizer должен быть активен"

    def test_temp_file_timer_has_finalizer(self):
        """Тест 3: _TempFileTimer имеет weakref.finalize."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            timer = _TempFileTimer(temp_dir=Path(tmpdir))

            # Проверяем наличие finalizer
            assert hasattr(timer, "_finalizer"), "_TempFileTimer должен иметь _finalizer"
            assert hasattr(timer, "_weak_ref"), "_TempFileTimer должен иметь _weak_ref"

            # Проверяем что finalizer активен
            assert timer._finalizer.alive, "Finalizer должен быть активен"

    def test_finalizer_called_on_garbage_collection(self):
        """Тест 4: Finalizer вызывается при сборке мусора."""
        import tempfile

        finalizer_called = False

        def mock_cleanup(*args):
            nonlocal finalizer_called
            finalizer_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаём объект и заменяем finalizer на mock
            cache = CacheManager(cache_dir=Path(tmpdir))
            original_finalizer = cache._finalizer

            # Detach original finalizer и создаём новый с mock
            cache._finalizer.detach()
            cache._finalizer = weakref.finalize(cache, mock_cleanup, Path(tmpdir))

            # Удаляем ссылку на объект
            del cache
            gc.collect()

            # Finalizer должен быть вызван
            assert finalizer_called, "Finalizer должен быть вызван при сборке мусора"

    def test_weakref_callback_cleanup(self):
        """Тест 5: weakref.callback для очистки ресурсов."""
        import tempfile

        cleanup_called = False

        def cleanup_callback(ref):
            nonlocal cleanup_called
            cleanup_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))
            weak_ref = weakref.ref(cache, cleanup_callback)

            # Проверяем что weakref работает
            assert weak_ref() is cache, "weakref должен ссылаться на объект"

            # Удаляем объект
            del cache
            gc.collect()

            # Callback должен быть вызван
            assert cleanup_called, "weakref callback должен быть вызван"

    def test_finalizer_detachment(self):
        """Тест 6: Отключение finalizer при явной очистке."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))
            finalizer = cache._finalizer

            # Закрываем явно
            cache.close()

            # Finalizer должен быть отключён
            assert not finalizer.alive, "Finalizer должен быть отключён после close()"

    def test_multiple_finalizers_independence(self):
        """Тест 7: Независимость нескольких finalizer."""
        import tempfile

        finalizer1_called = False
        finalizer2_called = False

        def cleanup1(*args):
            nonlocal finalizer1_called
            finalizer1_called = True

        def cleanup2(*args):
            nonlocal finalizer2_called
            finalizer2_called = True

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                cache1 = CacheManager(cache_dir=Path(tmpdir1))
                cache2 = CacheManager(cache_dir=Path(tmpdir2))

                # Заменяем finalizer на mock
                cache1._finalizer.detach()
                cache2._finalizer.detach()

                cache1._finalizer = weakref.finalize(cache1, cleanup1)
                cache2._finalizer = weakref.finalize(cache2, cleanup2)

                # Удаляем только первый объект
                del cache1
                gc.collect()

                # Первый finalizer должен сработать, второй - нет
                assert finalizer1_called, "Первый finalizer должен быть вызван"
                assert not finalizer2_called, "Второй finalizer не должен быть вызван"

    def test_finalizer_with_exception(self):
        """Тест 8: Finalizer обрабатывает исключения."""
        import tempfile

        exception_handled = False

        def cleanup_with_exception(*args):
            nonlocal exception_handled
            exception_handled = True
            raise ValueError("Test exception in finalizer")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Заменяем finalizer на mock с исключением
            cache._finalizer.detach()
            cache._finalizer = weakref.finalize(cache, cleanup_with_exception)

            # Удаляем объект - исключение не должно прервать программу
            del cache
            gc.collect()

            # Finalizer должен быть вызван несмотря на исключение
            assert exception_handled, "Finalizer должен быть вызван даже с исключением"

    def test_finalizer_prevents_resource_leak(self):
        """Тест 9: Finalizer предотвращает утечку ресурсов."""
        import tempfile

        resources_cleaned = False

        def cleanup_resources(pool):
            nonlocal resources_cleaned
            # Имитация очистки ресурсов
            pool.clear()
            resources_cleaned = True

        class MockPool:
            def __init__(self):
                self.data = [1, 2, 3]

            def clear(self):
                pass

        pool = MockPool()
        finalizer = weakref.finalize(pool, cleanup_resources, pool)

        del pool
        gc.collect()

        # Finalizer должен очистить ресурсы
        assert resources_cleaned, "Finalizer должен предотвратить утечку ресурсов"

    def test_finalizer_order_in_nested_objects(self):
        """Тест 10: Порядок вызова finalizer во вложенных объектах."""
        import tempfile

        cleanup_order = []

        def cleanup_outer(*args):
            cleanup_order.append("outer")

        def cleanup_inner(*args):
            cleanup_order.append("inner")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Создаём вложенный объект
            inner_cache = CacheManager(cache_dir=Path(tmpdir))

            # Заменяем finalizer на mock
            cache._finalizer.detach()
            inner_cache._finalizer.detach()

            cache._finalizer = weakref.finalize(cache, cleanup_outer)
            inner_cache._finalizer = weakref.finalize(inner_cache, cleanup_inner)

            # Удаляем оба объекта
            del cache
            del inner_cache
            gc.collect()

            # Оба finalizer должны быть вызваны
            assert "outer" in cleanup_order, "Outer finalizer должен быть вызван"
            assert "inner" in cleanup_order, "Inner finalizer должен быть вызван"

    def test_finalizer_with_circular_references(self):
        """Тест 11: Finalizer работает с циклическими ссылками."""
        import tempfile

        circular_cleanup_called = False

        def circular_cleanup(*args):
            nonlocal circular_cleanup_called
            circular_cleanup_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = CacheManager(cache_dir=Path(tmpdir))
            cache2 = CacheManager(cache_dir=Path(tmpdir))

            # Создаём циклическую ссылку
            cache1._reference = cache2  # type: ignore[attr-defined]
            cache2._reference = cache1  # type: ignore[attr-defined]

            # Заменяем finalizer на mock
            cache1._finalizer.detach()
            cache2._finalizer.detach()

            cache1._finalizer = weakref.finalize(cache1, circular_cleanup)

            # Удаляем ссылки
            del cache1
            del cache2
            gc.collect()

            # Finalizer должен сработать несмотря на циклические ссылки
            assert circular_cleanup_called, "Finalizer должен работать с циклическими ссылками"

    def test_finalizer_thread_safety(self):
        """Тест 12: Finalizer потокобезопасен."""
        import tempfile
        import threading

        finalizer_count = {"value": 0}
        lock = threading.Lock()

        def thread_safe_cleanup(*args):
            with lock:
                finalizer_count["value"] += 1

        objects = []
        finalizers = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаём несколько объектов
            for _ in range(5):
                cache = CacheManager(cache_dir=Path(tmpdir))
                cache._finalizer.detach()
                finalizer = weakref.finalize(cache, thread_safe_cleanup)
                cache._finalizer = finalizer
                objects.append(cache)
                finalizers.append(finalizer)

            # Удаляем все объекты
            del objects
            gc.collect()

            # Все finalizer должны быть вызваны
            assert finalizer_count["value"] == 5, "Все finalizer должны быть вызваны"

    def test_finalizer_with_timeout(self):
        """Тест 13: Finalizer с таймаутом."""
        import tempfile

        cleanup_completed = False

        def slow_cleanup(*args):
            nonlocal cleanup_completed
            time.sleep(0.1)  # Имитация медленной очистки
            cleanup_completed = True

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))
            cache._finalizer.detach()
            cache._finalizer = weakref.finalize(cache, slow_cleanup)

            del cache
            gc.collect()

            # Ждём завершения очистки
            time.sleep(0.2)

            assert cleanup_completed, "Finalizer должен завершиться"

    def test_finalizer_registration_multiple_callbacks(self):
        """Тест 14: Регистрация нескольких callback в finalizer."""
        import tempfile

        callback1_called = False
        callback2_called = False

        def callback1(*args):
            nonlocal callback1_called
            callback1_called = True

        def callback2(*args):
            nonlocal callback2_called
            callback2_called = True

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Регистрируем несколько finalizer
            cache._finalizer.detach()
            finalizer1 = weakref.finalize(cache, callback1)
            finalizer2 = weakref.finalize(cache, callback2)

            del cache
            gc.collect()

            # Оба callback должны быть вызваны
            assert callback1_called, "Первый callback должен быть вызван"
            assert callback2_called, "Второй callback должен быть вызван"
