"""
Тесты для проверки потокобезопасности глобальных переменных.

Проверяет корректность работы _temp_files_registry с threading.RLock.
Тесты покрывают исправления из отчета FIXES_IMPLEMENTATION_REPORT.md:
- Потокобезопасность _temp_files_registry
- Timeout блокировки (5 секунд)
- Очистка временных файлов
"""

import threading
import time

import pytest


class TestTempFilesRegistryThreadSafety:
    """Тесты для проверки потокобезопасности реестра временных файлов."""

    def test_concurrent_file_registration(self, tmp_path):
        """
        Тест 2.1: Проверка _temp_files_registry с threading.RLock.

        Запускает несколько потоков одновременно.
        Каждый поток добавляет файл в реестр.
        Проверяет что нет race condition и все файлы добавлены.
        """
        from parser_2gis.parallel_parser import (
            _cleanup_all_temp_files,
            _register_temp_file,
            _temp_files_lock,
            _temp_files_registry,
        )

        # Очищаем реестр перед тестом
        with _temp_files_lock:
            _temp_files_registry.clear()

        # Создаем тестовые файлы
        num_threads = 10
        temp_files = [tmp_path / f"temp_file_{i}.csv" for i in range(num_threads)]
        for f in temp_files:
            f.write_text("test data")

        # Функция для регистрации файла в потоке
        def register_file(file_path):
            _register_temp_file(file_path)

        # Запускаем потоки
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=register_file, args=(temp_files[i],))
            threads.append(thread)
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()

        # Проверяем что все файлы добавлены в реестр
        with _temp_files_lock:
            assert len(_temp_files_registry) == num_threads, (
                f"Ожидалось {num_threads} файлов в реестре, "
                f"но найдено {_temp_files_registry}"
            )

            for f in temp_files:
                assert f in _temp_files_registry, f"Файл {f} не найден в реестре"

        # Очищаем реестр после теста
        _cleanup_all_temp_files()

    def test_lock_timeout_works(self, tmp_path):
        """
        Тест 2.2: Проверка timeout блокировки.

        Блокирует lock в одном потоке.
        Пытается получить lock в другом потоке.
        Проверяет что timeout работает (5 секунд) и нет deadlock.
        """
        from parser_2gis.parallel_parser import (
            _temp_files_lock,
        )

        lock_acquired = threading.Event()
        lock_release_requested = threading.Event()
        timeout_occurred = threading.Event()

        # Функция которая захватывает lock и держит его
        def hold_lock():
            # Напрямую захватываем lock
            if _temp_files_lock.acquire(timeout=5.0):
                try:
                    lock_acquired.set()
                    # Ждем сигнала освободить lock
                    lock_release_requested.wait(timeout=10)
                finally:
                    _temp_files_lock.release()

        # Функция которая пытается получить lock
        def try_acquire_lock():
            # Ждем пока первый поток захватит lock
            lock_acquired.wait(timeout=5)
            time.sleep(0.1)  # Небольшая задержка

            # Пытаемся получить lock с timeout
            start_time = time.time()
            acquired = _temp_files_lock.acquire(timeout=5.0)
            _elapsed = time.time() - start_time

            if not acquired:
                timeout_occurred.set()
            else:
                _temp_files_lock.release()

        # Запускаем поток который держит lock
        holder_thread = threading.Thread(target=hold_lock)
        holder_thread.start()

        # Запускаем поток который пытается получить lock
        waiter_thread = threading.Thread(target=try_acquire_lock)
        waiter_thread.start()

        # Ждем завершения
        waiter_thread.join(timeout=10)
        lock_release_requested.set()
        holder_thread.join(timeout=5)

        # Проверяем что timeout сработал
        assert timeout_occurred.is_set(), (
            "Timeout не сработал - возможна проблема с блокировкой"
        )

    def test_cleanup_removes_all_files(self, tmp_path):
        """
        Тест 2.3: Проверка очистки временных файлов.

        Регистрирует несколько файлов.
        Вызывает _cleanup_all_temp_files.
        Проверяет что все файлы удалены и реестр очищен.
        """
        from parser_2gis.parallel_parser import (
            _cleanup_all_temp_files,
            _register_temp_file,
            _temp_files_lock,
            _temp_files_registry,
        )

        # Очищаем реестр перед тестом
        with _temp_files_lock:
            _temp_files_registry.clear()

        # Создаем и регистрируем тестовые файлы
        num_files = 5
        temp_files = []
        for i in range(num_files):
            f = tmp_path / f"cleanup_test_{i}.csv"
            f.write_text("test data")
            temp_files.append(f)
            _register_temp_file(f)

        # Проверяем что файлы зарегистрированы
        with _temp_files_lock:
            assert len(_temp_files_registry) == num_files

        # Вызываем очистку
        _cleanup_all_temp_files()

        # Проверяем что все файлы удалены
        for f in temp_files:
            assert not f.exists(), f"Файл {f} не был удален при очистке"

        # Проверяем что реестр очищен
        with _temp_files_lock:
            assert len(_temp_files_registry) == 0, "Реестр не был очищен"


class TestRLockReentrancy:
    """Тесты для проверки рекурсивной блокировки RLock."""

    def test_rlock_allows_reentry(self):
        """
        Проверка что RLock позволяет повторный вход из того же потока.

        RLock должен позволять одному потоку захватывать lock несколько раз.
        """
        from parser_2gis.parallel_parser import _temp_files_lock

        acquired_count = 0

        def reentrant_acquire():
            nonlocal acquired_count
            # Первый захват
            if _temp_files_lock.acquire(timeout=5.0):
                try:
                    acquired_count += 1
                    # Второй захват из того же потока
                    if _temp_files_lock.acquire(timeout=5.0):
                        try:
                            acquired_count += 1
                        finally:
                            _temp_files_lock.release()
                finally:
                    _temp_files_lock.release()

        thread = threading.Thread(target=reentrant_acquire)
        thread.start()
        thread.join()

        # RLock должен позволить 2 захвата из одного потока
        assert acquired_count == 2, "RLock не позволил повторный вход"


class TestRegistryConcurrentModification:
    """Тесты для проверки одновременной модификации реестра."""

    def test_concurrent_add_remove(self, tmp_path):
        """
        Проверка одновременного добавления и удаления файлов.

        Один поток добавляет файлы, другой удаляет.
        Проверяет что нет race condition и ошибок.
        """
        from parser_2gis.parallel_parser import (
            _cleanup_all_temp_files,
            _register_temp_file,
            _temp_files_lock,
            _temp_files_registry,
            _unregister_temp_file,
        )

        # Очищаем реестр перед тестом
        with _temp_files_lock:
            _temp_files_registry.clear()

        errors = []

        # Функция добавления файлов
        def add_files():
            try:
                for i in range(10):
                    f = tmp_path / f"concurrent_{i}.csv"
                    f.write_text("test")
                    _register_temp_file(f)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Add error: {e}")

        # Функция удаления файлов
        def remove_files():
            try:
                for i in range(10):
                    time.sleep(0.005)  # Начинаем немного позже
                    f = tmp_path / f"concurrent_{i}.csv"
                    _unregister_temp_file(f)
            except Exception as e:
                errors.append(f"Remove error: {e}")

        # Запускаем потоки
        add_thread = threading.Thread(target=add_files)
        remove_thread = threading.Thread(target=remove_files)

        add_thread.start()
        remove_thread.start()

        add_thread.join()
        remove_thread.join()

        # Проверяем что не было ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

        # Очищаем реестр
        _cleanup_all_temp_files()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
