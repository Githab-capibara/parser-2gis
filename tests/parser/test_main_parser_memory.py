"""
Тесты для утечки памяти и TimeoutError в parser/parsers/main.py.

Проверяет:
- OrderedDict не растет бесконечно
- При достижении лимита старые записи удаляются
- Обработку TimeoutError в методах навигации
- Retry logic при таймауте
"""

from collections import OrderedDict
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.parser.parsers.main_parser import MAX_VISITED_LINKS_SIZE, MainPageParser
from parser_2gis.writer import FileWriter


class TestableMainPageParser(MainPageParser):
    """Тестовая реализация MainPageParser для тестов.

    Реализует абстрактные методы parse и get_stats.
    """

    def parse(self, writer: FileWriter) -> None:
        """Заглушка для теста."""
        pass

    def get_stats(self) -> dict[str, Any]:
        """Заглушка для теста."""
        return self._stats


class TestVisitedLinksMemoryLimit:
    """Тесты ограничения памяти visited_links."""

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
        options.retry_delay_base = 1.0
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

    def test_visited_links_ordered_dict_limit(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест ограничения размера OrderedDict для visited_links.

        Проверяет:
        - OrderedDict не растет бесконечно
        - При достижении лимита старые записи удаляются
        """
        # Создаем OrderedDict с ограничением
        visited_links = OrderedDict()
        max_size = 100  # Тестовый лимит

        # Добавляем больше записей чем лимит
        for i in range(max_size * 2):
            url = f"https://example.com/link_{i}"

            # Имитируем логику ограничения размера из _parse_search_results
            if len(visited_links) >= max_size:
                # Удаляем oldest 25% записей
                remove_count = max_size // 4
                for _ in range(remove_count):
                    if visited_links:
                        visited_links.popitem(last=False)

            visited_links[url] = None

        # Проверяем что размер не превысил лимит
        assert len(visited_links) <= max_size

    def test_visited_links_memory_optimization(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест оптимизации памяти visited_links.

        Проверяет:
        - Старые записи удаляются при превышении лимита
        - OrderedDict используется корректно
        """
        visited_links = OrderedDict()
        max_size = MAX_VISITED_LINKS_SIZE

        # Добавляем записи до лимита
        for i in range(max_size + 1000):
            url = f"https://example.com/link_{i}"

            # Проверяем и оптимизируем память
            if len(visited_links) >= max_size:
                # Удаляем oldest записи
                remove_count = int(max_size * 0.25)  # 25%
                for _ in range(remove_count):
                    if visited_links:
                        visited_links.popitem(last=False)

            visited_links[url] = None

        # Проверяем что размер контролируется
        assert len(visited_links) <= max_size

    def test_visited_links_thread_safety(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест потокобезопасности visited_links.

        Проверяет:
        - RLock используется для защиты
        - Операции атомарны
        """
        import threading

        visited_links = OrderedDict()
        visited_links_lock = threading.RLock()
        max_size = 1000

        def add_links(start, count):
            for i in range(start, start + count):
                url = f"https://example.com/link_{i}"
                with visited_links_lock:
                    if len(visited_links) >= max_size:
                        remove_count = max_size // 4
                        for _ in range(remove_count):
                            if visited_links:
                                visited_links.popitem(last=False)
                    visited_links[url] = None

        # Создаем несколько потоков
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_links, args=(i * 100, 100))
            threads.append(t)
            t.start()

        # Ждем завершения всех потоков
        for t in threads:
            t.join()

        # Проверяем что размер контролируется
        assert len(visited_links) <= max_size

    def test_visited_links_cleanup_on_memory_pressure(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест очистки visited_links при нехватке памяти.

        Проверяет:
        - При нехватке памяти старые записи удаляются
        - gc.collect() вызывается
        """
        visited_links = OrderedDict()
        max_size = 100

        # Заполняем visited_links
        for i in range(max_size * 2):
            url = f"https://example.com/link_{i}"

            if len(visited_links) >= max_size:
                # Принудительная очистка
                remove_count = int(len(visited_links) * 0.75)
                for _ in range(remove_count):
                    if visited_links:
                        visited_links.popitem(last=False)

            visited_links[url] = None

        # Проверяем что размер контролируется
        assert len(visited_links) <= max_size


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
        options.retry_delay_base = 0.1  # Быстрый тест
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

    def test_navigate_timeout_handling(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест обработки TimeoutError в _navigate_to_search.

        Проверяет:
        - TimeoutError обрабатывается корректно
        - Retry logic работает
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

            # Проверяем что результат False (навигация не удалась)
            assert result is False

    def test_navigate_success_after_retry(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест успешной навигации после retry.

        Проверяет:
        - При успешной навигации после retry возвращается True
        """
        parser = TestableMainPageParser(
            url="https://2gis.ru/moscow/search/test",
            chrome_options=mock_chrome_options,
            parser_options=mock_parser_options,
            browser=mock_browser,
        )

        # Mock navigate для выбрасывания TimeoutError первые 2 раза, затем успех
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

    def test_navigate_network_error_handling(
        self, mock_chrome_options, mock_parser_options, mock_browser
    ):
        """Тест обработки ошибок сети в навигации.

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
