"""
Модуль для слияния CSV файлов.

Содержит функции для объединения результатов парсинга
из нескольких CSV файлов в один итоговый файл.
"""

from __future__ import annotations

import csv
import csv as csv_module
import fcntl
import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, TextIO, Tuple

from parser_2gis.constants import (
    DEFAULT_BUFFER_SIZE,
    MAX_LOCK_FILE_AGE,
    MERGE_BATCH_SIZE,
    MERGE_BUFFER_SIZE,
    MERGE_LOCK_TIMEOUT,
    validate_env_int,
)

# =============================================================================
# КОНСТАНТЫ ДЛЯ СЛИЯНИЯ ФАЙЛОВ
# =============================================================================

# Размер буфера для чтения/записи файлов в байтах (256 KB)
MERGE_BUFFER_SIZE_LOCAL: int = DEFAULT_BUFFER_SIZE

# Размер пакета строк для пакетной записи в CSV
MERGE_BATCH_SIZE_LOCAL: int = MERGE_BATCH_SIZE


# Таймаут ожидания блокировки merge операции в секундах
MERGE_LOCK_TIMEOUT_LOCAL: int = validate_env_int(
    "PARSER_MERGE_LOCK_TIMEOUT", default=60, min_value=10, max_value=600
)


def _acquire_merge_lock(
    lock_file_path: Path,
    timeout: int = MERGE_LOCK_TIMEOUT,
    log_callback: Optional[Callable[[str, str], None]] = None,
) -> Tuple[Optional[object], bool]:
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
                log(f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)", "debug")
                lock_file_path.unlink()
            else:
                log(f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...", "warning")
        except OSError as e:
            log(f"Ошибка проверки lock файла: {e}", "debug")

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
                except (OSError, RuntimeError, ValueError) as close_error:
                    log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                lock_file_handle = None

            if time.time() - start_time > timeout:
                log(f"Таймаут ожидания lock файла ({timeout} сек)", "error")
                return None, False

            time.sleep(1)

    return lock_file_handle, lock_acquired


def _merge_csv_files(
    file_paths: List[Path],
    output_path: Path,
    encoding: str,
    buffer_size: int = MERGE_BUFFER_SIZE,
    batch_size: int = MERGE_BATCH_SIZE,
    log_callback: Optional[Callable[[str, str], None]] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[bool, int, List[Path]]:
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

    def log(msg: str, level: str = "info") -> None:
        if log_callback:
            log_callback(msg, level)

    files_to_delete: List[Path] = []
    total_rows = 0
    fieldnames_cache: Dict[Tuple[str, ...], List[str]] = {}
    writer = None
    infile: Optional[object] = None
    outfile: Optional[object] = None

    def _open_outfile_with_fallback(
        path: Path, enc: str, buf_size: int, log_func: Callable[[str, str], None]
    ) -> Tuple[Optional[TextIO], bool]:
        """Открывает выходной файл с fallback механизмом.

        Returns:
            Кортеж (file_object, success):
            - file_object: объект файла или None при ошибке
            - success: True если файл успешно открыт
        """
        try:
            file_obj = open(path, "w", encoding=enc, newline="", buffering=buf_size)  # nosec B228
            log_func(f"Выходной файл открыт с буфером {buf_size} байт", "debug")
            return file_obj, True
        except OSError as output_error:
            error_type = type(output_error).__name__
            log_func(
                f"Ошибка записи в выходной файл {path} ({error_type}): {output_error}", "error"
            )

            if buf_size > 8192:
                log_func("Fallback попытка: уменьшаем размер буфера до 8KB", "warning")
                try:
                    file_obj = open(path, "w", encoding=enc, newline="", buffering=8192)  # nosec B228
                    log_func("Fallback успешен: файл открыт с уменьшенным буфером", "info")
                    return file_obj, True
                except OSError as fallback_error:
                    log_func(f"Fallback не удался: {fallback_error}", "error")
                    return None, False
            return None, False

    outfile, open_success = _open_outfile_with_fallback(output_path, encoding, buffer_size, log)
    if not open_success or outfile is None:
        return False, 0, []

    try:
        with outfile:  # type: ignore[union-attr]
            for csv_file in file_paths:
                if cancel_event is not None and cancel_event.is_set():
                    log("Объединение отменено пользователем", "warning")
                    return False, 0, []

                if progress_callback:
                    progress_callback(f"Обработка: {csv_file.name}")

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
                        csv_file, "r", encoding="utf-8-sig", newline="", buffering=buffer_size
                    )
                except OSError as file_error:
                    error_type = type(file_error).__name__
                    log(f"Ошибка доступа к файлу {csv_file} ({error_type}): {file_error}", "error")

                    if buffer_size > 0:
                        log(f"Попытка fallback: читаем файл {csv_file} без буферизации", "warning")
                        try:
                            infile = open(
                                csv_file, "r", encoding="utf-8-sig", newline="", buffering=0
                            )
                            log(f"Fallback успешен: файл {csv_file} открыт без буферизации", "info")
                        except OSError as fallback_error:
                            log(f"Fallback не удался для {csv_file}: {fallback_error}", "error")
                            continue
                    else:
                        continue

                try:
                    reader = csv_module.DictReader(infile)

                    if reader.fieldnames is None:
                        log(
                            f"Файл {csv_file} пуст или не имеет заголовков (fieldnames=None)",
                            "warning",
                        )
                        continue

                    if len(reader.fieldnames) == 0:
                        log(f"Файл {csv_file} имеет пустой список заголовков", "warning")
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
                    log(f"Файл {csv_file.name} обработан (строк: {batch_total})", "debug")

                except OSError as csv_error:
                    error_type = type(csv_error).__name__
                    log(f"Ошибка при обработке CSV {csv_file} ({error_type}): {csv_error}", "error")
                    continue
                except csv.Error as csv_parse_error:
                    log(f"Ошибка парсинга CSV {csv_file}: {csv_parse_error}", "error")
                    continue
                finally:
                    if infile is not None:
                        try:
                            infile.close()
                            log(f"Файл {csv_file.name} закрыт", "debug")
                        except (OSError, RuntimeError, ValueError) as close_error:
                            log(
                                f"Ошибка при закрытии файла {csv_file.name}: {close_error}", "debug"
                            )

                files_to_delete.append(csv_file)

            if writer is None:
                log("Все CSV файлы пустые или не имеют заголовков", "warning")
                return False, 0, []

            log(f"Объединение завершено. Всего записей: {total_rows}", "info")
            return True, total_rows, files_to_delete

    except KeyboardInterrupt:
        log("Объединение прервано пользователем (KeyboardInterrupt)", "warning")
        return False, 0, files_to_delete

    except OSError as e:
        error_type = type(e).__name__
        error_details = str(e)
        log(f"Критическая ошибка ОС при объединении CSV ({error_type}): {error_details}", "error")
        return False, 0, files_to_delete

    except (RuntimeError, TypeError, ValueError, MemoryError) as e:
        error_type = type(e).__name__
        log(f"Непредвиденная ошибка при объединении CSV ({error_type}): {e}", "error")
        return False, 0, files_to_delete


def _cleanup_source_files(
    file_paths: List[Path], log_callback: Optional[Callable[[str, str], None]] = None
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
        except (OSError, RuntimeError, TypeError, ValueError) as e:
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
        f"Объединённый файл валиден: {output_path.name} ({output_path.stat().st_size} байт)", "info"
    )
    return True


__all__ = [
    "_acquire_merge_lock",
    "_merge_csv_files",
    "_cleanup_source_files",
    "_validate_merged_file",
    "MERGE_BUFFER_SIZE_LOCAL",
    "MERGE_BATCH_SIZE_LOCAL",
    "MERGE_LOCK_TIMEOUT_LOCAL",
]
