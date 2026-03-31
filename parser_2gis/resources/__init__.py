"""
Модуль ресурсов парсера.

Предоставляет доступ к статическим ресурсам: города, рубрики, изображения.
"""

from parser_2gis.resources.categories_93 import CATEGORIES_93
from parser_2gis.resources.cities_loader import load_cities_json

__all__ = ["CATEGORIES_93", "load_cities_json"]
