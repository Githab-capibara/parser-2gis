"""Константы буферизации для parser-2gis.

Этот модуль содержит константы связанные с буферизацией данных:
- Размеры буферов для чтения/записи
- Параметры batch операций
- Пороги для mmap

Пример использования:
    >>> from parser_2gis.constants.buffer import DEFAULT_BUFFER_SIZE, MERGE_BUFFER_SIZE
    >>> print(f"Размер буфера: {DEFAULT_BUFFER_SIZE}")
"""

from __future__ import annotations

# =============================================================================
# РАЗМЕРЫ БУФЕРОВ
# =============================================================================

# Размер буфера по умолчанию (512 KB)
DEFAULT_BUFFER_SIZE: int = 512 * 1024  # 524288

# Размер буфера для merge операций (128 KB)
MERGE_BUFFER_SIZE: int = 128 * 1024  # 131072

# Размер буфера для CSV операций (1 MB)
CSV_BATCH_SIZE: int = 1000  # строк за раз

# Количество колонок на сущность в CSV
CSV_COLUMNS_PER_ENTITY: int = 5

# Размер batch для merge операций
MERGE_BATCH_SIZE: int = 500

# Порог для больших файлов (100 MB)
LARGE_FILE_THRESHOLD_MB: int = 100

# Множитель буфера для больших файлов
LARGE_FILE_BUFFER_MULTIPLIER: int = 4

# Максимальный размер буфера (1 MB)
MAX_BUFFER_SIZE: int = 1024 * 1024  # 1048576

# Порог для mmap (10 MB)
MMAP_THRESHOLD_BYTES: int = 10 * 1024 * 1024


__all__ = [
    "CSV_BATCH_SIZE",
    "CSV_COLUMNS_PER_ENTITY",
    "DEFAULT_BUFFER_SIZE",
    "LARGE_FILE_BUFFER_MULTIPLIER",
    "LARGE_FILE_THRESHOLD_MB",
    "MAX_BUFFER_SIZE",
    "MERGE_BATCH_SIZE",
    "MERGE_BUFFER_SIZE",
    "MMAP_THRESHOLD_BYTES",
]
