"""
Модуль обработки данных для парсера 2GIS.

Предоставляет класс MainDataProcessor для обработки данных:
- Обработка пагинации и переходов между страницами
- Парсинг результатов поисковой выдачи
- Управление памятью и GC
- Обработка посещённых ссылок

Этот модуль выделен из main.py для разделения ответственности:
- MainPageParser: DOM операции и навигация
- MainDataExtractor: Извлечение данных
- MainDataProcessor: Обработка данных
"""

from __future__ import annotations

import gc
import threading
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, Tuple

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    PSUTIL_AVAILABLE = False

from parser_2gis.chrome.dom import DOMNode
from parser_2gis.logger import logger
from parser_2gis.parser.parsers.main_extractor import MainDataExtractor
from parser_2gis.parser.parsers.main_parser import (
    GET_UNIQUE_LINKS_TIMEOUT,
    MAX_LINK_ATTEMPTS,
    MAX_VISITED_LINKS_SIZE,
    MainPageParser,
)
from parser_2gis.utils.decorators import wait_until_finished

if TYPE_CHECKING:
    from parser_2gis.writer import FileWriter


class MainDataProcessor:
    """Класс для обработки данных парсинга 2GIS.

    Предоставляет функциональность для:
    - Обработки пагинации и переходов между страницами
    - Парсинга результатов поисковой выдачи
    - Управления памятью и GC
    - Обработки посещённых ссылок

    Attributes:
        parser: Экземпляр MainPageParser для доступа к браузеру.
        extractor: Экземпляр MainDataExtractor для извлечения данных.
    """

    def __init__(self, parser: "MainPageParser") -> None:
        """Инициализация процессора данных.

        Args:
            parser: Экземпляр MainPageParser.
        """
        self._parser = parser
        self._extractor = MainDataExtractor(parser)

    def _handle_pagination(
        self, current_page_number: int, walk_page_number: Optional[int]
    ) -> Tuple[int, bool]:
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
                available_pages = self._parser._get_available_pages()
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
        current_page_number_result = self._parser._go_page(next_page_number)
        if not current_page_number_result:
            logger.info("Достигнут конец результатов поиска")
            return next_page_number, False

        # Сбрасываем страницу назначения, если мы закончили переход к желаемой странице
        if walk_page_number is not None and walk_page_number <= current_page_number_result:
            walk_page_number = None

        return current_page_number_result, True

    def _parse_search_results(
        self,
        writer: "FileWriter",
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
            """Проверяет использование памяти и выполняет автоматическую оптимизацию."""
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
                        self._parser._options.memory_threshold,
                    )

                # Проверяем превышение порога
                if memory_mb > self._parser._options.memory_threshold:
                    logger.warning(
                        "Использование памяти %.1f МБ превышает порог %d МБ. "
                        "Выполняем автоматическую оптимизацию...",
                        memory_mb,
                        self._parser._options.memory_threshold,
                    )

                    # Оптимизация 3.1: OrderedDict автоматически управляет размером
                    # Удаляем старые записи при превышении max_visited_links
                    with visited_links_lock:
                        if len(visited_links) > max_visited_links:
                            # Вычисляем количество элементов для удаления (75%)
                            target_remove = int(len(visited_links) * 0.75)

                            if target_remove > 0:
                                # Удаляем старые элементы из начала OrderedDict
                                for _ in range(target_remove):
                                    visited_links.popitem(last=False)

                                logger.debug(
                                    "Очищено %d ссылок для освобождения памяти", target_remove
                                )

                    # Принудительный вызов GC
                    gc_collected = gc.collect()
                    logger.info(
                        "GC собрал %d объектов",
                        gc_collected,
                    )

                    # Очищаем кэш запросов Chrome если возможно
                    try:
                        self._parser._chrome_remote.clear_requests()
                        logger.debug("Очищен кэш запросов Chrome")
                    except (OSError, RuntimeError, TypeError, ValueError) as cache_error:
                        logger.debug("Ошибка при очистке кэша: %s", cache_error)

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as memory_error:
                logger.debug("Ошибка при проверке памяти: %s", memory_error)

        # Эта обёртка не необходима, но я хочу быть уверен,
        # что мы не собрали ссылки из старого DOM каким-то образом.
        @wait_until_finished(
            timeout=GET_UNIQUE_LINKS_TIMEOUT, throw_exception=False, poll_interval=0.01
        )
        def get_unique_links() -> Optional[list["DOMNode"]]:
            """Получает уникальные ссылки, которые ещё не были посещены."""
            try:
                links = self._parser._get_links()
                # Проверяем, что ссылки успешно получены
                if links is None:
                    return None

                # Optimization: use set comprehension for fast set creation
                link_hrefs = {
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
                    if len(visited_links) > max_visited_links:
                        overflow = len(visited_links) - max_visited_links
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

        # Максимальное количество итераций цикла для предотвращения бесконечного цикла
        MAX_TOTAL_ITERATIONS = MAX_LINK_ATTEMPTS * 2 + 10
        total_iterations = 0

        try:
            # Счётчик попыток получения ссылок для предотвращения бесконечного цикла
            link_attempt_count = 0

            while True:
                # Защита от бесконечного цикла по общему числу итераций
                total_iterations += 1
                if total_iterations > MAX_TOTAL_ITERATIONS:
                    logger.error(
                        "Достигнут лимит общих итераций цикла (%d). Прекращаем парсинг URL.",
                        MAX_TOTAL_ITERATIONS,
                    )
                    return

                # Ждём завершения всех 2GIS запросов
                try:
                    if not self._parser._wait_requests_finished():
                        logger.warning("Таймаут ожидания завершения запросов")
                except (OSError, RuntimeError, TypeError, ValueError) as wait_error:
                    logger.warning("Ошибка при ожидании запросов: %s", wait_error)

                # Собираем ссылки для клика
                links: list | None = get_unique_links()

                # Проверяем, что ссылки успешно получены
                if links is None:
                    consecutive_empty_pages += 1
                    link_attempt_count += 1
                    logger.warning(
                        "Не удалось получить ссылки, переходим к следующей странице. "
                        "(Пустых страниц подряд: %d/%d, Попыток: %d/%d, Итераций: %d/%d)",
                        consecutive_empty_pages,
                        self._parser._options.max_consecutive_empty_pages,
                        link_attempt_count,
                        MAX_LINK_ATTEMPTS,
                        total_iterations,
                        MAX_TOTAL_ITERATIONS,
                    )

                    # Если подряд слишком много пустых страниц - прерываем парсинг
                    if consecutive_empty_pages >= self._parser._options.max_consecutive_empty_pages:
                        logger.error(
                            "Достигнут лимит подряд пустых страниц (%d). Прекращаем парсинг URL.",
                            self._parser._options.max_consecutive_empty_pages,
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
                    # Ссылки успешно получены - сбрасываем счётчики
                    consecutive_empty_pages = 0
                    link_attempt_count = 0

                # Парсим страницу, если не идём к определённой странице
                if not walk_page_number:
                    # Счётчик ссылок для периодической очистки памяти
                    links_since_gc = 0

                    # Итерируемся по собранным ссылкам
                    for link in links:
                        # Парсим страницу организации
                        if self._extractor._parse_firm_page(link, writer):
                            collected_records += 1

                            # Проверяем достижение лимита после каждой успешной записи
                            if collected_records >= self._parser._options.max_records:
                                logger.info(
                                    "Спарсено максимально разрешенное количество записей с данного URL."
                                )
                                return

                        # Периодическая очистка памяти каждые 10 ссылок
                        links_since_gc += 1
                        if links_since_gc >= 10:
                            gc.collect()
                            links_since_gc = 0

                # Запускаем сборщик мусора и проверяем использование памяти
                if current_page_number % self._parser._options.gc_pages_interval == 0:
                    check_and_optimize_memory()

                    # Запускаем сборщик мусора, если включён
                    if self._parser._options.use_gc:
                        logger.debug("Запуск сборщика мусора.")
                        try:
                            self._parser._chrome_remote.execute_script('"gc" in window && window.gc()')
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
                try:
                    self._parser._chrome_remote.clear_requests()
                except (OSError, RuntimeError, TypeError, ValueError) as clear_error:
                    logger.debug("Ошибка при очистке запросов: %s", clear_error)

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            logger.error("Критическая ошибка при парсинге: %s", e, exc_info=True)
            raise
        finally:
            # Гарантируем очистку ресурсов
            try:
                self._parser._chrome_remote.clear_requests()
            except (OSError, RuntimeError, TypeError, ValueError) as e:
                logger.debug("Ошибка при очистке запросов: %s", e)
