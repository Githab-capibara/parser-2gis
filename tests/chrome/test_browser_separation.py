"""
Тесты для разделения классов в chrome/browser.py.

Проверяет:
- BrowserPathResolver - проверка поиска пути к браузеру
- ProfileManager - проверка управления профилем
- ProcessManager - проверка управления процессом
- BrowserLifecycleManager - проверка координации классов
"""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.chrome.browser import (
    BrowserLifecycleManager,
    BrowserPathResolver,
    ProcessManager,
    ProfileManager,
)
from parser_2gis.chrome.exceptions import ChromePathNotFound


class TestBrowserPathResolver:
    """Тесты для BrowserPathResolver."""

    @pytest.fixture
    def path_resolver(self) -> BrowserPathResolver:
        """Создает BrowserPathResolver для тестов.

        Returns:
            BrowserPathResolver экземпляр.
        """
        return BrowserPathResolver()

    @pytest.fixture
    def mock_chrome_options(self) -> MagicMock:
        """Создает mock опций Chrome.

        Returns:
            MagicMock с опциями Chrome.
        """
        options = MagicMock()
        options.binary_path = None
        return options

    def test_browser_path_resolver_with_explicit_path(self, path_resolver: BrowserPathResolver):
        """Тест разрешения пути с явным указанием пути к браузеру.

        Проверяет:
        - Корректное разрешение пути при явном указании
        - Валидация пути работает
        """
        mock_options = MagicMock()
        mock_options.binary_path = "/usr/bin/google-chrome"

        with patch("os.path.isabs", return_value=True):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.isfile", return_value=True):
                    with patch("os.access", return_value=True):
                        with patch("os.path.islink", return_value=False):
                            with patch("os.path.realpath", return_value="/usr/bin/google-chrome"):
                                result = path_resolver.resolve_path(mock_options)

                                assert result == "/usr/bin/google-chrome"

    def test_browser_path_resolver_auto_detect(self, path_resolver: BrowserPathResolver):
        """Тест автоматического обнаружения пути к браузеру.

        Проверяет:
        - locate_chrome_path вызывается при отсутствии binary_path
        - Путь корректно разрешается
        """
        mock_options = MagicMock()
        mock_options.binary_path = None

        with patch(
            "parser_2gis.chrome.browser.locate_chrome_path", return_value="/usr/bin/google-chrome"
        ):
            with patch("os.path.isabs", return_value=True):
                with patch("os.path.exists", return_value=True):
                    with patch("os.path.isfile", return_value=True):
                        with patch("os.access", return_value=True):
                            with patch("os.path.islink", return_value=False):
                                with patch(
                                    "os.path.realpath", return_value="/usr/bin/google-chrome"
                                ):
                                    result = path_resolver.resolve_path(mock_options)

                                    assert result == "/usr/bin/google-chrome"

    def test_browser_path_resolver_not_found(self, path_resolver: BrowserPathResolver):
        """Тест отсутствия пути к браузеру.

        Проверяет:
        - ChromePathNotFound выбрасывается при отсутствии пути
        """
        mock_options = MagicMock()
        mock_options.binary_path = None

        with patch("parser_2gis.chrome.browser.locate_chrome_path", return_value=None):
            with pytest.raises(ChromePathNotFound):
                path_resolver.resolve_path(mock_options)

    def test_browser_path_resolver_symlink_resolution(
        self, path_resolver: BrowserPathResolver, caplog
    ):
        """Тест разрешения символических ссылок.

        Проверяет:
        - Символические ссылки разрешаются через realpath
        - Логирование работает корректно
        """
        import logging

        mock_options = MagicMock()
        mock_options.binary_path = "/usr/bin/chrome"

        with caplog.at_level(logging.WARNING):
            with patch("os.path.islink", return_value=True):
                with patch("os.path.realpath", return_value="/usr/bin/google-chrome"):
                    with patch("os.path.isabs", return_value=True):
                        with patch("os.path.exists", return_value=True):
                            with patch("os.path.isfile", return_value=True):
                                with patch("os.access", return_value=True):
                                    result = path_resolver.resolve_path(mock_options)

                                    assert result == "/usr/bin/google-chrome"
                                    assert any(
                                        "символическую ссылку" in record.message
                                        for record in caplog.records
                                    )

    def test_browser_path_resolver_relative_path_error(self, path_resolver: BrowserPathResolver):
        """Тест относительного пути.

        Проверяет:
        - ValueError выбрасывается для относительных путей
        """
        mock_options = MagicMock()
        mock_options.binary_path = "chrome"

        with patch("os.path.isabs", return_value=False):
            with pytest.raises(ValueError, match="абсолютным"):
                path_resolver.resolve_path(mock_options)

    def test_browser_path_resolver_not_exists_error(self, path_resolver: BrowserPathResolver):
        """Тест несуществующего пути.

        Проверяет:
        - FileNotFoundError выбрасывается для несуществующих путей
        """
        mock_options = MagicMock()
        mock_options.binary_path = "/nonexistent/chrome"

        with patch("os.path.isabs", return_value=True):
            with patch("os.path.exists", return_value=False):
                with pytest.raises(FileNotFoundError):
                    path_resolver.resolve_path(mock_options)

    def test_browser_path_resolver_not_file_error(self, path_resolver: BrowserPathResolver):
        """Тест пути к директории.

        Проверяет:
        - ValueError выбрасывается для путей к директориям
        """
        mock_options = MagicMock()
        mock_options.binary_path = "/usr/bin"

        with patch("os.path.isabs", return_value=True):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.isfile", return_value=False):
                    with pytest.raises(ValueError, match="файл"):
                        path_resolver.resolve_path(mock_options)

    def test_browser_path_resolver_not_executable_error(self, path_resolver: BrowserPathResolver):
        """Тест неисполняемого файла.

        Проверяет:
        - PermissionError выбрасывается для неисполняемых файлов
        """
        mock_options = MagicMock()
        mock_options.binary_path = "/usr/bin/chrome"

        with patch("os.path.isabs", return_value=True):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.isfile", return_value=True):
                    with patch("os.access", return_value=False):
                        with pytest.raises(PermissionError):
                            path_resolver.resolve_path(mock_options)


class TestProfileManager:
    """Тесты для ProfileManager."""

    @pytest.fixture
    def profile_manager(self) -> ProfileManager:
        """Создает ProfileManager для тестов.

        Returns:
            ProfileManager экземпляр.
        """
        return ProfileManager()

    def test_profile_manager_create_profile(self, profile_manager: ProfileManager):
        """Тест создания профиля.

        Проверяет:
        - TemporaryDirectory создается
        - Путь к профилю возвращается
        """
        tempdir, profile_path = profile_manager.create_profile()

        assert tempdir is not None
        assert profile_path is not None
        assert os.path.exists(profile_path)

    def test_profile_manager_cleanup_profile(self, profile_manager: ProfileManager):
        """Тест очистки профиля.

        Проверяет:
        - Профиль удаляется после cleanup
        """
        tempdir, profile_path = profile_manager.create_profile()

        profile_manager.cleanup_profile()

        # Профиль должен быть удалён
        assert not os.path.exists(profile_path)

    def test_profile_manager_cleanup_fallback(self, caplog):
        """Тест fallback очистки профиля.

        Проверяет:
        - shutil.rmtree используется как fallback
        - Логирование работает корректно
        """

        manager = ProfileManager()
        tempdir, profile_path = manager.create_profile()

        # Mock cleanup для выбрасывания исключения
        with patch.object(tempdir, "cleanup", side_effect=OSError("Mocked OSError")):
            with patch("shutil.rmtree") as mock_rmtree:
                manager.cleanup_profile()

                # Проверяем что fallback был вызван
                mock_rmtree.assert_called_once()

    def test_profile_manager_cleanup_exception_logging(self, caplog):
        """Тест логирования исключений при очистке.

        Проверяет:
        - Исключения логируются корректно
        """
        import logging

        manager = ProfileManager()
        tempdir, profile_path = manager.create_profile()

        # Mock cleanup и rmtree для выбрасывания исключений
        with patch.object(tempdir, "cleanup", side_effect=OSError("Mocked OSError")):
            with patch("shutil.rmtree", side_effect=OSError("Mocked OSError")):
                with caplog.at_level(logging.ERROR):
                    manager.cleanup_profile()

                    # Проверяем что ошибка была залогирована
                    assert any("OSError" in record.message for record in caplog.records)

    def test_profile_manager_properties(self, profile_manager: ProfileManager):
        """Тест свойств ProfileManager.

        Проверяет:
        - profile_path возвращает корректное значение
        - profile_tempdir возвращает корректное значение
        """
        tempdir, profile_path = profile_manager.create_profile()

        assert profile_manager.profile_path == profile_path
        assert profile_manager.profile_tempdir is tempdir

        profile_manager.cleanup_profile()

        assert profile_manager.profile_path is not None  # Путь сохраняется
        assert profile_manager.profile_tempdir is tempdir


class TestProcessManager:
    """Тесты для ProcessManager."""

    @pytest.fixture
    def process_manager(self) -> ProcessManager:
        """Создает ProcessManager для тестов.

        Returns:
            ProcessManager экземпляр.
        """
        return ProcessManager()

    def test_process_manager_launch_process_silent(self, process_manager: ProcessManager):
        """Тест запуска процесса в тихом режиме.

        Проверяет:
        - subprocess.Popen вызывается с правильными аргументами
        - STDOUT и STDERR перенаправляются в DEVNULL
        """
        mock_options = MagicMock()
        mock_options.silent_browser = True

        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            process_manager.launch_process(
                chrome_cmd=["/usr/bin/chrome"],
                profile_path="/tmp/profile",
                chrome_options=mock_options,
            )

            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            assert call_args.kwargs["stderr"] == subprocess.DEVNULL
            assert call_args.kwargs["stdout"] == subprocess.DEVNULL

    def test_process_manager_launch_process_verbose(self, process_manager: ProcessManager):
        """Тест запуска процесса в обычном режиме.

        Проверяет:
        - subprocess.Popen вызывается без перенаправления
        """
        mock_options = MagicMock()
        mock_options.silent_browser = False

        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            process_manager.launch_process(
                chrome_cmd=["/usr/bin/chrome"],
                profile_path="/tmp/profile",
                chrome_options=mock_options,
            )

            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            assert call_args.kwargs.get("stderr") != subprocess.DEVNULL

    def test_process_manager_launch_process_exception(self, process_manager: ProcessManager):
        """Тест исключения при запуске процесса.

        Проверяет:
        - Исключения обрабатываются корректно
        - Профиль очищается при ошибке
        """
        mock_options = MagicMock()
        mock_options.silent_browser = True

        with patch("subprocess.Popen", side_effect=FileNotFoundError("Mocked FileNotFoundError")):
            with patch("shutil.rmtree") as mock_rmtree:
                with pytest.raises(FileNotFoundError):
                    process_manager.launch_process(
                        chrome_cmd=["/usr/bin/chrome"],
                        profile_path="/tmp/profile",
                        chrome_options=mock_options,
                    )

                # Проверяем что профиль был очищен
                mock_rmtree.assert_called_once()

    def test_process_manager_terminate_graceful_success(self, process_manager: ProcessManager):
        """Тест корректного завершения процесса.

        Проверяет:
        - terminate() вызывается
        - Процесс завершается успешно
        """
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.pid = 12345
        process_manager._proc = mock_proc

        success, status = process_manager.terminate_process_graceful(12345)

        assert success is True
        assert status == "terminated (exit code: 0)"
        mock_proc.terminate.assert_called_once()

    def test_process_manager_terminate_graceful_timeout(self, process_manager: ProcessManager):
        """Тест таймаута при корректном завершении.

        Проверяет:
        - wait() вызывается с timeout
        - При таймауте возвращается False
        """
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.terminate.return_value = None
        mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="chrome", timeout=5)
        mock_proc.pid = 12345
        process_manager._proc = mock_proc

        success, status = process_manager.terminate_process_graceful(12345)

        assert success is False
        assert status == "terminate_timeout"

    def test_process_manager_terminate_forceful_success(self, process_manager: ProcessManager):
        """Тест принудительного завершения процесса.

        Проверяет:
        - kill() вызывается
        - Процесс завершается успешно
        """
        mock_proc = MagicMock()
        mock_proc.poll.return_value = -9
        mock_proc.pid = 12345
        process_manager._proc = mock_proc

        success, status = process_manager.terminate_process_forceful(12345)

        assert success is True
        assert "killed" in status
        mock_proc.kill.assert_called_once()

    def test_process_manager_is_running(self, process_manager: ProcessManager):
        """Тест проверки состояния процесса.

        Проверяет:
        - is_running() возвращает корректное значение
        """
        # Процесс не запущен
        assert process_manager.is_running() is False

        # Процесс запущен
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        process_manager._proc = mock_proc

        assert process_manager.is_running() is True

    def test_process_manager_properties(self, process_manager: ProcessManager):
        """Тест свойств ProcessManager.

        Проверяет:
        - process возвращает корректное значение
        - pid возвращает корректное значение
        """
        assert process_manager.process is None
        assert process_manager.pid is None

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        process_manager._proc = mock_proc

        assert process_manager.process is mock_proc
        assert process_manager.pid == 12345


class TestBrowserLifecycleManager:
    """Тесты для BrowserLifecycleManager."""

    @pytest.fixture
    def mock_chrome_options(self) -> MagicMock:
        """Создает mock опций Chrome.

        Returns:
            MagicMock с опциями Chrome.
        """
        options = MagicMock()
        options.binary_path = None
        options.silent_browser = True
        options.headless = False
        options.start_maximized = False
        options.disable_images = False
        options.memory_limit = 2048
        return options

    def test_browser_lifecycle_manager_init(self, mock_chrome_options: MagicMock):
        """Тест инициализации BrowserLifecycleManager.

        Проверяет:
        - Компоненты инициализируются корректно
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        assert manager._path_resolver is not None
        assert manager._profile_manager is not None
        assert manager._process_manager is not None
        assert isinstance(manager._path_resolver, BrowserPathResolver)
        assert isinstance(manager._profile_manager, ProfileManager)
        assert isinstance(manager._process_manager, ProcessManager)

    def test_browser_lifecycle_manager_init_success(self, mock_chrome_options: MagicMock):
        """Тест успешной инициализации браузера.

        Проверяет:
        - Все компоненты вызываются корректно
        - Порт возвращается
        """
        with patch.object(BrowserPathResolver, "resolve_path", return_value="/usr/bin/chrome"):
            with patch.object(
                ProfileManager, "create_profile", return_value=(MagicMock(), "/tmp/profile")
            ):
                with patch("parser_2gis.chrome.browser.free_port", return_value=9222):
                    with patch.object(ProcessManager, "launch_process") as mock_launch:
                        manager = BrowserLifecycleManager(mock_chrome_options)
                        port = manager.init()

                        assert port == 9222
                        mock_launch.assert_called_once()

    def test_browser_lifecycle_manager_init_exception(self, mock_chrome_options: MagicMock):
        """Тест исключения при инициализации.

        Проверяет:
        - Профиль очищается при ошибке ПОСЛЕ его создания
        - Исключение пробрасывается
        """
        with patch.object(BrowserPathResolver, "resolve_path", return_value="/usr/bin/chrome"):
            with patch.object(
                ProfileManager, "create_profile", return_value=(MagicMock(), "/tmp/profile")
            ):
                with patch.object(
                    ProcessManager, "launch_process", side_effect=FileNotFoundError("Mocked error")
                ):
                    with patch.object(ProfileManager, "cleanup_profile") as mock_cleanup:
                        manager = BrowserLifecycleManager(mock_chrome_options)

                        with pytest.raises(FileNotFoundError):
                            manager.init()

                        # Проверяем что профиль был очищен
                        mock_cleanup.assert_called()

    def test_browser_lifecycle_manager_close(self, mock_chrome_options: MagicMock):
        """Тест закрытия браузера.

        Проверяет:
        - Процесс завершается корректно
        - Профиль очищается
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Mock процесс
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None
        manager._process_manager._proc = mock_proc

        with patch.object(
            manager._process_manager,
            "terminate_process_graceful",
            return_value=(True, "terminated"),
        ):
            with patch.object(manager._profile_manager, "cleanup_profile") as mock_cleanup:
                manager.close()

                # Проверяем что профиль был очищен
                mock_cleanup.assert_called()

    def test_browser_lifecycle_manager_close_idempotent(self, mock_chrome_options: MagicMock):
        """Тест идемпотентности close.

        Проверяет:
        - Повторный вызов close игнорируется
        """
        manager = BrowserLifecycleManager(mock_chrome_options)
        manager._closed = True

        with patch.object(manager._process_manager, "terminate_process_graceful") as mock_terminate:
            with patch.object(manager._profile_manager, "cleanup_profile") as mock_cleanup:
                manager.close()

                # Проверяем что методы не были вызваны
                mock_terminate.assert_not_called()
                mock_cleanup.assert_not_called()

    def test_browser_lifecycle_manager_build_chrome_cmd(self, mock_chrome_options: MagicMock):
        """Тест построения команды Chrome.

        Проверяет:
        - Команда строится корректно
        - Все аргументы добавляются
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        assert "/usr/bin/chrome" in cmd
        assert "--remote-debugging-port=9222" in cmd
        assert "--user-data-dir=/tmp/profile" in cmd
        assert "--no-sandbox" in cmd
        assert "--max-old-space-size=2048" in cmd

    def test_browser_lifecycle_manager_build_chrome_cmd_headless(
        self, mock_chrome_options: MagicMock
    ):
        """Тест построения команды Chrome в headless режиме.

        Проверяет:
        - Headless аргументы добавляются
        """
        mock_chrome_options.headless = True

        manager = BrowserLifecycleManager(mock_chrome_options)

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        assert "--headless" in cmd
        assert "--disable-gpu" in cmd

    def test_browser_lifecycle_manager_build_chrome_cmd_disable_images(
        self, mock_chrome_options: MagicMock
    ):
        """Тест построения команды Chrome с отключенными изображениями.

        Проверяет:
        - Аргумент отключения изображений добавляется
        """
        mock_chrome_options.disable_images = True

        manager = BrowserLifecycleManager(mock_chrome_options)

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        assert "--blink-settings=imagesEnabled=false" in cmd

    def test_browser_lifecycle_manager_weakref_finalizer(self, mock_chrome_options: MagicMock):
        """Тест weakref.finalizer для гарантированной очистки.

        Проверяет:
        - Finalizer регистрируется корректно
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        assert hasattr(manager, "_finalizer")
        assert manager._finalizer is not None

    def test_browser_lifecycle_manager_cleanup_from_finalizer(self, mock_chrome_options: MagicMock):
        """Тест очистки из finalizer.

        Проверяет:
        - Процесс завершается при вызове finalizer
        - Профиль очищается
        """
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        mock_tempdir = MagicMock()

        BrowserLifecycleManager._cleanup_from_finalizer(mock_proc, mock_tempdir, "/tmp/profile")

        mock_proc.terminate.assert_called()
        mock_tempdir.cleanup.assert_called()
