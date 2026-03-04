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
        # Переходим по URL с таймаутом 5 минут
        self._chrome_remote.navigate(self._url, referer='https://google.com', timeout=300)

        # Документ загружен, получаем ответ
        responses = self._chrome_remote.get_responses()
        if not responses:
            logger.error('Ошибка получения ответа сервера.')
            return

        # Безопасное получение первого ответа
        try:
            document_response = responses[0]
        except (IndexError, KeyError):
            logger.error('Список ответов пуст или некорректен.')
            return

        # Обработка 404
        if document_response.get('mimeType') != 'text/html':
            logger.error('Неверный тип MIME ответа: %s', document_response.get('mimeType', 'неизвестно'))
            return

        if document_response.get('status') == 404:
            logger.warning('Сервер вернул сообщение "Организация не найдена".')

            if self._options.skip_404_response:
                return

        # Ждём завершения всех запросов 2GIS
        self._wait_requests_finished()

        # Получаем ответ и собираем полезную нагрузку.
        try:
            initial_state = self._chrome_remote.execute_script('window.initialState')
            if not initial_state:
                logger.warning('Данные организации не найдены (initialState отсутствует).')
                return

            # Безопасное извлечение данных с проверкой всех ключей
            data_dict = initial_state.get('data', {})
            entity = data_dict.get('entity', {})
            profile = entity.get('profile', {})
            
            if not profile:
                logger.warning('Данные организации не найдены (profile отсутствует).')
                return

            data = list(profile.values())
            if not data:
                logger.warning('Данные организации не найдены (пустой профиль).')
                return
            doc = data[0]
        except (KeyError, TypeError, AttributeError) as e:
            logger.error('Ошибка при получении данных организации: %s', e)
            return

        # Записываем API документ в файл
        writer.write({
            'result': {
                'items': [doc['data']]
            },
            'meta': doc.get('meta', {})
        })
