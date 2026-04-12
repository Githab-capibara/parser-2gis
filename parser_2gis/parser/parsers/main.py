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

import random
import re
import time
from typing import TYPE_CHECKING, Any

from parser_2gis.constants import MAX_VISITED_LINKS_SIZE
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
        browser: BrowserService | None = None,
    ) -> None:
        """Инициализация основного парсера.

        Args:
            url: URL для парсинга.
            chrome_options: Опции Chrome.
            parser_options: Опции парсера.
            browser: Опциональный браузер.

        Raises:
            ValueError: Если chrome_options или parser_options некорректны.

        """
        # ISSUE-134: Валидация chrome_options и parser_options
        if chrome_options is None:
            raise ValueError("chrome_options не может быть None")
        if parser_options is None:
            raise ValueError("parser_options не может быть None")

        # Валидация url
        if not url or not isinstance(url, str):
            raise ValueError("url должен быть непустой строкой")

        self._options = parser_options
        self._url = url

        # Создаём основной парсер страниц
        self._page_parser = MainPageParser(
            url=url, chrome_options=chrome_options, parser_options=parser_options, browser=browser,
        )

        # Отмечаем, владеет ли парсер браузером (для корректного закрытия)
        # Если браузер передан извне — не закрываем его при close()
        self._owns_browser = browser is None

        # Создаём экстрактор данных
        self._data_extractor = MainDataExtractor(self._page_parser)

        # Создаём процессор данных
        self._data_processor = MainDataProcessor(self._page_parser)

    @property
    def _chrome_remote(self) -> BrowserService:
        """Делегирует доступ к ChromeRemote через page_parser.

        Предоставляет backward compatibility для дочерних классов
        (FirmParser, InBuildingParser), которые обращаются к _chrome_remote напрямую.
        """
        return self._page_parser._chrome_remote

    @property
    def _item_response_pattern(self) -> str:
        """Делегирует доступ к паттерну ответа через page_parser."""
        return self._page_parser._item_response_pattern

    def _wait_requests_finished(self) -> bool:
        """Делегирует проверку завершения запросов через page_parser."""
        return self._page_parser._wait_requests_finished()  # type: ignore[no-any-return]

    @staticmethod
    def url_pattern() -> str:
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
        from collections import deque

        # Начиная со страницы 6 и далее
        # 2GIS автоматически перенаправляет пользователя в начало (anti-bot защита).
        # Если в URL найден аргумент страницы, мы должны вручную перейти к ней сначала.

        url = re.sub(r"/page/\d+", "", self._url, flags=re.IGNORECASE)

        page_match = re.search(r"/page/(?P<page_number>\d+)", self._url, re.IGNORECASE)
        start_page = int(page_match.group("page_number")) if page_match else None

        # ISSUE-133: Используем deque с maxlen для автоматического LRU eviction
        # deque автоматически удаляет старые записи при превышении maxlen
        visited_links: deque[str] = deque(maxlen=MAX_VISITED_LINKS_SIZE)

        # Навигация к поисковой выдаче с retry logic и jitter
        max_retries = self._options.max_retries
        base_delay = self._options.retry_delay_base

        try:
            # ISSUE-131: Упрощение вложенности try-except через выделение навигации
            navigate_success = self._perform_navigation_with_retries(url, max_retries, base_delay)

            if not navigate_success:
                return

            # Валидация ответа документа
            document_response = self._page_parser._validate_document_response()
            if document_response is None:
                return

            # Парсинг результатов поиска
            # Передаём visited_links для управления памятью с eviction policy
            self._data_processor._parse_search_results(
                writer, start_page, visited_links, MAX_VISITED_LINKS_SIZE,
            )

        finally:
            # Гарантированная очистка ресурсов браузера при любом исходе
            self.close()

    def _perform_navigation_with_retries(
        self, url: str, max_retries: int, base_delay: float,
    ) -> bool:
        """Выполняет навигацию с повторными попытками.

        Args:
            url: URL для навигации.
            max_retries: Максимальное количество попыток.
            base_delay: Базовая задержка между попытками.

        Returns:
            True если навигация успешна, False иначе.

        """
        navigate_success = False

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

            except MemoryError as memory_error:
                # Критическая ошибка памяти - не повторяем
                logger.error("MemoryError при навигации по URL %s: %s", url, memory_error)
                return False

            except (OSError, RuntimeError) as system_error:
                # Системные ошибки - повторяем если разрешено
                if attempt < max_retries and self._options.retry_on_network_errors:
                    # Добавляем jitter для предотвращения thundering herd эффекта
                    jitter = random.uniform(0, 0.3)
                    delay = base_delay * (1.5**attempt) + jitter
                    logger.warning(
                        "Системная ошибка при навигации (попытка %d/%d): %s. "
                        "Повторная попытка через %.1f сек...",
                        attempt + 1,
                        max_retries,
                        system_error,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    # Исчерпаны все попытки
                    logger.error("Таймаут навигации по URL %s: %s", url, system_error)
                    return False

            except (TypeError, ValueError) as validation_error:
                # Ошибки валидации - не повторяем, это программная ошибка
                logger.error("Ошибка валидации при навигации по URL %s: %s", url, validation_error)
                return False

        return navigate_success

    def close(self) -> None:
        """Закрывает браузер и освобождает ресурсы.

        Закрывает только если браузер был создан внутри парсера
        (не был передан извне через browser параметр).
        """
        if self._owns_browser:
            self._page_parser._chrome_remote.stop()

    def __enter__(self) -> MainParser:
        """Контекстный менеджер: вход.

        Запускает браузер через _page_parser.

        Returns:
            Экземпляр MainParser.

        """
        self._page_parser.__enter__()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Контекстный менеджер: выход.

        Закрывает браузер через _page_parser.

        Args:
            exc_info: Информация об исключении (если было).

        """
        self.close()

    def __repr__(self) -> str:
        """Возвращает строковое представление парсера для отладки.

        Returns:
            Строка с именем класса и основными параметрами.

        """
        classname = self.__class__.__name__
        return (
            f"{classname}(parser_options={self._options!r}, "
            f"chrome_remote={self._page_parser._chrome_remote!r}, "
            f"url={self._url!r})"
        )
