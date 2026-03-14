"""
Новый TUI модуль для Parser2GIS на библиотеке pytermgui.

Предоставляет современный интерактивный интерфейс с:
- Многоэкранной навигацией
- Формами настроек
- Выбором городов и категорий
- Прогресс-барами и логами в реальном времени
"""

from .app import Parser2GISTUI, TUIApp
from .run_parallel import run_omsk_parallel

__all__ = [
    "Parser2GISTUI",
    "TUIApp",
    "run_omsk_parallel",
]
