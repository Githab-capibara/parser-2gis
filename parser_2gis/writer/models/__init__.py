"""Модуль моделей данных для writer.

Предоставляет Pydantic модели для представления данных каталога 2GIS:
- CatalogItem - элемент каталога (филиал организации)
- Address, Point, Rubric, ContactGroup и другие модели
"""

from .address import Address
from .adm_div_item import AdmDivItem
from .catalog_item import CatalogItem
from .contact_group import ContactGroup
from .name_ex import NameEx
from .org import Org
from .point import Point
from .reviews import Reviews
from .rubric import Rubric
from .schedule import Schedule

__all__ = [
    "Address",
    "AdmDivItem",
    "CatalogItem",
    "ContactGroup",
    "NameEx",
    "Org",
    "Point",
    "Reviews",
    "Rubric",
    "Schedule",
]
