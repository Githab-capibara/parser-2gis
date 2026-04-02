"""Константы безопасности для parser-2gis.

Этот модуль содержит константы связанные с безопасностью:
- Лимиты данных
- Безопасность путей
- Защита от атак

Пример использования:
    >>> from parser_2gis.constants.security import MAX_DATA_DEPTH, MAX_STRING_LENGTH
    >>> print(f"Максимальная глубина данных: {MAX_DATA_DEPTH}")
"""

from __future__ import annotations

# =============================================================================
# БЕЗОПАСНОСТЬ ДАННЫХ
# =============================================================================

# Максимальная глубина вложенности данных
MAX_DATA_DEPTH: int = 100

# Максимальная длина строки
MAX_STRING_LENGTH: int = 10000

# Максимальный размер данных
MAX_DATA_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Максимальный размер коллекции
MAX_COLLECTION_SIZE: int = 100000

# Максимальная длина пути
MAX_PATH_LENGTH: int = 4096


# =============================================================================
# БЕЗОПАСНОСТЬ INITIAL STATE
# =============================================================================

# Максимальная глубина initialState
MAX_INITIAL_STATE_DEPTH: int = 10

# Максимальный размер initialState
MAX_INITIAL_STATE_SIZE: int = 5 * 1024 * 1024  # 5 MB

# Максимальное количество элементов в коллекции
MAX_ITEMS_IN_COLLECTION: int = 10000


# =============================================================================
# БЕЗОПАСНОСТЬ JS
# =============================================================================

# Максимальная длина JavaScript кода
MAX_JS_CODE_LENGTH: int = 100000  # 100 KB

# Максимальный размер ответа
MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Максимальный общий размер JS скриптов
MAX_TOTAL_JS_SIZE: int = 50 * 1024 * 1024  # 50 MB

# Задержка запуска Chrome
CHROME_STARTUP_DELAY: float = 5.0


# =============================================================================
# RATE LIMITING
# =============================================================================

# Количество вызовов для внешнего rate limiting
EXTERNAL_RATE_LIMIT_CALLS: int = 10

# Период для внешнего rate limiting в секундах
EXTERNAL_RATE_LIMIT_PERIOD: int = 60


# =============================================================================
# HTTP КЭШИРОВАНИЕ
# =============================================================================

# TTL для HTTP кэша в секундах
HTTP_CACHE_TTL_SECONDS: int = 300

# Максимальный размер HTTP кэша
HTTP_CACHE_MAXSIZE: int = 1024


# =============================================================================
# БЕЗОПАСНОСТЬ ПУТЕЙ
# =============================================================================

# Максимальная длина URL decode итераций
MAX_URL_DECODE_ITERATIONS: int = 5

# Максимальная глубина рекурсии для unwrap_dot_dict
MAX_DICT_RECURSION_DEPTH: int = 10

# Максимальное количество попыток для уникальных имён файлов
MAX_UNIQUE_NAME_ATTEMPTS: int = 10

# Максимальная безопасная длина пути
MAX_PATH_LENGTH_SAFE: int = 4096

# Запрещённые символы в путях
FORBIDDEN_PATH_CHARS: list[str] = None  # type: ignore

# HTTP статус код OK
HTTP_STATUS_OK: int = 200


# Инициализация FORBIDDEN_PATH_CHARS после определения типа
FORBIDDEN_PATH_CHARS = ["..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"]


__all__ = [
    "MAX_DATA_DEPTH",
    "MAX_STRING_LENGTH",
    "MAX_DATA_SIZE",
    "MAX_COLLECTION_SIZE",
    "MAX_PATH_LENGTH",
    "MAX_INITIAL_STATE_DEPTH",
    "MAX_INITIAL_STATE_SIZE",
    "MAX_ITEMS_IN_COLLECTION",
    "MAX_JS_CODE_LENGTH",
    "MAX_RESPONSE_SIZE",
    "MAX_TOTAL_JS_SIZE",
    "CHROME_STARTUP_DELAY",
    "EXTERNAL_RATE_LIMIT_CALLS",
    "EXTERNAL_RATE_LIMIT_PERIOD",
    "HTTP_CACHE_TTL_SECONDS",
    "HTTP_CACHE_MAXSIZE",
    "HTTP_STATUS_OK",
    "MAX_URL_DECODE_ITERATIONS",
    "MAX_DICT_RECURSION_DEPTH",
    "MAX_UNIQUE_NAME_ATTEMPTS",
    "MAX_PATH_LENGTH_SAFE",
    "FORBIDDEN_PATH_CHARS",
]
