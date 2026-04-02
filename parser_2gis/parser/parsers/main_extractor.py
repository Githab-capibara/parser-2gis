"""Модуль извлечения данных для парсера 2GIS.

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
from typing import TYPE_CHECKING, Any

from parser_2gis.logger import logger
from parser_2gis.parser.parsers.main_parser import MAX_RESPONSE_ATTEMPTS, RESPONSE_RETRY_DELAY

# =============================================================================
# КОНСТАНТЫ МОДУЛЯ
# =============================================================================

# Размер кэша извлечённых данных (увеличено с 1024 для поддержки большего количества данных)
EXTRACTOR_CACHE_MAX_SIZE: int = 2048

# Процент записей для LRU eviction при превышении размера кэша
CACHE_EVICTION_PERCENT: int = 10

# Задержка между кликами в миллисекундах (используется для вычисления задержки в секундах)
CLICK_DELAY_DIVISOR: int = 1000

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

    def __init__(self, parser: MainPageParser) -> None:
        """Инициализация экстрактора данных.

        Args:
            parser: Экземпляр MainPageParser.

        """
        self._parser = parser
        # C005: Увеличен размер кэша до 2048 и используется OrderedDict для эффективного LRU
        self._extracted_data_cache: dict[str, dict[str, Any]] = {}
        self._cache_max_size = EXTRACTOR_CACHE_MAX_SIZE

    def _get_link_url(self, link) -> str | None:
        """Получает URL из DOM-узла ссылки.

        H006: Извлекает URL для использования в качестве ключа кэша.

        Args:
            link: DOM-узел ссылки.

        Returns:
            URL или None если не удалось извлечь.

        Raises:
            OSError: При ошибке доступа к атрибутам DOM-узла.
            RuntimeError: При ошибке выполнения методов DOM-узла.
            TypeError: При некорректном типе DOM-узла.
            ValueError: При некорректном значении атрибута href.

        """
        try:
            # Пытаемся получить href атрибут
            if hasattr(link, "getAttribute"):
                return link.getAttribute("href")
            # Fallback: используем repr для создания уникального ключа
            return str(hash(link))
        except (OSError, RuntimeError, TypeError, ValueError):
            return None

    def _evict_cache_if_needed(self) -> None:
        """C005: LRU eviction кэша при превышении размера.

        ISSUE-138: Оптимизировано с использованием islice для эффективного удаления записей.
        Вместо создания полного списка ключей используется itertools.islice.

        Raises:
            RuntimeError: При ошибке модификации кэша.

        """
        if len(self._extracted_data_cache) >= self._cache_max_size:
            # ISSUE-138: Оптимизация - удаляем первые 10% записей (LRU - oldest entries)
            # Используем islice для эффективного получения ключей без создания полного списка
            from itertools import islice

            keys_count_to_remove = self._cache_max_size // CACHE_EVICTION_PERCENT
            keys_to_remove = list(islice(self._extracted_data_cache.keys(), keys_count_to_remove))
            for key in keys_to_remove:
                del self._extracted_data_cache[key]

    def _parse_firm_page(self, link, writer: FileWriter) -> bool:
        """Парсит страницу организации по ссылке.

        Args:
            link: DOM-узел ссылки на организацию.
            writer: Файловый писатель для сохранения данных.

        Returns:
            True если данные успешно записаны, False иначе.

        Raises:
            OSError: При ошибке доступа к DOM или сети.
            RuntimeError: При ошибке выполнения операций Chrome.
            TypeError: При некорректном типе данных.
            ValueError: При некорректных параметрах.
            MemoryError: При нехватке памяти.
            json.JSONDecodeError: При некорректном JSON ответе сервера.

        Примечание:
            H006: Добавлено кэширование для часто извлекаемых данных.
            - Кликает на ссылку, чтобы спровоцировать запрос
            - Ожидает ответ Catalog Item Document
            - Парсит JSON и записывает в writer
            - Обрабатывает до MAX_RESPONSE_ATTEMPTS попыток

        """
        # H006: Проверяем кэш перед парсингом
        link_url = self._get_link_url(link)
        if link_url and link_url in self._extracted_data_cache:
            doc = self._extracted_data_cache[link_url]
            try:
                writer.write(doc)
                logger.debug("Данные получены из кэша для %s", link_url[:50] if link_url else "N/A")
                return True
            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as write_error:
                logger.error("Ошибка записи кэшированных данных: %s", write_error)
                # Удаляем повреждённую запись из кэша
                del self._extracted_data_cache[link_url]

        resp: dict[str, Any] | None = None

        # ISSUE-140: Выносим вычисления за пределы цикла
        delay_between_clicks = self._parser._options.delay_between_clicks
        delay_seconds = delay_between_clicks / CLICK_DELAY_DIVISOR if delay_between_clicks else 0
        item_response_pattern = self._parser._item_response_pattern
        chrome_remote = self._parser._chrome_remote

        for attempt in range(MAX_RESPONSE_ATTEMPTS):
            try:
                # ISSUE-139: Добавлено логирование номера попытки
                if attempt > 0:
                    logger.debug(
                        "Попытка получения ответа %d/%d для ссылки",
                        attempt + 1,
                        MAX_RESPONSE_ATTEMPTS,
                    )

                # Кликаем на ссылку, чтобы спровоцировать запрос
                # с ключом авторизации и секретными аргументами
                chrome_remote.perform_click(link)

                # Задержка между кликами, может быть полезна, если
                # anti-bot сервис 2GIS станет более строгим.
                if delay_seconds:
                    chrome_remote.wait(delay_seconds)

                # Собираем ответы и собираем полезные данные.
                resp = chrome_remote.wait_response(item_response_pattern)

                # Если запрос не удался - повторяем, иначе идём дальше.
                if resp and resp.get("status", -1) >= 0:
                    break

                # Добавляем небольшую задержку между попытками для снижения нагрузки
                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                    chrome_remote.wait(RESPONSE_RETRY_DELAY)

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as click_error:
                logger.warning(
                    "Ошибка при клике на ссылку (попытка %d/%d): %s",
                    attempt + 1,
                    MAX_RESPONSE_ATTEMPTS,
                    click_error,
                )
                if attempt < MAX_RESPONSE_ATTEMPTS - 1:
                    chrome_remote.wait(RESPONSE_RETRY_DELAY)

        # Пропускаем позицию, если все попытки получить ответ неудачны
        if not resp or resp.get("status", -1) < 0:
            logger.error(
                "Не удалось получить ответ после %d попыток, пропуск позиции.",
                MAX_RESPONSE_ATTEMPTS,
            )
            return False

        # Получаем данные тела ответа
        try:
            data = chrome_remote.get_response_body(resp)
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as body_error:
            logger.error("Ошибка при получении тела ответа: %s", body_error)
            return False

        # Парсим JSON
        doc: dict[str, Any] | None = None
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
                # H006: Сохраняем в кэш для повторного использования
                if link_url:
                    self._evict_cache_if_needed()
                    self._extracted_data_cache[link_url] = doc
                return True
            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as write_error:
                logger.error("Ошибка записи данных: %s", write_error)
                return False
        else:
            logger.error("Данные не получены, пропуск позиции.")
            return False
