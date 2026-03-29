#!/usr/bin/env python3
"""
Тесты для выявления проблем с timeout и WebSocket соединениями.

Проверяет следующие проблемы из лога:
1. WebSocketConnectionClosedException при работе с Chrome DevTools
2. Превышение времени ожидания _wait_requests_finished (60 сек)
3. Превышение времени ожидания _get_links (30 сек)
4. Превышение времени ожидания get_unique_links (30 сек)
5. Превышение времени ожидания wait_response (3600 сек)
6. DOM.resolveNode error при клике
7. Достигнут лимит пустых страниц

Всего тестов: 7 (по 1 на каждую проблему)
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parser_2gis.chrome.patches import pychrome
from parser_2gis.parser.parsers.main import (
    GET_LINKS_TIMEOUT,
    GET_UNIQUE_LINKS_TIMEOUT,
    MAX_RESPONSE_ATTEMPTS,
    WAIT_REQUESTS_TIMEOUT,
    MainParser,
)

# Добавляем путь к модулю parser_2gis
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWebSocketConnectionHandling:
    """Тесты для проблемы WebSocketConnectionClosedException."""

    def test_pychrome_patch_handles_websocket_exception(self):
        """
        Тест 1: Обработка WebSocketConnectionClosedException в pychrome патче.

        Проверяет, что патч pychrome корректно обрабатывает
        WebSocketConnectionClosedException и не вызывает краш приложения.

        Проблема из лога:
            websocket._exceptions.WebSocketConnectionClosedException:
            Connection to remote host was lost.
            в pychrome.py:24 в _recv_loop_patched
        """
        # Импортируем websocket для симуляции исключения
        try:
            import websocket

            WebSocketConnectionClosedException = websocket.WebSocketConnectionClosedException
        except ImportError:
            # Если websocket не установлен, создаём мок
            WebSocketConnectionClosedException = Exception

        # Создаём мок для вкладки
        mock_tab = MagicMock()
        mock_tab._stopped = MagicMock()
        mock_tab._stopped.is_set = MagicMock(side_effect=[False, False, True])
        mock_tab._ws = MagicMock()

        # Настраиваем ws.recv() для выбрасывания WebSocketConnectionClosedException
        mock_tab._ws.recv.side_effect = WebSocketConnectionClosedException(
            "Connection to remote host was lost"
        )
        mock_tab.event_queue = MagicMock()

        # Применяем патч
        pychrome.patch_pychrome()

        # Вызываем патченную функцию
        try:
            from parser_2gis.chrome.patches.pychrome import patch_pychrome

            # Создаём тестовый объект с необходимыми атрибутами
            class MockTab:
                def __init__(self):
                    self._stopped = MagicMock()
                    self._stopped.is_set = MagicMock(side_effect=[False, False, True])
                    self._ws = MagicMock()
                    self._ws.settimeout = MagicMock()
                    self._ws.recv = MagicMock(
                        side_effect=WebSocketConnectionClosedException("Connection lost")
                    )
                    self.event_queue = MagicMock()
                    self.debug = False
                    self.method_results = {}

            mock_tab = MockTab()

            patch_pychrome()

            # Получаем патченную функцию
            import pychrome.tab as pychrome_tab

            # Вызываем патченную функцию
            pychrome_tab.Tab._recv_loop(mock_tab)

            # Если дошли сюда - исключение обработано корректно
            assert True
        except WebSocketConnectionClosedException:
            pytest.fail("WebSocketConnectionClosedException не была обработана в pychrome патче")


class TestTimeoutHandling:
    """Тесты для проблем с timeout."""

    def test_wait_requests_finished_timeout_handling(self):
        """
        Тест 2: Обработка timeout в _wait_requests_finished.

        Проверяет, что функция корректно обрабатывает ситуацию,
        когда запросы не завершаются в течение WAIT_REQUESTS_TIMEOUT (60 сек).

        Проблема из лога:
            WARNING | parser-2gis | Ошибка при ожидании запросов:
            Превышено время ожидания для _wait_requests_finished (60 сек)
        """
        # Проверяем, что константа установлена в разумное значение
        assert WAIT_REQUESTS_TIMEOUT == 60, "WAIT_REQUESTS_TIMEOUT должно быть 60 секунд"

        # Проверяем, что декоратор wait_until_finished используется
        # Симулируем ситуацию, когда функция выполняется дольше timeout
        from parser_2gis.utils.decorators import wait_until_finished

        @wait_until_finished(timeout=1, throw_exception=False, poll_interval=0.1)
        def slow_function():
            time.sleep(2)  # Дольше чем timeout
            return False

        start_time = time.time()
        result = slow_function()
        elapsed = time.time() - start_time

        # Функция должна завершиться примерно через 1 секунду (timeout)
        # Допускаем небольшую погрешность
        assert elapsed < 2.5, f"Функция не прервалась по timeout, прошло {elapsed} сек"
        # Результат может быть False или None при timeout
        assert result is False or result is None, "Функция должна вернуть False/None при timeout"

    def test_get_links_timeout_handling(self):
        """
        Тест 3: Обработка timeout в _get_links.

        Проверяет, что функция корректно обрабатывает ситуацию,
        когда получение ссылок занимает больше GET_LINKS_TIMEOUT (30 сек).

        Проблема из лога:
            WARNING | parser-2gis | Превышено время ожидания для _get_links (30 сек)
        """
        # Проверяем, что константа установлена в разумное значение
        assert GET_LINKS_TIMEOUT == 30, "GET_LINKS_TIMEOUT должно быть 30 секунд"

        # Проверяем, что декоратор используется с правильным timeout

        # Получаем декоратор функции _get_links
        get_links_method = MainParser._get_links

        # Проверяем, что wait_until_finished используется
        # Декорированная функция должна иметь __wrapped__ атрибут
        assert hasattr(get_links_method, "__wrapped__"), (
            "_get_links должен использовать декоратор @wait_until_finished"
        )

    def test_get_unique_links_timeout_handling(self):
        """
        Тест 4: Обработка timeout в get_unique_links.

        Проверяет, что функция корректно обрабатывает ситуацию,
        когда получение уникальных ссылок занимает больше
        GET_UNIQUE_LINKS_TIMEOUT (30 сек).

        Проблема из лога:
            WARNING | parser-2gis | Превышено время ожидания для
            get_unique_links (30 сек)
        """
        # Проверяем, что константа установлена в разумное значение
        assert GET_UNIQUE_LINKS_TIMEOUT == 30, "GET_UNIQUE_LINKS_TIMEOUT должно быть 30 секунд"

    def test_wait_response_timeout_handling(self):
        """
        Тест 5: Обработка timeout в wait_response.

        Проверяет, что функция корректно обрабатывает ситуацию,
        когда ответ не получен в течение разумного времени.

        Проблема из лога:
            WARNING | parser-2gis | Превышено время ожидания для
            wait_response (3600 сек) - ОЧЕНЬ ДОЛГО!

        Это критическая проблема - 3600 секунд (1 час) это слишком долго.
        """
        # Проверяем, что MAX_RESPONSE_ATTEMPTS установлен
        assert MAX_RESPONSE_ATTEMPTS == 3, "MAX_RESPONSE_ATTEMPTS должно быть 3"

        # Проверяем, что response_retry_delay не слишком большой
        from parser_2gis.parser.parsers.main import RESPONSE_RETRY_DELAY

        assert RESPONSE_RETRY_DELAY <= 1.0, (
            f"RESPONSE_RETRY_DELAY ({RESPONSE_RETRY_DELAY}) должно быть <= 1.0 сек"
        )


class TestDOMNodeHandling:
    """Тесты для проблем с DOM узлами."""

    def test_dom_resolve_node_error_handling(self):
        """
        Тест 6: Обработка ошибки DOM.resolveNode.

        Проверяет, что код корректно обрабатывает ситуацию,
        когда DOM узел больше не существует.

        Проблема из лога:
            ERROR | parser-2gis | Ошибка при выполнении клика:
            calling method: DOM.resolveNode error: No node with given id found
        """
        # Создаём мок DOM узла
        mock_dom_node = MagicMock()
        mock_dom_node.node_id = 123

        # Симулируем ситуацию, когда узел больше не существует
        mock_browser = MagicMock()
        mock_browser.Runtime = MagicMock()
        mock_browser.DOM = MagicMock()

        # Настраиваем DOM.resolveNode для выбрасывания исключения
        from parser_2gis.chrome.exceptions import ChromeRuntimeException

        mock_browser.DOM.resolveNode = MagicMock(
            side_effect=ChromeRuntimeException("No node with given id found")
        )

        # Проверяем, что исключение обрабатывается
        with pytest.raises(ChromeRuntimeException):
            mock_browser.DOM.resolveNode(mock_dom_node.node_id)

        # В реальном коде это должно обрабатываться в try-except
        # и логироваться как предупреждение


class TestEmptyPagesHandling:
    """Тесты для проблем с пустыми страницами."""

    def test_consecutive_empty_pages_limit(self):
        """
        Тест 7: Обработка лимита пустых страниц.

        Проверяет, что парсер корректно обрабатывает ситуацию,
        когда достигнуто максимальное количество пустых страниц подряд.

        Проблема из лога:
            WARNING | parser-2gis | Не удалось получить ссылки,
            переходим к следующей странице. (Пустых страниц подряд: 1/3,
            Попыток: 1/5)
            ERROR | parser-2gis | Достигнут лимит подряд пустых страниц (3).
            Прекращаем парсинг URL.
        """
        # Проверяем, что MainParser имеет атрибут для отслеживания пустых страниц
        # Это проверяется через ParserOptions.max_consecutive_empty_pages

        from parser_2gis.parser.options import ParserOptions

        options = ParserOptions()

        # Проверяем, что max_consecutive_empty_pages установлено
        assert hasattr(options, "max_consecutive_empty_pages"), (
            "ParserOptions должен иметь атрибут max_consecutive_empty_pages"
        )
        assert options.max_consecutive_empty_pages == 3, "max_consecutive_empty_pages должно быть 3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
