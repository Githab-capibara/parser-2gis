"""
Тесты для метода _cleanup_interface() в chrome/remote.py.

Проверяет:
- Корректное освобождение ресурсов вкладки
- Обработку ошибок при очистке
- Сброс _chrome_tab в None
- Обработку ошибок при закрытии внешнего HTTP-запроса
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from parser_2gis.chrome.remote import ChromeRemote


class TestCleanupInterface:
    """Тесты метода _cleanup_interface()."""

    @pytest.fixture
    def mock_chrome_options(self) -> MagicMock:
        """Создаёт mock Chrome options."""
        options = MagicMock()
        options.remote_port = 9222
        options.headless = True
        return options

    @pytest.fixture
    def mock_response_patterns(self) -> list:
        """Создаёт mock response patterns."""
        return [".*"]

    @pytest.fixture
    def chrome_remote(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> ChromeRemote:
        """Создаёт ChromeRemote для тестов."""
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._dev_url = "http://127.0.0.1:9222"
        return chrome_remote

    def test_cleanup_interface_with_started_tab(self, chrome_remote: ChromeRemote) -> None:
        """Тест 1: Очистка вкладки со статусом started."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        mock_tab.id = "tab-123"
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request") as mock_request:
            mock_request.return_value = MagicMock()
            chrome_remote._cleanup_interface()

        mock_tab.stop.assert_called_once()
        mock_request.assert_called_once_with(
            "put",
            "http://127.0.0.1:9222/json/close/tab-123",
            timeout=10,
            verify=True,
        )
        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_with_stopped_tab(self, chrome_remote: ChromeRemote) -> None:
        """Тест 2: Очистка вкладки со статусом stopped — stop() не вызывается."""
        mock_tab = MagicMock()
        mock_tab.status = "stopped"
        mock_tab.id = "tab-456"
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request") as mock_request:
            mock_request.return_value = MagicMock()
            chrome_remote._cleanup_interface()

        mock_tab.stop.assert_not_called()
        mock_request.assert_called_once()
        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_os_error_on_stop(self, chrome_remote: ChromeRemote) -> None:
        """Тест 3: OSError при stop() — не должен падать."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        mock_tab.id = "tab-789"
        mock_tab.stop.side_effect = OSError("Mocked OSError")
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request"):
            chrome_remote._cleanup_interface()

        # Вкладка всё равно должна быть очищена
        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_runtime_error_on_stop(self, chrome_remote: ChromeRemote) -> None:
        """Тест 4: RuntimeError при stop() — не должен падать."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        mock_tab.id = "tab-001"
        mock_tab.stop.side_effect = RuntimeError("Mocked RuntimeError")
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request"):
            chrome_remote._cleanup_interface()

        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_http_error_on_close_request(self, chrome_remote: ChromeRemote) -> None:
        """Тест 5: Ошибка HTTP-запроса при закрытии вкладки."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        mock_tab.id = "tab-002"
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request") as mock_request:
            from requests import RequestException
            mock_request.side_effect = RequestException("HTTP error")
            chrome_remote._cleanup_interface()

        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_key_error_on_close(self, chrome_remote: ChromeRemote) -> None:
        """Тест 6: KeyError при закрытии вкладки."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        mock_tab.id = "tab-003"
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request") as mock_request:
            mock_request.side_effect = KeyError("missing key")
            chrome_remote._cleanup_interface()

        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_attribute_error_on_tab(self, chrome_remote: ChromeRemote) -> None:
        """Тест 7: AttributeError при доступе к атрибутам вкладки."""
        mock_tab = MagicMock()
        type(mock_tab).status = PropertyMock(side_effect=AttributeError("No status"))
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request"):
            chrome_remote._cleanup_interface()

        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_none_tab(self, chrome_remote: ChromeRemote) -> None:
        """Тест 8: Очистка когда _chrome_tab уже None."""
        chrome_remote._chrome_tab = None
        chrome_remote._chrome_interface = MagicMock()

        chrome_remote._cleanup_interface()

        assert chrome_remote._chrome_tab is None
        assert chrome_remote._chrome_interface is None

    def test_cleanup_interface_clears_chrome_interface(self, chrome_remote: ChromeRemote) -> None:
        """Тест 9: _chrome_interface сбрасывается в None."""
        mock_tab = MagicMock()
        mock_tab.status = "stopped"
        mock_tab.id = "tab-004"
        chrome_remote._chrome_tab = mock_tab
        chrome_remote._chrome_interface = MagicMock()

        with patch("parser_2gis.chrome.remote._safe_external_request"):
            chrome_remote._cleanup_interface()

        assert chrome_remote._chrome_interface is None

    def test_cleanup_interface_no_dev_url(self, chrome_remote: ChromeRemote) -> None:
        """Тест 10: Очистка без dev_url — HTTP-запрос не делается."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        mock_tab.id = "tab-005"
        chrome_remote._chrome_tab = mock_tab
        chrome_remote._dev_url = None

        with patch("parser_2gis.chrome.remote._safe_external_request") as mock_request:
            chrome_remote._cleanup_interface()

        mock_request.assert_not_called()
        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_multiple_calls(self, chrome_remote: ChromeRemote) -> None:
        """Тест 11: Многократный вызов безопасен."""
        mock_tab = MagicMock()
        mock_tab.status = "stopped"
        mock_tab.id = "tab-006"
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request"):
            chrome_remote._cleanup_interface()
            chrome_remote._cleanup_interface()  # Второй вызов

        # Не должно быть исключений
        assert chrome_remote._chrome_tab is None

    def test_cleanup_interface_outer_exception(self, chrome_remote: ChromeRemote) -> None:
        """Тест 12: Непредвиденная ошибка на внешнем уровне try/except."""
        mock_tab = MagicMock()
        mock_tab.status = "started"
        # Имитируем AttributeError на внешнем уровне
        type(mock_tab).id = PropertyMock(side_effect=AttributeError("outer error"))
        chrome_remote._chrome_tab = mock_tab

        with patch("parser_2gis.chrome.remote._safe_external_request"):
            # Не должно выбрасывать исключение
            chrome_remote._cleanup_interface()

        # Метод должен завершиться без исключений
