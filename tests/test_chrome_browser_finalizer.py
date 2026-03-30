"""Тесты для проверки weakref.finalize() в chrome/browser.py."""

import subprocess
from unittest.mock import MagicMock, patch


from parser_2gis.chrome.browser import BrowserLifecycleManager, ProcessManager


class TestChromeBrowserFinalizer:
    """Тесты для weakref.finalize() в ChromeBrowser."""

    def test_finalizer_is_registered(self):
        """Finalizer должен быть зарегистрирован после инициализации."""
        options = MagicMock()
        options.binary_path = None

        with patch.object(BrowserLifecycleManager, "_build_chrome_cmd", return_value=["/bin/true"]):
            with patch.object(ProcessManager, "launch_process") as mock_launch:
                mock_proc = MagicMock()
                mock_proc.pid = 12345
                mock_proc.poll.return_value = None
                mock_launch.return_value = mock_proc

                with patch("parser_2gis.chrome.browser.free_port", return_value=9222):
                    manager = BrowserLifecycleManager(options)

                    assert hasattr(manager, "_finalizer")
                    assert manager._finalizer is not None

    def test_cleanup_from_finalizer_static_method(self):
        """_cleanup_from_finalizer должен работать как статический метод."""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            mock_tempdir = MagicMock()

            BrowserLifecycleManager._cleanup_from_finalizer(mock_proc, mock_tempdir, "/tmp/path")

            mock_proc.terminate.assert_called_once()
            mock_tempdir.cleanup.assert_called_once()

    def test_finalizer_detach_on_del(self):
        """__del__ должен использовать finalizer.detach() если доступно."""
        options = MagicMock()
        options.binary_path = None

        with patch.object(BrowserLifecycleManager, "_build_chrome_cmd", return_value=["/bin/true"]):
            with patch.object(ProcessManager, "launch_process") as mock_launch:
                mock_proc = MagicMock()
                mock_proc.pid = 12345
                mock_proc.poll.return_value = None
                mock_launch.return_value = mock_proc

                with patch("parser_2gis.chrome.browser.free_port", return_value=9222):
                    manager = BrowserLifecycleManager(options)

                    mock_finalizer = MagicMock()
                    mock_finalizer.detach.return_value = True
                    manager._finalizer = mock_finalizer

                    with patch.object(manager, "_cleanup_from_finalizer"):
                        manager.__del__()

                    mock_finalizer.detach.assert_called_once()

    def test_cleanup_handles_none_proc(self):
        """Очистка должна обрабатывать None процесс."""
        BrowserLifecycleManager._cleanup_from_finalizer(None, None, None)

    def test_cleanup_handles_already_terminated_proc(self):
        """Очистка должна обрабатывать уже завершённый процесс."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0

        mock_tempdir = MagicMock()

        BrowserLifecycleManager._cleanup_from_finalizer(mock_proc, mock_tempdir, "/tmp/path")

        mock_proc.terminate.assert_not_called()
        mock_tempdir.cleanup.assert_called_once()

    def test_cleanup_kills_hung_process(self):
        """Очистка должна убивать зависший процесс."""

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.side_effect = [None, None, 0]
            mock_proc.wait.side_effect = [subprocess.TimeoutExpired("cmd", 3), None]
            mock_popen.return_value = mock_proc

            mock_tempdir = MagicMock()

            BrowserLifecycleManager._cleanup_from_finalizer(mock_proc, mock_tempdir, "/tmp/path")

            mock_proc.terminate.assert_called_once()
            mock_proc.kill.assert_called_once()
            mock_tempdir.cleanup.assert_called_once()

    def test_atexit_false_set(self):
        """Finalizer должен иметь atexit=False."""
        options = MagicMock()
        options.binary_path = None

        with patch.object(BrowserLifecycleManager, "_build_chrome_cmd", return_value=["/bin/true"]):
            with patch.object(ProcessManager, "launch_process") as mock_launch:
                mock_proc = MagicMock()
                mock_proc.pid = 12345
                mock_proc.poll.return_value = None
                mock_launch.return_value = mock_proc

                with patch("parser_2gis.chrome.browser.free_port", return_value=9222):
                    manager = BrowserLifecycleManager(options)

                    assert manager._finalizer.atexit is False
