"""
Модуль виджетов для TUI Parser2GIS.

Современные виджеты с поддержкой:
- Unicode иконок
- Градиентов
- Анимаций
- Цветовых схем
"""

from .category_list import CategoryList
from .checkbox import Checkbox
from .city_list import CityList
from .log_viewer import CompactLogViewer, DetailedLogViewer, LogViewer
from .navigable_widget import ButtonWidget, NavigableContainer, NavigableWidget
from .progress_bar import MultiProgressBar, ProgressBar
from .scroll_area import ScrollArea

__all__ = [
    # Прогресс-бары
    "ProgressBar",
    "MultiProgressBar",
    # Логгеры
    "LogViewer",
    "CompactLogViewer",
    "DetailedLogViewer",
    # Списки
    "CityList",
    "CategoryList",
    # Контейнеры
    "ScrollArea",
    # Элементы управления
    "Checkbox",
    "NavigableWidget",
    "NavigableContainer",
    "ButtonWidget",
]
