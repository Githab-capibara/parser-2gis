"""Модуль опций Chrome.

Предоставляет класс ChromeOptions для настройки параметров браузера:
- Путь к бинарному файлу
- Режимы запуска (headless, maximized)
- Лимиты памяти
- Задержки запуска
"""

from __future__ import annotations

import pathlib

import psutil
from pydantic import BaseModel, PositiveInt

from parser_2gis.chrome.constants import MEMORY_FRACTION_FOR_V8
from parser_2gis.utils import floor_to_hundreds


def default_memory_limit() -> int:
    """Лимит памяти по умолчанию для V8 — MEMORY_FRACTION_FOR_V8 от общей физической памяти в МБ.

    Returns:
        Лимит памяти в мегабайтах, округлённый вниз до ближайшей сотни.

    """
    memory_total = psutil.virtual_memory().total / 1024**2  # Конвертируем в МБ
    # ISSUE-038: Вынесено магическое число 0.75 в константу MEMORY_FRACTION_FOR_V8
    return floor_to_hundreds(round(MEMORY_FRACTION_FOR_V8 * memory_total))


class ChromeOptions(BaseModel):
    """Представляет все возможные опции для Chrome.

    Атрибуты:
        binary_path: Путь к бинарному файлу Chrome. Если не указан, определяется автоматически.
        start_maximized: Запускать браузер развёрнутым.
        headless: Запускать браузер скрыто, без графического интерфейса.
        disable_images: Отключить загрузку изображений для экономии трафика.
        silent_browser: Не показывать отладочную информацию Chrome в stdout.
        memory_limit: Максимальный размер памяти V8 в мегабайтах.
        startup_delay: Задержка запуска браузера в секундах.
    """

    binary_path: pathlib.Path | None = None
    start_maximized: bool = False
    headless: bool = False
    disable_images: bool = True
    silent_browser: bool = True
    memory_limit: PositiveInt = default_memory_limit()
    startup_delay: int = 0
