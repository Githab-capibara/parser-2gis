"""Модуль runner для запуска парсера.

Предоставляет классы для запуска парсинга:
- CLIRunner - запуск в режиме командной строки
- AbstractRunner - абстрактный базовый класс

Примечание:
    GUIRunner был удалён как неиспользуемый код (YAGNI).
"""

from .cli import CLIRunner
from .runner import AbstractRunner

__all__ = ["AbstractRunner", "CLIRunner"]
