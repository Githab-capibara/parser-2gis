"""
Модуль виджетов для TUI Parser2GIS.

Современные виджеты с поддержкой:
- Unicode иконок
- Градиентов
- Анимаций
- Цветовых схем
"""

from .progress_bar import ProgressBar, MultiProgressBar
from .log_viewer import LogViewer, CompactLogViewer, DetailedLogViewer
from .city_list import CityList
from .category_list import CategoryList
from .scroll_area import ScrollArea
from .checkbox import Checkbox
from .navigable_widget import NavigableWidget, NavigableContainer, ButtonWidget

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
