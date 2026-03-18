"""
Parser2GIS — парсер сайта 2GIS для сбора данных об организациях.

Экспортируемые компоненты:
- main: Точка входа CLI
- __version__: Версия пакета
- ParallelCityParser: Параллельный парсер городов
- ParallelCityParserThread: Поток для параллельного парсинга
- CacheManager: Менеджер кэширования результатов
- DataValidator: Валидатор данных
- ValidationResult: Результат валидации
- ParserStatistics: Статистика парсера
- StatisticsExporter: Экспортёр статистики
- ProgressManager: Менеджер прогресс-баров
- logger: Логгер приложения
"""

from .cache import CacheManager
from .cli.progress import ProgressManager
from .logger import logger
from .main import main
from .parallel_parser import ParallelCityParser, ParallelCityParserThread
from .statistics import ParserStatistics, StatisticsExporter
from .validator import DataValidator, ValidationResult
from .version import version as __version__

__all__ = [
    "main",
    "__version__",
    "ParallelCityParser",
    "ParallelCityParserThread",
    "CacheManager",
    "DataValidator",
    "ValidationResult",
    "ParserStatistics",
    "StatisticsExporter",
    "ProgressManager",
    "logger",
]
