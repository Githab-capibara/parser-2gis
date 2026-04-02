"""Модуль стратегий парсинга для параллельного парсинга.

Предоставляет классы стратегий для:
- ParseStrategy - стратегия парсинга单个 URL
- UrlGenerationStrategy - стратегия генерации URL
- MemoryCheckStrategy - стратегия проверки памяти

ISSUE-002: Выделено из ParallelCityParser для соблюдения SRP.
"""

from __future__ import annotations

import gc
import os
import random
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Callable

from typing_extensions import TypeAlias

from parser_2gis.constants import DEFAULT_TIMEOUT
from parser_2gis.infrastructure import MemoryMonitor
from parser_2gis.logger.logger import logger
from parser_2gis.utils.temp_file_manager import temp_file_manager
from parser_2gis.utils.url_utils import generate_category_url

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

# Type aliases
ParserResult: TypeAlias = tuple[bool, str]  # (success, message)
UrlTuple: TypeAlias = tuple[str, str, str]  # (url, category_name, city_name)

# Константы
MEMORY_THRESHOLD_BYTES: int = 100 * 1024 * 1024  # 100MB порог для проверки памяти


class UrlGenerationStrategy:
    """Стратегия генерации URL для парсинга.

    Отвечает за генерацию URL из городов и категорий.
    Поддерживает lazy generation для экономии памяти.
    """

    def __init__(
        self, cities: list[dict], categories: list[dict], stats_lock: threading.RLock
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

    def generate_all_urls(self, stats: dict) -> list[UrlTuple]:
        """Генерирует все URL для парсинга.

        Args:
            stats: Словарь статистики для обновления.

        Returns:
            Список кортежей (url, category_name, city_name).

        """
        all_urls = list(self.generate_all_urls_lazy())

        with self._stats_lock:
            stats["total"] = len(all_urls)

        logger.info(f"Сгенерировано {len(all_urls)} URL для парсинга")
        return all_urls

    def generate_all_urls_lazy(self):
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
                        f"Ошибка генерации URL для {city['name']} - {category['name']}: {e}"
                    )
                    continue


class MemoryCheckStrategy:
    """Стратегия проверки доступной памяти.

    Отвечает за мониторинг памяти и принятие решения о возможности парсинга.
    """

    def __init__(self, memory_threshold_mb: int = 100) -> None:
        """Инициализирует стратегию проверки памяти.

        Args:
            memory_threshold_mb: Порог минимальной доступной памяти в MB.

        """
        self._memory_threshold_mb = memory_threshold_mb
        self._memory_monitor = MemoryMonitor()

    def check_memory(self) -> tuple[bool, int]:
        """Проверяет доступную память.

        Returns:
            Кортеж (is_enough, available_mb):
            - is_enough: True если памяти достаточно
            - available_mb: Доступная память в MB

        """
        available_memory = self._memory_monitor.get_available_memory()
        available_mb = available_memory // (1024 * 1024)
        is_enough = available_memory >= MEMORY_THRESHOLD_BYTES

        return is_enough, available_mb

    def is_memory_low(self) -> bool:
        """Проверяет, является ли доступная память низкой.

        Returns:
            True если память ниже порога.

        """
        available_mb = self._memory_monitor.get_available_memory() // (1024 * 1024)
        return available_mb < self._memory_threshold_mb


class ParseStrategy:
    """Стратегия парсинга单个 URL.

    Отвечает за:
    - Проверку памяти перед парсингом
    - Создание временных файлов
    - Выполнение парсинга с таймаутом
    - Обработку ошибок и очистку ресурсов

    ISSUE-002: Выделено из ParallelCityParser для соблюдения SRP.
    """

    def __init__(
        self,
        output_dir: Path,
        config: Configuration,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        browser_semaphore: threading.BoundedSemaphore | None = None,
        stats: dict | None = None,
        stats_lock: threading.RLock | None = None,
    ) -> None:
        """Инициализирует стратегию парсинга.

        Args:
            output_dir: Директория для сохранения результатов.
            config: Конфигурация парсера.
            timeout_per_url: Таймаут на один URL в секундах.
            browser_semaphore: Семафор для контроля браузеров.
            stats: Словарь статистики.
            stats_lock: Блокировка для защиты статистики.

        """
        self.output_dir = output_dir
        self.config = config
        self.timeout_per_url = timeout_per_url
        self._browser_semaphore = browser_semaphore
        self._stats = stats or {}
        self._stats_lock = stats_lock or threading.RLock()
        self._memory_strategy = MemoryCheckStrategy()

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

    def _ensure_unique_temp_file(self, temp_filepath: Path, max_attempts: int = 3) -> Path:
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
        try:
            if temp_filepath.exists():
                temp_filepath.unlink()
                self._log(f"Временный файл удалён: {temp_filepath.name}", "debug")
        except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
            self._log(
                f"Не удалось удалить временный файл {temp_filepath.name}: {cleanup_error}",
                "warning",
            )

    def _update_stats(self, success: bool) -> None:
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
    ) -> ParserResult:
        """Парсит один URL и сохраняет результат в файл.

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обновления прогресса.
            cancel_event: Событие отмены.

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
                "Low memory (%dMB), skipping %s - %s", available_mb, city_name, category_name
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
        temp_file_manager.register(temp_filepath)

        def do_parse() -> ParserResult:
            """Выполняет парсинг внутри потока."""
            self._log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )

            # Rate limiting
            use_delays = getattr(self.config.parallel, "use_delays", True)
            initial_delay_min = getattr(self.config.parallel, "initial_delay_min", 0.5)
            initial_delay_max = getattr(self.config.parallel, "initial_delay_max", 2.0)
            delay = random.uniform(max(0.1, initial_delay_min), initial_delay_max)
            self._log(f"Rate limiting задержка: {delay:.2f} сек", "debug")
            time.sleep(delay)

            # Приобретаем семафор
            semaphore_acquired = False
            if self._browser_semaphore:
                self._browser_semaphore.acquire()
                semaphore_acquired = True

            parser = None
            writer = None

            try:
                # Локальные импорты
                from parser_2gis.chrome.exceptions import ChromeException
                from parser_2gis.parser import get_parser
                from parser_2gis.writer import get_writer

                # Дополнительная задержка запуска
                if use_delays:
                    launch_delay_min = getattr(self.config.parallel, "launch_delay_min", 0.1)
                    launch_delay_max = getattr(self.config.parallel, "launch_delay_max", 1.0)
                    launch_delay = random.uniform(launch_delay_min, launch_delay_max)
                    time.sleep(launch_delay)

                # Создаём parser и writer с повторными попытками
                max_retries = 10
                retry_delay = 5.0

                for attempt in range(max_retries):
                    try:
                        writer = get_writer(str(temp_filepath), "csv", self.config.writer)
                        parser = get_parser(
                            url,
                            chrome_options=self.config.chrome,
                            parser_options=self.config.parser,
                        )
                        break
                    except ChromeException as chrome_error:
                        if attempt < max_retries - 1:
                            self._log(
                                f"Попытка {attempt + 1}/{max_retries} не удалась: {chrome_error}. "
                                f"Повтор через {retry_delay:.1f} сек...",
                                "warning",
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            raise

                # Выполняем парсинг
                try:
                    with parser:
                        with writer:
                            parser.parse(writer)
                except MemoryError as memory_error:
                    logger.error(f"Memory error while parsing {url}: {memory_error}")
                    if hasattr(parser, "_cache"):
                        parser._cache.clear()
                    gc.collect()
                    self._update_stats(False)
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
                self._update_stats(True)

                if progress_callback:
                    with self._stats_lock:
                        success_count = self._stats["success"]
                        failed_count = self._stats["failed"]
                    progress_callback(success_count, failed_count, filepath.name)

                return True, str(filepath)

            except ChromeException as chrome_error:
                self._log(f"Ошибка Chrome после {max_retries} попыток: {chrome_error}", "error")
                self._cleanup_temp_file(temp_filepath)
                self._update_stats(False)
                return False, f"Ошибка Chrome: {chrome_error}"

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as parse_error:
                self._log(
                    f"Ошибка при парсинге {city_name} - {category_name}: {parse_error}", "error"
                )
                self._cleanup_temp_file(temp_filepath)
                self._update_stats(False)

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

        # Выполняем с таймаутом
        try:
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
                    self._update_stats(False)

                    if progress_callback:
                        with self._stats_lock:
                            success_count = self._stats["success"]
                            failed_count = self._stats["failed"]
                        progress_callback(success_count, failed_count, "N/A")

                    return False, f"Таймаут: {self.timeout_per_url} сек"

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self._log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")
            self._cleanup_temp_file(temp_filepath)
            self._update_stats(False)

            if progress_callback:
                with self._stats_lock:
                    success_count = self._stats["success"]
                    failed_count = self._stats["failed"]
                progress_callback(success_count, failed_count, "N/A")

            return False, str(e)

        finally:
            temp_file_manager.unregister(temp_filepath)


__all__ = [
    "ParseStrategy",
    "UrlGenerationStrategy",
    "MemoryCheckStrategy",
    "ParserResult",
    "UrlTuple",
]
