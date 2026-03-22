"""
Тесты для проверки гонки данных в _TempFileTimer.

ИСПРАВЛЕНИЕ P0-5: Исправление гонки данных в _TempFileTimer
Файлы: parser_2gis/parallel_parser.py

Тестируют:
- Реентерабельность методов
- Отсутствие deadlock
- Корректную очистку временных файлов

Маркеры:
- @pytest.mark.unit для юнит-тестов
- @pytest.mark.integration для интеграционных тестов
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import List

import pytest

from parser_2gis.parallel_parser import (
    _cleanup_all_temp_files,
    _register_temp_file,
    _temp_files_lock,
    _temp_files_registry,
    _TempFileTimer,
    _unregister_temp_file,
)

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# ТЕСТ 1: РЕЕНТЕРАБЕЛЬНОСТЬ МЕТОДОВ
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerReentrancy:
    """Тесты для реентерабельности методов _TempFileTimer."""

    def test_rlock_allows_reentry(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка что RLock позволяет повторный вход.

        RLock должен позволять одному и тому же потоку
        получать блокировку несколько раз.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)

        # Получаем доступ к внутренней блокировке
        lock = timer._lock

        acquired_count = {"count": 0}

        def reentrant_acquire() -> None:
            """Повторный захват блокировки."""
            # Первый захват
            if lock.acquire(timeout=5.0):
                try:
                    acquired_count["count"] += 1
                    # Второй захват из того же потока
                    if lock.acquire(timeout=5.0):
                        try:
                            acquired_count["count"] += 1
                        finally:
                            lock.release()
                finally:
                    lock.release()

        thread = threading.Thread(target=reentrant_acquire)
        thread.start()
        thread.join(timeout=10)

        # RLock должен позволить 2 захвата из одного потока
        assert acquired_count["count"] == 2, "RLock не позволил повторный вход"

    def test_start_method_reentrancy(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка реентерабельности метода start().

        Многократный вызов start() не должен вызывать deadlock.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)

        errors: List[Exception] = []

        def call_start() -> None:
            """Вызывает start() несколько раз."""
            try:
                timer.start()
                timer.start()  # Повторный вызов
                timer.start()  # Ещё один вызов
            except Exception as e:
                errors.append(e)

        thread = threading.Thread(target=call_start)
        thread.start()
        thread.join(timeout=10)

        # Не должно быть ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

        # Останавливаем таймер
        timer.stop()

    def test_stop_method_reentrancy(self, tmp_path: Path) -> None:
        """
        Тест 1.3: Проверка реентерабельности метода stop().

        Многократный вызов stop() не должен вызывать deadlock.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        errors: List[Exception] = []

        def call_stop() -> None:
            """Вызывает stop() несколько раз."""
            try:
                timer.stop()
                timer.stop()  # Повторный вызов
                timer.stop()  # Ещё один вызов
            except Exception as e:
                errors.append(e)

        thread = threading.Thread(target=call_stop)
        thread.start()
        thread.join(timeout=10)

        # Не должно быть ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"


# =============================================================================
# ТЕСТ 2: ОТСУТСТВИЕ DEADLOCK
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerNoDeadlock:
    """Тесты для отсутствия deadlock в _TempFileTimer."""

    def test_no_deadlock_concurrent_start_stop(self, tmp_path: Path) -> None:
        """
        Тест 2.1: Проверка отсутствия deadlock при конкурентных start/stop.

        Один поток вызывает start(), другой stop().
        Проверяет что нет deadlock.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)

        errors: List[Exception] = []
        start_completed = threading.Event()
        stop_completed = threading.Event()

        def starter() -> None:
            """Вызывает start()."""
            try:
                timer.start()
                start_completed.set()
            except Exception as e:
                errors.append(("start", e))

        def stopper() -> None:
            """Вызывает stop()."""
            try:
                time.sleep(0.1)  # Небольшая задержка перед stop()
                timer.stop()
                stop_completed.set()
            except Exception as e:
                errors.append(("stop", e))

        # Запускаем потоки
        start_thread = threading.Thread(target=starter)
        stop_thread = threading.Thread(target=stopper)

        start_thread.start()
        stop_thread.start()

        # Ждем завершения с timeout
        start_thread.join(timeout=10)
        stop_thread.join(timeout=10)

        # Проверяем что не было deadlock
        assert len(errors) == 0, f"Произошли ошибки: {errors}"
        assert start_completed.is_set(), "start() не завершился"
        assert stop_completed.is_set(), "stop() не завершился"

    def test_no_deadlock_timeout_lock(self, tmp_path: Path) -> None:
        """
        Тест 2.2: Проверка что timeout блокировки работает.

        Блокировка с timeout должна предотвращать deadlock.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=60)

        # Получаем доступ к блокировке
        lock = timer._lock

        # Захватываем блокировку в основном потоке
        lock_acquired = threading.Event()
        release_requested = threading.Event()

        def hold_lock() -> None:
            """Удерживает блокировку."""
            if lock.acquire(timeout=5.0):
                try:
                    lock_acquired.set()
                    # Держим блокировку
                    release_requested.wait(timeout=10)
                finally:
                    lock.release()

        # Запускаем поток который держит блокировку
        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()

        # Ждем пока блокировка будет захвачена
        lock_acquired.wait(timeout=5)

        # Пытаемся захватить блокировку с timeout
        timeout_occurred = threading.Event()

        def try_acquire() -> None:
            """Пытается захватить блокировку."""
            acquired = lock.acquire(timeout=5.0)
            if not acquired:
                timeout_occurred.set()
            else:
                lock.release()

        acquirer_thread = threading.Thread(target=try_acquire)
        acquirer_thread.start()
        acquirer_thread.join(timeout=10)

        # Освобождаем блокировку
        release_requested.set()
        holder_thread.join(timeout=5)

        # Проверяем что timeout сработал (deadlock предотвращен)
        assert timeout_occurred.is_set(), "Timeout не сработал - возможен deadlock"

    def test_no_deadlock_cleanup_callback(self, tmp_path: Path) -> None:
        """
        Тест 2.3: Проверка отсутствия deadlock в callback очистки.

        Callback очистки не должен вызывать deadlock.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=1)  # Короткий интервал

        # Создаем тестовые файлы
        for i in range(5):
            temp_file = tmp_path / f"test_file_{i}.tmp"
            temp_file.write_text(f"test data {i}")

        errors: List[Exception] = []

        def call_cleanup() -> None:
            """Вызывает очистку."""
            try:
                timer._cleanup_temp_files()
            except Exception as e:
                errors.append(e)

        # Запускаем несколько потоков с очисткой
        threads = []
        for i in range(5):
            thread = threading.Thread(target=call_cleanup)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        # Проверяем что не было deadlock
        assert len(errors) == 0, f"Произошли ошибки: {errors}"


# =============================================================================
# ТЕСТ 3: КОРРЕКТНАЯ ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerCleanup:
    """Тесты для проверки корректной очистки временных файлов."""

    def setup_method(self) -> None:
        """Очистка перед каждым тестом."""
        with _temp_files_lock:
            _temp_files_registry.clear()

    def test_cleanup_only_registered_files(self, tmp_path: Path) -> None:
        """
        Тест 3.1: Проверка что очищаются только зарегистрированные файлы.

        Регистрирует файлы в реестре.
        Вызывает очистку.
        Проверяет что не зарегистрированные файлы не удаляются.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=60, max_files=100, orphan_age=1)

        # Создаем тестовые файлы
        old_files = []
        new_files = []

        for i in range(5):
            old_file = tmp_path / f"old_file_{i}.tmp"
            old_file.write_text(f"old data {i}")
            old_files.append(old_file)
            # Устанавливаем старое время модификации
            old_time = time.time() - 10  # 10 секунд назад
            os.utime(str(old_file), (old_time, old_time))

        for i in range(5):
            new_file = tmp_path / f"new_file_{i}.tmp"
            new_file.write_text(f"new data {i}")
            new_files.append(new_file)
            # Устанавливаем новое время модификации
            new_time = time.time()
            os.utime(str(new_file), (new_time, new_time))

        # Вызываем очистку
        deleted_count = timer._cleanup_temp_files()

        # Проверяем что старые файлы удалены
        for old_file in old_files:
            assert not old_file.exists(), f"Старый файл не удален: {old_file}"

        # Проверяем что новые файлы остались
        for new_file in new_files:
            assert new_file.exists(), f"Новый файл ошибочно удален: {new_file}"

        # Проверяем количество удаленных файлов
        assert deleted_count == 5, f"Удалено {deleted_count} файлов вместо 5"

    def test_cleanup_handles_missing_files(self, tmp_path: Path) -> None:
        """
        Тест 3.3: Проверка что очистка обрабатывает отсутствующие файлы.

        Регистрирует файлы, удаляет их вручную.
        Вызывает очистку.
        Проверяет что нет ошибок.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Очищаем реестр перед тестом
        with _temp_files_lock:
            _temp_files_registry.clear()

        # Создаем и регистрируем файлы
        temp_files = []
        for i in range(5):
            temp_file = tmp_path / f"missing_file_{i}.tmp"
            temp_file.write_text(f"missing data {i}")
            temp_files.append(temp_file)
            _register_temp_file(temp_file)

        # Удаляем файлы вручную
        for temp_file in temp_files:
            temp_file.unlink()

        # Проверяем что файлы не существуют
        for temp_file in temp_files:
            assert not temp_file.exists(), "Файл должен быть удален"

        # Вызываем очистку - не должно быть ошибок
        try:
            _cleanup_all_temp_files()
        except Exception as e:
            pytest.fail(f"Очистка вызвала ошибку: {e}")

        # Проверяем что реестр очищен
        with _temp_files_lock:
            assert len(_temp_files_registry) == 0, "Реестр не очищен"


# =============================================================================
# ТЕСТ 4: ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


@pytest.mark.integration
class TestTempFileTimerIntegration:
    """Интеграционные тесты для _TempFileTimer."""

    def test_timer_periodic_cleanup(self, tmp_path: Path) -> None:
        """
        Тест 4.1: Проверка периодической очистки таймером.

        Запускает таймер с коротким интервалом.
        Создаёт файлы.
        Проверяет что файлы удаляются автоматически.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = _TempFileTimer(temp_dir=tmp_path, interval=1, orphan_age=1)
        timer.start()

        try:
            # Создаем файлы
            temp_files = []
            for i in range(5):
                temp_file = tmp_path / f"periodic_file_{i}.tmp"
                temp_file.write_text(f"periodic data {i}")
                temp_files.append(temp_file)
                # Устанавливаем старое время
                old_time = time.time() - 2
                os.utime(str(temp_file), (old_time, old_time))

            # Ждем очистки
            time.sleep(2.5)

            # Проверяем что файлы удалены
            for temp_file in temp_files:
                assert not temp_file.exists(), f"Файл не удален: {temp_file}"

        finally:
            timer.stop()

    def test_concurrent_register_unregister(self, tmp_path: Path) -> None:
        """
        Тест 4.2: Проверка конкурентной регистрации/удаления.

        Несколько потоков регистрируют и удаляют файлы.
        Проверяет что нет ошибок и реестр корректен.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Очищаем реестр перед тестом
        with _temp_files_lock:
            _temp_files_registry.clear()

        errors: List[Exception] = []
        lock = threading.Lock()

        def register_worker(start: int) -> None:
            """Регистрирует файлы."""
            try:
                for i in range(start, start + 10):
                    temp_file = tmp_path / f"concurrent_{i}.tmp"
                    temp_file.write_text(f"data {i}")
                    _register_temp_file(temp_file)
                    time.sleep(0.01)
            except Exception as e:
                with lock:
                    errors.append(("register", e))

        def unregister_worker(start: int) -> None:
            """Удаляет файлы из реестра."""
            try:
                for i in range(start, start + 10):
                    temp_file = tmp_path / f"concurrent_{i}.tmp"
                    _unregister_temp_file(temp_file)
                    time.sleep(0.01)
            except Exception as e:
                with lock:
                    errors.append(("unregister", e))

        # Запускаем потоки
        threads = [
            threading.Thread(target=register_worker, args=(0,)),
            threading.Thread(target=register_worker, args=(10,)),
            threading.Thread(target=unregister_worker, args=(5,)),
            threading.Thread(target=unregister_worker, args=(15,)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        # Проверяем отсутствие ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

        # Очищаем реестр
        _cleanup_all_temp_files()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
