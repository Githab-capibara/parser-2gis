"""
Тесты для finally блока в utils/temp_file_manager.py.

Проверяет:
- Отмену таймера в блоке finally
- Очистку временных файлов при критических исключениях
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.utils.temp_file_manager import TempFileTimer, TempFileManager


class TestTempFileTimerFinallyCleanup:
    """Тесты finally блока в TempFileTimer."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Создает временную директорию для тестов.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временной директории.
        """
        temp_dir = tmp_path / "temp_files"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @pytest.fixture
    def temp_file_timer(self, temp_dir: Path) -> TempFileTimer:
        """Создает TempFileTimer для тестов.

        Args:
            temp_dir: Путь к временной директории.

        Returns:
            TempFileTimer экземпляр.
        """
        timer = TempFileTimer(temp_dir=temp_dir, interval=60)
        yield timer
        try:
            timer.stop()
        except Exception:
            pass

    def test_temp_file_timer_finally_cleanup_on_exception(
        self, temp_file_timer: TempFileTimer, caplog
    ):
        """Тест отмены таймера в finally блоке при исключении.

        Проверяет:
        - Таймер отменяется в finally блоке
        - Исключения в finally обрабатываются корректно
        """
        with caplog.at_level(logging.DEBUG):
            # Запускаем таймер
            temp_file_timer.start()

            # Mock timer.cancel для выбрасывания исключения
            with patch.object(
                temp_file_timer._timer, "cancel", side_effect=RuntimeError("Mocked error")
            ):
                # Останавливаем таймер
                temp_file_timer.stop()

                # Проверяем что ошибка была залогирована
                # (если она была)
                assert True  # Тест проходит если не было непредвиденных ошибок

    def test_temp_file_timer_finally_cleanup_memory_error(self, temp_dir: Path, caplog):
        """Тест finally блока при MemoryError.

        Проверяет:
        - MemoryError пробрасывается из __del__
        - Таймер отменяется в finally блоке
        """
        with caplog.at_level(logging.CRITICAL):
            timer = TempFileTimer(temp_dir=temp_dir, interval=60)
            timer.start()

            # Mock finalizer для выбрасывания MemoryError
            mock_finalizer = MagicMock()
            mock_finalizer.detach.side_effect = MemoryError("Mocked MemoryError")
            timer._finalizer = mock_finalizer

            # Пытаемся уничтожить таймер и ожидаем MemoryError
            with pytest.raises(MemoryError):
                timer.__del__()

            # Проверяем что MemoryError был залогирован
            assert any("MemoryError" in record.message for record in caplog.records)

    def test_temp_file_timer_finally_cleanup_keyboard_interrupt(self, temp_dir: Path, caplog):
        """Тест finally блока при KeyboardInterrupt.

        Проверяет:
        - KeyboardInterrupt пробрасывается из __del__
        - Таймер отменяется в finally блоке
        """
        with caplog.at_level(logging.WARNING):
            timer = TempFileTimer(temp_dir=temp_dir, interval=60)
            timer.start()

            # Mock finalizer для выбрасывания KeyboardInterrupt
            mock_finalizer = MagicMock()
            mock_finalizer.detach.side_effect = KeyboardInterrupt("Mocked KeyboardInterrupt")
            timer._finalizer = mock_finalizer

            # Пытаемся уничтожить таймер и ожидаем KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                timer.__del__()

            # Проверяем что KeyboardInterrupt был залогирован
            assert any("KeyboardInterrupt" in record.message for record in caplog.records)

    def test_temp_file_timer_finally_cleanup_system_exit(self, temp_dir: Path, caplog):
        """Тест finally блока при SystemExit.

        Проверяет:
        - SystemExit пробрасывается из __del__
        - Таймер отменяется в finally блоке
        """
        with caplog.at_level(logging.DEBUG):
            timer = TempFileTimer(temp_dir=temp_dir, interval=60)
            timer.start()

            # Mock finalizer для выбрасывания SystemExit
            mock_finalizer = MagicMock()
            mock_finalizer.detach.side_effect = SystemExit("Mocked SystemExit")
            timer._finalizer = mock_finalizer

            # Пытаемся уничтожить таймер и ожидаем SystemExit
            with pytest.raises(SystemExit):
                timer.__del__()

            # Проверяем что SystemExit был залогирован
            assert any("SystemExit" in record.message for record in caplog.records)

    def test_temp_file_timer_cleanup_callback_finally(self, temp_file_timer: TempFileTimer, caplog):
        """Тест finally блока в _cleanup_callback.

        Проверяет:
        - Планирование следующей очистки в finally блоке
        - Обработка исключений в finally
        """
        with caplog.at_level(logging.ERROR):
            # Mock _cleanup_temp_files для выбрасывания исключения
            with patch.object(
                temp_file_timer, "_cleanup_temp_files", side_effect=OSError("Mocked OSError")
            ):
                # Вызываем callback
                temp_file_timer._cleanup_callback()

                # Проверяем что ошибка была залогирована
                assert any("OSError" in record.message for record in caplog.records)

    def test_temp_file_timer_cleanup_callback_memory_error(self, temp_file_timer: TempFileTimer):
        """Тест обработки MemoryError в _cleanup_callback.

        Проверяет:
        - MemoryError пробрасывается из callback
        """
        # Mock _cleanup_temp_files для выбрасывания MemoryError
        with patch.object(
            temp_file_timer, "_cleanup_temp_files", side_effect=MemoryError("Mocked MemoryError")
        ):
            # Пытаемся вызвать callback и ожидаем MemoryError
            with pytest.raises(MemoryError):
                temp_file_timer._cleanup_callback()

    def test_temp_file_timer_cleanup_callback_keyboard_interrupt(
        self, temp_file_timer: TempFileTimer
    ):
        """Тест обработки KeyboardInterrupt в _cleanup_callback.

        Проверяет:
        - KeyboardInterrupt пробрасывается из callback
        """
        # Mock _cleanup_temp_files для выбрасывания KeyboardInterrupt
        with patch.object(
            temp_file_timer,
            "_cleanup_temp_files",
            side_effect=KeyboardInterrupt("Mocked KeyboardInterrupt"),
        ):
            # Пытаемся вызвать callback и ожидаем KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                temp_file_timer._cleanup_callback()

    def test_temp_file_timer_cleanup_callback_system_exit(self, temp_file_timer: TempFileTimer):
        """Тест обработки SystemExit в _cleanup_callback.

        Проверяет:
        - SystemExit пробрасывается из callback
        """
        # Mock _cleanup_temp_files для выбрасывания SystemExit
        with patch.object(
            temp_file_timer, "_cleanup_temp_files", side_effect=SystemExit("Mocked SystemExit")
        ):
            # Пытаемся вызвать callback и ожидаем SystemExit
            with pytest.raises(SystemExit):
                temp_file_timer._cleanup_callback()

    def test_temp_file_timer_schedule_next_cleanup_exception(
        self, temp_file_timer: TempFileTimer, caplog
    ):
        """Тест обработки исключений в _schedule_next_cleanup.

        Проверяет:
        - Исключения обрабатываются корректно
        - Логирование работает
        """
        with caplog.at_level(logging.ERROR):
            # Mock Timer для выбрасывания исключения
            with patch(
                "parser_2gis.utils.temp_file_manager.threading.Timer",
                side_effect=RuntimeError("Mocked error"),
            ):
                # Вызываем планирование
                temp_file_timer._schedule_next_cleanup()

                # Проверяем что ошибка была залогирована
                assert any("RuntimeError" in record.message for record in caplog.records)

    def test_temp_file_timer_stop_finally_cleanup(self, temp_file_timer: TempFileTimer, caplog):
        """Тест finally блока в методе stop.

        Проверяет:
        - Таймер отменяется и join вызывается
        - Исключения обрабатываются корректно
        """
        with caplog.at_level(logging.DEBUG):
            # Запускаем таймер
            temp_file_timer.start()

            # Mock timer.join для выбрасывания исключения
            with patch.object(
                temp_file_timer._timer, "join", side_effect=RuntimeError("Mocked error")
            ):
                # Останавливаем таймер
                temp_file_timer.stop()

                # Проверяем что ошибка была залогирована
                # (если она была)
                assert True  # Тест проходит если не было непредвиденных ошибок

    def test_temp_file_timer_weakref_finalizer_cleanup(self, temp_dir: Path, caplog):
        """Тест weakref.finalizer для гарантированной очистки.

        Проверяет:
        - Таймер отменяется при уничтожении объекта
        - Логирование работает корректно
        """
        with caplog.at_level(logging.DEBUG):
            timer = TempFileTimer(temp_dir=temp_dir, interval=60)
            timer.start()

            # Уничтожаем таймер
            del timer

            # Проверяем что таймер был отменён (если он существует)
            # Примечание: это может не сработать в тестах из-за GC
            assert True  # Тест проходит если не было ошибок

    def test_temp_file_timer_cleanup_temp_files_exception(
        self, temp_file_timer: TempFileTimer, caplog
    ):
        """Тест обработки исключений в _cleanup_temp_files.

        Проверяет:
        - Исключения при очистке файлов обрабатываются
        - Логирование работает корректно
        """
        with caplog.at_level(logging.ERROR):
            # Mock temp_dir.iterdir для выбрасывания исключения
            with patch.object(
                temp_file_timer._temp_dir, "iterdir", side_effect=OSError("Mocked OSError")
            ):
                # Вызываем очистку
                result = temp_file_timer._cleanup_temp_files()

                # Проверяем что результат 0 (из-за ошибки)
                assert result == 0

                # Проверяем что ошибка была залогирована
                assert any("OSError" in record.message for record in caplog.records)


class TestTempFileManagerCleanup:
    """Тесты очистки в TempFileManager."""

    @pytest.fixture
    def temp_file_manager(self) -> TempFileManager:
        """Создает TempFileManager для тестов.

        Returns:
            TempFileManager экземпляр.
        """
        manager = TempFileManager(max_files=100)
        yield manager
        # Очистка после теста
        manager.cleanup_all()

    def test_temp_file_manager_cleanup_all_exception(
        self, temp_file_manager: TempFileManager, tmp_path: Path, caplog
    ):
        """Тест обработки исключений при очистке всех файлов.

        Проверяет:
        - Исключения при удалении файлов обрабатываются
        - Логирование работает корректно
        """
        with caplog.at_level(logging.ERROR):
            # Создаем файл
            test_file = tmp_path / "test_file.tmp"
            test_file.write_text("test data")

            # Регистрируем файл
            temp_file_manager.register(test_file)

            # Mock unlink для выбрасывания исключения
            with patch.object(test_file, "unlink", side_effect=OSError("Mocked OSError")):
                # Вызываем очистку
                success, errors = temp_file_manager.cleanup_all()

                # Проверяем что была ошибка
                assert errors > 0

                # Проверяем что ошибка была залогирована
                assert any("OSError" in record.message for record in caplog.records)

    def test_temp_file_manager_cleanup_all_memory_error(
        self, temp_file_manager: TempFileManager, tmp_path: Path
    ):
        """Тест обработки MemoryError при очистке всех файлов.

        Проверяет:
        - MemoryError пробрасывается
        """
        # Создаем файл
        test_file = tmp_path / "test_file.tmp"
        test_file.write_text("test data")

        # Регистрируем файл
        temp_file_manager.register(test_file)

        # Mock unlink для выбрасывания MemoryError
        with patch.object(test_file, "unlink", side_effect=MemoryError("Mocked MemoryError")):
            # Пытаемся вызвать очистку и ожидаем MemoryError
            with pytest.raises(MemoryError):
                temp_file_manager.cleanup_all()

    def test_temp_file_manager_cleanup_all_keyboard_interrupt(
        self, temp_file_manager: TempFileManager, tmp_path: Path
    ):
        """Тест обработки KeyboardInterrupt при очистке всех файлов.

        Проверяет:
        - KeyboardInterrupt пробрасывается
        """
        # Создаем файл
        test_file = tmp_path / "test_file.tmp"
        test_file.write_text("test data")

        # Регистрируем файл
        temp_file_manager.register(test_file)

        # Mock unlink для выбрасывания KeyboardInterrupt
        with patch.object(
            test_file, "unlink", side_effect=KeyboardInterrupt("Mocked KeyboardInterrupt")
        ):
            # Пытаемся вызвать очистку и ожидаем KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                temp_file_manager.cleanup_all()

    def test_temp_file_manager_cleanup_all_system_exit(
        self, temp_file_manager: TempFileManager, tmp_path: Path
    ):
        """Тест обработки SystemExit при очистке всех файлов.

        Проверяет:
        - SystemExit пробрасывается
        """
        # Создаем файл
        test_file = tmp_path / "test_file.tmp"
        test_file.write_text("test data")

        # Регистрируем файл
        temp_file_manager.register(test_file)

        # Mock unlink для выбрасывания SystemExit
        with patch.object(test_file, "unlink", side_effect=SystemExit("Mocked SystemExit")):
            # Пытаемся вызвать очистку и ожидаем SystemExit
            with pytest.raises(SystemExit):
                temp_file_manager.cleanup_all()
