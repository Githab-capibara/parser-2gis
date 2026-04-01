"""Модуль парсеров для различных типов страниц 2GIS.

Предоставляет классы парсеров:
- MainParser - основной парсер для поисковой выдачи (использует композицию)
- FirmParser - парсер для страниц организаций
- InBuildingParser - парсер для вкладок "В здании"

Структура основного парсера:
- main_parser.py: MainPageParser (DOM операции и навигация)
- main_extractor.py: MainDataExtractor (извлечение данных)
- main_processor.py: MainDataProcessor (обработка данных и пагинация)
"""

from .firm import FirmParser
from .in_building import InBuildingParser
from .main import MainParser
from .main_extractor import MainDataExtractor
from .main_parser import MainPageParser
from .main_processor import MainDataProcessor

__all__ = [
    "FirmParser",
    "InBuildingParser",
    "MainDataExtractor",
    "MainDataProcessor",
    "MainPageParser",
    "MainParser",
]
