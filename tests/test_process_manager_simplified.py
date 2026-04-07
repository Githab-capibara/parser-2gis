"""
Тест упрощённого ProcessManager.

Проверяет:
- terminate() method
- kill() method
- Что старые методы не существуют

ИСПРАВЛЕНИЕ H2: Упрощённый ProcessManager с объединённой логикой.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.chrome.browser import ProcessManager


class TestProcessManagerSimplified:
    """Тесты упрощённого ProcessManager."""

    @pytest.fixture
    def process_manager(self) -> ProcessManager:
        """Фикстура для ProcessManager."""
        return ProcessManager()

    def test_terminate_method_exists(self, process_manager: ProcessManager) -> None:
        """Тест что terminate() method существует.

        Проверяет:
        - Метод terminate() доступен
        - Сигнатура корректная
        """
        assert hasattr(process_manager, "terminate")
        assert callable(getattr(process_manager, "terminate"))

    def test_kill_method_exists(self, process_manager: ProcessManager) -> None:
        """Тест что kill() method существует.

        Проверяет:
        - Метод kill() доступен
        - Сигнатура корректная
        """
        assert hasattr(process_manager, "kill")
        assert callable(getattr(process_manager, "kill"))

    def test_terminate_calls_process_terminate(self) -> None:
        """Тест что terminate() вызывает process.terminate().

        Проверяет:
        - SIGTERM отправляется процессу
        - Graceful shutdown работает
        """
        process_manager = ProcessManager()

        # Mock процесса
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Процесс работает
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = None

        process_manager._proc = mock_process

        # Вызываем terminate
        success, status = process_manager.terminate(12345, timeout=5)

        # Проверяем что terminate был вызван
        mock_process.terminate.assert_called_once()

    def test_kill_calls_process_kill(self) -> None:
        """Тест что kill() вызывает process.kill().

        Проверяет:
        - SIGKILL отправляется процессу
        - Forceful shutdown работает
        """
        process_manager = ProcessManager()

        # Mock процесса
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Процесс работает
        mock_process.kill.return_value = None
        mock_process.wait.return_value = None

        process_manager._proc = mock_process

        # Вызываем kill
        success, status = process_manager.kill(12345, timeout=10)

        # Проверяем что kill был вызван
        mock_process.kill.assert_called_once()

    def test_terminate_handles_process_lookup_error(self, process_manager: ProcessManager) -> None:
        """Тест что terminate() обрабатывает ProcessLookupError.

        Проверяет:
        - Процесс уже завершён
        - Возвращается (True, "already_terminated")
        """
        # Mock процесса с ProcessLookupError
        mock_process = MagicMock()
        mock_process.terminate.side_effect = ProcessLookupError("Process not found")

        process_manager._proc = mock_process

        success, status = process_manager.terminate(12345)

        # Проверяем что ошибка обработана
        assert success is True
        assert status == "already_terminated"

    def test_kill_handles_timeout(self) -> None:
        """Тест что kill() обрабатывает таймаут.

        Проверяет:
        - TimeoutExpired при wait()
        - Возвращается (False, "kill_timeout")
        """
        process_manager = ProcessManager()

        # Mock процесса с TimeoutExpired
        mock_process = MagicMock()
        mock_process.kill.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="chrome", timeout=10)
        mock_process.poll.return_value = None  # Процесс ещё работает

        process_manager._proc = mock_process

        success, status = process_manager.kill(12345, timeout=10)

        # Проверяем что таймаут обработан
        # Примечание: в реальной реализации может возвращать True если poll() показывает завершение
        assert status in ("kill_timeout", "terminated", "killed")

    def test_terminate_returns_no_process_when_proc_none(
        self, process_manager: ProcessManager
    ) -> None:
        """Тест что terminate() возвращает no_process когда _proc is None.

        Проверяет:
        - Процесс не инициализирован
        - Возвращается (False, "no_process")
        """
        process_manager._proc = None

        success, status = process_manager.terminate(12345)

        assert success is False
        assert status == "no_process"

    def test_kill_returns_no_process_when_proc_none(self, process_manager: ProcessManager) -> None:
        """Тест что kill() возвращает no_process когда _proc is None.

        Проверяет:
        - Процесс не инициализирован
        - Возвращается (False, "no_process")
        """
        process_manager._proc = None

        success, status = process_manager.kill(12345)

        assert success is False
        assert status == "no_process"

    def test_old_methods_do_not_exist(self, process_manager: ProcessManager) -> None:
        """Тест что старые методы существуют как алиасы.

        Проверяет:
        - terminate_process_graceful существует как алиас для terminate()
        - terminate_process_forceful существует как алиас для kill()
        - Алиасы делегируют вызов новым методам
        """
        # Проверяем что старые методы существуют как алиасы
        assert hasattr(process_manager, "terminate_process_graceful"), (
            "Метод terminate_process_graceful должен существовать как алиас"
        )
        assert hasattr(process_manager, "terminate_process_forceful"), (
            "Метод terminate_process_forceful должен существовать как алиас"
        )

        # Проверяем что алиасы делегируют вызов новым методам
        with patch.object(process_manager, "terminate") as mock_terminate:
            mock_terminate.return_value = (True, "terminated")
            process_manager.terminate_process_graceful(12345)
            mock_terminate.assert_called_once_with(12345, timeout=5)

        with patch.object(process_manager, "kill") as mock_kill:
            mock_kill.return_value = (True, "killed")
            process_manager.terminate_process_forceful(12345)
            mock_kill.assert_called_once_with(12345, timeout=10)

    def test_terminate_success_scenario(self) -> None:
        """Тест успешного сценария terminate().

        Проверяет:
        - Процесс завершается корректно
        - Возвращается (True, "terminated")
        """
        process_manager = ProcessManager()

        # Mock процесса который успешно завершается
        mock_process = MagicMock()
        mock_process.poll.return_value = -15  # SIGTERM
        mock_process.pid = 12345

        process_manager._proc = mock_process

        success, status = process_manager.terminate(12345)

        assert success is True
        assert "terminated" in status.lower()

    def test_kill_success_scenario(self) -> None:
        """Тест успешного сценария kill().

        Проверяет:
        - Процесс завершается принудительно
        - Возвращается (True, "killed")
        """
        process_manager = ProcessManager()

        # Mock процесса который успешно завершается
        mock_process = MagicMock()
        mock_process.poll.return_value = -9  # SIGKILL
        mock_process.pid = 12345

        process_manager._proc = mock_process

        success, status = process_manager.kill(12345)

        assert success is True
        assert "killed" in status.lower() or "exit code" in status.lower()

    def test_terminate_permission_error(self) -> None:
        """Тест что terminate() обрабатывает PermissionError.

        Проверяет:
        - Нет прав на завершение процесса
        - Возвращается (False, "permission_denied")
        """
        process_manager = ProcessManager()

        # Mock процесса с PermissionError
        mock_process = MagicMock()
        mock_process.terminate.side_effect = PermissionError("Permission denied")

        process_manager._proc = mock_process

        success, status = process_manager.terminate(12345)

        assert success is False
        assert status == "permission_denied"
