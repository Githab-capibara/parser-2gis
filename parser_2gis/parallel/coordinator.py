"""Модуль координации для параллельного парсинга.

Предоставляет класс ParallelCoordinator для координации параллельного парсинга:
- Координация потоков и задач
- Управление браузером и семафорами
- Запуск парсинга и объединение результатов
- Обработка отмены и сигналов
"""

from __future__ import annotations

import asyncio
import random
import shutil
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from threading import BoundedSemaphore
from typing import TYPE_CHECKING
from collections.abc import Callable

from parser_2gis.chrome.exceptions import ChromeException
from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MIN_TIMEOUT,
    MIN_WORKERS,
)
from parser_2gis.infrastructure import MemoryMonitor
from parser_2gis.logger import log_parser_finish, logger
from parser_2gis.parallel.error_handler import ParallelErrorHandler
from parser_2gis.parallel.merger import ParallelFileMerger
from parser_2gis.parallel.progress import ParallelProgressReporter
from parser_2gis.parser import get_parser
from parser_2gis.utils.temp_file_manager import TempFileTimer, temp_file_manager
from parser_2gis.utils.url_utils import generate_category_url
from parser_2gis.validation import (
    validate_categories_config,
    validate_cities_config,
    validate_parallel_config,
)
from parser_2gis.writer import get_writer

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


# Глобальная переменная для отслеживания активного координатора
_active_coordinator: ParallelCoordinator | None = None  # noqa: E0602


def _signal_handler(signum: int, frame) -> None:
    """Глобальный обработчик сигналов SIGINT (Ctrl+C).

    Args:
        signum: Номер сигнала.
        frame: Текущий фрейм.

    """
    global _active_coordinator  # noqa: PLW0602 - используется для установки координатора
    if _active_coordinator is not None:
        logger.warning("Получен сигнал прерывания (SIGINT), остановка парсинга...")
        _active_coordinator.stop()


class ParallelCoordinator:
    """Координатор для параллельного парсинга городов.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельную папку output/, затем объединяются.

    H3: Dependency Injection для errorHandler и fileMerger через конструктор.

    Пример использования:
        >>> from parser_2gis.parallel import ParallelCoordinator
        >>> from parser_2gis.config import Configuration

        # Базовое использование
        >>> coordinator = ParallelCoordinator(
        ...     cities=[{'code': 'msk', 'domain': '2gis.ru'}],
        ...     categories=[{'id': '1', 'name': 'Аптеки'}],
        ...     output_dir='./output',
        ...     config=Configuration(),
        ...     max_workers=5
        ... )
        >>> coordinator.run_parsing()

    Пример Dependency Injection:
        >>> # Внедрение кастомного обработчика ошибок
        >>> from parser_2gis.parallel.error_handler import ParallelErrorHandler
        >>> from parser_2gis.parallel.merger import ParallelFileMerger
        >>> from parser_2gis.parallel.progress import ParallelProgressReporter

        # Создание кастомных компонентов
        >>> custom_error_handler = ParallelErrorHandler(
        ...     max_retries=5,
        ...     retry_delay=1.0
        ... )
        >>> custom_file_merger = ParallelFileMerger(
        ...     buffer_size=256 * 1024,
        ...     batch_size=500
        ... )

        # Внедрение зависимостей через конструктор
        >>> coordinator = ParallelCoordinator(
        ...     cities=[...],
        ...     categories=[...],
        ...     output_dir='./output',
        ...     config=Configuration(),
        ...     max_workers=5,
        ...     error_handler=custom_error_handler,  # DI
        ...     file_merger=custom_file_merger  # DI
        ... )

        # Запуск с кастомными компонентами
        >>> success = coordinator.run_parsing(
        ...     progress_callback=lambda s, f, fn: print(f"Прогресс: {s}/{f}")
        ... )

    Пример с кастомным progress reporter:
        >>> # Создание кастомного репортёра
        >>> class CustomProgressReporter:
        ...     def update(self, success: int, failed: int, filename: str):
        ...         print(f"Файл: {filename}, Успешно: {success}, Ошибок: {failed}")

        # Внедрение кастомного репортёра
        >>> custom_reporter = CustomProgressReporter()
        >>> coordinator = ParallelCoordinator(
        ...     cities=[...],
        ...     categories=[...],
        ...     output_dir='./output',
        ...     config=Configuration(),
        ...     max_workers=5,
        ...     error_handler=custom_error_handler,
        ...     file_merger=custom_file_merger,
        ... )

        # Запуск с кастомным прогрессом
        >>> coordinator.run_parsing(progress_callback=custom_reporter.update)
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        error_handler: ParallelErrorHandler | None = None,
        file_merger: ParallelFileMerger | None = None,
    ) -> None:
        """Инициализация координатора параллельного парсинга.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            output_dir: Директория для сохранения результатов.
            config: Конфигурация парсера.
            max_workers: Максимальное количество рабочих потоков.
            timeout_per_url: Таймаут на один URL в секундах.
            error_handler: Опциональный обработчик ошибок (DI).
            file_merger: Опциональный объединитель файлов (DI).

        Note:
            Для удобства можно использовать ParallelRunConfig:
            >>> run_config = ParallelRunConfig(
            ...     cities=cities,
            ...     categories=categories,
            ...     output_dir=Path("./output"),
            ...     config=config,
            ...     max_workers=5,
            ... )
            >>> coordinator = ParallelCoordinator(**run_config.to_dict())

        H3: Dependency Injection через конструктор:
            - error_handler и file_merger могут быть переданы извне
            - По умолчанию создаются внутренние экземпляры для обратной совместимости

        """
        self._validate_inputs(cities, categories, max_workers, timeout_per_url, output_dir)

        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers
        self.timeout_per_url = timeout_per_url

        self._stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}
        self._lock = threading.RLock()
        self._cancel_event = threading.Event()
        self._stop_event = threading.Event()
        self._browser_launch_semaphore = BoundedSemaphore(max_workers + 20)

        # H3: Dependency Injection с fallback на создание по умолчанию
        self._error_handler = error_handler or ParallelErrorHandler(self.output_dir, self.config)
        self._file_merger = file_merger or ParallelFileMerger(
            self.output_dir, self.config, self._cancel_event, self._lock
        )
        self._progress_reporter: ParallelProgressReporter | None = None

        self._temp_file_cleanup_timer: TempFileTimer | None = None
        if self.config.parallel.use_temp_file_cleanup:
            try:
                from parser_2gis.utils.temp_file_manager import (
                    MAX_TEMP_FILES_MONITORING,
                    ORPHANED_TEMP_FILE_AGE,
                    TEMP_FILE_CLEANUP_INTERVAL,
                )

                self._temp_file_cleanup_timer = TempFileTimer(
                    temp_dir=self.output_dir,
                    interval=TEMP_FILE_CLEANUP_INTERVAL,
                    max_files=MAX_TEMP_FILES_MONITORING,
                    orphan_age=ORPHANED_TEMP_FILE_AGE,
                )
                logger.info(
                    "Инициализирован таймер периодической очистки временных файлов для %s",
                    self.output_dir,
                )
            except (OSError, RuntimeError, TypeError, ValueError) as timer_error:
                logger.warning(
                    "Не удалось инициализировать таймер очистки временных файлов: %s", timer_error
                )

        self.log(
            f"Инициализирован парсер: {len(cities)} городов, {len(categories)} "
            f"категорий, max_workers={max_workers}",
            "info",
        )

    def _validate_inputs(
        self,
        cities: list[dict],
        categories: list[dict],
        max_workers: int,
        timeout_per_url: int,
        output_dir: str,
    ) -> None:
        """Валидирует входные данные с использованием централизованных функций валидации.

        H6: Централизация валидации в validation/data_validator.py
        """
        # Валидация городов
        validate_cities_config(cities, "cities")

        # Валидация категорий
        validate_categories_config(categories, "categories")

        # Валидация конфигурации параллельного парсинга
        validate_parallel_config(
            max_workers=max_workers,
            timeout_per_url=timeout_per_url,
            min_workers=MIN_WORKERS,
            max_workers_limit=MAX_WORKERS,
            min_timeout=MIN_TIMEOUT,
            max_timeout=MAX_TIMEOUT,
        )

        # Валидация output_dir
        if not output_dir:
            raise ValueError("output_dir не может быть пустым")

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def _create_parser(self, url: str):
        """Создаёт парсер для указанного URL.

        Args:
            url: URL для парсинга.

        Returns:
            Экземпляр парсера или None при ошибке.

        """
        try:
            return get_parser(
                url, chrome_options=self.config.chrome, parser_options=self.config.parser
            )
        except (ChromeException, OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка создания парсера: {e}", "error")
            return None

    def _create_writer(self, temp_filepath: Path):
        """Создаёт writer для временного файла.

        Args:
            temp_filepath: Путь к временному файлу.

        Returns:
            Экземпляр writer или None при ошибке.

        """
        try:
            return get_writer(str(temp_filepath), "csv", self.config.writer)
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка создания writer: {e}", "error")
            return None

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """Генерирует все URL для парсинга.

        C014: Использует list() для обратной совместимости.
        """
        # C014: Используем генератор для эффективного создания списка
        all_urls = list(self.generate_all_urls_lazy())

        with self._lock:
            self._stats["total"] = len(all_urls)

        self.log(f"Сгенерировано {len(all_urls)} URL для парсинга", "info")
        return all_urls

    def generate_all_urls_lazy(self):
        """Генератор URL для парсинга.

        C014: Lazy loading для снижения потребления памяти.
        Yield:
            Кортеж (url, category_name, city_name).

        """
        for city in self.cities:
            for category in self.categories:
                try:
                    url = generate_category_url(city, category)
                    yield (url, category["name"], city["name"])
                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    self.log(
                        f"Ошибка генерации URL для {city['name']} - {category['name']}: {e}",
                        "error",
                    )

    def _parse_single_url_impl(
        self,
        url: str,
        category_name: str,
        city_name: str,
        temp_filepath: Path,
        filepath: Path,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[bool, str]:
        """Реализация парсинга одного URL."""
        self.log(
            "Начало парсинга: %s - %s (временный файл: %s)",
            city_name,
            category_name,
            temp_filepath.name,
            level="info",
        )

        # H003: Задержка ТОЛЬКО если use_delays=True
        if getattr(self.config.parallel, "use_delays", True):
            initial_delay = random.uniform(
                self.config.parallel.initial_delay_min, self.config.parallel.initial_delay_max
            )
            time.sleep(initial_delay)

        self._browser_launch_semaphore.acquire()
        try:
            # H003: Задержка ТОЛЬКО если use_delays=True
            if getattr(self.config.parallel, "use_delays", True):
                launch_delay = random.uniform(
                    self.config.parallel.launch_delay_min, self.config.parallel.launch_delay_max
                )
                self.log(f"Задержка перед запуском Chrome: {launch_delay:.2f} сек", "debug")
                time.sleep(launch_delay)

            # Вынесено в отдельные методы для устранения nonlocal
            parser = self._create_parser(url)
            writer = self._create_writer(temp_filepath)

            # Проверка что parser и writer были успешно созданы
            if parser is None or writer is None:
                self._browser_launch_semaphore.release()
                return False, "Ошибка инициализации парсера или писателя"

            try:
                # pylint: disable=not-context-manager
                with parser:
                    with writer:
                        try:
                            parser.parse(writer)
                        except MemoryError as memory_error:
                            return self._error_handler.handle_memory_error(
                                memory_error, temp_filepath, url
                            )
                        finally:
                            logger.debug("Завершена очистка ресурсов парсера")
            finally:
                self._browser_launch_semaphore.release()

            # Атомарное переименование с проверкой и retry логикой
            max_rename_attempts = 3
            rename_success = False

            for rename_attempt in range(max_rename_attempts):
                try:
                    # Задержка 0.1 сек перед проверкой exists() для стабильности
                    time.sleep(0.1)

                    # Проверка существования временного файла перед переименованием
                    if not temp_filepath.exists():
                        self.log(f"Временный файл не существует: {temp_filepath}", "error")
                        return False, "Временный файл не существует"

                    # Используем shutil.move вместо Path.rename() для кроссплатформенности
                    shutil.move(str(temp_filepath), str(filepath))
                    self.log(
                        f"Временный файл перемещён: {temp_filepath.name} → {filepath.name}", "debug"
                    )
                    rename_success = True
                    break

                except OSError as move_error:
                    if rename_attempt < max_rename_attempts - 1:
                        self.log(
                            "Попытка %d/%d не удалась: %s. Повтор...",
                            rename_attempt + 1,
                            max_rename_attempts,
                            move_error,
                            level="warning",
                        )
                        time.sleep(0.1 * (rename_attempt + 1))  # Экспоненциальная задержка
                    else:
                        self.log(
                            "Не удалось переместить временный файл %s: %s",
                            temp_filepath.name,
                            move_error,
                            level="error",
                        )
                        self._error_handler._cleanup_temp_file(temp_filepath)
                        raise move_error

            if not rename_success:
                return False, "Не удалось переименовать файл"

            self.log(f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info")

            with self._lock:
                self._stats["success"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        except Exception as e:
            return self._error_handler.handle_other_error(
                e, temp_filepath, city_name, category_name
            )

    def parse_single_url(
        self,
        url: str,
        category_name: str,
        city_name: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[bool, str]:
        """Парсит один URL и сохраняет результат в отдельный файл.

        Returns:
            Кортеж (успех, сообщение/путь к файлу).

        """
        # H9: Проверка доступной памяти через инфраструктурный модуль
        memory_monitor = MemoryMonitor()
        available_memory = memory_monitor.get_available_memory()
        if available_memory < 100 * 1024 * 1024:
            logger.warning(
                "Low memory (%dMB), skipping %s - %s",
                available_memory // 1024 // 1024,
                city_name,
                category_name,
            )
            return False, "Недостаточно памяти"

        if self._cancel_event.is_set():
            return False, "Отменено пользователем"

        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        temp_filepath: Path | None = None
        try:
            temp_filepath = self._error_handler.create_unique_temp_file(city_name, category_name)
        except (OSError, RuntimeError) as e:
            self.log(f"Не удалось создать временный файл: {e}", "error")
            return False, f"Ошибка создания временного файла: {e}"

        def do_parse() -> tuple[bool, str]:
            return self._parse_single_url_impl(
                url, category_name, city_name, temp_filepath, filepath, progress_callback
            )

        # ИСПРАВЛЕНИЕ: Добавлена обработка отмены с try/finally для очистки временных файлов
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_parse)
                try:
                    success, message = future.result(timeout=self.timeout_per_url)
                    return success, message
                except FuturesTimeoutError:
                    return self._error_handler.handle_timeout_error(
                        temp_filepath, city_name, category_name, self.timeout_per_url
                    )
                except (KeyboardInterrupt, asyncio.CancelledError):
                    # ИСПРАВЛЕНИЕ: Обработка отмены с очисткой временных файлов
                    self.log(f"Парсинг отменён: {city_name} - {category_name}", "warning")
                    if temp_filepath and temp_filepath.exists():
                        try:
                            temp_filepath.unlink()
                            self.log(f"Временный файл удалён: {temp_filepath}", "debug")
                        except (OSError, RuntimeError) as cleanup_error:
                            self.log(
                                f"Ошибка при удалении временного файла: {cleanup_error}", "error"
                            )
                    return False, "Отменено пользователем"
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            return self._error_handler.handle_other_error(
                e, temp_filepath, city_name, category_name
            )
        finally:
            # ИСПРАВЛЕНИЕ: Очистка временных файлов в finally
            if temp_filepath and temp_filepath.exists() and not filepath.exists():
                # Временный файл существует, но финальный файл не создан - удаляем временный
                try:
                    temp_filepath.unlink()
                    self.log(f"Временный файл удалён в finally: {temp_filepath}", "debug")
                except (OSError, RuntimeError) as cleanup_error:
                    self.log(
                        f"Ошибка при удалении временного файла в finally: {cleanup_error}", "error"
                    )

    def run(
        self,
        output_file: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
        merge_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг всех городов и категорий."""
        global _active_coordinator

        # Установка глобального обработчика сигнала SIGINT
        old_signal_handler = signal.signal(signal.SIGINT, _signal_handler)
        _active_coordinator = self

        start_time = time.time()
        total_tasks = len(self.cities) * len(self.categories)

        self._progress_reporter = ParallelProgressReporter(
            total_tasks=total_tasks,
            lock=self._lock,
            progress_callback=progress_callback,
            merge_callback=merge_callback,
        )

        if self._temp_file_cleanup_timer is not None:
            try:
                self._temp_file_cleanup_timer.start()
                self.log("Запущен таймер периодической очистки временных файлов", "info")
            except (OSError, RuntimeError, TypeError, ValueError) as timer_error:
                self.log(f"Не удалось запустить таймер очистки: {timer_error}", "warning")

        self.log(f"Запуск параллельного парсинга ({self.max_workers} потока)", "info")
        self.log(f"Города: {[c['name'] for c in self.cities]}", "info")
        self.log(f"Категории: {len(self.categories)}", "info")
        self.log(f"Всего задач: {total_tasks}", "info")

        all_urls = self.generate_all_urls()
        if not all_urls:
            self.log("Нет URL для парсинга", "error")
            return False

        self.log(f"Таймаут на один URL: {self.timeout_per_url} секунд", "info")

        executor = None
        futures: dict = {}
        try:
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
            futures = {
                executor.submit(
                    self.parse_single_url, url, category_name, city_name, progress_callback
                ): (url, category_name, city_name)
                for url, category_name, city_name in all_urls
            }

            for future in as_completed(futures):
                url, category_name, city_name = futures[future]
                try:
                    success, result = future.result(timeout=self.timeout_per_url)
                    if self._progress_reporter:
                        self._progress_reporter.update_progress(
                            success=success, filename=result if success else "N/A"
                        )
                    if not success:
                        self.log(f"Не удалось: {city_name} - {category_name}: {result}", "error")
                except FuturesTimeoutError:
                    if self._progress_reporter:
                        self._progress_reporter.update_progress(success=False, filename="N/A")
                    self.log(f"Таймаут при парсинге {city_name} - {category_name}", "error")
                except (KeyboardInterrupt, asyncio.CancelledError):
                    self.log("Парсинг прерван пользователем", "warning")
                    self._cancel_event.set()
                    for f in futures:
                        f.cancel()
                    return False
                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    if self._progress_reporter:
                        self._progress_reporter.update_progress(success=False, filename="N/A")
                    self.log(f"Исключение при парсинге {city_name} - {category_name}: {e}", "error")

        except (KeyboardInterrupt, asyncio.CancelledError):
            self.log("Парсинг прерван пользователем", "warning")
            self._cancel_event.set()
            if executor is not None:
                for f in futures:
                    f.cancel()
            return False
        finally:
            # Восстановление обработчика сигнала и очистка ресурсов
            _active_coordinator = None
            try:
                signal.signal(signal.SIGINT, old_signal_handler)
            except (ValueError, TypeError):
                pass  # Игнорируем ошибки при восстановлении обработчика

            if executor is not None:
                try:
                    executor.shutdown(wait=True, cancel_futures=True)
                    self.log("ThreadPoolExecutor корректно завершён", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as shutdown_error:
                    self.log(f"Ошибка при shutdown ThreadPoolExecutor: {shutdown_error}", "error")

            # Остановка таймера очистки временных файлов
            if self._temp_file_cleanup_timer is not None:
                try:
                    self._temp_file_cleanup_timer.stop()
                    self.log("Таймер периодической очистки остановлен", "info")
                except (OSError, RuntimeError, TypeError, ValueError) as timer_error:
                    self.log(f"Ошибка при остановке таймера: {timer_error}", "debug")

            self.log("Ресурсы координатора освобождены", "debug")

        duration = time.time() - start_time
        duration_str = f"{duration:.2f} сек."

        if self._progress_reporter:
            stats_dict = self._progress_reporter.get_stats()
            success_count = stats_dict["success"]
            failed_count = stats_dict["failed"]
        else:
            success_count = self._stats["success"]
            failed_count = self._stats["failed"]

        self.log(f"Парсинг завершён. Успешно: {success_count}, Ошибок: {failed_count}", "info")

        if success_count > 0:
            self.log("Начало объединения результатов...", "info")
            merge_success = self._file_merger.merge_csv_files(output_file, merge_callback)
            if not merge_success:
                self.log("Не удалось объединить CSV файлы", "error")
                log_parser_finish(
                    success=False,
                    stats={
                        "Городов": len(self.cities),
                        "Категорий": len(self.categories),
                        "Успешно": success_count,
                        "Ошибки": failed_count,
                    },
                    duration=duration_str,
                )
                return False
        else:
            self.log("Нет успешных результатов для объединения", "warning")
            log_parser_finish(
                success=False,
                stats={
                    "Городов": len(self.cities),
                    "Категорий": len(self.categories),
                    "Успешно": 0,
                    "Ошибки": failed_count,
                },
                duration=duration_str,
            )
            return False

        stats = {
            "Городов": len(self.cities),
            "Категорий": len(self.categories),
            "Всего URL": total_tasks,
            "Успешно": success_count,
            "Ошибки": failed_count,
        }
        log_parser_finish(success=True, stats=stats, duration=duration_str)

        return True

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._cancel_event.set()
        self._stop_event.set()
        self.log("Получена команда остановки парсинга", "warning")

    def get_statistics(self) -> dict:
        """Возвращает статистику парсинга."""
        with self._lock:
            return dict(self._stats)


# Функции для управления временными файлами
_temp_files_lock = temp_file_manager._lock
_temp_files_registry = temp_file_manager._registry


def _register_temp_file(file_path: Path) -> None:
    temp_file_manager.register(file_path)


def _unregister_temp_file(file_path: Path) -> None:
    temp_file_manager.unregister(file_path)


def _cleanup_all_temp_files() -> None:
    temp_file_manager.cleanup_all()


__all__ = [
    "ParallelCoordinator",
    "_cleanup_all_temp_files",
    "_register_temp_file",
    "_temp_files_lock",
    "_temp_files_registry",
    "_unregister_temp_file",
]
