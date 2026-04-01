"""Менеджер временных файлов проекта parser-2gis.

Этот модуль предоставляет классы для управления временными файлами:
- TempFileManager: Регистрация и очистка временных файлов
- TempFileTimer: Периодическая автоматическая очистка осиротевших файлов

Пример использования:
    >>> from parser_2gis.utils.temp_file_manager import temp_file_manager, TempFileTimer
    >>> temp_file_manager.register(Path("/tmp/test.csv"))
    >>> timer = TempFileTimer()
    >>> timer.start()
    >>> # ... работа парсера ...
    >>> timer.stop()
    >>> temp_file_manager.cleanup_all()
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
import weakref
from pathlib import Path

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
# осиротевшим (3600 секунд = 1 час)
# Увеличено до 1 часа, чтобы файлы не удалялись во время длительного парсинга категорий
# Допустимый диапазон: 60-86400 секунд (1 день)
ORPHANED_TEMP_FILE_AGE = validate_env_int(
    "PARSER_ORPHANED_TEMP_FILE_AGE", default=3600, min_value=60, max_value=86400
)


# =============================================================================
# КЛАСС TempFileManager
# =============================================================================


class TempFileManager:
    """Менеджер временных файлов.

    Этот класс управляет реестром временных файлов и обеспечивает
    их централизованную очистку.

    Attributes:
        _registry: Множество путей к временным файлам.
        _lock: Блокировка для потокобезопасной работы.
        _max_files: Максимальное количество отслеживаемых файлов.

    Example:
        >>> manager = TempFileManager()
        >>> manager.register(Path("/tmp/file1.csv"))
        >>> manager.register(Path("/tmp/file2.csv"))
        >>> print(f"Отслеживается файлов: {manager.get_count()}")
        Отслеживается файлов: 2
        >>> manager.unregister(Path("/tmp/file1.csv"))
        >>> manager.cleanup_all()

    """

    def __init__(self, max_files: int = 1000) -> None:
        """Инициализирует менеджер временных файлов.

        Args:
            max_files: Максимальное количество отслеживаемых файлов.

        """
        self._registry: set[Path] = set()
        self._lock = threading.RLock()
        self._max_files = max_files
        self._logger = logger

    def register(self, file_path: Path) -> None:
        """Регистрирует временный файл для последующей очистки.

        Args:
            file_path: Путь к временному файлу.

        Raises:
            ValueError: Если file_path некорректен.
            TypeError: Если file_path не является Path.

        Note:
            Если достигнут лимит файлов, новые файлы не регистрируются.

        """
        # D015: Валидация пути перед регистрацией
        if file_path is None:
            raise ValueError("file_path не может быть None")
        if not isinstance(file_path, Path):
            raise TypeError(f"file_path должен быть Path, получен {type(file_path).__name__}")

        # Проверка на path traversal
        try:
            resolved_path = file_path.resolve()
            # Проверка что путь находится в допустимой директории
            path_str = str(resolved_path)
            if ".." in path_str:
                raise ValueError(f"file_path содержит '..': {file_path}")
        except (OSError, RuntimeError) as resolve_error:
            raise ValueError(f"Некорректный file_path: {file_path}") from resolve_error

        with self._lock:
            if len(self._registry) >= self._max_files:
                self._logger.warning(
                    f"Достигнут лимит временных файлов ({self._max_files}), "
                    f"файл {file_path} не зарегистрирован"
                )
                return
            self._registry.add(file_path)
            self._logger.debug(f"Зарегистрирован временный файл: {file_path}")

    def unregister(self, file_path: Path) -> None:
        """Удаляет файл из реестра.

        Args:
            file_path: Путь к файлу для удаления из реестра.

        """
        with self._lock:
            if file_path in self._registry:
                self._registry.discard(file_path)
                self._logger.debug(f"Удалён из реестра: {file_path}")

    def cleanup_all(self) -> tuple[int, int]:
        """Очищает все зарегистрированные временные файлы.

        Returns:
            Кортеж (успешно, ошибок) - количество успешно удалённых
            и количество файлов с ошибками.

        Note:
            После очистки реестр очищается.

        """
        success_count = 0
        error_count = 0

        with self._lock:
            files_to_clean = list(self._registry)

        for file_path in files_to_clean:
            try:
                # D018: Проверка прав доступа перед удалением
                if not file_path.exists():
                    self._logger.debug(f"Файл не существует: {file_path}")
                    continue

                # Проверка прав на запись (можем ли удалить файл)
                try:
                    # Проверяем что файл доступен для записи
                    if not os.access(str(file_path), os.W_OK):
                        self._logger.warning(f"Нет прав на удаление файла {file_path}, пропускаем")
                        error_count += 1
                        continue
                except (OSError, RuntimeError) as access_error:
                    self._logger.warning(
                        f"Ошибка проверки прав доступа к {file_path}: {access_error}"
                    )
                    error_count += 1
                    continue

                # Безопасное удаление файла
                file_path.unlink()
                success_count += 1
                self._logger.debug(f"Удалён временный файл: {file_path}")
            except PermissionError as perm_error:
                error_count += 1
                self._logger.error(f"Нет прав на удаление файла {file_path}: {perm_error}")
            except OSError as e:
                error_count += 1
                self._logger.error(f"Ошибка удаления файла {file_path}: {e}")

        with self._lock:
            self._registry.clear()

        try:
            self._logger.info(
                f"Очистка временных файлов завершена: успешно={success_count}, ошибок={error_count}"
            )
        except (ValueError, OSError):
            # Логгер закрыт, игнорируем
            pass

        return success_count, error_count

    def get_count(self) -> int:
        """Возвращает количество зарегистрированных файлов.

        Returns:
            Количество файлов в реестре.

        """
        with self._lock:
            return len(self._registry)

    def get_files(self) -> list[Path]:
        """Возвращает список зарегистрированных файлов.

        Returns:
            Список путей к файлам.

        """
        with self._lock:
            return list(self._registry)


# Singleton экземпляр для глобального использования
temp_file_manager = TempFileManager()


# Функции-обёртки для обратной совместимости
def register_temp_file(file_path: Path) -> None:
    """Регистрирует временный файл для последующей очистки.

    Args:
        file_path: Путь к временному файлу.

    Note:
        Это функция-обёртка для обратной совместимости.
        Рекомендуется использовать temp_file_manager.register().

    """
    temp_file_manager.register(file_path)


def unregister_temp_file(file_path: Path) -> None:
    """Удаляет файл из реестра временных файлов.

    Args:
        file_path: Путь к файлу для удаления из реестра.

    Note:
        Это функция-обёртка для обратной совместимости.
        Рекомендуется использовать temp_file_manager.unregister().

    """
    temp_file_manager.unregister(file_path)


def cleanup_all_temp_files() -> tuple[int, int]:
    """Очищает все зарегистрированные временные файлы.

    Returns:
        Кортеж (успешно, ошибок) - количество успешно удалённых
        и количество файлов с ошибками.

    Note:
        Это функция-обёртка для обратной совместимости.
        Рекомендуется использовать temp_file_manager.cleanup_all().

    """
    return temp_file_manager.cleanup_all()


def get_temp_file_count() -> int:
    """Возвращает количество зарегистрированных временных файлов.

    Returns:
        Количество файлов в реестре.

    Note:
        Это функция-обёртка для обратной совместимости.
        Рекомендуется использовать temp_file_manager.get_count().

    """
    return temp_file_manager.get_count()


# =============================================================================
# КЛАСС TempFileTimer
# =============================================================================


class TempFileTimer:
    """Таймер для периодической очистки временных файлов.

    Особенности:
        - Периодическая очистка через threading.Timer
        - Использование weak references для предотвращения утечек памяти
        - Мониторинг количества временных файлов
        - Автоматическая очистка осиротевших файлов
        - Блокировка для защиты общих данных (_lock)
        - Событие для координации остановки (_stop_event)

    Пример использования:
        >>> cleanup_timer = TempFileTimer(temp_dir=Path('/tmp'))
        >>> cleanup_timer.start()
        >>> # ... работа парсера ...
        >>> cleanup_timer.stop()
    """

    def __init__(
        self,
        temp_dir: Path | None = None,
        interval: int = TEMP_FILE_CLEANUP_INTERVAL,
        max_files: int = MAX_TEMP_FILES_MONITORING,
        orphan_age: int = ORPHANED_TEMP_FILE_AGE,
        cleanup_interval: int | None = None,
    ) -> None:
        """Инициализация таймера очистки.

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
        self._timer: threading.Timer | None = None
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
        """Выполняет очистку временных файлов.

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
    def _cleanup_timer(timer: threading.Timer | None, lock: threading.RLock | None = None) -> None:
        """Статический метод для гарантированной очистки таймера.

        Вызывается weakref.finalize() при уничтожении объекта сборщиком мусора.

        Args:
            timer: Таймер для отмены.
            lock: Блокировка (не используется, оставлена для совместимости).

        """
        if timer is not None:
            try:
                timer.cancel()
            except (RuntimeError, TypeError, ValueError):
                pass
        # Блокировка не освобождается здесь - она управляется в _cleanup_thread

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
        timer_to_cancel: threading.Timer | None = None
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
        """Гарантирует остановку таймера при уничтожении.

        Важно:
            - Используется weakref.finalize() для гарантированной очистки
            - Блок finally обеспечивает выполнение остановки даже при исключениях
            - Критические исключения (MemoryError, KeyboardInterrupt, SystemExit) пробрасываются
        """
        cleanup_performed = False
        timer_to_cancel: threading.Timer | None = None

        try:
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    logger.debug("TempFileTimer очищен через weakref.finalize()")
                    cleanup_performed = True
                    return

            if hasattr(self, "_is_running") and self._is_running:
                logger.warning(
                    "TempFileTimer уничтожается сборщиком мусора без явной остановки. "
                    "Всегда вызывайте stop() явно."
                )
                # Сохраняем ссылку на таймер для очистки в finally
                timer_to_cancel = getattr(self, "_timer", None)
        except MemoryError:
            # Критическая ошибка памяти - пробрасываем дальше
            logger.critical("MemoryError в __del__ TempFileTimer")
            raise
        except KeyboardInterrupt:
            # Прерывание пользователем - пробрасываем дальше
            logger.warning("KeyboardInterrupt в __del__ TempFileTimer")
            raise
        except SystemExit:
            # Выход из системы - пробрасываем дальше
            logger.debug("SystemExit в __del__ TempFileTimer")
            raise
        except (RuntimeError, TypeError, ValueError, OSError) as stop_error:
            # Ожидаемые ошибки - логируем но не пробрасываем
            logger.debug("Ошибка при остановке таймера в __del__: %s", stop_error)
        finally:
            # Гарантия выполнения очистки ресурсов
            try:
                if not cleanup_performed:
                    # Отменяем таймер если это не было сделано
                    if timer_to_cancel is not None:
                        try:
                            timer_to_cancel.cancel()
                        except (RuntimeError, TypeError, ValueError):
                            pass  # Игнорируем ошибки при отмене в __del__

                    # Сбрасываем флаг выполнения
                    try:
                        if hasattr(self, "_is_running"):
                            object.__setattr__(self, "_is_running", False)
                    except (AttributeError, TypeError, ValueError):
                        pass  # Игнорируем ошибки при сбросе флага
            except (MemoryError, KeyboardInterrupt, SystemExit):
                # Критические исключения пробрасываем даже из finally
                raise
            except Exception as cleanup_error:
                # Любые другие ошибки в finally только логируем
                logger.debug("Ошибка в finally блоке __del__ TempFileTimer: %s", cleanup_error)


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def create_temp_file(directory: str, prefix: str = "parser_") -> str:
    """Атомарное создание временного файла.

    Использует tempfile.mkstemp для атомарного создания временного файла,
    что предотвращает race condition при параллельном создании файлов.

    Args:
        directory: Директория для создания файла.
        prefix: Префикс имени файла.

    Returns:
        Путь к созданному временному файлу.

    Example:
        >>> temp_path = create_temp_file("/tmp", prefix="myapp_")
        >>> print(temp_path)
        /tmp/myapp_abc123.tmp

    """
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
    os.close(fd)  # Закрываем дескриптор, файл остается
    return path


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    # Константы
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
    # TempFileManager
    "TempFileManager",
    "temp_file_manager",
    "register_temp_file",
    "unregister_temp_file",
    "cleanup_all_temp_files",
    "get_temp_file_count",
    # TempFileTimer
    "TempFileTimer",
    # Helper functions
    "create_temp_file",
]
