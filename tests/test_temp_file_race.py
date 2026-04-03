"""Тесты для проверки race condition в register_temp_file."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from parser_2gis.utils.temp_file_manager import temp_file_manager


# Вспомогательные функции для обратной совместимости
def register_temp_file(path):
    """Регистрирует временный файл."""
    temp_file_manager.register(path)


def unregister_temp_file(path):
    """Удаляет временный файл из реестра."""
    temp_file_manager.unregister(path)


@pytest.fixture(autouse=True)
def cleanup_temp_file_registry():
    """Фикстура для очистки реестра временных файлов после каждого теста."""
    yield
    with temp_file_manager._lock:
        temp_file_manager._registry.clear()


class TestTempFileRaceCondition:
    """Тесты для проверки race condition в регистрации временных файлов."""

    def test_concurrent_registration_no_duplicates(self):
        """Параллельная регистрация не должна создавать дубликаты."""

        def worker(worker_id):
            for i in range(10):
                file_path = Path(f"/tmp/test_file_{worker_id}_{i}.tmp")
                register_temp_file(file_path)
            return worker_id

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for f in as_completed(futures):
                f.result()

        # Проверяем что нет дубликатов
        with temp_file_manager._lock:
            unique_files = set(temp_file_manager._registry)
            registered_count = len(temp_file_manager._registry)

        assert len(unique_files) == registered_count, (
            f"Обнаружены дубликаты: {registered_count} зарегистрировано, "
            f"но только {len(unique_files)} уникальных"
        )

    def test_concurrent_registration_and_unregistration(self):
        """Параллельная регистрация и удаление должны быть безопасны."""
        num_workers = 10
        files_per_worker = 5

        def register_worker(worker_id):
            for i in range(files_per_worker):
                file_path = Path(f"/tmp/test_reg_{worker_id}_{i}.tmp")
                register_temp_file(file_path)
            return worker_id

        def unregister_worker(worker_id):
            for i in range(files_per_worker):
                file_path = Path(f"/tmp/test_reg_{worker_id}_{i}.tmp")
                unregister_temp_file(file_path)
            return worker_id

        with ThreadPoolExecutor(max_workers=num_workers * 2) as executor:
            # Сначала регистрируем
            register_futures = [executor.submit(register_worker, i) for i in range(num_workers)]
            for f in as_completed(register_futures):
                f.result()

            # Затем удаляем
            unregister_futures = [executor.submit(unregister_worker, i) for i in range(num_workers)]
            for f in as_completed(unregister_futures):
                f.result()

        # Все файлы должны быть удалены
        with temp_file_manager._lock:
            assert len(temp_file_manager._registry) == 0, (
                f"Реестр должен быть пуст, но содержит {len(temp_file_manager._registry)} файлов"
            )

    def test_thread_safe_registry_operations(self):
        """Операции реестра должны быть потокобезопасными."""
        errors = []

        def worker(worker_id):
            try:
                for i in range(20):
                    file_path = Path(f"/tmp/test_thread_{worker_id}_{i}.tmp")
                    register_temp_file(file_path)
                    unregister_temp_file(file_path)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"

        with temp_file_manager._lock:
            assert len(temp_file_manager._registry) == 0, (
                "Реестр должен быть пуст после всех операций"
            )
