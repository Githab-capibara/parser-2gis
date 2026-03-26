"""
Модуль для параллельного парсинга.

Предоставляет классы и функции для одновременного парсинга
нескольких городов с использованием нескольких экземпляров браузера.

Структура модуля:
- parallel_parser.py: ParallelCityParser и ParallelCityParserThread
- file_merger.py: Функции слияния CSV файлов
- temp_file_timer.py: Таймер очистки временных файлов
- progress_tracker.py: Константы и функции отслеживания прогресса
- options.py: Опции параллельного парсинга
"""

# Ре-экспорт констант из constants.py для обратной совместимости
from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_LOCK_FILE_AGE,
    MAX_TEMP_FILES_MONITORING,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MIN_TIMEOUT,
    MIN_WORKERS,
    ORPHANED_TEMP_FILE_AGE,
    TEMP_FILE_CLEANUP_INTERVAL,
)

from .file_merger import (
    MERGE_LOCK_TIMEOUT_LOCAL,
    _acquire_merge_lock,
    _cleanup_source_files,
    _merge_csv_files,
    _validate_merged_file,
)
from .options import MAX_TEMP_FILES, ParallelOptions
from .parallel_parser import (
    ParallelCityParser,
    ParallelCityParserThread,
    _cleanup_all_temp_files,
    _register_temp_file,
    _temp_files_lock,
    _temp_files_registry,
    _unregister_temp_file,
)
from .progress_tracker import PROGRESS_UPDATE_INTERVAL

MERGE_LOCK_TIMEOUT = MERGE_LOCK_TIMEOUT_LOCAL

# Экспорт основного API для обратной совместимости
__all__ = [
    # Основные классы
    "ParallelCityParser",
    "ParallelCityParserThread",
    # Опции
    "ParallelOptions",
    "MAX_TEMP_FILES",
    # Константы очистки
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
    # Слияние файлов
    "_merge_csv_files",
    "_acquire_merge_lock",
    "_cleanup_source_files",
    "_validate_merged_file",
    # Константы из file_merger
    "MERGE_LOCK_TIMEOUT",
    "MAX_LOCK_FILE_AGE",
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL",
    # Ре-экспорт для обратной совместимости с тестами
    "_temp_files_lock",
    "_temp_files_registry",
    "_register_temp_file",
    "_unregister_temp_file",
    "_cleanup_all_temp_files",
    # Константы
    "MIN_WORKERS",
    "MAX_WORKERS",
    "MIN_TIMEOUT",
    "MAX_TIMEOUT",
    "DEFAULT_TIMEOUT",
]
