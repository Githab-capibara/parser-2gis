"""
Модуль слияния файлов для параллельного парсинга.

Предоставляет класс ParallelFileMerger для объединения CSV файлов:
- Потокобезопасное слияние с использованием lock файлов
- Добавление колонки "Категория" из имени файла
- Оптимизированная буферизация и пакетная запись
- Обработка прерываний и очистка временных файлов
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
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from parser_2gis.constants import (
    MAX_LOCK_FILE_AGE,
    MERGE_BATCH_SIZE,
    MERGE_BUFFER_SIZE,
    MERGE_LOCK_TIMEOUT,
)
from parser_2gis.logger import logger
from parser_2gis.utils.temp_file_manager import register_temp_file, unregister_temp_file


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
        self, output_dir: Path, config, cancel_event: threading.Event, lock: threading.RLock
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
        self._merge_temp_files: List[Path] = []
        self._merge_lock = threading.RLock()

    def log(self, message: str, level: str = "info") -> None:
        """Логгирование сообщения.

        Args:
            message: Текст сообщения.
            level: Уровень логирования.
        """
        log_func = getattr(logger, level)
        log_func(message)

    def get_csv_files_list(self, output_file_path: Path) -> List[Path]:
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

    def acquire_merge_lock(self, lock_file_path: Path) -> Tuple[Optional[typing.TextIO], bool]:
        """Получает блокировку merge операции.

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

    def cleanup_merge_lock(
        self, lock_file_handle: Optional[typing.TextIO], lock_file_path: Path
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

    def process_single_csv_file(
        self,
        csv_file: Path,
        writer: Optional["csv.DictWriter"],
        outfile: "typing.TextIO",
        buffer_size: int,
        batch_size: int,
        fieldnames_cache: Dict[Tuple[str, ...], List[str]],
    ) -> Tuple[Optional["csv.DictWriter"], int]:
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
        category_name = self.extract_category_from_filename(csv_file)

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

    def merge_csv_files(
        self, output_file: str, progress_callback: Optional[Callable[[str], None]] = None
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
        lock_file_handle, lock_acquired = self.acquire_merge_lock(lock_file_path)
        if not lock_acquired:
            return False

        # БЛОКИРОВКА 2: Signal handler для очистки при KeyboardInterrupt
        old_sigint_handler = signal.getsignal(signal.SIGINT)
        old_sigterm_handler = signal.getsignal(signal.SIGTERM)
        sigint_registered = False
        sigterm_registered = False

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
                    raise move_error

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
                        f"Ошибка при восстановлении SIGINT обработчика: {restore_error}", "error"
                    )

            if sigterm_registered:
                try:
                    signal.signal(signal.SIGTERM, old_sigterm_handler)
                except (OSError, RuntimeError, TypeError, ValueError) as restore_error:
                    self.log(
                        f"Ошибка при восстановлении SIGTERM обработчика: {restore_error}", "error"
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
