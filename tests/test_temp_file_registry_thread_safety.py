#!/usr/bin/env python3
"""
Тесты для проверки потокобезопасности temp_file_manager.

Проверяет что:
- temp_file_manager потокобезопасен
- Отсутствуют race condition при одновременном add/discard
- Блокировка temp_file_manager корректно работает
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import pytest

from parser_2gis.temp_file_manager import (
    cleanup_all_temp_files,
    register_temp_file,
    temp_file_manager,
    unregister_temp_file,
)


@pytest.fixture(autouse=True)
def cleanup_temp_file_registry():
    """Фикстура для очистки реестра временных файлов до и после каждого теста."""
    with temp_file_manager._lock:
        temp_file_manager._registry.clear()
    yield
    with temp_file_manager._lock:
        temp_file_manager._registry.clear()


class TestTempFileRegistryThreadSafety:
    """Тесты для проверки потокобезопасности реестра временных файлов."""

    def test_concurrent_registration_no_duplicates(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка отсутствия дубликатов при параллельной регистрации.

        Несколько потоков одновременно регистрируют файлы.
        Проверяет что в реестре нет дубликатов.
        """
        num_workers = 10
        files_per_worker = 20

        def worker(worker_id: int) -> List[Path]:
            files = []
            for i in range(files_per_worker):
                file_path = tmp_path / f"test_file_{worker_id}_{i}.tmp"
                register_temp_file(file_path)
                files.append(file_path)
            return files

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_workers)]
            all_files = []
            for f in as_completed(futures):
                all_files.extend(f.result())

        # Проверяем что нет дубликатов в реестре
        with temp_file_manager._lock:
            registry_set = set(temp_file_manager._registry)
            registry_list = list(temp_file_manager._registry)

        assert len(registry_set) == len(registry_list), (
            f"Обнаружены дубликаты в реестре: {len(registry_list)} записей, "
            f"но только {len(registry_set)} уникальных"
        )

    def test_concurrent_registration_and_unregistration(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Параллельная регистрация и удаление.

        Проверяет что регистрация и удаление потокобезопасны.
        """
        num_workers = 10
        files_per_worker = 10

        def register_worker(worker_id: int) -> List[Path]:
            files = []
            for i in range(files_per_worker):
                file_path = tmp_path / f"reg_file_{worker_id}_{i}.tmp"
                register_temp_file(file_path)
                files.append(file_path)
            return files

        def unregister_worker(worker_id: int, files: List[Path]) -> None:
            for file_path in files:
                unregister_temp_file(file_path)

        with ThreadPoolExecutor(max_workers=num_workers * 2) as executor:
            register_futures = [executor.submit(register_worker, i) for i in range(num_workers)]
            registered_files = []
            for f in as_completed(register_futures):
                registered_files.extend(f.result())

            unregister_futures = [
                executor.submit(unregister_worker, i, registered_files) for i in range(num_workers)
            ]
            for f in as_completed(unregister_futures):
                f.result()

        # Все файлы должны быть удалены
        with temp_file_manager._lock:
            assert len(temp_file_manager._registry) == 0, (
                f"Реестр должен быть пуст, но содержит {len(temp_file_manager._registry)} файлов"
            )

    def test_cleanup_all_is_thread_safe(self, tmp_path: Path) -> None:
        """
        Тест 1.3: Очистка всех файлов потокобезопасна.

        Проверяет что cleanup_all работает корректно в многопоточной среде.
        """
        num_workers = 5
        files_per_worker = 10

        def worker(worker_id: int) -> None:
            for i in range(files_per_worker):
                file_path = tmp_path / f"cleanup_file_{worker_id}_{i}.tmp"
                register_temp_file(file_path)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_workers)]
            for f in as_completed(futures):
                f.result()

        # Запускаем очистку
        success, errors = cleanup_all_temp_files()

        # Реестр должен быть пуст
        with temp_file_manager._lock:
            assert len(temp_file_manager._registry) == 0, (
                f"Реестр должен быть пуст после очистки, но содержит {len(temp_file_manager._registry)} файлов"
            )

        # Все файлы должны быть успешно удалены
        expected_files = num_workers * files_per_worker
        assert success == expected_files, (
            f"Ожидалось {expected_files} успешно удалённых файлов, но удалено {success}"
        )
        assert errors == 0, f"Ожидалось 0 ошибок при очистке, но получено {errors}"
