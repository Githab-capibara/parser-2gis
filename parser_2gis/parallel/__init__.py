"""Модуль для параллельного парсинга.

Предоставляет классы и функции для одновременного парсинга
нескольких городов с использованием нескольких экземпляров браузера.

Структура модуля:
- coordinator.py: ParallelCoordinator (координация потоков)
- thread_coordinator.py: ThreadCoordinator (управление потоками и семафорами)
- merger.py: ParallelFileMerger (слияние файлов) + функции слияния
- file_merger.py: FileMergerStrategy (стратегия слияния файлов)
- error_handler.py: ParallelErrorHandler (обработка ошибок)
- progress.py: ParallelProgressReporter (прогресс)
- url_parser.py: ParallelUrlParser (генерация и парсинг URL)
- memory_manager.py: MemoryManager (управление памятью и GC)
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
from .file_merger import FileMergerStrategy
from .lock_manager import ParallelLockManager
from .memory_manager import MemoryManager, check_memory_safety, get_memory_manager
from .merge_csv_handler import MergeCSVHandler
from .merge_lock_manager import MergeLockManager
from .merger import (
    ParallelFileMerger,
)
from .options import MAX_TEMP_FILES, ParallelOptions
from .parallel_parser import (
    ParallelCityParser,
    ParallelCityParserThread,
    ParserThreadConfig,
)
from .progress import ParallelProgressReporter
from .strategies import (
    MemoryCheckStrategy,
    MemoryMonitorProtocol,
    ParserFactory,
    ParserResult,
    ParseStrategy,
    UrlGenerationStrategy,
    UrlTuple,
    WriterFactory,
)
from .thread_coordinator import ThreadCoordinator
from .thread_manager import ThreadManager
from .url_parser import ParallelUrlParser

# Экспорт основного API для обратной совместимости
__all__ = [
    "DEFAULT_TIMEOUT",
    "MAX_LOCK_FILE_AGE",
    "MAX_TEMP_FILES",
    "MAX_TEMP_FILES_MONITORING",
    "MAX_TIMEOUT",
    "MAX_WORKERS",
    # Константы из file_merger
    "MERGE_LOCK_TIMEOUT",
    "MIN_TIMEOUT",
    # Константы
    "MIN_WORKERS",
    "ORPHANED_TEMP_FILE_AGE",
    # Прогресс
    "PROGRESS_UPDATE_INTERVAL",
    # Константы очистки
    "TEMP_FILE_CLEANUP_INTERVAL",
    "FileMergerStrategy",
    "MemoryCheckStrategy",
    "MemoryManager",
    "MemoryMonitorProtocol",
    "MergeCSVHandler",
    "MergeLockManager",
    # Основные классы (старые для обратной совместимости)
    "ParallelCityParser",
    "ParallelCityParserThread",
    # Основные классы (новые)
    "ParallelCoordinator",
    "ParallelErrorHandler",
    "ParallelFileMerger",
    # ISSUE-024, 025: Новые выделенные компоненты
    "ParallelLockManager",
    # Опции
    "ParallelOptions",
    "ParallelProgressReporter",
    "ParallelRunConfig",
    "ParallelUrlParser",
    # ISSUE-030, 040: Стратегии с DI
    "ParseStrategy",
    "ParserFactory",
    "ParserResult",
    "ParserThreadConfig",  # Deprecated: используйте ParallelRunConfig
    "ThreadCoordinator",
    "ThreadManager",
    "UrlGenerationStrategy",
    "UrlTuple",
    "WriterFactory",
    "check_memory_safety",
    # Функции управления памятью
    "get_memory_manager",
]
