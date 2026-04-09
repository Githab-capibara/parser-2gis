"""Модуль Chrome для управления браузером.

Предоставляет классы и функции для работы с Chrome:
- ChromeRemote - удалённое управление через DevTools Protocol
- ChromeOptions - настройка параметров браузера

Backward совместимость:
- Все импорты из parser_2gis.chrome продолжают работать
- Экспортируются все публичные API из подмодулей
"""

from .browser import ChromeBrowser
from .browser_builder import ChromeBrowserBuilder
from .js_executor import (
    DANGEROUS_JS_PATTERNS,
    MAX_JS_CODE_LENGTH,
    _validate_js_code,
)
from .options import ChromeOptions
from .rate_limiter import _safe_external_request
from .remote import ChromeRemote

__all__ = [
    # Валидация JS (для backward совместимости)
    "DANGEROUS_JS_PATTERNS",
    "MAX_JS_CODE_LENGTH",
    # ISSUE 114: Builder для ChromeBrowser
    "ChromeBrowserBuilder",
    "ChromeBrowser",
    "ChromeOptions",
    # Основные классы
    "ChromeRemote",
    # Rate limiting (для backward совместимости)
    "_safe_external_request",
    "_validate_js_code",
]
