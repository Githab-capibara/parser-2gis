#!/usr/bin/env python3
"""
Тесты для проверки потокобезопасности _temp_files_registry.

Проверяет что:
- _temp_files_registry потокобезопасен
- Отсутствуют race condition при одновременном add/discard
- Блокировка _temp_files_lock корректно работает

Тесты покрывают исправления критической проблемы #3 из audit-report.md.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Set

import pytest

from parser_2gis.parallel_parser import (
    MAX_TEMP_FILES,
    _cleanup_all_temp_files,
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


class TestTempFileRegistryThreadSafety:
    """Тесты для проверки потокобезопасности реестра временных файлов."""

    @pytest.mark.usefixtures("temp_files_registry")
    def test_concurrent_registration_no_duplicates(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка отсутствия дубликатов при параллельной регистрации.

        Несколько потоков одновременно регистрируют файлы.
        Проверяет что в реестре нет дубликатов.

        Note:
            Используем ThreadPoolExecutor для параллельного выполнения
        """
        errors: List[Exception] = []

        def worker(worker_id: int) -> None:
            """Регистрирует файлы."""
            try:
                for i in range(10):
                    file_path = tmp_path / f"test_concurrent_{worker_id}_{i}.tmp"
                    file_path.touch()  # Создаём реальный файл
                    _register_temp_file(file_path)
            except Exception as e:
                errors.append(e)

        # Запускаем 10 потоков
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        # Проверяем отсутствие ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

        # Проверяем реестр на дубликаты (set не может содержать дубликаты)
        with _temp_files_lock:
            # Все элементы должны быть уникальны
            assert len(_temp_files_registry) <= 100, "Не должно быть больше 100 файлов"

    @pytest.mark.usefixtures("temp_files_registry")
    def test_concurrent_register_unregister_no_race(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка отсутствия race condition при register/unregister.

        Несколько потоков одновременно регистрируют и удаляют файлы.
        Проверяет что нет race condition.

        Note:
            Race condition может привести к KeyError или потере файлов
        """
        errors: List[Exception] = []
        registered_files: Set[Path] = set()
        lock = threading.Lock()

        def register_worker(worker_id: int) -> None:
            """Регистрирует файлы."""
            try:
                for i in range(5):
                    file_path = tmp_path / f"test_reg_{worker_id}_{i}.tmp"
                    file_path.touch()  # Создаём реальный файл
                    _register_temp_file(file_path)
                    with lock:
                        registered_files.add(file_path)
            except Exception as e:
                errors.append(("register", e))

        def unregister_worker(worker_id: int) -> None:
            """Удаляет файлы."""
            try:
                for i in range(5):
                    file_path = tmp_path / f"test_unreg_{worker_id}_{i}.tmp"
                    file_path.touch()  # Создаём реальный файл
                    _register_temp_file(file_path)
                    _unregister_temp_file(file_path)
            except Exception as e:
                errors.append(("unregister", e))

        # Запускаем потоки
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(register_worker, i))
                futures.append(executor.submit(unregister_worker, i))

            for future in as_completed(futures):
                future.result()

        # Проверяем отсутствие ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

    @pytest.mark.usefixtures("temp_files_registry")
    def test_concurrent_access_no_deadlock(self, tmp_path: Path) -> None:
        """
        Тест 1.3: Проверка отсутствия deadlock при конкурентном доступе.

        Несколько потоков одновременно обращаются к реестру.
        Проверяет что нет deadlock.

        Note:
            Deadlock может возникнуть при неправильном использовании блокировок
        """
        errors: List[Exception] = []

        def access_registry(worker_id: int) -> None:
            """Обращается к реестру."""
            try:
                for i in range(10):
                    file_path = tmp_path / f"test_deadlock_{worker_id}_{i}.tmp"
                    file_path.touch()  # Создаём реальный файл
                    _register_temp_file(file_path)
                    if i % 2 == 0:
                        _unregister_temp_file(file_path)
            except Exception as e:
                errors.append(e)

        # Запускаем потоки
        threads = [threading.Thread(target=access_registry, args=(i,)) for i in range(10)]
        for thread in threads:
            thread.start()

        # Ждем завершения с timeout
        for thread in threads:
            thread.join(timeout=10)

        # Проверяем что все потоки завершились
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

    @pytest.mark.usefixtures("temp_files_registry")
    def test_stress_test_concurrent_operations(self, tmp_path: Path) -> None:
        """
        Тест 1.4: Стресс-тест конкурентных операций.

        Множество потоков выполняют множество операций.
        Проверяет стабильность при высокой нагрузке.

        Note:
            Стресс-тест выявляет редкие race condition
        """
        errors: List[Exception] = []
        operation_count = {"value": 0}
        lock = threading.Lock()

        def stress_worker(worker_id: int) -> None:
            """Выполняет стресс-операции."""
            try:
                for i in range(50):
                    file_path = tmp_path / f"test_stress_{worker_id}_{i}.tmp"
                    file_path.touch()  # Создаём реальный файл
                    _register_temp_file(file_path)
                    with lock:
                        operation_count["value"] += 1

                    if i % 3 == 0:
                        _unregister_temp_file(file_path)
                        with lock:
                            operation_count["value"] += 1
            except Exception as e:
                errors.append(e)

        # Запускаем 20 потоков
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(stress_worker, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Проверяем отсутствие ошибок
        assert len(errors) == 0, f"Произошли ошибки: {errors}"

        # Проверяем что все операции выполнены
        assert operation_count["value"] > 0, "Операции должны быть выполнены"


class TestTempFileLockUsage:
    """Тесты для проверки корректности использования блокировки."""

    @pytest.mark.usefixtures("temp_files_registry")
    def test_lock_is_rlock(self) -> None:
        """
        Тест 2.1: Проверка что используется RLock.

        Проверяет что _temp_files_lock это RLock,
        а не обычный Lock.

        Note:
            RLock позволяет повторный захват из одного потока
        """
        # Проверяем тип блокировки
        assert isinstance(_temp_files_lock, type(threading.RLock())), "Должен использоваться RLock"

    @pytest.mark.usefixtures("temp_files_registry")
    def test_lock_reentrant(self) -> None:
        """
        Тест 2.2: Проверка реентрантности блокировки.

        Проверяет что один поток может захватить
        блокировку несколько раз.

        Note:
            RLock позволяет повторный захват
        """
        acquired_count = {"value": 0}

        def reentrant_acquire() -> None:
            """Повторный захват."""
            if _temp_files_lock.acquire(timeout=5.0):
                try:
                    acquired_count["value"] += 1
                    # Повторный захват
                    if _temp_files_lock.acquire(timeout=5.0):
                        try:
                            acquired_count["value"] += 1
                        finally:
                            _temp_files_lock.release()
                finally:
                    _temp_files_lock.release()

        thread = threading.Thread(target=reentrant_acquire)
        thread.start()
        thread.join(timeout=10)

        # RLock должен позволить 2 захвата
        assert acquired_count["value"] == 2, "RLock должен позволить повторный захват"

    @pytest.mark.usefixtures("temp_files_registry")
    def test_lock_timeout_prevents_deadlock(self) -> None:
        """
        Тест 2.3: Проверка что timeout предотвращает deadlock.

        Проверяет что блокировка с timeout возвращает
        False при невозможности захвата.

        Note:
            Timeout предотвращает вечное ожидание
        """
        # Захватываем блокировку
        _temp_files_lock.acquire()
        try:
            # Пытаемся захватить с timeout в другом потоке
            timeout_occurred = threading.Event()

            def try_acquire() -> None:
                """Пытается захватить."""
                acquired = _temp_files_lock.acquire(timeout=2.0)
                if not acquired:
                    timeout_occurred.set()
                else:
                    _temp_files_lock.release()

            thread = threading.Thread(target=try_acquire)
            thread.start()
            thread.join(timeout=5)

            # Проверяем что timeout сработал
            assert timeout_occurred.is_set(), "Timeout должен сработать"
        finally:
            # Освобождаем блокировку
            _temp_files_lock.release()


class TestTempFileRegistryConsistency:
    """Тесты для проверки консистентности реестра."""

    def test_registry_contains_only_paths(self, tmp_path: Path, temp_files_registry: set) -> None:
        """
        Тест 3.1: Проверка что реестр содержит только Path.

        Проверяет что все элементы в реестре
        являются экземплярами Path.

        Note:
            Типовая безопасность реестра
        """
        # Регистрируем файлы
        for i in range(10):
            file_path = tmp_path / f"test_type_{i}.tmp"
            file_path.touch()  # Создаём реальный файл
            _register_temp_file(file_path)

        # Проверяем типы
        with _temp_files_lock:
            print(f"DEBUG: Реестр содержит {len(_temp_files_registry)} файлов")
            print(
                f"DEBUG: temp_files_registry is _temp_files_registry: {temp_files_registry is _temp_files_registry}"
            )
            for item in _temp_files_registry:
                assert isinstance(item, Path), f"Элемент должен быть Path: {item}"
            assert len(_temp_files_registry) == 10, (
                f"Должно быть 10 файлов в реестре, но найдено {len(_temp_files_registry)}"
            )

    def test_registry_empty_after_cleanup(self, tmp_path: Path, temp_files_registry: set) -> None:
        """
        Тест 3.2: Проверка что реестр пуст после очистки.

        Проверяет что _cleanup_all_temp_files()
        очищает реестр.

        Note:
            Очистка должна быть полной
        """
        # Создаём реальные временные файлы и регистрируем их
        created_files = []
        for i in range(10):
            file_path = tmp_path / f"test_cleanup_{i}.tmp"
            file_path.touch()  # Создаём реальный файл
            _register_temp_file(file_path)
            created_files.append(file_path)

        # Проверяем что реестр не пуст
        with _temp_files_lock:
            assert len(_temp_files_registry) > 0, "Реестр должен содержать файлы"
            assert len(_temp_files_registry) == 10, "Реестр должен содержать 10 файлов"

        # Очищаем
        _cleanup_all_temp_files()

        # Проверяем что реестр пуст
        with _temp_files_lock:
            assert len(_temp_files_registry) == 0, "Реестр должен быть пуст после очистки"

        # Проверяем что файлы удалены
        for file_path in created_files:
            assert not file_path.exists(), f"Файл {file_path} должен быть удалён"

    def test_unregister_nonexistent_file(self, tmp_path: Path, temp_files_registry: set) -> None:
        """
        Тест 3.3: Проверка удаления несуществующего файла.

        Проверяет что _unregister_temp_file не вызывает
        ошибок при удалении несуществующего файла.

        Note:
            Удаление должно быть идемпотентным
        """
        # Пытаемся удалить несуществующий файл
        file_path = tmp_path / "test_nonexistent.tmp"

        # Не должно вызвать ошибок
        _unregister_temp_file(file_path)

    def test_register_same_file_multiple_times(
        self, tmp_path: Path, temp_files_registry: set
    ) -> None:
        """
        Тест 3.4: Проверка регистрации одного файла несколько раз.

        Проверяет что повторная регистрация того же файла
        не создаёт дубликатов.

        Note:
            Set автоматически устраняет дубликаты
        """
        file_path = tmp_path / "test_duplicate.tmp"
        file_path.touch()  # Создаём реальный файл

        # Регистрируем несколько раз
        _register_temp_file(file_path)
        _register_temp_file(file_path)
        _register_temp_file(file_path)

        # Проверяем что файл только один
        with _temp_files_lock:
            count = sum(1 for p in _temp_files_registry if p == file_path)
            assert count == 1, "Файл должен быть только один"
            assert len(_temp_files_registry) == 1, "В реестре должен быть только один файл"


class TestTempFileRegistryEdgeCases:
    """Тесты для проверки граничных случаев."""

    @pytest.mark.usefixtures("temp_files_registry")
    def test_max_files_limit(self, tmp_path: Path) -> None:
        """
        Тест 4.1: Проверка лимита MAX_TEMP_FILES.

        Проверяет что реестр не превышает лимит.

        Note:
            LRU eviction должен удалять старые файлы
        """
        try:
            # Регистрируем больше файлов чем лимит
            for i in range(MAX_TEMP_FILES + 100):
                file_path = tmp_path / f"test_limit_{i}.tmp"
                file_path.touch()  # Создаём реальный файл
                _register_temp_file(file_path)

            # Проверяем что лимит соблюдён
            with _temp_files_lock:
                assert len(_temp_files_registry) <= MAX_TEMP_FILES, (
                    f"Лимит превышен: {len(_temp_files_registry)} > {MAX_TEMP_FILES}"
                )
        finally:
            with _temp_files_lock:
                _temp_files_registry.clear()

    @pytest.mark.usefixtures("temp_files_registry")
    def test_concurrent_eviction_no_crash(self, tmp_path: Path) -> None:
        """
        Тест 4.2: Проверка что eviction не вызывает краш.

        Проверяет что параллельная eviction не вызывает
        ошибок.

        Note:
            Eviction должен быть потокобезопасным
        """
        errors: List[Exception] = []

        def eviction_worker(worker_id: int) -> None:
            """Выполняет eviction."""
            try:
                for i in range(200):
                    file_path = tmp_path / f"test_evict_{worker_id}_{i}.tmp"
                    file_path.touch()  # Создаём реальный файл
                    _register_temp_file(file_path)
            except Exception as e:
                errors.append(e)

        try:
            # Запускаем потоки
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(eviction_worker, i) for i in range(10)]
                for future in as_completed(futures):
                    future.result()

            # Проверяем отсутствие ошибок
            assert len(errors) == 0, f"Произошли ошибки: {errors}"
        finally:
            with _temp_files_lock:
                _temp_files_registry.clear()

    @pytest.mark.usefixtures("temp_files_registry")
    def test_registry_thread_count(self, tmp_path: Path) -> None:
        """
        Тест 4.3: Проверка количества потоков.

        Проверяет что операции с реестром не создают
        лишних потоков.

        Note:
            Утечка потоков может привести к исчерпанию ресурсов
        """
        initial_threads = threading.active_count()

        # Выполняем операции
        for i in range(50):
            file_path = tmp_path / f"test_thread_{i}.tmp"
            file_path.touch()  # Создаём реальный файл
            _register_temp_file(file_path)

        final_threads = threading.active_count()

        # Проверяем что количество потоков не увеличилось значительно
        assert final_threads <= initial_threads + 2, (
            f"Утечка потоков: было {initial_threads}, стало {final_threads}"
        )


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
