"""Модуль runner для запуска парсера.

Предоставляет классы для запуска парсинга:
- CLIRunner - запуск в режиме командной строки
- GUIRunner - заглушка для GUI режима (тесты)
- AbstractRunner - абстрактный базовый класс
"""

from .cli import CLIRunner
from .runner import AbstractRunner, GUIRunner

__all__ = ["CLIRunner", "AbstractRunner", "GUIRunner"]
