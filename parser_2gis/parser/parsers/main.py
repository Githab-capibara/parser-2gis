from __future__ import annotations

import base64
import json
import re
import urllib.parse
from typing import TYPE_CHECKING, Optional

from ...chrome import ChromeRemote
from ...common import wait_until_finished
from ...logger import logger
from ..utils import blocked_requests

if TYPE_CHECKING:
    from ...chrome import ChromeOptions
    from ...chrome.dom import DOMNode
    from ...writer import FileWriter
    from ..options import ParserOptions


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

    @wait_until_finished(timeout=5, throw_exception=False)
    def _get_links(self) -> list[DOMNode]:
        """Извлекает определённые DOM-узлы ссылок из текущего снимка DOM."""
        def valid_link(node: DOMNode) -> bool:
            if node.local_name == 'a' and 'href' in node.attributes:
                link_match = re.match(r'.*/(firm|station)/.*\?stat=(?P<data>[a-zA-Z0-9%]+)', node.attributes['href'])
                if link_match:
                    try:
                        base64.b64decode(urllib.parse.unquote(link_match.group('data')))
                        return True
                    except Exception:
                        pass

            return False

        dom_tree = self._chrome_remote.get_document()
        return dom_tree.search(valid_link)

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

    @wait_until_finished(timeout=120)
    def _wait_requests_finished(self) -> bool:
        """Ждёт завершения всех ожидающих запросов."""
        return self._chrome_remote.execute_script('window.openHTTPs == 0')

    def _get_available_pages(self) -> dict[int, DOMNode]:
        """Получает доступные страницы для навигации."""
        dom_tree = self._chrome_remote.get_document()
        dom_links = dom_tree.search(lambda x: x.local_name == 'a' and 'href' in x.attributes)

        available_pages = {}
        for link in dom_links:
            link_match = re.match(r'.*/search/.*/page/(?P<page_number>\d+)', link.attributes['href'])
            if link_match:
                available_pages[int(link_match.group('page_number'))] = link

        return available_pages

    def _go_page(self, n_page: int) -> Optional[int]:
        """Переходит на страницу с номером `n_page`.

        Note:
            `n_page` должна существовать в текущем DOM.
            В противном случае 2GIS anti-bot перенаправит вас на первую страницу.

        Args:
            n_page: Номер страницы.

        Returns:
            Номер страницы, на которую перешли.
        """
        available_pages = self._get_available_pages()
        if n_page in available_pages:
            self._chrome_remote.perform_click(available_pages[n_page])
            return n_page

        return None

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с элементами результатов.

        Args:
            writer: Целевой файловый писатель.
        """
        # Начиная со страницы 6 и далее
        # 2GIS автоматически перенаправляет пользователя в начало (anti-bot защита).
        # Если в URL найден аргумент страницы, мы должны вручную перейти к ней сначала.

        current_page_number = 1
        url = re.sub(r'/page/\d+', '', self._url, re.I)

        page_match = re.search(r'/page/(?P<page_number>\d+)', self._url, re.I)
        if page_match:
            walk_page_number = int(page_match.group('page_number'))
        else:
            walk_page_number = None

        # Переходим по URL
        self._chrome_remote.navigate(url, referer='https://google.com', timeout=120)

        # Документ загружен, получаем его ответ
        responses = self._chrome_remote.get_responses(timeout=5)
        if not responses:
            logger.error('Ошибка получения ответа сервера.')
            return
        document_response = responses[0]

        # Обработка 404
        if document_response['mimeType'] != 'text/html':
            logger.error('Неверный тип MIME ответа: %s', document_response['mimeType'])
            return
            
        if document_response['status'] == 404:
            logger.warning('Сервер вернул сообщение "Точных совпадений нет / Не найдено".')

            if self._options.skip_404_response:
                return

        # Спарсенные записи
        collected_records = 0

        # Уже посещённые ссылки
        visited_links: set[str] = set()

        # Эта обёртка не необходима, но я хочу быть уверен,
        # что мы не собрали ссылки из старого DOM каким-то образом.
        @wait_until_finished(timeout=10, throw_exception=False)
        def get_unique_links() -> list[DOMNode]:
            links = self._get_links()
            link_addresses = set(x.attributes['href'] for x in links)
            if link_addresses & visited_links:
                return []

            visited_links.update(link_addresses)
            return links

        while True:
            # Ждём завершения всех 2GIS запросов
            self._wait_requests_finished()

            # Собираем ссылки для клика
            links = get_unique_links()

            # Мы должны парсить страницу, если не идём к определённой странице
            if not walk_page_number:
                # Итерируемся по собранным ссылкам
                for link in links:
                    for _ in range(3):  # 3 попытки получить ответ
                        # Кликаем на ссылку, чтобы спровоцировать запрос
                        # с ключом авторизации и секретными аргументами
                        self._chrome_remote.perform_click(link)

                        # Задержка между кликами, может быть полезна, если
                        # 2GIS's anti-bot сервис станет более строгим.
                        if self._options.delay_between_clicks:
                            self._chrome_remote.wait(self._options.delay_between_clicks / 1000)

                        # Собираем ответы и собираем полезные данные.
                        resp = self._chrome_remote.wait_response(self._item_response_pattern)

                        # Если запрос не удался - повторяем, иначе идём дальше.
                        if resp and resp['status'] >= 0:
                            break

                    # Получаем данные тела ответа
                    if resp and resp['status'] >= 0:
                        data = self._chrome_remote.get_response_body(resp, timeout=10) if resp else None

                        try:
                            doc = json.loads(data)
                        except json.JSONDecodeError:
                            logger.error('Сервер вернул некорректный JSON документ: "%s", пропуск позиции.', data)
                            doc = None
                    else:
                        doc = None

                    if doc:
                        # Записываем API документ в файл
                        writer.write(doc)
                        collected_records += 1
                    else:
                        logger.error('Данные не получены, пропуск позиции.')

                    # Мы достигли нашего лимита, выходим
                    if collected_records >= self._options.max_records:
                        logger.info('Спарсено максимально разрешенное количество записей с данного URL.')
                        return

            # Запускаем сборщик мусора, если он доступен и включён
            if self._options.use_gc and current_page_number % self._options.gc_pages_interval == 0:
                logger.debug('Запуск сборщика мусора.')
                self._chrome_remote.execute_script('"gc" in window && window.gc()')

            # Освобождаем память, выделенную для собранных запросов
            self._chrome_remote.clear_requests()

            # Вычисляем следующий номер страницы и переходим к ней
            if walk_page_number:
                available_pages = self._get_available_pages()
                available_pages_ahead = {k: v for k, v in available_pages.items()
                                         if k > current_page_number}
                next_page_number = min(available_pages_ahead, key=lambda n: abs(n - walk_page_number),  # type: ignore
                                       default=current_page_number + 1)
            else:
                next_page_number = current_page_number + 1

            current_page_number = self._go_page(next_page_number)  # type: ignore
            if not current_page_number:
                break  # Достигли конца результатов поиска

            # Сбрасываем страницу назначения, если мы закончили переход к желаемой странице
            if walk_page_number and walk_page_number <= current_page_number:
                walk_page_number = None

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
