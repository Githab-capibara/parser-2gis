"""Модуль парсеров для различных типов страниц 2GIS.

Предоставляет классы парсеров:
- MainParser - основной парсер для поисковой выдачи
- FirmParser - парсер для страниц организаций
- InBuildingParser - парсер для вкладок "В здании"
"""

from .firm import FirmParser
from .in_building import InBuildingParser
from .main import MainParser

__all__ = ["FirmParser", "InBuildingParser", "MainParser"]
