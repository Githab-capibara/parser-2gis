"""Парсер для вкладок "В здании" 2GIS.

Предоставляет класс InBuildingParser для парсинга списка организаций
во вкладке "В здании":
- URL-паттерн: /inside/<building_id>
- Пошаговый переход по ссылкам организаций
- Извлечение данных через API
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from parser_2gis.logger import logger
from parser_2gis.utils.decorators import wait_until_finished

from .main import MainParser

if TYPE_CHECKING:
    from parser_2gis.chrome.dom import DOMNode
    from parser_2gis.writer import FileWriter


class InBuildingParser(MainParser):
    """Парсер для списка организаций, предоставленных 2GIS с вкладкой "В здании".

    URL-паттерн для таких случаев: https://2gis.<domain>/<city_id>/inside/<building_id>
    """

    @staticmethod
    def url_pattern() -> str:
        """Возвращает URL-паттерн для парсера вкладок "В здании".

        Returns:
            Regex паттерн для匹配 URL вкладок "В здании" 2GIS.

        """
        return r"https?://2gis\.[^/]+/[^/]+/inside/.*"

    @wait_until_finished(timeout=1.5, throw_exception=False, poll_interval=0.01)
    def _get_links(self, _timeout: float = 1.5) -> list[DOMNode] | None:
        """Извлекает конкретные ссылки узлов DOM из текущего снимка DOM.

        Args:
            _timeout: Таймаут ожидания завершения операции в секундах (по умолчанию 1.5).

        Returns:
            Список DOM-узлов ссылок или None при ошибке.

        Примечание:
            Функция валидирует каждую ссылку и проверяет соответствие паттерну
            /<city_id>/firm/<firm_id>.

        """

        def valid_link(node: DOMNode) -> bool:
            """Проверяет, что DOM-узел является допустимой ссылкой на фирму 2GIS."""
            if node.local_name == "a" and "href" in node.attributes:
                link_match = re.match(r"/[^/]+/firm/[^/]+$", node.attributes["href"])
                return bool(link_match)

            return False

        dom_tree = self._chrome_remote.get_document()
        links = dom_tree.search(valid_link)
        return links if links else None

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с организациями.

        Args:
            writer: Целевой файловый писатель.

        """
        # Переходим по URL с агрессивно уменьшенным таймаутом для ускорения
        self._chrome_remote.navigate(self._url, referer="https://google.com", timeout=20)

        # Документ загружен, получаем ответ
        responses = self._chrome_remote.get_responses()
        if not responses:
            logger.error("Ошибка получения ответа сервера.")
            return

        # Безопасное получение первого ответа
        try:
            document_response = responses[0]
        except (IndexError, KeyError):
            logger.error("Список ответов пуст или некорректен.")
            return

        # Обработка 404
        if document_response.get("mimeType") != "text/html":
            logger.error(
                "Неверный тип MIME ответа: %s", document_response.get("mimeType", "неизвестно")
            )
            return

        if document_response.get("status") == 404:
            logger.warning('Сервер вернул сообщение "Точных совпадений нет / Не найдено".')

            if self._options.skip_404_response:
                return

        # Спарсенные записи
        collected_records = 0

        # Уже посещённые ссылки
        visited_links: set[str] = set()

        # Получаем новые ссылки
        @wait_until_finished(timeout=1.5, throw_exception=False, poll_interval=0.01)
        def get_unique_links() -> list[DOMNode] | None:
            """Возвращает список непосещённых ссылок на фирмы."""
            links = self._get_links()
            if links is None:
                return None
            link_addresses = {x.attributes["href"] for x in links} - visited_links
            visited_links.update(link_addresses)
            return [x for x in links if x.attributes["href"] in link_addresses]

        # Проходим по лениво загружаемому списку организаций
        while True:
            # Ждём завершения всех запросов 2GIS
            self._wait_requests_finished()

            # Собираем ссылки для клика
            links = get_unique_links()
            if links is None:
                break
            if not links:
                break

            # Итерируемся по собранным ссылкам
            for link in links:
                resp = None
                for _ in range(3):  # 3 попытки получить ответ
                    # Кликаем по ссылке, чтобы вызвать запрос
                    # с ключом авторизации и секретными аргументами
                    self._chrome_remote.perform_click(link)

                    # Задержка между кликами, может быть полезна, если
                    # анти-бот сервис 2GIS станет более строгим.
                    if self._options.delay_between_clicks:
                        self._chrome_remote.wait(self._options.delay_between_clicks / 1000)

                    # Получаем ответ и собираем полезную нагрузку.
                    resp = self._chrome_remote.wait_response(self._item_response_pattern)

                    # Если запрос не удался — повторяем, иначе идём дальше.
                    if resp and resp.get("status", -1) >= 0:
                        break

                # Получаем данные тела ответа
                if resp and resp.get("status", -1) >= 0:
                    data = self._chrome_remote.get_response_body(resp)

                    try:
                        doc = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error(
                            'Сервер вернул некорректный JSON документ: "%s", пропуск позиции.', data
                        )
                        doc = None
                else:
                    doc = None

                if doc:
                    # Записываем API документ в файл
                    writer.write(doc)
                    collected_records += 1
                else:
                    logger.error("Данные не получены, пропуск позиции.")

                # Достигли лимита, выходим
                if collected_records >= self._options.max_records:
                    logger.info(
                        "Спарсено максимально разрешенное количество записей с данного URL."
                    )
                    return
