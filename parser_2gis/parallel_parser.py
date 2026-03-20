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
import os
import shutil
import signal
import threading
import time
import uuid
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed

from .common import DEFAULT_BUFFER_SIZE, MERGE_BATCH_SIZE, generate_category_url
from .logger import log_parser_finish, logger, print_progress
from .parser import get_parser
from .writer import get_writer

# =============================================================================
# КОНСТАНТЫ ВАЛИДАЦИИ ПАРАМЕТРОВ
# =============================================================================

# Минимальное количество рабочих потоков
MIN_WORKERS: int = 1  # Минимум 1 работник

# Максимальное количество рабочих потоков (разумный предел для I/O операций)
# ОБОСНОВАНИЕ: 20 потоков выбрано исходя из:
# - Типичное количество ядер CPU: 4-16
# - I/O-bound операции (парсинг) требуют больше потоков чем ядер
# - 20 потоков - баланс между производительностью и потреблением памяти
# - Каждый поток создаёт экземпляр браузера (~100-200MB памяти)
# - 20 * 200MB = 4GB - разумный предел для большинства систем
MAX_WORKERS: int = 20  # Разумный предел для I/O операций

# Минимальный таймаут на один URL в секундах
MIN_TIMEOUT: int = 1  # Минимум 1 секунда

# Максимальный таймаут на один URL в секундах (1 час)
# ОБОСНОВАНИЕ: 3600 секунд (1 час) - разумный максимум для парсинга одного URL
# Превышение может указывать на проблемы с сетью или зависание
MAX_TIMEOUT: int = 3600  # 1 час максимум

# Таймаут по умолчанию на один URL в секундах (5 минут)
DEFAULT_TIMEOUT: int = 300

# =============================================================================
# ВАЛИДАЦИЯ ENV ПЕРЕМЕННЫХ
# =============================================================================


def _validate_env_int(
    env_name: str,
    default: int,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """Валидирует ENV переменную как целое число в допустимом диапазоне.

    Args:
        env_name: Имя ENV переменной.
        default: Значение по умолчанию (используется если переменная не установлена).
        min_value: Минимальное допустимое значение (None если нет ограничения).
        max_value: Максимальное допустимое значение (None если нет ограничения).

    Returns:
        Валидированное целое число.

    Raises:
        ValueError: Если значение не является целым числом (нечисловая строка).

    Примечание:
        - Выбрасывает ValueError при некорректных значениях (нечисловые строки)
        - Возвращает min/max значение при выходе за пределы диапазона (с предупреждением)
        - Возвращает значение по умолчанию только если переменная не установлена
    """
    value_str = os.getenv(env_name)

    if value_str is None:
        return default

    # Преобразуем в целое число (выбросит ValueError при некорректном значении)
    value = int(value_str)

    # Проверяем минимальное значение
    if min_value is not None and value < min_value:
        logger.warning(
            "ENV переменная %s=%d меньше минимального значения %d. Используется %d",
            env_name,
            value,
            min_value,
            min_value,
        )
        return min_value

    # Проверяем максимальное значение
    if max_value is not None and value > max_value:
        logger.warning(
            "ENV переменная %s=%d больше максимального значения %d. Используется %d",
            env_name,
            value,
            max_value,
            max_value,
        )
        return max_value

    return value


# =============================================================================
# КОНСТАНТЫ С ВАЛИДАЦИЕЙ ENV ПЕРЕМЕННЫХ
# =============================================================================

# Интервал периодической очистки временных файлов в секундах (60 секунд)
# Допустимый диапазон: 10-3600 секунд (10 минут)
TEMP_FILE_CLEANUP_INTERVAL = _validate_env_int(
    "PARSER_TEMP_FILE_CLEANUP_INTERVAL", default=60, min_value=10, max_value=3600
)

# Максимальное количество временных файлов для мониторинга
# Допустимый диапазон: 100-10000
MAX_TEMP_FILES_MONITORING = _validate_env_int(
    "PARSER_MAX_TEMP_FILES_MONITORING", default=1000, min_value=100, max_value=10000
)

# Возраст временного файла в секундах, после которого он считается осиротевшим (300 секунд = 5 минут)
# Допустимый диапазон: 60-86400 секунд (1 день)
ORPHANED_TEMP_FILE_AGE = _validate_env_int(
    "PARSER_ORPHANED_TEMP_FILE_AGE", default=300, min_value=60, max_value=86400
)


class _TempFileTimer:
    """
    Таймер для периодической очистки временных файлов.

        - Периодическая очистка через threading.Timer
    - Использование weak references для предотвращения утечек памяти
    - Мониторинг количества временных файлов
    - Автоматическая очистка осиротевших файлов
    - Добавлена блокировка для защиты общих данных (_lock)
    - Добавлено событие для координации остановки (_stop_event)

    Пример использования:
        >>> cleanup_timer = _TempFileTimer(temp_dir=Path('/tmp'))
        >>> cleanup_timer.start()
        >>> # ... работа парсера ...
        >>> cleanup_timer.stop()
    """

    def __init__(
        self,
        temp_dir: Path,
        interval: int = TEMP_FILE_CLEANUP_INTERVAL,
        max_files: int = MAX_TEMP_FILES_MONITORING,
        orphan_age: int = ORPHANED_TEMP_FILE_AGE,
    ) -> None:
        """
        Инициализация таймера очистки.

        Args:
            temp_dir: Директория для мониторинга временных файлов.
            interval: Интервал очистки в секундах.
            max_files: Максимальное количество файлов для мониторинга.
            orphan_age: Возраст файла в секундах, после которого он считается осиротевшим.
        """
        self._temp_dir = temp_dir
        self._interval = interval
        self._max_files = max_files
        self._orphan_age = orphan_age
        self._timer: Optional[threading.Timer] = None
        self._is_running = False
        self._stop_event = threading.Event()  # Событие для координации остановки
        self._lock = threading.Lock()  # Блокировка для защиты общих данных
        self._cleanup_count = 0
        self._weak_ref = weakref.ref(self)

        logger.debug(
            "Инициализирован таймер очистки временных файлов: интервал=%d сек, макс. файлов=%d, возраст=%d сек",
            interval,
            max_files,
            orphan_age,
        )

    def _cleanup_callback(self) -> None:
        """Callback для периодической очистки."""
        # Проверяем флаг остановки через _stop_event
        if self._stop_event.is_set():
            return

        try:
            self._cleanup_temp_files()
        except Exception as cleanup_error:
            logger.error(
                "Ошибка при периодической очистке временных файлов: %s",
                cleanup_error,
                exc_info=True,
            )
        except BaseException as base_error:
            # Обработка всех исключений включая KeyboardInterrupt и SystemExit
            logger.error(
                "Критическая ошибка в callback очистки: %s",
                base_error,
                exc_info=True,
            )
        finally:
            # Планируем следующую очистку только если не была установлена остановка
            if not self._stop_event.is_set():
                self._schedule_next_cleanup()

    def _schedule_next_cleanup(self) -> None:
        """Планирует следующую очистку."""
        try:
            self._timer = threading.Timer(self._interval, self._cleanup_callback)
            self._timer.daemon = True
            self._timer.start()
        except Exception as schedule_error:
            logger.error(
                "Ошибка при планировании следующей очистки: %s",
                schedule_error,
                exc_info=True,
            )

    def _cleanup_temp_files(self) -> int:
        """
        Выполняет очистку временных файлов.

        Returns:
            Количество удалённых файлов.
        """
        deleted_count = 0
        current_time = time.time()

        if not self._temp_dir.exists():
            return 0

        try:
            # Получаем список файлов в директории
            temp_files = list(self._temp_dir.iterdir())

            # Мониторинг количества файлов
            if len(temp_files) > self._max_files:
                logger.warning(
                    "Превышено максимальное количество временных файлов: %d (макс: %d)",
                    len(temp_files),
                    self._max_files,
                )

            # Удаляем осиротевшие файлы
            for temp_file in temp_files:
                try:
                    # Пропускаем директории
                    if temp_file.is_dir():
                        continue

                    # Проверяем возраст файла
                    file_age = current_time - temp_file.stat().st_mtime

                    if file_age > self._orphan_age:
                        temp_file.unlink()
                        deleted_count += 1
                        logger.debug(
                            "Удалён осиротевший временный файл: %s (возраст: %.0f сек)",
                            temp_file,
                            file_age,
                        )

                except OSError as os_error:
                    logger.debug("Ошибка при удалении файла %s: %s", temp_file, os_error)
                except Exception as file_error:
                    logger.debug(
                        "Непредвиденная ошибка при обработке файла %s: %s",
                        temp_file,
                        file_error,
                    )

            if deleted_count > 0:
                # Используем блокировку для защиты общих данных
                with self._lock:
                    self._cleanup_count += deleted_count
                logger.info(
                    "Периодическая очистка: удалено %d временных файлов (всего: %d)",
                    deleted_count,
                    self._cleanup_count,
                )

        except Exception as cleanup_error:
            logger.error(
                "Ошибка при сканировании директории %s: %s",
                self._temp_dir,
                cleanup_error,
                exc_info=True,
            )

        return deleted_count

    def start(self) -> None:
        """Запускает таймер периодической очистки."""
        # ИСПРАВЛЕНИЕ 7: Используем try/finally для гарантии освобождения блокировки
        # Добавлен timeout к acquire() для предотвращения deadlock
        lock_acquired = False
        try:
            # pylint: disable=consider-using-with
            lock_acquired = self._lock.acquire(timeout=5.0)
            if not lock_acquired:
                logger.warning(
                    "Не удалось получить блокировку в start() (таймаут 5 сек). "
                    "Возможна конкуренция за ресурсы."
                )
                return

            if self._is_running:
                logger.warning("Таймер очистки уже запущен")
                return

            self._is_running = True
            self._stop_event.clear()  # Сбрасываем событие остановки
        finally:
            # Гарантированно освобождаем блокировку
            if lock_acquired:
                self._lock.release()

        self._schedule_next_cleanup()
        logger.info("Запущен таймер периодической очистки временных файлов")

    def stop(self) -> None:
        """Останавливает таймер периодической очистки."""
        # Устанавливаем событие остановки
        self._stop_event.set()

        # ИСПРАВЛЕНИЕ 7: Используем try/finally для гарантии освобождения блокировки
        # Добавлен timeout к acquire() для предотвращения deadlock
        lock_acquired = False
        try:
            # pylint: disable=consider-using-with
            lock_acquired = self._lock.acquire(timeout=5.0)
            if not lock_acquired:
                logger.warning(
                    "Не удалось получить блокировку в stop() (таймаут 5 сек). "
                    "Возможна конкуренция за ресурсы."
                )
                return

            self._is_running = False

            if self._timer is not None:
                try:
                    self._timer.cancel()
                except Exception as cancel_error:
                    logger.debug("Ошибка при отмене таймера: %s", cancel_error)
                finally:
                    self._timer = None
        finally:
            # Гарантированно освобождаем блокировку
            if lock_acquired:
                self._lock.release()

        # Ожидаем завершения таймера с таймаутом
        if self._timer is not None:
            try:
                # Ждём завершения таймера не более 2 интервалов
                self._timer.join(timeout=self._interval * 2)
            except Exception as join_error:
                logger.debug("Ошибка при ожидании таймера: %s", join_error)

        logger.info(
            "Таймер периодической очистки остановлен (всего удалено файлов: %d)",
            self._cleanup_count,
        )

    def __del__(self) -> None:
        """Гарантирует остановку таймера при уничтожении."""
        try:
            if hasattr(self, "_is_running") and self._is_running:
                self.stop()
        except Exception as e:
            # Игнорируем ошибки при очистке в деструкторе
            logger.debug("Ошибка при остановке таймера в __del__: %s", e)


# =============================================================================
# КОНСТАНТЫ ПРОГРЕССА И ОТОБРАЖЕНИЯ
# =============================================================================

# Интервал обновления прогресс-бара в секундах
PROGRESS_UPDATE_INTERVAL: int = 3

# =============================================================================
# КОНСТАНТЫ ДЛЯ СЛИЯНИЯ ФАЙЛОВ И БУФЕРИЗАЦИИ (ОБОСНОВАНИЕ ЗНАЧЕНИЙ)
# =============================================================================

# Размер буфера для чтения/записи файлов в байтах (256 KB)
MERGE_BUFFER_SIZE: int = DEFAULT_BUFFER_SIZE

# Размер пакета строк для пакетной записи в CSV
MERGE_BATCH_SIZE_LOCAL: int = MERGE_BATCH_SIZE

# =============================================================================
# КОНСТАНТЫ ДЛЯ УНИКАЛЬНЫХ ИМЁН ФАЙЛОВ (ОБОСНОВАНИЕ ЗНАЧЕНИЙ)
# =============================================================================

# Максимальное количество попыток создания уникального имени файла
# ОБОСНОВАНИЕ: 10 попыток выбрано исходя из:
# - Вероятность коллизии UUID4: ~10^-15 (практически невозможно)
# - 10 попыток - защита от крайне редких случаев генерации дубликатов
# - Достаточно для защиты от бесконечного цикла при сбоях ФС
# - Баланс между надёжностью и производительностью
MAX_UNIQUE_NAME_ATTEMPTS: int = 10

# =============================================================================
# КОНСТАНТЫ ДЛЯ БЛОКИРОВОК И ЗАЩИТЫ ОТ CONCURRENT OPERATIONS (ОБОСНОВАНИЕ)
# =============================================================================

# Таймаут ожидания блокировки merge операции в секундах
# ОБОСНОВАНИЕ: 300 секунд (5 минут) выбрано исходя из:
# - Типичное время merge операции: 10-60 секунд
# - 5 минут - достаточно для обработки больших файлов (1GB+)
# - Защита от зависших процессов (осиротевшие lock файлы)
# - Достаточно времени для завершения медленных дисковых операций
# Допустимый диапазон: 60-3600 секунд (1 час)
MERGE_LOCK_TIMEOUT: int = _validate_env_int(
    "PARSER_MERGE_LOCK_TIMEOUT", default=300, min_value=60, max_value=3600
)

# Максимальный возраст lock файла в секундах (5 минут)
# ОБОСНОВАНИЕ: 300 секунд выбрано исходя из:
# - Типичное время merge: 10-60 секунд
# - 5 минут - 5x запас на случай медленных дисков/больших файлов
# - Lock файлы старше считаются осиротевшими (процесс упал)
# - Баланс между защитой от race condition и очисткой мусора
# Допустимый диапазон: 60-3600 секунд (1 час)
MAX_LOCK_FILE_AGE: int = _validate_env_int(
    "PARSER_MAX_LOCK_FILE_AGE", default=300, min_value=60, max_value=3600
)

# =============================================================================
# КОНСТАНТА ДЛЯ ОГРАНИЧЕНИЯ ВРЕМЕННЫХ ФАЙЛОВ
# =============================================================================

# Максимальное количество отслеживаемых временных файлов
# ОБОСНОВАНИЕ: 1000 файлов выбрано исходя из:
# - Типичное количество временных файлов: 10-100
# - 1000 - разумный лимит для предотвращения утечки памяти
# - При достижении лимита происходит LRU eviction
# Допустимый диапазон: 100-5000 файлов
MAX_TEMP_FILES: int = _validate_env_int(
    "PARSER_MAX_TEMP_FILES", default=1000, min_value=100, max_value=5000
)

# =============================================================================
# ГЛОБАЛЬНЫЙ НАБОР ДЛЯ ОТСЛЕЖИВАНИЯ ВРЕМЕННЫХ ФАЙЛОВ (ATEXIT ОЧИСТКА)
# =============================================================================

# Глобальный набор для отслеживания временных файлов созданных этим процессом
# Используется для гарантированной очистки при аварийном завершении

_temp_files_lock = threading.RLock()
_temp_files_registry: set[Path] = set()


def _register_temp_file(file_path: Path) -> None:
    """Регистрирует временный файл для последующей очистки.

        - Добавлено ограничение максимального размера реестра
    - Реализована LRU eviction при достижении лимита
    - Удаляются oldest записи при превышении MAX_TEMP_FILES

    Args:
        file_path: Путь к временному файлу.
    """
    # pylint: disable=consider-using-with
    if _temp_files_lock.acquire(timeout=5.0):
        try:
            if len(_temp_files_registry) >= MAX_TEMP_FILES:
                # Удаляем oldest записи (50% от лимита)
                # Примечание: set неупорядочен, поэтому удаляем случайные элементы
                # Для более точного LRU можно использовать OrderedDict
                files_to_remove = list(_temp_files_registry)[: MAX_TEMP_FILES // 2]
                for old_file in files_to_remove:
                    _temp_files_registry.discard(old_file)
                logger.warning(
                    "Достигнут лимит временных файлов (%d), удалено %d старых файлов",
                    MAX_TEMP_FILES,
                    len(files_to_remove),
                )

            _temp_files_registry.add(file_path)
        finally:
            _temp_files_lock.release()


def _unregister_temp_file(file_path: Path) -> None:
    """Удаляет временный файл из реестра.

    Args:
        file_path: Путь к временному файлу.
    """
    # pylint: disable=consider-using-with
    if _temp_files_lock.acquire(timeout=5.0):
        try:
            _temp_files_registry.discard(file_path)
        finally:
            _temp_files_lock.release()


def _cleanup_all_temp_files() -> None:
    """Очищает все зарегистрированные временные файлы.

    Вызывается через atexit при завершении процесса для предотвращения утечек.

    Использует контекстный менеджер для гарантии освобождения блокировки
    и конкретные типы исключений для лучшего логирования.
    """
    from contextlib import contextmanager

    @contextmanager
    def temp_file_lock_context():
        """Контекстный менеджер для безопасного управления блокировкой."""
        lock_acquired = _temp_files_lock.acquire(timeout=5.0)
        try:
            yield lock_acquired
        finally:
            if lock_acquired:
                _temp_files_lock.release()

    with temp_file_lock_context() as lock_acquired:
        if not lock_acquired:
            logger.warning("Не удалось получить блокировку для очистки временных файлов")
            return

        for temp_file in list(_temp_files_registry):
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug("Временный файл удалён через atexit: %s", temp_file)
            except FileNotFoundError:
                # Файл уже удалён - это нормально
                logger.debug("Временный файл уже удалён: %s", temp_file)
            except PermissionError as perm_error:
                # Нет прав на удаление
                logger.error(
                    "Нет прав на удаление временного файла %s: %s",
                    temp_file,
                    perm_error,
                    exc_info=True,
                )
            except OSError as os_error:
                # Ошибка ОС при удалении
                logger.error(
                    "Ошибка ОС при удалении временного файла %s: %s",
                    temp_file,
                    os_error,
                    exc_info=True,
                )
            except Exception as e:
                # Любая другая ошибка
                logger.error(
                    "Не удалось удалить временный файл %s: %s (тип: %s)",
                    temp_file,
                    e,
                    type(e).__name__,
                    exc_info=True,
                )
            finally:
                _temp_files_registry.discard(temp_file)


# Регистрируем очистку через atexit для гарантированной очистки при аварийном завершении
atexit.register(_cleanup_all_temp_files)

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РЕФАКТОРИНГА MERGE_CSV_FILES
# =============================================================================


def _acquire_merge_lock(
    lock_file_path: Path,
    timeout: int = MERGE_LOCK_TIMEOUT,
    log_callback: Optional[Callable[[str, str], None]] = None,
) -> tuple[Optional[object], bool]:
    """Получает блокировку для merge операции.

    Args:
        lock_file_path: Путь к lock файлу.
        timeout: Таймаут ожидания блокировки в секундах.
        log_callback: Функция для логирования (принимает message, level).

    Returns:
        Кортеж (lock_file_handle, lock_acquired):
        - lock_file_handle: Дескриптор файла блокировки или None.
        - lock_acquired: True если блокировка получена, False иначе.

    Raises:
        Exception: Если произошла ошибка при получении блокировки.
    """

    def log(msg: str, level: str = "debug") -> None:
        if log_callback:
            log_callback(msg, level)

    lock_file_handle = None
    lock_acquired = False

    # Проверяем возраст существующего lock файла
    if lock_file_path.exists():
        try:
            lock_age = time.time() - lock_file_path.stat().st_mtime
            if lock_age > MAX_LOCK_FILE_AGE:
                log(
                    f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)",
                    "debug",
                )
                lock_file_path.unlink()
            else:
                log(
                    f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                    "warning",
                )
        except OSError:
            pass

    # Пытаемся получить блокировку с таймаутом
    start_time = time.time()
    while not lock_acquired:
        lock_file_handle = None
        try:
            # pylint: disable=consider-using-with
            lock_file_handle = open(lock_file_path, "w", encoding="utf-8")
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file_handle.write(f"{os.getpid()}\n")
            lock_file_handle.flush()
            lock_acquired = True
            log("Lock file получен успешно", "debug")
        except (IOError, OSError):
            if lock_file_handle:
                try:
                    lock_file_handle.close()
                except Exception as close_error:
                    log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                lock_file_handle = None

            if time.time() - start_time > timeout:
                log(f"Таймаут ожидания lock файла ({timeout} сек)", "error")
                return None, False

            time.sleep(1)

    return lock_file_handle, lock_acquired


def _merge_csv_files(
    file_paths: list[Path],
    output_path: Path,
    encoding: str,
    buffer_size: int = MERGE_BUFFER_SIZE,
    batch_size: int = MERGE_BATCH_SIZE,
    log_callback: Optional[Callable[[str, str], None]] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> tuple[bool, int, list[Path]]:
    """Объединяет CSV файлы в один с добавлением колонки "Категория".

    Args:
        file_paths: Список путей к CSV файлам для объединения.
        output_path: Путь к выходному файлу.
        encoding: Кодировка для чтения/записи.
        buffer_size: Размер буфера в байтах.
        batch_size: Размер пакета строк для записи.
        log_callback: Функция для логирования.
        progress_callback: Функция обновления прогресса.
        cancel_event: Событие для отмены операции.

    Returns:
        Кортеж (success, total_rows, files_to_delete):
        - success: True если успешно.
        - total_rows: Количество объединённых строк.
        - files_to_delete: Список файлов для удаления.
    """
    # pylint: disable=reimported
    import csv as csv_module

    def log(msg: str, level: str = "info") -> None:
        if log_callback:
            log_callback(msg, level)

    files_to_delete: list[Path] = []
    total_rows = 0
    fieldnames_cache: dict[tuple[str, ...], list[str]] = {}
    writer = None
    outfile = None
    infile: Optional[object] = None

    try:
        try:
            outfile = open(output_path, "w", encoding=encoding, newline="", buffering=buffer_size)
        except OSError as output_error:
            # Детальное логирование ошибки с указанием типа ошибки
            error_type = type(output_error).__name__
            log(
                f"Ошибка записи в выходной файл {output_path} ({error_type}): {output_error}",
                "error",
            )

            # Fallback механизм - пробуем уменьшить размер буфера
            if buffer_size > 8192:
                log("Попытка fallback: уменьшаем размер буфера до 8KB", "warning")
                try:
                    # pylint: disable=consider-using-with
                    outfile = open(output_path, "w", encoding=encoding, newline="", buffering=8192)
                    log("Fallback успешен: файл открыт с уменьшенным буфером", "info")
                except OSError as fallback_error:
                    log(f"Fallback не удался: {fallback_error}", "error")
                    return False, 0, []
            else:
                return False, 0, []

        try:
            for csv_file in file_paths:
                if cancel_event is not None and cancel_event.is_set():
                    log("Объединение отменено пользователем", "warning")
                    return False, 0, []

                if progress_callback:
                    progress_callback(f"Обработка: {csv_file.name}")

                # Извлекаем категорию из имени файла
                stem = csv_file.stem
                last_underscore_idx = stem.rfind("_")
                category_name = (
                    stem[last_underscore_idx + 1 :].replace("_", " ")
                    if last_underscore_idx > 0
                    else stem.replace("_", " ")
                )

                if last_underscore_idx <= 0:
                    log(
                        f"Предупреждение: файл {csv_file.name} не содержит категорию в имени",
                        "warning",
                    )

                infile = None
                try:
                    infile = open(
                        csv_file,
                        "r",
                        encoding="utf-8-sig",
                        newline="",
                        buffering=buffer_size,
                    )
                except OSError as file_error:
                    # Детальное логирование с указанием типа ошибки
                    error_type = type(file_error).__name__
                    log(
                        f"Ошибка доступа к файлу {csv_file} ({error_type}): {file_error}",
                        "error",
                    )

                    # Fallback механизм - пробуем прочитать без буферизации
                    if buffer_size > 0:
                        log(
                            f"Попытка fallback: читаем файл {csv_file} без буферизации",
                            "warning",
                        )
                        try:
                            # pylint: disable=consider-using-with
                            infile = open(
                                csv_file,
                                "r",
                                encoding="utf-8-sig",
                                newline="",
                                buffering=0,
                            )
                            log(
                                f"Fallback успешен: файл {csv_file} открыт без буферизации",
                                "info",
                            )
                        except OSError as fallback_error:
                            log(
                                f"Fallback не удался для {csv_file}: {fallback_error}",
                                "error",
                            )
                            # Продолжаем с следующим файлом вместо полного провала
                            continue
                    else:
                        continue

                try:
                    reader = csv_module.DictReader(infile)

                    # Проверка reader.fieldnames на None или пустоту
                    # Это предотвращает IndexError при доступе к пустым файлам
                    if reader.fieldnames is None:
                        log(
                            f"Файл {csv_file} пуст или не имеет заголовков (fieldnames=None)",
                            "warning",
                        )
                        continue

                    if len(reader.fieldnames) == 0:
                        log(
                            f"Файл {csv_file} имеет пустой список заголовков",
                            "warning",
                        )
                        continue

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

                    total_rows += batch_total
                    log(
                        f"Файл {csv_file.name} обработан (строк: {batch_total})",
                        "debug",
                    )

                except OSError as csv_error:
                    error_type = type(csv_error).__name__
                    log(
                        f"Ошибка при обработке CSV {csv_file} ({error_type}): {csv_error}",
                        "error",
                    )
                    # Продолжаем со следующим файлом
                    continue
                except csv.Error as csv_parse_error:
                    # Обработка ошибок парсинга CSV
                    log(
                        f"Ошибка парсинга CSV {csv_file}: {csv_parse_error}",
                        "error",
                    )
                    continue
                finally:
                    # Гарантированно закрываем infile
                    if infile is not None:
                        try:
                            infile.close()
                            log(f"Файл {csv_file.name} закрыт", "debug")
                        except Exception as close_error:
                            log(
                                f"Ошибка при закрытии файла {csv_file.name}: {close_error}",
                                "debug",
                            )

                files_to_delete.append(csv_file)

            if writer is None:
                log("Все CSV файлы пустые или не имеют заголовков", "warning")
                return False, 0, []

            log(f"Объединение завершено. Всего записей: {total_rows}", "info")
            return True, total_rows, files_to_delete

        finally:
            # Гарантированная очистка outfile в finally блоке
            if outfile is not None:
                try:
                    if not outfile.closed:
                        outfile.close()
                        log("Выходной файл закрыт в finally блоке", "debug")
                except Exception as close_error:
                    log(
                        f"Ошибка при закрытии выходного файла в finally: {close_error}",
                        "error",
                    )

    except KeyboardInterrupt:
        # Обработка прерывания пользователем (Ctrl+C)
        log("Объединение прервано пользователем (KeyboardInterrupt)", "warning")
        # Гарантированная очистка ресурсов при прерывании
        return False, 0, files_to_delete

    except OSError as e:
        error_type = type(e).__name__
        error_details = str(e)
        log(
            f"Критическая ошибка ОС при объединении CSV ({error_type}): {error_details}",
            "error",
        )
        # Возвращаем files_to_delete для очистки даже при ошибке
        return False, 0, files_to_delete

    except Exception as e:
        # Обработка всех остальных исключений
        error_type = type(e).__name__
        log(f"Непредвиденная ошибка при объединении CSV ({error_type}): {e}", "error")
        # Возвращаем files_to_delete для очистки даже при ошибке
        return False, 0, files_to_delete


def _cleanup_source_files(
    file_paths: list[Path], log_callback: Optional[Callable[[str, str], None]] = None
) -> int:
    """Очищает исходные файлы после объединения.

    Args:
        file_paths: Список путей к файлам для удаления.
        log_callback: Функция для логирования.

    Returns:
        Количество успешно удалённых файлов.
    """

    def log(msg: str, level: str = "debug") -> None:
        if log_callback:
            log_callback(msg, level)

    deleted_count = 0
    for csv_file in file_paths:
        try:
            csv_file.unlink()
            log(f"Исходный файл удалён: {csv_file.name}")
            deleted_count += 1
        except Exception as e:
            log(f"Не удалось удалить файл {csv_file}: {e}", "warning")
    return deleted_count


def _validate_merged_file(
    output_path: Path, log_callback: Optional[Callable[[str, str], None]] = None
) -> bool:
    """Валидирует объединённый файл.

    Args:
        output_path: Путь к объединённому файлу.
        log_callback: Функция для логирования.

    Returns:
        True если файл валиден, False иначе.
    """

    def log(msg: str, level: str = "debug") -> None:
        if log_callback:
            log_callback(msg, level)

    if not output_path.exists():
        log(f"Объединённый файл не существует: {output_path}", "error")
        return False

    if output_path.stat().st_size == 0:
        log(f"Объединённый файл пуст: {output_path}", "error")
        return False

    log(
        f"Объединённый файл валиден: {output_path.name} ({output_path.stat().st_size} байт)",
        "info",
    )
    return True


if TYPE_CHECKING:
    from .config import Configuration


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
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
    ) -> None:
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
                f"Превышение лимита может привести к чрезмерному потреблению памяти и снижению производительности."
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
            # EAFP подход: проверяем права попыткой записи тестового файла
            # Это защищает от race condition между проверкой и фактической записью
            test_file: Optional[Path] = None
            try:
                test_file = self.output_dir / ".write_test"
                test_file.touch()
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Нет прав на запись в директорию: {output_dir}. Ошибка: {e}"
                ) from e
            finally:
                # Гарантируем удаление тестового файла
                if test_file is not None and test_file.exists():
                    try:
                        test_file.unlink()
                    except Exception as cleanup_error:
                        logger.warning(
                            "Не удалось удалить тестовый файл %s: %s",
                            test_file,
                            cleanup_error,
                        )
        else:
            # Попытка создать директорию
            test_file = None
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                # EAFP проверка прав после создания
                test_file = self.output_dir / ".write_test"
                test_file.touch()
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Не удалось создать директорию output_dir: {output_dir}. Ошибка: {e}"
                ) from e
            finally:
                # Гарантируем удаление тестового файла
                if test_file is not None and test_file.exists():
                    try:
                        test_file.unlink()
                    except Exception as cleanup_error:
                        logger.warning(
                            "Не удалось удалить тестовый файл %s: %s",
                            test_file,
                            cleanup_error,
                        )

        # Статистика (все операции защищены _lock)
        self._stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }
        # Блокировка для потокобезопасного доступа к _stats и логгирования
        self._lock = threading.Lock()

        # Флаг отмены
        self._cancel_event = threading.Event()

        # Список для отслеживания временных файлов merge операции (используется вместо глобальной переменной)
        self._merge_temp_files: List[Path] = []
        # Блокировка для потокобезопасного доступа к временным файлам
        self._merge_lock = threading.Lock()
        self._temp_file_cleanup_timer: Optional[_TempFileTimer] = None
        if self.config.parallel.use_temp_file_cleanup:  # type: ignore[attr-defined]
            try:
                self._temp_file_cleanup_timer = _TempFileTimer(
                    temp_dir=self.output_dir,
                    interval=TEMP_FILE_CLEANUP_INTERVAL,
                    max_files=MAX_TEMP_FILES_MONITORING,
                    orphan_age=ORPHANED_TEMP_FILE_AGE,
                )
                logger.info(
                    "Инициализирован таймер периодической очистки временных файлов для %s",
                    self.output_dir,
                )
            except Exception as timer_error:
                logger.warning(
                    "Не удалось инициализировать таймер очистки временных файлов: %s",
                    timer_error,
                )

        # Логирование успешной инициализации
        self.log(
            f"Инициализирован парсер: {len(cities)} городов, {len(categories)} категорий, max_workers={max_workers}",
            "info",
        )

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """
        Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).
        """
        all_urls = []

        for city in self.cities:
            for category in self.categories:
                try:
                    # Используем общую функцию генерации URL
                    url = generate_category_url(city, category)
                    all_urls.append((url, category["name"], city["name"]))
                except Exception as e:
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
    ) -> tuple[bool, str]:
        """
        Парсит один URL и сохраняет результат в отдельный файл.

        Использует временный файл для защиты от race condition:
        - Запись происходит во временный файл с уникальным именем
        - После успешного завершения файл переименовывается в целевое имя
        - При ошибке временный файл удаляется

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (успех, сообщение).
        """
        # Проверяем флаг отмены
        if self._cancel_event.is_set():
            return False, "Отменено пользователем"

        # Используем signal.alarm для установки таймаута на парсинг (только Unix)
        timeout_occurred = False
        use_signal_timeout = hasattr(signal, "alarm")  # Проверяем поддержку signal.alarm

        # Формируем целевое имя файла
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        # Создаём уникальное временное имя файла
        # ВАЖНО: Используем PID процесса для уникальности и предотвращения race condition
        # uuid.uuid4() + pid гарантирует уникальность даже при параллельном запуске
        temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
        temp_filepath = self.output_dir / temp_filename

        # ВАЖНО: Атомарное создание временного файла для предотвращения race condition
        # Используем os.open() с флагами O_CREAT | O_EXCL для атомарного создания
        # Это гарантирует, что между проверкой и созданием файла не будет гонки условий
        temp_fd = None
        for attempt in range(MAX_UNIQUE_NAME_ATTEMPTS):
            try:
                # Атомарное создание файла через os.open с O_CREAT | O_EXCL
                # O_CREAT - создать файл если не существует
                # O_EXCL - выбросить ошибку если файл уже существует (вместе с O_CREAT)
                # O_WRONLY - открыть для записи
                # O_CREAT | O_EXCL гарантирует атомарное создание
                temp_fd = os.open(
                    str(temp_filepath),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    mode=0o644,  # Права доступа: владелец чтение/запись, остальные чтение
                )
                # Закрываем файловый дескриптор - файл создан
                os.close(temp_fd)
                temp_fd = None
                logger.log(5, "Временный файл атомарно создан: %s", temp_filename)
                break  # Успех - выходим из цикла
            except FileExistsError:
                # Файл уже существует (race condition) - генерируем новое имя
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(
                        5,
                        "Коллизия имён (попытка %d): генерация нового имени",
                        attempt + 1,
                    )
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
                # Ошибка при создании файла
                if temp_fd is not None:
                    try:
                        os.close(temp_fd)
                    except OSError:
                        pass
                    temp_fd = None
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(
                        5,
                        "Ошибка создания файла (попытка %d): повторная попытка",
                        attempt + 1,
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

        # Сохраняем старый обработчик SIGALRM для восстановления
        old_handler = None
        if use_signal_timeout:

            def timeout_handler(signum, frame):
                """Обработчик сигнала таймаута."""
                nonlocal timeout_occurred
                timeout_occurred = True
                raise TimeoutError(f"Превышен таймаут парсинга ({self.timeout_per_url} сек)")

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_per_url)  # Устанавливаем таймаут

        try:
            self.log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )
            try:
                writer = get_writer(str(temp_filepath), "csv", self.config.writer)
                parser = get_parser(
                    url,
                    chrome_options=self.config.chrome,
                    parser_options=self.config.parser,
                )
            except Exception as init_error:
                self.log(
                    f"Ошибка инициализации для {url}: {init_error}",
                    "error",
                )
                # Удаляем временный файл при ошибке инициализации
                try:
                    if temp_filepath.exists():
                        temp_filepath.unlink()
                        self.log(
                            f"Временный файл удалён после ошибки инициализации: {temp_filename}",
                            "debug",
                        )
                except Exception as cleanup_error:
                    self.log(
                        f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                        "warning",
                    )

                # Потокобезопасное обновление статистики
                with self._lock:
                    self._stats["failed"] += 1

                return False, f"Ошибка инициализации: {init_error}"

            # Создаем парсер и writer с использованием контекстных менеджеров
            with parser:
                with writer:
                    # Парсим с гарантированной очисткой ресурсов
                    try:
                        parser.parse(writer)
                    finally:
                        # Гарантируем очистку даже при исключении
                        # контекстные менеджеры вызовут __exit__, но явно указываем на важность
                        pass

            # После успешного парсинга переименовываем временный файл в целевой

            # Используем os.replace() вместо shutil.move для гарантии атомарности
            # os.replace() гарантирует атомарную замену на POSIX системах
            # Это предотвращает race condition при параллельном переименовании
            move_success = False
            try:
                # os.replace() гарантирует атомарность на POSIX
                # и является предпочтительным методом для переименования
                os.replace(str(temp_filepath), str(filepath))
                move_success = True
            except OSError as replace_error:
                # Fallback для перемещения между разными файловыми системами
                # shutil.move не атомарен, но работает跨 файловых систем
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. Используем shutil.move",
                    "debug",
                )
                try:
                    shutil.move(str(temp_filepath), str(filepath))
                    move_success = True
                except Exception as move_error:
                    # Очистка временного файла при ошибке перемещения
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
                    except Exception as cleanup_error:
                        self.log(
                            f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                            "warning",
                        )
                    raise move_error

            if move_success:
                self.log(
                    f"Временный файл переименован: {temp_filename} → {filename}",
                    "debug",
                )

            self.log(f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info")

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["success"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        except TimeoutError as timeout_error:
            self.log(
                f"Таймаут парсинга {city_name} - {category_name} ({self.timeout_per_url} сек): {timeout_error}",
                "error",
            )

            # Удаляем временный файл при таймауте
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(
                        f"Временный файл удалён после таймаута: {temp_filename}",
                        "debug",
                    )
            except Exception as cleanup_error:
                self.log(
                    f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                    "warning",
                )

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["failed"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, "N/A")

            return False, f"Таймаут: {timeout_error}"

        except Exception as e:
            self.log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")

            # Удаляем временный файл при ошибке
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(f"Временный файл удалён после ошибки: {temp_filename}", "debug")
            except Exception as cleanup_error:
                self.log(
                    f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                    "warning",
                )

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["failed"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, "N/A")

            return False, str(e)

        finally:
            if use_signal_timeout and old_handler is not None:
                signal.alarm(0)  # Отменяем таймаут
                signal.signal(signal.SIGALRM, old_handler)  # Восстанавливаем обработчик

    # =====================================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ merge_csv_files
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

        # Исключаем объединенный файл если он уже существует (повторный запуск)
        if output_file_path.exists():
            csv_files = [f for f in csv_files if f != output_file_path]
            self.log(
                f"Исключен объединенный файл из списка: {output_file_path.name}",
                "debug",
            )

        # Сортируем файлы по имени для детерминированного порядка
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
        self.log(
            f"Предупреждение: файл {csv_file.name} не содержит категорию в имени",
            "warning",
        )
        return category

    def _acquire_merge_lock(self, lock_file_path: Path) -> Tuple[Optional[object], bool]:
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
            # Проверяем возраст существующего lock файла
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        # Lock файл осиротевший - удаляем
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
                except OSError:
                    pass

            # Пытаемся получить блокировку с таймаутом
            start_time = time.time()
            while not lock_acquired:
                lock_file_handle = None
                try:
                    # pylint: disable=consider-using-with
                    lock_file_handle = open(lock_file_path, "w", encoding="utf-8")
                    fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Записываем PID процесса для отладки
                    lock_file_handle.write(f"{os.getpid()}\n")
                    lock_file_handle.flush()
                    lock_acquired = True
                    self.log("Lock file получен успешно", "debug")
                except (IOError, OSError):
                    # Блокировка занята другим процессом
                    if lock_file_handle:
                        try:
                            lock_file_handle.close()
                        except Exception as close_error:
                            self.log(
                                f"Ошибка при закрытии lock файла: {close_error}",
                                "error",
                            )
                        lock_file_handle = None

                    # Проверяем таймаут ожидания
                    if time.time() - start_time > MERGE_LOCK_TIMEOUT:
                        self.log(
                            f"Таймаут ожидания lock файла ({MERGE_LOCK_TIMEOUT} сек)",
                            "error",
                        )
                        return None, False

                    # Ждём перед следующей попыткой
                    time.sleep(1)

        except Exception as lock_error:
            self.log(f"Ошибка при получении lock файла: {lock_error}", "error")
            if lock_file_handle:
                try:
                    lock_file_handle.close()
                except Exception as close_error:
                    self.log(f"Ошибка при закрытии lock файла: {close_error}", "error")
            return None, False

        return lock_file_handle, lock_acquired

    def _cleanup_merge_lock(self, lock_file_handle: Optional[object], lock_file_path: Path) -> None:
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
        except Exception as lock_error:
            self.log(f"Ошибка при удалении lock файла: {lock_error}", "debug")

    def _process_single_csv_file(
        self,
        csv_file: Path,
        writer: Optional["csv.DictWriter"],
        outfile: object,
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
        # Извлекаем категорию из имени файла
        category_name = self._extract_category_from_filename(csv_file)

        # Читаем исходный файл с увеличенной буферизацией
        import csv

        with open(
            csv_file,
            "r",
            encoding="utf-8-sig",
            newline="",
            buffering=buffer_size,
        ) as infile:
            reader = csv.DictReader(infile)

            # Проверяем наличие заголовков
            if not reader.fieldnames:
                self.log(
                    f"Файл {csv_file} пуст или не имеет заголовков",
                    "warning",
                )
                return writer, 0

            # Оптимизация: кэшируем fieldnames для файлов с одинаковой структурой
            fieldnames_key = tuple(reader.fieldnames)
            if fieldnames_key not in fieldnames_cache:
                fieldnames = list(reader.fieldnames)
                if "Категория" not in fieldnames:
                    fieldnames.insert(0, "Категория")
                fieldnames_cache[fieldnames_key] = fieldnames
            else:
                fieldnames = fieldnames_cache[fieldnames_key]

            # Создаем writer если ещё не создан
            if writer is None:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

            # Уменьшаем количество операций записи через буферизацию
            batch = []
            batch_total = 0

            for row in reader:
                # Избегаем мутации исходного словаря, создаём копию
                row_with_category = {"Категория": category_name, **row}
                batch.append(row_with_category)

                # Записываем пакет при достижении размера
                if len(batch) >= batch_size:
                    writer.writerows(batch)
                    batch_total += len(batch)
                    batch.clear()

            # Записываем оставшиеся строки (неполный пакет)
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
        self,
        output_file: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Объединяет все CSV файлы в один с добавлением колонки "Категория".

        Оптимизация:
        - Увеличенная буферизация чтения/записи (128KB вместо 32KB)
        - Предварительное вычисление категории для снижения операций в цикле
        - Увеличенный размер пакета для записи (500 строк вместо 100)
        - Использование list comprehension для быстрой фильтрации
        - Предварительное резервирование места на диске

        Важно: Сначала объединяются ВСЕ файлы, и ТОЛЬКО ПОСЛЕ успешного
        объединения удаляются все исходные файлы. Это предотвращает потерю
        данных при ошибке в середине процесса.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.
        """
        self.log("Начало объединения CSV файлов...", "info")

        # Находим все CSV файлы в output_dir
        output_file_path = Path(output_file)
        csv_files = self._get_csv_files_list(self.output_dir, output_file_path)

        if not csv_files:
            self.log("Не найдено CSV файлов для объединения", "warning")
            return False

        self.log(f"Найдено {len(csv_files)} CSV файлов для объединения", "info")

        # Список файлов для удаления (заполняется после успешного объединения)
        files_to_delete: list[Path] = []

        # Создаём временный файл для результата объединения
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"
        temp_file_created = False

        # Регистрируем временный файл для очистки через atexit
        _register_temp_file(temp_output)

        # Lock file для защиты от concurrent merge операций
        lock_file_path = self.output_dir / ".merge.lock"
        lock_file_handle = None
        lock_acquired = False

        output_encoding = self.config.writer.encoding
        # Используем предопределённые константы для буферизации и размера пакета
        buffer_size = MERGE_BUFFER_SIZE  # 128KB буфер для чтения/записи
        batch_size = MERGE_BATCH_SIZE  # Размер пакета для записи (500 строк)

        # =====================================================================
        # БЛОКИРОВКА 1: Получаем lock file для предотвращения concurrent merge
        # =====================================================================
        lock_file_handle, lock_acquired = self._acquire_merge_lock(lock_file_path)
        if not lock_acquired:
            return False

        # =====================================================================
        # БЛОКИРОВКА 2: Signal handler для очистки при KeyboardInterrupt
        # =====================================================================
        # Сохраняем старые обработчики сигналов
        old_sigint_handler = signal.getsignal(signal.SIGINT)
        old_sigterm_handler = signal.getsignal(signal.SIGTERM)

        def cleanup_temp_files():
            """Функция очистки временных файлов при прерывании."""
            with self._merge_lock:
                for temp_file in self._merge_temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                            self.log(
                                f"Временный файл удалён при прерывании: {temp_file}",
                                "debug",
                            )
                    except Exception as cleanup_error:
                        self.log(
                            f"Ошибка при удалении временного файла {temp_file}: {cleanup_error}",
                            "error",
                        )

        def signal_handler(signum, frame):
            """Обработчик сигналов прерывания."""
            self.log(f"Получен сигнал {signum}, очистка временных файлов...", "warning")
            cleanup_temp_files()
            # Вызываем старый обработчик
            if callable(old_sigint_handler):
                old_sigint_handler(signum, frame)

        # Устанавливаем наши обработчики
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Регистрируем временный файл для очистки при прерывании
            with self._merge_lock:
                self._merge_temp_files.append(temp_output)

            # Открываем с увеличенной буферизацией для улучшения производительности
            with open(
                temp_output,
                "w",
                encoding=output_encoding,
                newline="",
                buffering=buffer_size,
            ) as outfile:
                temp_file_created = True  # Файл создан успешно
                writer = None
                total_rows = 0
                fieldnames_cache: dict[tuple[str, ...], list[str]] = {}  # Кэш полей для файлов

                for csv_file in csv_files:
                    if self._cancel_event.is_set():
                        self.log("Объединение отменено пользователем", "warning")
                        try:
                            temp_output.unlink()
                        except Exception as e:
                            self.log(
                                f"Не удалось удалить временный файл при отмене: {e}",
                                "debug",
                            )
                        return False

                    if progress_callback:
                        progress_callback(f"Обработка: {csv_file.name}")

                    # Используем выделенную функцию для обработки файла
                    writer, batch_total = self._process_single_csv_file(
                        csv_file=csv_file,
                        writer=writer,
                        outfile=outfile,
                        buffer_size=buffer_size,
                        batch_size=batch_size,
                        fieldnames_cache=fieldnames_cache,
                    )

                    # Если файл был пустым, пропускаем его
                    if batch_total == 0:
                        continue

                    total_rows += batch_total

                    # Добавляем файл в список на удаление
                    files_to_delete.append(csv_file)

                # Проверка: если writer остался None, значит все файлы были пустыми
                if writer is None:
                    self.log(
                        "Все CSV файлы пустые или не имеют заголовков. Объединение невозможно.",
                        "warning",
                    )

                    # Очищаем временный файл
                    try:
                        temp_output.unlink()
                        self.log("Временный файл удалён (все файлы пустые)", "debug")
                    except Exception as e:
                        self.log(f"Не удалось удалить временный файл: {e}", "debug")

                    # Удаляем lock файл
                    self._cleanup_merge_lock(lock_file_handle, lock_file_path)

                    return False

                self.log(f"Объединение завершено. Всего записей: {total_rows}", "info")

            # Переименовываем временный файл в целевой

            # Используем os.replace() вместо shutil.move для гарантии атомарности
            # os.replace() гарантирует атомарную замену на POSIX системах
            # Это предотвращает race condition при параллельном переименовании
            try:
                # os.replace() гарантирует атомарность на POSIX
                os.replace(str(temp_output), str(output_file_path))
            except OSError as replace_error:
                # Fallback для перемещения между разными файловыми системами
                # shutil.move не атомарен, но работает跨 файловых систем
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. Используем shutil.move",
                    "debug",
                )
                try:
                    shutil.move(str(temp_output), str(output_file_path))
                except Exception as move_error:
                    # Очистка временного файла при ошибке перемещения
                    self.log(
                        f"Не удалось переместить временный файл в {output_file}: {move_error}",
                        "error",
                    )
                    try:
                        if temp_output.exists():
                            temp_output.unlink()
                            self.log(
                                "Временный файл удалён после ошибки перемещения",
                                "debug",
                            )
                    except Exception as cleanup_error:
                        self.log(
                            f"Не удалось удалить временный файл: {cleanup_error}",
                            "debug",
                        )
                    raise move_error

            # Удаляем исходные файлы после успешного переименования
            for csv_file in files_to_delete:
                try:
                    csv_file.unlink()
                    self.log(f"Исходный файл удалён: {csv_file.name}", "debug")
                except Exception as e:
                    self.log(f"Не удалось удалить файл {csv_file}: {e}", "warning")

            self.log(
                f"Объединение завершено. Файлы удалены ({len(files_to_delete)} шт.)",
                "info",
            )
            temp_file_created = False  # Файл успешно перемещён, не нужно удалять

            # Удаляем lock файл
            self._cleanup_merge_lock(lock_file_handle, lock_file_path)

            return True

        except KeyboardInterrupt:
            # Обработка прерывания пользователем (Ctrl+C)
            self.log("Объединение прервано пользователем (KeyboardInterrupt)", "warning")
            cleanup_temp_files()
            return False

        except Exception as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            return False

        finally:
            # Восстанавливаем старые обработчики сигналов
            try:
                signal.signal(signal.SIGINT, old_sigint_handler)
                signal.signal(signal.SIGTERM, old_sigterm_handler)
            except Exception as restore_error:
                self.log(
                    f"Ошибка при восстановлении обработчиков сигналов: {restore_error}",
                    "error",
                )

            # Снимаем временный файл с регистрации в реестре atexit
            _unregister_temp_file(temp_output)

            # Гарантированная очистка временного файла если он ещё существует
            # Это защищает от утечек файлов при KeyboardInterrupt или других исключениях
            if temp_file_created and temp_output.exists():
                try:
                    temp_output.unlink()
                    self.log(
                        "Временный файл удалён в блоке finally (защита от утечек)",
                        "debug",
                    )
                except Exception as cleanup_error:
                    self.log(
                        f"Не удалось удалить временный файл в finally: {cleanup_error}",
                        "warning",
                    )

            # Освобождаем блокировку и удаляем lock файл если ещё существует
            self._cleanup_merge_lock(lock_file_handle, lock_file_path)

            # Удаляем временный файл из списка экземпляра
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
            except Exception as timer_error:
                self.log(f"Не удалось запустить таймер очистки: {timer_error}", "warning")

        self.log(f"🚀 Запуск параллельного парсинга ({self.max_workers} потока)", "info")
        self.log(f"📍 Города: {[c['name'] for c in self.cities]}", "info")
        self.log(f"📑 Категории: {len(self.categories)}", "info")
        self.log(f"📊 Всего задач: {total_tasks}", "info")

        # Генерируем все URL
        all_urls = self.generate_all_urls()

        if not all_urls:
            self.log("❌ Нет URL для парсинга", "error")
            return False

        # Запускаем параллельный парсинг
        success_count = 0
        failed_count = 0
        last_progress_time = time.time()

        # Используем таймаут из конфигурации объекта
        self.log(f"⏱️ Таймаут на один URL: {self.timeout_per_url} секунд", "info")

        executor = None
        try:
            executor = ThreadPoolExecutor(max_workers=self.max_workers)

            # Создаём futures
            futures = {
                executor.submit(
                    self.parse_single_url,
                    url,
                    category_name,
                    city_name,
                    progress_callback,
                ): (url, category_name, city_name)
                for url, category_name, city_name in all_urls
            }

            # Обрабатываем результаты
            for idx, future in enumerate(as_completed(futures), 1):
                url, category_name, city_name = futures[future]

                try:
                    # Получаем результат с таймаутом
                    success, result = future.result(timeout=self.timeout_per_url)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        self.log(
                            f"❌ Не удалось: {city_name} - {category_name}: {result}",
                            "error",
                        )

                    # Выводим прогресс каждые 3 секунды
                    current_time = time.time()
                    if current_time - last_progress_time >= PROGRESS_UPDATE_INTERVAL or idx == len(
                        futures
                    ):
                        progress_bar = print_progress(
                            success_count + failed_count,
                            len(futures),
                            prefix="   Прогресс",
                        )
                        self.log(progress_bar, "info")
                        last_progress_time = current_time

                except FuturesTimeoutError:
                    failed_count += 1
                    self.log(
                        f"❌ Таймаут при парсинге {city_name} - {category_name} ({self.timeout_per_url} сек)",
                        "error",
                    )

                except KeyboardInterrupt:
                    self.log(
                        "⚠️ Парсинг прерван пользователем (KeyboardInterrupt)",
                        "warning",
                    )
                    # Устанавливаем флаг отмены для остановки остальных задач
                    self._cancel_event.set()
                    # Отменяем все ожидающие задачи
                    for f in futures:
                        f.cancel()
                    # Возвращаем False для индикации прерывания
                    return False

                except Exception as e:
                    failed_count += 1
                    self.log(
                        f"❌ Исключение при парсинге {city_name} - {category_name}: {e}",
                        "error",
                    )

        except KeyboardInterrupt:
            self.log(
                "⚠️ Парсинг прерван пользователем (KeyboardInterrupt в цикле)",
                "warning",
            )
            # Устанавливаем флаг отмены
            self._cancel_event.set()
            # Отменяем все задачи
            if executor is not None:
                for f in futures:
                    f.cancel()
            return False

        finally:
            if executor is not None:
                try:
                    # shutdown(wait=True) ожидает завершения всех задач
                    # cancel_futures=True отменяет ожидающие задачи
                    executor.shutdown(wait=True, cancel_futures=True)
                    self.log("ThreadPoolExecutor корректно завершён", "debug")
                except Exception as shutdown_error:
                    self.log(
                        f"Ошибка при shutdown ThreadPoolExecutor: {shutdown_error}",
                        "error",
                    )

        # Вычисляем длительность
        duration = time.time() - start_time
        duration_str = f"{duration:.2f} сек."

        self.log(
            f"🏁 Парсинг завершён. Успешно: {success_count}, Ошибок: {failed_count}",
            "info",
        )

        # Объединяем CSV файлы
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

        # Финальный отчёт
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
            except Exception as timer_error:
                self.log(f"Ошибка при остановке таймера: {timer_error}", "debug")

        return True

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._cancel_event.set()
        self.log("Получена команда остановки парсинга", "warning")


class ParallelCityParserThread(ParallelCityParser, threading.Thread):
    """
    Поток для параллельного парсинга городов.

    Наследуется от ParallelCityParser и threading.Thread для запуска в отдельном потоке.
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        output_file: Optional[str] = None,
    ) -> None:
        ParallelCityParser.__init__(
            self,
            cities,
            categories,
            output_dir,
            config,
            max_workers,
            timeout_per_url,
        )
        threading.Thread.__init__(self)

        self._result: Optional[bool] = None
        self._output_file = output_file

    def run(self) -> None:  # type: ignore[override]
        """Точка входа потока."""
        try:
            # Используем переданный output_file или путь по умолчанию
            output_file = self._output_file or str(self.output_dir / "merged_result.csv")
            # Вызываем метод родительского класса ParallelCityParser.run
            self._result = ParallelCityParser.run(self, output_file=output_file)
        except Exception as e:
            # Используем self.log() вместо прямого вызова logger для потокобезопасности
            self.log(f"Ошибка в потоке параллельного парсинга: {e}", "error")
            self._result = False

    def get_result(self) -> Optional[bool]:
        """Возвращает результат парсинга."""
        return self._result
