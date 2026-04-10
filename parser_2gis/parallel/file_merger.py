"""Модуль стратегии слияния файлов для параллельного парсинга.

Этот модуль предоставляет класс FileMergerStrategy для:
- Объединения CSV файлов
- Управления временными файлами
- Обработки блокировок при слиянии
"""

from __future__ import annotations

import csv
import fcntl
import os
import shutil
import signal
import threading
import time
import types
import typing
import uuid
from asyncio import CancelledError
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from parser_2gis.constants import (
    MAX_LOCK_FILE_AGE,
    MERGE_BATCH_SIZE,
    MERGE_BUFFER_SIZE,
    MERGE_LOCK_TIMEOUT,
)
from parser_2gis.logger.logger import logger
from parser_2gis.parallel.filename_utils import extract_category_from_filename
from parser_2gis.utils.temp_file_manager import temp_file_manager

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


class FileMergerStrategy:
    """Стратегия слияния CSV файлов.

    Отвечает за:
    - Объединение множества CSV файлов в один
    - Добавление колонки "Категория"
    - Управление временными файлами
    - Обработку блокировок (lock files)

    Args:
        output_dir: Директория с CSV файлами.
        config: Конфигурация парсера.
        cancel_event: Событие отмены.
        lock: Блокировка для защиты общих ресурсов.

    """

    def __init__(
        self,
        output_dir: Path,
        config: Configuration,
        cancel_event: threading.Event,
        lock: threading.Lock,
    ) -> None:
        """Инициализирует стратегию слияния.

        Args:
            output_dir: Директория с CSV файлами.
            config: Конфигурация парсера.
            cancel_event: Событие отмены.
            lock: Блокировка для защиты общих ресурсов.

        """
        self.output_dir = output_dir
        self.config = config
        self._cancel_event = cancel_event
        self._lock = lock

        # Список для отслеживания временных файлов merge операции
        self._merge_temp_files: list[Path] = []
        self._merge_lock = threading.Lock()

        logger.debug("Инициализирована стратегия слияния файлов для %s", output_dir)

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def merge_csv_files(
        self, output_file: str, progress_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Объединяет все CSV файлы в один с добавлением колонки "Категория".

        Примечание: Логика дублируется в parser_2gis/parallel/parallel_parser.py.
        Рефакторинг отложен — слишком большой объём изменений для текущего цикла.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.

        """
        self.log("Начало объединения CSV файлов...", "info")

        output_file_path = Path(output_file)
        csv_files = self._get_csv_files_list(output_file_path)

        if not csv_files:
            self.log("Не найдено CSV файлов для объединения", "warning")
            return False

        self.log(f"Найдено {len(csv_files)} CSV файлов для объединения", "info")

        files_to_delete: list[Path] = []
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"

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

        def signal_handler(signum: int, frame: types.FrameType | None) -> None:
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
                    self.log(f"Не удалось переместить временный файл: {move_error}", "error")
                    try:
                        temp_output.unlink()
                    except (OSError, RuntimeError, TypeError, ValueError) as unlink_error:
                        self.log(f"Не удалось удалить временный файл: {unlink_error}", "debug")
                    raise

            self.log(f"Временный файл переименован: {temp_output.name} → {output_file}", "debug")

            # Удаляем исходные файлы
            for csv_file in files_to_delete:
                try:
                    csv_file.unlink()
                    self.log(f"Удалён исходный файл: {csv_file.name}", "debug")
                except (OSError, RuntimeError, TypeError, ValueError) as e:
                    self.log(f"Не удалось удалить файл {csv_file.name}: {e}", "debug")

            self._cleanup_merge_lock(lock_file_handle, lock_file_path)

            # Отменяем регистрацию временного файла т.к. он был переименован
            temp_file_manager.unregister(temp_output)

            return True

        except (KeyboardInterrupt, CancelledError):
            self.log("Объединение прервано пользователем", "warning")
            cleanup_temp_files()
            self._cleanup_merge_lock(lock_file_handle, lock_file_path)
            return False

        except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
            self.log(f"Ошибка при объединении CSV файлов: {e}", "error")
            cleanup_temp_files()
            self._cleanup_merge_lock(lock_file_handle, lock_file_path)
            return False

        finally:
            # Восстанавливаем обработчики сигналов
            try:
                if sigint_registered:
                    signal.signal(signal.SIGINT, old_sigint_handler)
                if sigterm_registered:
                    signal.signal(signal.SIGTERM, old_sigterm_handler)
            except (OSError, ValueError, TypeError) as signal_error:
                self.log(
                    f"Ошибка при восстановлении обработчиков сигналов (игнорируется): {signal_error}",
                    "debug",
                )

    def _get_csv_files_list(self, output_file_path: Path) -> list[Path]:
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

    def _extract_category_from_filename(self, csv_file: Path) -> str:
        """Извлекает название категории из имени CSV файла.

        Args:
            csv_file: Путь к CSV файлу.

        Returns:
            Название категории.

        """
        # #64: Использует общую утилиту из filename_utils.py
        return extract_category_from_filename(csv_file, log_func=self.log)

    def _acquire_merge_lock(self, lock_file_path: Path) -> tuple[typing.TextIO | None, bool]:
        """Получает блокировку merge операции.

        Args:
            lock_file_path: Путь к lock файлу.

        Returns:
            Кортеж (lock_file_handle, lock_acquired).

        """
        lock_file_handle = None
        lock_acquired = False

        try:
            # Проверка и очистка осиротевших lock файлов
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
                                f"Lock файл существует (возраст: {lock_age:.0f} сек, PID: {lock_pid}), ожидаем...",
                            )
                        except (ProcessLookupError, ValueError, OSError):
                            # Процесс не существует - это осиротевший lock
                            self.log(
                                f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек, PID: {lock_pid})",
                            )
                            lock_file_path.unlink()
                    else:
                        self.log(
                            "Lock файл существует (возраст: %.0f сек), ожидаем...", level="warning",
                        )
                except OSError as e:
                    self.log(f"Ошибка проверки lock файла: {e}")

            # Атомарное создание lock файла через O_CREAT | O_EXCL
            start_time = time.time()
            while not lock_acquired:
                lock_fd = None
                try:
                    # Атомарное создание файла - вернёт ошибку если файл уже существует
                    lock_fd = os.open(
                        str(lock_file_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644,
                    )
                    lock_file_handle = os.fdopen(lock_fd, "w", encoding="utf-8")
                    lock_fd = None  # Теперь файл управляется через lock_file_handle

                    # Получаем exclusive lock
                    fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_file_handle.write(f"{os.getpid()}\n")
                    lock_file_handle.flush()
                    lock_acquired = True
                    self.log("Lock file получен успешно", "debug")
                except (OSError, FileExistsError):
                    if lock_fd is not None:
                        try:
                            os.close(lock_fd)
                        except OSError as close_error:
                            self.log(
                                f"Ошибка при закрытии fd lock файла (игнорируется): {close_error}",
                                "debug",
                            )
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

        return typing.cast("tuple[typing.TextIO | None, bool]", (lock_file_handle, lock_acquired))

    def _cleanup_merge_lock(
        self, lock_file_handle: typing.TextIO | None, lock_file_path: Path,
    ) -> None:
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
        writer: csv.DictWriter[str] | None,
        outfile: typing.TextIO,
        buffer_size: int,
        batch_size: int,
        fieldnames_cache: dict[tuple[str, ...], list[str]],
    ) -> tuple[csv.DictWriter[str] | None, int]:
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
