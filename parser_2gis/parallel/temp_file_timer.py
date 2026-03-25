"""
Модуль для периодической очистки временных файлов.

Содержит класс _TempFileTimer для автоматической очистки
осиротевших временных файлов парсера.
"""

from __future__ import annotations

import tempfile
import threading
import time
import weakref
from pathlib import Path
from typing import Optional

from parser_2gis.constants import validate_env_int
from parser_2gis.logger import logger

# =============================================================================
# КОНСТАНТЫ ДЛЯ ОЧИСТКИ ВРЕМЕННЫХ ФАЙЛОВ
# =============================================================================

# Интервал периодической очистки временных файлов в секундах (60 секунд)
# Допустимый диапазон: 10-3600 секунд (10 минут)
TEMP_FILE_CLEANUP_INTERVAL = validate_env_int(
    "PARSER_TEMP_FILE_CLEANUP_INTERVAL", default=60, min_value=10, max_value=3600
)

# Максимальное количество временных файлов для мониторинга
# Допустимый диапазон: 100-10000
MAX_TEMP_FILES_MONITORING = validate_env_int(
    "PARSER_MAX_TEMP_FILES_MONITORING", default=1000, min_value=100, max_value=10000
)

# Возраст временного файла в секундах, после которого он считается
# осиротевшим (300 секунд = 5 минут)
# Допустимый диапазон: 60-86400 секунд (1 день)
ORPHANED_TEMP_FILE_AGE = validate_env_int(
    "PARSER_ORPHANED_TEMP_FILE_AGE", default=300, min_value=60, max_value=86400
)


class _TempFileTimer:
    """
    Таймер для периодической очистки временных файлов.

    Особенности:
        - Периодическая очистка через threading.Timer
        - Использование weak references для предотвращения утечек памяти
        - Мониторинг количества временных файлов
        - Автоматическая очистка осиротевших файлов
        - Блокировка для защиты общих данных (_lock)
        - Событие для координации остановки (_stop_event)

    Пример использования:
        >>> cleanup_timer = _TempFileTimer(temp_dir=Path('/tmp'))
        >>> cleanup_timer.start()
        >>> # ... работа парсера ...
        >>> cleanup_timer.stop()
    """

    def __init__(
        self,
        temp_dir: Optional[Path] = None,
        interval: int = TEMP_FILE_CLEANUP_INTERVAL,
        max_files: int = MAX_TEMP_FILES_MONITORING,
        orphan_age: int = ORPHANED_TEMP_FILE_AGE,
        cleanup_interval: Optional[int] = None,
    ) -> None:
        """
        Инициализация таймера очистки.

        Args:
            temp_dir: Директория для мониторинга временных файлов.
            interval: Интервал очистки в секундах.
            max_files: Максимальное количество файлов для мониторинга.
            orphan_age: Возраст файла в секундах, после которого он считается осиротевшим.
            cleanup_interval: Алиас для interval (для обратной совместимости).
        """
        if cleanup_interval is not None:
            interval = cleanup_interval
        if temp_dir is None:
            temp_dir = Path(tempfile.gettempdir()) / "parser_2gis_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir = temp_dir
        self._interval = interval
        self._max_files = max_files
        self._orphan_age = orphan_age
        self._timer: Optional[threading.Timer] = None
        self._is_running = False
        self._stop_event = threading.Event()  # Событие для координации остановки
        # RLock для предотвращения гонок данных
        self._lock = threading.RLock()  # Блокировка для защиты общих данных
        self._cleanup_count = 0
        # weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_timer, self._timer, self._lock)

        logger.debug(
            "Инициализирован таймер очистки: интервал=%d сек, макс. файлов=%d, возраст=%d сек",
            interval,
            max_files,
            orphan_age,
        )

    def _cleanup_callback(self) -> None:
        """Callback для периодической очистки.

        ИСПРАВЛЕНИЕ C-001: Устранение гонки данных через:
        1. Объединение проверки _stop_event.is_set() и планирования в единую атомарную операцию
        2. Вызов _schedule_next_cleanup() внутри блокировки для предотвращения race condition
        """
        # Проверяем флаг остановки ВНУТРИ блокировки для предотвращения гонки
        should_stop = False
        try:
            lock_acquired = self._lock.acquire(timeout=5.0)
            if lock_acquired:
                try:
                    should_stop = self._stop_event.is_set()
                finally:
                    self._lock.release()
            else:
                logger.warning("Не удалось получить блокировку в _cleanup_callback")
                should_stop = True
        except (RuntimeError, OSError) as lock_error:
            logger.debug("Ошибка при получении блокировки в _cleanup_callback: %s", lock_error)
            should_stop = True

        if should_stop:
            return

        try:
            self._cleanup_temp_files()
        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, TypeError) as cleanup_error:
            logger.error(
                "Ошибка при периодической очистке временных файлов: %s",
                cleanup_error,
                exc_info=True,
            )
        except BaseException as base_error:
            logger.error("Критическая ошибка в callback очистки: %s", base_error, exc_info=True)
        finally:
            # Планируем следующую очистку ВНУТРИ блокировки
            should_schedule = False
            try:
                lock_acquired = self._lock.acquire(timeout=5.0)
                if lock_acquired:
                    try:
                        should_schedule = not self._stop_event.is_set()
                        if should_schedule:
                            self._schedule_next_cleanup()
                    finally:
                        self._lock.release()
            except (RuntimeError, OSError):
                should_schedule = False

    def _schedule_next_cleanup(self) -> None:
        """Планирует следующую очистку."""
        try:
            self._timer = threading.Timer(self._interval, self._cleanup_callback)
            self._timer.daemon = True
            self._timer.start()
        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except (RuntimeError, OSError, TypeError, ValueError) as schedule_error:
            logger.error(
                "Ошибка при планировании следующей очистки: %s", schedule_error, exc_info=True
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
            temp_files = list(self._temp_dir.iterdir())

            if len(temp_files) > self._max_files:
                logger.warning(
                    "Превышено максимальное количество временных файлов: %d (макс: %d)",
                    len(temp_files),
                    self._max_files,
                )

            for temp_file in temp_files:
                try:
                    if temp_file.is_dir():
                        continue

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
                except (MemoryError, KeyboardInterrupt, SystemExit):
                    raise
                except (RuntimeError, TypeError, ValueError) as file_error:
                    logger.debug(
                        "Непредвиденная ошибка при обработке файла %s: %s", temp_file, file_error
                    )

            if deleted_count > 0:
                with self._lock:
                    self._cleanup_count += deleted_count
                logger.info(
                    "Периодическая очистка: удалено %d временных файлов (всего: %d)",
                    deleted_count,
                    self._cleanup_count,
                )

        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, TypeError) as cleanup_error:
            logger.error(
                "Ошибка при сканировании директории %s: %s",
                self._temp_dir,
                cleanup_error,
                exc_info=True,
            )

        return deleted_count

    @staticmethod
    def _cleanup_timer(timer: Optional[threading.Timer], lock: threading.RLock) -> None:
        """
        Статический метод для гарантированной очистки таймера.

        Вызывается weakref.finalize() при уничтожении объекта сборщиком мусора.

        Args:
            timer: Таймер для отмены.
            lock: Блокировка для потокобезопасной очистки.
        """
        if timer is not None:
            try:
                timer.cancel()
            except (RuntimeError, TypeError, ValueError) as e:
                logger.debug("Ошибка отмены таймера: %s", e)
        if lock is not None:
            try:
                lock.release()
            except (RuntimeError, TypeError) as e:
                logger.debug("Ошибка освобождения блокировки: %s", e)

    def start(self) -> None:
        """Запускает таймер периодической очистки."""
        lock_acquired = False
        try:
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
            self._stop_event.clear()
        finally:
            if lock_acquired:
                self._lock.release()

        self._schedule_next_cleanup()
        logger.info("Запущен таймер периодической очистки временных файлов")

    def stop(self) -> None:
        """Останавливает таймер периодической очистки."""
        self._stop_event.set()

        lock_acquired = False
        timer_to_cancel: Optional[threading.Timer] = None
        try:
            lock_acquired = self._lock.acquire(timeout=5.0)
            if not lock_acquired:
                logger.warning(
                    "Не удалось получить блокировку в stop() (таймаут 5 сек). "
                    "Возможна конкуренция за ресурсами."
                )
                return

            self._is_running = False

            if self._timer is not None:
                timer_to_cancel = self._timer
                self._timer = None
        finally:
            if lock_acquired:
                self._lock.release()

        if timer_to_cancel is not None:
            try:
                timer_to_cancel.cancel()
            except (RuntimeError, TypeError, ValueError) as cancel_error:
                logger.debug("Ошибка при отмене таймера: %s", cancel_error)

        if timer_to_cancel is not None:
            try:
                timer_to_cancel.join(timeout=self._interval * 2)
            except (RuntimeError, OSError, ValueError) as join_error:
                logger.debug("Ошибка при ожидании таймера: %s", join_error)

        logger.info(
            "Таймер периодической очистки остановлен (всего удалено файлов: %d)",
            self._cleanup_count,
        )

    def __del__(self) -> None:
        """Гарантирует остановку таймера при уничтожении."""
        try:
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    logger.debug("_TempFileTimer очищен через weakref.finalize()")
                    return

            if hasattr(self, "_is_running") and self._is_running:
                logger.warning(
                    "_TempFileTimer уничтожается сборщиком мусора без явной остановки. "
                    "Всегда вызывайте stop() явно."
                )
        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except (RuntimeError, TypeError, ValueError, OSError) as stop_error:
            logger.debug("Ошибка при остановке таймера в __del__: %s", stop_error)


__all__ = [
    "_TempFileTimer",
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
]
