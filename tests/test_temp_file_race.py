"""Тесты для проверки race condition в _register_temp_file."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from parser_2gis.parallel_parser import (
    MAX_TEMP_FILES,
    _register_temp_file,
    _temp_files_lock,
    _temp_files_registry,
    _unregister_temp_file,
)


@pytest.fixture(autouse=True)
def cleanup_temp_files_registry():
    """Фикстура для очистки реестра временных файлов после каждого теста."""
    yield
    with _temp_files_lock:
        _temp_files_registry.clear()


class TestTempFileRaceCondition:
    """Тесты для проверки race condition в регистрации временных файлов."""

    def test_concurrent_registration_no_duplicates(self):
        """Параллельная регистрация не должна создавать дубликаты."""

        def worker(worker_id):
            for i in range(10):
                file_path = Path(f"/tmp/test_file_{worker_id}_{i}.tmp")
                _register_temp_file(file_path)
            return worker_id

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        with _temp_files_lock:
            assert len(results) == 10

    def test_concurrent_register_unregister(self):
        """Параллельная регистрация и удаление должны работать корректно."""
        results = []

        def register_worker(worker_id):
            for i in range(5):
                file_path = Path(f"/tmp/register_{worker_id}_{i}.tmp")
                _register_temp_file(file_path)
                results.append(("register", worker_id, i))

        def unregister_worker(worker_id):
            for i in range(5):
                file_path = Path(f"/tmp/unregister_{worker_id}_{i}.tmp")
                _register_temp_file(file_path)
                _unregister_temp_file(file_path)
                results.append(("unregister", worker_id, i))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(register_worker, i))
            for i in range(5):
                futures.append(executor.submit(unregister_worker, i))
            for f in as_completed(futures):
                f.result()

    def test_race_between_check_and_add(self):
        """Race между проверкой и добавлением не должен приводить к ошибкам."""
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    file_path = Path(f"/tmp/race_{worker_id}_{i}.tmp")
                    _register_temp_file(file_path)
            except Exception as e:
                errors.append((worker_id, e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_max_files_limit_respected(self):
        """Лимит на количество файлов должен соблюдаться."""
        try:
            for i in range(MAX_TEMP_FILES + 100):
                _register_temp_file(Path(f"/tmp/limit_test_{i}.tmp"))

            with _temp_files_lock:
                final_count = len(_temp_files_registry)
                assert final_count <= MAX_TEMP_FILES
        finally:
            with _temp_files_lock:
                _temp_files_registry.clear()

    def test_concurrent_eviction_no_crash(self):
        """Параллельное вытеснение не должно вызывать краш."""

        def worker(worker_id):
            for i in range(200):
                file_path = Path(f"/tmp/evict_{worker_id}_{i}.tmp")
                _register_temp_file(file_path)

        try:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker, i) for i in range(10)]
                for f in as_completed(futures):
                    f.result()
        finally:
            with _temp_files_lock:
                _temp_files_registry.clear()

    def test_unregister_thread_safety(self):
        """Удаление должно быть потокобезопасным."""
        errors = []

        for i in range(100):
            file_path = Path(f"/tmp/unreg_thread_{i}.tmp")
            _register_temp_file(file_path)

        def unregister_worker(start_idx):
            try:
                for i in range(start_idx, start_idx + 50):
                    if i % 2 == 0:
                        file_path = Path(f"/tmp/unreg_thread_{i}.tmp")
                        _unregister_temp_file(file_path)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=unregister_worker, args=(i * 50,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
