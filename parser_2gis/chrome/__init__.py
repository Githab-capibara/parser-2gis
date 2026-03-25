"""Модуль Chrome для управления браузером.

Предоставляет классы и функции для работы с Chrome:
- ChromeRemote - удалённое управление через DevTools Protocol
- ChromeOptions - настройка параметров браузера

Backward совместимость:
- Все импорты из parser_2gis.chrome продолжают работать
- Экспортируются все публичные API из подмодулей
"""

from .browser import ChromeBrowser
from .http_cache import (
    HTTP_CACHE_MAXSIZE,
    HTTP_CACHE_TTL_SECONDS,
    _cleanup_expired_cache,
    _get_cache_key,
    _get_http_cache,
    _HTTPCache,
    _HTTPCacheEntry,
)
from .js_executor import (
    _DANGEROUS_JS_PATTERNS,
    MAX_JS_CODE_LENGTH,
    _sanitize_js_string,
    _validate_js_code,
)
from .options import ChromeOptions
from .rate_limiter import _safe_external_request
from .remote import ChromeRemote

__all__ = [
    # Основные классы
    "ChromeRemote",
    "ChromeOptions",
    "ChromeBrowser",
    # HTTP кэш (для backward совместимости)
    "_HTTPCache",
    "_HTTPCacheEntry",
    "_cleanup_expired_cache",
    "_get_cache_key",
    "_get_http_cache",
    "HTTP_CACHE_MAXSIZE",
    "HTTP_CACHE_TTL_SECONDS",
    # Валидация JS (для backward совместимости)
    "_DANGEROUS_JS_PATTERNS",
    "_sanitize_js_string",
    "_validate_js_code",
    "MAX_JS_CODE_LENGTH",
    # Rate limiting (для backward совместимости)
    "_safe_external_request",
]
