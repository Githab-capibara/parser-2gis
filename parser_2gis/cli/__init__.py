"""Модуль CLI для взаимодействия с пользователем.

Предоставляет компоненты для CLI режима:
- cli_app - функция запуска CLI приложения
- ProgressManager - менеджер прогресс-бара
- ProgressStats - статистика прогресса
- main - точка входа CLI приложения
- parse_arguments - парсинг аргументов командной строки
- ArgumentValidator - валидатор аргументов
- ArgumentHelpFormatter - форматировщик справки

Backward совместимость:
- from parser_2gis.cli import main
- from parser_2gis.cli import parse_arguments
- from parser_2gis.cli import ArgumentValidator
- from parser_2gis.cli import ArgumentHelpFormatter
"""

from .app import cli_app
from .arguments import parse_arguments
from .formatter import ArgumentHelpFormatter
from .main import main
from .progress import ProgressManager, ProgressStats
from .validator import ArgumentValidator

__all__ = [
    "cli_app",
    "ProgressManager",
    "ProgressStats",
    "main",
    "parse_arguments",
    "ArgumentValidator",
    "ArgumentHelpFormatter",
]
