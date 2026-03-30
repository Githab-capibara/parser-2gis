"""
Модуль для вспомогательных классов параллельного парсинга.

DEPRECATED: Этот модуль перемещён в parser_2gis.parallel.helpers
Используйте: from parser_2gis.parallel.helpers import FileMerger, ProgressTracker, StatsCollector
"""

from parser_2gis.parallel.helpers import FileMerger, ProgressTracker, StatsCollector

__all__ = ["FileMerger", "ProgressTracker", "StatsCollector"]
