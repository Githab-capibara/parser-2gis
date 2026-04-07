"""Модуль файловых писателей.

Предоставляет классы для записи данных в различные форматы:
- FileWriter - базовый абстрактный класс
- CSVWriter - запись в CSV таблицу
- XLSXWriter - запись в XLSX таблицу
- JSONWriter - запись в JSON файл
- CSVPostProcessor - постобработка CSV
- CSVDeduplicator - дедупликация CSV
- CSVBufferManager - утилиты буферизации и mmap
"""

from .csv_buffer_manager import (
    HASH_BATCH_SIZE,
    MAX_BUFFER_SIZE,
    MMAP_THRESHOLD_BYTES,
    READ_BUFFER_SIZE,
    WRITE_BUFFER_SIZE,
    _calculate_optimal_buffer_size,
    _safe_move_file,
    _should_use_mmap,
    mmap_file_context,
)
from .csv_deduplicator import CSVDeduplicator
from .csv_post_processor import CSVPostProcessor
from .csv_writer import CSVWriter
from .file_writer import FileWriter
from .json_writer import JSONWriter
from .xlsx_writer import XLSXWriter

__all__ = [
    "FileWriter",
    "CSVWriter",
    "XLSXWriter",
    "JSONWriter",
    "CSVPostProcessor",
    "CSVDeduplicator",
    # Утилиты буферизации
    "HASH_BATCH_SIZE",
    "MAX_BUFFER_SIZE",
    "MMAP_THRESHOLD_BYTES",
    "READ_BUFFER_SIZE",
    "WRITE_BUFFER_SIZE",
    "_calculate_optimal_buffer_size",
    # #75: _open_file_with_mmap_support и _close_file_with_mmap_support удалены как неиспользуемые
    "_safe_move_file",
    "_should_use_mmap",
    "mmap_file_context",
]
