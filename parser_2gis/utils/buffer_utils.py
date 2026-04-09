"""Утилиты для расчёта оптимальных буферов.

ISSUE 054: Вынесено из csv_deduplicator.py и csv_post_processor.py (csv_buffer_manager.py)
для устранения дублирования логики расчёта оптимального буфера и mmap.

Пример использования:
    >>> from parser_2gis.utils.buffer_utils import calculate_optimal_buffer
    >>> buffer_size = calculate_optimal_buffer(file_path="large_file.csv")
"""

from __future__ import annotations

import os

from parser_2gis.logger import logger as app_logger

# Константы буферизации
DEFAULT_BUFFER_SIZE = 256 * 1024  # 256 KB
LARGE_FILE_THRESHOLD_MB = 100
LARGE_FILE_BUFFER_MULTIPLIER = 4
MAX_BUFFER_SIZE = 1024 * 1024  # 1 MB
MMAP_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MB


def calculate_optimal_buffer(
    file_path: str | None = None,
    file_size_bytes: int | None = None,
    use_mmap_threshold: int = MMAP_THRESHOLD_BYTES,
) -> tuple[int, bool]:
    """Рассчитывает оптимальный размер буфера и определяет необходимость mmap.

    Общая функция для устранения дублирования между:
    - writer/writers/csv_deduplicator.py: расчёт буфера для дедупликации
    - writer/writers/csv_post_processor.py: расчёт буфера для постобработки
    - writer/writers/csv_buffer_manager.py: _calculate_optimal_buffer_size, _should_use_mmap

    Args:
        file_path: Путь к файлу для определения размера.
        file_size_bytes: Размер файла в байтах (если известен).
        use_mmap_threshold: Порог для использования mmap.

    Returns:
        Кортеж (buffer_size, should_use_mmap).

    """
    # Проверяем переменную окружения для переопределения
    env_buffer_size = os.getenv("PARSER_CSV_BUFFER_SIZE")
    if env_buffer_size is not None:
        try:
            custom_buffer = int(env_buffer_size)
            if custom_buffer <= 0:
                app_logger.warning(
                    "Некорректное значение PARSER_CSV_BUFFER_SIZE=%d (<=0), используется дефолтное",
                    custom_buffer,
                )
            elif custom_buffer > MAX_BUFFER_SIZE * 10:
                app_logger.warning(
                    "Некорректное значение PARSER_CSV_BUFFER_SIZE=%d (слишком большой), "
                    "используется максимальное %d",
                    custom_buffer,
                    MAX_BUFFER_SIZE,
                )
                return MAX_BUFFER_SIZE, False
            else:
                app_logger.debug(
                    "Используется пользовательский размер буфера: %d байт", custom_buffer
                )
                return custom_buffer, False
        except ValueError:
            app_logger.warning("Некорректное значение PARSER_CSV_BUFFER_SIZE: %s", env_buffer_size)

    # Определяем размер файла
    if file_size_bytes is None and file_path is not None:
        try:
            file_size_bytes = os.path.getsize(file_path)
        except OSError:
            file_size_bytes = 0

    if file_size_bytes is None:
        file_size_bytes = 0

    # Определяем метод чтения
    should_use_mmap = file_size_bytes > use_mmap_threshold

    # Рассчитываем оптимальный буфер
    threshold_bytes = LARGE_FILE_THRESHOLD_MB * 1024 * 1024  # 100 MB

    if file_size_bytes > threshold_bytes:
        optimal_size = min(DEFAULT_BUFFER_SIZE * LARGE_FILE_BUFFER_MULTIPLIER, MAX_BUFFER_SIZE)
        app_logger.debug(
            "Файл большой (%.2f MB), используется увеличенный буфер: %d байт",
            file_size_bytes / (1024 * 1024),
            optimal_size,
        )
    else:
        optimal_size = DEFAULT_BUFFER_SIZE
        app_logger.debug(
            "Файл стандартного размера (%.2f MB), используется стандартный буфер: %d байт",
            file_size_bytes / (1024 * 1024) if file_size_bytes > 0 else 0,
            DEFAULT_BUFFER_SIZE,
        )

    return optimal_size, should_use_mmap


def should_use_mmap(file_size_bytes: int, threshold: int = MMAP_THRESHOLD_BYTES) -> bool:
    """Определяет, следует ли использовать mmap для чтения файла.

    Args:
        file_size_bytes: Размер файла в байтах.
        threshold: Порог для использования mmap.

    Returns:
        True если размер файла превышает порог.

    """
    return file_size_bytes > threshold
