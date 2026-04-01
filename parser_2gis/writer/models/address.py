"""Модель адреса организации.

Предоставляет класс Address для представления адреса филиала:
- building_id - уникальный идентификатор дома
- building_name - название здания
- postcode - почтовый индекс
- makani - Makani адрес (Ближний Восток)
"""

from __future__ import annotations


from pydantic import BaseModel


class Address(BaseModel):
    """Модель адреса.

    Атрибуты:
        building_id: Уникальный идентификатор дома, к которому относится данный адрес.
        building_name: Название здания (в адресе для филиалов).
        building_code: Уникальный почтовый код здания.
        postcode: Почтовый индекс.
        makani: Makani адрес объекта (применяется в странах Ближнего Востока).
    """

    # Уникальный идентификатор дома, к которому относится данный адрес
    building_id: str | None = None

    # Название здания (в адресе для филиалов)
    building_name: str | None = None

    # Уникальный почтовый код здания
    building_code: str | None = None

    # Почтовый индекс
    postcode: str | None = None

    # Makani адрес объекта (применяется в странах Ближнего Востока)
    makani: str | None = None
