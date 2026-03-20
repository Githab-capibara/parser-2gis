"""Модуль CLI для взаимодействия с пользователем.

Предоставляет компоненты для CLI режима:
- cli_app - функция запуска CLI приложения
- ProgressManager - менеджер прогресс-бара
- ProgressStats - статистика прогресса
"""

from .app import cli_app
from .progress import ProgressManager, ProgressStats

__all__ = ["cli_app", "ProgressManager", "ProgressStats"]
