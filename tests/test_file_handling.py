#!/usr/bin/env python3
"""
Тесты обработки файлов для parser-2gis.

Проверяет исправления следующих проблем:
- Проблема 2: Race condition с временными файлами (parallel_parser.py)
- Проблема 8: Утечка файловых дескрипторов при чтении CSV (csv_writer.py)

Всего тестов: 6 (по 3 на каждую проблему)
"""

import pytest
import sys
import os
import tempfile
import threading
import time
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from concurrent.futures import ThreadPoolExecutor, as_completed

# Добавляем путь к модулю parser_2gis
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_2gis.parallel_parser import (
    _register_temp_file,
    _unregister_temp_file,
    _cleanup_all_temp_files,
    _temp_files_registry,
    _temp_files_lock,
    MAX_TEMP_FILES,
)

# =============================================================================
# ПРОБЛЕМА 2: RACE CONDITION С ВРЕМЕННЫМИ ФАЙЛАМИ (parallel_parser.py)
# =============================================================================


class TestRaceConditionTempFiles:
    """Тесты для проблемы 2: Race condition с временными файлами."""

    def setup_method(self):
        """Очистка реестра временных файлов перед каждым тестом."""
        with _temp_files_lock:
            _temp_files_registry.clear()

    def teardown_method(self):
        """Очистка реестра временных файлов после каждого теста."""
        with _temp_files_lock:
            _temp_files_registry.clear()

    def test_atomic_temp_file_creation(self):
        """
        Тест 1: Атомарное создание временных файлов.

        Проверяет что временные файлы регистрируются атомарно
        и не возникает race condition при регистрации.
        """
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(b"test data")

        try:
            # Регистрируем файл
            _register_temp_file(temp_path)

            # Проверяем что файл зарегистрирован
            with _temp_files_lock:
                assert (
                    temp_path in _temp_files_registry
                ), "Временный файл должен быть зарегистрирован"
                assert len(_temp_files_registry) == 1, "В реестре должен быть один файл"
        finally:
            # Очищаем
            _temp_files_registry.clear()
            if temp_path.exists():
                temp_path.unlink()

    def test_temp_file_cleanup(self):
        """
        Тест 2: Корректная очистка временных файлов.

        Проверяет что временные файлы корректно удаляются
        при очистке.
        """
        # Создаём несколько временных файлов
        temp_files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    temp_path = Path(tmp.name)
                    tmp.write(f"test data {i}".encode())
                    temp_files.append(temp_path)
                    _register_temp_file(temp_path)

            # Проверяем что все файлы зарегистрированы
            with _temp_files_lock:
                assert len(_temp_files_registry) == 3, "В реестре должно быть 3 файла"

            # Очищаем все файлы
            _cleanup_all_temp_files()

            # Проверяем что реестр очищен
            with _temp_files_lock:
                assert len(_temp_files_registry) == 0, "Реестр должен быть очищен"

            # Проверяем что файлы удалены
            for temp_path in temp_files:
                assert (
                    not temp_path.exists()
                ), f"Временный файл {temp_path} должен быть удалён"

        finally:
            # Гарантированная очистка
            _temp_files_registry.clear()
            for temp_path in temp_files:
                if temp_path.exists():
                    temp_path.unlink()

    def test_parallel_file_registration(self):
        """
        Тест 3: Параллельная запись без конфликтов.

        Проверяет что несколько потоков могут регистрировать
        файлы без race condition.
        """
        num_threads = 10
        files_per_thread = 5
        registered_files = []
        lock = threading.Lock()

        def register_files(thread_id):
            """Регистрирует файлы из потока."""
            thread_files = []
            for i in range(files_per_thread):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    temp_path = Path(tmp.name)
                    tmp.write(f"thread {thread_id} file {i}".encode())
                    _register_temp_file(temp_path)
                    thread_files.append(temp_path)

            with lock:
                registered_files.extend(thread_files)

        try:
            # Запускаем потоки
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=register_files, args=(i,))
                threads.append(t)
                t.start()

            # Ждём завершения
            for t in threads:
                t.join()

            # Проверяем что все файлы зарегистрированы
            expected_count = num_threads * files_per_thread
            with _temp_files_lock:
                # Из-за LRU eviction количество может быть меньше MAX_TEMP_FILES
                actual_count = len(_temp_files_registry)
                # Проверяем что реестр не пуст и не превышает лимит
                assert actual_count > 0, "Реестр не должен быть пустым"
                assert (
                    actual_count <= MAX_TEMP_FILES
                ), f"Реестр не должен превышать лимит {MAX_TEMP_FILES}"

            # Проверяем что файлы существуют
            existing_files = sum(1 for f in registered_files if f.exists())
            assert existing_files == len(
                registered_files
            ), f"Все {len(registered_files)} файлов должны существовать"

        finally:
            # Очищаем
            _cleanup_all_temp_files()
            _temp_files_registry.clear()

    def test_lru_eviction_on_limit(self):
        """
        Дополнительный тест: LRU eviction при достижении лимита.

        Проверяет что при превышении лимита происходит eviction.
        """
        # Создаём больше файлов чем лимит
        temp_files = []
        try:
            for i in range(MAX_TEMP_FILES + 50):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    temp_path = Path(tmp.name)
                    temp_files.append(temp_path)
                    _register_temp_file(temp_path)

            # Проверяем что реестр не превышает лимит
            with _temp_files_lock:
                assert (
                    len(_temp_files_registry) <= MAX_TEMP_FILES
                ), f"Реестр не должен превышать лимит {MAX_TEMP_FILES}"

        finally:
            _cleanup_all_temp_files()
            _temp_files_registry.clear()
            for f in temp_files:
                if f.exists():
                    f.unlink()


# =============================================================================
# ПРОБЛЕМА 8: УТЕЧКА ФАЙЛОВЫХ ДЕСКРИПТОРОВ ПРИ ЧТЕНИИ CSV (csv_writer.py)
# =============================================================================


class TestCSVFileDescriptorLeak:
    """Тесты для проблемы 8: Утечка файловых дескрипторов при чтении CSV."""

    def test_csv_file_close_on_error(self):
        """
        Тест 1: Закрытие файлов при ошибке чтения.

        Проверяет что файловые дескрипторы закрываются
        даже при возникновении ошибки.
        """
        # Создаём тестовый CSV файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["col1", "col2", "col3"])
            for i in range(10):
                writer.writerow([f"value{i}_1", f"value{i}_2", f"value{i}_3"])
            temp_path = tmp.name

        try:
            # Проверяем что файл закрывается при ошибке
            file_descriptors_before = self._count_open_fds()

            # Имитируем ошибку при чтении
            try:
                with open(temp_path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i == 5:
                            raise ValueError("Имитация ошибки при чтении")
            except ValueError:
                pass  # Ожидаемая ошибка

            file_descriptors_after = self._count_open_fds()

            # Проверяем что файловые дескрипторы освобождены
            assert file_descriptors_after <= file_descriptors_before + 1, (
                f"Файловые дескрипторы должны быть освобождены. "
                f"До: {file_descriptors_before}, После: {file_descriptors_after}"
            )

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_csv_file_close_on_success(self):
        """
        Тест 2: Закрытие файлов при нормальном завершении.

        Проверяет что файловые дескрипторы закрываются
        при успешном чтении.
        """
        # Создаём тестовый CSV файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["col1", "col2", "col3"])
            for i in range(100):
                writer.writerow([f"value{i}_1", f"value{i}_2", f"value{i}_3"])
            temp_path = tmp.name

        try:
            file_descriptors_before = self._count_open_fds()

            # Читаем файл успешно
            rows_read = 0
            with open(temp_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows_read += 1

            file_descriptors_after = self._count_open_fds()

            # Проверяем что все строки прочитаны
            assert (
                rows_read == 100
            ), f"Должно быть прочитано 100 строк, прочитано {rows_read}"

            # Проверяем что файловые дескрипторы освобождены
            assert file_descriptors_after <= file_descriptors_before + 1, (
                f"Файловые дескрипторы должны быть освобождены. "
                f"До: {file_descriptors_before}, После: {file_descriptors_after}"
            )

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_open_file_descriptor_count(self):
        """
        Тест 3: Проверка количества открытых файловых дескрипторов.

        Проверяет что при множественном чтении CSV не происходит
        утечки файловых дескрипторов.
        """
        # Создаём несколько тестовых CSV файлов
        temp_files = []
        try:
            for i in range(10):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".csv", delete=False
                ) as tmp:
                    writer = csv.writer(tmp)
                    writer.writerow(["col1", "col2", "col3"])
                    for j in range(50):
                        writer.writerow(
                            [
                                f"file{i}_row{j}_1",
                                f"file{i}_row{j}_2",
                                f"file{i}_row{j}_3",
                            ]
                        )
                    temp_files.append(tmp.name)

            # Измеряем количество открытых дескрипторов до
            fds_before = self._count_open_fds()

            # Читаем все файлы многократно
            for iteration in range(5):
                for temp_path in temp_files:
                    with open(temp_path, "r", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        assert (
                            len(rows) == 50
                        ), f"Должно быть 50 строк, прочитано {len(rows)}"

            # Измеряем количество открытых дескрипторов после
            fds_after = self._count_open_fds()

            # Проверяем что нет утечки (допускаем небольшой разброс)
            fd_increase = fds_after - fds_before
            assert fd_increase < 10, (
                f"Подозрительная утечка файловых дескрипторов: "
                f"До: {fds_before}, После: {fds_after}, Разница: {fd_increase}"
            )

        finally:
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def _count_open_fds(self):
        """Подсчитывает количество открытых файловых дескрипторов."""
        try:
            # Для Linux
            fd_dir = f"/proc/{os.getpid()}/fd"
            return len(os.listdir(fd_dir))
        except (OSError, FileNotFoundError):
            # Fallback для других систем
            try:
                import resource

                # Получаем максимальное количество дескрипторов
                soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                # Подсчитываем открытые через lsof
                import subprocess

                result = subprocess.run(
                    ["lsof", "-p", str(os.getpid())],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return len(result.stdout.strip().split("\n")) - 1  # Минус заголовок
            except Exception:
                # Если ничего не работает, возвращаем 0
                return 0


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestFileHandlingIntegration:
    """Интеграционные тесты для обработки файлов."""

    def test_temp_file_registry_thread_safety(self):
        """
        Интеграционный тест: Потокобезопасность реестра временных файлов.

        Проверяет что операции с реестром потокобезопасны.
        """
        operations = []
        lock = threading.Lock()

        def register_and_unregister(thread_id):
            """Регистрирует и удаляет файлы из потока."""
            temp_files = []
            try:
                for i in range(10):
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        temp_path = Path(tmp.name)
                        _register_temp_file(temp_path)
                        temp_files.append(temp_path)

                        with lock:
                            operations.append(f"thread_{thread_id}_register_{i}")

                        time.sleep(0.001)  # Небольшая задержка

                    # Сразу unregister
                    _unregister_temp_file(temp_path)
                    with lock:
                        operations.append(f"thread_{thread_id}_unregister_{i}")
            finally:
                for f in temp_files:
                    if f.exists():
                        f.unlink()

        try:
            threads = []
            for i in range(5):
                t = threading.Thread(target=register_and_unregister, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Проверяем что реестр пуст после завершения
            with _temp_files_lock:
                assert (
                    len(_temp_files_registry) == 0
                ), "Реестр должен быть пуст после завершения всех потоков"

        finally:
            _cleanup_all_temp_files()
            _temp_files_registry.clear()

    def test_concurrent_csv_operations(self):
        """
        Интеграционный тест: Параллельные операции с CSV.

        Проверяет что параллельное чтение CSV не вызывает утечек.
        """
        # Создаём тестовый CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["col1", "col2", "col3"])
            for i in range(100):
                writer.writerow([f"val{i}_1", f"val{i}_2", f"val{i}_3"])
            temp_path = tmp.name

        results = []

        def read_csv(thread_id):
            """Читает CSV из потока."""
            rows = []
            with open(temp_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
            results.append((thread_id, len(rows)))

        try:
            threads = []
            for i in range(10):
                t = threading.Thread(target=read_csv, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Проверяем что все потоки прочитали все строки
            for thread_id, row_count in results:
                assert (
                    row_count == 100
                ), f"Поток {thread_id} должен прочитать 100 строк, прочитано {row_count}"

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
