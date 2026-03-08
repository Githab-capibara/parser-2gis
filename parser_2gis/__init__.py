"""
Parser2GIS - парсер сайта 2GIS для сбора данных об организациях.

Экспортируемые компоненты:
- main: Точка входа CLI
- __version__: Версия пакета
- ParallelCityParser: Параллельный парсер городов
- ParallelCityParserThread: Поток для параллельного парсинга
"""

from .main import main
from .parallel_parser import ParallelCityParser, ParallelCityParserThread
from .version import version as __version__
from .cache import CacheManager
from .validator import DataValidator, ValidationResult
from .statistics import ParserStatistics, StatisticsExporter
from .cli.progress import ProgressManager
from .logger import logger

__all__ = [
    'main',
    '__version__',
    'ParallelCityParser',
    'ParallelCityParserThread',
    'CacheManager',
    'DataValidator',
    'ValidationResult',
    'ParserStatistics',
    'StatisticsExporter',
    'ProgressManager',
    'logger',
]