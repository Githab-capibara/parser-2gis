"""Модуль слияния файлов для параллельного парсинга.

Предоставляет класс ParallelFileMerger для объединения CSV файлов:
- Потокобезопасное слияние с использованием lock файлов
- Добавление колонки "Категория" из имени файла
- Оптимизированная буферизация и пакетная запись
- Обработка прерываний и очистка временных файлов

Этот модуль объединяет логику из бывшего file_merger.py для устранения дублирования.
"""

from __future__ import annotations

import csv
import fcntl
import os
import shutil
import signal
import threading
import time
import typing
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from parser_2gis.constants import (
    MAX_LOCK_FILE_AGE,
    MERGE_BATCH_SIZE,
    MERGE_BUFFER_SIZE,
    MERGE_LOCK_TIMEOUT,
)
from parser_2gis.logger import logger
from parser_2gis.parallel.common.csv_merge_common import merge_csv_files_common
from parser_2gis.parallel.merge_csv_handler import MergeCSVHandler
from parser_2gis.parallel.merge_lock_manager import MergeLockManager
from parser_2gis.utils.temp_file_manager import temp_file_manager

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


# =============================================================================
# ОБЩАЯ ФУНКЦИЯ ЛОГИРОВАНИЯ (устранение дублирования)
# =============================================================================


def _log_message(
    msg: str, level: str = "debug", log_callback: Callable[[str, str], None] | None = None,
) -> None:
    """Общая функция для логирования через callback.

    Args:
        msg: Сообщение для логирования.
        level: Уровень логирования (debug, info, warning, error).
        log_callback: Функция обратного вызова для логирования.

    """
    if log_callback:
        log_callback(msg, level)


# =============================================================================
# ФУНКЦИИ СЛИЯНИЯ (перемещены из file_merger.py)
# =============================================================================


def _acquire_merge_lock(
    lock_file_path: Path,
    timeout: int = MERGE_LOCK_TIMEOUT,
    log_callback: Callable[[str, str], None] | None = None,
) -> tuple[object | None, bool]:
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
    lock_file_handle = None
    lock_acquired = False

    # Проверяем возраст существующего lock файла
    if lock_file_path.exists():
        try:
            lock_age = time.time() - lock_file_path.stat().st_mtime
            if lock_age > MAX_LOCK_FILE_AGE:
                _log_message(
                    f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)",
                    "debug",
                    log_callback,
                )
                lock_file_path.unlink()
            else:
                _log_message(
                    f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                    "warning",
                    log_callback,
                )
        except OSError as e:
            _log_message(f"Ошибка проверки lock файла: {e}", "debug", log_callback)

    # Пытаемся получить блокировку с таймаутом
    start_time = time.time()
    while not lock_acquired:
        try:
            # pylint: disable=consider-using-with
            lock_file_handle = open(lock_file_path, "w", encoding="utf-8")
            try:
                fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_file_handle.write(f"{os.getpid()}\n")
                lock_file_handle.flush()
                lock_acquired = True
                _log_message("Lock file получен успешно", "debug", log_callback)
            except OSError:
                # #188: Гарантированное закрытие дескриптора через try/finally
                try:
                    lock_file_handle.close()
                except (OSError, RuntimeError, ValueError) as close_error:
                    _log_message(
                        f"Ошибка при закрытии lock файла: {close_error}", "error", log_callback,
                    )
                lock_file_handle = None

                if time.time() - start_time > timeout:
                    _log_message(
                        f"Таймаут ожидания lock файла ({timeout} сек)", "error", log_callback,
                    )
                    return None, False

                time.sleep(1)
        except OSError:
            if lock_file_handle:
                try:
                    lock_file_handle.close()
                except (OSError, RuntimeError, ValueError) as close_error:
                    _log_message(
                        f"Ошибка при закрытии lock файла: {close_error}", "error", log_callback,
                    )
                lock_file_handle = None

            if time.time() - start_time > timeout:
                _log_message(f"Таймаут ожидания lock файла ({timeout} сек)", "error", log_callback)
                return None, False

            time.sleep(1)

    return lock_file_handle, lock_acquired


def _merge_csv_files(
    file_paths: list[Path],
    output_path: Path,
    encoding: str,
    buffer_size: int = MERGE_BUFFER_SIZE,
    batch_size: int = MERGE_BATCH_SIZE,
    log_callback: Callable[[str, str], None] | None = None,
    progress_callback: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, int, list[Path]]:
    """Объединяет CSV файлы в один с добавлением колонки "Категория".

    ISSUE-085: Делегирует общую функцию merge_csv_files_common
    из csv_merge_common.py для устранения дублирования кода.

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
        Кортеж (success, total_rows, files_to_delete).

    """
    return merge_csv_files_common(
        file_paths=file_paths,
        output_path=output_path,
        encoding=encoding,
        buffer_size=buffer_size,
        batch_size=batch_size,
        log_callback=log_callback,
        progress_callback=progress_callback,
        cancel_event=cancel_event,
    )


def _cleanup_source_files(
    file_paths: list[Path], log_callback: Callable[[str, str], None] | None = None,
) -> int:
    """Очищает исходные файлы после объединения.

    Args:
        file_paths: Список путей к файлам для удаления.
        log_callback: Функция для логирования.

    Returns:
        Количество успешно удалённых файлов.

    """
    deleted_count = 0
    for csv_file in file_paths:
        try:
            csv_file.unlink()
            _log_message(f"Исходный файл удалён: {csv_file.name}", "debug", log_callback)
            deleted_count += 1
        except (OSError, RuntimeError, TypeError, ValueError) as e:
            _log_message(f"Не удалось удалить файл {csv_file}: {e}", "warning", log_callback)
    return deleted_count


def _validate_merged_file(
    output_path: Path, log_callback: Callable[[str, str], None] | None = None,
) -> bool:
    """Валидирует объединённый файл.

    Args:
        output_path: Путь к объединённому файлу.
        log_callback: Функция для логирования.

    Returns:
        True если файл валиден, False иначе.

    """
    if not output_path.exists():
        _log_message(f"Объединённый файл не существует: {output_path}", "error", log_callback)
        return False

    if output_path.stat().st_size == 0:
        _log_message(f"Объединённый файл пуст: {output_path}", "error", log_callback)
        return False

    _log_message(
        f"Объединённый файл валиден: {output_path.name} ({output_path.stat().st_size} байт)",
        "info",
        log_callback,
    )
    return True


class ParallelFileMerger:
    """Класс для слияния CSV файлов в параллельном парсинге.

    Предоставляет функциональность для:
    - Получения списка CSV файлов для объединения
    - Извлечения названия категории из имени файла
    - Потокобезопасного слияния с использованием lock файлов
    - Обработки прерываний и очистки временных файлов

    Attributes:
        output_dir: Директория с CSV файлами для объединения.
        config: Конфигурация парсера.
        cancel_event: Событие для отмены операции.
        lock: Блокировка для потокобезопасного доступа.
        merge_temp_files: Список временных файлов merge операции.

    """

    def __init__(
        self,
        output_dir: Path,
        config: Configuration,
        cancel_event: threading.Event,
        lock: threading.RLock,
    ) -> None:
        """Инициализация слияния файлов.

        Args:
            output_dir: Директория с CSV файлами.
            config: Конфигурация парсера.
            cancel_event: Событие для отмены операции.
            lock: Блокировка для потокобезопасного доступа.

        """
        self.output_dir = output_dir
        self.config = config
        self._cancel_event = cancel_event
        self._lock = lock
        self._merge_temp_files: list[Path] = []
        self._merge_lock = threading.RLock()

        # ISSUE-025: Делегирование специализированным компонентам
        self._csv_handler = MergeCSVHandler(
            log_callback=self.log,
            buffer_size=MERGE_BUFFER_SIZE,
            batch_size=MERGE_BATCH_SIZE,
        )
        self._lock_manager = MergeLockManager(
            log_callback=self.log, timeout=MERGE_LOCK_TIMEOUT,
        )

    def log(self, message: str, level: str = "info") -> None:
        """Логгирование сообщения.

        Args:
            message: Текст сообщения.
            level: Уровень логирования.

        """
        log_func = getattr(logger, level)
        log_func(message)

    def get_csv_files_list(self, output_file_path: Path) -> list[Path]:
        """Получает список CSV файлов для объединения.

        Args:
            output_file_path: Путь к целевому файлу (исключается из списка).

        Returns:
            Отсортированный список CSV файлов.

        """
        csv_files = list(self.output_dir.glob("*.csv"))

        if output_file_path.exists():
            csv_files = [f for f in csv_files if f != output_file_path]
            self.log(f"Исключен объединенный файл из списка: {output_file_path.name}", "debug")

        csv_files.sort(key=lambda x: x.name)
        return csv_files

    def extract_category_from_filename(self, csv_file: Path) -> str:
        """Извлекает название категории из имени CSV файла.

        ISSUE-025: Делегирует MergeCSVHandler.
        """
        return self._csv_handler.extract_category_from_filename(csv_file)

    def acquire_merge_lock(self, lock_file_path: Path) -> tuple[typing.TextIO | None, bool]:
        """Получает блокировку merge операции.

        ISSUE-025: Делегирует MergeLockManager.
        """
        return self._lock_manager.acquire_lock(lock_file_path)

    def cleanup_merge_lock(
        self, lock_file_handle: typing.TextIO | None, lock_file_path: Path,
    ) -> None:
        """Очищает и удаляет lock файл.

        ISSUE-025: Делегирует MergeLockManager.
        """
        self._lock_manager.release_lock(lock_file_handle, lock_file_path)

    # TODO(ISSUE-058): Дублирование логики слияния с parallel_parser.py (~60% overlap).
    # Общая функция: parser_2gis.parallel.common.csv_merge_common.merge_csv_files_common
    # Код намеренно дублируется т.к. выполняется в контексте основного процесса (main context).
    # При следующем рефакторинге использовать merge_csv_files_common из parallel.common.
    def process_single_csv_file(
        self,
        csv_file: Path,
        writer: csv.DictWriter[str] | None,
        outfile: typing.TextIO,
        _buffer_size: int,
        _batch_size: int,
        fieldnames_cache: dict[tuple[str, ...], list[str]],
    ) -> tuple[csv.DictWriter[str] | None, int]:
        """Обрабатывает один CSV файл и добавляет данные в выходной файл.

        ISSUE-025: Делегирует MergeCSVHandler.
        """
        return self._csv_handler.process_single_csv_file(
            csv_file=csv_file, writer=writer, outfile=outfile, fieldnames_cache=fieldnames_cache,
        )

    def merge_csv_files(
        self, output_file: str, progress_callback: Callable[[str], None] | None = None,
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
        csv_files = self.get_csv_files_list(output_file_path)

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
        lock_file_handle, lock_acquired = self.acquire_merge_lock(lock_file_path)
        if not lock_acquired:
            return False

        # БЛОКИРОВКА 2: Signal handler для очистки при KeyboardInterrupt
        old_sigint_handler = signal.getsignal(signal.SIGINT)
        old_sigterm_handler = signal.getsignal(signal.SIGTERM)
        sigint_registered = False
        sigterm_registered = False

        def cleanup_temp_files() -> None:
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

        def signal_handler(signum: int, frame: object | None) -> None:
            """Обработчик сигналов прерывания."""
            self.log(f"Получен сигнал {signum}, очистка временных файлов...", "warning")
            cleanup_temp_files()

            if callable(old_sigint_handler):
                old_sigint_handler(signum, frame)

        # Регистрируем обработчики сигналов
        try:
            signal.signal(signal.SIGINT, signal_handler)
            sigint_registered = True
            signal.signal(signal.SIGTERM, signal_handler)
            sigterm_registered = True
        except (OSError, ValueError) as sig_error:
            self.log(f"Не удалось зарегистрировать обработчики сигналов: {sig_error}", "warning")

        try:
            with self._merge_lock:
                self._merge_temp_files.append(temp_output)

            with open(
                temp_output, "w", encoding=output_encoding, newline="", buffering=buffer_size,
            ) as outfile:
                temp_file_created = True
                writer = None
                total_rows = 0
                fieldnames_cache: dict[tuple[str, ...], list[str]] = {}

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

                    writer, batch_total = self.process_single_csv_file(
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

                    self.cleanup_merge_lock(lock_file_handle, lock_file_path)
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
                    raise

            for csv_file in files_to_delete:
                try:
                    csv_file.unlink()
                    self.log(f"Исходный файл удалён: {csv_file.name}", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as e:
                    self.log(f"Не удалось удалить файл {csv_file}: {e}", "warning")

            self.log(f"Объединение завершено. Файлы удалены ({len(files_to_delete)} шт.)", "info")
            temp_file_created = False

            self.cleanup_merge_lock(lock_file_handle, lock_file_path)
            return True

        except KeyboardInterrupt:
            self.log("Объединение прервано пользователем (KeyboardInterrupt)", "warning")
            cleanup_temp_files()
            return False

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            return False

        finally:
            self.cleanup_merge_lock(lock_file_handle, lock_file_path)

            # ВОССТАНОВЛЕНИЕ СИГНАЛОВ ВСЕГДА через try/finally
            if sigint_registered:
                try:
                    signal.signal(signal.SIGINT, old_sigint_handler)
                except (OSError, RuntimeError, TypeError, ValueError) as restore_error:
                    self.log(
                        f"Ошибка при восстановлении SIGINT обработчика: {restore_error}", "error",
                    )

            if sigterm_registered:
                try:
                    signal.signal(signal.SIGTERM, old_sigterm_handler)
                except (OSError, RuntimeError, TypeError, ValueError) as restore_error:
                    self.log(
                        f"Ошибка при восстановлении SIGTERM обработчика: {restore_error}", "error",
                    )

            temp_file_manager.unregister(temp_output)

            if temp_file_created and temp_output.exists():
                try:
                    temp_output.unlink()
                    self.log("Временный файл удалён в блоке finally (защита от утечек)", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
                    self.log(
                        f"Не удалось удалить временный файл в finally: {cleanup_error}", "warning",
                    )

            with self._merge_lock:
                if temp_output in self._merge_temp_files:
                    self._merge_temp_files.remove(temp_output)
