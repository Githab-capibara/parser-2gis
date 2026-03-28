"""Основной парсер для поисковой выдачи 2GIS.

Предоставляет класс MainParser для парсинга поисковых результатов:
- Переход по страницам выдачи
- Извлечение ссылок на организации
- Парсинг данных через API Catalog Item
- Поддержка пагинации
- Оптимизация памяти и GC
"""

from __future__ import annotations

import gc
import json
import random
import re
import threading
import time
import urllib.parse
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    PSUTIL_AVAILABLE = False

from parser_2gis.chrome import ChromeRemote
from parser_2gis.chrome.dom import DOMNode
from parser_2gis.logger import logger
from parser_2gis.parser.utils import blocked_requests
from parser_2gis.protocols import BrowserService
from parser_2gis.utils.decorators import wait_until_finished

if TYPE_CHECKING:
    from parser_2gis.chrome import ChromeOptions
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.writer import FileWriter

# =============================================================================
# КОНСТАНТЫ МОДУЛЯ ДЛЯ МАГИЧЕСКИХ ЧИСЕЛ
# =============================================================================

# Попытки и таймауты
MAX_RESPONSE_ATTEMPTS: int = 3  # Максимальное количество попыток получить ответ
NAVIGATION_TIMEOUT: int = 45  # Таймаут навигации в секундах (уменьшен для ускорения)
WAIT_REQUESTS_TIMEOUT: int = 15  # Таймаут ожидания завершения запросов (уменьшен для ускорения)
GET_LINKS_TIMEOUT: int = 3  # Таймаут получения ссылок (уменьшен для ускорения)
GET_UNIQUE_LINKS_TIMEOUT: int = 5  # Таймаут получения уникальных ссылок (уменьшен для ускорения)
MAX_RETRY_ATTEMPTS: int = 5  # Максимальное количество попыток получения ссылок
MAX_LINK_ATTEMPTS: int = 5  # Максимальное количество попыток получения ссылок

# Память и оптимизация
MAX_VISITED_LINKS_SIZE: int = 10000  # Максимальный размер множества посещённых ссылок
MEMORY_KEEP_RATIO: float = 0.25  # Доля памяти для сохранения при оптимизации (25%)
MEMORY_REMOVE_RATIO: float = 0.75  # Доля памяти для удаления при оптимизации (75%)

# Задержки
RESPONSE_RETRY_DELAY: float = (
    0.05  # Задержка между попытками получения ответа (сек) — ускорено для интенсивного парсинга
)

# MAX_CONSECUTIVE_EMPTY_PAGES теперь задается через ParserOptions.max_consecutive_empty_pages (по умолчанию 3)

# Типы для типизации
DOMNodeList = List["DOMNode"]


class MainParser:
    """Основной парсер, который извлекает полезные данные
    со страниц поисковой выдачи с помощью браузера Chrome
    и сохраняет их в файлы `csv`, `xlsx` или `json`.

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
        browser: Optional[BrowserService] = None,
    ) -> None:
        self._options = parser_options
        self._url = url

        # Паттерн ответа "Catalog Item Document"
        self._item_response_pattern = r"https://catalog\.api\.2gis.[^/]+/.*/items/byid"

        # Используем переданный браузер или создаём новый ChromeRemote
        if browser is not None:
            # Используем внешнюю абстракцию BrowserService
            self._browser = browser
            self._chrome_remote = browser  # Для backward совместимости
            self._owns_browser = False
        else:
            # Создаём внутренний ChromeRemote (старое поведение)
            response_patterns = [self._item_response_pattern]
            self._chrome_remote = ChromeRemote(
                chrome_options=chrome_options, response_patterns=response_patterns
            )
            self._chrome_remote.start()
            self._browser = self._chrome_remote
            self._owns_browser = True

        # Добавляем счётчик для 2GIS запросов
        self._add_xhr_counter()

        # Отключаем определённые запросы
        blocked_urls = blocked_requests(extended=chrome_options.disable_images)
        self._chrome_remote.add_blocked_requests(blocked_urls)

    @staticmethod
    def url_pattern():
        """URL-паттерн для парсера."""
        return r"https?://2gis\.[^/]+/[^/]+/search/.*"

    @wait_until_finished(timeout=GET_LINKS_TIMEOUT, throw_exception=False, poll_interval=0.05)
    def _get_links(self) -> Optional[DOMNodeList]:
        """Извлекает определённые DOM-узлы ссылок из текущего снимка DOM.

        Returns:
            Список DOM-узлов ссылок или None при ошибке.

        Примечание:
            Функция валидирует каждую ссылку и декодирует base64 данные
            для проверки корректности.

        Обработка ошибок:
            - TimeoutError: Логируется предупреждение, возвращается None
            - Любые другие исключения: Логируются, возвращается None
        """

        def valid_link(node: "DOMNode") -> bool:
            """Проверяет валидность ссылки."""
            if node.local_name == "a" and "href" in node.attributes:
                href = node.attributes.get("href", "")
                if not href:
                    return False

                link_match = re.match(r".*/(firm|station)/.*\?stat=(?P<data>[a-zA-Z0-9%]+)", href)
                if link_match:
                    try:
                        # Декодируем base64 данные для проверки корректности
                        urllib.parse.unquote(link_match.group("data"))
                        return True
                    except (OSError, RuntimeError, TypeError, ValueError) as e:
                        # Ошибка декодирования - ссылка невалидна
                        logger.debug("Ошибка декодирования ссылки: %s", e)

            return False

        try:
            dom_tree = self._chrome_remote.get_document()
            links = dom_tree.search(valid_link)
            # Возвращаем None если ссылки не найдены, иначе список ссылок
            return links if links else None

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
        """Внедряет old-school обёртку вокруг XMLHttpRequest
        для отслеживания всех ожидающих запросов к сайту 2GIS."""
        xhr_script = r"""
            (function() {
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
                }
            })();
        """
        self._chrome_remote.add_start_script(xhr_script)

    @wait_until_finished(timeout=WAIT_REQUESTS_TIMEOUT, poll_interval=0.05)
    def _wait_requests_finished(self) -> bool:
        """Ждёт завершения всех ожидающих запросов."""
        return self._chrome_remote.execute_script("window.openHTTPs == 0")

    def _get_available_pages(self) -> Dict[int, "DOMNode"]:
        """Получает доступные страницы для навигации.

        Returns:
            Словарь {номер_страницы: DOMNode} доступных страниц.
        """
        try:
            dom_tree = self._chrome_remote.get_document()
            dom_links = dom_tree.search(lambda x: x.local_name == "a" and "href" in x.attributes)

            available_pages: Dict[int, "DOMNode"] = {}
            for link in dom_links:
                href = link.attributes.get("href", "")
                if not href:
                    continue

                link_match = re.match(r".*/search/.*/page/(?P<page_number>\d+)", href)
                if link_match:
                    page_number = int(link_match.group("page_number"))
                    available_pages[page_number] = link

            return available_pages
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            logger.error("Ошибка при получении доступных страниц: %s", e)
            return {}

    def _go_page(self, n_page: int) -> Optional[int]:
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
            else:
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

        Примечание:
            - Автоматический повторный парсинг при временных ошибках (502, 503, 504, TimeoutError)
            - Экспоненциальная задержка между попытками с jitter
            - Обработка HTTP статусов (404, 403, 5xx)
        """
        # Переходим по URL с возможностью повторных попыток при ошибках сети
        for retry_attempt in range(self._options.max_retries + 1):
            try:
                # Первая попытка или повторная
                if retry_attempt > 0:
                    logger.info(
                        "Повторная попытка навигации (%d/%d) для URL: %s",
                        retry_attempt,
                        self._options.max_retries,
                        url,
                    )

                self._chrome_remote.navigate(
                    url, referer="https://google.com", timeout=NAVIGATION_TIMEOUT
                )
                # Если навигация успешна - выходим из цикла
                return True

            except TimeoutError as timeout_error:
                # Явная обработка TimeoutError с retry logic
                if (
                    retry_attempt < self._options.max_retries
                    and self._options.retry_on_network_errors
                ):
                    # Формула: base_delay * (2 ** retry) + random.uniform(0, 1)
                    base_delay = self._options.retry_delay_base * (2**retry_attempt)
                    jitter = random.uniform(0, 1)
                    delay = base_delay + jitter
                    logger.warning(
                        "Таймаут при навигации (попытка %d/%d): %s. "
                        "Повторная попытка через %.1f сек...",
                        retry_attempt + 1,
                        self._options.max_retries,
                        timeout_error,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    # Исчерпаны все попытки
                    logger.error("Таймаут навигации по URL %s: %s", url, timeout_error)
                    return False

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as navigate_error:
                error_msg = str(navigate_error).lower()
                is_network_error = (
                    "502" in error_msg
                    or "503" in error_msg
                    or "504" in error_msg
                    or "timeout" in error_msg
                )

                if (
                    retry_attempt < self._options.max_retries
                    and self._options.retry_on_network_errors
                    and is_network_error
                ):
                    # Формула: base_delay * (2 ** retry) + random.uniform(0, 1)
                    base_delay = self._options.retry_delay_base * (2**retry_attempt)
                    jitter = random.uniform(0, 1)
                    delay = base_delay + jitter
                    logger.warning(
                        "Ошибка сети при навигации (попытка %d/%d): %s. "
                        "Повторная попытка через %.1f сек...",
                        retry_attempt + 1,
                        self._options.max_retries,
                        navigate_error,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    # Либо это не ошибка сети, либо исчерпаны все попытки
                    logger.error("Ошибка навигации по URL %s: %s", url, navigate_error)
                    return False

        return False

    def _validate_document_response(self) -> Optional[Dict[str, Any]]:
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
            if self._options.skip_404_response:
                logger.info("Пропуск URL из-за 404 ответа (skip_404_response=True).")
                return None
            # Если включен режим немедленной остановки при первом 404 - завершаем парсинг
            if self._options.stop_on_first_404:
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

    def _parse_firm_page(self, link: "DOMNode", writer: FileWriter) -> bool:
        """Парсит страницу организации по ссылке.

        Args:
            link: DOM-узел ссылки на организацию.
            writer: Файловый писатель для сохранения данных.

        Returns:
            True если данные успешно записаны, False иначе.

        Примечание:
            - Кликает на ссылку для получения API запроса
            - Ожидает ответ Catalog Item Document
            - Парсит JSON и записывает в writer
            - Обрабатывает до MAX_RESPONSE_ATTEMPTS попыток
        """
        resp: Optional[Dict[str, Any]] = None

        for attempt in range(MAX_RESPONSE_ATTEMPTS):
            try:
                # Кликаем на ссылку, чтобы спровоцировать запрос
                # с ключом авторизации и секретными аргументами
                self._chrome_remote.perform_click(link)

                # Задержка между кликами, может быть полезна, если
                # anti-bot сервис 2GIS станет более строгим.
                if self._options.delay_between_clicks:
                    self._chrome_remote.wait(self._options.delay_between_clicks / 1000)

                # Собираем ответы и собираем полезные данные.
                resp = self._chrome_remote.wait_response(self._item_response_pattern)

                # Если запрос не удался - повторяем, иначе идём дальше.
                if resp and resp.get("status", -1) >= 0:
                    break

                # Добавляем небольшую задержку между попытками для снижения нагрузки
                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                    self._chrome_remote.wait(RESPONSE_RETRY_DELAY)

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as click_error:
                logger.warning(
                    "Ошибка при клике на ссылку (попытка %d): %s", attempt + 1, click_error
                )
                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                    self._chrome_remote.wait(RESPONSE_RETRY_DELAY)

        # Пропускаем позицию, если все попытки получить ответ неудачны
        if not resp or resp.get("status", -1) < 0:
            logger.error(
                "Не удалось получить ответ после %d попыток, пропуск позиции.",
                MAX_RESPONSE_ATTEMPTS,
            )
            return False

        # Получаем данные тела ответа
        try:
            data = self._chrome_remote.get_response_body(resp)
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as body_error:
            logger.error("Ошибка при получении тела ответа: %s", body_error)
            return False

        # Парсим JSON
        doc: Optional[Dict[str, Any]] = None
        try:
            doc = json.loads(data) if data else None
        except json.JSONDecodeError as json_error:
            logger.error(
                'Сервер вернул некорректный JSON документ: "%s...", ошибка: %s',
                data[:100] if data else "",
                json_error,
            )
            return False

        if doc:
            # Записываем API документ в файл
            try:
                writer.write(doc)
                return True
            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as write_error:
                logger.error("Ошибка записи данных: %s", write_error)
                return False
        else:
            logger.error("Данные не получены, пропуск позиции.")
            return False

    def _handle_pagination(
        self, current_page_number: int, walk_page_number: Optional[int]
    ) -> tuple[int, bool]:
        """Обрабатывает пагинацию и переход на следующую страницу.

        Args:
            current_page_number: Текущий номер страницы.
            walk_page_number: Целевой номер страницы для перехода (или None).

        Returns:
            Кортеж (next_page_number, should_continue):
            - next_page_number: Номер следующей страницы
            - should_continue: True если есть следующие страницы

        Примечание:
            - Вычисляет следующую страницу на основе доступных
            - Обрабатывает режим перехода к определённой странице
            - Возвращает False если достигнут конец результатов
        """
        # Вычисляем следующий номер страницы
        if walk_page_number is not None:
            try:
                available_pages = self._get_available_pages()
                available_pages_ahead = {
                    k: v for k, v in available_pages.items() if k > current_page_number
                }
                next_page_number = min(
                    available_pages_ahead,
                    key=lambda n: abs(n - walk_page_number) if walk_page_number is not None else 0,
                    default=current_page_number + 1,
                )
            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as pages_error:
                logger.error("Ошибка при вычислении следующей страницы: %s", pages_error)
                next_page_number = current_page_number + 1
        else:
            next_page_number = current_page_number + 1

        # Переходим на следующую страницу
        current_page_number_result = self._go_page(next_page_number)
        if not current_page_number_result:
            logger.info("Достигнут конец результатов поиска")
            return next_page_number, False

        # Сбрасываем страницу назначения, если мы закончили переход к желаемой странице
        if walk_page_number is not None and walk_page_number <= current_page_number_result:
            walk_page_number = None

        return current_page_number_result, True

    def _parse_search_results(
        self,
        writer: FileWriter,
        walk_page_number: Optional[int],
        visited_links: Optional[OrderedDict[str, None]] = None,
        max_visited_links: int = MAX_VISITED_LINKS_SIZE,
    ) -> None:
        """Парсит результаты поисковой выдачи.

        Args:
            writer: Файловый писатель для сохранения данных.
            walk_page_number: Целевой номер страницы для перехода (или None).
            visited_links: OrderedDict для хранения посещённых ссылок (опционально).
            max_visited_links: Максимальный размер visited_links.

        Примечание:
            - Основной цикл парсинга ссылок
            - Обработка пагинации
            - Оптимизация памяти и GC
            - Подсчёт пустых страниц и лимиты
        """
        # Спарсенные записи
        collected_records = 0

        # Уже посещённые ссылки (с оптимизацией памяти)
        # Оптимизация 3.1: используем OrderedDict с ограничением размера для эффективного управления памятью
        # OrderedDict автоматически удаляет старые записи при превышении maxlen
        if visited_links is None:
            visited_links = OrderedDict()
        visited_links_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

        # Оптимизация: кэшируем psutil.Process объект для снижения накладных расходов
        _process_cache = None
        if PSUTIL_AVAILABLE:
            try:
                _process_cache = psutil.Process()
            except (OSError, RuntimeError, TypeError, ValueError) as process_error:
                logger.debug("Не удалось создать кэш процесса psutil: %s", process_error)

        # Счётчик подряд пустых страниц (для избежания бесконечного цикла при 404)
        consecutive_empty_pages = 0

        # Счётчик вызовов оптимизации памяти
        memory_check_counter = 0

        # Проверка и автоматическая оптимизация памяти при больших объёмах данных
        def check_and_optimize_memory():
            """Проверяет использование памяти и выполняет автоматическую оптимизацию.

            - Добавлен мониторинг использования памяти в реальном времени
            - Автоматический вызов gc.collect() при превышении порога
            - Принудительная очистка кэшей и буферов
            - Логирование использования памяти для отладки

            Оптимизация 3.1:
            - Кэширование psutil.Process объекта
            - Снижение частоты вызовов gc.collect()
            - OrderedDict автоматически управляет размером через maxlen

            Примечание:
                Функция использует OrderedDict для visited_links, что позволяет
                автоматически удалять старые записи при превышении лимита.
            """
            nonlocal memory_check_counter
            memory_check_counter += 1

            # Проверяем доступность psutil
            if not PSUTIL_AVAILABLE or _process_cache is None:
                logger.debug("psutil не доступен - пропускаем проверку памяти")
                return

            try:
                # Получаем текущее использование памяти процесса в МБ
                # Оптимизация: используем кэшированный Process объект
                memory_info = _process_cache.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024  # Конвертируем в МБ

                # Мониторинг использования памяти в реальном времени
                # Логируем использование памяти каждые 10 вызовов
                if memory_check_counter % 10 == 0:
                    logger.debug(
                        "Использование памяти: %.1f МБ (порог: %d МБ)",
                        memory_mb,
                        self._options.memory_threshold,
                    )

                # Проверяем превышение порога
                if memory_mb > self._options.memory_threshold:
                    logger.warning(
                        "Использование памяти %.1f МБ превышает порог %d МБ. "
                        "Выполняем автоматическую оптимизацию...",
                        memory_mb,
                        self._options.memory_threshold,
                    )

                    # Оптимизация 3.1: OrderedDict автоматически управляет размером
                    # Удаляем старые записи при превышении max_visited_links
                    with visited_links_lock:
                        if len(visited_links) > max_visited_links:
                            # Вычисляем количество элементов для удаления (75%)
                            target_remove = int(len(visited_links) * MEMORY_REMOVE_RATIO)

                            if target_remove > 0:
                                # Удаляем старые элементы из начала OrderedDict
                                for _ in range(target_remove):
                                    visited_links.popitem(last=False)

                                logger.debug(
                                    "Очищено %d ссылок для освобождения памяти", target_remove
                                )

                    # Принудительный вызов GC
                    # Выполняем сборку мусора для освобождения памяти
                    gc_collected = gc.collect()
                    logger.info(
                        "GC собрал %d объектов, освобождено памяти: %.1f МБ",
                        gc_collected,
                        memory_mb - (_process_cache.memory_info().rss / 1024 / 1024),
                    )

                    # Очищаем кэш запросов Chrome если возможно
                    try:
                        self._chrome_remote.clear_requests()
                        logger.debug("Очищен кэш запросов Chrome")
                    except (OSError, RuntimeError, TypeError, ValueError) as cache_error:
                        logger.debug("Ошибка при очистке кэша: %s", cache_error)

                    # Проверяем, освободилась ли память (один вызов memory_info())
                    new_memory_info = _process_cache.memory_info()
                    new_memory_mb = new_memory_info.rss / 1024 / 1024
                    saved_mb = memory_mb - new_memory_mb

                    if saved_mb > 0:
                        logger.info(
                            "Освобождено %.1f МБ памяти (%.1f%% уменьшение)",
                            saved_mb,
                            (saved_mb / memory_mb) * 100,
                        )
                    else:
                        logger.debug("Не удалось освободить значительный объём памяти")

                    # Проверка на переполнение памяти
                    # Если память всё ещё превышает порог после очистки - логируем критическую ошибку
                    if new_memory_mb > self._options.memory_threshold * 1.5:
                        logger.error(
                            "КРИТИЧЕСКОЕ ПЕРЕПОЛНЕНИЕ ПАМЯТИ: %.1f МБ после очистки. "
                            "Рекомендуется уменьшить batch_size или увеличить memory_threshold.",
                            new_memory_mb,
                        )

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as memory_error:
                logger.debug("Ошибка при проверке памяти: %s", memory_error)

        # Эта обёртка не необходима, но я хочу быть уверен,
        # что мы не собрали ссылки из старого DOM каким-то образом.
        @wait_until_finished(
            timeout=GET_UNIQUE_LINKS_TIMEOUT, throw_exception=False, poll_interval=0.05
        )
        def get_unique_links() -> Optional[DOMNodeList]:
            """Получает уникальные ссылки, которые ещё не были посещены.

            Оптимизация 3.1:
            - Использование OrderedDict для эффективного управления памятью
            - Пакетное добавление ссылок вместо поэлементного
            - Автоматическое удаление старых ссылок при превышении лимита

            Returns:
                Список уникальных DOM-узлов ссылок или None при ошибке/повторе.
            """
            try:
                links = self._get_links()
                # Проверяем, что ссылки успешно получены
                if links is None:
                    return None

                # Optimization: use set comprehension for fast set creation
                link_hrefs = {  # FIX #10: Unclear variable naming
                    link.attributes["href"] for link in links if "href" in link.attributes
                }

                with visited_links_lock:
                    # Optimization: use set.intersection for fast checking
                    if link_hrefs.intersection(visited_links.keys()):
                        # Возвращаем None вместо пустого списка для явного указания на повтор
                        return None

                    # Optimization 3.1: batch add links to OrderedDict
                    for url in link_hrefs:
                        visited_links[url] = None

                    # Немедленное удаление старых ссылок при превышении лимита
                    # Это гарантирует что visited_links не превысит max_visited_links
                    if len(visited_links) > max_visited_links:
                        # Вычисляем количество элементов для удаления (LRU - старые записи)
                        overflow = len(visited_links) - max_visited_links
                        # Удаляем старые элементы из начала OrderedDict (LRU eviction)
                        for _ in range(overflow):
                            visited_links.popitem(last=False)

                        logger.debug(
                            "LRU eviction: удалено %d старых ссылок, осталось %d (max: %d)",
                            overflow,
                            len(visited_links),
                            max_visited_links,
                        )

                return links
            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                logger.error("Ошибка при получении уникальных ссылок: %s", e)
                return None

        current_page_number = 1

        try:
            # Счётчик попыток получения ссылок для предотвращения бесконечного цикла
            # Используем константу MAX_LINK_ATTEMPTS вместо магического числа
            link_attempt_count = 0

            while True:
                # Ждём завершения всех 2GIS запросов
                try:
                    if not self._wait_requests_finished():
                        logger.warning("Таймаут ожидания завершения запросов")
                except (OSError, RuntimeError, TypeError, ValueError) as wait_error:
                    logger.warning("Ошибка при ожидании запросов: %s", wait_error)

                # Собираем ссылки для клика
                links: list[DOMNode] | None = get_unique_links()

                # Проверяем, что ссылки успешно получены
                if links is None:
                    consecutive_empty_pages += 1
                    link_attempt_count += 1
                    logger.warning(
                        "Не удалось получить ссылки, переходим к следующей странице. "
                        "(Пустых страниц подряд: %d/%d, Попыток: %d/%d)",
                        consecutive_empty_pages,
                        self._options.max_consecutive_empty_pages,
                        link_attempt_count,
                        MAX_LINK_ATTEMPTS,
                    )

                    # Если подряд слишком много пустых страниц - прерываем парсинг
                    # Это избегает бесконечного цикла при 404 ошибках
                    if consecutive_empty_pages >= self._options.max_consecutive_empty_pages:
                        logger.error(
                            "Достигнут лимит подряд пустых страниц (%d). Прекращаем парсинг URL.",
                            self._options.max_consecutive_empty_pages,
                        )
                        return

                    # Если слишком много попыток получения ссылок неудачны - прерываем цикл
                    if link_attempt_count >= MAX_LINK_ATTEMPTS:
                        logger.error(
                            "Достигнут лимит попыток получения ссылок (%d). Прекращаем парсинг URL.",
                            MAX_LINK_ATTEMPTS,
                        )
                        return

                    # Переходим к следующей странице
                    next_page, should_continue = self._handle_pagination(
                        current_page_number, walk_page_number
                    )
                    if not should_continue:
                        return
                    current_page_number = next_page
                    continue
                else:
                    # Ссылки успешно получены - сбрасываем счётчик пустых страниц и попыток
                    consecutive_empty_pages = 0
                    link_attempt_count = 0

                # Парсим страницу, если не идём к определённой странице
                if not walk_page_number:
                    # Счётчик ссылок для периодической очистки памяти
                    links_since_gc = 0

                    # Итерируемся по собранным ссылкам
                    for link in links:
                        # Парсим страницу организации
                        if self._parse_firm_page(link, writer):
                            collected_records += 1

                            # Проверяем достижение лимита после каждой успешной записи
                            if collected_records >= self._options.max_records:
                                logger.info(
                                    "Спарсено максимально разрешенное количество записей с данного URL."
                                )
                                return

                        # Периодическая очистка памяти каждые 10 ссылок вместо каждой
                        links_since_gc += 1
                        if links_since_gc >= 10:
                            gc.collect()
                            links_since_gc = 0

                # Запускаем сборщик мусора и проверяем использование памяти
                # Это выполняется каждые несколько страниц для предотвращения OutOfMemory ошибок
                if current_page_number % self._options.gc_pages_interval == 0:
                    # Проверяем и оптимизируем использование памяти
                    check_and_optimize_memory()

                    # Запускаем сборщик мусора, если включён
                    if self._options.use_gc:
                        logger.debug("Запуск сборщика мусора.")
                        try:
                            self._chrome_remote.execute_script('"gc" in window && window.gc()')
                        except (OSError, RuntimeError, TypeError, ValueError) as gc_error:
                            logger.debug("Ошибка при запуске сборщика мусора: %s", gc_error)

                # Переходим к следующей странице
                next_page, should_continue = self._handle_pagination(
                    current_page_number, walk_page_number
                )
                if not should_continue:
                    return
                current_page_number = next_page

                # Освобождаем память, выделенную для собранных запросов
                # Вызываем ПОСЛЕ перехода на следующую страницу, чтобы не удалить нужные запросы
                try:
                    self._chrome_remote.clear_requests()
                except (OSError, RuntimeError, TypeError, ValueError) as clear_error:
                    logger.debug("Ошибка при очистке запросов: %s", clear_error)

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            # При любом исключении гарантируем закрытие chrome_remote
            logger.error("Критическая ошибка при парсинге: %s", e, exc_info=True)
            raise
        finally:
            # Гарантируем очистку ресурсов
            try:
                self._chrome_remote.clear_requests()
            except (OSError, RuntimeError, TypeError, ValueError) as e:
                logger.debug("Ошибка при очистке запросов: %s", e)

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с элементами результатов.

        Args:
            writer: Целевой файловый писатель.

        Примечание:
            Функция включает улучшенную обработку HTTP ошибок (404, 403, 500 и т.д.),
            детальную обработку ошибок на каждом этапе парсинга и оптимизацию
            работы с памятью через очистку посещённых ссылок.

            Структура функции:
            1. _navigate_to_search() — навигация к поиску
            2. _validate_document_response() — валидация ответа
            3. _parse_search_results() — парсинг выдачи
            4. _handle_pagination() — обработка пагинации (вызывается внутри)
        """
        # Начиная со страницы 6 и далее
        # 2GIS автоматически перенаправляет пользователя в начало (anti-bot защита).
        # Если в URL найден аргумент страницы, мы должны вручную перейти к ней сначала.

        url = re.sub(r"/page/\d+", "", self._url, re.I)

        page_match = re.search(r"/page/(?P<page_number>\d+)", self._url, re.I)
        walk_page_number = int(page_match.group("page_number")) if page_match else None

        # Оптимизация: используем OrderedDict для эффективного управления памятью
        # посещённых ссылок с автоматическим удалением старых записей (LRU eviction)
        visited_links: OrderedDict[str, None] = OrderedDict()
        max_visited_links = MAX_VISITED_LINKS_SIZE

        # Навигация к поисковой выдаче с retry logic и jitter
        max_retries = self._options.max_retries
        base_delay = self._options.retry_delay_base

        navigate_success = False
        for attempt in range(max_retries + 1):
            try:
                # Первая попытка или повторная
                if attempt > 0:
                    logger.info(
                        "Повторная попытка навигации (%d/%d) для URL: %s", attempt, max_retries, url
                    )

                self._navigate_to_search(url)
                navigate_success = True
                break

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as navigate_error:
                if attempt < max_retries and self._options.retry_on_network_errors:
                    # Добавляем jitter для предотвращения thundering herd эффекта
                    # Формула: base_delay * (2 ** attempt) + random.uniform(0, 1)
                    jitter = random.uniform(0, 1)
                    delay = base_delay * (2**attempt) + jitter
                    logger.warning(
                        "Ошибка при навигации (попытка %d/%d): %s. "
                        "Повторная попытка через %.1f сек...",
                        attempt + 1,
                        max_retries,
                        navigate_error,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    # Исчерпаны все попытки
                    logger.error("Таймаут навигации по URL %s: %s", url, navigate_error)
                    return

        # Если навигация не удалась - выходим
        if not navigate_success:
            return

        # Валидация ответа документа
        document_response = self._validate_document_response()
        if document_response is None:
            return

        # Парсинг результатов поиска
        # Передаём visited_links для управления памятью с eviction policy
        self._parse_search_results(writer, walk_page_number, visited_links, max_visited_links)

    def close(self) -> None:
        """Закрывает браузер и освобождает ресурсы.

        Закрывает только если браузер был создан внутри парсера
        (не был передан извне через browser параметр).
        """
        if self._owns_browser:
            self._chrome_remote.stop()

    def __enter__(self) -> MainParser:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return (
            f"{classname}(parser_options={self._options!r}, "
            f"chrome_remote={self._chrome_remote!r}, "
            f"url={self._url!r})"
        )
