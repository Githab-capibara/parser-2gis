"""Менеджер буферов и mmap для CSV файлов.

Предоставляет утилиты для оптимизированной работы с файлами:
- Управление буферами чтения/записи
- mmap поддержка для больших файлов
- Безопасное перемещение файлов
"""

from __future__ import annotations

import io
import mmap
import os
import shutil
from contextlib import contextmanager
from typing import Generator, Optional, Tuple, Union

from parser_2gis.common import DEFAULT_BUFFER_SIZE
from parser_2gis.logger import logger

# =============================================================================
# КОНСТАНТЫ ДЛЯ ОПТИМИЗАЦИИ (ОБОСНОВАНИЕ ЗНАЧЕНИЙ)
# =============================================================================

# ОБОСНОВАНИЕ: 256 KB выбрано как баланс между:
# - Частые системные вызовы (маленький буфер)
# - Избыточное использование памяти (большой буфер)
# - Стандартный размер страницы памяти: 4KB
# - 256KB = 64 страницы - оптимально для последовательного чтения/записи
# Буфер для чтения файлов в байтах (256 KB)
READ_BUFFER_SIZE = DEFAULT_BUFFER_SIZE

# ОБОСНОВАНИЕ: 256 KB для записи обеспечивает:
# - Уменьшение количества системных вызовов write()
# - Эффективное использование кэша диска
# - Баланс между памятью и производительностью
# Буфер для записи файлов в байтах (256 KB)
WRITE_BUFFER_SIZE = DEFAULT_BUFFER_SIZE

# Размер пакета для хеширования строк
# ОБОСНОВАНИЕ: 1000 строк выбрано исходя из:
# - Средняя длина строки: 200-500 байт
# - 1000 * 300 байт = 300KB - разумное использование памяти
# - Пакетная обработка улучшает производительность хеширования
HASH_BATCH_SIZE = 1000

# Порог размера файла для использования увеличенного буфера (100 MB)
LARGE_FILE_THRESHOLD_MB = 100

# Множитель увеличения буфера для больших файлов
LARGE_FILE_BUFFER_MULTIPLIER = 4

# Максимальный размер буфера (1 MB)
MAX_BUFFER_SIZE = 1048576

# Порог размера файла для использования mmap (10 MB)
# Файлы больше этого размера будут читаться через mmap для оптимизации памяти
MMAP_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MB


def _should_use_mmap(file_size_bytes: int) -> bool:
    """
    Определяет, следует ли использовать mmap для чтения файла.

    Args:
        file_size_bytes: Размер файла в байтах.

    Returns:
        True если размер файла превышает порог MMAP_THRESHOLD_BYTES.

    Примечание:
        mmap эффективен для больших файлов (>10MB) так как:
        - Не загружает весь файл в память
        - Использует виртуальную память ОС
        - Уменьшает накладные расходы на ввод-вывод
    """
    return file_size_bytes > MMAP_THRESHOLD_BYTES


def _open_file_with_mmap_support(
    file_path: str, mode: str = "r", encoding: Optional[str] = None, create_if_missing: bool = False
) -> Tuple[Union[io.TextIOWrapper, object], bool]:
    """
    Открывает файл с использованием mmap для больших файлов или обычной буферизации.

    Args:
        file_path: Путь к файлу.
        mode: Режим открытия файла ('r' для чтения, 'w' для записи).
        encoding: Кодировка файла (только для текстового режима).
        create_if_missing: Создать файл если он не существует (по умолчанию False).

    Returns:
        Кортеж (file_object, is_mmap):
        - file_object: объект файла или mmap
        - is_mmap: True если используется mmap

    Raises:
        OSError: При ошибке получения размера файла или открытия mmap.
        ValueError: При некорректных параметрах.
        FileNotFoundError: Если файл не существует и create_if_missing=False.

    Примечание:
        - Для файлов >10MB используется mmap.mmap()
        - Для файлов <=10MB используется обычная буферизация
        - Детальное логирование выбора метода чтения
    """
    # Создаём файл если он не существует и create_if_missing=True
    if create_if_missing and mode == "r":
        try:
            if not os.path.exists(file_path):
                # Создаём пустой файл
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")
        except OSError as create_error:
            logger.warning("Не удалось создать файл %s: %s.", file_path, create_error)
            raise

    try:
        # Получаем размер файла
        file_size = os.path.getsize(file_path)
    except OSError as size_error:
        logger.warning(
            "Не удалось получить размер файла %s: %s. Используется обычная буферизация.",
            file_path,
            size_error,
        )
        # При ошибке получения размера используем обычную буферизацию
        file_obj = open(file_path, mode, encoding=encoding)
        return file_obj, False

    # Определяем метод чтения на основе размера файла
    use_mmap = _should_use_mmap(file_size) and mode == "r"

    if use_mmap:
        try:
            logger.info(
                "Файл большой (%.2f MB > 10 MB), используется mmap для чтения",
                file_size / (1024 * 1024),
            )
            # Открываем файл в бинарном режиме для mmap
            fp = open(file_path, "rb")
            # Создаём mmap объект
            mmapped_file = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)  # type: ignore[mmap.mmap]
            # Оборачиваем в TextIOWrapper для текстового чтения
            # mmap.mmap совместим с RawIOBase, но mypy не может это вывести
            text_file = io.TextIOWrapper(
                mmapped_file,  # type: ignore[arg-type]
                encoding=encoding or "utf-8",
                errors="replace",
            )
            return text_file, True
        except OSError as mmap_error:
            logger.warning(
                "Не удалось открыть mmap для файла %s: %s. Используется обычная буферизация.",
                file_path,
                mmap_error,
            )
            # Fallback на обычную буферизацию
            file_obj = open(file_path, mode, encoding=encoding)
            return file_obj, False
        except Exception as unexpected_error:
            logger.error(
                "Непредвиденная ошибка при открытии mmap для файла %s: %s. "
                "Используется обычная буферизация.",
                file_path,
                unexpected_error,
            )
            # Fallback на обычную буферизацию
            file_obj = open(file_path, mode, encoding=encoding)
            return file_obj, False
    else:
        logger.debug(
            "Файл стандартного размера (%.2f MB <= 10 MB), используется обычная буферизация",
            file_size / (1024 * 1024),
        )
        file_obj = open(file_path, mode, encoding=encoding)
        return file_obj, False


def _close_file_with_mmap_support(
    file_obj: Union[io.TextIOWrapper, object], is_mmap: bool, underlying_fp: Optional[object] = None
) -> None:
    """
    Корректно закрывает файл, открытый с mmap или обычной буферизацией.

    Args:
        file_obj: Объект файла или mmap.
        is_mmap: True если используется mmap.
        underlying_fp: Исходный файловый дескриптор для mmap (если есть).

    Примечание:
        - Для mmap: закрывает TextIOWrapper, mmap и файловый дескриптор
        - Для обычной буферизации: просто закрывает файл
    """
    try:
        if is_mmap:
            # Закрываем TextIOWrapper
            if hasattr(file_obj, "close"):
                file_obj.close()
            # Закрываем underlying файловый дескриптор если предоставлен
            if underlying_fp is not None and hasattr(underlying_fp, "close"):
                underlying_fp.close()
        else:
            # Обычное закрытие файла
            if hasattr(file_obj, "close"):
                file_obj.close()
    except Exception as close_error:
        logger.warning("Ошибка при закрытии файла: %s", close_error)


@contextmanager
def mmap_file_context(
    file_path: str, mode: str = "r", encoding: str = "utf-8"
) -> Generator[Tuple[Union[io.TextIOWrapper, object], bool, Optional[object]], None, None]:
    """
    Контекстный менеджер для безопасной работы с файлами через mmap.

    Гарантирует закрытие всех ресурсов (mmap, файловый дескриптор, TextIOWrapper)
    даже при возникновении исключений.

    Args:
        file_path: Путь к файлу.
        mode: Режим открытия файла ('r' для чтения, 'w' для записи).
        encoding: Кодировка файла (только для текстового режима).

    Yields:
        Кортеж (file_object, is_mmap, underlying_fp):
        - file_object: объект файла или TextIOWrapper обёрнутый mmap
        - is_mmap: True если используется mmap
        - underlying_fp: исходный файловый дескриптор (для закрытия)

    Example:
        >>> with mmap_file_context("large_file.csv") as (f, is_mmap, underlying_fp):
        ...     content = f.read()
        ... # Все ресурсы автоматически закрыты

    Примечание:
        - Для файлов >10MB используется mmap.mmap()
        - Для файлов <=10MB используется обычная буферизация
        - Все ресурсы закрываются в finally блоке
        - При ошибке mmap используется fallback на обычную буферизацию
    """
    underlying_fp: Optional[object] = None
    mmapped_file: Optional[mmap.mmap] = None  # type: ignore[mmap.mmap]
    text_file: Optional[io.TextIOWrapper] = None
    is_mmap_mode = False
    fallback_file: Optional[object] = None

    try:
        # Получаем размер файла
        file_size = os.path.getsize(file_path)
        use_mmap = file_size > (10 * 1024 * 1024) and mode == "r"  # 10MB threshold

        if use_mmap:
            logger.info(
                "Файл большой (%.2f MB > 10 MB), используется mmap для чтения",
                file_size / (1024 * 1024),
            )
            # Открываем файл в бинарном режиме
            underlying_fp = open(file_path, "rb")
            # Создаём mmap объект
            mmapped_file = mmap.mmap(underlying_fp.fileno(), 0, access=mmap.ACCESS_READ)  # type: ignore[mmap.mmap]
            # Оборачиваем в TextIOWrapper для текстового чтения
            text_file = io.TextIOWrapper(
                mmapped_file,
                encoding=encoding,
                errors="replace",  # type: ignore[arg-type]
            )
            is_mmap_mode = True
            yield text_file, True, underlying_fp
        else:
            logger.debug(
                "Файл стандартного размера (%.2f MB <= 10 MB), используется обычная буферизация",
                file_size / (1024 * 1024),
            )
            fallback_file = open(file_path, mode, encoding=encoding)
            yield fallback_file, False, None

    except OSError as mmap_error:
        logger.warning(
            "Не удалось открыть mmap для файла %s: %s. Используется обычная буферизация.",
            file_path,
            mmap_error,
        )
        # Fallback на обычную буферизацию
        if underlying_fp is not None and hasattr(underlying_fp, "close"):
            underlying_fp.close()
        if mmapped_file is not None:
            mmapped_file.close()
        fallback_file = open(file_path, mode, encoding=encoding)
        try:
            yield fallback_file, False, None
        finally:
            if hasattr(fallback_file, "close"):
                fallback_file.close()
    except Exception as unexpected_error:
        logger.error(
            "Непредвиденная ошибка при открытии mmap для файла %s: %s. "
            "Используется обычная буферизация.",
            file_path,
            unexpected_error,
        )
        # Fallback на обычную буферизацию
        if underlying_fp is not None and hasattr(underlying_fp, "close"):
            underlying_fp.close()
        if mmapped_file is not None:
            mmapped_file.close()
        fallback_file = open(file_path, mode, encoding=encoding)
        try:
            yield fallback_file, False, None
        finally:
            if hasattr(fallback_file, "close"):
                fallback_file.close()
    finally:
        # Закрываем все ресурсы если не было fallback
        if is_mmap_mode:
            if text_file is not None and hasattr(text_file, "close"):
                text_file.close()
            if mmapped_file is not None:
                mmapped_file.close()
            if underlying_fp is not None and hasattr(underlying_fp, "close"):
                underlying_fp.close()
        elif fallback_file is None and hasattr(text_file, "close"):
            # Если не было fallback и text_file ещё открыт
            text_file.close()


def _calculate_optimal_buffer_size(
    file_path: Optional[str] = None, file_size_bytes: Optional[int] = None
) -> int:
    """
    Рассчитывает оптимальный размер буфера для чтения/записи CSV файлов.

    - Для файлов >100MB используется увеличенный буфер (1MB)
    - Для файлов <=100MB используется стандартный буфер (256KB)
    - Автоматическое определение размера файла если не предоставлен
    - Настройка через конфигурацию (переменные окружения)

    Args:
        file_path: Путь к файлу для определения размера (опционально).
        file_size_bytes: Размер файла в байтах (опционально).

    Returns:
        Оптимальный размер буфера в байтах.

    Пример:
        >>> _calculate_optimal_buffer_size(file_size_bytes=150_000_000)
        1048576  # 1MB для файлов >100MB
        >>> _calculate_optimal_buffer_size(file_size_bytes=50_000_000)
        262144  # 256KB для файлов <=100MB
    """
    # Проверяем переменную окружения для переопределения размера буфера
    env_buffer_size = os.getenv("PARSER_CSV_BUFFER_SIZE")
    if env_buffer_size is not None:
        try:
            custom_buffer = int(env_buffer_size)
            if custom_buffer > 0:
                logger.debug("Используется пользовательский размер буфера: %d байт", custom_buffer)
                return custom_buffer
        except ValueError:
            logger.warning("Некорректное значение PARSER_CSV_BUFFER_SIZE: %s", env_buffer_size)

    # Определяем размер файла если не предоставлен
    if file_size_bytes is None and file_path is not None:
        try:
            file_size_bytes = os.path.getsize(file_path)
        except OSError:
            # Если не удалось получить размер, используем дефолтное значение
            file_size_bytes = 0

    # Если размер файла неизвестен, используем дефолтное значение
    if file_size_bytes is None:
        return DEFAULT_BUFFER_SIZE

    # Рассчитываем оптимальный размер буфера
    threshold_bytes = LARGE_FILE_THRESHOLD_MB * 1024 * 1024  # 100 MB

    if file_size_bytes > threshold_bytes:
        # Для больших файлов используем увеличенный буфер
        optimal_size = min(DEFAULT_BUFFER_SIZE * LARGE_FILE_BUFFER_MULTIPLIER, MAX_BUFFER_SIZE)
        logger.debug(
            "Файл большой (%.2f MB), используется увеличенный буфер: %d байт",
            file_size_bytes / (1024 * 1024),
            optimal_size,
        )
        return optimal_size
    else:
        # Для обычных файлов используем стандартный буфер
        logger.debug(
            "Файл стандартного размера (%.2f MB), используется стандартный буфер: %d байт",
            file_size_bytes / (1024 * 1024),
            DEFAULT_BUFFER_SIZE,
        )
        return DEFAULT_BUFFER_SIZE


def _safe_move_file(src: str, dst: str) -> bool:
    """
    Безопасное перемещение файла с fallback на copy+delete.
    - Обрабатывает ошибку shutil.move() с fallback на copy+delete
    - Проверяет существование файла после move
    - Удаляет source файл если move успешен но source остался

    Args:
        src: Путь к исходному файлу
        dst: Путь к целевому файлу

    Returns:
        True если перемещение успешно, False иначе
    """
    try:
        # Пытаемся атомарное перемещение
        shutil.move(src, dst)

        # Проверяем что целевой файл существует
        if not os.path.exists(dst):
            logger.error("Файл не был перемещён: %s -> %s", src, dst)
            return False

        # Если source файл всё ещё существует - удаляем его
        # Это может произойти если shutil.move использовал copy+unlink вместо rename
        if os.path.exists(src):
            try:
                os.remove(src)
                logger.debug("Source файл удалён после move: %s", src)
            except OSError as remove_error:
                logger.warning(
                    "Не удалось удалить source файл %s после move: %s", src, remove_error
                )

        return True

    except Exception as move_error:
        # Fallback на copy+delete
        logger.warning(
            "shutil.move не удался (%s: %s), используем fallback copy+delete",
            type(move_error).__name__,
            move_error,
        )
        try:
            # Копируем файл с сохранением метаданных
            shutil.copy2(src, dst)

            # Проверяем что копия успешна
            if os.path.exists(dst):
                # Удаляем оригинал
                os.remove(src)
                logger.info("Файл перемещён через fallback copy+delete: %s -> %s", src, dst)
                return True
            else:
                logger.error("Fallback copy+delete не удался: файл %s не создан", dst)
                return False

        except Exception as fallback_error:
            logger.error(
                "Fallback copy+delete не удался: %s (%s)",
                fallback_error,
                type(fallback_error).__name__,
            )
            return False
