from __future__ import annotations

from typing import TYPE_CHECKING

from ...logger import logger
from .main import MainParser

if TYPE_CHECKING:
    from ...writer import FileWriter


class FirmParser(MainParser):
    """Парсер для фирм, предоставленных 2GIS.

    URL-паттерн для таких случаев: https://2gis.<domain>/<city_id>/firm/<firm_id>
    """
    @staticmethod
    def url_pattern():
        """URL-паттерн для парсера."""
        return r'https?://2gis\.[^/]+(/[^/]+)?/firm/.*'

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с организацией.

        Args:
            writer: Целевой файловый писатель.
        """
        # Переходим по URL
        self._chrome_remote.navigate(self._url, referer='https://google.com', timeout=120)

        # Документ загружен, получаем ответ
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
            logger.warning('Сервер вернул сообщение "Организация не найдена".')

            if self._options.skip_404_response:
                return

        # Ждём завершения всех запросов 2GIS
        self._wait_requests_finished()

        # Получаем ответ и собираем полезную нагрузку.
        initial_state = self._chrome_remote.execute_script('window.initialState')
        data = list(initial_state['data']['entity']['profile'].values())
        if not data:
            logger.warning('Данные организации не найдены.')
            return
        doc = data[0]

        # Записываем API документ в файл
        writer.write({
            'result': {
                'items': [doc['data']]
            },
            'meta': doc['meta']
        })
