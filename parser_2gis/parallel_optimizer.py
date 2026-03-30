"""
Модуль для оптимизации параллельного парсинга.

DEPRECATED: Этот модуль перемещён в parser_2gis.parallel.optimizer
Используйте: from parser_2gis.parallel.optimizer import ParallelOptimizer, ParallelTask
"""

from parser_2gis.parallel.optimizer import ParallelOptimizer, ParallelTask

__all__ = ["ParallelOptimizer", "ParallelTask"]
