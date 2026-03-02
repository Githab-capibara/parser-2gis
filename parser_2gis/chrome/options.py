from __future__ import annotations

import pathlib
from typing import Optional

import psutil
from pydantic import BaseModel, PositiveInt

from ..common import floor_to_hundreds


def default_memory_limit() -> int:
    """Лимит памяти по умолчанию для V8 - 0.75 от общей физической памяти в МБ."""
    memory_total = psutil.virtual_memory().total / 1024 ** 2  # Конвертируем в МБ
    return floor_to_hundreds(round(0.75 * memory_total))


class ChromeOptions(BaseModel):
    """Представляет все возможные опции для Chrome.

    Атрибуты:
        binary_path: Путь к бинарному файлу Chrome. Если не указан, пытается найти автоматически.
        start_maximized: Запускать браузер развёрнутым.
        headless: Запускать браузер скрыто, без GUI.
        disable_images: Отключить изображения.
        silent_browser: Не показывать вывод Chrome в `stdout`.
        memory_size: Максимальный размер памяти V8.
    """
    binary_path: Optional[pathlib.Path] = None
    start_maximized: bool = False
    headless: bool = False
    disable_images: bool = True
    silent_browser: bool = True
    memory_limit: PositiveInt = default_memory_limit()
