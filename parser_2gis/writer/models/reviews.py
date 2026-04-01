"""Модель отзывов об организации.

Предоставляет класс Reviews для представления отзывов:
- general_rating - общий рейтинг (0-5)
- general_review_count - общее количество отзывов
"""

from __future__ import annotations


from pydantic import BaseModel


class Reviews(BaseModel):
    """Модель отзывов об организации.

    Атрибуты:
        general_rating: Общий рейтинг организации (от 0 до 5).
        general_review_count: Общее количество отзывов.
    """

    # Общий рейтинг
    general_rating: float | None = None

    # Общее кол-во отзывов
    general_review_count: int | None = None
