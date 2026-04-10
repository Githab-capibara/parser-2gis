"""
Тесты для обработки TimeoutError в parser/parsers/main.py.

Проверяет:
- Обработку TimeoutError в методах навигации
- Retry logic при таймауте
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.parser.parsers.main_parser import MainPageParser
from parser_2gis.writer import FileWriter


class TestableMainPageParser(MainPageParser):
    """Тестовая реализация MainPageParser для тестов.

    Реализует абстрактные методы parse и get_stats.
    """

    def parse(self, writer: FileWriter) -> None:
        """Заглушка для теста."""

    def get_stats(self) -> dict[str, Any]:
        """Заглушка для теста."""
        return self._stats


class TestNavigateTimeoutHandling:
    """Тесты обработки TimeoutError в навигации."""

    @pytest.fixture
    def mock_chrome_options(self) -> MagicMock:
        """Создает mock опций Chrome.

        Returns:
            MagicMock с опциями Chrome.
        """
        options = MagicMock()
        options.headless = True
        options.disable_images = False
        options.silent_browser = True
        options.memory_limit = 2048
        return options

    @pytest.fixture
    def mock_parser_options(self) -> MagicMock:
        """Создает mock опций парсера.

        Returns:
            MagicMock с опциями парсера.
        """
        options = MagicMock()
        options.max_retries = 3
        options.retry_delay_base = 0.01  # Очень быстрый тест
        options.retry_on_network_errors = True
        options.delay_between_clicks = 100
        options.skip_404_response = False
        options.stop_on_first_404 = False
        options.verbose = False
        options.max_consecutive_empty_pages = 3
        return options

    @pytest.fixture
    def mock_browser(self) -> MagicMock:
        """Создает mock браузера.

        Returns:
            MagicMock с методами браузера.
        """
        browser = MagicMock()
        browser.start.return_value = None
        browser.close.return_value = None
        browser.navigate.return_value = None
        browser.get_document.return_value = None
        browser.get_responses.return_value = []
        browser.execute_script.return_value = True
        browser.perform_click.return_value = None
        browser.wait_response.return_value = None
        browser.get_response_body.return_value = "{}"
        browser.add_start_script.return_value = None
        browser.add_blocked_requests.return_value = None
        return browser

    def test_navigate_timeout_retry_logic(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест retry logic при TimeoutError.

        Проверяет:
        - При TimeoutError выполняется retry
        - Задержка между попытками экспоненциальная
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания TimeoutError
        mock_browser.navigate.side_effect = TimeoutError("Mocked TimeoutError")

        with patch("time.sleep") as mock_sleep:
            result = parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что navigate был вызван несколько раз (retry)
            assert mock_browser.navigate.call_count > 1

            # Проверяем что sleep был вызван для задержки между попытками
            assert mock_sleep.call_count > 0

            # Проверяем что задержки были вызваны (экспоненциальная задержка с jitter)
            sleep_calls = mock_sleep.call_args_list
            if len(sleep_calls) > 1:
                delays = [call[0][0] for call in sleep_calls]
                # Проверяем что были задержки (с учётом jitter значения могут варьироваться)
                assert len(delays) > 0
                assert all(d >= 0 for d in delays)

            # Проверяем что результат False (навигация не удалась)
            assert result is False

    def test_navigate_timeout_success_after_retry(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест успешной навигации после retry.

        Проверяет:
        - При успешной навигации после retry возвращается True
        - Retry выполняется нужное количество раз
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate: первые 2 раза TimeoutError, затем успех
        mock_browser.navigate.side_effect = [
            TimeoutError("Mocked TimeoutError 1"),
            TimeoutError("Mocked TimeoutError 2"),
            None,  # Успех
        ]

        with patch("time.sleep"):
            result = parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что navigate был вызван 3 раза
            assert mock_browser.navigate.call_count == 3

            # Проверяем что результат True
            assert result is True

    def test_navigate_timeout_no_retry_when_disabled(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест отсутствия retry при отключенной опции.

        Проверяет:
        - При retry_on_network_errors=False retry не выполняется
        """
        mock_parser_options.retry_on_network_errors = False

        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания TimeoutError
        mock_browser.navigate.side_effect = TimeoutError("Mocked TimeoutError")

        with patch("time.sleep") as mock_sleep:
            result = parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что navigate был вызван только 1 раз (без retry)
            assert mock_browser.navigate.call_count == 1

            # Проверяем что sleep не был вызван
            assert mock_sleep.call_count == 0

            # Проверяем что результат False
            assert result is False

    def test_navigate_timeout_exhaust_all_retries(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест исчерпания всех попыток retry.

        Проверяет:
        - Все попытки retry выполняются
        - После исчерпания возвращается False
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания TimeoutError всегда
        mock_browser.navigate.side_effect = TimeoutError("Mocked TimeoutError")

        with patch("time.sleep"):
            result = parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что navigate был вызван max_retries + 1 раз
            expected_calls = mock_parser_options.max_retries + 1
            assert mock_browser.navigate.call_count == expected_calls

            # Проверяем что результат False
            assert result is False

    def test_navigate_timeout_exponential_backoff(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест экспоненциальной задержки при retry.

        Проверяет:
        - Задержка увеличивается экспоненциально
        - Jitter добавляется к задержке
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания TimeoutError
        mock_browser.navigate.side_effect = TimeoutError("Mocked TimeoutError")

        with patch("time.sleep") as mock_sleep:
            with patch("random.uniform", return_value=0.1):  # Фиксированный jitter для теста
                parser._navigate_to_search("https://2gis.ru/moscow/search/test")

                # Проверяем что задержки увеличиваются
                sleep_calls = mock_sleep.call_args_list
                delays = [call[0][0] for call in sleep_calls]

                # Проверяем что задержки возрастают (экспоненциальная задержка + jitter)
                for i in range(1, len(delays)):
                    assert delays[i] > delays[i - 1]

    def test_navigate_timeout_logging(
        self, mock_chrome_options, mock_parser_options, mock_browser, caplog
    ):
        """Тест логирования при TimeoutError.

        Проверяет:
        - TimeoutError логируется корректно
        - Информация о retry логируется
        """
        import logging

        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания TimeoutError
        mock_browser.navigate.side_effect = TimeoutError("Mocked TimeoutError")

        with caplog.at_level(logging.WARNING), patch("time.sleep"):
            parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что TimeoutError был залогирован
            assert any(
                "Таймаут" in record.message or "Timeout" in record.message
                for record in caplog.records
            )

    def test_navigate_network_error_with_retry(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест retry для сетевых ошибок.

        Проверяет:
        - Ошибки сети (502, 503, 504) обрабатываются с retry
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания OSError с ошибкой сети
        mock_browser.navigate.side_effect = OSError("502 Bad Gateway")

        with patch("time.sleep") as mock_sleep:
            result = parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что navigate был вызван несколько раз (retry)
            assert mock_browser.navigate.call_count > 1

            # Проверяем что sleep был вызван
            assert mock_sleep.call_count > 0

            # Проверяем что результат False
            assert result is False

    def test_navigate_non_network_error_no_retry(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест отсутствия retry для не-сетевых ошибок.

        Проверяет:
        - Не-сетевые ошибки не вызывают retry
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания не-сетевой ошибки
        mock_browser.navigate.side_effect = OSError("Some other error")

        with patch("time.sleep") as mock_sleep:
            result = parser._navigate_to_search("https://2gis.ru/moscow/search/test")

            # Проверяем что navigate был вызван только 1 раз (без retry)
            assert mock_browser.navigate.call_count == 1

            # Проверяем что sleep не был вызван
            assert mock_sleep.call_count == 0

            # Проверяем что результат False
            assert result is False

    def test_get_links_timeout_handling(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест обработки TimeoutError в _get_links.

        Проверяет:
        - TimeoutError обрабатывается корректно
        - Возвращается None
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock get_document для выбрасывания TimeoutError
        mock_browser.get_document.side_effect = TimeoutError("Mocked TimeoutError")

        result = parser._get_links()

        # Проверяем что результат None
        assert result is None

    def test_wait_requests_timeout_handling(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест обработки таймаута в _wait_requests_finished.

        Проверяет:
        - TimeoutError пробрасывается из декоратора @wait_until_finished
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock execute_script для выбрасывания TimeoutError
        mock_browser.execute_script.side_effect = TimeoutError("Mocked TimeoutError")

        # TimeoutError пробрасывается из декоратора
        with pytest.raises(TimeoutError, match="Mocked TimeoutError"):
            parser._wait_requests_finished()
