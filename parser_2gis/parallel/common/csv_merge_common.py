"""Общие функции для слияния CSV файлов.

ISSUE-045: Вынесено из parallel_parser.py, merger.py и file_merger.py для устранения
дублирования логики слияния CSV файлов (~60% overlap).

ISSUE-056: parallel_parser.py и file_merger.py должны использовать эти функции.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.parallel.common.csv_merge_common import merge_csv_files_common
    >>> success, rows = merge_csv_files_common(
    ...     file_paths=[Path("file1.csv"), Path("file2.csv")],
    ...     output_path=Path("merged.csv"),
    ...     encoding="utf-8",
    ... )
"""

from __future__ import annotations

import csv
import threading
import uuid
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import TextIO

from parser_2gis.constants import MERGE_BATCH_SIZE, MERGE_BUFFER_SIZE
from parser_2gis.parallel.filename_utils import extract_category_from_filename



def _log_message(
    msg: str, level: str = "debug", log_callback: Callable[[str, str], None] | None = None
) -> None:
    """Общая функция для логирования через callback.

    Args:
        msg: Сообщение для логирования.
        level: Уровень логирования (debug, info, warning, error).
        log_callback: Функция обратного вызова для логирования.

    """
    if log_callback:
        log_callback(msg, level)


def _get_cached_fieldnames(fieldnames_tuple: tuple[str, ...], *, add_category: bool) -> list[str]:
    """Вычисляет fieldnames с добавлением колонки категории.

    Args:
        fieldnames_tuple: Кортеж исходных имён полей.
        add_category: Добавить ли колонку "Категория".

    Returns:
        Список имён полей.

    """
    fieldnames = list(fieldnames_tuple)
    if add_category and "Категория" not in fieldnames:
        fieldnames.insert(0, "Категория")
    return fieldnames


def merge_csv_files_common(
    file_paths: list[Path],
    output_path: Path,
    encoding: str = "utf-8",
    buffer_size: int = MERGE_BUFFER_SIZE,
    batch_size: int = MERGE_BATCH_SIZE,
    log_callback: Callable[[str, str], None] | None = None,
    progress_callback: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, int, list[Path]]:
    """Объединяет CSV файлы в один с добавлением колонки "Категория".

    Общая функция для устранения дублирования между:
    - parallel_parser.py: merge_csv_files
    - merger.py: merge_csv_files
    - file_merger.py: merge_csv_files
    - strategies.py (FileMergerStrategy): merge_csv_files

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

    Raises:
        ValueError: Если file_paths пустой или buffer_size/batch_size некорректны.

    """
    if not file_paths:
        raise ValueError("file_paths не может быть пустым")
    if buffer_size <= 0:
        raise ValueError(f"buffer_size должен быть положительным числом, получено {buffer_size}")
    if batch_size <= 0:
        raise ValueError(f"batch_size должен быть положительным числом, получено {batch_size}")

    files_to_delete: list[Path] = []
    total_rows = 0
    fieldnames_cache: dict[tuple[str, ...], list[str]] = {}
    writer = None

    def _open_outfile_with_fallback(
        path: Path, enc: str, buf_size: int, log_func: Callable[[str, str], None] | None
    ) -> tuple[TextIO | None, bool]:
        """Открывает выходной файл с fallback механизмом."""
        try:
            file_obj = open(path, "w", encoding=enc, newline="", buffering=buf_size)
            _log_message(f"Выходной файл открыт с буфером {buf_size} байт", "debug", log_func)
            return file_obj, True
        except OSError as output_error:
            error_type = type(output_error).__name__
            _log_message(
                f"Ошибка записи в выходной файл {path} ({error_type}): {output_error}",
                "error",
                log_func,
            )

            if buf_size > 8192:
                _log_message(
                    "Fallback попытка: уменьшаем размер буфера до 8KB", "warning", log_func
                )
                try:
                    file_obj = open(path, "w", encoding=enc, newline="", buffering=8192)
                    _log_message(
                        "Fallback успешен: файл открыт с уменьшенным буфером", "info", log_func
                    )
                    return file_obj, True
                except OSError as fallback_error:
                    _log_message(f"Fallback не удался: {fallback_error}", "error", log_func)
                    return None, False
            return None, False

    outfile, open_success = _open_outfile_with_fallback(
        output_path, encoding, buffer_size, log_callback
    )
    if not open_success or outfile is None:
        return False, 0, []

    try:
        with outfile:
            for csv_file in file_paths:
                if cancel_event is not None and cancel_event.is_set():
                    _log_message("Объединение отменено пользователем", "warning", log_callback)
                    return False, 0, []

                if progress_callback:
                    progress_callback(f"Обработка: {csv_file.name}")

                category_name = extract_category_from_filename(
                    csv_file, log_func=partial(_log_message, log_callback=log_callback)
                )

                infile = None
                try:
                    infile = open(csv_file, encoding="utf-8-sig", newline="", buffering=buffer_size)
                except OSError as file_error:
                    error_type = type(file_error).__name__
                    _log_message(
                        f"Ошибка доступа к файлу {csv_file} ({error_type}): {file_error}",
                        "error",
                        log_callback,
                    )
                    if buffer_size > 0:
                        try:
                            infile = open(
                                csv_file, encoding="utf-8-sig", newline="", buffering=4096
                            )
                            _log_message(
                                f"Fallback успешен: файл {csv_file} открыт с буфером 4KB",
                                "info",
                                log_callback,
                            )
                        except OSError as fallback_error:
                            _log_message(
                                f"Fallback не удался для {csv_file}: {fallback_error}",
                                "error",
                                log_callback,
                            )
                            continue
                    else:
                        continue

                try:
                    reader = csv.DictReader(infile)

                    if reader.fieldnames is None or len(reader.fieldnames) == 0:
                        _log_message(
                            f"Файл {csv_file} пуст или не имеет заголовков", "warning", log_callback
                        )
                        continue

                    fieldnames_key = tuple(reader.fieldnames)
                    if fieldnames_key not in fieldnames_cache:
                        fieldnames = _get_cached_fieldnames(fieldnames_key, add_category=True)
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
                    _log_message(
                        f"Файл {csv_file.name} обработан (строк: {batch_total})",
                        "debug",
                        log_callback,
                    )

                except (OSError, csv.Error) as csv_error:
                    _log_message(
                        f"Ошибка при обработке CSV {csv_file}: {csv_error}", "error", log_callback
                    )
                    continue
                finally:
                    if infile is not None:
                        try:
                            infile.close()
                        except (OSError, RuntimeError, ValueError) as close_error:
                            _log_message(
                                f"Ошибка при закрытии файла {csv_file.name}: {close_error}",
                                "debug",
                                log_callback,
                            )

                files_to_delete.append(csv_file)

            if writer is None:
                _log_message(
                    "Все CSV файлы пустые или не имеют заголовков", "warning", log_callback
                )
                return False, 0, []

            _log_message(
                f"Объединение завершено. Всего записей: {total_rows}", "info", log_callback
            )
            return True, total_rows, files_to_delete

    except KeyboardInterrupt:
        _log_message(
            "Объединение прервано пользователем (KeyboardInterrupt)", "warning", log_callback
        )
        return False, 0, files_to_delete

    except OSError as e:
        _log_message(f"Критическая ошибка ОС при объединении CSV: {e}", "error", log_callback)
        return False, 0, files_to_delete

    except (RuntimeError, TypeError, ValueError, MemoryError) as e:
        _log_message(f"Непредвиденная ошибка при объединении CSV: {e}", "error", log_callback)
        return False, 0, files_to_delete


def generate_temp_merge_path(output_dir: Path) -> Path:
    """Генерирует путь для временного файла merge операции.

    Args:
        output_dir: Директория для временного файла.

    Returns:
        Путь к временному файлу.

    """
    return output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"
