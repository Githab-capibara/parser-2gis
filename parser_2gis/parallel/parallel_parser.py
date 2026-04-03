"""Модуль для параллельного парсинга городов.

Этот модуль предоставляет возможность одновременного парсинга нескольких URL
с использованием нескольких экземпляров браузера Chrome.

Оптимизации:
- Буферизация при работе с CSV файлами
- Улучшенная обработка прогресса
- Оптимизация памяти при слиянии файлов

ISSUE-002: Рефакторинг - выделены стратегии в strategies.py
"""

from __future__ import annotations

import asyncio
import atexit
import csv
import fcntl
import os
import shutil
import signal
import threading
import time
import types
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import BoundedSemaphore
from typing import TYPE_CHECKING, TextIO, cast
from collections.abc import Callable

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
    PROGRESS_UPDATE_INTERVAL,
)
from parser_2gis.logger import log_parser_finish, logger, print_progress
from parser_2gis.utils.temp_file_manager import (
    MAX_TEMP_FILES_MONITORING,
    ORPHANED_TEMP_FILE_AGE,
    TEMP_FILE_CLEANUP_INTERVAL,
    TempFileTimer,
    temp_file_manager,
)
from parser_2gis.validation import (
    validate_categories_config,
    validate_cities_config,
    validate_parallel_config,
)

# Импорты стратегий ISSUE-002
from parser_2gis.parallel.strategies import (
    ParseStrategy,
    UrlGenerationStrategy,
    ParserResult,
    UrlTuple,
)

# Импорты для типизации - откладываются до времени проверки типов
# для уменьшения связанности модуля
if TYPE_CHECKING:
    from parser_2gis.config import Configuration

# Константы
MEMORY_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100MB порог для проверки памяти
MAX_LOCK_ATTEMPTS = 50  # Максимальное число попыток получения lock файла (50 попыток с интервалом 1 сек = до 50 сек ожидания)


# =============================================================================
# MODULE-LEVEL HELPER FUNCTIONS (P0-11: Вынесены из merge_csv_files для тестируемости)
# =============================================================================


def _create_merge_fieldnames_cache() -> dict[tuple[str, ...], list[str]]:
    """Создаёт кэш для fieldnames CSV файлов.

    P0-9: LRU кэш для fieldnames чтобы не создавать новый словарь при каждом вызове merge.
    """
    return {}


@lru_cache(maxsize=256)
def _get_cached_fieldnames(fieldnames_tuple: tuple[str, ...], add_category: bool) -> list[str]:
    """Кэширует вычисление fieldnames с добавлением колонки категории.

    P0-9: LRU кэш на 256 записей для предотвращения повторных вычислений
    fieldnames при обработке множества CSV файлов с одинаковой структурой.
    """
    fieldnames = list(fieldnames_tuple)
    if add_category and "Категория" not in fieldnames:
        fieldnames.insert(0, "Категория")
    return fieldnames


@dataclass
class ParserThreadConfig:
    """Конфигурация для потока параллельного парсинга.

    Attributes:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Папка для сохранения результатов.
        config: Конфигурация парсера.
        max_workers: Максимальное количество одновременных браузеров.
        timeout_per_url: Таймаут на один URL в секундах.
        output_file: Имя выходного файла (опционально).

    """

    cities: list[dict]
    categories: list[dict]
    output_dir: str
    config: Configuration
    max_workers: int = 3
    timeout_per_url: int = DEFAULT_TIMEOUT
    output_file: str | None = None


# Регистрируем очистку через atexit для гарантированной очистки при аварийном завершении
atexit.register(temp_file_manager.cleanup_all)


class ParallelCityParser:
    """Параллельный парсер для парсинга городов по категориям.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельную папку output/, затем объединяются.

    ISSUE-002: Рефакторинг - использованы стратегии для соблюдения SRP.

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
        cities: list[dict],
        categories: list[dict],
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
        # D006: Валидация output_dir перед использованием
        if output_dir is None:
            raise ValueError("output_dir не может быть None")
        if not isinstance(output_dir, str):
            raise TypeError(f"output_dir должен быть строкой, получен {type(output_dir).__name__}")
        if not output_dir.strip():
            raise ValueError("output_dir не может быть пустой строкой")
        # Проверка на path traversal атаки
        if ".." in output_dir:
            raise ValueError("output_dir не должен содержать '..'")
        # Преобразуем в абсолютный путь
        output_dir_path = Path(output_dir)
        if not output_dir_path.is_absolute():
            output_dir = os.path.abspath(output_dir)
            output_dir_path = Path(output_dir)

        # H6: Централизация валидации в validation/data_validator.py
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

        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers
        self.timeout_per_url = timeout_per_url

        # Проверка существования output_dir и прав на запись
        self._validate_output_dir(self.output_dir, output_dir)

        # Статистика (все операции защищены _lock)
        self._stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}
        self._lock = threading.RLock()
        self._cancel_event = threading.Event()
        self._stop_event = threading.Event()

        # Валидация max_workers ПЕРЕД созданием семафора
        if max_workers < MIN_WORKERS:
            raise ValueError(
                f"max_workers должен быть не менее {MIN_WORKERS}, получено {max_workers}"
            )
        if max_workers > MAX_WORKERS:
            raise ValueError(
                f"max_workers не должен превышать {MAX_WORKERS}, получено {max_workers}"
            )

        # Семафор для контроля одновременного запуска браузеров
        self._browser_launch_semaphore = BoundedSemaphore(max_workers + 20)

        # Инициализация стратегий ISSUE-002
        self._url_strategy = UrlGenerationStrategy(cities, categories, self._lock)
        self._parse_strategy = ParseStrategy(
            output_dir=self.output_dir,
            config=config,
            timeout_per_url=timeout_per_url,
            browser_semaphore=self._browser_launch_semaphore,
            stats=self._stats,
            stats_lock=self._lock,
        )

        # Список для отслеживания временных файлов merge операции
        self._merge_temp_files: list[Path] = []
        self._merge_lock = threading.Lock()

        # Таймер очистки временных файлов
        self._temp_file_cleanup_timer: TempFileTimer | None = None
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

        self.log(
            f"Инициализирован парсер: {len(cities)} городов, {len(categories)} "
            f"категорий, max_workers={max_workers}",
            "info",
        )

    def _validate_output_dir(self, output_dir_path: Path, output_dir: str) -> None:
        """Проверяет директорию output_dir на существование и права записи.

        Args:
            output_dir_path: Путь к директории.
            output_dir: Исходная строка пути.

        Raises:
            ValueError: Если директория невалидна.

        """
        if output_dir_path.exists():
            if not output_dir_path.is_dir():
                raise ValueError(f"output_dir существует, но не является директорией: {output_dir}")
            test_file: Path | None = None
            try:
                test_file = output_dir_path / ".write_test"
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
                output_dir_path.mkdir(parents=True, exist_ok=True)
                test_file = output_dir_path / ".write_test"
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

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> list[UrlTuple]:
        """Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).

        """
        return self._url_strategy.generate_all_urls(self._stats)

    def generate_all_urls_lazy(self):
        """Генератор URL для парсинга (lazy loading).

        Yields:
            Кортеж (url, category_name, city_name).

        """
        yield from self._url_strategy.generate_all_urls_lazy()

    def parse_single_url(
        self,
        url: str,
        category_name: str,
        city_name: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ParserResult:
        """Парсит один URL и сохраняет результат в отдельный файл.

        ISSUE-002: Делегирует ParseStrategy.

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обновления прогресса.

        Returns:
            Кортеж (success, message).

        """
        return self._parse_strategy.parse_single_url(
            url=url,
            category_name=category_name,
            city_name=city_name,
            progress_callback=progress_callback,
            cancel_event=self._cancel_event,
        )

    # =====================================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ MERGE_CSV_FILES
    # =====================================================================

    def _get_csv_files_list(self, output_dir: Path, output_file_path: Path) -> list[Path]:
        """Получает список CSV файлов для объединения.

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
        """Извлекает название категории из имени CSV файла.

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

    def _acquire_merge_lock(self, lock_file_path: Path) -> tuple[TextIO | None, bool]:
        """Получает блокировку merge операции.

        CRITICAL 3: Улучшенная обработка race condition:
        1. Проверка возраста lock файла
        2. Очистка осиротевших блокировок
        3. Атомарное создание lock через O_CREAT | O_EXCL

        Args:
            lock_file_path: Путь к lock файлу.

        Returns:
            Кортеж (lock_file_handle, lock_acquired).

        """
        lock_file_handle = None
        lock_acquired = False

        try:
            # CRITICAL 3: Проверка и очистка осиротевших lock файлов
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        # Проверяем, активен ли процесс, создавший lock
                        try:
                            with open(lock_file_path, encoding="utf-8") as f:
                                lock_pid = int(f.read().strip())
                            # Проверяем, существует ли процесс
                            os.kill(lock_pid, 0)
                            # Процесс существует - это не осиротевший lock
                            self.log(
                                f"Lock файл существует (возраст: {lock_age:.0f} сек, PID: {lock_pid}), ожидаем..."
                            )
                        except (ProcessLookupError, ValueError, OSError):
                            # Процесс не существует - это осиротевший lock
                            self.log(
                                f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек, PID: {lock_pid})"
                            )
                            lock_file_path.unlink()
                    else:
                        self.log(
                            "Lock файл существует (возраст: %.0f сек), ожидаем...", level="warning"
                        )
                except OSError as e:
                    self.log(f"Ошибка проверки lock файла: {e}", level="debug")

            # CRITICAL 3: Атомарное создание lock файла через O_CREAT | O_EXCL
            start_time = time.time()
            lock_attempts = 0
            while not lock_acquired:
                lock_attempts += 1
                if lock_attempts > MAX_LOCK_ATTEMPTS:
                    self.log(
                        f"Превышено максимальное число попыток получения lock ({MAX_LOCK_ATTEMPTS})",
                        "error",
                    )
                    raise RuntimeError(
                        f"Не удалось получить lock файл после {MAX_LOCK_ATTEMPTS} попыток"
                    )
                lock_fd = None
                try:
                    # Атомарное создание файла - вернёт ошибку если файл уже существует
                    lock_fd = os.open(
                        str(lock_file_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o600
                    )
                    try:
                        lock_file_handle = os.fdopen(lock_fd, "w", encoding="utf-8")
                        lock_fd = None  # Теперь файл управляется через lock_file_handle

                        # Получаем exclusive lock
                        fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        lock_file_handle.write(f"{os.getpid()}\n")
                        lock_file_handle.flush()
                        lock_acquired = True
                        self.log("Lock file получен успешно", "debug")
                    finally:
                        # Гарантированное закрыие fd при любой ошибке
                        if lock_fd is not None:
                            try:
                                os.close(lock_fd)
                            except OSError:
                                pass
                except (OSError, FileExistsError):
                    if lock_file_handle is not None:
                        try:
                            lock_file_handle.close()
                        except (OSError, RuntimeError, TypeError, ValueError) as close_error:
                            self.log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                    lock_file_handle = None
                    lock_fd = None

                    # Проверяем не истёк ли таймаут
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

        return cast(tuple[TextIO | None, bool], (lock_file_handle, lock_acquired))

    def _cleanup_merge_lock(self, lock_file_handle: TextIO | None, lock_file_path: Path) -> None:
        """Очищает и удаляет lock файл.

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
        writer: csv.DictWriter | None,
        outfile: TextIO,
        buffer_size: int,
        batch_size: int,
        fieldnames_cache: dict[tuple[str, ...], list[str]],
    ) -> tuple[csv.DictWriter | None, int]:
        """Обрабатывает один CSV файл и добавляет данные в выходной файл.

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

        with open(csv_file, encoding="utf-8-sig", newline="", buffering=buffer_size) as infile:
            reader = csv.DictReader(infile)

            if not reader.fieldnames:
                self.log(f"Файл {csv_file} пуст или не имеет заголовков", "warning")
                return writer, 0

            fieldnames_key = tuple(reader.fieldnames)
            # P0-9: Сначала проверяем локальный кэш, затем используем lru_cache
            if fieldnames_key not in fieldnames_cache:
                fieldnames = _get_cached_fieldnames(fieldnames_key, True)
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

            batch_count = (batch_total // batch_size) + (1 if batch_total % batch_size else 0)
            self.log(
                f"Файл {csv_file.name} обработан (строк: {batch_total}, пакетов: {batch_count})",
                level="debug",
            )

            return writer, batch_total

    # =====================================================================
    # ОСНОВНОЙ МЕТОД ОБЪЕДИНЕНИЯ CSV ФАЙЛОВ
    # =====================================================================

    def merge_csv_files(
        self, output_file: str, progress_callback: Callable[[str], None] | None = None
    ) -> bool:
        """Объединяет все CSV файлы в один с добавлением колонки "Категория".

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

        files_to_delete: list[Path] = []
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"
        temp_file_created = False

        temp_file_manager.register(temp_output)

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
        sigint_registered = False
        sigterm_registered = False

        # P0-11: Выносим логику очистки в замыкание для передачи в signal handler
        merge_temp_files_ref = self._merge_temp_files
        merge_lock_ref = self._merge_lock
        log_method = self.log

        def _do_cleanup() -> None:
            """Функция очистки временных файлов при прерывании."""
            with merge_lock_ref:
                for temp_file in merge_temp_files_ref:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                            log_method(
                                f"Временный файл удалён при прерывании: {temp_file}", "debug"
                            )
                    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                        log_method(
                            f"Ошибка при удалении временного файла {temp_file}: {cleanup_error}",
                            "error",
                        )

        def _signal_handler(signum: int, frame: types.FrameType | None) -> None:
            """Обработчик сигналов прерывания."""
            self.log(f"Получен сигнал {signum}, очистка временных файлов...", "warning")
            _do_cleanup()
            if callable(old_sigint_handler):
                old_sigint_handler(signum, frame)

        # Регистрируем обработчики сигналов
        try:
            signal.signal(signal.SIGINT, _signal_handler)
            sigint_registered = True
            signal.signal(signal.SIGTERM, _signal_handler)
            sigterm_registered = True
        except (OSError, ValueError) as sig_error:
            self.log(f"Не удалось зарегистрировать обработчики сигналов: {sig_error}", "warning")

        try:
            with self._merge_lock:
                self._merge_temp_files.append(temp_output)

            with open(
                temp_output, "w", encoding=output_encoding, newline="", buffering=buffer_size
            ) as outfile:
                temp_file_created = True
                writer = None
                total_rows = 0
                # P0-9: Используем функцию для создания кэша fieldnames
                fieldnames_cache = _create_merge_fieldnames_cache()

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
            # Вложенная функция _do_cleanup определена выше в merge_csv_files
            # Вызываем inline очистку
            with self._merge_lock:
                for temp_file in self._merge_temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except OSError:
                        pass
            return False

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            return False

        finally:
            self._cleanup_merge_lock(lock_file_handle, lock_file_path)

            # ВОССТАНОВЛЕНИЕ СИГНАЛОВ ВСЕГДА через try/finally
            if sigint_registered:
                try:
                    signal.signal(signal.SIGINT, old_sigint_handler)
                except (OSError, RuntimeError, TypeError, ValueError) as restore_error:
                    self.log(
                        f"Ошибка при восстановлении SIGINT обработчика: {restore_error}", "error"
                    )

            if sigterm_registered:
                try:
                    signal.signal(signal.SIGTERM, old_sigterm_handler)
                except (OSError, RuntimeError, TypeError, ValueError) as restore_error:
                    self.log(
                        f"Ошибка при восстановлении SIGTERM обработчика: {restore_error}", "error"
                    )

            temp_file_manager.unregister(temp_output)

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
        progress_callback: Callable[[int, int, str], None] | None = None,
        merge_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг всех городов и категорий.

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

                except (KeyboardInterrupt, asyncio.CancelledError):
                    self.log(
                        "⚠️ Парсинг прерван пользователем (KeyboardInterrupt/CancelledError)",
                        "warning",
                    )
                    self._cancel_event.set()
                    for f in futures:
                        f.cancel()
                    return False

                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    failed_count += 1
                    self.log(
                        f"❌ Исключение при парсинге {city_name} - {category_name}: {e}", "error"
                    )

        except (KeyboardInterrupt, asyncio.CancelledError):
            self.log(
                "⚠️ Парсинг прерван пользователем (KeyboardInterrupt/CancelledError в цикле)",
                "warning",
            )
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
    """Поток для параллельного парсинга городов.

    Использует композицию вместо наследования для избежания проблем с MRO.
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        output_file: str | None = None,
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

        # Группировка параметров в dataclass для удобства
        thread_config = ParserThreadConfig(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=max_workers,
            timeout_per_url=timeout_per_url,
            output_file=output_file,
        )

        # Инициализация парсера (композиция)
        self._parser = ParallelCityParser(
            thread_config.cities,
            thread_config.categories,
            thread_config.output_dir,
            thread_config.config,
            thread_config.max_workers,
            thread_config.timeout_per_url,
        )

        self._result: bool | None = None
        self._output_file = thread_config.output_file

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

    def get_result(self) -> bool | None:
        """Возвращает результат парсинга."""
        return self._result


# =============================================================================
# РЕ-ЭКСПОРТ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ С ТЕСТАМИ
# =============================================================================

__all__ = ["ParallelCityParser", "ParallelCityParserThread"]
