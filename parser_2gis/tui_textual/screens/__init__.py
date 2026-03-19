"""
Модуль экранов для TUI на Textual.
"""

from .main_menu import MainMenuScreen
from .city_selector import CitySelectorScreen
from .category_selector import CategorySelectorScreen
from .parsing_screen import ParsingScreen
from .settings import BrowserSettingsScreen, ParserSettingsScreen, OutputSettingsScreen
from .other_screens import CacheViewerScreen, AboutScreen

__all__ = [
    "MainMenuScreen",
    "CitySelectorScreen",
    "CategorySelectorScreen",
    "BrowserSettingsScreen",
    "ParserSettingsScreen",
    "OutputSettingsScreen",
    "ParsingScreen",
    "CacheViewerScreen",
    "AboutScreen",
]
