"""Parser2GIS — парсер сайта 2GIS для сбора данных об организациях.

Экспортируемые компоненты:
- main: Точка входа CLI
- __version__: Версия пакета
- ParallelCityParser: Параллельный парсер городов
- ParallelCityParserThread: Поток для параллельного парсинга
- CacheManager: Менеджер кэширования результатов
- ValidationResult: Результат валидации
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
from .utils.temp_file_manager import TempFileManager, temp_file_manager
from .validation import ValidationResult
from .version import version as __version__

__all__ = [
    "CacheManager",
    "CancelCallback",
    "CleanupCallback",
    "LogCallback",
    "LoggerProtocol",
    "ParallelCityParser",
    "ParallelCityParserThread",
    "Parser",
    "ProgressCallback",
    "ProgressManager",
    "TempFileManager",
    "ValidationResult",
    "Writer",
    "__version__",
    "logger",
    "main",
    "temp_file_manager",
]
