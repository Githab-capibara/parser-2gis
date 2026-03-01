from __future__ import annotations

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from ..chrome.options import default_memory_limit
from ..common import floor_to_hundreds


def default_max_records() -> int:
    """Пытается найти линейную аппроксимацию для оптимального количества записей."""
    max_records = floor_to_hundreds((550 * default_memory_limit() / 1024 - 400))
    return max_records if max_records > 0 else 1


class ParserOptions(BaseModel):
    """Представляет все возможные опции для парсера.

    Атрибуты:
        skip_404_response: Пропускать ли 404 ответ документа или нет.
        delay_between_clicks: Задержка между кликами по каждому элементу в миллисекундах.
        max_records: Максимальное количество записей для парсинга с одного URL.
        use_gc: Использовать сборщик мусора.
        gc_pages_interval: Запускать сборщик мусора каждые N страниц (если `use_gc` включён).
    """
    skip_404_response: bool = True
    delay_between_clicks: NonNegativeInt = 0
    max_records: PositiveInt = default_max_records()
    use_gc: bool = False
    gc_pages_interval: PositiveInt = 10
