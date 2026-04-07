"""Модуль для парсинга URL в параллельном режиме.

Этот модуль предоставляет класс ParallelUrlParser для генерации и парсинга URL
с использованием нескольких потоков.

ISSUE-027: Реализует протокол UrlGeneratorProtocol из protocols.py.

Оптимизации:
- Буферизация при работе с CSV файлами
- Улучшенная обработка прогресса
- Оптимизация памяти при слиянии файлов
"""

from __future__ import annotations

import gc
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Callable

from parser_2gis.constants import DEFAULT_TIMEOUT, MAX_UNIQUE_NAME_ATTEMPTS
from parser_2gis.infrastructure import MemoryMonitor
from parser_2gis.logger.logger import logger
from parser_2gis.parallel.strategies import MEMORY_THRESHOLD_BYTES
from parser_2gis.protocols import UrlGeneratorProtocol
from parser_2gis.utils.url_utils import generate_category_url

if TYPE_CHECKING:
    from parser_2gis.config import Configuration
    from parser_2gis.parser import BaseParser


class ParallelUrlParser(UrlGeneratorProtocol):
    """Парсер URL для параллельного парсинга городов.

    ISSUE-027: Реализует протокол UrlGeneratorProtocol.

    Отвечает за:
    - Генерацию всех URL для парсинга
    - Парсинг отдельных URL с сохранением результатов
    - Управление временными файлами

    Args:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Папка для сохранения результатов.
        config: Конфигурация парсера.
        timeout_per_url: Таймаут на один URL в секундах.

    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: Path,
        config: Configuration,
        timeout_per_url: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Инициализирует парсер URL.

        ISSUE-106, ISSUE-107: Добавлена валидация cities и categories на пустой список.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            output_dir: Папка для сохранения результатов.
            config: Конфигурация парсера.
            timeout_per_url: Таймаут на один URL в секундах.

        Raises:
            ValueError: Если cities или categories пустой.

        """
        # ISSUE-106: Валидация cities на пустой список
        if not cities:
            raise ValueError("cities не может быть пустым списком")
        if not isinstance(cities, list):
            raise TypeError(f"cities должен быть списком, получен {type(cities).__name__}")

        # ISSUE-107: Валидация categories на пустой список
        if not categories:
            raise ValueError("categories не может быть пустым списком")
        if not isinstance(categories, list):
            raise TypeError(f"categories должен быть списком, получен {type(categories).__name__}")

        self.cities = cities
        self.categories = categories
        self.output_dir = output_dir
        self.config = config
        self.timeout_per_url = timeout_per_url

        # Статистика (все операции защищены _lock)
        self._stats: dict[str, int] = {"total": 0, "success": 0, "failed": 0, "skipped": 0}
        self._lock = threading.Lock()

        # Флаг отмены
        self._cancel_event = threading.Event()

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).

        """
        all_urls: list[tuple[str, str, str]] = []

        for city in self.cities:
            for category in self.categories:
                try:
                    url = generate_category_url(city, category)
                    all_urls.append((url, category["name"], city["name"]))
                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    self.log(
                        f"Ошибка генерации URL для {city['name']} - {category['name']}: {e}",
                        "error",
                    )
                    continue

        with self._lock:
            self._stats["total"] = len(all_urls)

        self.log(f"Сгенерировано {len(all_urls)} URL для парсинга", "info")
        return all_urls

    def parse_single_url(
        self,
        url: str,
        category_name: str,
        city_name: str,
        browser_semaphore: threading.BoundedSemaphore,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[bool, str]:
        """Парсит один URL и сохраняет результат в отдельный файл.

        Использует временный файл для защиты от race condition:
        - Запись происходит во временный файл с уникальным именем
        - После успешного завершения файл переименовывается в целевое имя
        - При ошибке временный файл удаляется

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            browser_semaphore: Семафор для контроля запуска браузеров.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (успех, сообщение).

        """
        # Проверка доступной памяти через инфраструктурный модуль
        memory_monitor = MemoryMonitor()
        available_memory = memory_monitor.get_available_memory()
        if available_memory < MEMORY_THRESHOLD_BYTES:
            logger.warning(
                "Low memory (%dMB), skipping %s - %s",
                available_memory // 1024 // 1024,
                city_name,
                category_name,
            )
            return False, "Недостаточно памяти"

        # Проверяем флаг отмены
        if self._cancel_event.is_set():
            return False, "Отменено пользователем"

        # Формируем целевое имя файла
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        # Создаём уникальное временное имя файла
        temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
        temp_filepath = self.output_dir / temp_filename

        # Атомарное создание временного файла для предотвращения race condition
        temp_fd: int | None = None
        for attempt in range(MAX_UNIQUE_NAME_ATTEMPTS):
            try:
                temp_fd = os.open(
                    str(temp_filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644
                )
                os.close(temp_fd)
                temp_fd = None
                logger.log(5, "Временный файл атомарно создан: %s", temp_filename)
                break
            except FileExistsError:
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(5, "Коллизия имён (попытка %d): генерация нового имени", attempt + 1)
                    temp_filename = (
                        f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
                    )
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать уникальный временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise
            except OSError:
                if temp_fd is not None:
                    try:
                        os.close(temp_fd)
                    except OSError as close_error:
                        logger.log(5, "Ошибка закрытия дескриптора файла: %s", close_error)
                    temp_fd = None
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(
                        5, "Ошибка создания файла (попытка %d): повторная попытка", attempt + 1
                    )
                    temp_filename = (
                        f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
                    )
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise

        def do_parse() -> tuple[bool, str]:
            """Выполняет парсинг внутри отдельного потока.

            Returns:
                Кортеж (успех, сообщение).

            """
            import random
            import time

            from parser_2gis.chrome.exceptions import ChromeException
            from parser_2gis.parser import get_parser
            from parser_2gis.writer import get_writer

            self.log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )

            # H003: Задержка ТОЛЬКО если use_delays=True
            if getattr(self.config.parallel, "use_delays", True):
                initial_delay = random.uniform(
                    self.config.parallel.initial_delay_min, self.config.parallel.initial_delay_max
                )
                time.sleep(initial_delay)

            browser_semaphore.acquire()
            try:
                # H003: Задержка ТОЛЬКО если use_delays=True
                if getattr(self.config.parallel, "use_delays", True):
                    launch_delay = random.uniform(
                        self.config.parallel.launch_delay_min, self.config.parallel.launch_delay_max
                    )
                    self.log(f"Задержка перед запуском Chrome: {launch_delay:.2f} сек", "debug")
                    time.sleep(launch_delay)

                max_retries = 10
                retry_delay = 5.0
                parser: BaseParser | None = None

                for attempt in range(max_retries):
                    writer = None
                    try:
                        writer = get_writer(str(temp_filepath), "csv", self.config.writer)
                        parser = get_parser(
                            url,
                            chrome_options=self.config.chrome,
                            parser_options=self.config.parser,
                        )
                        break
                    except ChromeException as chrome_error:
                        # ИСПРАВЛЕНИЕ #11: Закрываем writer при ошибке retry
                        if writer is not None:
                            try:
                                writer.close()
                            except (OSError, RuntimeError, ChromeException) as close_error:
                                self.log(
                                    f"Ошибка при закрытии writer в retry: {close_error}", "debug"
                                )
                        if attempt < max_retries - 1:
                            self.log(
                                f"Попытка {attempt + 1}/{max_retries} не удалась: {chrome_error}. "
                                f"Повтор через {retry_delay:.1f} сек...",
                                "warning",
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            raise chrome_error

                if parser is None:
                    browser_semaphore.release()
                    return False, "Ошибка инициализации парсера"

            except ChromeException as chrome_error:
                browser_semaphore.release()
                self.log(f"Ошибка Chrome после {max_retries} попыток: {chrome_error}", "error")
                self._cleanup_temp_file(temp_filepath)
                with self._lock:
                    self._stats["failed"] += 1
                return False, f"Ошибка Chrome: {chrome_error}"

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as init_error:
                browser_semaphore.release()
                self.log(f"Ошибка инициализации для {url}: {init_error}", "error")
                self._cleanup_temp_file(temp_filepath)
                with self._lock:
                    self._stats["failed"] += 1
                return False, f"Ошибка инициализации: {init_error}"

            try:
                with parser:
                    with get_writer(str(temp_filepath), "csv", self.config.writer) as writer:
                        try:
                            parser.parse(writer)
                        except MemoryError as memory_error:
                            logger.error(f"Memory error while parsing {url}: {memory_error}")
                            # Освобождаем кэш если есть
                            if hasattr(parser, "_cache"):
                                parser._cache.clear()
                            # Принудительный GC через memory_manager
                            if hasattr(self, "_memory_manager"):
                                self._memory_manager.force_gc()
                            else:
                                gc.collect()
                            raise
                        finally:
                            logger.debug("Завершена очистка ресурсов парсера")
            except MemoryError as memory_error:
                self.log(
                    f"MemoryError при парсинге {city_name} - {category_name}: {memory_error}",
                    "error",
                )
                browser_semaphore.release()
                self._cleanup_temp_file(temp_filepath)
                # Принудительный GC через memory_manager
                if hasattr(self, "_memory_manager"):
                    self._memory_manager.force_gc()
                else:
                    gc.collect()
                with self._lock:
                    self._stats["failed"] += 1
                return False, f"MemoryError: {memory_error}"
            finally:
                # Гарантированное освобождение семафора после завершения работы с браузером
                try:
                    browser_semaphore.release()
                except ValueError:
                    # Семафор уже освобождён — это ожидаемо при конкурентном доступе
                    pass  # noqa: PIE790 — семафор уже освобождён, ожидаемо

            # Переименовываем временный файл в целевой
            self._rename_temp_to_final(temp_filepath, filepath, temp_filename)

            self.log(f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info")

            with self._lock:
                self._stats["success"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        # Используем ThreadPoolExecutor для установки таймаута (потокобезопасная альтернатива signal.alarm)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_parse)
                try:
                    # Ожидаем результат с таймаутом
                    success, message = future.result(timeout=self.timeout_per_url)
                    return success, message
                except FuturesTimeoutError:
                    self.log(
                        f"Таймаут парсинга {city_name} - {category_name} "
                        f"({self.timeout_per_url} сек)",
                        "error",
                    )
                    self._cleanup_temp_file(temp_filepath)
                    with self._lock:
                        self._stats["failed"] += 1
                        success_count = self._stats["success"]
                        failed_count = self._stats["failed"]
                    if progress_callback:
                        progress_callback(success_count, failed_count, "N/A")
                    return False, f"Таймаут: {self.timeout_per_url} сек"

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self._cleanup_temp_file(temp_filepath)
            with self._lock:
                self._stats["failed"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]
            if progress_callback:
                progress_callback(success_count, failed_count, "N/A")
            return False, str(e)

    def _cleanup_temp_file(self, temp_filepath: Path) -> None:
        """Очищает временный файл.

        Args:
            temp_filepath: Путь к временному файлу.

        """
        try:
            if temp_filepath.exists():
                temp_filepath.unlink()
                self.log(f"Временный файл удалён: {temp_filepath.name}", "debug")
        except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
            self.log(
                f"Не удалось удалить временный файл {temp_filepath.name}: {cleanup_error}",
                "warning",
            )

    def _rename_temp_to_final(
        self, temp_filepath: Path, filepath: Path, temp_filename: str
    ) -> None:
        """Переименовывает временный файл в целевой.

        Args:
            temp_filepath: Путь к временному файлу.
            filepath: Путь к целевому файлу.
            temp_filename: Имя временного файла.

        """
        import shutil

        move_success = False
        try:
            os.replace(str(temp_filepath), str(filepath))
            move_success = True
        except OSError as replace_error:
            self.log(
                f"Не удалось переименовать файл (OSError): {replace_error}. Используем shutil.move",
                "debug",
            )
            try:
                shutil.move(str(temp_filepath), str(filepath))
                move_success = True
            except (OSError, RuntimeError, TypeError, ValueError) as move_error:
                self.log(
                    f"Не удалось переместить временный файл {temp_filename}: {move_error}", "error"
                )
                self._cleanup_temp_file(temp_filepath)
                raise move_error

        if move_success:
            self.log(f"Временный файл переименован: {temp_filename} → {filepath.name}", "debug")

    @property
    def stats(self) -> dict[str, int]:
        """Возвращает статистику парсинга."""
        with self._lock:
            return self._stats.copy()

    def cancel(self) -> None:
        """Отменяет парсинг."""
        self._cancel_event.set()
