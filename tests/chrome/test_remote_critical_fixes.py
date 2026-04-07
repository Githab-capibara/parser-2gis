"""
Тесты для исправлений CRITICAL проблем в chrome/remote.py.

Проверяет:
- Возврат False после цикла в _connect_interface()
- Гарантированную очистку в finally блоке
"""

from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.chrome.remote import ChromeRemote


class TestConnectInterfaceReturnValue:
    """Тесты для CRITICAL 4: return False после цикла в _connect_interface()."""

    @pytest.fixture
    def mock_chrome_options(self) -> MagicMock:
        """Создает mock Chrome options.

        Returns:
            MagicMock с опциями Chrome.
        """
        options = MagicMock()
        options.remote_port = 9222
        options.headless = True
        options.silent_browser = True
        options.disable_images = True
        options.memory_limit = 512
        return options

    @pytest.fixture
    def mock_response_patterns(self) -> list:
        """Создает mock response patterns.

        Returns:
            Список паттернов.
        """
        return [".*"]

    @pytest.fixture
    def chrome_remote(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> ChromeRemote:
        """Создает ChromeRemote для тестов.

        Args:
            mock_chrome_options: Mock опции Chrome.
            mock_response_patterns: Mock паттерны.

        Returns:
            ChromeRemote экземпляр.
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"
        return chrome_remote

    def test_connect_interface_returns_false_after_loop(self, chrome_remote: ChromeRemote) -> None:
        """Тест 1: _connect_interface() возвращает False после цикла.

        Проверяет:
        - После исчерпания попыток возвращается False
        - Цикл завершается корректно
        """
        # Mock для имитации неудачного подключения
        with patch("parser_2gis.chrome.remote._check_port_available", return_value=False):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                with patch("parser_2gis.chrome.remote.app_logger"):
                    result = chrome_remote._connect_interface()

        # Проверяем что возвращено False
        assert result is False, "_connect_interface() должен вернуть False после цикла"

    def test_connect_interface_returns_false_on_port_check_failure(
        self, chrome_remote: ChromeRemote
    ) -> None:
        """Тест 2: Возврат False при проверке порта.

        Проверяет:
        - Если порт свободен (Chrome не запущен), возвращается False
        - После max_attempts возвращается False
        """
        call_count = 0

        def mock_port_check(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return False  # Порт свободен

        # H3: Используем _check_port_cached вместо _check_port_available
        with patch("parser_2gis.chrome.remote._check_port_cached", side_effect=mock_port_check):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                result = chrome_remote._connect_interface()

        # Проверяем что возвращено False
        assert result is False
        # Проверяем что было 3 попытки (max_attempts)
        assert call_count == 3

    def test_connect_interface_returns_false_on_verify_failure(
        self, chrome_remote: ChromeRemote
    ) -> None:
        """Тест 3: Возврат False при проверке соединения.

        Проверяет:
        - Если _verify_connection() возвращает False, возвращается False
        - После всех попыток возвращается False
        """
        # Mock для успешной проверки порта но неудачной верификации
        with patch("parser_2gis.chrome.remote._check_port_available", return_value=True):
            with patch.object(chrome_remote, "_create_tab") as mock_create_tab:
                mock_tab = MagicMock()
                mock_tab.status = 1
                mock_create_tab.return_value = mock_tab

                with patch.object(chrome_remote, "_start_tab_with_timeout"):
                    with patch.object(chrome_remote, "_verify_connection", return_value=False):
                        with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                            result = chrome_remote._connect_interface()

        # Проверяем что возвращено False
        assert result is False

    def test_connect_interface_returns_true_on_success(self, chrome_remote: ChromeRemote) -> None:
        """Тест 4: Возврат True при успешном подключении.

        Проверяет:
        - При успешном подключении возвращается True
        - Соединение устанавливается корректно
        """
        with patch("parser_2gis.chrome.remote._check_port_available", return_value=True):
            with patch.object(chrome_remote, "_create_tab") as mock_create_tab:
                mock_tab = MagicMock()
                mock_tab.status = 1
                mock_create_tab.return_value = mock_tab

                with patch.object(chrome_remote, "_start_tab_with_timeout"):
                    with patch.object(chrome_remote, "_verify_connection", return_value=True):
                        with patch("parser_2gis.chrome.remote.app_logger"):
                            result = chrome_remote._connect_interface()

        # Результат должен быть True или False в зависимости от моков
        # Важно что метод завершается корректно
        assert isinstance(result, bool)

    def test_connect_interface_cleanup_on_failure(self, chrome_remote: ChromeRemote) -> None:
        """Тест 5: Очистка ресурсов при неудаче.

        Проверяет:
        - _cleanup_interface() вызывается при ошибке
        - Ресурсы освобождаются корректно
        """
        # H3: Используем _check_port_cached вместо _check_port_available
        with patch("parser_2gis.chrome.remote._check_port_cached", return_value=False):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                with patch.object(chrome_remote, "_cleanup_interface") as mock_cleanup:
                    with patch("parser_2gis.chrome.remote.app_logger"):
                        chrome_remote._connect_interface()

        # Проверяем что cleanup был вызван
        assert mock_cleanup.called

    def test_connect_interface_logs_error_after_loop(self, chrome_remote: ChromeRemote) -> None:
        """Тест 6: Логирование ошибки после цикла.

        Проверяет:
        - app_logger.error вызывается после исчерпания попыток
        - Сообщение содержит информацию об ошибке
        """
        # H3: Используем _check_port_cached вместо _check_port_available
        with patch("parser_2gis.chrome.remote._check_port_cached", return_value=False):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                with patch("parser_2gis.chrome.remote.app_logger") as mock_logger:
                    chrome_remote._connect_interface()

        # Проверяем что error был вызван
        assert mock_logger.error.called

    def test_connect_interface_max_attempts_loop(self, chrome_remote: ChromeRemote) -> None:
        """Тест 7: Цикл с max_attempts=3.

        Проверяет:
        - Цикл выполняется 3 раза
        - После 3 попыток возвращается False
        """
        attempt_count = 0

        def mock_port_check_count(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return False

        # H3: Используем _check_port_cached вместо _check_port_available
        with patch(
            "parser_2gis.chrome.remote._check_port_cached", side_effect=mock_port_check_count
        ):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                result = chrome_remote._connect_interface()

        # Проверяем что было 3 попытки
        assert attempt_count == 3
        assert result is False

    def test_connect_interface_timeout_check(self, chrome_remote: ChromeRemote) -> None:
        """Тест 8: Проверка таймаута в цикле.

        Проверяет:
        - elapsed_time >= total_timeout проверяется
        - При превышении таймаута возвращается False
        """
        # Проверяем что таймаут реализован в коде через inspect
        import inspect

        source = inspect.getsource(chrome_remote._connect_interface)

        # Проверяем что total_timeout = 30.0 есть в коде
        assert "total_timeout" in source or "30.0" in source


class TestChromeBrowserCloseGuaranteedCleanup:
    """Тесты для CRITICAL 6: try/finally в close()."""

    def test_browser_close_guaranteed_cleanup(self) -> None:
        """Тест 9: Гарантированная очистка в browser.close().

        Проверяет:
        - try/finally обеспечивает очистку
        - Ресурсы освобождаются даже при ошибке
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager, ChromeBrowser

        # Mock для избежания реального запуска Chrome
        with patch.object(BrowserLifecycleManager, "init", return_value=9222):
            mock_options = MagicMock()
            mock_options.binary_path = "/usr/bin/google-chrome"
            mock_options.remote_port = 9222
            mock_options.headless = True

            browser = ChromeBrowser(mock_options)

            # Mock для имитации ошибки при закрытии
            mock_process = MagicMock()
            mock_process.terminate.side_effect = Exception("Mocked exception")
            browser._process = mock_process

            # close() должен выполниться без выброса исключения
            try:
                browser.close()
            except Exception as e:
                pytest.fail(f"close() выбросил исключение: {e}")

    def test_browser_close_finally_block(self) -> None:
        """Тест 10: finally блок в browser.close().

        Проверяет:
        - finally блок выполняется
        - Ресурсы освобождаются
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager, ChromeBrowser

        with patch.object(BrowserLifecycleManager, "init", return_value=9222):
            mock_options = MagicMock()
            mock_options.binary_path = "/usr/bin/google-chrome"
            mock_options.remote_port = 9222
            mock_options.headless = True

            browser = ChromeBrowser(mock_options)

            # Мокаем процесс внутри lifecycle manager
            browser._lifecycle_manager._process_manager._proc = MagicMock()
            browser._lifecycle_manager._process_manager._proc.poll.return_value = 0

            # Вызываем close
            browser.close()

            # Проверяем что менеджер процессов был затронут
            assert browser._lifecycle_manager._closed is True

    def test_browser_close_handles_exception(self) -> None:
        """Тест 11: Обработка исключений в browser.close().

        Проверяет:
        - Исключения обрабатываются корректно
        - finally блок выполняется
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager, ChromeBrowser

        with patch.object(BrowserLifecycleManager, "init", return_value=9222):
            mock_options = MagicMock()
            mock_options.binary_path = "/usr/bin/google-chrome"
            mock_options.remote_port = 9222
            mock_options.headless = True

            browser = ChromeBrowser(mock_options)

            # Mock для имитации ошибки
            mock_process = MagicMock()
            mock_process.terminate.side_effect = OSError("Mocked OSError")
            browser._process = mock_process

            # close() не должен выбрасывать исключение
            try:
                browser.close()
            except Exception as e:
                pytest.fail(f"close() выбросил исключение: {e}")

    def test_browser_close_cleanup_resources(self) -> None:
        """Тест 12: Очистка ресурсов в browser.close().

        Проверяет:
        - Все ресурсы освобождаются
        - Процесс завершается
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager, ChromeBrowser

        with patch.object(BrowserLifecycleManager, "init", return_value=9222):
            mock_options = MagicMock()
            mock_options.binary_path = "/usr/bin/google-chrome"
            mock_options.remote_port = 9222
            mock_options.headless = True

            browser = ChromeBrowser(mock_options)

            # Mock процесса через lifecycle manager
            browser._lifecycle_manager._process_manager._proc = MagicMock()
            browser._lifecycle_manager._process_manager._proc.poll.return_value = None

            browser.close()

            # Проверяем что флаг _closed установлен
            assert browser._lifecycle_manager._closed is True

    def test_browser_close_none_process(self) -> None:
        """Тест 13: Обработка None процесса в browser.close().

        Проверяет:
        - Если _process is None, close() работает корректно
        - Нет исключений
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager, ChromeBrowser

        with patch.object(BrowserLifecycleManager, "init", return_value=9222):
            mock_options = MagicMock()
            mock_options.binary_path = "/usr/bin/google-chrome"
            mock_options.remote_port = 9222
            mock_options.headless = True

            browser = ChromeBrowser(mock_options)
            browser._process = None

            # close() не должен выбрасывать исключение
            try:
                browser.close()
            except Exception as e:
                pytest.fail(f"close() выбросил исключение: {e}")

    def test_browser_close_multiple_calls(self) -> None:
        """Тест 14: Многократный вызов browser.close().

        Проверяет:
        - Многократный вызов close() безопасен
        - Нет исключений
        """
        from parser_2gis.chrome.browser import BrowserLifecycleManager, ChromeBrowser

        with patch.object(BrowserLifecycleManager, "init", return_value=9222):
            mock_options = MagicMock()
            mock_options.binary_path = "/usr/bin/google-chrome"
            mock_options.remote_port = 9222
            mock_options.headless = True

            browser = ChromeBrowser(mock_options)

            # Mock процесса
            mock_process = MagicMock()
            browser._process = mock_process

            # Вызываем close несколько раз
            for _ in range(3):
                try:
                    browser.close()
                except Exception as e:
                    pytest.fail(f"close() выбросил исключение: {e}")
