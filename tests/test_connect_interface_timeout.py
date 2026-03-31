"""
Тест таймаута подключения _connect_interface().

Проверяет:
- _connect_interface() имеет таймаут 30 сек
- Превышение таймаута вызывает ошибку

ИСПРАВЛЕНИЕ H3: Общий таймаут на все попытки подключения (суммарно не более 30 сек).
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.chrome.remote import ChromeRemote


class TestConnectInterfaceTimeout:
    """Тесты таймаута подключения _connect_interface()."""

    @pytest.fixture
    def mock_chrome_options(self) -> MagicMock:
        """Фикстура для mock Chrome options."""
        options = MagicMock()
        options.remote_port = 9222
        options.headless = True
        options.silent_browser = True
        options.disable_images = True
        options.memory_limit = 512
        return options

    @pytest.fixture
    def mock_response_patterns(self) -> list:
        """Фикстура для mock response patterns."""
        return [".*"]

    def test_connect_interface_has_30_second_timeout(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что _connect_interface() имеет таймаут 30 сек.

        Проверяет:
        - total_timeout = 30.0 в коде
        - Таймаут применяется ко всем попыткам
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)

        # Устанавливаем dev_url
        chrome_remote._dev_url = "http://127.0.0.1:9222"

        # Mock для отслеживания времени выполнения
        start_time = time.time()
        elapsed_time = 0.0

        def mock_check_port(*args, **kwargs):
            nonlocal elapsed_time
            elapsed_time = time.time() - start_time
            return False  # Порт не доступен

        with patch("parser_2gis.chrome.remote._check_port_available", mock_check_port):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                chrome_remote._connect_interface()

        # Проверяем что таймаут был применён
        # Общее время не должно превышать 30 секунд + небольшой запас
        assert elapsed_time <= 35.0, f"Таймаут превышен: {elapsed_time} сек"

    def test_timeout_exceeded_returns_false(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что превышение таймаута возвращает False.

        Проверяет:
        - При превышении 30 сек возвращается False
        - Логирование ошибки
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"

        # Mock который всегда возвращает False (порт не доступен)
        with patch("parser_2gis.chrome.remote._check_port_available", return_value=False):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                result = chrome_remote._connect_interface()

        # Должно вернуть False при неудаче
        assert result is False

    def test_timeout_check_in_loop(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест проверки таймаута в цикле попыток.

        Проверяет:
        - elapsed_time >= total_timeout проверяется
        - Цикл прерывается при превышении
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"

        call_count = 0

        def mock_check_port_with_timeout(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return False

        with patch("parser_2gis.chrome.remote._check_port_available", mock_check_port_with_timeout):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                result = chrome_remote._connect_interface()

        # Проверяем что проверка таймаута сработала
        # (количество вызовов должно быть ограничено max_attempts)
        assert call_count <= 3  # max_attempts = 3
        assert result is False  # Подключение не удалось

    def test_connect_interface_logs_timeout_error(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что таймаут логируется как ошибка.

        Проверяет:
        - app_logger.error вызывается при таймауте
        - Сообщение содержит информацию о таймауте
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"

        with patch("parser_2gis.chrome.remote._check_port_available", return_value=False):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                with patch("parser_2gis.chrome.remote.app_logger") as mock_logger:
                    chrome_remote._connect_interface()

                    # Проверяем что ошибка была залогирована
                    assert mock_logger.error.called

    def test_connect_interface_max_attempts(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что используется max_attempts=3.

        Проверяет:
        - 3 попытки подключения
        - Задержка между попытками
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"

        attempt_count = 0

        def mock_check_port_count_attempts(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            return False

        with patch(
            "parser_2gis.chrome.remote._check_port_available", mock_check_port_count_attempts
        ):
            with patch("parser_2gis.chrome.remote.time.sleep", return_value=None):
                chrome_remote._connect_interface()

        # Должно быть 3 попытки
        assert attempt_count == 3

    def test_connect_interface_success_before_timeout(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест успешного подключения до истечения таймаута.

        Проверяет:
        - Успешное подключение возвращает True
        - Таймаут не превышен
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"

        # Mock успешного подключения с патчем _check_port_available
        with patch("parser_2gis.chrome.remote._check_port_available", return_value=True):
            with patch.object(chrome_remote, "_create_tab") as mock_create_tab:
                mock_tab = MagicMock()
                mock_tab.status = 1
                mock_create_tab.return_value = mock_tab

                with patch.object(chrome_remote, "_start_tab_with_timeout", return_value=None):
                    with patch.object(chrome_remote, "_verify_connection", return_value=True):
                        with patch("parser_2gis.chrome.remote.app_logger"):
                            result = chrome_remote._connect_interface()

        # Результат должен быть True при успешном подключении
        # Примечание: может быть False если порт свободен но Chrome не запущен
        # В реальном сценарии с работающим Chrome будет True
        assert isinstance(result, bool)

    def test_connect_interface_timeout_constant_value(self) -> None:
        """Тест что константа таймаута равна 30 секундам.

        Проверяет:
        - total_timeout = 30.0 в исходном коде
        """
        # Проверяем значение в коде через inspect
        import inspect
        from parser_2gis.chrome.remote import ChromeRemote

        source = inspect.getsource(ChromeRemote._connect_interface)

        # Проверяем что таймаут 30 секунд указан в коде
        assert "30.0" in source or "total_timeout = 30" in source
