"""Модуль управления файлами для параллельного парсинга.

Предоставляет класс FileManager для:
- Атомарного создания временных файлов
- Переименования файлов
- Очистки временных файлов
- Управления lock файлами
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from pathlib import Path

from parser_2gis.constants import MAX_LOCK_FILE_AGE, MAX_UNIQUE_NAME_ATTEMPTS
from parser_2gis.logger.logger import logger


class FileManager:
    """Менеджер управления файлами.

    Отвечает за:
    - Атомарное создание временных файлов
    - Безопасное переименование файлов
    - Очистку временных файлов
    - Управление lock файлами для слияния

    Args:
        output_dir: Директория для работы с файлами.

    """

    def __init__(self, output_dir: Path) -> None:
        """Инициализирует менеджер файлов.

        Args:
            output_dir: Директория для работы с файлами.

        """
        self.output_dir = output_dir
        self._temp_files: list[Path] = []
        logger.debug("Инициализирован FileManager для %s", output_dir)

    def create_unique_temp_file(self, city_name: str, category_name: str) -> tuple[Path, str]:
        """Создаёт уникальный временный файл атомарно.

        Args:
            city_name: Название города.
            category_name: Название категории.

        Returns:
            Кортеж (путь к файлу, имя файла).

        Raises:
            OSError: Если не удалось создать файл.

        """
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")

        # Создаём уникальное временное имя файла
        temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
        temp_filepath = self.output_dir / temp_filename

        # Атомарное создание временного файла для предотвращения race condition
        temp_fd: int | None = None
        for attempt in range(MAX_UNIQUE_NAME_ATTEMPTS):
            try:
                temp_fd = os.open(
                    str(temp_filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644
                )
                os.close(temp_fd)
                temp_fd = None
                logger.log(5, "Временный файл атомарно создан: %s", temp_filename)
                self._temp_files.append(temp_filepath)
                return temp_filepath, temp_filename
            except FileExistsError:
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(5, "Коллизия имён (попытка %d): генерация нового имени", attempt + 1)
                    temp_filename = (
                        f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
                    )
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать уникальный временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise
            except OSError:
                if temp_fd is not None:
                    try:
                        os.close(temp_fd)
                    except OSError as close_error:
                        logger.log(5, "Ошибка закрытия дескриптора файла: %s", close_error)
                    temp_fd = None
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(
                        5, "Ошибка создания файла (попытка %d): повторная попытка", attempt + 1
                    )
                    temp_filename = (
                        f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
                    )
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise

        # Должны были создать файл в цикле
        raise OSError(f"Не удалось создать временный файл: {temp_filename}")

    def rename_file(self, src_path: Path, dst_path: Path) -> bool:
        """Переименовывает файл с fallback на shutil.move.

        Args:
            src_path: Исходный путь.
            dst_path: Целевой путь.

        Returns:
            True если успешно.

        Raises:
            OSError: Если не удалось переименовать.

        """
        try:
            os.replace(str(src_path), str(dst_path))
            logger.debug("Файл переименован: %s → %s", src_path.name, dst_path.name)
            return True
        except OSError as replace_error:
            logger.debug(
                "Не удалось переименовать файл (OSError): %s. Используем shutil.move", replace_error
            )
            try:
                shutil.move(str(src_path), str(dst_path))
                logger.debug(
                    "Файл перемещён через shutil.move: %s → %s", src_path.name, dst_path.name
                )
                return True
            except (OSError, RuntimeError, TypeError, ValueError) as move_error:
                logger.error("Не удалось переместить файл: %s", move_error)
                raise

    def cleanup_file(self, file_path: Path) -> bool:
        """Очищает (удаляет) файл.

        Args:
            file_path: Путь к файлу.

        Returns:
            True если файл удалён, False иначе.

        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug("Файл удалён: %s", file_path.name)
                if file_path in self._temp_files:
                    self._temp_files.remove(file_path)
                return True
        except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
            logger.warning("Не удалось удалить файл %s: %s", file_path, cleanup_error)
        return False

    def cleanup_all_temp_files(self) -> int:
        """Очищает все временные файлы.

        Returns:
            Количество удалённых файлов.

        """
        deleted_count = 0
        for temp_file in self._temp_files[:]:  # Копия списка для безопасного удаления
            if self.cleanup_file(temp_file):
                deleted_count += 1
        self._temp_files.clear()
        logger.info("Очищено %d временных файлов", deleted_count)
        return deleted_count

    def acquire_lock(
        self, lock_file_path: Path, timeout: int = MAX_LOCK_FILE_AGE
    ) -> tuple[int | None, bool]:
        """Получает блокировку файла.

        Args:
            lock_file_path: Путь к lock файлу.
            timeout: Таймаут ожидания в секундах.

        Returns:
            Кортеж (file_descriptor, lock_acquired).

        """
        import fcntl

        lock_fd: int | None = None
        lock_acquired = False

        try:
            # Проверка и очистка осиротевших lock файлов
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        try:
                            with open(lock_file_path, encoding="utf-8") as f:
                                lock_pid = int(f.read().strip())
                            os.kill(lock_pid, 0)
                            logger.warning(
                                "Lock файл существует (возраст: %.0f сек, PID: %d), ожидаем...",
                                lock_age,
                                lock_pid,
                            )
                        except (ProcessLookupError, ValueError, OSError):
                            logger.debug(
                                "Удаление осиротевшего lock файла (возраст: %.0f сек)", lock_age
                            )
                            lock_file_path.unlink()
                    else:
                        logger.warning(
                            "Lock файл существует (возраст: %.0f сек), ожидаем...", lock_age
                        )
                except OSError as e:
                    logger.debug("Ошибка проверки lock файла: %s", e)

            # Атомарное создание lock файла
            start_time = time.time()
            while not lock_acquired:
                try:
                    lock_fd = os.open(
                        str(lock_file_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644
                    )
                    # Получаем exclusive lock
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Записываем PID
                    with os.fdopen(lock_fd, "w", encoding="utf-8") as f:
                        f.write(f"{os.getpid()}\n")
                        f.flush()
                    lock_acquired = True
                    logger.debug("Lock file получен успешно")
                    return lock_fd, lock_acquired
                except (OSError, FileExistsError):
                    if lock_fd is not None:
                        try:
                            os.close(lock_fd)
                        except OSError as close_error:
                            logger.debug(
                                "Ошибка при закрытии fd lock файла (игнорируется): %s", close_error
                            )
                    lock_fd = None

                    if time.time() - start_time > timeout:
                        logger.error("Таймаут ожидания lock файла (%d сек)", timeout)
                        return None, False

                    time.sleep(1)

        except (OSError, RuntimeError, TypeError, ValueError) as lock_error:
            logger.error("Ошибка при получении lock файла: %s", lock_error)
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except OSError as close_error:
                    logger.debug(
                        "Ошибка при закрытии fd lock файла при ошибе (игнорируется): %s",
                        close_error,
                    )
            return None, False

        return lock_fd, lock_acquired

    def release_lock(self, lock_fd: int | None, lock_file_path: Path) -> None:
        """Освобождает и удаляет lock файл.

        Args:
            lock_fd: Дескриптор lock файла.
            lock_file_path: Путь к lock файлу.

        """
        import fcntl

        try:
            if lock_fd is not None:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            if lock_file_path.exists():
                lock_file_path.unlink()
                logger.debug("Lock файл удалён: %s", lock_file_path.name)
        except (OSError, RuntimeError, TypeError, ValueError) as lock_error:
            logger.debug("Ошибка при удалении lock файла: %s", lock_error)

    def get_csv_files(self, exclude_path: Path | None = None) -> list[Path]:
        """Получает список CSV файлов.

        Args:
            exclude_path: Путь к файлу для исключения из списка.

        Returns:
            Отсортированный список CSV файлов.

        """
        csv_files = list(self.output_dir.glob("*.csv"))

        if exclude_path and exclude_path.exists():
            csv_files = [f for f in csv_files if f != exclude_path]
            logger.debug("Исключен файл из списка: %s", exclude_path.name)

        csv_files.sort(key=lambda x: x.name)
        return csv_files

    @property
    def temp_files(self) -> list[Path]:
        """Возвращает список временных файлов."""
        return self._temp_files.copy()
