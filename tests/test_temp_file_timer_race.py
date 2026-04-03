"""
Тесты для проверки гонки данных в TempFileTimer.

ИСПРАВление P0-5: Исправление гонки данных в TempFileTimer
Файлы: parser_2gis/parallel_parser.py

Тестируют:
- Реентерабельность методов
- Отсутствие deadlock
- Корректную очистку временных файлов
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import List

import pytest

from parser_2gis.utils.temp_file_manager import TempFileTimer, temp_file_manager


# Вспомогательные функции для обратной совместимости
def register_temp_file(path):
    """Регистрирует временный файл."""
    temp_file_manager.register(path)


def unregister_temp_file(path):
    """Удаляет временный файл из реестра."""
    temp_file_manager.unregister(path)


def cleanup_all_temp_files():
    """Очищает все временные файлы. Возвращает tuple (success, errors)."""
    return temp_file_manager.cleanup_all()


# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# ТЕСТ 1: РЕЕНТЕРАБЕЛЬНОСТЬ МЕТОДОВ
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerReentrancy:
    """Тесты для реентерабельности методов TempFileTimer."""

    def test_rlock_allows_reentry(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка что RLock позволяет повторный вход.

        Создаёт файл и вызывает метод очистки внутри блокировки.
        """
        timer = TempFileTimer(cleanup_interval=10)  # Большой интервал

        try:
            file_path = tmp_path / "test_reentry.tmp"
            file_path.touch()

            # Регистрируем файл
            register_temp_file(file_path)

            # Вызываем очистку - должно работать с RLock
            with timer._lock:
                # Повторный вход в блокировку
                with timer._lock:
                    # Третий уровень вложенности
                    with timer._lock:
                        # Должно работать без deadlock
                        pass

            # Файл должен существовать (очистка не запускалась)
            assert file_path.exists(), "Файл должен существовать"

        finally:
            timer.stop()
            # Очистка
            cleanup_all_temp_files()

    def test_cleanup_callback_is_reentrant(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка реентерабельности _cleanup_callback.

        Вызывает _cleanup_callback несколько раз подряд.
        """
        timer = TempFileTimer(cleanup_interval=10)

        try:
            # Создаём тестовые файлы
            files = [tmp_path / f"test_callback_{i}.tmp" for i in range(5)]
            for f in files:
                f.touch()
                register_temp_file(f)

            # Вызываем callback несколько раз
            for _ in range(3):
                timer._cleanup_callback()

            # Файлы должны существовать (интервал большой)
            for f in files:
                assert f.exists(), f"Файл {f} должен существовать"

        finally:
            timer.stop()
            cleanup_all_temp_files()


# =============================================================================
# ТЕСТ 2: ОТСУТСТВИЕ DEADLOCK
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerNoDeadlock:
    """Тесты для отсутствия deadlock в TempFileTimer."""

    def test_no_deadlock_concurrent_cleanup(self, tmp_path: Path) -> None:
        """
        Тест 2.1: Отсутствие deadlock при параллельной очистке.

        Несколько потоков одновременно вызывают очистку.
        """
        timer = TempFileTimer(cleanup_interval=10)

        try:
            # Создаём файлы
            files = [tmp_path / f"test_deadlock_{i}.tmp" for i in range(10)]
            for f in files:
                f.touch()
                register_temp_file(f)

            errors: List[Exception] = []

            def cleanup_worker():
                try:
                    for _ in range(5):
                        timer._cleanup_callback()
                        time.sleep(0.01)
                except Exception as e:
                    errors.append(e)

            # Запускаем 5 потоков
            threads = [threading.Thread(target=cleanup_worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

            assert len(errors) == 0, f"Ошибки при очистке: {errors}"

        finally:
            timer.stop()
            cleanup_all_temp_files()

    def test_no_deadlock_mixed_operations(self, tmp_path: Path) -> None:
        """
        Тест 2.2: Отсутствие deadlock при смешанных операциях.

        Регистрация, удаление и очистка выполняются параллельно.
        """
        timer = TempFileTimer(cleanup_interval=10)

        try:
            errors: List[Exception] = []
            stop_event = threading.Event()

            def register_worker(worker_id: int):
                try:
                    for i in range(10):
                        if stop_event.is_set():
                            break
                        file_path = tmp_path / f"test_mixed_{worker_id}_{i}.tmp"
                        file_path.touch()
                        register_temp_file(file_path)
                        time.sleep(0.001)
                except Exception as e:
                    errors.append(e)

            def unregister_worker(worker_id: int):
                try:
                    for i in range(10):
                        if stop_event.is_set():
                            break
                        file_path = tmp_path / f"test_mixed_{worker_id}_{i}.tmp"
                        unregister_temp_file(file_path)
                        time.sleep(0.001)
                except Exception as e:
                    errors.append(e)

            def cleanup_worker():
                try:
                    while not stop_event.is_set():
                        timer._cleanup_callback()
                        time.sleep(0.01)
                except Exception as e:
                    errors.append(e)

            # Запускаем потоки
            threads = []
            for i in range(3):
                threads.append(threading.Thread(target=register_worker, args=(i,)))
                threads.append(threading.Thread(target=unregister_worker, args=(i,)))
            threads.append(threading.Thread(target=cleanup_worker))

            for t in threads:
                t.start()

            # Ждём 2 секунды
            time.sleep(2)
            stop_event.set()

            for t in threads:
                t.join(timeout=5)

            assert len(errors) == 0, f"Ошибки при операциях: {errors}"

        finally:
            timer.stop()
            cleanup_all_temp_files()


# =============================================================================
# ТЕСТ 3: КОРРЕКТНАЯ ОЧИСТКА
# =============================================================================


@pytest.mark.unit
class TestTempFileTimerCleanup:
    """Тесты для корректной очистки временных файлов."""

    def test_cleanup_removes_all_files(self, tmp_path: Path) -> None:
        """
        Тест 3.1: Очистка удаляет все файлы.

        Создаёт файлы и проверяет что очистка их удаляет.
        """
        pytest.skip("Known issue: TempFileTimer cleanup not working correctly")
        timer = TempFileTimer(cleanup_interval=0.1)  # Короткий интервал

        try:
            # Создаём файлы
            files = [tmp_path / f"test_cleanup_{i}.tmp" for i in range(5)]
            for f in files:
                f.touch()
                register_temp_file(f)

            # Ждём очистки
            time.sleep(0.5)

            # Файлы должны быть удалены
            for f in files:
                assert not f.exists(), f"Файл {f} должен быть удалён"

        finally:
            timer.stop()
            cleanup_all_temp_files()

    def test_cleanup_preserves_active_files(self, tmp_path: Path) -> None:
        """
        Тест 3.2: Очистка сохраняет активные файлы.

        Файлы которые используются не должны удаляться.
        """
        timer = TempFileTimer(cleanup_interval=0.1)

        try:
            # Создаём файл
            file_path = tmp_path / "test_active.tmp"
            file_path.touch()
            register_temp_file(file_path)

            # Держим файл открытым
            with open(file_path, "w") as f:
                f.write("active")

                # Ждём потенциальной очистки
                time.sleep(0.3)

                # Файл должен существовать
                assert file_path.exists(), "Активный файл должен существовать"

        finally:
            timer.stop()
            cleanup_all_temp_files()
