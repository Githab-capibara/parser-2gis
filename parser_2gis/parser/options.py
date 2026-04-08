"""Модуль опций парсера.

Предоставляет класс ParserOptions для настройки параметров парсинга:
- Задержки между кликами
- Лимиты записей
- Настройки сборщика мусора
- Повторные попытки при ошибках
- Таймауты и пороги памяти
"""

from __future__ import annotations

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from parser_2gis.chrome.constants import DEFAULT_MEMORY_LIMIT_MB
from parser_2gis.chrome.options import default_memory_limit

# NOTE: Циклический импорт: constants -> parser -> parser.options -> utils -> constants
# Данный модуль импортирует из constants и utils, создавая цикл зависимостей.
from parser_2gis.constants import (
    MAX_RECORDS_BASE_OFFSET,
    MAX_RECORDS_MEMORY_COEFFICIENT,
    MAX_RECORDS_MEMORY_DIVISOR,
)
from parser_2gis.utils import floor_to_hundreds

# Константы для значений по умолчанию
_DEFAULT_GC_PAGES_INTERVAL = 10
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY_BASE = 1
_DEFAULT_MAX_CONSECUTIVE_EMPTY_PAGES = 3
_DEFAULT_TIMEOUT_SECONDS = 60
_DEFAULT_MAX_RECORDS_FALLBACK = 100


def default_max_records() -> int:
    """Пытается найти линейную аппроксимацию для оптимального количества записей."""
    memory_limit = default_memory_limit()

    # Защита от отрицательного или нулевого значения памяти
    if memory_limit <= 0:
        return _DEFAULT_MAX_RECORDS_FALLBACK

    # ISSUE-039: Вынесены магические числа в константы
    max_records = floor_to_hundreds(
        (
            MAX_RECORDS_MEMORY_COEFFICIENT * memory_limit / MAX_RECORDS_MEMORY_DIVISOR
            - MAX_RECORDS_BASE_OFFSET
        )
    )

    # Гарантируем положительное значение
    return max(_DEFAULT_MAX_RECORDS_FALLBACK, max_records)


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
        retry_delay_base: Базовая задержка между повторными попытками в секундах
            (используется экспоненциальная задержка).
        memory_threshold: Порог использования памяти в МБ для автоматической очистки (по умолчанию 2048).
        stop_on_first_404: Останавливать парсинг немедленно при первом 404 ответе (по умолчанию False).
        max_consecutive_empty_pages: Максимальное количество подряд пустых страниц перед остановкой (по умолчанию 3).
        timeout: Таймаут выполнения парсинга в секундах (по умолчанию 60).
    """

    skip_404_response: bool = True
    delay_between_clicks: NonNegativeInt = 0
    max_records: PositiveInt = default_max_records()
    use_gc: bool = False
    gc_pages_interval: PositiveInt = _DEFAULT_GC_PAGES_INTERVAL
    retry_on_network_errors: bool = True
    max_retries: PositiveInt = _DEFAULT_MAX_RETRIES
    retry_delay_base: PositiveInt = _DEFAULT_RETRY_DELAY_BASE
    memory_threshold: PositiveInt = DEFAULT_MEMORY_LIMIT_MB
    stop_on_first_404: bool = False
    max_consecutive_empty_pages: PositiveInt = _DEFAULT_MAX_CONSECUTIVE_EMPTY_PAGES
    timeout: PositiveInt = _DEFAULT_TIMEOUT_SECONDS
