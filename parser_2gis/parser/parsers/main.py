"""Основной парсер для поисковой выдачи 2GIS.

Предоставляет класс MainParser для парсинга поисковых результатов:
- Переход по страницам выдачи
- Извлечение ссылок на организации
- Парсинг данных через API Catalog Item
- Поддержка пагинации
- Оптимизация памяти и GC

Этот модуль использует композицию для разделения ответственности:
- MainPageParser: DOM операции и навигация
- MainDataExtractor: Извлечение данных
- MainDataProcessor: Обработка данных и пагинация
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from parser_2gis.logger import logger
from parser_2gis.parser.parsers.main_extractor import MainDataExtractor
from parser_2gis.parser.parsers.main_parser import MainPageParser
from parser_2gis.parser.parsers.main_processor import MainDataProcessor
from parser_2gis.protocols import BrowserService

if TYPE_CHECKING:
    from parser_2gis.chrome import ChromeOptions
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.writer import FileWriter


class MainParser:
    """Основной парсер для поисковой выдачи 2GIS.

    Использует композицию для делегирования задач специализированным классам:
    - _page_parser: MainPageParser для DOM операций и навигации
    - _data_extractor: MainDataExtractor для извлечения данных
    - _data_processor: MainDataProcessor для обработки данных и пагинации

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
        """Инициализация основного парсера.

        Args:
            url: URL для парсинга.
            chrome_options: Опции Chrome.
            parser_options: Опции парсера.
            browser: Опциональный браузер.
        """
        self._options = parser_options
        self._url = url

        # Создаём основной парсер страниц
        self._page_parser = MainPageParser(
            url=url, chrome_options=chrome_options, parser_options=parser_options, browser=browser
        )

        # Создаём экстрактор данных
        self._data_extractor = MainDataExtractor(self._page_parser)

        # Создаём процессор данных
        self._data_processor = MainDataProcessor(self._page_parser)

    @staticmethod
    def url_pattern():
        """URL-паттерн для парсера."""
        return r"https?://2gis\.[^/]+/[^/]+/search/.*"

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
        from collections import OrderedDict

        # Начиная со страницы 6 и далее
        # 2GIS автоматически перенаправляет пользователя в начало (anti-bot защита).
        # Если в URL найден аргумент страницы, мы должны вручную перейти к ней сначала.

        url = re.sub(r"/page/\d+", "", self._url, re.I)

        page_match = re.search(r"/page/(?P<page_number>\d+)", self._url, re.I)
        walk_page_number = int(page_match.group("page_number")) if page_match else None

        # Оптимизация: используем OrderedDict для эффективного управления памятью
        # посещённых ссылок с автоматическим удалением старых записей (LRU eviction)
        visited_links: OrderedDict[str, None] = OrderedDict()
        max_visited_links = 10000  # MAX_VISITED_LINKS_SIZE

        # Навигация к поисковой выдаче с retry logic и jitter
        max_retries = self._options.max_retries
        base_delay = self._options.retry_delay_base

        navigate_success = False
        try:
            for attempt in range(max_retries + 1):
                try:
                    # Первая попытка или повторная
                    if attempt > 0:
                        logger.info(
                            "Повторная попытка навигации (%d/%d) для URL: %s",
                            attempt,
                            max_retries,
                            url,
                        )

                    self._page_parser._navigate_to_search(url)
                    navigate_success = True
                    break

                except (
                    OSError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                    MemoryError,
                ) as navigate_error:
                    if attempt < max_retries and self._options.retry_on_network_errors:
                        # Добавляем jitter для предотвращения thundering herd эффекта
                        # Формула: base_delay * (1.5 ** attempt) + random.uniform(0, 0.3)
                        import random

                        jitter = random.uniform(0, 0.3)
                        delay = base_delay * (1.5**attempt) + jitter
                        logger.warning(
                            "Ошибка при навигации (попытка %d/%d): %s. "
                            "Повторная попытка через %.1f сек...",
                            attempt + 1,
                            max_retries,
                            navigate_error,
                            delay,
                        )
                        import time

                        time.sleep(delay)
                    else:
                        # Исчерпаны все попытки
                        logger.error("Таймаут навигации по URL %s: %s", url, navigate_error)
                        return

            # Если навигация не удалась - выходим
            if not navigate_success:
                return

            # Валидация ответа документа
            document_response = self._page_parser._validate_document_response()
            if document_response is None:
                return

            # Парсинг результатов поиска
            # Передаём visited_links для управления памятью с eviction policy
            self._data_processor._parse_search_results(
                writer, walk_page_number, visited_links, max_visited_links
            )

        finally:
            # Гарантированная очистка ресурсов браузера при любом исходе
            self.close()

    def close(self) -> None:
        """Закрывает браузер и освобождает ресурсы.

        Закрывает только если браузер был создан внутри парсера
        (не был передан извне через browser параметр).
        """
        if hasattr(self._page_parser, "_owns_browser") and self._page_parser._owns_browser:
            self._page_parser._chrome_remote.stop()

    def __enter__(self) -> "MainParser":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return (
            f"{classname}(parser_options={self._options!r}, "
            f"chrome_remote={self._page_parser._chrome_remote!r}, "
            f"url={self._url!r})"
        )
