"""
Менеджер временных файлов проекта parser-2gis.

Этот модуль предоставляет класс TempFileManager для инкапсуляции
управления временными файлами вместо использования глобальных переменных.

Пример использования:
    >>> from parser_2gis.temp_file_manager import temp_file_manager
    >>> temp_file_manager.register(Path("/tmp/test.csv"))
    >>> temp_file_manager.cleanup_all()
"""

from __future__ import annotations

import threading
from pathlib import Path

from .logger import logger


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

        Note:
            Если достигнут лимит файлов, новые файлы не регистрируются.
        """
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
                if file_path.exists():
                    file_path.unlink()
                    success_count += 1
                    self._logger.debug(f"Удалён временный файл: {file_path}")
                else:
                    self._logger.debug(f"Файл не существует: {file_path}")
            except OSError as e:
                error_count += 1
                self._logger.error(f"Ошибка удаления файла {file_path}: {e}")

        with self._lock:
            self._registry.clear()

        self._logger.info(
            f"Очистка временных файлов завершена: успешно={success_count}, ошибок={error_count}"
        )

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


__all__ = [
    "TempFileManager",
    "temp_file_manager",
    "register_temp_file",
    "unregister_temp_file",
    "cleanup_all_temp_files",
    "get_temp_file_count",
]
