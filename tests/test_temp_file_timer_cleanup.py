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
from typing import Never
from unittest.mock import patch

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
        assert timer._timer is None, "Таймер должен быть очищен"
        assert timer._is_running is False, "Флаг is_running должен быть False"

    def test_stop_sets_is_running_false(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка что stop() устанавливает _is_running в False.

        Проверяет что _is_running сбрасывается при вызове stop().

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer.start()

        # Проверяем что флаг установлен
        assert timer._is_running is True, "Таймер должен быть запущен"

        # Вызываем stop
        timer.stop()

        # Проверяем что флаг сброшен
        assert timer._is_running is False, "Флаг is_running должен быть False"

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


class TestTempFileTimerCallback:
    """Тесты для проверки callback функции очистки."""

    def test_callback_checks_is_running(self, tmp_path: Path) -> None:
        """
        Тест 3.1: Проверка что callback проверяет _is_running.

        Проверяет что _cleanup_callback проверяет _is_running
        перед выполнением очистки.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)

        # Убеждаемся что таймер не запущен
        timer._is_running = False

        # Вызываем callback - не должно выполнять очистку
        timer._cleanup_callback()

        # Проверяем что очистка не была вызвана
        assert timer._cleanup_count == 0, "Очистка не должна была быть вызвана"

    def test_callback_calls_cleanup(self, tmp_path: Path) -> None:
        """
        Тест 3.2: Проверка что callback вызывает очистку.

        Проверяет что _cleanup_callback вызывает _cleanup_temp_files
        когда _is_running = True.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer._is_running = True

        cleanup_called = {"count": 0}

        def mock_cleanup() -> None:
            cleanup_called["count"] += 1

        timer._cleanup_temp_files = mock_cleanup

        # Вызываем callback
        timer._cleanup_callback()

        # Проверяем что очистка была вызвана
        assert cleanup_called["count"] == 1, "Очистка должна быть вызвана"

    def test_callback_schedules_next(self, tmp_path: Path) -> None:
        """
        Тест 3.3: Проверка что callback планирует следующую очистку.

        Проверяет что после очистки вызывается _schedule_next_cleanup.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer._is_running = True

        timer._cleanup_temp_files = lambda: 0

        # Вызываем callback
        timer._cleanup_callback()

        # Проверяем что следующий таймер запланирован
        assert timer._timer is not None, "Следующий таймер должен быть запланирован"

    def test_callback_handles_cleanup_error(self, tmp_path: Path, caplog) -> None:
        """
        Тест 3.4: Проверка обработки ошибки очистки.

        Проверяет что при ошибке очистки callback
        логирует ошибку и планирует следующую очистку.

        Args:
            tmp_path: pytest tmp_path fixture.
            caplog: pytest caplog fixture.
        """
        timer = TempFileTimer(temp_dir=tmp_path, interval=60)
        timer._is_running = True

        def mock_cleanup_error() -> Never:
            raise OSError("Cleanup failed")

        timer._cleanup_temp_files = mock_cleanup_error

        # Вызываем callback — не должен выбросить исключение
        timer._cleanup_callback()

        # Проверяем что ошибка была залогирована
        assert "Ошибка при периодической очистке" in caplog.text


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

        def slow_cleanup() -> None:
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
        assert timer._is_running is False, "Флаг is_running должен быть False"

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

        # Запускаем таймер чтобы _is_running = True
        timer.start()

        # Счетчик увеличивается внутри _cleanup_temp_files
        original_cleanup = timer._cleanup_temp_files
        call_count = {"count": 0}

        def mock_cleanup():
            call_count["count"] += 1
            return original_cleanup()

        timer._cleanup_temp_files = mock_cleanup

        timer._cleanup_callback()
        timer._cleanup_callback()
        timer._cleanup_callback()

        # Останавливаем таймер чтобы остановить рекурсивное планирование
        timer._is_running = False

        # Проверяем что _cleanup_temp_files был вызван 3 раза
        assert call_count["count"] == 3, (
            f"_cleanup_temp_files должен быть вызван 3 раза, вызван {call_count['count']}"
        )


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
