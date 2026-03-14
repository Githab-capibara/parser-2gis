from __future__ import annotations

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from ..chrome.options import default_memory_limit
from ..common import floor_to_hundreds


def default_max_records() -> int:
    """Пытается найти линейную аппроксимацию для оптимального количества записей."""
    memory_limit = default_memory_limit()

    # Защита от отрицательного или нулевого значения памяти
    if memory_limit <= 0:
        return 100

    max_records = floor_to_hundreds((550 * memory_limit / 1024 - 400))

    # Гарантируем положительное значение
    return max(100, max_records)


class ParserOptions(BaseModel):
    """Представляет все возможные опции для парсера.

    Атрибуты:
        skip_404_response: Пропускать ли 404 ответ документа или нет.
        delay_between_clicks: Задержка между кликами по каждому элементу в миллисекундах.
        max_records: Максимальное количество записей для парсинга с одного URL.
        use_gc: Использовать сборщик мусора.
        gc_pages_interval: Запускать сборщик мусора каждые N страниц (если `use_gc` включён).
        retry_on_network_errors: Выполнять повторные попытки при ошибках сети (502, 503, 504, TimeoutError).
        max_retries: Максимальное количество повторных попыток при ошибках сети.
        retry_delay_base: Базовая задержка между повторными попытками в секундах (используется экспоненциальная задержка).
        memory_threshold: Порог использования памяти в МБ для автоматической очистки (по умолчанию 2048).
        stop_on_first_404: Останавливать парсинг немедленно при первом 404 ответе (по умолчанию False).
        max_consecutive_empty_pages: Максимальное количество подряд пустых страниц перед остановкой (по умолчанию 3).
    """

    skip_404_response: bool = True
    delay_between_clicks: NonNegativeInt = 0
    max_records: PositiveInt = default_max_records()
    use_gc: bool = False
    gc_pages_interval: PositiveInt = 10
    retry_on_network_errors: bool = True
    max_retries: PositiveInt = 3
    retry_delay_base: PositiveInt = 1
    memory_threshold: PositiveInt = 2048
    stop_on_first_404: bool = False
    max_consecutive_empty_pages: PositiveInt = 3
