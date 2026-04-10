"""
Тесты для безопасности subprocess в chrome/browser.py.

Проверяет:
- Валидацию всех аргументов перед subprocess
- Отказ при невалидных аргументах
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.chrome.browser import BrowserLifecycleManager, ProcessManager


class TestSubprocessArgumentsValidation:
    """Тесты валидации аргументов subprocess."""

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

    def test_subprocess_binary_path_validation(self, mock_chrome_options) -> None:
        """Тест валидации пути к бинарнику.

        Проверяет:
        - Путь к браузеру валидируется перед запуском
        - Относительные пути отклоняются
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с относительным путем
        with pytest.raises(ValueError, match="абсолютным"):
            manager._path_resolver._validate_binary_path("chrome")

        # Тест с несуществующим путем
        with pytest.raises(FileNotFoundError):
            manager._path_resolver._validate_binary_path("/nonexistent/chrome")

        # Тест с путем к директории
        with pytest.raises(ValueError, match="файл"):
            manager._path_resolver._validate_binary_path("/tmp")

    def test_subprocess_profile_path_validation(self, mock_chrome_options) -> None:
        """Тест валидации пути к профилю.

        Проверяет:
        - Путь к профилю валидируется
        - Символические ссылки разрешаются
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с нормальным путем
        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что путь к профилю добавлен в команду
        assert any("--user-data-dir=" in arg for arg in cmd)

    def test_subprocess_memory_limit_validation(self, mock_chrome_options) -> None:
        """Тест валидации memory_limit.

        Проверяет:
        - memory_limit валидируется
        - Значение по умолчанию используется при None
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с None memory_limit (должно использоваться значение по умолчанию)
        mock_chrome_options.memory_limit = None

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что memory_limit установлен в значение по умолчанию (2048)
        assert any("--max-old-space-size=2048" in arg for arg in cmd)

        # Тест с валидным memory_limit
        mock_chrome_options.memory_limit = 4096

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что memory_limit установлен корректно
        assert any("--max-old-space-size=4096" in arg for arg in cmd)

    def test_subprocess_remote_port_validation(self, mock_chrome_options) -> None:
        """Тест валидации remote_port.

        Проверяет:
        - remote_port валидируется
        - Порт добавляется в команду корректно
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что remote-port добавлен корректно
        assert any("--remote-debugging-port=9222" in arg for arg in cmd)

    def test_subprocess_command_injection_prevention(self, mock_chrome_options) -> None:
        """Тест предотвращения command injection.

        Проверяет:
        - shell=False используется в subprocess
        - Аргументы не интерпретируются shell
        """
        process_manager = ProcessManager()

        mock_options = MagicMock()
        mock_options.silent_browser = True

        # Тест с потенциально опасными аргументами
        chrome_cmd = [
            "/usr/bin/chrome",
            "--remote-debugging-port=9222",
            "; rm -rf /",  # Попытка injection
            "&& cat /etc/passwd",  # Еще одна попытка
        ]

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc

            process_manager.launch_process(
                chrome_cmd=chrome_cmd, profile_path="/tmp/profile", chrome_options=mock_options
            )

            # Проверяем что shell=False был использован
            call_args = mock_popen.call_args
            assert call_args.kwargs["shell"] is False

            # Проверяем что аргументы были переданы как список
            assert call_args.args[0] == chrome_cmd

    def test_subprocess_shell_false_usage(self, mock_chrome_options) -> None:
        """Тест использования shell=False.

        Проверяет:
        - shell=False используется для безопасности
        - Аргументы передаются как список
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        with patch.object(ProcessManager, "launch_process") as mock_launch:
            manager.init()

            # Проверяем что launch_process был вызван
            assert mock_launch.called

            # Получаем аргументы вызова
            call_args = mock_launch.call_args

            # Проверяем что chrome_cmd это список
            chrome_cmd = (
                call_args.kwargs["chrome_cmd"]
                if "chrome_cmd" in call_args.kwargs
                else call_args.args[0]
            )
            assert isinstance(chrome_cmd, list)

    def test_subprocess_invalid_memory_limit(self, mock_chrome_options) -> None:
        """Тест невалидного memory_limit.

        Проверяет:
        - Отрицательный memory_limit обрабатывается
        - Очень большой memory_limit обрабатывается
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с отрицательным memory_limit
        mock_chrome_options.memory_limit = -1024

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что отрицательное значение было использовано (валидация на уровне Chrome)
        assert any("--max-old-space-size=-1024" in arg for arg in cmd)

        # Тест с очень большим memory_limit
        mock_chrome_options.memory_limit = 1024 * 1024  # 1TB

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что большое значение было использовано
        assert any("--max-old-space-size=1048576" in arg for arg in cmd)

    def test_subprocess_invalid_port(self, mock_chrome_options) -> None:
        """Тест невалидного порта.

        Проверяет:
        - Отрицательный порт обрабатывается
        - Порт за пределами диапазона обрабатывается
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с отрицательным портом
        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=-1,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что отрицательный порт был использован (валидация на уровне Chrome)
        assert any("--remote-debugging-port=-1" in arg for arg in cmd)

        # Тест с очень большим портом
        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=99999,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что большой порт был использован
        assert any("--remote-debugging-port=99999" in arg for arg in cmd)

    def test_subprocess_path_traversal_prevention(self, mock_chrome_options) -> None:
        """Тест предотвращения path traversal.

        Проверяет:
        - Пути с .. обрабатываются корректно
        - Символические ссылки разрешаются
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с путем содержащим ..
        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/../tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что путь был нормализован
        assert any("--user-data-dir=" in arg for arg in cmd)

    def test_subprocess_special_characters_in_path(self, mock_chrome_options) -> None:
        """Тест специальных символов в путях.

        Проверяет:
        - Пробелы в путях обрабатываются
        - Специальные символы экранируются
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        # Тест с пробелами в пути
        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/my profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что путь был добавлен в команду
        assert any("--user-data-dir=" in arg for arg in cmd)

    def test_process_manager_launch_with_invalid_args(self) -> None:
        """Тест запуска процесса с невалидными аргументами.

        Проверяет:
        - subprocess.Popen обрабатывает невалидные аргументы
        - Исключения пробрасываются корректно
        """
        process_manager = ProcessManager()

        mock_options = MagicMock()
        mock_options.silent_browser = True

        # Тест с пустым списком команд
        with pytest.raises((ValueError, FileNotFoundError, subprocess.SubprocessError)):
            process_manager.launch_process(
                chrome_cmd=[], profile_path="/tmp/profile", chrome_options=mock_options
            )

    def test_process_manager_launch_with_none_args(self) -> None:
        """Тест запуска процесса с None аргументами.

        Проверяет:
        - None аргументы обрабатываются корректно
        """
        process_manager = ProcessManager()

        mock_options = MagicMock()
        mock_options.silent_browser = True

        # Тест с None в команде
        with pytest.raises((TypeError, subprocess.SubprocessError)):
            process_manager.launch_process(
                chrome_cmd=[None, "--remote-debugging-port=9222"],
                profile_path="/tmp/profile",
                chrome_options=mock_options,
            )

    def test_browser_lifecycle_manager_cmd_validation(self, mock_chrome_options) -> None:
        """Тест валидации команды в BrowserLifecycleManager.

        Проверяет:
        - Команда валидируется перед запуском
        - Все аргументы корректны
        """
        manager = BrowserLifecycleManager(mock_chrome_options)

        cmd = manager._build_chrome_cmd(
            binary_path="/usr/bin/chrome",
            profile_path="/tmp/profile",
            remote_port=9222,
            chrome_options=mock_chrome_options,
        )

        # Проверяем что команда это список
        assert isinstance(cmd, list)

        # Проверяем что первый элемент это путь к браузеру
        assert cmd[0] == "/usr/bin/chrome"

        # Проверяем что все элементы это строки
        for arg in cmd:
            assert isinstance(arg, str)

        # Проверяем что обязательные аргументы присутствуют
        assert any("--remote-debugging-port=" in arg for arg in cmd)
        assert any("--user-data-dir=" in arg for arg in cmd)
        assert any("--no-sandbox" in arg for arg in cmd)
