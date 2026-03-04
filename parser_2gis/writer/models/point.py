from __future__ import annotations

from pydantic import BaseModel


class Point(BaseModel):
    """Модель точки на карте (координаты).

    Атрибуты:
        lat: Широта в системе координат WGS84.
        lon: Долгота в системе координат WGS84.
    """
    # Широта
    lat: float

    # Долгота
    lon: float
