"""Модуль runner для запуска парсера.

Предоставляет классы для запуска парсинга:
- AbstractRunner - базовый абстрактный класс
- CLIRunner - запуск в режиме командной строки
- GUIRunner - запуск в режиме GUI
"""

from .cli import CLIRunner
from .runner import AbstractRunner, GUIRunner

__all__ = ["CLIRunner", "AbstractRunner", "GUIRunner"]
