"""
Модуль координации для параллельного парсинга.

Предоставляет класс ParallelCoordinator для координации параллельного парсинга:
- Координация потоков и задач
- Управление браузером и семафорами
- Запуск парсинга и объединение результатов
- Обработка отмены и сигналов
"""

from __future__ import annotations

import asyncio
import os
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from threading import BoundedSemaphore
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

import psutil

from parser_2gis.chrome.exceptions import ChromeException
from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MIN_TIMEOUT,
    MIN_WORKERS,
)
from parser_2gis.logger import log_parser_finish, logger
from parser_2gis.parallel.error_handler import ParallelErrorHandler
from parser_2gis.parallel.merger import ParallelFileMerger
from parser_2gis.parallel.progress import ParallelProgressReporter
from parser_2gis.parser import get_parser
from parser_2gis.utils.temp_file_manager import TempFileTimer, temp_file_manager
from parser_2gis.utils.url_utils import generate_category_url
from parser_2gis.writer import get_writer

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


class ParallelCoordinator:
    """Координатор для параллельного парсинга городов.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельную папку output/, затем объединяются.
    """

    def __init__(
        self,
        cities: List[dict],
        categories: List[dict],
        output_dir: str,
        config: "Configuration",
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Инициализация координатора параллельного парсинга.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            output_dir: Директория для сохранения результатов.
            config: Конфигурация парсера.
            max_workers: Максимальное количество рабочих потоков.
            timeout_per_url: Таймаут на один URL в секундах.

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

        self._error_handler = ParallelErrorHandler(self.output_dir, self.config)
        self._file_merger = ParallelFileMerger(
            self.output_dir, self.config, self._cancel_event, self._lock
        )
        self._progress_reporter: Optional[ParallelProgressReporter] = None

        self._temp_file_cleanup_timer: Optional[TempFileTimer] = None
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
        cities: List[dict],
        categories: List[dict],
        max_workers: int,
        timeout_per_url: int,
        output_dir: str,
    ) -> None:
        """Валидирует входные данные."""
        if not cities:
            raise ValueError("Список городов не может быть пустым")
        if not categories:
            raise ValueError("Список категорий не может быть пустым")
        if max_workers < MIN_WORKERS:
            raise ValueError(f"max_workers должен быть не менее {MIN_WORKERS}")
        if max_workers > MAX_WORKERS:
            raise ValueError(
                f"max_workers слишком большой: {max_workers} (максимум: {MAX_WORKERS})"
            )
        if timeout_per_url < MIN_TIMEOUT:
            raise ValueError(f"timeout_per_url должен быть не менее {MIN_TIMEOUT} секунд")
        if timeout_per_url > MAX_TIMEOUT:
            raise ValueError(f"timeout_per_url слишком большой: {timeout_per_url} секунд")

        for idx, city in enumerate(cities):
            if not isinstance(city, dict) or "name" not in city:
                raise ValueError(f"Город {idx} должен быть словарём с ключом 'name'")

        for idx, category in enumerate(categories):
            if not isinstance(category, dict) or "name" not in category:
                raise ValueError(f"Категория {idx} должна быть словарём с ключом 'name'")

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> List[Tuple[str, str, str]]:
        """Генерирует все URL для парсинга."""
        all_urls = []
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

        with self._lock:
            self._stats["total"] = len(all_urls)

        self.log(f"Сгенерировано {len(all_urls)} URL для парсинга", "info")
        return all_urls

    def _parse_single_url_impl(
        self,
        url: str,
        category_name: str,
        city_name: str,
        temp_filepath: Path,
        filepath: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Реализация парсинга одного URL."""
        self.log(
            f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filepath.name})",
            "info",
        )

        initial_delay = random.uniform(
            self.config.parallel.initial_delay_min, self.config.parallel.initial_delay_max
        )
        time.sleep(initial_delay)

        self._browser_launch_semaphore.acquire()
        try:
            launch_delay = random.uniform(
                self.config.parallel.launch_delay_min, self.config.parallel.launch_delay_max
            )
            self.log(f"Задержка перед запуском Chrome: {launch_delay:.2f} сек", "debug")
            time.sleep(launch_delay)

            parser = None
            writer = None

            def create_parser_writer():
                nonlocal parser, writer
                writer = get_writer(str(temp_filepath), "csv", self.config.writer)
                parser = get_parser(
                    url, chrome_options=self.config.chrome, parser_options=self.config.parser
                )

            try:
                self._error_handler.retry_with_backoff(create_parser_writer)
            except ChromeException as chrome_error:
                self._browser_launch_semaphore.release()
                return self._error_handler.handle_chrome_error(chrome_error, temp_filepath)
            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as init_error:
                self._browser_launch_semaphore.release()
                return self._error_handler.handle_init_error(init_error, temp_filepath, url)

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

            try:
                os.replace(str(temp_filepath), str(filepath))
                self.log(
                    f"Временный файл переименован: {temp_filepath.name} → {filepath.name}", "debug"
                )
            except OSError as replace_error:
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. Используем shutil.move",
                    "debug",
                )
                try:
                    shutil.move(str(temp_filepath), str(filepath))
                except (OSError, RuntimeError, TypeError, ValueError) as move_error:
                    self.log(
                        f"Не удалось переместить временный файл {temp_filepath.name}: {move_error}",
                        "error",
                    )
                    self._error_handler._cleanup_temp_file(temp_filepath)
                    raise move_error

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
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Парсит один URL и сохраняет результат в отдельный файл.

        Returns:
            Кортеж (успех, сообщение/путь к файлу).
        """
        available_memory = psutil.virtual_memory().available
        if available_memory < 100 * 1024 * 1024:
            logger.warning(
                f"Low memory ({available_memory // 1024 // 1024}MB), skipping {city_name} - {category_name}"
            )
            return False, "Недостаточно памяти"

        if self._cancel_event.is_set():
            return False, "Отменено пользователем"

        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        temp_filepath: Optional[Path] = None
        try:
            temp_filepath = self._error_handler.create_unique_temp_file(city_name, category_name)
        except (OSError, RuntimeError) as e:
            self.log(f"Не удалось создать временный файл: {e}", "error")
            return False, f"Ошибка создания временного файла: {e}"

        def do_parse() -> Tuple[bool, str]:
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
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        merge_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Запускает параллельный парсинг всех городов и категорий."""
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
            if executor is not None:
                try:
                    executor.shutdown(wait=True, cancel_futures=True)
                    self.log("ThreadPoolExecutor корректно завершён", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as shutdown_error:
                    self.log(f"Ошибка при shutdown ThreadPoolExecutor: {shutdown_error}", "error")

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

        if self._temp_file_cleanup_timer is not None:
            try:
                self._temp_file_cleanup_timer.stop()
                self.log("Таймер периодической очистки остановлен", "info")
            except (OSError, RuntimeError, TypeError, ValueError) as timer_error:
                self.log(f"Ошибка при остановке таймера: {timer_error}", "debug")

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
    "_temp_files_lock",
    "_temp_files_registry",
    "_register_temp_file",
    "_unregister_temp_file",
    "_cleanup_all_temp_files",
]
