"""
Модуль для параллельного парсинга.

Предоставляет классы и функции для одновременного парсинга
нескольких городов с использованием нескольких экземпляров браузера.

Структура модуля:
- coordinator.py: ParallelCoordinator (координация потоков)
- merger.py: ParallelFileMerger (слияние файлов) + функции слияния
- error_handler.py: ParallelErrorHandler (обработка ошибок)
- progress.py: ParallelProgressReporter (прогресс)
- url_parser.py: UrlParser (генерация URL)
- thread_manager.py: ThreadManager (управление потоками)
- parallel_parser.py: Устаревший класс (обратная совместимость)
- options.py: Опции параллельного парсинга

Примечание:
    Константы перемещены в constants.py для централизованного управления.
"""

# Ре-экспорт констант из constants.py для обратной совместимости
from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_LOCK_FILE_AGE,
    MAX_TEMP_FILES_MONITORING,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MERGE_LOCK_TIMEOUT,
    MIN_TIMEOUT,
    MIN_WORKERS,
    ORPHANED_TEMP_FILE_AGE,
    PROGRESS_UPDATE_INTERVAL,
    TEMP_FILE_CLEANUP_INTERVAL,
)

from .config import ParallelRunConfig
from .coordinator import ParallelCoordinator
from .error_handler import ParallelErrorHandler
from .merger import (
    MergeConfig,  # noqa: F401 - используется для типизации
    ParallelFileMerger,
    _acquire_merge_lock,
    _cleanup_source_files,
    _merge_csv_files,
    _validate_merged_file,
)
from .options import MAX_TEMP_FILES, ParallelOptions
from .parallel_parser import (
    ParallelCityParser,
    ParallelCityParserThread,
    ParserThreadConfig,  # noqa: F401 - используется для __all__
    _cleanup_all_temp_files,
    _register_temp_file,
    _temp_files_lock,
    _temp_files_registry,
    _unregister_temp_file,
)
from .progress import ParallelProgressReporter
from .thread_manager import ThreadManager
from .url_parser import UrlParser

# Экспорт основного API для обратной совместимости
__all__ = [
    # Основные классы (новые)
    "ParallelCoordinator",
    "ParallelFileMerger",
    "ParallelErrorHandler",
    "ParallelProgressReporter",
    "ParallelRunConfig",
    "UrlParser",
    "ThreadManager",
    # Основные классы (старые для обратной совместимости)
    "ParallelCityParser",
    "ParallelCityParserThread",
    "ParserThreadConfig",  # Deprecated: используйте ParallelRunConfig
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
