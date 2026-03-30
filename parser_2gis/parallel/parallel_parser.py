"""
Модуль для параллельного парсинга городов.

Этот модуль предоставляет возможность одновременного парсинга нескольких URL
с использованием нескольких экземпляров браузера Chrome.

Оптимизации:
- Буферизация при работе с CSV файлами
- Улучшенная обработка прогресса
- Оптимизация памяти при слиянии файлов
"""

from __future__ import annotations

import atexit
import csv
import fcntl
import gc
import os
import random
import shutil
import signal
import threading
import time
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import BoundedSemaphore
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

import psutil

from parser_2gis.chrome.exceptions import ChromeException
from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_LOCK_FILE_AGE,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MERGE_BATCH_SIZE,
    MERGE_BUFFER_SIZE,
    MERGE_LOCK_TIMEOUT,
    MIN_TIMEOUT,
    MIN_WORKERS,
)
from parser_2gis.logger import log_parser_finish, logger, print_progress
from parser_2gis.parallel.progress_tracker import PROGRESS_UPDATE_INTERVAL
from parser_2gis.parser import get_parser
from parser_2gis.utils.temp_file_manager import (
    MAX_TEMP_FILES_MONITORING,
    ORPHANED_TEMP_FILE_AGE,
    TEMP_FILE_CLEANUP_INTERVAL,
    TempFileTimer,
    cleanup_all_temp_files,
    register_temp_file,
    temp_file_manager,
    unregister_temp_file,
)
from parser_2gis.utils.url_utils import generate_category_url
from parser_2gis.writer import get_writer

if TYPE_CHECKING:
    from .config import Configuration


# =============================================================================
# КОНСТАНТЫ ДЛЯ УНИКАЛЬНЫХ ИМЁН ФАЙЛОВ
# =============================================================================

# Максимальное количество попыток создания уникального имени файла
MAX_UNIQUE_NAME_ATTEMPTS: int = 10


# =============================================================================
# TEMP FILE MANAGEMENT (using temp_file_manager module)
# =============================================================================

# Регистрируем очистку через atexit для гарантированной очистки при аварийном завершении
atexit.register(cleanup_all_temp_files)


class ParallelCityParser:
    """
    Параллельный парсер для парсинга городов по категориям.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельную папку output/, затем объединяются.

    Args:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Папка для сохранения результатов.
        config: Конфигурация.
        max_workers: Максимальное количество одновременных браузеров.
        timeout_per_url: Таймаут на один URL в секундах (по умолчанию 300).
    """

    def __init__(
        self,
        cities: List[dict],
        categories: List[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Инициализирует параллельный парсер городов.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            output_dir: Папка для сохранения результатов.
            config: Конфигурация парсера.
            max_workers: Максимальное количество одновременных браузеров.
            timeout_per_url: Таймаут на один URL в секундах.

        Raises:
            ValueError: Если входные данные невалидны.
        """
        # Валидация входных данных: проверка списка городов
        if not cities:
            raise ValueError("Список городов не может быть пустым")

        # Валидация входных данных: проверка списка категорий
        if not categories:
            raise ValueError("Список категорий не может быть пустым")

        # Валидация max_workers: проверка на разумные пределы
        if max_workers < MIN_WORKERS:
            raise ValueError(f"max_workers должен быть не менее {MIN_WORKERS}")
        if max_workers > MAX_WORKERS:
            raise ValueError(
                f"max_workers слишком большой: {max_workers} (максимум: {MAX_WORKERS}). "
                f"Превышение лимита может привести к чрезмерному потреблению "
                f"памяти и снижению производительности."
            )

        # Валидация timeout_per_url: проверка на разумные пределы
        if timeout_per_url < MIN_TIMEOUT:
            raise ValueError(f"timeout_per_url должен быть не менее {MIN_TIMEOUT} секунд")
        if timeout_per_url > MAX_TIMEOUT:
            raise ValueError(
                f"timeout_per_url слишком большой: {timeout_per_url} секунд "
                f"(максимум: {MAX_TIMEOUT} секунд = {MAX_TIMEOUT // 3600} ч.). "
                f"Превышение лимита может указывать на проблемы с сетью или зависание."
            )

        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers
        self.timeout_per_url = timeout_per_url

        # Проверка существования output_dir и прав на запись
        if self.output_dir.exists():
            if not self.output_dir.is_dir():
                raise ValueError(f"output_dir существует, но не является директорией: {output_dir}")
            test_file: Optional[Path] = None
            try:
                test_file = self.output_dir / ".write_test"
                test_file.touch()
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Нет прав на запись в директорию: {output_dir}. Ошибка: {e}"
                ) from e
            finally:
                if test_file is not None and test_file.exists():
                    try:
                        test_file.unlink()
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        logger.warning(
                            "Не удалось удалить тестовый файл %s: %s", test_file, cleanup_error
                        )
        else:
            test_file = None
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                test_file = self.output_dir / ".write_test"
                test_file.touch()
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Не удалось создать директорию output_dir: {output_dir}. Ошибка: {e}"
                ) from e
            finally:
                if test_file is not None and test_file.exists():
                    try:
                        test_file.unlink()
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        logger.warning(
                            "Не удалось удалить тестовый файл %s: %s", test_file, cleanup_error
                        )

        # Статистика (все операции защищены _lock)
        self._stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}
        # Блокировка для потокобезопасного доступа к _stats и логгирования
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

        # Флаг отмены
        self._cancel_event = threading.Event()

        # Событие для координации остановки (для тестов keyboard_interrupt_handling)
        self._stop_event = threading.Event()

        # Семафор для контроля одновременного запуска браузеров
        # Большое значение для поддержки 40+ потоков
        self._browser_launch_semaphore = BoundedSemaphore(max_workers + 20)

        # Список для отслеживания временных файлов merge операции
        self._merge_temp_files: List[Path] = []
        # Блокировка для потокобезопасного доступа к временным файлам
        self._merge_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов
        self._temp_file_cleanup_timer: Optional[TempFileTimer] = None
        if self.config.parallel.use_temp_file_cleanup:  # type: ignore[attr-defined]
            try:
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

        # Логирование успешной инициализации
        self.log(
            f"Инициализирован парсер: {len(cities)} городов, {len(categories)} "
            f"категорий, max_workers={max_workers}",
            "info",
        )

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> List[Tuple[str, str, str]]:
        """
        Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).
        """
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
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Парсит один URL и сохраняет результат в отдельный файл.

        Использует временный файл для защиты от race condition:
        - Запись происходит во временный файл с уникальным именем
        - После успешного завершения файл переименовывается в целевое имя
        - При ошибке временный файл удаляется

        Для установки таймаута используется ThreadPoolExecutor с future.result(timeout=...),
        что является потокобезопасной альтернативой signal.alarm().

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (успех, сообщение).
        """
        # Проверка доступной памяти перед началом парсинга
        available_memory = psutil.virtual_memory().available
        if available_memory < 100 * 1024 * 1024:  # Менее 100MB
            logger.warning(
                f"Low memory ({available_memory // 1024 // 1024}MB), skipping {city_name} - {category_name}"
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
        temp_fd = None
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

        def do_parse() -> Tuple[bool, str]:
            """
            Выполняет парсинг внутри отдельного потока.

            Returns:
                Кортеж (успех, сообщение).
            """
            self.log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )

            # Добавляем случайную задержку ПЕРЕД получением семафора
            # Для 40+ потоков нужна большая задержка для равномерного распределения
            initial_delay = random.uniform(
                self.config.parallel.initial_delay_min, self.config.parallel.initial_delay_max
            )
            time.sleep(initial_delay)

            # Семафор для контроля одновременного запуска браузеров
            # Освобождаем после завершения работы с браузером
            self._browser_launch_semaphore.acquire()
            active_count = self.max_workers - self._browser_launch_semaphore._value + 1
            self.log(
                f"Семафор получен. Активных браузеров: {active_count}/{self.max_workers}", "debug"
            )
            try:
                # Дополнительная задержка для распределения нагрузки при запуске
                launch_delay = random.uniform(
                    self.config.parallel.launch_delay_min, self.config.parallel.launch_delay_max
                )
                self.log(f"Задержка перед запуском Chrome: {launch_delay:.2f} сек", "debug")
                time.sleep(launch_delay)

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
                            self.log(
                                f"Попытка {attempt + 1}/{max_retries} не удалась: {chrome_error}. "
                                f"Повтор через {retry_delay:.1f} сек...",
                                "warning",
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            raise chrome_error

            except ChromeException as chrome_error:
                self._browser_launch_semaphore.release()
                self.log(f"Ошибка Chrome после {max_retries} попыток: {chrome_error}", "error")
                try:
                    if temp_filepath.exists():
                        temp_filepath.unlink()
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass

                with self._lock:
                    self._stats["failed"] += 1

                return False, f"Ошибка Chrome: {chrome_error}"

            except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as init_error:
                self._browser_launch_semaphore.release()
                self.log(f"Ошибка инициализации для {url}: {init_error}", "error")
                try:
                    if temp_filepath.exists():
                        temp_filepath.unlink()
                        self.log(
                            f"Временный файл удалён после ошибки инициализации: {temp_filename}",
                            "debug",
                        )
                except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                    self.log(
                        f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                        "warning",
                    )

                with self._lock:
                    self._stats["failed"] += 1

                return False, f"Ошибка инициализации: {init_error}"

            try:
                with parser:
                    with writer:
                        try:
                            parser.parse(writer)
                        except MemoryError as memory_error:
                            logger.error(f"Memory error while parsing {url}: {memory_error}")
                            # Освобождаем кэш если есть
                            if hasattr(parser, "_cache"):
                                parser._cache.clear()
                            # Принудительный GC
                            gc.collect()
                            raise
                        finally:
                            logger.debug("Завершена очистка ресурсов парсера")
            finally:
                # Освобождаем семафор после завершения работы с браузером
                # Это позволяет следующей задаче начать запуск Chrome
                self._browser_launch_semaphore.release()

            # Переименовываем временный файл в целевой
            move_success = False
            try:
                os.replace(str(temp_filepath), str(filepath))
                move_success = True
            except OSError as replace_error:
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. "
                    f"Используем shutil.move",
                    "debug",
                )
                try:
                    shutil.move(str(temp_filepath), str(filepath))
                    move_success = True
                except (OSError, RuntimeError, TypeError, ValueError) as move_error:
                    self.log(
                        f"Не удалось переместить временный файл {temp_filename}: {move_error}",
                        "error",
                    )
                    try:
                        if temp_filepath.exists():
                            temp_filepath.unlink()
                            self.log(
                                f"Временный файл удалён после ошибки перемещения: {temp_filename}",
                                "debug",
                            )
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        self.log(
                            f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                            "warning",
                        )
                    raise move_error

            if move_success:
                self.log(f"Временный файл переименован: {temp_filename} → {filename}", "debug")

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

                    try:
                        if temp_filepath.exists():
                            temp_filepath.unlink()
                            self.log(
                                f"Временный файл удалён после таймаута: {temp_filename}", "debug"
                            )
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        self.log(
                            f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                            "warning",
                        )

                    with self._lock:
                        self._stats["failed"] += 1
                        success_count = self._stats["success"]
                        failed_count = self._stats["failed"]

                    if progress_callback:
                        progress_callback(success_count, failed_count, "N/A")

                    return False, f"Таймаут: {self.timeout_per_url} сек"

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")

            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(f"Временный файл удалён после ошибки: {temp_filename}", "debug")
            except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                self.log(
                    f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}", "warning"
                )

            with self._lock:
                self._stats["failed"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, "N/A")

            return False, str(e)

    # =====================================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ MERGE_CSV_FILES
    # =====================================================================

    def _get_csv_files_list(self, output_dir: Path, output_file_path: Path) -> List[Path]:
        """
        Получает список CSV файлов для объединения.

        Args:
            output_dir: Директория с CSV файлами.
            output_file_path: Путь к целевому файлу (исключается из списка).

        Returns:
            Отсортированный список CSV файлов.
        """
        csv_files = list(output_dir.glob("*.csv"))

        if output_file_path.exists():
            csv_files = [f for f in csv_files if f != output_file_path]
            self.log(f"Исключен объединенный файл из списка: {output_file_path.name}", "debug")

        csv_files.sort(key=lambda x: x.name)
        return csv_files

    def _extract_category_from_filename(self, csv_file: Path) -> str:
        """
        Извлекает название категории из имени CSV файла.

        Args:
            csv_file: Путь к CSV файлу.

        Returns:
            Название категории.
        """
        stem = csv_file.stem
        last_underscore_idx = stem.rfind("_")

        if last_underscore_idx > 0:
            return stem[last_underscore_idx + 1 :].replace("_", " ")

        category = stem.replace("_", " ")
        self.log(f"Предупреждение: файл {csv_file.name} не содержит категорию в имени", "warning")
        return category

    def _acquire_merge_lock(self, lock_file_path: Path) -> Tuple[Optional[typing.TextIO], bool]:
        """
        Получает блокировку merge операции.

        Args:
            lock_file_path: Путь к lock файлу.

        Returns:
            Кортеж (lock_file_handle, lock_acquired).
        """
        lock_file_handle = None
        lock_acquired = False

        try:
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        self.log(
                            f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)",
                            "debug",
                        )
                        lock_file_path.unlink()
                    else:
                        self.log(
                            f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                            "warning",
                        )
                except OSError as e:
                    self.log(f"Ошибка проверки lock файла: {e}", "debug")

            start_time = time.time()
            while not lock_acquired:
                lock_file_handle = None
                try:
                    lock_file_handle = open(lock_file_path, "w", encoding="utf-8")
                    fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_file_handle.write(f"{os.getpid()}\n")
                    lock_file_handle.flush()
                    lock_acquired = True
                    self.log("Lock file получен успешно", "debug")
                except (IOError, OSError):
                    if lock_file_handle:
                        try:
                            lock_file_handle.close()
                        except (OSError, RuntimeError, TypeError, ValueError) as close_error:
                            self.log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                        lock_file_handle = None

                    if time.time() - start_time > MERGE_LOCK_TIMEOUT:
                        self.log(f"Таймаут ожидания lock файла ({MERGE_LOCK_TIMEOUT} сек)", "error")
                        return None, False

                    time.sleep(1)

        except (OSError, RuntimeError, TypeError, ValueError) as lock_error:
            self.log(f"Ошибка при получении lock файла: {lock_error}", "error")
            if lock_file_handle:
                try:
                    lock_file_handle.close()
                except (OSError, RuntimeError, TypeError, ValueError) as close_error:
                    self.log(f"Ошибка при закрытии lock файла: {close_error}", "error")
            return None, False

        return typing.cast(Tuple[Optional[typing.TextIO], bool], (lock_file_handle, lock_acquired))

    def _cleanup_merge_lock(
        self, lock_file_handle: Optional[typing.TextIO], lock_file_path: Path
    ) -> None:
        """
        Очищает и удаляет lock файл.

        Args:
            lock_file_handle: Дескриптор lock файла.
            lock_file_path: Путь к lock файлу.
        """
        try:
            if lock_file_handle:
                fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
                lock_file_handle.close()
                lock_file_path.unlink()
                self.log("Lock файл удалён", "debug")
        except (OSError, RuntimeError, TypeError, ValueError) as lock_error:
            self.log(f"Ошибка при удалении lock файла: {lock_error}", "debug")

    def _process_single_csv_file(
        self,
        csv_file: Path,
        writer: Optional["csv.DictWriter"],
        outfile: "typing.TextIO",
        buffer_size: int,
        batch_size: int,
        fieldnames_cache: Dict[Tuple[str, ...], List[str]],
    ) -> Tuple[Optional["csv.DictWriter"], int]:
        """
        Обрабатывает один CSV файл и добавляет данные в выходной файл.

        Args:
            csv_file: Путь к исходному CSV файлу.
            writer: Текущий CSV writer.
            outfile: Выходной файл.
            buffer_size: Размер буфера.
            batch_size: Размер пакета для записи.
            fieldnames_cache: Кэш полей для файлов.

        Returns:
            Кортеж (writer, total_rows).
        """
        category_name = self._extract_category_from_filename(csv_file)

        with open(csv_file, "r", encoding="utf-8-sig", newline="", buffering=buffer_size) as infile:
            reader = csv.DictReader(infile)

            if not reader.fieldnames:
                self.log(f"Файл {csv_file} пуст или не имеет заголовков", "warning")
                return writer, 0

            fieldnames_key = tuple(reader.fieldnames)
            if fieldnames_key not in fieldnames_cache:
                fieldnames = list(reader.fieldnames)
                if "Категория" not in fieldnames:
                    fieldnames.insert(0, "Категория")
                fieldnames_cache[fieldnames_key] = fieldnames
            else:
                fieldnames = fieldnames_cache[fieldnames_key]

            if writer is None:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

            batch = []
            batch_total = 0

            for row in reader:
                row_with_category = {"Категория": category_name, **row}
                batch.append(row_with_category)

                if len(batch) >= batch_size:
                    writer.writerows(batch)
                    batch_total += len(batch)
                    batch.clear()

            if batch:
                writer.writerows(batch)
                batch_total += len(batch)

            self.log(
                f"Файл {csv_file.name} обработан (строк: {batch_total}, пакетов: {
                    (batch_total // batch_size) + (1 if batch_total % batch_size else 0)
                })",
                level="debug",
            )

            return writer, batch_total

    # =====================================================================
    # ОСНОВНОЙ МЕТОД ОБЪЕДИНЕНИЯ CSV ФАЙЛОВ
    # =====================================================================

    def merge_csv_files(
        self, output_file: str, progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Объединяет все CSV файлы в один с добавлением колонки "Категория".

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.
        """
        self.log("Начало объединения CSV файлов...", "info")

        output_file_path = Path(output_file)
        csv_files = self._get_csv_files_list(self.output_dir, output_file_path)

        if not csv_files:
            self.log("Не найдено CSV файлов для объединения", "warning")
            return False

        self.log(f"Найдено {len(csv_files)} CSV файлов для объединения", "info")

        files_to_delete: List[Path] = []
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"
        temp_file_created = False

        register_temp_file(temp_output)

        lock_file_path = self.output_dir / ".merge.lock"
        lock_file_handle = None
        lock_acquired = False

        output_encoding = self.config.writer.encoding
        buffer_size = MERGE_BUFFER_SIZE
        batch_size = MERGE_BATCH_SIZE

        # БЛОКИРОВКА 1: Получаем lock file
        lock_file_handle, lock_acquired = self._acquire_merge_lock(lock_file_path)
        if not lock_acquired:
            return False

        # БЛОКИРОВКА 2: Signal handler для очистки при KeyboardInterrupt
        old_sigint_handler = signal.getsignal(signal.SIGINT)
        old_sigterm_handler = signal.getsignal(signal.SIGTERM)

        def cleanup_temp_files():
            """Функция очистки временных файлов при прерывании."""
            with self._merge_lock:
                for temp_file in self._merge_temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                            self.log(f"Временный файл удалён при прерывании: {temp_file}", "debug")
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        self.log(
                            f"Ошибка при удалении временного файла {temp_file}: {cleanup_error}",
                            "error",
                        )

        def signal_handler(signum, frame):
            """Обработчик сигналов прерывания."""
            self.log(f"Получен сигнал {signum}, очистка временных файлов...", "warning")
            cleanup_temp_files()
            if callable(old_sigint_handler):
                old_sigint_handler(signum, frame)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            with self._merge_lock:
                self._merge_temp_files.append(temp_output)

            with open(
                temp_output, "w", encoding=output_encoding, newline="", buffering=buffer_size
            ) as outfile:
                temp_file_created = True
                writer = None
                total_rows = 0
                fieldnames_cache: Dict[Tuple[str, ...], List[str]] = {}

                for csv_file in csv_files:
                    if self._cancel_event.is_set():
                        self.log("Объединение отменено пользователем", "warning")
                        try:
                            temp_output.unlink()
                        except (OSError, RuntimeError, TypeError, ValueError) as e:
                            self.log(f"Не удалось удалить временный файл при отмене: {e}", "debug")
                        return False

                    if progress_callback:
                        progress_callback(f"Обработка: {csv_file.name}")

                    writer, batch_total = self._process_single_csv_file(
                        csv_file=csv_file,
                        writer=writer,
                        outfile=outfile,
                        buffer_size=buffer_size,
                        batch_size=batch_size,
                        fieldnames_cache=fieldnames_cache,
                    )

                    if batch_total == 0:
                        continue

                    total_rows += batch_total
                    files_to_delete.append(csv_file)

                if writer is None:
                    self.log(
                        "Все CSV файлы пустые или не имеют заголовков. Объединение невозможно.",
                        "warning",
                    )

                    try:
                        temp_output.unlink()
                        self.log("Временный файл удалён (все файлы пустые)", "debug")
                    except (OSError, RuntimeError, TypeError, ValueError) as e:
                        self.log(f"Не удалось удалить временный файл: {e}", "debug")

                    self._cleanup_merge_lock(lock_file_handle, lock_file_path)
                    return False

                self.log(f"Объединение завершено. Всего записей: {total_rows}", "info")

            try:
                os.replace(str(temp_output), str(output_file_path))
            except OSError as replace_error:
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. "
                    f"Используем shutil.move",
                    "debug",
                )
                try:
                    shutil.move(str(temp_output), str(output_file_path))
                except (OSError, RuntimeError, TypeError, ValueError) as move_error:
                    self.log(
                        f"Не удалось переместить временный файл в {output_file}: {move_error}",
                        "error",
                    )
                    try:
                        if temp_output.exists():
                            temp_output.unlink()
                            self.log("Временный файл удалён после ошибки перемещения", "debug")
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        self.log(f"Не удалось удалить временный файл: {cleanup_error}", "debug")
                    raise move_error

            for csv_file in files_to_delete:
                try:
                    csv_file.unlink()
                    self.log(f"Исходный файл удалён: {csv_file.name}", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as e:
                    self.log(f"Не удалось удалить файл {csv_file}: {e}", "warning")

            self.log(f"Объединение завершено. Файлы удалены ({len(files_to_delete)} шт.)", "info")
            temp_file_created = False

            self._cleanup_merge_lock(lock_file_handle, lock_file_path)
            return True

        except KeyboardInterrupt:
            self.log("Объединение прервано пользователем (KeyboardInterrupt)", "warning")
            cleanup_temp_files()
            return False

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            return False

        finally:
            self._cleanup_merge_lock(lock_file_handle, lock_file_path)

            try:
                signal.signal(signal.SIGINT, old_sigint_handler)
                signal.signal(signal.SIGTERM, old_sigterm_handler)
            except (OSError, RuntimeError, TypeError, ValueError) as restore_error:
                self.log(
                    f"Ошибка при восстановлении обработчиков сигналов: {restore_error}", "error"
                )

            unregister_temp_file(temp_output)

            if temp_file_created and temp_output.exists():
                try:
                    temp_output.unlink()
                    self.log("Временный файл удалён в блоке finally (защита от утечек)", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                    self.log(
                        f"Не удалось удалить временный файл в finally: {cleanup_error}", "warning"
                    )

            with self._merge_lock:
                if temp_output in self._merge_temp_files:
                    self._merge_temp_files.remove(temp_output)

    def run(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        merge_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Запускает параллельный парсинг всех городов и категорий.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса парсинга.
            merge_callback: Функция обратного вызова для обновления прогресса объединения.

        Returns:
            True если успешно.
        """
        start_time = time.time()
        total_tasks = len(self.cities) * len(self.categories)
        if self._temp_file_cleanup_timer is not None:
            try:
                self._temp_file_cleanup_timer.start()
                self.log("Запущен таймер периодической очистки временных файлов", "info")
            except (OSError, RuntimeError, TypeError, ValueError) as timer_error:
                self.log(f"Не удалось запустить таймер очистки: {timer_error}", "warning")

        self.log(f"🚀 Запуск параллельного парсинга ({self.max_workers} потока)", "info")
        self.log(f"📍 Города: {[c['name'] for c in self.cities]}", "info")
        self.log(f"📑 Категории: {len(self.categories)}", "info")
        self.log(f"📊 Всего задач: {total_tasks}", "info")

        all_urls = self.generate_all_urls()

        if not all_urls:
            self.log("❌ Нет URL для парсинга", "error")
            return False

        success_count = 0
        failed_count = 0
        last_progress_time = time.time()

        self.log(f"⏱️ Таймаут на один URL: {self.timeout_per_url} секунд", "info")

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

            for idx, future in enumerate(as_completed(futures), 1):
                url, category_name, city_name = futures[future]

                try:
                    success, result = future.result(timeout=self.timeout_per_url)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        self.log(f"❌ Не удалось: {city_name} - {category_name}: {result}", "error")

                    current_time = time.time()
                    if current_time - last_progress_time >= PROGRESS_UPDATE_INTERVAL or idx == len(
                        futures
                    ):
                        progress_bar = print_progress(
                            success_count + failed_count, len(futures), prefix="   Прогресс"
                        )
                        self.log(progress_bar, "info")
                        last_progress_time = current_time

                except FuturesTimeoutError:
                    failed_count += 1
                    self.log(
                        f"❌ Таймаут при парсинге {city_name} - {category_name} "
                        f"({self.timeout_per_url} сек)",
                        "error",
                    )

                except KeyboardInterrupt:
                    self.log("⚠️ Парсинг прерван пользователем (KeyboardInterrupt)", "warning")
                    self._cancel_event.set()
                    for f in futures:
                        f.cancel()
                    return False

                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    failed_count += 1
                    self.log(
                        f"❌ Исключение при парсинге {city_name} - {category_name}: {e}", "error"
                    )

        except KeyboardInterrupt:
            self.log("⚠️ Парсинг прерван пользователем (KeyboardInterrupt в цикле)", "warning")
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

        self.log(f"🏁 Парсинг завершён. Успешно: {success_count}, Ошибок: {failed_count}", "info")

        if success_count > 0:
            self.log("📁 Начало объединения результатов...", "info")
            merge_success = self.merge_csv_files(output_file, merge_callback)

            if not merge_success:
                self.log("❌ Не удалось объединить CSV файлы", "error")
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
            self.log("⚠️ Нет успешных результатов для объединения", "warning")
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
        """Возвращает статистику парсинга.

        Returns:
            Словарь со статистикой парсинга.
        """
        with self._lock:
            return dict(self._stats)


class ParallelCityParserThread:
    """
    Поток для параллельного парсинга городов.

    Использует композицию вместо наследования для избежания проблем с MRO.
    """

    def __init__(
        self,
        cities: List[dict],
        categories: List[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        output_file: Optional[str] = None,
    ) -> None:
        """Инициализирует поток для параллельного парсинга.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            output_dir: Папка для сохранения результатов.
            config: Конфигурация парсера.
            max_workers: Максимальное количество одновременных браузеров.
            timeout_per_url: Таймаут на один URL в секундах.
            output_file: Имя выходного файла (опционально).
        """
        # Инициализация базового класса Thread
        super().__init__()

        # Инициализация парсера (композиция)
        self._parser = ParallelCityParser(
            cities, categories, output_dir, config, max_workers, timeout_per_url
        )

        self._result: Optional[bool] = None
        self._output_file = output_file

    @property
    def output_dir(self) -> Path:
        """Проксирует доступ к output_dir парсера."""
        return self._parser.output_dir

    def log(self, message: str, level: str = "info") -> None:
        """Проксирует доступ к методу log парсера."""
        self._parser.log(message, level)

    def run(self) -> None:  # type: ignore[override]
        """Точка входа потока."""
        try:
            output_file = self._output_file or str(self.output_dir / "merged_result.csv")
            self._result = self._parser.run(output_file=output_file)
        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка в потоке параллельного парсинга: {e}", "error")
            self._result = False

    def get_result(self) -> Optional[bool]:
        """Возвращает результат парсинга."""
        return self._result


# =============================================================================
# РЕ-ЭКСПОРТ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ С ТЕСТАМИ
# =============================================================================

_temp_files_lock = temp_file_manager._lock
_temp_files_registry = temp_file_manager._registry


def _register_temp_file(file_path: Path) -> None:
    """Регистрирует временный файл для отслеживания."""
    temp_file_manager.register(file_path)


def _unregister_temp_file(file_path: Path) -> None:
    """Удаляет временный файл из реестра."""
    temp_file_manager.unregister(file_path)


def _cleanup_all_temp_files() -> None:
    """Очищает все временные файлы."""
    temp_file_manager.cleanup_all()


__all__ = [
    "ParallelCityParser",
    "ParallelCityParserThread",
    "_temp_files_lock",
    "_temp_files_registry",
    "_register_temp_file",
    "_unregister_temp_file",
    "_cleanup_all_temp_files",
]
