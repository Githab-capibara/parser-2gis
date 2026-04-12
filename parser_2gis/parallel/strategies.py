"""Модуль стратегий парсинга для параллельного парсинга.

Предоставляет классы стратегий для:
- ParseStrategy - стратегия парсинга URL
- UrlGenerationStrategy - стратегия генерации URL
- MemoryCheckStrategy - стратегия проверки памяти

ISSUE-002: Выделено из ParallelCityParser для соблюдения SRP.
ISSUE-030: Parser и Writer принимаются через factory callable, а не создаются внутри.
ISSUE-040: MemoryMonitor принимается через протокол вместо прямого импорта.
"""

from __future__ import annotations

import gc
import os
import shutil
import threading
import time
import uuid
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import TYPE_CHECKING, Any

from parser_2gis.constants import DEFAULT_TIMEOUT
from parser_2gis.delay_utils import apply_startup_delay
from parser_2gis.logger.logger import logger
from parser_2gis.parallel.cleanup_utils import cleanup_temp_file
from parser_2gis.parallel.protocols import MemoryMonitorProtocol
from parser_2gis.protocols import UrlGeneratorProtocol as UrlGeneratorProtocolBase
from parser_2gis.utils.temp_file_manager import temp_file_manager
from parser_2gis.utils.url_utils import generate_category_url

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

# Type aliases
type ParserResult = tuple[bool, str]  # (success, message)
type UrlTuple = tuple[str, str, str]  # (url, category_name, city_name)

# Константы
MEMORY_THRESHOLD_BYTES: int = 100 * 1024 * 1024  # 100MB порог для проверки памяти
DEFAULT_MAX_ATTEMPTS: int = 3
"""Максимальное количество попыток по умолчанию."""

DEFAULT_PARSE_MAX_RETRIES: int = 10
"""Максимальное количество повторных попыток инициализации парсера."""

DEFAULT_PARSE_RETRY_DELAY: float = 5.0
"""Задержка между повторными попытками инициализации парсера (секунды)."""


# =============================================================================
# PROTOCOLS FOR FACTORY INJECTION (ISSUE-030, ISSUE-040)
# =============================================================================

# Type aliases для factory callable
ParserFactory = Callable[[str, Any, Any], Any]
WriterFactory = Callable[[str, str, Any], Any]


class UrlGenerationStrategy(UrlGeneratorProtocolBase):
    """Стратегия генерации URL для парсинга.

    Отвечает за генерацию URL из городов и категорий.
    Поддерживает lazy generation для экономии памяти.

    ISSUE 074, 080: Реализует протокол UrlGeneratorProtocol.
    """

    def __init__(
        self, cities: list[dict[str, Any]], categories: list[dict[str, Any]], stats_lock: threading.RLock,
    ) -> None:
        """Инициализирует стратегию генерации URL.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            stats_lock: Блокировка для защиты статистики.

        """
        self.cities = cities
        self.categories = categories
        self._stats_lock = stats_lock

    def generate_all_urls(self, stats: dict[str, Any] | None = None) -> list[UrlTuple]:
        """Генерирует все URL для парсинга.

        Args:
            stats: Словарь статистики для обновления (опционально).

        Returns:
            Список кортежей (url, category_name, city_name).

        """
        all_urls = list(self.generate_all_urls_lazy())

        if stats is not None:
            with self._stats_lock:
                stats["total"] = len(all_urls)

        logger.info("Сгенерировано %d URL для парсинга", len(all_urls))
        return all_urls

    def generate_all_urls_lazy(self) -> Generator[UrlTuple, None, None]:
        """Генератор URL для парсинга (lazy loading).

        Yields:
            Кортеж (url, category_name, city_name).

        """
        for city in self.cities:
            for category in self.categories:
                try:
                    url = generate_category_url(city, category)
                    yield (url, category["name"], city["name"])
                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    logger.error(
                        f"Ошибка генерации URL для {city['name']} - {category['name']}: {e}",
                    )
                    continue


class MemoryCheckStrategy:
    """Стратегия проверки доступной памяти.

    Отвечает за мониторинг памяти и принятие решения о возможности парсинга.

    ISSUE-040: MemoryMonitor принимается через протокол вместо прямого импорта.
    """

    def __init__(
        self, memory_monitor: MemoryMonitorProtocol | None = None, memory_threshold_mb: int = 100,
    ) -> None:
        """Инициализирует стратегию проверки памяти.

        Args:
            memory_monitor: Экземпляр мониторинга памяти (протокол).
            memory_threshold_mb: Порог минимальной доступной памяти в MB.

        """
        # ISSUE-040: Ленивый импорт если не передан через DI
        if memory_monitor is None:
            from parser_2gis.infrastructure import MemoryMonitor

            self._memory_monitor: MemoryMonitorProtocol = MemoryMonitor()
        else:
            self._memory_monitor = memory_monitor
        self._memory_threshold_mb = memory_threshold_mb

    def check_memory(self) -> tuple[bool, int]:
        """Проверяет доступную память.

        Returns:
            Кортеж (is_enough, available_mb):
            - is_enough: True если памяти достаточно
            - available_mb: Доступная память в MB

        """
        available_memory = self._memory_monitor.get_available_memory()
        available_mb = available_memory // (1024 * 1024)
        is_enough = available_memory >= (self._memory_threshold_mb * 1024 * 1024)

        return is_enough, available_mb

    def is_memory_low(self) -> bool:
        """Проверяет, является ли доступная память низкой.

        Returns:
            True если память ниже порога.

        """
        available_mb = self._memory_monitor.get_available_memory() // (1024 * 1024)
        return available_mb < self._memory_threshold_mb


class ParseStrategy:
    """Стратегия парсинга URL.

    Отвечает за:
    - Проверку памяти перед парсингом
    - Создание временных файлов
    - Выполнение парсинга с таймаутом
    - Обработку ошибок и очистку ресурсов

    ISSUE-002: Выделено из ParallelCityParser для соблюдения SRP.
    ISSUE-030: Parser и Writer фабрики принимаются через конструктор.
    ISSUE-040: MemoryMonitor через протокол.
    """

    def __init__(
        self,
        output_dir: Path,
        config: Configuration,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        browser_semaphore: threading.BoundedSemaphore | None = None,
        stats: dict[str, Any] | None = None,
        stats_lock: threading.RLock | None = None,
        max_retries: int = DEFAULT_PARSE_MAX_RETRIES,
        retry_delay: float = DEFAULT_PARSE_RETRY_DELAY,
        parser_factory: ParserFactory | None = None,
        writer_factory: WriterFactory | None = None,
        memory_monitor: MemoryMonitorProtocol | None = None,
    ) -> None:
        """Инициализирует стратегию парсинга.

        Args:
            output_dir: Директория для сохранения результатов.
            config: Конфигурация парсера.
            timeout_per_url: Таймаут на один URL в секундах.
            browser_semaphore: Семафор для контроля браузеров.
            stats: Словарь статистики.
            stats_lock: Блокировка для защиты статистики.
            max_retries: Максимальное количество попыток инициализации парсера.
            retry_delay: Начальная задержка между попытками (секунды).
            parser_factory: Фабрика для создания парсеров (ISSUE-030).
            writer_factory: Фабрика для создания writer'ов (ISSUE-030).
            memory_monitor: Мониторинг памяти через протокол (ISSUE-040).

        """
        self.output_dir = output_dir
        self.config = config
        self.timeout_per_url = timeout_per_url
        self._browser_semaphore = browser_semaphore
        self._stats = stats or {}
        self._stats_lock = stats_lock or threading.RLock()
        # ISSUE-040: MemoryMonitor через протокол
        self._memory_strategy = MemoryCheckStrategy(memory_monitor=memory_monitor)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        # ISSUE-030: Фабрики для создания parser и writer
        self._parser_factory = parser_factory
        self._writer_factory = writer_factory

    def _log(self, message: str, level: str = "info") -> None:
        """Логгирует сообщение."""
        log_func = getattr(logger, level)
        log_func(message)

    def _create_temp_filename(self, safe_city: str, safe_category: str) -> tuple[str, Path]:
        """Создаёт уникальное имя временного файла.

        Args:
            safe_city: Безопасное имя города.
            safe_category: Безопасное имя категории.

        Returns:
            Кортеж (temp_filename, temp_filepath).

        """
        timestamp = str(int(time.time() * 1000000))[-10:]
        temp_filename = (
            f"{safe_city}_{safe_category}_{os.getpid()}_{timestamp}_{uuid.uuid4().hex[:8]}.tmp"
        )
        temp_filepath = self.output_dir / temp_filename
        return temp_filename, temp_filepath

    def _ensure_unique_temp_file(
        self, temp_filepath: Path, max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> Path:
        """Гарантирует создание уникального временного файла.

        Args:
            temp_filepath: Путь к временному файлу.
            max_attempts: Максимальное количество попыток.

        Returns:
            Путь к созданному файлу.

        Raises:
            FileExistsError: Если не удалось создать уникальный файл.

        """
        base_path = temp_filepath.parent
        base_name = temp_filepath.stem
        extension = temp_filepath.suffix

        for attempt in range(max_attempts):
            try:
                # Атомарное создание файла
                fd = os.open(str(temp_filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644)
                os.close(fd)
                logger.log(5, "Временный файл атомарно создан: %s", temp_filepath.name)
                return temp_filepath
            except FileExistsError:
                if attempt < max_attempts - 1:
                    # Генерируем новое имя
                    timestamp = str(int(time.time() * 1000000))[-10:]
                    new_name = f"{base_name}_{timestamp}_{uuid.uuid4().hex[:8]}{extension}"
                    temp_filepath = base_path / new_name
                else:
                    logger.error(
                        "Не удалось создать уникальный временный файл после %d попыток",
                        max_attempts,
                    )
                    raise
            except OSError as e:
                if attempt < max_attempts - 1:
                    timestamp = str(int(time.time() * 1000000))[-10:]
                    new_name = f"{base_name}_{timestamp}_{uuid.uuid4().hex[:8]}{extension}"
                    temp_filepath = base_path / new_name
                else:
                    logger.error("Не удалось создать временный файл: %s", e)
                    raise

        return temp_filepath

    def _cleanup_temp_file(self, temp_filepath: Path) -> None:
        """Очищает временный файл."""
        # #63: Использует общую утилиту из cleanup_utils.py
        cleanup_temp_file(temp_filepath, description="Временный файл удалён")

    def _update_stats(self, *, success: bool) -> None:
        """Обновляет статистику."""
        with self._stats_lock:
            if success:
                self._stats["success"] += 1
            else:
                self._stats["failed"] += 1

    def parse_single_url(
        self,
        url: str,
        category_name: str,
        city_name: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_event: threading.Event | None = None,
        parser: Any | None = None,
        writer: Any | None = None,
    ) -> ParserResult:
        """Парсит один URL и сохраняет результат в файл.

        ISSUE 067: parser и writer могут быть переданы как параметры
        вместо вызова get_parser()/get_writer() напрямую.

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обновления прогресса.
            cancel_event: Событие отмены.
            parser: Готовый экземпляр парсера (ISSUE 067).
            writer: Готовый экземпляр писателя (ISSUE 067).

        Returns:
            Кортеж (success, message).

        """
        # Проверяем флаг отмены
        if cancel_event is not None and cancel_event.is_set():
            return False, "Отменено пользователем"

        # Проверяем память
        is_enough, available_mb = self._memory_strategy.check_memory()
        if not is_enough:
            logger.warning(
                "Low memory (%dMB), skipping %s - %s", available_mb, city_name, category_name,
            )
            return False, "Недостаточно памяти"

        # Формируем имя файла
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        # Создаём временный файл
        temp_filename, temp_filepath = self._create_temp_filename(safe_city, safe_category)
        temp_filepath = self._ensure_unique_temp_file(temp_filepath)

        def do_parse() -> ParserResult:
            """Выполняет парсинг внутри потока."""
            self._log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )

            # Rate limiting
            # #65-#67: Использует общую утилиту apply_startup_delay
            apply_startup_delay(self.config, phase="initial", log_func=self._log)

            # Приобретаем семафор
            semaphore_acquired = False
            if self._browser_semaphore:
                self._browser_semaphore.acquire()
                semaphore_acquired = True

            # ISSUE 067: Используем переданные parser и writer если они есть
            local_parser = parser
            local_writer = writer

            try:
                # Локальные импорты
                from parser_2gis.chrome.exceptions import ChromeException

                # Дополнительная задержка запуска
                # #65-#67: Использует общую утилиту apply_startup_delay
                apply_startup_delay(self.config, phase="launch", log_func=self._log)

                # Создаём parser и writer если не переданы
                if local_parser is None or local_writer is None:
                    max_retries = self._max_retries
                    retry_delay = self._retry_delay

                    for attempt in range(max_retries):
                        try:
                            if local_writer is None:
                                if self._writer_factory:
                                    local_writer = self._writer_factory(
                                        str(temp_filepath), "csv", self.config.writer,
                                    )
                                else:
                                    from parser_2gis.writer import get_writer

                                    local_writer = get_writer(
                                        str(temp_filepath), "csv", self.config.writer,
                                    )

                            if local_parser is None:
                                if self._parser_factory:
                                    local_parser = self._parser_factory(
                                        url, self.config.chrome, self.config.parser,
                                    )
                                else:
                                    from parser_2gis.parser import get_parser

                                    local_parser = get_parser(
                                        url,
                                        chrome_options=self.config.chrome,
                                        parser_options=self.config.parser,
                                    )
                            break
                        except ChromeException as chrome_error:
                            if attempt < max_retries - 1:
                                self._log(
                                    f"Попытка {attempt + 1}/{max_retries} не удалась: "
                                    f"{chrome_error}. "
                                    f"Повтор через {retry_delay:.1f} сек...",
                                    "warning",
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2
                            else:
                                raise

                # Выполняем парсинг
                try:
                    with local_parser, local_writer:
                        local_parser.parse(local_writer)
                except MemoryError as memory_error:
                    logger.error("Memory error while parsing %s: %s", url, memory_error)
                    if hasattr(local_parser, "_cache"):
                        local_parser._cache.clear()
                    gc.collect()
                    self._update_stats(success=False)
                    return False, f"MemoryError: {memory_error}"

                # Переименовываем файл
                try:
                    os.replace(str(temp_filepath), str(filepath))
                except OSError as replace_error:
                    self._log(
                        f"Не удалось переименовать файл: {replace_error}. Используем shutil.move.",
                        "debug",
                    )
                    shutil.move(str(temp_filepath), str(filepath))

                self._log(f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info")
                self._update_stats(success=True)

                if progress_callback:
                    with self._stats_lock:
                        success_count = self._stats["success"]
                        failed_count = self._stats["failed"]
                    progress_callback(success_count, failed_count, filepath.name)

                return True, str(filepath)

            except ChromeException as chrome_error:
                self._log(f"Ошибка Chrome после {max_retries} попыток: {chrome_error}", "error")
                self._cleanup_temp_file(temp_filepath)
                self._update_stats(success=False)
                return False, f"Ошибка Chrome: {chrome_error}"

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as parse_error:
                self._log(
                    f"Ошибка при парсинге {city_name} - {category_name}: {parse_error}", "error",
                )
                self._cleanup_temp_file(temp_filepath)
                self._update_stats(success=False)

                if progress_callback:
                    with self._stats_lock:
                        success_count = self._stats["success"]
                        failed_count = self._stats["failed"]
                    progress_callback(success_count, failed_count, "N/A")

                return False, str(parse_error)

            finally:
                # Гарантированное освобождение семафора
                if semaphore_acquired and self._browser_semaphore:
                    self._browser_semaphore.release()

        # Выполняем с таймаутом и гарантированной регистрацией временного файла
        try:
            temp_file_manager.register(temp_filepath)

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_parse)
                try:
                    success, message = future.result(timeout=self.timeout_per_url)
                    return success, message
                except FuturesTimeoutError:
                    self._log(
                        f"Таймаут парсинга {city_name} - {category_name} "
                        f"({self.timeout_per_url} сек)",
                        "error",
                    )
                    self._cleanup_temp_file(temp_filepath)
                    self._update_stats(success=False)

                    if progress_callback:
                        with self._stats_lock:
                            success_count = self._stats["success"]
                            failed_count = self._stats["failed"]
                        progress_callback(success_count, failed_count, "N/A")

                    return False, f"Таймаут: {self.timeout_per_url} сек"

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self._log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")
            self._cleanup_temp_file(temp_filepath)
            self._update_stats(success=False)

            if progress_callback:
                with self._stats_lock:
                    success_count = self._stats["success"]
                    failed_count = self._stats["failed"]
                progress_callback(success_count, failed_count, "N/A")

            return False, str(e)

        finally:
            temp_file_manager.unregister(temp_filepath)


__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_PARSE_MAX_RETRIES",
    "DEFAULT_PARSE_RETRY_DELAY",
    "MEMORY_THRESHOLD_BYTES",
    "MemoryCheckStrategy",
    "MemoryMonitorProtocol",
    "ParseStrategy",
    "ParserFactory",
    "ParserResult",
    "UrlGenerationStrategy",
    "UrlTuple",
    "WriterFactory",
]
