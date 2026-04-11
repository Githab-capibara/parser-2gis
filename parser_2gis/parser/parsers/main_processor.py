"""Модуль обработки данных для парсера 2GIS.

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
import os
import threading
from collections import deque
from typing import TYPE_CHECKING, Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

from parser_2gis.chrome.dom import DOMNode
from parser_2gis.logger import logger
from parser_2gis.parser.parsers.main_extractor import MainDataExtractor
from parser_2gis.parser.parsers.main_parser import (
    GET_UNIQUE_LINKS_TIMEOUT,
    MAX_LINK_ATTEMPTS,
    MAX_TOTAL_ITERATIONS,
    MAX_VISITED_LINKS_SIZE,
    MainPageParser,
)
from parser_2gis.utils.decorators import wait_until_finished

# =============================================================================
# КОНСТАНТЫ МОДУЛЯ
# =============================================================================

# Коэффициент для очистки памяти при превышении порога
# (можно переопределить через PARSER_MEMORY_CLEANUP_FRACTION)
MEMORY_CLEANUP_FRACTION: float = float(
    os.environ.get("PARSER_MEMORY_CLEANUP_FRACTION", "0.75")
)

# Периодичность проверки памяти (каждые 10 вызовов)
MEMORY_CHECK_INTERVAL: int = 10

# Периодичность очистки visited_links (каждые 5 вызовов)
VISITED_LINKS_CLEANUP_INTERVAL: int = 5

# Коэффициент для агрессивной очистки visited_links (50%)
VISITED_LINKS_CLEANUP_FRACTION: float = 0.5

# Количество ссылок для вызова GC
GC_LINKS_INTERVAL: int = 10


def check_and_optimize_memory(
    process_cache: Any,
    parser: MainPageParser,
    visited_links: deque[str],
    visited_links_lock: threading.RLock,
    max_visited_links: int,
    memory_check_counter: int,
    visited_links_cleanup_counter: int,
) -> tuple[int, int]:
    """Проверяет использование памяти и выполняет автоматическую оптимизацию.

    C5: Добавлена периодическая принудительная очистка visited_links.

    Args:
        process_cache: Кэшированный объект psutil.Process.
        parser: Экземпляр MainPageParser для доступа к опциям и Chrome.
        visited_links: deque с посещёнными ссылками.
        visited_links_lock: Блокировка для visited_links.
        max_visited_links: Максимальный размер visited_links.
        memory_check_counter: Счётчик проверок памяти.
        visited_links_cleanup_counter: Счётчик очисток visited_links.

    Returns:
        Кортеж (memory_check_counter, visited_links_cleanup_counter).

    """
    memory_check_counter += 1
    visited_links_cleanup_counter += 1

    # Проверяем доступность psutil
    if not PSUTIL_AVAILABLE or process_cache is None:
        logger.debug("psutil не доступен - пропускаем проверку памяти")
        return memory_check_counter, visited_links_cleanup_counter

    try:
        # Получаем текущее использование памяти процесса в МБ
        memory_info = process_cache.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # Конвертируем в МБ

        # Мониторинг использования памяти в реальном времени
        if memory_check_counter % MEMORY_CHECK_INTERVAL == 0:
            logger.debug(
                "Использование памяти: %.1f МБ (порог: %d МБ)",
                memory_mb,
                parser._parser_options.memory_threshold,
            )

        # Проверяем превышение порога
        if memory_mb > parser._parser_options.memory_threshold:
            logger.warning(
                "Использование памяти %.1f МБ превышает порог %d МБ. "
                "Выполняем автоматическую оптимизацию...",
                memory_mb,
                parser._parser_options.memory_threshold,
            )

            with visited_links_lock:
                if len(visited_links) > max_visited_links // 2:
                    target_remove = int(len(visited_links) * MEMORY_CLEANUP_FRACTION)

                    if target_remove > 0:
                        for _ in range(target_remove):
                            visited_links.popleft()

                        logger.debug("Очищено %d ссылок для освобождения памяти", target_remove)

        # Принудительный вызов GC
        gc_collected = gc.collect()
        logger.info("GC собрал %d объектов", gc_collected)

        # Очищаем кэш запросов Chrome если возможно
        try:
            parser._chrome_remote.clear_requests()
            logger.debug("Очищен кэш запросов Chrome")
        except (OSError, RuntimeError, TypeError, ValueError) as cache_error:
            logger.debug("Ошибка при очистке кэша: %s", cache_error)

        # C5: Периодическая принудительная очистка visited_links
        if visited_links_cleanup_counter >= VISITED_LINKS_CLEANUP_INTERVAL:
            with visited_links_lock:
                if len(visited_links) > max_visited_links * VISITED_LINKS_CLEANUP_FRACTION:
                    target_remove = int(len(visited_links) * VISITED_LINKS_CLEANUP_FRACTION)
                    if target_remove > 0:
                        for _ in range(target_remove):
                            visited_links.popleft()
                        logger.debug(
                            "C5: Периодическая очистка visited_links: удалено %d ссылок",
                            target_remove,
                        )
            visited_links_cleanup_counter = 0

    except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as memory_error:
        logger.debug("Ошибка при проверке памяти: %s", memory_error)

    return memory_check_counter, visited_links_cleanup_counter


@wait_until_finished(timeout=GET_UNIQUE_LINKS_TIMEOUT, throw_exception=False, poll_interval=0.01)
def get_unique_links(
    parser: MainPageParser,
    visited_links: deque[str],
    visited_links_lock: threading.RLock,
    visited_set: set[str],
    max_visited_links: int,
) -> list[DOMNode] | None:
    """Получает уникальные ссылки, которые ещё не были посещены.

    ISSUE-150: Оптимизация алгоритма проверки уникальности ссылок.
    Вместо set.intersection() в цикле используется set.difference()
    для однократного получения уникальных ссылок.

    Args:
        parser: Экземпляр MainPageParser для получения ссылок.
        visited_links: deque с посещёнными ссылками.
        visited_links_lock: Блокировка для visited_links.
        visited_set: Кэшированный set посещённых href.
        max_visited_links: Максимальный размер visited_links.

    Returns:
        Список уникальных DOM-узлов ссылок или None при ошибке.

    """
    try:
        links = parser._get_links()
        # Проверяем, что ссылки успешно получены
        if links is None:
            return None

        # Optimization: use set comprehension for fast set creation
        link_hrefs = {link.attributes["href"] for link in links if "href" in link.attributes}

        with visited_links_lock:
            # P0-6: Оптимизация — используем кэшированный set вместо создания нового
            new_link_hrefs = link_hrefs - visited_set

            # Если нет новых ссылок - возвращаем None
            if not new_link_hrefs:
                return None

            # Обновляем кэшированный set инкрементально
            visited_set.update(new_link_hrefs)

            # ISSUE-133: batch add links to deque
            visited_links.extend(new_link_hrefs)

            # deque автоматически удаляет старые ссылки при превышении maxlen
            if len(visited_links) == max_visited_links:
                logger.debug(
                    "LRU eviction: deque заполнен до максимума (%d ссылок)", max_visited_links
                )

            # Возвращаем только ссылки с новыми href
            return [link for link in links if link.attributes.get("href") in new_link_hrefs]

    except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
        logger.error("Ошибка при получении уникальных ссылок: %s", e)
        return None


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

    def __init__(self, parser: MainPageParser) -> None:
        """Инициализация процессора данных.

        Args:
            parser: Экземпляр MainPageParser.

        """
        self._parser = parser
        self._extractor = MainDataExtractor(parser)
        # P0-6: Кэшированный set для инкрементального обновления уникальности ссылок
        self._visited_set: set[str] = set()

    def _handle_pagination(
        self, current_page_number: int, walk_page_number: int | None
    ) -> tuple[int, bool]:
        """Обрабатывает пагинацию и переход на следующую страницу.

        ISSUE-148: Добавлен docstring с описанием возвращаемых значений.

        Args:
            current_page_number: Текущий номер страницы.
            walk_page_number: Целевой номер страницы для перехода (или None).

        Returns:
            Кортеж (next_page_number, should_continue):
            - next_page_number: Номер следующей страницы для перехода
            - should_continue: True если есть следующие страницы для парсинга,
                               False если достигнут конец результатов

        Raises:
            OSError: При ошибке доступа к DOM.
            RuntimeError: При ошибке выполнения операций Chrome.
            TypeError: При некорректном типе данных.
            ValueError: При некорректных параметрах.
            MemoryError: При нехватке памяти.

        Примечание:
            - Вычисляет следующую страницу на основе доступных
            - Обрабатывает режим перехода к определённой странице
            - Возвращает False если достигнут конец результатов
            - Использует min() с key функцией для нахождения ближайшей страницы

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

    def _check_record_limit(self, collected_records: int) -> bool:
        """Проверяет достижение лимита записей.

        Args:
            collected_records: Текущее количество собранных записей.

        Returns:
            True если лимит достигнут.

        """
        if collected_records >= self._parser._parser_options.max_records:
            logger.info("Достигнут лимит записей (%d), завершаем парсинг", collected_records)
            return True
        return False

    def _parse_links_batch(self, links: list, writer: FileWriter, collected_records: int) -> int:
        """Парсит пакет ссылок и возвращает обновлённый счётчик записей.

        Args:
            links: Список ссылок для парсинга.
            writer: Файловый писатель.
            collected_records: Текущее количество записей.

        Returns:
            Обновлённое количество собранных записей.

        """
        links_since_gc = 0

        for link in links:
            if self._check_record_limit(collected_records):
                return collected_records

            if self._extractor._parse_firm_page(link, writer):
                collected_records += 1
                if collected_records >= self._parser._parser_options.max_records:
                    logger.info(
                        "Спарсено максимально разрешенное количество записей с данного URL."
                    )
                    return collected_records

            links_since_gc += 1
            if links_since_gc >= GC_LINKS_INTERVAL:
                gc.collect()
                links_since_gc = 0

        return collected_records

    def _handle_empty_page(
        self,
        consecutive_empty_pages: int,
        link_attempt_count: int,
        total_iterations: int,
        max_total_iterations: int,
    ) -> bool:
        """Обрабатывает случай получения пустой страницы.

        Args:
            consecutive_empty_pages: Счётчик пустых страниц подряд.
            link_attempt_count: Счётчик попыток получения ссылок.
            total_iterations: Общее число итераций.
            max_total_iterations: Максимум итераций.

        Returns:
            True если нужно прервать парсинг.

        """
        logger.warning(
            "Не удалось получить ссылки, переходим к следующей странице. "
            "(Пустых страниц подряд: %d/%d, Попыток: %d/%d, Итераций: %d/%d)",
            consecutive_empty_pages,
            self._parser._parser_options.max_consecutive_empty_pages,
            link_attempt_count,
            MAX_LINK_ATTEMPTS,
            total_iterations,
            max_total_iterations,
        )

        if consecutive_empty_pages >= self._parser._parser_options.max_consecutive_empty_pages:
            logger.error(
                "Достигнут лимит подряд пустых страниц (%d). Прекращаем парсинг URL.",
                self._parser._parser_options.max_consecutive_empty_pages,
            )
            return True

        if link_attempt_count >= MAX_LINK_ATTEMPTS:
            logger.error(
                "Достигнут лимит попыток получения ссылок (%d). Прекращаем парсинг URL.",
                MAX_LINK_ATTEMPTS,
            )
            return True

        return False

    def _parse_search_results(
        self,
        writer: FileWriter,
        walk_page_number: int | None,
        visited_links: deque[str] | None = None,
        max_visited_links: int = MAX_VISITED_LINKS_SIZE,
    ) -> None:
        """Парсит результаты поисковой выдачи.

        Args:
            writer: Файловый писатель для сохранения данных.
            walk_page_number: Целевой номер страницы для перехода (или None).
            visited_links: deque для хранения посещённых ссылок (опционально).
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
        # ISSUE-133: Используем deque с maxlen для автоматического LRU eviction
        # deque автоматически удаляет старые записи при превышении maxlen
        if visited_links is None:
            visited_links = deque(maxlen=max_visited_links)
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

        # C5: Счётчик для периодической принудительной очистки visited_links
        visited_links_cleanup_counter = 0

        current_page_number = 1

        # Максимальное количество итераций цикла для предотвращения бесконечного цикла
        max_total_iterations = MAX_LINK_ATTEMPTS * 2 + 10
        total_iterations = 0

        try:
            # Счётчик попыток получения ссылок для предотвращения бесконечного цикла
            link_attempt_count = 0

            while True:
                # Защита от бесконечного цикла по общему числу итераций
                total_iterations += 1
                if total_iterations > max_total_iterations:
                    logger.error(
                        "Достигнут лимит общих итераций цикла (%d). Прекращаем парсинг URL.",
                        max_total_iterations,
                    )
                    return

                # Ждём завершения всех 2GIS запросов
                try:
                    if not self._parser._wait_requests_finished():
                        logger.warning("Таймаут ожидания завершения запросов")
                except (OSError, RuntimeError, TypeError, ValueError) as wait_error:
                    logger.warning("Ошибка при ожидании запросов: %s", wait_error)

                # Собираем ссылки для клика
                links: list | None = get_unique_links(
                    parser=self._parser,
                    visited_links=visited_links,
                    visited_links_lock=visited_links_lock,
                    visited_set=self._visited_set,
                    max_visited_links=max_visited_links,
                )

                # Проверяем, что ссылки успешно получены
                if links is None:
                    consecutive_empty_pages += 1
                    link_attempt_count += 1
                    if self._handle_empty_page(
                        consecutive_empty_pages,
                        link_attempt_count,
                        total_iterations,
                        MAX_TOTAL_ITERATIONS,
                    ):
                        return

                    # Переходим к следующей странице
                    next_page, should_continue = self._handle_pagination(
                        current_page_number, walk_page_number
                    )
                    if not should_continue:
                        return
                    current_page_number = next_page
                    continue
                # Ссылки успешно получены - сбрасываем счётчики
                consecutive_empty_pages = 0
                link_attempt_count = 0

                # Парсим страницу, если не идём к определённой странице
                if not walk_page_number:
                    # H015: Ранний выход при достижении лимита записей
                    if self._check_record_limit(collected_records):
                        return

                    # Итерируемся по собранным ссылкам
                    collected_records = self._parse_links_batch(
                        links=links, writer=writer, collected_records=collected_records
                    )
                    if self._check_record_limit(collected_records):
                        return

                # Запускаем сборщик мусора и проверяем использование памяти
                if current_page_number % self._parser._parser_options.gc_pages_interval == 0:
                    memory_check_counter, visited_links_cleanup_counter = check_and_optimize_memory(
                        process_cache=_process_cache,
                        parser=self._parser,
                        visited_links=visited_links,
                        visited_links_lock=visited_links_lock,
                        max_visited_links=max_visited_links,
                        memory_check_counter=memory_check_counter,
                        visited_links_cleanup_counter=visited_links_cleanup_counter,
                    )

                    # Запускаем сборщик мусора, если включён
                    if self._parser._parser_options.use_gc:
                        logger.debug("Запуск сборщика мусора.")
                        try:
                            self._parser._chrome_remote.execute_script(
                                '"gc" in window && window.gc()'
                            )
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
