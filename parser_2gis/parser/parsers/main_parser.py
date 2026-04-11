"""Основной парсер для поисковой выдачи 2GIS.

Предоставляет класс MainPageParser для операций с DOM и навигации:
- Навигация по URL с обработкой ошибок
- Получение и валидация DOM элементов
- Управление страницами и пагинацией
- Обработка запросов и ответов

Этот модуль выделен из main.py для разделения ответственности:
- MainPageParser: DOM операции и навигация
- MainDataExtractor: Извлечение данных
- MainDataProcessor: Обработка данных
"""

from __future__ import annotations

import os
import random
import re
import time
from typing import TYPE_CHECKING, Any

from parser_2gis.chrome.dom import DOMNode
from parser_2gis.logger import logger
from parser_2gis.parser.parsers.base import BaseParser, ParserStats
from parser_2gis.protocols import BrowserService
from parser_2gis.shared_config_constants import CATALOG_API_PATTERN
from parser_2gis.utils.decorators import wait_until_finished

if TYPE_CHECKING:
    from parser_2gis.chrome import ChromeOptions
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.writer import FileWriter

# =============================================================================
# КОНСТАНТЫ МОДУЛЯ
# =============================================================================

# Попытки и таймауты
MAX_RESPONSE_ATTEMPTS: int = (
    3  # Максимальное количество попыток получить ответ (достаточно для временных сбоев сети)
)
# Таймаут навигации можно переопределить через переменную окружения PARSER_NAVIGATION_TIMEOUT
NAVIGATION_TIMEOUT: int = int(
    os.environ.get("PARSER_NAVIGATION_TIMEOUT", "300")
)  # По умолчанию 5 минут
WAIT_REQUESTS_TIMEOUT: int = 60  # Таймаут ожидания завершения запросов (1 минута)
GET_LINKS_TIMEOUT: int = 30  # Таймаут получения ссылок (30 секунд)
GET_UNIQUE_LINKS_TIMEOUT: int = 30  # Таймаут получения уникальных ссылок (30 секунд)
MAX_RETRY_ATTEMPTS: int = 5  # Максимальное количество попыток получения ссылок
MAX_LINK_ATTEMPTS: int = 5  # Максимальное количество попыток получения ссылок
MAX_TOTAL_ITERATIONS: int = MAX_LINK_ATTEMPTS * 2 + 10  # Максимальное общее количество итераций

# Память и оптимизация
MAX_VISITED_LINKS_SIZE: int = 10000  # Максимальный размер множества посещённых ссылок

# Задержки
RESPONSE_RETRY_DELAY: float = 0.5  # Задержка между попытками получения ответа (сек)

# Типы для типизации
DOMNodeList = list["DOMNode"]


# =============================================================================
# ИСКЛЮЧЕНИЯ ДЛЯ НАВИГАЦИИ (ISSUE-147: Вынесены на уровень модуля)
# =============================================================================


class NavigationTimeoutError(Exception):
    """Ошибка таймаута навигации."""


class NavigationNetworkError(Exception):
    """Ошибка сети при навигации (502, 503, 504 и т.д.)."""


class NavigationBlockedError(Exception):
    """Ошибка блокировки (403, 429 и т.д.)."""


class NavigationGenericError(Exception):
    """Общая ошибка навигации."""


# =============================================================================
# СКОМПИЛИРОВАННЫЕ REGEX ПАТТЕРНЫ (ISSUE-144: Оптимизация)
# =============================================================================

# Паттерн для извлечения номера страницы из URL
_PAGE_NUMBER_PATTERN = re.compile(r".*/search/.*/page/(?P<page_number>\d+)")

# Паттерн для валидации ссылок firm/station
_LINK_VALIDATION_PATTERN = re.compile(r".*/(firm|station)/.*\?stat=(?P<data>[a-zA-Z0-9%]+)")


class MainPageParser(BaseParser):
    """Парсер для операций с DOM и навигации на поисковой выдаче 2GIS.

    Предоставляет функциональность для:
    - Навигации к поисковой выдаче с обработкой ошибок
    - Получения и валидации DOM элементов
    - Управления страницами и пагинацией
    - Обработки запросов и ответов

    Args:
        url: 2GIS URLs с элементами для сбора.
        chrome_options: Опции Chrome.
        parser_options: Опции парсера.
        browser: Опциональный объект BrowserService. Если не передан,
                 создаётся внутренний ChromeRemote (для backward совместимости).

    """

    def __init__(
        self,
        url: str,
        chrome_options: ChromeOptions,
        parser_options: ParserOptions,
        browser: BrowserService | None = None,
    ) -> None:
        """Инициализация парсера.

        Args:
            url: URL для парсинга.
            chrome_options: Опции Chrome.
            parser_options: Опции парсера.
            browser: Опциональный браузер. Если не передан, создаётся внутренний ChromeRemote.

        """
        # Если браузер не передан, создаём внутренний ChromeRemote
        self._owns_browser = browser is None
        if self._owns_browser:
            from parser_2gis.chrome.remote import ChromeRemote

            # Паттерн ответа "Catalog Item Document" - должен совпадать с _item_response_pattern
            response_patterns = [CATALOG_API_PATTERN]
            browser = ChromeRemote(chrome_options, response_patterns)

        # Mypy не может сузить тип после переназначения — используем assert
        assert browser is not None, "browser должен быть создан к этому моменту"
        # Инициализируем базовый класс только browser аргументом
        # BaseParser принимает только browser, остальные аргументы обрабатываются здесь
        super().__init__(browser)

        # Сохраняем опции для использования в дочернем классе
        self._chrome_options = chrome_options
        self._parser_options = parser_options
        self._url = url

        # Паттерн ответа "Catalog Item Document"
        self._item_response_pattern = CATALOG_API_PATTERN

        # Добавляем счётчик для 2GIS запросов
        self._add_xhr_counter()

        # Отключаем определённые запросы (будет вызвано в __enter__ после start())
        self._blocked_requests_added = False

    @staticmethod
    def url_pattern() -> str:
        """Возвращает URL-паттерн для основного парсера поисковой выдачи.

        Returns:
            Regex паттерн для匹配 URL поисковой выдачи 2GIS.

        """
        return r"https?://2gis\.[^/]+/[^/]+/search/.*"

    @wait_until_finished(timeout=GET_LINKS_TIMEOUT, throw_exception=False, poll_interval=0.01)
    def _get_links(self) -> DOMNodeList | None:
        """Извлекает определённые DOM-узлы ссылок из текущего снимка DOM.

        Returns:
            Список DOM-узлов ссылок или None при ошибке.

        Raises:
            TimeoutError: При таймауте получения ссылок.
            OSError: При ошибке доступа к DOM.
            RuntimeError: При ошибке выполнения операций Chrome.
            TypeError: При некорректном типе данных.
            ValueError: При некорректных параметрах.
            MemoryError: При нехватке памяти.

        Примечание:
            Функция валидирует каждую ссылку и декодирует base64 данные
            для проверки корректности.

        Обработка ошибок:
            - TimeoutError: Логируется предупреждение, возвращается None
            - Любые другие исключения: Логируются, возвращается None

        """

        def valid_link(node: DOMNode) -> bool:
            """Проверяет валидность ссылки.

            Args:
                node: DOM-узел для проверки.

            Returns:
                True если ссылка валидна, False иначе.

            """
            if node.local_name == "a" and "href" in node.attributes:
                href = node.attributes.get("href", "")
                if not href:
                    return False

                # ISSUE-144: Используем скомпилированный паттерн
                link_match = _LINK_VALIDATION_PATTERN.match(href)
                if link_match:
                    try:
                        # Декодируем base64 данные для проверки корректности
                        import urllib.parse

                        urllib.parse.unquote(link_match.group("data"))
                        return True
                    except (OSError, RuntimeError, TypeError, ValueError) as e:
                        # Ошибка декодирования - ссылка невалидна
                        logger.debug("Ошибка декодирования ссылки: %s", e)

            return False

        try:
            dom_tree = self._chrome_remote.get_document()
            # ISSUE-145: Валидация на None
            if dom_tree is None:
                logger.warning("DOM дерево не получено при получении ссылок")
                return None

            links = dom_tree.search(valid_link)
            # Возвращаем None если ссылки не найдены, иначе список ссылок
            return links or None

        except TimeoutError as timeout_error:
            # Явная обработка TimeoutError - возвращаем None вместо падения
            logger.warning(
                "Таймаут при получении ссылок (%d сек): %s. Возврат None.",
                GET_LINKS_TIMEOUT,
                timeout_error,
            )
            return None

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            logger.error("Ошибка при получении ссылок: %s", e)
            return None

    def _add_xhr_counter(self) -> None:
        """Внедряет обёртку вокруг XMLHttpRequest для отслеживания запросов.

        ISSUE-141: Добавлен docstring с описанием формата JavaScript.

        Формат JavaScript:
            - IIFE (Immediately Invoked Function Expression) для изоляции области видимости
            - try-catch блок для обработки ошибок
            - Сохраняет оригинальную XMLHttpRequest.prototype.open функцию
            - Переопределяет open для подсчёта запросов к 2gis домену
            - Увеличивает window.openHTTPs при каждом запросе
            - Уменьшает window.openHTTPs при завершении запроса (readyState == 4)
            - Логирует ошибки в console.error

        Raises:
            RuntimeError: При ошибке внедрения JavaScript скрипта.
            OSError: При ошибке доступа к Chrome Remote.

        """
        xhr_script = r"""
            (function() {
                try {
                    var oldOpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function(method, url, async, user, pass) {
                        if (url.match(/^https?\:\/\/[^\/]*2gis\.[a-z]+/i)) {
                            if (window.openHTTPs == undefined) {
                                window.openHTTPs = 1;
                            } else {
                                window.openHTTPs++;
                            }
                            this.addEventListener("readystatechange", function() {
                                if (this.readyState == 4) {
                                    window.openHTTPs--;
                                }
                            }, false);
                        }
                        oldOpen.call(this, method, url, async, user, pass);
                    };
                } catch (e) {
                    console.error('Ошибка при установке XHR счётчика:', e);
                }
            })();
        """
        # Проверяем что скрипт не содержит потенциально опасных паттернов
        if self._validate_js_script(xhr_script):
            self._chrome_remote.add_start_script(xhr_script)

    def _validate_js_script(self, script: str) -> bool:
        """Валидирует JavaScript код перед внедрением.

        Args:
            script: JavaScript код для проверки.

        Returns:
            True если скрипт безопасен, False иначе.

        """
        # Запрещённые паттерны в JavaScript
        dangerous_patterns = [
            r"document\.cookie",
            r"localStorage",
            r"sessionStorage",
            r"eval\s*\(",
            r"Function\s*\(",
            r"setTimeout\s*\(\s*['\"].*['\"]",
            r"setInterval\s*\(\s*['\"].*['\"]",
            r"innerHTML\s*=",
            r"outerHTML\s*=",
            r"insertAdjacentHTML",
            r"document\.write",
            r"window\.location",
            r"location\.href",
            r"XMLHttpRequest\.prototype\.setRequestHeader",
            # C010: Дополнительные опасные паттерны
            r"import\s*\(",
            r"fetch\s*\(",
            r"WebSocket",
            r"navigator\.(sendBeacon|beacon)",
            r"window\.open\s*\(",
            r"postMessage",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                logger.warning("Заблокирован потенциально опасный JavaScript паттерн: %s", pattern)
                return False

        return True

    @wait_until_finished(timeout=WAIT_REQUESTS_TIMEOUT, poll_interval=0.01)
    def _wait_requests_finished(self) -> bool:
        """Ждёт завершения всех ожидающих запросов."""
        return self._chrome_remote.execute_script("window.openHTTPs == 0")

    def _get_available_pages(self) -> dict[int, DOMNode]:
        """Получает доступные страницы для навигации.

        ISSUE-145: Добавлена валидация dom_tree на None.
        ISSUE-144: Оптимизация через использование скомпилированного regex паттерна.

        Returns:
            Словарь {номер_страницы: DOMNode} доступных страниц.

        Raises:
            OSError: При ошибке доступа к DOM.
            RuntimeError: При ошибке выполнения операций Chrome.
            TypeError: При некорректном типе данных.
            ValueError: При некорректных параметрах.
            MemoryError: При нехватке памяти.

        """
        try:
            dom_tree = self._chrome_remote.get_document()
            # ISSUE-145: Валидация на None
            if dom_tree is None:
                logger.warning("DOM дерево не получено - возвращаем пустой словарь")
                return {}

            dom_links = dom_tree.search(lambda x: x.local_name == "a" and "href" in x.attributes)

            available_pages: dict[int, DOMNode] = {}
            for link in dom_links:
                href = link.attributes.get("href", "")
                if not href:
                    continue

                # ISSUE-144: Используем скомпилированный паттерн
                link_match = _PAGE_NUMBER_PATTERN.match(href)
                if link_match:
                    page_number = int(link_match.group("page_number"))
                    available_pages[page_number] = link

            return available_pages
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            logger.error("Ошибка при получении доступных страниц: %s", e)
            return {}

    def _go_page(self, n_page: int) -> int | None:
        """Переходит на страницу с номером `n_page`.

        Note:
            `n_page` должна существовать в текущем DOM.
            В противном случае 2GIS anti-bot перенаправит вас на первую страницу.

        Args:
            n_page: Номер страницы для перехода.

        Returns:
            Номер страницы, на которую перешли, или None при ошибке.

        """
        try:
            available_pages = self._get_available_pages()
            if n_page in available_pages:
                self._chrome_remote.perform_click(available_pages[n_page])
                return n_page
            logger.warning("Страница %d недоступна для перехода", n_page)
            return None
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            logger.error("Ошибка при переходе на страницу %d: %s", n_page, e)
            return None

    def _navigate_to_search(self, url: str) -> bool:
        """Выполняет навигацию к поисковой выдаче с обработкой ошибок и повторными попытками.

        Args:
            url: URL для навигации.

        Returns:
            True если навигация успешна, False иначе.

        Raises:
            NavigationTimeoutError: При таймауте навигации.
            NavigationNetworkError: При ошибке сети (502, 503, 504).
            NavigationBlockedError: При блокировке (403, 429).
            NavigationGenericError: При общей ошибке навигации.

        Примечание:
            - Автоматический повторный парсинг при временных ошибках (502, 503, 504, TimeoutError)
            - Экспоненциальная задержка между попытками с jitter
            - Обработка HTTP статусов (404, 403, 5xx)
            - Создаёт отдельные исключения для разных типов ошибок навигации

        """
        # Переходим по URL с возможностью повторных попыток при ошибках сети
        for retry_attempt in range(self._parser_options.max_retries + 1):
            try:
                # Первая попытка или повторная
                if retry_attempt > 0:
                    logger.info(
                        "Повторная попытка навигации (%d/%d) для URL: %s",
                        retry_attempt,
                        self._parser_options.max_retries,
                        url,
                    )

                self._chrome_remote.navigate(
                    url, referer="https://google.com", timeout=NAVIGATION_TIMEOUT
                )
                # Если навигация успешна - выходим из цикла
                return True

            except TimeoutError as timeout_error:
                should_continue = self._handle_navigation_timeout(
                    url, timeout_error, retry_attempt, NavigationTimeoutError
                )
                if should_continue:
                    continue
                return False

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as navigate_error:
                should_continue = self._handle_navigation_error(url, navigate_error, retry_attempt)
                if should_continue:
                    continue
                return False

        return False

    def _handle_navigation_timeout(
        self,
        url: str,
        timeout_error: TimeoutError,
        retry_attempt: int,
        error_class: type[Exception],
    ) -> bool:
        """Обрабатывает таймаут навигации.

        Args:
            url: URL для навигации.
            timeout_error: Исключение таймаута.
            retry_attempt: Текущая попытка.
            error_class: Класс исключения для логирования.

        Returns:
            True если навигация успешна, False иначе.

        """
        if (
            retry_attempt < self._parser_options.max_retries
            and self._parser_options.retry_on_network_errors
        ):
            delay = self._calculate_retry_delay(retry_attempt)
            logger.warning(
                "[%s] Таймаут при навигации (попытка %d/%d): %s. "
                "Повторная попытка через %.1f сек...",
                error_class.__name__,
                retry_attempt + 1,
                self._parser_options.max_retries,
                timeout_error,
                delay,
            )
            time.sleep(delay)
            return True  # Продолжаем попытки
        logger.error(
            "[%s] Таймаут навигации по URL %s: %s", error_class.__name__, url, timeout_error
        )
        return False

    def _handle_navigation_error(
        self, url: str, navigate_error: Exception, retry_attempt: int
    ) -> bool:
        """Обрабатывает ошибки навигации.

        ISSUE-146: Упрощена вложенность через выделение методов.

        Args:
            url: URL для навигации.
            navigate_error: Исключение ошибки.
            retry_attempt: Текущая попытка.

        Returns:
            True если навигация успешна, False иначе.

        """
        error_msg = str(navigate_error).lower()
        error_classification = self._classify_error(error_msg)

        if error_classification == "blocked":
            logger.error(
                "[NavigationBlockedError] Доступ заблокирован при навигации по URL %s: %s",
                url,
                navigate_error,
            )
            return False

        if error_classification == "network":
            return self._handle_network_error(url, navigate_error, retry_attempt)

        # Общая ошибка - не подлежит повтору
        logger.error(
            "[NavigationGenericError] Общая ошибка навигации по URL %s: %s", url, navigate_error
        )
        return False

    def _classify_error(self, error_msg: str) -> str:
        """Классифицирует тип ошибки навигации.

        Объединяет логику проверки сетевых и блокирующих ошибок.

        Args:
            error_msg: Сообщение ошибки.

        Returns:
            Тип ошибки: "network", "blocked" или "generic".

        """
        # Проверяем блокирующие ошибки (приоритетнее сетевых)
        if any(code in error_msg for code in ("403", "429", "blocked", "forbidden")):
            return "blocked"
        # Проверяем сетевые ошибки
        if any(code in error_msg for code in ("502", "503", "504", "timeout")):
            return "network"
        return "generic"

    def _is_network_error(self, error_msg: str) -> bool:
        """Проверяет является ли ошибку сетевой.

        Args:
            error_msg: Сообщение ошибки.

        Returns:
            True если ошибка сетевая.

        """
        return self._classify_error(error_msg) == "network"

    def _is_blocked_error(self, error_msg: str) -> bool:
        """Проверяет является ли ошибку блокировкой.

        Args:
            error_msg: Сообщение ошибки.

        Returns:
            True если ошибка блокировкой.

        """
        return self._classify_error(error_msg) == "blocked"

    def _handle_network_error(
        self, url: str, navigate_error: Exception, retry_attempt: int
    ) -> bool:
        """Обрабатывает сетевую ошибку.

        Args:
            url: URL для навигации.
            navigate_error: Исключение ошибки.
            retry_attempt: Текущая попытка.

        Returns:
            True если навигация успешна, False иначе.

        """
        if (
            retry_attempt < self._parser_options.max_retries
            and self._parser_options.retry_on_network_errors
        ):
            delay = self._calculate_retry_delay(retry_attempt)
            logger.warning(
                "[NavigationNetworkError] Ошибка сети при навигации (попытка %d/%d): %s. "
                "Повторная попытка через %.1f сек...",
                retry_attempt + 1,
                self._parser_options.max_retries,
                navigate_error,
                delay,
            )
            time.sleep(delay)
            return True  # Продолжаем попытки
        logger.error(
            "[NavigationNetworkError] Исчерпаны все попытки для URL %s: %s", url, navigate_error
        )
        return False

    def _calculate_retry_delay(self, retry_attempt: int) -> float:
        """Вычисляет задержку перед повторной попыткой.

        Args:
            retry_attempt: Номер текущей попытки.

        Returns:
            Задержка в секундах.

        """
        base_delay = self._parser_options.retry_delay_base * (1.5**retry_attempt)
        jitter = random.uniform(0, 0.3)
        return base_delay + jitter

    def _validate_document_response(self) -> dict[str, Any] | None:
        """Получает и валидирует ответ документа после навигации.

        Returns:
            Валидированный ответ документа или None при ошибке.

        Примечание:
            - Проверяет MIME тип (должен быть text/html)
            - Обрабатывает HTTP статусы (404, 403, 5xx)
            - Учитывает настройки skip_404_response и stop_on_first_404

        """
        # Получаем ответы
        try:
            responses = self._chrome_remote.get_responses()
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            logger.error("Ошибка при получении ответов: %s", e)
            return None

        if not responses:
            logger.error("Ошибка получения ответа сервера.")
            return None

        # Безопасное получение первого ответа с проверкой
        try:
            document_response = responses[0]
        except (IndexError, KeyError):
            logger.error("Список ответов пуст или некорректен.")
            return None

        # Проверка наличия документа
        if not document_response:
            logger.error("Первый ответ пуст.")
            return None

        # Обработка MIME типа
        mime_type = document_response.get("mimeType", "")
        if mime_type != "text/html":
            logger.error("Неверный тип MIME ответа: %s", mime_type)
            return None

        # Улучшенная обработка HTTP статусов
        http_status = document_response.get("status", 0)

        if http_status == 404:
            logger.warning('Сервер вернул 404: "Точных совпадений нет / Не найдено".')
            if self._parser_options.skip_404_response:
                logger.info("Пропуск URL из-за 404 ответа (skip_404_response=True).")
                return None
            # Если включен режим немедленной остановки при первом 404 - завершаем парсинг
            if self._parser_options.stop_on_first_404:
                logger.info(
                    "Немедленная остановка парсинга при первом 404 (stop_on_first_404=True)."
                )
                return None

        elif http_status == 403:
            logger.error("Сервер вернул 403: Доступ запрещён. Возможна блокировка.")
            return None

        elif http_status in (500, 502, 503, 504):
            logger.error(
                "Сервер вернул ошибку %d: Временная проблема на стороне сервера.", http_status
            )
            return None

        elif http_status < 200 or http_status >= 400:
            logger.warning("Сервер вернул нестандартный статус: %d", http_status)

        return document_response

    def parse(self, writer: FileWriter) -> None:
        """Основной метод парсинга.

        MainPageParser является вспомогательным классом для MainParser,
        поэтому этот метод не используется напрямую.

        Args:
            writer: Объект FileWriter для записи данных.

        Raises:
            NotImplementedError: Метод не предназначен для прямого вызова.

        """
        raise NotImplementedError(
            "MainPageParser.parse() не предназначен для прямого вызова. "
            "Используйте MainParser.parse() вместо этого."
        )

    def get_stats(self) -> ParserStats:
        """Получение статистики парсера.

        Returns:
            Словарь со статистикой парсера.

        """
        return dict(self._stats)  # type: ignore[return-value]

    def __enter__(self) -> MainPageParser:
        """Контекстный менеджер: вход.

        Запускает браузер, если он был создан внутри парсера.

        Returns:
            Экземпляр MainPageParser.

        """
        if self._owns_browser:
            self._chrome_remote.start()

        # Добавляем заблокированные запросы после запуска браузера
        if not self._blocked_requests_added:
            from parser_2gis.parser.utils import blocked_requests

            blocked_urls = list(blocked_requests(extended=self._chrome_options.disable_images))
            self._chrome_remote.add_blocked_requests(blocked_urls)
            self._blocked_requests_added = True

        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Контекстный менеджер: выход.

        Закрывает браузер, если он был создан внутри парсера.

        Args:
            exc_info: Информация об исключении (если было).

        """
        self.close()

    def close(self) -> None:
        """Закрывает браузер и освобождает ресурсы.

        Закрывает только если браузер был создан внутри парсера
        (не был передан извне через browser параметр).
        """
        if self._owns_browser:
            self._chrome_remote.stop()
