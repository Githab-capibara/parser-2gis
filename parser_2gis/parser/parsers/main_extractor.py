"""
Модуль извлечения данных для парсера 2GIS.

Предоставляет класс MainDataExtractor для извлечения данных:
- Парсинг страниц организаций
- Извлечение JSON данных из API ответов
- Валидация и обработка данных
- Запись данных в writer

Этот модуль выделен из main.py для разделения ответственности:
- MainPageParser: DOM операции и навигация
- MainDataExtractor: Извлечение данных
- MainDataProcessor: Обработка данных
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Optional

from parser_2gis.logger import logger
from parser_2gis.parser.parsers.main_parser import MAX_RESPONSE_ATTEMPTS, RESPONSE_RETRY_DELAY

if TYPE_CHECKING:
    from parser_2gis.parser.parsers.main_parser import MainPageParser
    from parser_2gis.writer import FileWriter


class MainDataExtractor:
    """Класс для извлечения данных из страниц организаций 2GIS.

    Предоставляет функциональность для:
    - Парсинга страниц организаций по ссылкам
    - Извлечения JSON данных из API ответов
    - Валидации и обработки данных
    - Записи данных в writer

    Attributes:
        parser: Экземпляр MainPageParser для доступа к браузеру.
    """

    def __init__(self, parser: "MainPageParser") -> None:
        """Инициализация экстрактора данных.

        Args:
            parser: Экземпляр MainPageParser.
        """
        self._parser = parser

    def _parse_firm_page(self, link, writer: "FileWriter") -> bool:
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
                self._parser._chrome_remote.perform_click(link)

                # Задержка между кликами, может быть полезна, если
                # anti-bot сервис 2GIS станет более строгим.
                if self._parser._options.delay_between_clicks:
                    self._parser._chrome_remote.wait(
                        self._parser._options.delay_between_clicks / 1000
                    )

                # Собираем ответы и собираем полезные данные.
                resp = self._parser._chrome_remote.wait_response(
                    self._parser._item_response_pattern
                )

                # Если запрос не удался - повторяем, иначе идём дальше.
                if resp and resp.get("status", -1) >= 0:
                    break

                # Добавляем небольшую задержку между попытками для снижения нагрузки
                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                    self._parser._chrome_remote.wait(RESPONSE_RETRY_DELAY)

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as click_error:
                logger.warning(
                    "Ошибка при клике на ссылку (попытка %d): %s", attempt + 1, click_error
                )
                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                    self._parser._chrome_remote.wait(RESPONSE_RETRY_DELAY)

        # Пропускаем позицию, если все попытки получить ответ неудачны
        if not resp or resp.get("status", -1) < 0:
            logger.error(
                "Не удалось получить ответ после %d попыток, пропуск позиции.",
                MAX_RESPONSE_ATTEMPTS,
            )
            return False

        # Получаем данные тела ответа
        try:
            data = self._parser._chrome_remote.get_response_body(resp)
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
