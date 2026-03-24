"""
Parser2GIS — парсер сайта 2GIS для сбора данных об организациях.

Экспортируемые компоненты:
- main: Точка входа CLI
- __version__: Версия пакета
- ParallelCityParser: Параллельный парсер городов
- ParallelCityParserThread: Поток для параллельного парсинга
- CacheManager: Менеджер кэширования результатов
- ValidationResult: Результат валидации
- ParserStatistics: Статистика парсера
- StatisticsExporter: Экспортёр статистики
- ProgressManager: Менеджер прогресс-баров
- logger: Логгер приложения
- temp_file_manager: Менеджер временных файлов
- protocols: Protocol для callback и интерфейсов
"""

from .cache import CacheManager
from .cli.progress import ProgressManager
from .logger import logger
from .main import main
from .parallel import ParallelCityParser, ParallelCityParserThread
from .protocols import (
    CancelCallback,
    CleanupCallback,
    LogCallback,
    LoggerProtocol,
    Parser,
    ProgressCallback,
    Writer,
)
from .statistics import ParserStatistics, StatisticsExporter
from .temp_file_manager import TempFileManager, temp_file_manager
from .validation import ValidationResult
from .version import version as __version__

__all__ = [
    "main",
    "__version__",
    "ParallelCityParser",
    "ParallelCityParserThread",
    "CacheManager",
    "ValidationResult",
    "ParserStatistics",
    "StatisticsExporter",
    "ProgressManager",
    "logger",
    "temp_file_manager",
    "TempFileManager",
    "ProgressCallback",
    "LogCallback",
    "CleanupCallback",
    "CancelCallback",
    "Writer",
    "Parser",
    "LoggerProtocol",
]
