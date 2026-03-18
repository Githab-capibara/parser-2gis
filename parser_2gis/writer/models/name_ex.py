from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

class NameEx(BaseModel):
    """Модель расширенного названия организации.

    Атрибуты:
        primary: Собственное имя филиала.
        extension: Расширение имени филиала (например "кафе").
        legal_name: Юридическое название филиала (например "ООО Солнышко").
        description: Описание филиала (например "Склад").
        short_name: Короткое имя на карте.
        addition: Дополнительная информация к названию филиала, которая должна быть показана в развёрнутой карточке.
    """

    # Собственное имя филиала
    primary: str

    # Расширение имени филиала (например "кафе")
    extension: Optional[str] = None

    # Юридическое название филиала (например "ООО Солнышко")
    legal_name: Optional[str] = None

    # Описание филиала (например "Склад")
    description: Optional[str] = None

    # Короткое имя на карте
    short_name: Optional[str] = None

    # Дополнительная информация к названию филиала,
    # которая должна быть показана в развёрнутой карточке
    addition: Optional[str] = None
