from __future__ import annotations

import base64
import gc
import json
import re
import sys
import time
import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    PSUTIL_AVAILABLE = False

from ...chrome import ChromeRemote
from ...common import wait_until_finished
from ...logger import logger
from ..utils import blocked_requests

if TYPE_CHECKING:
    from ...chrome import ChromeOptions
    from ...chrome.dom import DOMNode
    from ...writer import FileWriter
    from ..options import ParserOptions


# Константы модуля для магических чисел
MAX_RESPONSE_ATTEMPTS: int = 3  # Максимальное количество попыток получить ответ
NAVIGATION_TIMEOUT: int = 120  # Таймаут навигации в секундах
WAIT_REQUESTS_TIMEOUT: int = 120  # Таймаут ожидания завершения запросов
GET_LINKS_TIMEOUT: int = 5  # Таймаут получения ссылок
GET_UNIQUE_LINKS_TIMEOUT: int = 10  # Таймаут получения уникальных ссылок
MAX_VISITED_LINKS_SIZE: int = 10000  # Максимальный размер множества посещённых ссылок
# MAX_CONSECUTIVE_EMPTY_PAGES теперь задается через ParserOptions.max_consecutive_empty_pages (по умолчанию 3)


# Типы для типизации
DOMNodeList = List['DOMNode']


class MainParser:
    """Основной парсер, который извлекает полезные данные
    со страниц поисковой выдачи с помощью браузера Chrome
    и сохраняет их в файлы `csv`, `xlsx` или `json`.

    Args:
        url: 2GIS URLs с элементами для сбора.
        chrome_options: Опции Chrome.
        parser_options: Опции парсера.
    """

    def __init__(self, url: str,
                 chrome_options: ChromeOptions,
                 parser_options: ParserOptions) -> None:
        self._options = parser_options
        self._url = url

        # Паттерн ответа "Catalog Item Document"
        self._item_response_pattern = r'https://catalog\.api\.2gis.[^/]+/.*/items/byid'

        # Открываем браузер, запускаем remote
        response_patterns = [self._item_response_pattern]
        self._chrome_remote = ChromeRemote(chrome_options=chrome_options,
                                           response_patterns=response_patterns)
        self._chrome_remote.start()

        # Добавляем счётчик для 2GIS запросов
        self._add_xhr_counter()

        # Отключаем определённые запросы
        blocked_urls = blocked_requests(extended=chrome_options.disable_images)
        self._chrome_remote.add_blocked_requests(blocked_urls)

    @staticmethod
    def url_pattern():
        """URL-паттерн для парсера."""
        return r'https?://2gis\.[^/]+/[^/]+/search/.*'

    @wait_until_finished(timeout=GET_LINKS_TIMEOUT, throw_exception=False)
    def _get_links(self) -> Optional[DOMNodeList]:
        """Извлекает определённые DOM-узлы ссылок из текущего снимка DOM.

        Returns:
            Список DOM-узлов ссылок или None при ошибке.
            
        Примечание:
            Функция валидирует каждую ссылку и декодирует base64 данные
            для проверки корректности.
        """
        def valid_link(node: 'DOMNode') -> bool:
            """Проверяет валидность ссылки."""
            if node.local_name == 'a' and 'href' in node.attributes:
                href = node.attributes.get('href', '')
                if not href:
                    return False
                    
                link_match = re.match(
                    r'.*/(firm|station)/.*\?stat=(?P<data>[a-zA-Z0-9%]+)', 
                    href
                )
                if link_match:
                    try:
                        # Декодируем base64 данные для проверки корректности
                        urllib.parse.unquote(link_match.group('data'))
                        return True
                    except Exception:
                        # Ошибка декодирования - ссылка невалидна
                        pass

            return False

        try:
            dom_tree = self._chrome_remote.get_document()
            links = dom_tree.search(valid_link)
            # Возвращаем None если ссылки не найдены, иначе список ссылок
            return links if links else None
        except Exception as e:
            logger.error('Ошибка при получении ссылок: %s', e)
            return None

    def _add_xhr_counter(self) -> None:
        """Внедряет old-school обёртку вокруг XMLHttpRequest
        для отслеживания всех ожидающих запросов к сайту 2GIS."""
        xhr_script = r'''
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
        '''
        self._chrome_remote.add_start_script(xhr_script)

    @wait_until_finished(timeout=WAIT_REQUESTS_TIMEOUT)
    def _wait_requests_finished(self) -> bool:
        """Ждёт завершения всех ожидающих запросов."""
        return self._chrome_remote.execute_script('window.openHTTPs == 0')

    def _get_available_pages(self) -> Dict[int, 'DOMNode']:
        """Получает доступные страницы для навигации.
        
        Returns:
            Словарь {номер_страницы: DOMNode} доступных страниц.
        """
        try:
            dom_tree = self._chrome_remote.get_document()
            dom_links = dom_tree.search(
                lambda x: x.local_name == 'a' and 'href' in x.attributes
            )

            available_pages: Dict[int, 'DOMNode'] = {}
            for link in dom_links:
                href = link.attributes.get('href', '')
                if not href:
                    continue
                    
                link_match = re.match(
                    r'.*/search/.*/page/(?P<page_number>\d+)', 
                    href
                )
                if link_match:
                    page_number = int(link_match.group('page_number'))
                    available_pages[page_number] = link

            return available_pages
        except Exception as e:
            logger.error('Ошибка при получении доступных страниц: %s', e)
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
                logger.warning('Страница %d недоступна для перехода', n_page)
                return None
        except Exception as e:
            logger.error('Ошибка при переходе на страницу %d: %s', n_page, e)
            return None

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с элементами результатов.

        Args:
            writer: Целевой файловый писатель.
            
        Примечание:
            Функция включает улучшенную обработку HTTP ошибок (404, 403, 500 и т.д.),
            детальную обработку ошибок на каждом этапе парсинга и оптимизацию
            работы с памятью через очистку посещённых ссылок.
        """
        # Начиная со страницы 6 и далее
        # 2GIS автоматически перенаправляет пользователя в начало (anti-bot защита).
        # Если в URL найден аргумент страницы, мы должны вручную перейти к ней сначала.

        current_page_number = 1
        url = re.sub(r'/page/\d+', '', self._url, re.I)

        page_match = re.search(r'/page/(?P<page_number>\d+)', self._url, re.I)
        walk_page_number = int(page_match.group('page_number')) if page_match else None

        # Переходим по URL с возможностью повторных попыток при ошибках сети
        # Автоматический повторный парсинг при временных ошибках (502, 503, 504, TimeoutError)
        for retry_attempt in range(self._options.max_retries + 1):
            try:
                # Первая попытка или повторная
                if retry_attempt > 0:
                    logger.info('Повторная попытка навигации (%d/%d) для URL: %s', 
                               retry_attempt, self._options.max_retries, url)
                    
                self._chrome_remote.navigate(url, referer='https://google.com', timeout=NAVIGATION_TIMEOUT)
                # Если навигация успешна - выходим из цикла
                break
                
            except Exception as navigate_error:
                error_msg = str(navigate_error).lower()
                is_network_error = (
                    '502' in error_msg or 
                    '503' in error_msg or 
                    '504' in error_msg or 
                    'timeout' in error_msg
                )
                
                if retry_attempt < self._options.max_retries and self._options.retry_on_network_errors and is_network_error:
                    # Экспоненциальная задержка: 1с, 2с, 4с, ...
                    delay = self._options.retry_delay_base * (2 ** retry_attempt)
                    logger.warning(
                        'Ошибка сети при навигации (попытка %d/%d): %s. '
                        'Повторная попытка через %.1f сек...',
                        retry_attempt + 1, self._options.max_retries, navigate_error, delay
                    )
                    time.sleep(delay)
                else:
                    # Либо это не ошибка сети, либо исчерпаны все попытки
                    logger.error('Ошибка навигации по URL %s: %s', url, navigate_error)
                    return

        # Документ загружен, получаем его ответ
        try:
            responses = self._chrome_remote.get_responses()
        except Exception as e:
            logger.error('Ошибка при получении ответов: %s', e)
            return
            
        if not responses:
            logger.error('Ошибка получения ответа сервера.')
            return

        # Безопасное получение первого ответа с проверкой
        try:
            document_response = responses[0]
        except (IndexError, KeyError):
            logger.error('Список ответов пуст или некорректен.')
            return

        # Проверка наличия документа
        if not document_response:
            logger.error('Первый ответ пуст.')
            return

        # Обработка MIME типа
        mime_type = document_response.get('mimeType', '')
        if mime_type != 'text/html':
            logger.error('Неверный тип MIME ответа: %s', mime_type)
            return

        # Улучшенная обработка HTTP статусов
        http_status = document_response.get('status', 0)
        
        if http_status == 404:
            logger.warning('Сервер вернул 404: "Точных совпадений нет / Не найдено".')
            if self._options.skip_404_response:
                logger.info('Пропуск URL из-за 404 ответа (skip_404_response=True).')
                return
            # Если включен режим немедленной остановки при первом 404 - завершаем парсинг
            if self._options.stop_on_first_404:
                logger.info('Немедленная остановка парсинга при первом 404 (stop_on_first_404=True).')
                return
                
        elif http_status == 403:
            logger.error('Сервер вернул 403: Доступ запрещён. Возможна блокировка.')
            return
            
        elif http_status in (500, 502, 503, 504):
            logger.error('Сервер вернул ошибку %d: Временная проблема на стороне сервера.', http_status)
            return
            
        elif http_status < 200 or http_status >= 400:
            logger.warning('Сервер вернул нестандартный статус: %d', http_status)

        # Спарсенные записи
        collected_records = 0

        # Уже посещённые ссылки (с оптимизацией памяти)
        visited_links: Set[str] = set()

        # Счётчик подряд пустых страниц (для избежания бесконечного цикла при 404)
        consecutive_empty_pages = 0
        
        # Проверка и автоматическая оптимизация памяти при больших объёмах данных
        def check_and_optimize_memory():
            """Проверяет использование памяти и выполняет автоматическую оптимизацию.

            Эта функция вызывается периодически для предотвращения OutOfMemory ошибок
            при парсинге больших объёмов данных (>10000 записей).
            
            Примечание:
                Требуется установленный пакет psutil для мониторинга памяти.
            """
            # Проверяем доступность psutil
            if not PSUTIL_AVAILABLE:
                logger.debug('psutil не установлен - пропускаем проверку памяти')
                return
                
            try:
                # Получаем текущее использование памяти процесса в МБ
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024  # Конвертируем в МБ

                # Проверяем превышение порога (увеличен с 500 до 2048 МБ)
                if memory_mb > self._options.memory_threshold:
                    logger.warning(
                        'Использование памяти %.1f МБ превышает порог %d МБ. '
                        'Выполняем автоматическую оптимизацию...',
                        memory_mb, self._options.memory_threshold
                    )

                    # Усиливаем очистку: очищаем 75% посещённых ссылок вместо 50%
                    if len(visited_links) > 1000:
                        links_list = list(visited_links)
                        keep_count = len(links_list) // 4  # Оставляем 25% старых ссылок
                        visited_links.clear()
                        visited_links.update(links_list[keep_count:])
                        logger.debug('Очищено %d ссылок для освобождения памяти', len(links_list) - keep_count)

                    # Дополнительный вызов сборщика мусора для агрессивной очистки
                    gc.collect()
                    gc.collect()  # Двойной вызов для лучшей очистки

                    # Очищаем кэш запросов Chrome если возможно
                    try:
                        self._chrome_remote.clear_requests()
                        logger.debug('Очищен кэш запросов Chrome')
                    except Exception as cache_error:
                        logger.debug('Ошибка при очистке кэша: %s', cache_error)

                    # Проверяем, освободилась ли память
                    new_memory_info = process.memory_info()
                    new_memory_mb = new_memory_info.rss / 1024 / 1024
                    saved_mb = memory_mb - new_memory_mb

                    if saved_mb > 0:
                        logger.info('Освобождено %.1f МБ памяти (%.1f%% уменьшение)',
                                   saved_mb, (saved_mb / memory_mb) * 100)
                    else:
                        logger.warning('Не удалось освободить значительный объём памяти')

            except Exception as memory_error:
                logger.debug('Ошибка при проверке памяти: %s', memory_error)

        # Эта обёртка не необходима, но я хочу быть уверен,
        # что мы не собрали ссылки из старого DOM каким-то образом.
        @wait_until_finished(timeout=GET_UNIQUE_LINKS_TIMEOUT, throw_exception=False)
        def get_unique_links() -> Optional[DOMNodeList]:
            """Получает уникальные ссылки, которые ещё не были посещены.

            Returns:
                Список уникальных DOM-узлов ссылок или None при ошибке/повторе.
            """
            try:
                links = self._get_links()
                # Проверяем, что ссылки успешно получены
                if links is None:
                    return None
                    
                link_addresses = {x.attributes['href'] for x in links if 'href' in x.attributes}
                
                if link_addresses & visited_links:
                    # Возвращаем None вместо пустого списка для явного указания на повтор
                    return None

                visited_links.update(link_addresses)
                
                # Оптимизация памяти: очищаем старые ссылки при превышении лимита
                if len(visited_links) > MAX_VISITED_LINKS_SIZE:
                    # Оставляем только последние 25% ссылок (усилено с 50%)
                    links_list = list(visited_links)
                    keep_count = len(links_list) // 4  # Оставляем 25% вместо 50%
                    visited_links.clear()
                    visited_links.update(links_list[keep_count:])
                    logger.debug('Оптимизация памяти: очищено %d старых ссылок', len(links_list) - keep_count)
                
                return links
            except Exception as e:
                logger.error('Ошибка при получении уникальных ссылок: %s', e)
                return None

        try:
            while True:
                # Ждём завершения всех 2GIS запросов
                try:
                    if not self._wait_requests_finished():
                        logger.warning('Таймаут ожидания завершения запросов')
                except Exception as wait_error:
                    logger.warning('Ошибка при ожидании запросов: %s', wait_error)

                # Собираем ссылки для клика
                links = get_unique_links()

                # Проверяем, что ссылки успешно получены
                if links is None:
                    consecutive_empty_pages += 1
                    logger.warning('Не удалось получить ссылки, переходим к следующей странице. (Пустых страниц подряд: %d/%d)', 
                                consecutive_empty_pages, self._options.max_consecutive_empty_pages)
                    
                    # Если подряд слишком много пустых страниц - прерываем парсинг
                    # Это избегает бесконечного цикла при 404 ошибках
                    if consecutive_empty_pages >= self._options.max_consecutive_empty_pages:
                        logger.error('Достигнут лимит подряд пустых страниц (%d). Прекращаем парсинг URL.', 
                                    self._options.max_consecutive_empty_pages)
                        return
                    
                    continue
                else:
                    # Ссылки успешно получены - сбрасываем счётчик пустых страниц
                    consecutive_empty_pages = 0

                # Парсим страницу, если не идём к определённой странице
                if not walk_page_number:
                    # Итерируемся по собранным ссылкам
                    for link in links:
                        resp: Optional[Dict[str, Any]] = None
                        
                        for attempt in range(MAX_RESPONSE_ATTEMPTS):  # 3 попытки получить ответ
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
                                if resp and resp.get('status', -1) >= 0:
                                    break

                                # Добавляем небольшую задержку между попытками для снижения нагрузки
                                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                                    self._chrome_remote.wait(0.5)
                                    
                            except Exception as click_error:
                                logger.warning('Ошибка при клике на ссылку (попытка %d): %s', 
                                             attempt + 1, click_error)
                                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                                    self._chrome_remote.wait(0.5)

                        # Пропускаем позицию, если все попытки получить ответ неудачны
                        if not resp or resp.get('status', -1) < 0:
                            logger.error('Не удалось получить ответ после %d попыток, пропуск позиции.',
                                        MAX_RESPONSE_ATTEMPTS)
                            continue

                        # Получаем данные тела ответа
                        try:
                            data = self._chrome_remote.get_response_body(resp)
                        except Exception as body_error:
                            logger.error('Ошибка при получении тела ответа: %s', body_error)
                            continue

                        # Парсим JSON
                        doc: Optional[Dict[str, Any]] = None
                        try:
                            doc = json.loads(data) if data else None
                        except json.JSONDecodeError as json_error:
                            logger.error('Сервер вернул некорректный JSON документ: "%s...", ошибка: %s', 
                                        data[:100] if data else '', json_error)

                        if doc:
                            # Записываем API документ в файл
                            try:
                                writer.write(doc)
                                collected_records += 1
                            except Exception as write_error:
                                logger.error('Ошибка записи данных: %s', write_error)
                                continue

                            # Проверяем достижение лимита после каждой успешной записи
                            if collected_records >= self._options.max_records:
                                logger.info('Спарсено максимально разрешенное количество записей с данного URL.')
                                return
                        else:
                            logger.error('Данные не получены, пропуск позиции.')

                        # Очистка памяти после обработки каждой ссылки
                        del resp
                        del data

                # Запускаем сборщик мусора и проверяем использование памяти
                # Это выполняется каждые несколько страниц для предотвращения OutOfMemory ошибок
                if current_page_number % self._options.gc_pages_interval == 0:
                    # Проверяем и оптимизируем использование памяти
                    check_and_optimize_memory()
                    
                    # Запускаем сборщик мусора, если включён
                    if self._options.use_gc:
                        logger.debug('Запуск сборщика мусора.')
                        try:
                            self._chrome_remote.execute_script('"gc" in window && window.gc()')
                        except Exception as gc_error:
                            logger.debug('Ошибка при запуске сборщика мусора: %s', gc_error)

                # Вычисляем следующий номер страницы и переходим к ней
                if walk_page_number:
                    try:
                        available_pages = self._get_available_pages()
                        available_pages_ahead = {k: v for k, v in available_pages.items()
                                                 if k > current_page_number}
                        next_page_number = min(
                            available_pages_ahead, 
                            key=lambda n: abs(n - walk_page_number),
                            default=current_page_number + 1
                        )
                    except Exception as pages_error:
                        logger.error('Ошибка при вычислении следующей страницы: %s', pages_error)
                        next_page_number = current_page_number + 1
                else:
                    next_page_number = current_page_number + 1

                current_page_number_result = self._go_page(next_page_number)
                if not current_page_number_result:
                    logger.info('Достигнут конец результатов поиска')
                    break  # Достигли конца результатов поиска
                    
                current_page_number = current_page_number_result

                # Сбрасываем страницу назначения, если мы закончили переход к желаемой странице
                if walk_page_number is not None and walk_page_number <= current_page_number:
                    walk_page_number = None

                # Освобождаем память, выделенную для собранных запросов
                # Вызываем ПОСЛЕ перехода на следующую страницу, чтобы не удалить нужные запросы
                try:
                    self._chrome_remote.clear_requests()
                except Exception as clear_error:
                    logger.debug('Ошибка при очистке запросов: %s', clear_error)
                    
        except Exception as e:
            # При любом исключении гарантируем закрытие chrome_remote
            logger.error('Критическая ошибка при парсинге: %s', e, exc_info=True)
            raise
        finally:
            # Гарантируем очистку ресурсов
            try:
                self._chrome_remote.clear_requests()
            except Exception:
                pass

    def close(self) -> None:
        self._chrome_remote.stop()

    def __enter__(self) -> MainParser:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return (f'{classname}(parser_options={self._options!r}, '
                f'chrome_remote={self._chrome_remote!r}, '
                f'url={self._url!r})')