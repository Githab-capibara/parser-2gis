from __future__ import annotations

from pydantic import BaseModel


class Org(BaseModel):
    """Модель организации.

    Атрибуты:
        id: Уникальный идентификатор организации.
        name: Собственное имя организации.
        branch_count: Количество филиалов данной организации.
    """

    # Идентификатор
    id: str

    # Собственное имя организации
    name: str

    # Количество филиалов данной организации
    branch_count: int
