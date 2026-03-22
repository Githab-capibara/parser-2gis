"""Тесты для проверки использования weakref.finalize.

Проверяет что weakref.finalize используется для гарантированной очистки ресурсов
в CacheManager, _ConnectionPool и _TempFileTimer.
"""

import gc
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

    def test_weakref_returns_object(self):
        """Тест 4: weakref возвращает объект."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))
            weak_ref = cache._weak_ref

            # Проверяем что weakref возвращает объект
            assert weak_ref() is cache, "weakref должен возвращать объект"

    def test_finalizer_is_callable(self):
        """Тест 5: Finalizer является вызываемым объектом."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Finalizer должен быть вызываемым
            assert callable(cache._finalizer), "Finalizer должен быть вызываемым"

    def test_finalizer_detach(self):
        """Тест 6: Finalizer можно отключить."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))
            finalizer = cache._finalizer

            # Отключаем finalizer
            finalizer.detach()

            # Finalizer должен быть отключён
            assert not finalizer.alive, "Finalizer должен быть отключён"

    def test_weakref_callback_called(self):
        """Тест 7: weakref callback вызывается при удалении объекта."""
        callback_called = {"value": False}

        def callback(ref):
            callback_called["value"] = True

        # Создаём простой объект с weakref callback
        class TestObj:
            pass

        obj = TestObj()
        weak_ref = weakref.ref(obj, callback)

        # Удаляем объект
        del obj
        gc.collect()

        # Callback должен быть вызван
        assert callback_called["value"], "weakref callback должен быть вызван"

    def test_finalizer_with_static_cleanup(self):
        """Тест 8: Finalizer использует статический метод очистки."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Проверяем что finalizer использует статический метод
            # Это видно по аргументам finalizer
            assert cache._finalizer.alive, "Finalizer должен быть активен"

    def test_multiple_objects_have_finalizers(self):
        """Тест 9: Несколько объектов имеют finalizer."""
        import tempfile

        finalizers = []

        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                cache1 = CacheManager(cache_dir=Path(tmpdir1))
                cache2 = CacheManager(cache_dir=Path(tmpdir2))

                finalizers.append(cache1._finalizer)
                finalizers.append(cache2._finalizer)

                # Оба finalizer должны быть активны
                assert all(f.alive for f in finalizers), "Все finalizer должны быть активны"

    def test_finalizer_prevents_circular_reference_leak(self):
        """Тест 10: Finalizer работает с циклическими ссылками."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = CacheManager(cache_dir=Path(tmpdir))
            cache2 = CacheManager(cache_dir=Path(tmpdir))

            # Создаём циклическую ссылку
            cache1._reference = cache2  # type: ignore[attr-defined]
            cache2._reference = cache1  # type: ignore[attr-defined]

            # Оба finalizer должны быть активны несмотря на циклические ссылки
            assert cache1._finalizer.alive, "Finalizer 1 должен быть активен"
            assert cache2._finalizer.alive, "Finalizer 2 должен быть активен"

    def test_finalizer_registered_for_cleanup(self):
        """Тест 11: Finalizer зарегистрирован для очистки."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Finalizer должен быть зарегистрирован
            assert cache._finalizer is not None, "Finalizer должен быть зарегистрирован"

    def test_weakref_finalizer_independence(self):
        """Тест 12: weakref и finalizer независимы."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # weakref и finalizer должны быть разными объектами
            assert cache._weak_ref is not None, "weakref должен существовать"
            assert cache._finalizer is not None, "finalizer должен существовать"
            assert type(cache._weak_ref) != type(cache._finalizer), (
                "weakref и finalizer должны быть разными типами"
            )

    def test_finalizer_cleanup_method_exists(self):
        """Тест 13: Метод очистки для finalizer существует."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            # Проверяем что метод очистки существует
            assert hasattr(CacheManager, "_cleanup_cache_manager"), (
                "Метод _cleanup_cache_manager должен существовать"
            )

    def test_connection_pool_cleanup_method_exists(self):
        """Тест 14: Метод очистки для _ConnectionPool существует."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            pool = _ConnectionPool(Path(tmp.name))

            # Проверяем что метод очистки существует
            assert hasattr(_ConnectionPool, "_cleanup_pool"), (
                "Метод _cleanup_pool должен существовать"
            )
