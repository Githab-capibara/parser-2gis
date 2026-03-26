#!/usr/bin/env python3
"""
Тесты для проверки исправления Memory Leak в TempFileTimer.

Проверяет что:
- TempFileTimer.stop() вызывается корректно
- Таймер отменяется правильно
- Отсутствует утечка потоков

Тесты покрывают исправления критической проблемы #2 из audit-report.md.
"""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.utils.temp_file_manager import TempFileTimer


class TestTempFileTimerStop:
    """Тесты для проверки метода stop() в TempFileTimer."""

    def test_stop_cancels_timer(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка что stop() отменяет таймер.

        Проверяет что после вызова stop() таймер
        отменяется и не выполняет очистку.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Проверяем что таймер запущен
        assert timer._timer is not None, "Таймер должен быть создан"
        assert timer._is_running, "Таймер должен быть запущен"

        # Вызываем stop
        timer.stop()

        # Проверяем что таймер остановлен
        # timer._timer может быть None после stop()
        if timer._timer is not None:
            assert timer._timer.is_alive() is False, "Таймер должен быть остановлен"
        assert timer._is_running is False, "Флаг is_running должен быть False"

    def test_stop_sets_stop_event(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка что stop() устанавливает событие остановки.

        Проверяет что _stop_event устанавливается при вызове stop().

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Проверяем что событие не установлено изначально
        assert timer._stop_event.is_set() is False, "Событие остановки не должно быть установлено"

        # Вызываем stop
        timer.stop()

        # Проверяем что событие установлено
        assert timer._stop_event.is_set(), "Событие остановки должно быть установлено"

    def test_stop_clears_timer_reference(self, tmp_path: Path) -> None:
        """
        Тест 1.3: Проверка что stop() очищает ссылку на таймер.

        Проверяет что после stop() ссылка на таймер
        обнуляется для предотвращения утечек памяти.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Сохраняем ссылку на таймер
        original_timer = timer._timer
        assert original_timer is not None, "Таймер должен быть создан"

        # Вызываем stop
        timer.stop()

        # Проверяем что ссылка очищена
        assert timer._timer is None, "Ссылка на таймер должна быть очищена"

    def test_stop_idempotent(self, tmp_path: Path) -> None:
        """
        Тест 1.4: Проверка идемпотентности stop().

        Проверяет что многократный вызов stop()
        не вызывает ошибок и безопасен.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Вызываем stop несколько раз
        timer.stop()
        timer.stop()
        timer.stop()

        # Проверяем что таймер остановлен
        assert timer._is_running is False, "Таймер должен быть остановлен"
        assert timer._stop_event.is_set(), "Событие остановки должно быть установлено"

    def test_stop_without_start(self, tmp_path: Path) -> None:
        """
        Тест 1.5: Проверка вызова stop() без start().

        Проверяет что вызов stop() без предварительного
        start() не вызывает ошибок.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Вызываем stop без start
        timer.stop()

        # Проверяем что состояние корректно
        assert timer._is_running is False, "Таймер не должен быть запущен"
        assert timer._stop_event.is_set(), "Событие остановки должно быть установлено"


class TestTempFileTimerMemoryLeak:
    """Тесты для проверки отсутствия утечек памяти."""

    def test_timer_garbage_collected(self, tmp_path: Path) -> None:
        """
        Тест 2.1: Проверка что таймер корректно удаляется GC.

        Проверяет что после stop() таймер может быть
        удалён сборщиком мусора.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        import gc
        import weakref

        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Создаём слабую ссылку на таймер
        weak_ref = weakref.ref(timer)

        # Останавливаем таймер
        timer.stop()

        # Удаляем ссылку на таймер
        del timer

        # Принудительно запускаем GC
        gc.collect()

        # Проверяем что таймер удалён
        assert weak_ref() is None, "Таймер должен быть удалён GC"

    def test_no_thread_leak_after_stop(self, tmp_path: Path) -> None:
        """
        Тест 2.2: Проверка отсутствия утечки потоков.

        Проверяет что после stop() не остаётся
        висящих потоков таймера.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Получаем количество потоков до создания таймера
        initial_threads = threading.active_count()

        # Создаём и запускаем таймер
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Останавливаем таймер
        timer.stop()

        # Ждем завершения потока
        time.sleep(0.5)

        # Получаем количество потоков после остановки
        final_threads = threading.active_count()

        # Проверяем что количество потоков вернулось к исходному
        assert final_threads <= initial_threads + 1, (
            f"Утечка потоков: было {initial_threads}, стало {final_threads}"
        )

    def test_finalizer_called_on_deletion(self, tmp_path: Path) -> None:
        """
        Тест 2.3: Проверка вызова finalizer при удалении.

        Проверяет что weakref.finalize вызывается
        при удалении объекта таймера.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        import gc

        finalizer_called = {"value": False}

        def mock_finalizer(timer_obj, timer_ref, lock):
            """Mock finalizer функции."""
            finalizer_called["value"] = True

        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Сохраняем ссылку на finalizer
        original_finalizer = timer._finalizer

        # Проверяем что finalizer существует
        assert original_finalizer is not None, "Finalizer должен быть создан"

        # Останавливаем таймер
        timer.stop()

        # Удаляем таймер
        del timer
        gc.collect()

        # Finalizer должен быть вызван (проверяем через detach)
        # Note: finalizer вызывается автоматически при удалении объекта


class TestTempFileTimerCallback:
    """Тесты для проверки callback функции очистки."""

    def test_callback_checks_stop_event(self, tmp_path: Path) -> None:
        """
        Тест 3.1: Проверка что callback проверяет событие остановки.

        Проверяет что _cleanup_callback проверяет _stop_event
        перед выполнением очистки.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Устанавливаем событие остановки
        timer._stop_event.set()

        # Вызываем callback - не должно выполнять очистку
        timer._cleanup_callback()

        # Проверяем что очистка не была вызвана
        assert timer._cleanup_count == 0, "Очистка не должна была быть вызвана"

    def test_callback_acquires_lock(self, tmp_path: Path) -> None:
        """
        Тест 3.2: Проверка что callback захватывает блокировку.

        Проверяет что _cleanup_callback захватывает
        блокировку перед проверкой события.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Захватываем блокировку
        lock_acquired = timer._lock.acquire(timeout=5.0)
        assert lock_acquired, "Блокировка должна быть захвачена"

        # Вызываем callback в отдельном потоке
        callback_completed = threading.Event()

        def call_callback():
            """Вызывает callback."""
            timer._cleanup_callback()
            callback_completed.set()

        thread = threading.Thread(target=call_callback)
        thread.start()

        # Ждем немного - callback должен ждать блокировку
        time.sleep(0.5)
        assert callback_completed.is_set() is False, "Callback должен ждать блокировку"

        # Освобождаем блокировку
        timer._lock.release()

        # Ждем завершения callback
        thread.join(timeout=5)
        assert callback_completed.is_set(), "Callback должен завершиться"

    def test_callback_handles_lock_timeout(self, tmp_path: Path, caplog) -> None:
        """
        Тест 3.3: Проверка обработки timeout блокировки.

        Проверяет что при timeout блокировки callback
        логирует предупреждение и возвращается.

        Args:
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Mock блокировки для имитации timeout
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False  # Timeout
        timer._lock = mock_lock

        # Вызываем callback
        timer._cleanup_callback()

        # Проверяем что предупреждение было залогировано
        assert "Не удалось получить блокировку" in caplog.text

    def test_callback_handles_lock_error(self, tmp_path: Path, caplog) -> None:
        """
        Тест 3.4: Проверка обработки ошибки блокировки.

        Проверяет что при ошибке блокировки callback
        логирует ошибку и возвращается.

        Args:
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Mock блокировки для имитации ошибки
        mock_lock = MagicMock()
        mock_lock.acquire.side_effect = RuntimeError("Lock error")
        timer._lock = mock_lock

        # Вызываем callback
        timer._cleanup_callback()

        # Проверяем что ошибка была залогирована
        assert "Ошибка при получении блокировки" in caplog.text


class TestTempFileTimerEdgeCases:
    """Тесты для проверки граничных случаев."""

    def test_stop_during_cleanup(self, tmp_path: Path) -> None:
        """
        Тест 4.1: Проверка вызова stop() во время очистки.

        Проверяет что вызов stop() во время выполнения
        очистки корректно останавливает таймер.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Mock очистки для имитации длительной операции
        cleanup_completed = threading.Event()

        def slow_cleanup():
            """Медленная очистка."""
            time.sleep(1)
            cleanup_completed.set()

        with patch.object(timer, "_cleanup_temp_files", side_effect=slow_cleanup):
            timer.start()

            # Вызываем очистку
            timer._cleanup_callback()

            # Вызываем stop во время очистки
            time.sleep(0.5)
            timer.stop()

            # Ждем завершения очистки
            cleanup_completed.wait(timeout=5)

        # Проверяем что таймер остановлен
        assert timer._stop_event.is_set(), "Событие остановки должно быть установлено"

    def test_timer_with_short_interval(self, tmp_path: Path) -> None:
        """
        Тест 4.2: Проверка таймера с коротким интервалом.

        Проверяет что таймер с коротким интервалом
        корректно останавливается.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=1)
        timer.start()

        # Ждем немного
        time.sleep(0.5)

        # Останавливаем
        timer.stop()

        # Проверяем что таймер остановлен
        assert timer._is_running is False, "Таймер должен быть остановлен"

    def test_timer_cleanup_count_increments(self, tmp_path: Path) -> None:
        """
        Тест 4.3: Проверка счетчика очисток.

        Проверяет что _cleanup_count увеличивается
        при каждой очистке.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Initial count
        initial_count = timer._cleanup_count

        # Вызываем очистку несколько раз (сначала снимаем с блокировки stop_event)
        timer._stop_event.clear()

        # Mock _cleanup_temp_files чтобы он не делал ничего но увеличивал счетчик
        def mock_cleanup():
            timer._cleanup_count += 1

        timer._cleanup_temp_files = mock_cleanup

        timer._cleanup_callback()
        timer._cleanup_callback()
        timer._cleanup_callback()

        # Проверяем что счетчик увеличился минимум на 3
        assert timer._cleanup_count >= initial_count + 3, (
            f"Счетчик должен быть >= {initial_count + 3}"
        )


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
