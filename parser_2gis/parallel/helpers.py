"""Модуль для вспомогательных классов параллельного парсинга.

Содержит классы:
- FileMerger: Объединение CSV файлов
- ProgressTracker: Отслеживание прогресса
- StatsCollector: Сбор статистики
- Выделены из ParallelCityParser для снижения сложности
- Устранена глобальная переменная _merge_temp_files через контекстный менеджер
"""

from __future__ import annotations

import csv
import fcntl
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any
from collections.abc import Callable

from parser_2gis.constants import MAX_LOCK_FILE_AGE, MERGE_BUFFER_SIZE, MERGE_LOCK_TIMEOUT
from parser_2gis.logger import logger
from parser_2gis.utils.signal_handler import SignalHandler


class FileMerger:
    """Класс для объединения CSV файлов с гарантированной очисткой ресурсов.
    - Использует контекстный менеджер для гарантии очистки временных файлов
    - Устранена глобальная переменная _merge_temp_files
    - Thread-safe реализация с использованием Lock

    Пример использования:
        >>> merger = FileMerger(output_dir=Path("output"))
        >>> with merger:
        ...     success = merger.merge_csv_files(
        ...         output_file="result.csv",
        ...         csv_files=[Path("file1.csv"), Path("file2.csv")]
        ...     )
    """

    def __init__(
        self, output_dir: Path, config: Any = None, cancel_event: threading.Event | None = None
    ) -> None:
        """Инициализация FileMerger.

        Args:
            output_dir: Директория с CSV файлами для объединения.
            config: Конфигурация (для encoding и других параметров).
            cancel_event: Событие для отмены операции.

        """
        self.output_dir = output_dir
        self.config = config
        self._cancel_event = cancel_event or threading.Event()
        self._temp_files: list[Path] = []
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов
        self._lock_file_handle: Any | None = None
        self._lock_acquired = False

    def __enter__(self) -> FileMerger:
        """Вход в контекстный менеджер."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Выход из контекстного менеджера с очисткой."""
        self._cleanup_temp_files()
        self._release_lock()

    def _cleanup_temp_files(self) -> None:
        """Очищает временные файлы."""
        with self._lock:
            for temp_file in self._temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                        logger.debug("Временный файл удалён: %s", temp_file)
                except OSError as e:
                    logger.warning("Не удалось удалить временный файл %s: %s", temp_file, e)
            self._temp_files.clear()

    def _release_lock(self) -> None:
        """Освобождает блокировку merge операции."""
        if self._lock_file_handle:
            try:
                fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_UN)
                self._lock_file_handle.close()
            except OSError as close_error:
                logger.error("Ошибка при закрытии lock файла: %s", close_error)
            self._lock_file_handle = None
            self._lock_acquired = False

    def _acquire_lock(self, lock_file_path: Path) -> bool:
        """Получает блокировку для merge операции.

        Args:
            lock_file_path: Путь к lock файлу.

        Returns:
            True если блокировка получена успешно.

        """
        try:
            # Проверяем возраст существующего lock файла
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        logger.debug("Удаление осиротевшего lock файла (возраст: %d сек)", lock_age)
                        lock_file_path.unlink()
                    else:
                        logger.warning(
                            "Lock файл существует (возраст: %d сек), ожидаем...", lock_age
                        )
                except OSError as cleanup_error:
                    logger.debug("Ошибка при удалении stale lock файла: %s", cleanup_error)

            # Пытаемся получить блокировку с таймаутом
            start_time = time.time()
            while not self._lock_acquired:
                lock_file_handle = None
                try:
                    # pylint: disable=consider-using-with
                    lock_file_handle = open(lock_file_path, "w", encoding="utf-8")
                    fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_file_handle.write(f"{os.getpid()}\n")
                    lock_file_handle.flush()
                    self._lock_file_handle = lock_file_handle
                    self._lock_acquired = True
                    logger.debug("Lock file получен успешно")
                    return True
                except OSError:
                    if lock_file_handle:
                        try:
                            lock_file_handle.close()
                        except OSError as close_error:
                            logger.error("Ошибка при закрытии lock файла: %s", close_error)
                    self._lock_file_handle = None

                    if time.time() - start_time > MERGE_LOCK_TIMEOUT:
                        logger.error("Таймаут ожидания lock файла (%d сек)", MERGE_LOCK_TIMEOUT)
                        return False

                    time.sleep(1)

        except (OSError, RuntimeError) as lock_error:
            logger.error("Ошибка при получении lock файла: %s", lock_error)
            if self._lock_file_handle:
                try:
                    self._lock_file_handle.close()
                except OSError as close_error:
                    logger.error("Ошибка при закрытии lock файла: %s", close_error)
            return False

        return True

    def merge_csv_files(
        self,
        output_file: str,
        csv_files: list[Path] | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Объединяет CSV файлы в один с добавлением колонки "Категория".

        Args:
            output_file: Путь к итоговому файлу.
            csv_files: Список CSV файлов для объединения (если None, будут найдены автоматически).
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.

        """
        output_file_path = Path(output_file)

        # Находим все CSV файлы если не предоставлены
        if csv_files is None:
            csv_files = list(self.output_dir.glob("*.csv"))
            # Исключаем объединенный файл если он существует
            if output_file_path.exists():
                csv_files = [f for f in csv_files if f != output_file_path]

        if not csv_files:
            logger.warning("Не найдено CSV файлов для объединения")
            return False

        logger.info("Найдено %d CSV файлов для объединения", len(csv_files))

        def _get_filename(file_path: Path) -> str:
            """Возвращает имя файла для сортировки."""
            return file_path.name

        csv_files.sort(key=_get_filename)

        # Создаём временный файл
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"
        files_to_delete: list[Path] = []

        # Lock file
        lock_file_path = self.output_dir / ".merge.lock"

        if not self._acquire_lock(lock_file_path):
            return False

        def _cleanup_wrapper() -> None:
            """Функция обратного вызова для очистки временных файлов."""
            self._cleanup_temp_files()

        # Используем SignalHandler для обработки сигналов
        sig_handler = SignalHandler(cleanup_callback=_cleanup_wrapper)

        try:
            sig_handler.setup()

            # Регистрируем временный файл
            with self._lock:
                self._temp_files.append(temp_output)

            buffer_size = MERGE_BUFFER_SIZE
            output_encoding = getattr(self.config, "writer", None)
            if output_encoding:
                output_encoding = getattr(output_encoding, "encoding", "utf-8")
            else:
                output_encoding = "utf-8"

            with open(
                temp_output, "w", encoding=output_encoding, newline="", buffering=buffer_size
            ) as outfile:
                writer = None
                total_rows = 0

                for csv_file in csv_files:
                    if self._cancel_event.is_set():
                        logger.warning("Объединение отменено пользователем")
                        return False

                    if progress_callback:
                        progress_callback(f"Обработка: {csv_file.name}")

                    # Извлекаем категорию из имени файла
                    stem = csv_file.stem
                    last_underscore_idx = stem.rfind("_")
                    category_name = (
                        stem[last_underscore_idx + 1 :].replace("_", " ")
                        if last_underscore_idx > 0
                        else "Unknown"
                    )

                    with open(
                        csv_file, encoding=output_encoding, newline="", buffering=buffer_size
                    ) as infile:
                        reader = csv.DictReader(infile)
                        if not reader.fieldnames:
                            continue

                        # Добавляем колонку Category если нужно
                        fieldnames = list(reader.fieldnames)
                        if "Category" not in fieldnames:
                            fieldnames.insert(0, "Category")

                        if writer is None:
                            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                            writer.writeheader()

                        for row in reader:
                            row["Category"] = category_name
                            if writer:
                                writer.writerow(row)
                            total_rows += 1

                logger.info("Объединено %d строк в файл %s", total_rows, temp_output.name)

            # Переименовываем временный файл в итоговый
            if output_file_path.exists():
                output_file_path.unlink()
            temp_output.rename(output_file_path)
            logger.info("CSV файлы успешно объединены в %s", output_file)

            # Добавляем файлы для удаления
            files_to_delete.extend(csv_files)

            # Удаляем исходные файлы
            for file_to_delete in files_to_delete:
                try:
                    file_to_delete.unlink()
                    logger.debug("Исходный файл удалён: %s", file_to_delete)
                except OSError as e:
                    logger.warning("Не удалось удалить файл %s: %s", file_to_delete, e)

            return True

        except (OSError, RuntimeError, csv.Error) as merge_error:
            logger.error("Ошибка при объединении CSV файлов: %s", merge_error)
            return False
        finally:
            # Восстанавливаем обработчики сигналов
            sig_handler.cleanup()
            # Освобождаем lock
            self._release_lock()


class ProgressTracker:
    """Трекер прогресса для параллельного парсинга.

    Отслеживает:
    - Количество обработанных городов
    - Количество обработанных категорий
    - Общее количество задач
    - Прогресс в процентах

    Пример использования:
        >>> tracker = ProgressTracker(total_cities=10, total_categories=5)
        >>> tracker.update(city_name="Москва", category_name="Рестораны")
        >>> print(tracker.get_progress_percent())
        10.0
    """

    def __init__(self, total_cities: int, total_categories: int) -> None:
        """Инициализация трекера прогресса.

        Args:
            total_cities: Общее количество городов.
            total_categories: Общее количество категорий.

        """
        self.total_cities = total_cities
        self.total_categories = total_categories
        self.total_tasks = total_cities * total_categories
        self.completed_tasks = 0
        self.current_city = ""
        self.current_category = ""
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

    def update(self, city_name: str, category_name: str) -> None:
        """Обновляет прогресс после завершения задачи.

        Args:
            city_name: Название текущего города.
            category_name: Название текущей категории.

        """
        with self._lock:
            self.completed_tasks += 1
            self.current_city = city_name
            self.current_category = category_name

    def get_progress_percent(self) -> float:
        """Получает процент выполнения.

        Returns:
            Процент выполнения (0.0 - 100.0).

        """
        with self._lock:
            if self.total_tasks is None or self.total_tasks <= 0:
                return 0.0
            return (self.completed_tasks / self.total_tasks) * 100.0

    def get_status(self) -> dict[str, Any]:
        """Получает текущий статус прогресса.

        Returns:
            Словарь со статусом прогресса.

        """
        with self._lock:
            return {
                "completed": self.completed_tasks,
                "total": self.total_tasks,
                "percent": self.get_progress_percent(),
                "current_city": self.current_city,
                "current_category": self.current_category,
            }


class StatsCollector:
    """Сборщик статистики для параллельного парсинга.

    Собирает:
    - Количество успешных операций
    - Количество ошибок
    - Время выполнения
    - Детали ошибок

    Пример использования:
        >>> stats = StatsCollector()
        >>> stats.record_success()
        >>> stats.record_error("Ошибка подключения", city="Москва")
        >>> print(stats.get_summary())
    """

    def __init__(self) -> None:
        """Инициализация сборщика статистики."""
        self.success_count = 0
        self.error_count = 0
        self.errors: list[dict[str, Any]] = []
        self.start_time: float | None = None
        self.end_time: float | None = None
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

    def start(self) -> None:
        """Начинает сбор статистики."""
        with self._lock:
            self.start_time = time.time()

    def stop(self) -> None:
        """Завершает сбор статистики."""
        with self._lock:
            self.end_time = time.time()

    # Максимальное значение счётчика для предотвращения overflow
    _MAX_COUNTER_VALUE: int = 10**9

    def record_success(self) -> None:
        """Записывает успешную операцию."""
        with self._lock:
            if self.success_count < self._MAX_COUNTER_VALUE:
                self.success_count += 1

    def record_error(self, error_message: str, city: str = "", category: str = "") -> None:
        """Записывает ошибку.

        Args:
            error_message: Сообщение об ошибке.
            city: Название города (опционально).
            category: Название категории (опционально).

        """
        with self._lock:
            if self.error_count < self._MAX_COUNTER_VALUE:
                self.error_count += 1
            self.errors.append(
                {
                    "message": error_message,
                    "city": city,
                    "category": category,
                    "timestamp": time.time(),
                }
            )

    def get_elapsed_time(self) -> float:
        """Получает прошедшее время.

        Returns:
            Время в секундах.

        """
        with self._lock:
            if self.start_time is None:
                return 0.0
            end = self.end_time if self.end_time else time.time()
            return end - self.start_time

    def get_summary(self) -> dict[str, Any]:
        """Получает сводку статистики.

        Returns:
            Словарь со сводкой статистики.

        """
        with self._lock:
            return {
                "success_count": self.success_count,
                "error_count": self.error_count,
                "total": self.success_count + self.error_count,
                "elapsed_time": self.get_elapsed_time(),
                "errors": list(self.errors),  # Копия для безопасности
            }
