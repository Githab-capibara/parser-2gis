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
from collections.abc import Generator
from contextlib import contextmanager

from parser_2gis.constants import DEFAULT_BUFFER_SIZE
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
    """Определяет, следует ли использовать mmap для чтения файла.

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


@contextmanager
def mmap_file_context(
    file_path: str, mode: str = "r", encoding: str = "utf-8"
) -> Generator[tuple[io.TextIOWrapper | object, bool, object | None], None, None]:
    """Контекстный менеджер для безопасной работы с файлами через mmap.

    Гарантирует закрытие всех ресурсов (mmap, файловый дескриптор, TextIOWrapper)
    даже при возникновении исключений.

    ISSUE-157: Упрощена fallback логика через выделение метода.

    Args:
        file_path: Путь к файлу.
        mode: Режим открытия файла ('r' для чтения, 'w' для записи).
        encoding: Кодировка файла (только для текстового режима).

    Yields:
        Кортеж (file_object, is_mmap, underlying_fp):
        - file_object: объект файла или TextIOWrapper обёрнутый mmap
        - is_mmap: True если используется mmap
        - underlying_fp: исходный файловый дескриптор (для закрытия)

    Raises:
        OSError: При ошибке доступа к файлу.
        PermissionError: При отсутствии прав доступа к файлу.

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
    underlying_fp: object | None = None
    mmapped_file: mmap.mmap | None = None  # type: ignore[mmap.mmap]
    text_file: io.TextIOWrapper | None = None
    is_mmap_mode = False
    fallback_file: object | None = None

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
            text_file = io.TextIOWrapper(mmapped_file, encoding=encoding, errors="replace")  # type: ignore[arg-type]
            is_mmap_mode = True
            yield text_file, True, underlying_fp
        else:
            logger.debug(
                "Файл стандартного размера (%.2f MB <= 10 MB), используется обычная буферизация",
                file_size / (1024 * 1024),
            )
            fallback_file = open(file_path, mode, encoding=encoding)
            yield fallback_file, False, None

    except (OSError, TypeError, RuntimeError) as error:
        # ISSUE-157: Упрощённая fallback логика через выделение метода
        logger.warning(
            "Не удалось открыть mmap для файла %s: %s. Используется обычная буферизация.",
            file_path,
            error,
        )
        # Закрываем ресурсы если они были открыты
        _cleanup_mmap_resources(underlying_fp, mmapped_file)
        # Fallback на обычную буферизацию
        fallback_file = open(file_path, mode, encoding=encoding)
        try:
            yield fallback_file, False, None
        finally:
            _close_file_safely(fallback_file)

    finally:
        # Закрываем все ресурсы если не было fallback
        if is_mmap_mode:
            _cleanup_mmap_resources(underlying_fp, mmapped_file, text_file)


def _cleanup_mmap_resources(
    underlying_fp: object | None = None,
    mmapped_file: mmap.mmap | None = None,  # type: ignore[mmap.mmap]
    text_file: io.TextIOWrapper | None = None,
) -> None:
    """Закрывает mmap ресурсы.

    ISSUE-157: Выделено для упрощения fallback логики.

    Args:
        underlying_fp: Исходный файловый дескриптор.
        mmapped_file: mmap объект.
        text_file: TextIOWrapper обёртка.

    """
    if text_file is not None and hasattr(text_file, "close"):
        try:
            text_file.close()
        except (OSError, TypeError) as close_error:
            logger.warning("Ошибка при закрытии text_file: %s", close_error)
    if mmapped_file is not None:
        try:
            mmapped_file.close()
        except (OSError, TypeError) as close_error:
            logger.warning("Ошибка при закрытии mmapped_file: %s", close_error)
    if underlying_fp is not None and hasattr(underlying_fp, "close"):
        try:
            underlying_fp.close()
        except (OSError, TypeError) as close_error:
            logger.warning("Ошибка при закрытии underlying_fp: %s", close_error)


def _close_file_safely(file_obj: object | None) -> None:
    """Безопасно закрывает файл.

    ISSUE-157: Выделено для упрощения fallback логики.

    Args:
        file_obj: Объект файла для закрытия.

    """
    if file_obj is not None and hasattr(file_obj, "close"):
        try:
            file_obj.close()
        except (OSError, TypeError) as close_error:
            logger.warning("Ошибка при закрытии файла: %s", close_error)


def _calculate_optimal_buffer_size(
    file_path: str | None = None, file_size_bytes: int | None = None
) -> int:
    """Рассчитывает оптимальный размер буфера для чтения/записи CSV файлов.

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

    Raises:
        ValueError: Если buffer_size некорректен.

    """
    # Проверяем переменную окружения для переопределения размера буфера
    env_buffer_size = os.getenv("PARSER_CSV_BUFFER_SIZE")
    if env_buffer_size is not None:
        try:
            custom_buffer = int(env_buffer_size)
            # ISSUE-117: Валидация buffer_size на разумность
            if custom_buffer <= 0:
                logger.warning(
                    "Некорректное значение PARSER_CSV_BUFFER_SIZE=%d (<=0), используется дефолтное",
                    custom_buffer,
                )
                return DEFAULT_BUFFER_SIZE
            if custom_buffer > MAX_BUFFER_SIZE * 10:
                logger.warning(
                    "Некорректное значение PARSER_CSV_BUFFER_SIZE=%d (слишком большой), "
                    "используется максимальное %d",
                    custom_buffer,
                    MAX_BUFFER_SIZE,
                )
                return MAX_BUFFER_SIZE
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
    # Для обычных файлов используем стандартный буфер
    logger.debug(
        "Файл стандартного размера (%.2f MB), используется стандартный буфер: %d байт",
        file_size_bytes / (1024 * 1024),
        DEFAULT_BUFFER_SIZE,
    )
    return DEFAULT_BUFFER_SIZE


def _fallback_copy_and_remove(src: str, dst: str) -> bool:
    """Fallback: копирует файл src в dst, затем удаляет src.

    #70: Вынесено из _safe_move_file для устранения дублирования copy+delete.

    Args:
        src: Путь к исходному файлу.
        dst: Путь к целевому файлу.

    Returns:
        True если операция успешна.

    """
    try:
        shutil.copy2(src, dst)
        if os.path.exists(dst):
            try:
                os.remove(src)
                logger.info("Файл перемещён через fallback copy+delete: %s -> %s", src, dst)
                return True
            except OSError as remove_error:
                logger.error("OSError при удалении оригинала %s после copy: %s", src, remove_error)
                return False
        else:
            logger.error("Fallback copy+delete не удался: файл %s не создан", dst)
            return False
    except OSError as fallback_error:
        logger.error("Fallback copy+delete не удался (OSError): %s", fallback_error)
        return False
    except (TypeError, RuntimeError) as fallback_error:
        logger.error(
            "Fallback copy+delete не удался: %s (%s)", fallback_error, type(fallback_error).__name__
        )
        return False


def _safe_move_file(src: str, dst: str) -> bool:
    """Безопасно перемещает файл с fallback на copy+delete.

    - Обрабатывает ошибку shutil.move() с fallback на copy+delete
    - Проверяет существование файла после move
    - Удаляет source файл если move успешен но source остался.

    Args:
        src: Путь к исходному файлу
        dst: Путь к целевому файлу

    Returns:
        True если перемещение успешно, False иначе

    """
    # ISSUE-117: Валидация путей
    if not src or not dst:
        logger.error("Пустой путь к файлу: src=%s, dst=%s", src, dst)
        return False

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
                # ISSUE-116: Обработка OSError при os.remove
                logger.warning(
                    "OSError при удалении source файла %s после move: %s", src, remove_error
                )

        return True

    except OSError as move_error:
        # ISSUE-115: Обработка OSError при shutil.move
        logger.warning(
            "shutil.move не удался (OSError: %s), используем fallback copy+delete", move_error
        )
        return _fallback_copy_and_remove(src, dst)

    except (TypeError, RuntimeError) as move_error:
        # Fallback на copy+delete для других исключений
        logger.warning(
            "shutil.move не удался (%s: %s), используем fallback copy+delete",
            type(move_error).__name__,
            move_error,
        )
        return _fallback_copy_and_remove(src, dst)
