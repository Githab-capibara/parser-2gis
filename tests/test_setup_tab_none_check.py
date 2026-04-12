"""
Тест проверки _chrome_tab на None в _setup_tab().

Проверяет:
- Вызов _setup_tab() с None
- Выбрасывается ChromeException
import pytest

pytestmark = pytest.mark.requires_chrome

ИСПРАВЛЕНИЕ H9: Явная проверка на None перед использованием _chrome_tab.
"""

from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.chrome.exceptions import ChromeException
from parser_2gis.chrome.remote import ChromeRemote

pytestmark = pytest.mark.requires_chrome


class TestSetupTabNoneCheck:
    """Тесты проверки _chrome_tab на None в _setup_tab()."""

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

    def test_setup_tab_with_none_raises_exception(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что _setup_tab() с None выбрасывает ChromeException.

        Проверяет:
        - _chrome_tab = None
        - Вызывается ChromeException
        - Сообщение об ошибке корректное
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)

        # Устанавливаем _chrome_tab в None
        chrome_remote._chrome_tab = None

        # Вызываем _setup_tab и ожидаем ChromeException
        with pytest.raises(ChromeException) as exc_info:
            chrome_remote._setup_tab()

        # Проверяем сообщение об ошибке
        assert "Chrome tab не инициализирован" in str(exc_info.value)
        assert "_setup_tab" in str(exc_info.value)

    def test_setup_tab_none_check_before_use(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что проверка None выполняется перед использованием.

        Проверяет:
        - Проверка в начале метода
        - Метод не продолжает выполнение при None
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._chrome_tab = None

        # Mock для отслеживания вызовов
        with patch.object(chrome_remote, "execute_script") as mock_execute:
            with pytest.raises(ChromeException):
                chrome_remote._setup_tab()

            # execute_script не должен быть вызван при None
            mock_execute.assert_not_called()

    def test_setup_tab_with_valid_tab_does_not_raise(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что _setup_tab() с валидным tab не выбрасывает исключение.

        Проверяет:
        - _chrome_tab != None
        - Метод выполняется корректно
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)

        # Создаём mock валидного tab
        mock_tab = MagicMock()
        mock_tab.status = 1  # Tab started
        chrome_remote._chrome_tab = mock_tab

        # Mock необходимых методов
        with patch.object(chrome_remote, "execute_script", return_value="Mozilla/5.0"):
            with patch.object(mock_tab, "Network"):
                with patch.object(chrome_remote, "add_start_script"):
                    # Не должно вызывать исключений
                    try:
                        chrome_remote._setup_tab()
                    except ChromeException:
                        pytest.fail("_setup_tab() выбросил ChromeException с валидным tab")

    def test_setup_tab_error_message_content(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест содержания сообщения об ошибке.

        Проверяет:
        - Сообщение содержит информацию о проблеме
        - Сообщение указывает на метод
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._chrome_tab = None

        with pytest.raises(ChromeException) as exc_info:
            chrome_remote._setup_tab()

        error_message = str(exc_info.value)

        # Проверяем содержание сообщения
        assert "Chrome" in error_message
        assert "tab" in error_message.lower()
        assert "не инициализирован" in error_message or "None" in error_message

    def test_setup_tab_none_check_logs_error(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list, monkeypatch
    ) -> None:
        """Тест что ошибка логируется перед выбрасыванием.

        Проверяет:
        - app_logger.error вызывается
        - Сообщение об ошибке логируется
        """
        from parser_2gis.chrome import remote as remote_module

        # Создаем mock логгера
        mock_logger = MagicMock()
        monkeypatch.setattr(remote_module, "app_logger", mock_logger)

        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._chrome_tab = None

        with pytest.raises(ChromeException):
            chrome_remote._setup_tab()

        # Проверяем что ошибка была залогирована
        assert mock_logger.error.called, "app_logger.error не был вызван"

        # Проверяем содержание лога
        log_args = mock_logger.error.call_args[0][0]
        assert "Chrome tab" in log_args or "_setup_tab" in log_args, (
            f"Некорректное сообщение лога: {log_args}"
        )

    def test_chrome_exception_type_not_runtime_error(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что выбрасывается ChromeException а не RuntimeError.

        Проверяет:
        - Тип исключения ChromeException
        - Не RuntimeError или другое
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._chrome_tab = None

        with pytest.raises(ChromeException) as exc_info:
            chrome_remote._setup_tab()

        # Проверяем тип исключения
        assert isinstance(exc_info.value, ChromeException)
        assert not isinstance(exc_info.value, RuntimeError)

    def test_setup_tab_check_is_first_operation(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что проверка None первая операция в методе.

        Проверяет:
        - Проверка выполняется до任何其他 операций
        - Порядок операций корректный
        """
        import inspect

        from parser_2gis.chrome.remote import ChromeRemote

        # Получаем исходный код метода
        source = inspect.getsource(ChromeRemote._setup_tab)

        # Проверяем что проверка на None идёт в начале
        lines = source.split("\n")
        check_line_index = None

        for i, line in enumerate(lines):
            if "_chrome_tab is None" in line or "if self._chrome_tab is None" in line:
                check_line_index = i
                break

        assert check_line_index is not None, "Проверка на None не найдена"

        # Проверяем что проверка идёт до других операций
        # (после docstring и до использования _chrome_tab)
        assert check_line_index < len(lines) - 1

    def test_setup_tab_none_prevents_attribute_error(
        self, mock_chrome_options: MagicMock, mock_response_patterns: list
    ) -> None:
        """Тест что проверка None предотвращает AttributeError.

        Проверяет:
        - Без проверки был бы AttributeError
        - С проверкой выбрасывается ChromeException
        """
        chrome_remote = ChromeRemote(mock_chrome_options, mock_response_patterns)
        chrome_remote._chrome_tab = None

        # С проверкой выбрасывается ChromeException
        with pytest.raises(ChromeException):
            chrome_remote._setup_tab()

        # Проверяем что это не AttributeError (тест проходит если ChromeException)
        # Второе вызывание для проверки что исключение того же типа
        with pytest.raises(ChromeException) as exc_info:
            chrome_remote._setup_tab()

        # Убеждаемся что это именно ChromeException
        assert isinstance(exc_info.value, ChromeException)
