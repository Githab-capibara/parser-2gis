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
from pathlib import Path

from parser_2gis.constants import (
    MAX_TEMP_FILES_MONITORING,
    ORPHANED_TEMP_FILE_AGE,
    TEMP_FILE_CLEANUP_INTERVAL,
)
from parser_2gis.logger import logger

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
        # ISSUE-098: Заменён RLock на Lock так как реентерабельность не требуется
        self._lock = threading.Lock()
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

    def create_unique_temp_file(
        self, directory: str | Path, prefix: str = "parser_", suffix: str = ".tmp"
    ) -> Path:
        """Создаёт уникальный временный файл и регистрирует его.

        D015: Использует криптографически безопасную генерацию имён для предотвращения
        атак через предсказание имени временного файла.

        Args:
            directory: Директория для создания файла.
            prefix: Префикс имени файла.
            suffix: Суффикс имени файла.

        Returns:
            Path к созданному временному файлу.

        Raises:
            ValueError: Если directory некорректен.
            OSError: Если не удалось создать файл.

        Example:
            >>> temp_path = temp_file_manager.create_unique_temp_file("/tmp", prefix="myapp_")
            >>> print(temp_path)
            /tmp/myapp_abc123.tmp

        """
        # D015: Валидация директории
        if directory is None:
            raise ValueError("directory не может быть None")

        if isinstance(directory, Path):
            directory = str(directory)

        if not directory or not isinstance(directory, str):
            raise ValueError("directory должен быть непустой строкой")

        # D015: Проверка на path traversal в directory
        if ".." in directory:
            raise ValueError(f"directory не должен содержать '..': {directory}")

        # D015: Санитизация префикса - удаляем опасные символы
        if prefix:
            # Разрешаем только буквы, цифры, подчёркивания и дефисы
            safe_prefix = "".join(c for c in prefix if c.isalnum() or c in "_-")
            if not safe_prefix:
                safe_prefix = "tmp_"
        else:
            safe_prefix = "tmp_"

        # D015: tempfile.mkstemp использует os.urandom() для криптографически
        # безопасной генерации случайных имён
        import os
        import tempfile

        fd, path = tempfile.mkstemp(prefix=safe_prefix, suffix=suffix, dir=directory)
        try:
            # D015: Проверка прав доступа к созданному файлу
            os.fchmod(fd, 0o600)  # Только владелец может читать/писать
        except (OSError, AttributeError):
            pass  # Игнорируем если система не поддерживает fchmod
        finally:
            os.close(fd)  # Закрываем дескриптор, файл остается

        # Регистрируем файл для последующей очистки
        self.register(Path(path))
        return Path(path)


# Singleton экземпляр для глобального использования
temp_file_manager = TempFileManager()


# =============================================================================
# КЛАСС TempFileTimer
# =============================================================================


class TempFileTimer:
    """Таймер для периодической очистки временных файлов.

    Упрощённая реализация на основе threading.Timer.
    ISSUE-019: Удалены weakref/finalizer/event для упрощения.

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
        self._cleanup_count = 0

        logger.debug(
            "Инициализирован таймер очистки: интервал=%d сек, макс. файлов=%d, возраст=%d сек",
            interval,
            max_files,
            orphan_age,
        )

    def _cleanup_callback(self) -> None:
        """Callback для периодической очистки.

        Упрощённая версия: просто вызывает очистку и планирует следующую.
        """
        if not self._is_running:
            return

        try:
            self._cleanup_temp_files()
        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except Exception as cleanup_error:
            logger.error(
                "Ошибка при периодической очистке временных файлов: %s",
                cleanup_error,
                exc_info=True,
            )
        finally:
            if self._is_running:
                self._schedule_next_cleanup()

    def _schedule_next_cleanup(self) -> None:
        """Планирует следующую очистку."""
        try:
            self._timer = threading.Timer(self._interval, self._cleanup_callback)
            self._timer.daemon = True
            self._timer.start()
        except Exception as schedule_error:
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
                except Exception as file_error:
                    logger.debug(
                        "Непредвиденная ошибка при обработке файла %s: %s", temp_file, file_error
                    )

            if deleted_count > 0:
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
        if self._is_running:
            logger.warning("Таймер очистки уже запущен")
            return

        self._is_running = True
        self._schedule_next_cleanup()
        logger.info("Запущен таймер периодической очистки временных файлов")

    def stop(self) -> None:
        """Останавливает таймер периодической очистки."""
        self._is_running = False

        if self._timer is not None:
            try:
                self._timer.cancel()
            except Exception as cancel_error:
                logger.debug("Ошибка при отмене таймера: %s", cancel_error)

            try:
                self._timer.join(timeout=self._interval * 2)
            except Exception as join_error:
                logger.debug("Ошибка при ожидании таймера: %s", join_error)

            self._timer = None

        logger.info(
            "Таймер периодической очистки остановлен (всего удалено файлов: %d)",
            self._cleanup_count,
        )


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def create_temp_file(directory: str, prefix: str = "parser_") -> str:
    """Атомарное создание временного файла.

    D015: Использует криптографически безопасную генерацию имён для предотвращения
    атак через предсказание имени временного файла.

    Args:
        directory: Директория для создания файла.
        prefix: Префикс имени файла.

    Returns:
        Путь к созданному временному файлу.

    Raises:
        ValueError: Если directory некорректен.
        OSError: Если не удалось создать файл.

    Example:
        >>> temp_path = create_temp_file("/tmp", prefix="myapp_")
        >>> print(temp_path)
        /tmp/myapp_abc123.tmp

    """
    # D015: Валидация директории
    if not directory or not isinstance(directory, str):
        raise ValueError("directory должен быть непустой строкой")

    # D015: Проверка на path traversal в directory
    if ".." in directory:
        raise ValueError(f"directory не должен содержать '..': {directory}")

    # D015: Санитизация префикса - удаляем опасные символы
    if prefix:
        # Разрешаем только буквы, цифры, подчёркивания и дефисы
        safe_prefix = "".join(c for c in prefix if c.isalnum() or c in "_-")
        if not safe_prefix:
            safe_prefix = "tmp_"
    else:
        safe_prefix = "tmp_"

    # D015: tempfile.mkstemp использует os.urandom() для криптографически
    # безопасной генерации случайных имён
    fd, path = tempfile.mkstemp(prefix=safe_prefix, suffix=".tmp", dir=directory)
    try:
        # D015: Проверка прав доступа к созданному файлу
        os.fchmod(fd, 0o600)  # Только владелец может читать/писать
    except (OSError, AttributeError):
        pass  # Игнорируем если система не поддерживает fchmod
    finally:
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
    # TempFileTimer
    "TempFileTimer",
    # Helper functions
    "create_temp_file",
]
