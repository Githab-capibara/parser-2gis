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

from .file_merger import (
    _acquire_merge_lock,
    _cleanup_source_files,
    _merge_csv_files,
    _validate_merged_file,
)
from .options import ParallelOptions
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
from .temp_file_timer import (
    MAX_TEMP_FILES_MONITORING,
    ORPHANED_TEMP_FILE_AGE,
    TEMP_FILE_CLEANUP_INTERVAL,
    _TempFileTimer,
)

# Экспорт основного API для обратной совместимости
__all__ = [
    # Основные классы
    "ParallelCityParser",
    "ParallelCityParserThread",
    # Опции
    "ParallelOptions",
    # Таймер очистки
    "_TempFileTimer",
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
    # Слияние файлов
    "_merge_csv_files",
    "_acquire_merge_lock",
    "_cleanup_source_files",
    "_validate_merged_file",
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL",
    # Ре-экспорт для обратной совместимости с тестами
    "_temp_files_lock",
    "_temp_files_registry",
    "_register_temp_file",
    "_unregister_temp_file",
    "_cleanup_all_temp_files",
]
