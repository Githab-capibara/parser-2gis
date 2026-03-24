"""Модуль удалённого управления Chrome через DevTools Protocol.

Предоставляет класс ChromeRemote для взаимодействия с браузером Chrome:
- Управление браузером через WebSocket
- Выполнение JavaScript кода
- Работа с DOM деревом
- Перехват сетевых запросов
- Кэширование HTTP запросов
- Валидация JavaScript кода на безопасность
"""

from __future__ import annotations

import base64
import queue
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import pychrome

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

try:
    from ratelimit import limits, sleep_and_retry
except ImportError:
    limits = None  # type: ignore[assignment, misc]
    sleep_and_retry = None  # type: ignore[assignment, misc]

try:
    from requests.exceptions import RequestException
except ImportError:
    RequestException = Exception  # type: ignore[misc, assignment]
from websocket import WebSocketException

from parser_2gis.logger.logger import logger as app_logger
from parser_2gis.utils.decorators import wait_until_finished

from .browser import ChromeBrowser
from .constants import (  # L6: rate limiting для внешних запросов
    CHROME_STARTUP_DELAY,  # L4: магические числа вынесены в константы
    EXTERNAL_RATE_LIMIT_CALLS,
    EXTERNAL_RATE_LIMIT_PERIOD,
    MAX_JS_CODE_LENGTH,  # L4: магические числа вынесены в константы
    MAX_RESPONSE_SIZE,  # L9: лимит размера загружаемых файлов
    MAX_TOTAL_JS_SIZE,  # L4: магические числа вынесены в константы
)
from .dom import DOMNode
from .exceptions import ChromeException
from .patches import patch_all

# =============================================================================
# ЛОКАЛЬНЫЕ КОНСТАНТЫ И ПАТТЕРНЫ
# =============================================================================

# Задержка между проверками порта в секундах
PORT_CHECK_RETRY_DELAY: float = 0.1

# Оптимизация: скомпилированные regex паттерны для проверки портов
_PORT_CHECK_PATTERN = re.compile(r"^http://127\.0\.0\.1:(\d+)$")

# Паттерн для обнаружения потенциально опасных конструкций в JS

# Оптимизация: скомпилированные паттерны вместо компиляции при каждом вызове
_DANGEROUS_JS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "eval() запрещён"),
    (re.compile(r"(?<![\w])Function\s*\("), "конструктор Function запрещён"),
    (re.compile(r'\bsetTimeout\s*\([^,]*,\s*["\']'), "setTimeout с строковым кодом запрещён"),
    (re.compile(r'\bsetInterval\s*\([^,]*,\s*["\']'), "setInterval с строковым кодом запрещён"),
    (re.compile(r"\bdocument\.write\s*\("), "document.write() запрещён"),
    (re.compile(r"\.innerHTML\s*="), "прямая установка innerHTML запрещена"),
    (re.compile(r"\.outerHTML\s*="), "прямая установка outerHTML запрещена"),
    (
        re.compile(r"document\s*\.\s*createElement\s*\(\s*['\"]script['\"]"),
        "создание script элемента запрещено",
    ),
    (re.compile(r"\bimport\s*\("), "динамический import запрещён"),
    (re.compile(r"\bWebSocket\s*\("), "WebSocket соединение запрещено"),
    (re.compile(r"\bfetch\s*\([^)]*\)\s*\.then"), "fetch с обработкой .then() запрещён"),
    (re.compile(r"\bfetch\s*\([^)]*\)\s*\.catch"), "fetch с обработкой .catch() запрещён"),
    (re.compile(r"\bXMLHttpRequest\s*\("), "XMLHttpRequest запрещён"),
    (re.compile(r"\.src\s*=\s*['\"]http"), "установка src с http запрещена"),
    # Дополнительные паттерны для обнаружения обфускации
    (re.compile(r"\[\s*['\"]eval['\"]\s*\]"), "обфускация eval через массив"),
    (re.compile(r"window\s*\[\s*['\"]eval['\"]\s*\]"), "доступ к eval через window[]"),
    (re.compile(r"this\s*\[\s*['\"]eval['\"]\s*\]"), "доступ к eval через this[]"),
    (re.compile(r"global\s*\[\s*['\"]eval['\"]\s*\]"), "доступ к eval через global[]"),
    (re.compile(r"self\s*\[\s*['\"]eval['\"]\s*\]"), "доступ к eval через self[]"),
]

# =============================================================================
# RATE LIMITING ДЛЯ ВНЕШНИХ ЗАПРОСОВ
# =============================================================================


# =============================================================================
# КЭШИРОВАНИЕ HTTP ЗАПРОСОВ С TTL
# =============================================================================

# Время жизни кэша HTTP запросов в секундах (5 минут)
HTTP_CACHE_TTL_SECONDS = 300

# Размер кэша HTTP запросов (максимальное количество записей)
HTTP_CACHE_MAXSIZE = 1024


class _HTTPCacheEntry:
    """Запись кэша HTTP запроса с TTL."""

    def __init__(self, response: requests.Response, timestamp: float) -> None:
        self.response = response
        self.timestamp = timestamp

    def is_expired(self) -> bool:
        """Проверяет истёк ли срок действия кэша."""
        return (time.time() - self.timestamp) > HTTP_CACHE_TTL_SECONDS


class _HTTPCache:
    """Инкапсулированный кэш для HTTP запросов с потокобезопасностью."""

    def __init__(self, maxsize: int = HTTP_CACHE_MAXSIZE) -> None:
        self._cache: Dict[tuple, _HTTPCacheEntry] = {}
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов
        self._maxsize = maxsize

    def get(self, key: tuple) -> Optional[requests.Response]:
        """Получает закэшированный ответ.

        Args:
            key: Ключ кэша.

        Returns:
            Response объект или None если не найден или истёк.
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    return entry.response
                del self._cache[key]
            return None

    def set(self, key: tuple, response: requests.Response) -> None:
        """Сохраняет ответ в кэш.

        Args:
            key: Ключ кэша.
            response: Response объект для кэширования.
        """
        with self._lock:
            if len(self._cache) >= self._maxsize:
                keys_to_remove = list(self._cache.keys())[: self._maxsize // 10]
                for k in keys_to_remove:
                    del self._cache[k]

            self._cache[key] = _HTTPCacheEntry(response, time.time())

    def cleanup_expired(self) -> int:
        """Очищает истёкшие записи.

        Returns:
            Количество удалённых записей.
        """
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def size(self) -> int:
        """Возвращает текущий размер кэша."""
        with self._lock:
            return len(self._cache)


_http_cache_instance: Optional[_HTTPCache] = None
_http_cache_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов


def _get_http_cache() -> _HTTPCache:
    """Получает синглтон экземпляр HTTP кэша."""
    global _http_cache_instance
    with _http_cache_lock:
        if _http_cache_instance is None:
            _http_cache_instance = _HTTPCache()
        return _http_cache_instance


def _get_cache_key(method: str, url: str, verify_ssl: bool) -> tuple:
    """
    Создаёт ключ кэша для HTTP запроса.

    Args:
        method: HTTP метод.
        url: URL запроса.
        verify_ssl: Флаг проверки SSL.

    Returns:
        Кортеж для использования в качестве ключа кэша.
    """
    return (method, url, verify_ssl)


def _cleanup_expired_cache() -> int:
    """Очищает истёкшие записи из кэша.

    Returns:
        Количество удалённых записей.
    """
    cache = _get_http_cache()
    cleaned = cache.cleanup_expired()

    if cleaned > 0:
        app_logger.debug("Очищено %d истёкших записей из кэша HTTP", cleaned)

    return cleaned


@sleep_and_retry
@limits(calls=EXTERNAL_RATE_LIMIT_CALLS, period=EXTERNAL_RATE_LIMIT_PERIOD)
def _rate_limited_request(method: str, url: str, **kwargs) -> requests.Response:
    """Выполняет HTTP запрос с rate limiting для внешних запросов к 2GIS.

    - Применяет @sleep_and_retry декоратор ко всем внешним запросам
    - Ограничивает количество запросов до EXTERNAL_RATE_LIMIT_CALLS в секунду
    - Предотвращает блокировки со стороны 2GIS
    - Автоматически ожидает если лимит превышен

    Args:
        method: HTTP метод ('get', 'post', 'put', 'delete').
        url: URL для запроса.
        **kwargs: Дополнительные аргументы для requests.

    Returns:
        Response объект от requests.

    Raises:
        RequestException: При ошибке сетевого запроса.
    """
    # Получаем функцию запроса по имени метода
    request_func = getattr(requests, method.lower(), None)
    if request_func is None:
        raise ValueError(f"Неподдерживаемый HTTP метод: {method}")

    # Выполняем запрос с rate limiting
    return request_func(url, **kwargs)


def _safe_external_request(
    method: str,
    url: str,
    verify_ssl: bool = True,
    timeout: int = 60,
    use_cache: bool = True,
    **kwargs,
) -> requests.Response:
    """Безопасный внешний HTTP запрос с rate limiting, валидацией SSL и кэшированием.

    - Добавлено кэширование запросов по (method, url, verify_ssl)
    - TTL кэша: 5 минут (настраивается через HTTP_CACHE_TTL_SECONDS)
    - Размер кэша: до 1024 записей (настраивается через HTTP_CACHE_MAXSIZE)
    - Автоматическая очистка истёкших записей
    - Потокобезопасность через threading.Lock

    Args:
        method: HTTP метод ('get', 'post', 'put', 'delete').
        url: URL для запроса.
        verify_ssl: Проверять ли SSL сертификаты.
        timeout: Таймаут запроса в секундах.
        use_cache: Использовать ли кэширование (по умолчанию True).
        **kwargs: Дополнительные аргументы для requests.

    Returns:
        Response объект от requests.

    Пример:
        >>> response = _safe_external_request('get', 'https://api.2gis.ru/data')
        >>> response.status_code
        200
    """
    # Устанавливаем параметры по умолчанию
    kwargs.setdefault("verify", verify_ssl)
    kwargs.setdefault("timeout", timeout)

    cache_key = None

    if use_cache:
        cache_key = _get_cache_key(method, url, verify_ssl)
        cache = _get_http_cache()

        cached_response = cache.get(cache_key)
        if cached_response is not None:
            app_logger.debug("Кэшированный ответ для %s %s", method, url)
            return cached_response

        if cache.size() % 10 == 0:
            _cleanup_expired_cache()

    response = _rate_limited_request(method, url, **kwargs)

    if use_cache and cache_key is not None:
        cache = _get_http_cache()
        cache.set(cache_key, response)
        app_logger.debug("Запрос закэширован для %s %s", method, url)

    return response


# Кэш для проверки доступности портов

# вместо ручного словаря для более эффективного кэширования
_PORT_CACHE_TTL = 2.0  # Время жизни кэша порта в секундах (для обратной совместимости)


# Уменьшен размер кэша с 128 до 64 для экономии памяти
# Это обоснованно так как одновременно используется не более 10-20 портов
@lru_cache(maxsize=64)
def _check_port_cached(port: int) -> bool:
    """Проверяет доступность порта с кэшированием через lru_cache.

    - Размер кэша уменьшен с 128 до 64 (экономия памяти без потери производительности)
    - Использует lru_cache(maxsize=64) для автоматического кэширования
    - Кэширует результат проверки порта
    - Уменьшенный timeout для кэшированных проверок (0.5 сек)
    - Автоматическое управление размером кэша через LRU

    Args:
        port: Номер порта для проверки.

    Returns:
        True если порт доступен для подключения, False иначе.

    Пример:
        >>> _check_port_cached(9222)
        True
    """
    # Внутренняя функция без кэширования для фактической проверки
    return _check_port_available_internal(port, timeout=0.5, retries=1)


def _check_port_available_internal(port: int, timeout: float = 0.5, retries: int = 2) -> bool:
    """Внутренняя функция проверки порта без кэширования.

    - Сокет создаётся внутри цикла retries
    - Явное закрытие в блоке finally гарантирует освобождение ресурса
    - Предотвращает утечку файловых дескрипторов при множественных проверках
    - Добавлена опция SO_REUSEADDR для предотвращения проблем с повторным использованием портов

    Args:
        port: Номер порта для проверки.
        timeout: Таймаут проверки в секундах.
        retries: Количество повторных проверок.

    Returns:
        True если порт доступен, False иначе.
    """
    result = True  # По умолчанию порт свободен

    for attempt in range(retries):
        # Создаём сокет внутри цикла для гарантии закрытия на каждой итерации
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Опция SO_REUSEADDR позволяет повторно использовать сокет
            # сразу после закрытия, предотвращая ошибки "Address already in use"
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(timeout)
            connect_result = sock.connect_ex(("127.0.0.1", port))
            # Если порт занят (result == 0), возвращаем False немедленно
            if connect_result == 0:
                result = False
                break
            # Небольшая задержка между проверками
            if attempt < retries - 1:
                time.sleep(PORT_CHECK_RETRY_DELAY)
        except (socket.error, OSError, MemoryError) as e:
            app_logger.debug("Ошибка при проверке порта %d: %s", port, e)
            result = False
            break
        finally:
            # Гарантированное закрытие сокета на каждой итерации
            sock.close()

    return result


def _check_port_available(port: int, timeout: float = 0.5, retries: int = 2) -> bool:
    """Проверяет доступность порта для подключения.

    Оптимизация 20:
    - Использует lru_cache для кэширования результатов проверки
    - Кэширует результат проверки порта через _check_port_cached
    - Уменьшает timeout для кэшированных проверок до 0.5 сек
    - Автоматическое управление размером кэша (maxsize=16)

    Args:
        port: Номер порта для проверки.
        timeout: Таймаут проверки в секундах (не используется для кэшированных проверок).
        retries: Количество повторных проверок (не используется для кэшированных проверок).

    Returns:
        True если порт доступен для подключения, False иначе.
    """

    # Игнорируем timeout и retries для кэшированных проверок
    return _check_port_cached(port)


def _clear_port_cache() -> None:
    """Очищает кэш проверки портов.

    Оптимизация 20:
    - Использует lru_cache.cache_clear() для очистки
    - Полезно при изменении состояния портов
    """
    _check_port_cached.cache_clear()


# =============================================================================
# КОНФИГУРАЦИЯ ПРОВЕРОК БЕЗОПАСНОСТИ JS КОДА
# =============================================================================

# Опасные конкатенации для проверки на обход фильтров
_DANGEROUS_CONCAT_LIST = [
    "eval",
    "function",
    "settimeout",
    "setinterval",
    "fromcharcode",
    "newfunction",
    "document",
    "window",
    "prototype",
    "constructor",
    "__proto__",
]

# Максимальное соотношение escape-последовательностей для обфускации
_MAX_ESCAPE_RATIO = 0.3

# Максимальное соотношение специальных символов для обфускации
_MAX_SPECIAL_CHARS_RATIO = 0.7

# Минимальная длина кода для проверок обфускации
_MIN_CODE_LENGTH_FOR_OBFUSCATION_CHECK = 100


# =============================================================================
# ФУНКЦИИ ПРОВЕРКИ JS КОДА (ТАБЛИЧНО-ОРИЕНТИРОВАННЫЙ ПОДХОД)
# =============================================================================


def _check_js_length(code: str, max_length: int) -> tuple[bool, Optional[str]]:
    """Проверяет длину JavaScript кода.

    Args:
        code: JavaScript код для проверки.
        max_length: Максимальная допустимая длина.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если длина в норме, False иначе
        - error_message: Сообщение об ошибке или None
    """
    if len(code) > max_length:
        return (
            False,
            f"JavaScript код превышает максимальную длину ({len(code)} > {max_length} символов)",
        )
    return True, None


def _check_dangerous_encoding(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на опасные кодировки (Unicode, HTML entities, octal, hex).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если кодировки безопасны, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверяем на попытки обхода через unicode кодировку (\u0065\u0076\u0061\u006C = eval)
    if re.search(r"\\u00[0-9a-fA-F]{2}", code, re.IGNORECASE):
        return False, "Обнаружена попытка обхода через Unicode кодировку"

    # Проверяем на расширенную Unicode кодировку (\u{...})
    if re.search(r"\\u\{[0-9a-fA-F]+\}", code, re.IGNORECASE):
        return False, "Обнаружена попытка обхода через расширенную Unicode кодировку"

    # Проверяем на HTML entity кодировку
    if re.search(r"&#x[0-9a-fA-F]+;|&#\d+;", code, re.IGNORECASE):
        return False, "Обнаружена попытка обхода через HTML entity кодировку"

    # Проверяем на octal кодировку (\042, \050 и т.д.)
    if re.search(r"\\0[0-7]{2,3}", code):
        return False, "Обнаружена попытка обхода через Octal кодировку"

    # Проверяем на hex кодировку (\x41, \x42 и т.д.)
    if re.search(r"\\x[0-9a-fA-F]{2}", code, re.IGNORECASE):
        return False, "Обнаружена попытка обхода через Hex кодировку"

    return True, None


def _check_base64_functions(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на использование base64 функций (atob, btoa, Buffer.from).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если base64 функции отсутствуют, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # atob() - декодирование base64
    if re.search(r"\batob\s*\(\s*[^)]+\)", code, re.IGNORECASE):
        return False, "Функция atob() запрещена (может скрывать опасный код)"

    # btoa() - кодирование в base64
    if re.search(r"\bbtoa\s*\(\s*[^)]+\)", code, re.IGNORECASE):
        return False, "Функция btoa() запрещена (может скрывать опасный код)"

    # Проверка на Buffer.from с base64
    if re.search(r'Buffer\s*\.\s*from\s*\([^,]+,\s*["\']base64["\']', code, re.IGNORECASE):
        return False, "Buffer.from с base64 запрещён (может скрывать опасный код)"

    return True, None


def _check_string_conversion_functions(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на использование String.fromCharCode и аналогов.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если функции отсутствуют, False иначе
        - error_message: Сообщение об ошибке или None
    """
    if re.search(r"String\s*\.\s*fromCharCode\s*\(", code, re.IGNORECASE):
        return False, "String.fromCharCode() запрещён (может использоваться для обхода)"

    if re.search(r"String\s*\.\s*fromCodePoint\s*\(", code, re.IGNORECASE):
        return False, "String.fromCodePoint() запрещён (может использоваться для обхода)"

    if re.search(r"Character\s*\.\s*fromCharCode\s*\(", code, re.IGNORECASE):
        return False, "Character.fromCharCode() запрещён (может использоваться для обхода)"

    return True, None


def _check_concatenation_bypass(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на конкатенацию строк для обхода фильтров.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если конкатенация безопасна, False иначе
        - error_message: Сообщение об ошибке или None
    """
    if "+" not in code or ('"' not in code and "'" not in code):
        return True, None

    # Удаляем все не-буквенные символы для проверки
    code_letters_only = "".join(c for c in code.lower() if c.isalpha())

    for dangerous in _DANGEROUS_CONCAT_LIST:
        if dangerous in code_letters_only:
            return False, f"Обнаружена подозрительная конкатенация строк с {dangerous}"

    # Дополнительная проверка на конкатенацию с array join
    if re.search(r'\[\s*["\'][^"\']*["\']\s*\]\s*\.\s*join\s*\(', code, re.IGNORECASE):
        return False, "Обнаружена подозрительная конкатенация через array.join()"

    return True, None


def _check_obfuscation_patterns(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на паттерны обфускации.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если обфускация отсутствует, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверка на split('').reverse().join() - техника обфускации
    if re.search(
        r'split\s*\(\s*["\']["\']\s*\)\s*\.reverse\s*\(\)\s*\.join\s*\(', code, re.IGNORECASE
    ):
        return False, "Обнаружена обфускация через split().reverse().join()"

    # Проверка на обфускацию через множественные escape-последовательности
    escape_count = len(re.findall(r"\\[uUxX0-9]", code))
    if len(code) > _MIN_CODE_LENGTH_FOR_OBFUSCATION_CHECK:
        if escape_count / len(code) > _MAX_ESCAPE_RATIO:
            return (
                False,
                "Обнаружена подозрительная обфускация кода (множественные escape-последовательности)",
            )

    # Проверка на чрезмерное использование специальных символов
    special_chars = re.findall(r'[^a-zA-Z0-9\s_$.(){}[\],;:\'"`=+\-*/<>!&|]', code)
    if len(code) > _MIN_CODE_LENGTH_FOR_OBFUSCATION_CHECK:
        if len(special_chars) / len(code) > _MAX_SPECIAL_CHARS_RATIO:
            return (
                False,
                "Обнаружена подозрительная обфускация кода (чрезмерное использование специальных символов)",
            )

    # Проверка на подозрительные переменные с именами типа _0x1234
    if re.search(r"var\s+_[0-9a-fA-F]{4,}\s*=", code) or re.search(
        r"let\s+_[0-9a-fA-F]{4,}\s*=", code
    ):
        return False, "Обнаружена обфускация кода (подозрительные имена переменных)"

    return True, None


def _check_prototype_pollution(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на попытки prototype pollution.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если prototype pollution отсутствует, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверка на использование Object.prototype.constructor
    if re.search(r"Object\s*\.\s*prototype\s*\.\s*constructor", code, re.IGNORECASE):
        return False, "Object.prototype.constructor запрещён (попытка обхода)"

    # Проверка на использование constructor.constructor
    if re.search(r"constructor\s*\.\s*constructor", code, re.IGNORECASE):
        return False, "constructor.constructor запрещён (попытка обхода)"

    return True, None


def _check_dangerous_constructors(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на опасные конструкторы (new Function, eval).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если конструкторы безопасны, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверяем на eval()
    if re.search(r"\beval\s*\(", code, re.IGNORECASE):
        return False, "Функция eval() запрещена"

    # Проверяем на new Function()
    if re.search(r"new\s+Function\s*\(", code, re.IGNORECASE):
        return False, "Конструктор 'new Function()' запрещён"

    # Проверяем на присваивание eval переменной
    if re.search(r"\b\s*\w+\s*=\s*eval\s*;", code):
        return False, "Присваивание eval переменной запрещено (попытка обхода)"

    # Проверка на присваивание Function переменной
    if re.search(r"\b\s*\w+\s*=\s*Function\s*;", code):
        return False, "Присваивание Function переменной запрещено (попытка обхода)"

    return True, None


def _check_bracket_access(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на доступ через квадратные скобки (eval["..."]).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если доступ безопасен, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверка на доступ к eval через квадратные скобки
    if re.search(r'\beval\s*\[\s*["\'][a-zA-Z]+["\']\s*\]', code):
        return False, "Доступ к eval через квадратные скобки запрещён"

    # Проверка на доступ к Function через квадратные скобки
    if re.search(r'\bFunction\s*\[\s*["\'][a-zA-Z]+["\']\s*\]', code):
        return False, "Доступ к Function через квадратные скобки запрещён"

    # Проверка на window['eval'] и window['Function']
    if re.search(r"window\s*\[\s*['\"](?:eval|Function)['\"]\s*\]", code, re.IGNORECASE):
        return False, "Доступ window['eval'] или window['Function'] запрещён"

    return True, None


def _check_reflect_and_apply(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на использование Reflect.construct и Function.apply/call.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если функции отсутствуют, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверка на использование Reflect
    if re.search(r"Reflect\s*\.", code, re.IGNORECASE):
        return False, "Reflect запрещён (может использоваться для обхода)"

    # Проверка на использование apply/call
    if re.search(r"\.\s*(?:apply|call)\s*\(", code, re.IGNORECASE):
        return False, "apply/call запрещён (попытка обхода)"

    return True, None


def _check_array_and_regexp(code: str) -> tuple[bool, Optional[str]]:
    """Проверяет код на Array.from и RegExp с eval/Function.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если функции безопасны, False иначе
        - error_message: Сообщение об ошибке или None
    """
    # Проверка на Array.from с подозрительными аргументами
    if re.search(r'Array\s*\.\s*from\s*\(\s*["\'][^"\']*["\']', code, re.IGNORECASE):
        return False, "Array.from со строкой запрещён (может использоваться для обхода)"

    # Проверка на скомпилированный RegExp с eval/Function
    if re.search(r"new\s+RegExp\s*\([^)]*(?:eval|Function)[^)]*\)", code, re.IGNORECASE):
        return False, "RegExp с eval/Function запрещён (попытка обхода)"

    return True, None


# Таблица проверок безопасности JS кода
_JS_SECURITY_CHECKS: List[tuple[Callable[[str], tuple[bool, Optional[str]]], str]] = [
    (_check_dangerous_encoding, "Обнаружены опасные кодировки"),
    (_check_base64_functions, "Обнаружены base64 функции"),
    (_check_string_conversion_functions, "Обнаружены функции конвертации строк"),
    (_check_concatenation_bypass, "Обнаружен обход через конкатенацию"),
    (_check_obfuscation_patterns, "Обнаружены паттерны обфускации"),
    (_check_prototype_pollution, "Обнаружена попытка prototype pollution"),
    (_check_dangerous_constructors, "Обнаружены опасные конструкторы"),
    (_check_bracket_access, "Обнаружен доступ через квадратные скобки"),
    (_check_reflect_and_apply, "Обнаружены Reflect/apply/call"),
    (_check_array_and_regexp, "Обнаружены Array.from/RegExp"),
]


def _validate_js_code(code: str, max_length: int = MAX_JS_CODE_LENGTH) -> tuple[bool, str]:
    """Валидирует JavaScript код на безопасность.

    Использует таблично-ориентированный подход для проверок безопасности.
    Каждая проверка выделена в отдельную функцию для снижения сложности.

    Args:
        code: JavaScript код для валидации.
        max_length: Максимальная допустимая длина кода.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если код безопасен, False иначе
        - error_message: Сообщение об ошибке или пустая строка

    Примечание:
        Проверки включают:
        - Проверка на None и пустую строку
        - Проверка максимальной длины
        - Проверка типа данных
        - Таблица проверок безопасности (10 функций)
        - Проверка на опасные паттерны из _DANGEROUS_JS_PATTERNS
        - Нормализация Unicode (NFKC) для предотвращения обходов через Unicode эскейпы
    """
    if code is None:
        return False, "JavaScript код не может быть None"

    # Проверка типа
    if not isinstance(code, str):
        return (False, f"JavaScript код должен быть строкой, получен {type(code).__name__}")

    # ИСПРАВЛЕНИЕ 5: Нормализуем Unicode для предотвращения обходов через Unicode эскейпы
    import unicodedata

    # Сначала нормализуем Unicode (NFKC)
    normalized_code = unicodedata.normalize("NFKC", code)

    # Затем декодируем Unicode эскейпы (\u0065 -> e)
    try:
        # Декодируем \uXXXX и \xXX эскейпы
        normalized_code = (
            normalized_code.encode("utf-8").decode("unicode_escape").encode("utf-8").decode("utf-8")
        )
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Если декодирование не удалось, используем нормализованный код
        pass

    # Проверка на None после нормализации
    if normalized_code is None:
        return False, "JavaScript код не может быть None"

    # Проверка типа после нормализации
    if not isinstance(normalized_code, str):
        return (
            False,
            f"JavaScript код должен быть строкой, получен {type(normalized_code).__name__}",
        )

    # Проверка на пустую строку
    if not normalized_code.strip():
        return False, "JavaScript код не может быть пустым"

    # Проверка максимальной длины
    is_length_valid, length_error = _check_js_length(normalized_code, max_length)
    if not is_length_valid:
        return False, length_error or ""

    # Выполняем все проверки безопасности из таблицы
    for check_func, error_prefix in _JS_SECURITY_CHECKS:
        is_valid, error = check_func(normalized_code)
        if not is_valid:
            return False, error or error_prefix

    # Проверка на опасные паттерны с использованием скомпилированных regex
    for pattern, description in _DANGEROUS_JS_PATTERNS:
        if pattern.search(normalized_code):
            return False, f"Обнаружен опасный паттерн в JavaScript коде: {description}"

    # Проверяем на попытки использования setTimeout/setInterval с функцией
    if re.search(r"setTimeout\s*\(\s*function\s*\(", normalized_code, re.IGNORECASE):
        # Это допустимо, но логируем для аудита
        app_logger.debug("Обнаружен setTimeout с function - допустимо")

    # Проверка на self-executing функции с обфускацией
    if re.search(
        r"\(function\s*\([^)]*\)\s*\{[^}]*\}\s*\)\.call\s*\(", normalized_code, re.IGNORECASE
    ):
        app_logger.debug("Обнаружена self-executing функция с .call() - допустимо")

    return True, ""


def _sanitize_js_string(value: str) -> str:
    """Санитизирует строку для безопасного использования в JavaScript.

    Args:
        value: Исходная строка.

    Returns:
        Санитизированная строка с экранированными специальными символами.

    Примечание:
        Экранирует следующие символы:
        - Обратные кавычки (`)
        - Обратные слеши (\\)
        - Доллар ($) для предотвращения инъекций в template literals
    """
    if not isinstance(value, str):
        value = str(value)

    # Экранируем обратные слеши в первую очередь
    value = value.replace("\\", "\\\\")
    # Экранируем обратные кавычки
    value = value.replace("`", "\\`")
    # Экранируем доллар для предотвращения инъекций
    value = value.replace("$", "\\$")
    # Экранируем кавычки
    value = value.replace("'", "\\'")
    value = value.replace('"', '\\"')

    return value


if TYPE_CHECKING:
    from .options import ChromeOptions

    Request = Dict[str, Any]
    Response = Dict[str, Any]


def _validate_remote_port(port: Any) -> int:
    """Валидирует remote_port как integer в допустимом диапазоне.

    Args:
        port: Значение порта для валидации.

    Returns:
        Валидный номер порта.

    Raises:
        ValueError: Если порт некорректен.

    Примечание:
        - Проверяется тип (не bool, только int)
        - Проверяется диапазон 1024-65535
        - Исключаются зарезервированные порты
    """
    # Явная проверка на bool, так как bool является подклассом int
    if isinstance(port, bool):
        raise ValueError(f"remote_port не должен быть bool, получен {type(port).__name__}")

    if not isinstance(port, int):
        raise ValueError(f"remote_port должен быть integer, получен {type(port).__name__}")

    # Проверка диапазона портов
    if port < 1024:
        raise ValueError(
            f"remote_port должен быть >= 1024 (зарезервированные порты), получен {port}"
        )

    if port > 65535:
        raise ValueError(f"remote_port должен быть <= 65535, получен {port}")

    return port


# Применяем все пользовательские патчи
patch_all()


class ChromeRemote:
    """Обёртка для Chrome DevTools Protocol Interface.

    Args:
        chrome_options: Параметры ChromeOptions.
        response_patterns: Паттерны URL ответов для перехвата.

    Примечание:
        Использует rate limiting из constants.py для ограничения
        количества вызовов API.
    """

    def __init__(self, chrome_options: ChromeOptions, response_patterns: list[str]) -> None:
        self._chrome_options: ChromeOptions = chrome_options
        self._chrome_browser: Optional[ChromeBrowser] = None
        self._chrome_interface: Optional[pychrome.Browser] = None
        self._chrome_tab: Optional[pychrome.Tab] = None
        self._dev_url: Optional[str] = None
        self._response_patterns: list[str] = response_patterns
        self._response_queues: dict[str, queue.Queue[Response]] = {
            x: queue.Queue() for x in response_patterns
        }
        self._requests: dict[str, Request] = {}  # _requests[request_id] = <Request>
        self._requests_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

        # Счётчик общего размера всех JS скриптов для предотвращения DoS атак
        self._total_js_size: int = 0
        self._js_size_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов

    @wait_until_finished(timeout=300)
    def _connect_interface(self) -> bool:
        """Устанавливает соединение с Chrome и открывает новую вкладку.

        Returns:
            `True` при успехе, `False` при неудаче.

        Примечание:
            Функция детально логирует все ошибки подключения для отладки.
            Перед подключением проверяется доступность порта.
            Выполняется до 3 попыток подключения.
            При ошибке после создания вкладки выполняется очистка ресурсов.
        """
        max_attempts = 3
        attempt_delay = 2.0

        for attempt in range(max_attempts):
            try:
                # Извлекаем порт из dev_url для проверки
                # Проверяем, что dev_url не None перед использованием
                if self._dev_url is None:
                    app_logger.error("dev_url не установлен при подключении")
                    return False
                from urllib.parse import urlparse

                parsed_url = urlparse(self._dev_url)
                port = int(parsed_url.port)

                # Проверка доступности порта перед подключением
                if not _check_port_available(port, timeout=1.0):
                    app_logger.warning(
                        "Порт %d недоступен при подключении к DevTools (попытка %d/%d)",
                        port,
                        attempt + 1,
                        max_attempts,
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(attempt_delay)
                        continue
                    return False

                app_logger.debug(
                    "Подключение к Chrome DevTools Protocol по адресу: %s", self._dev_url
                )
                self._chrome_interface = pychrome.Browser(url=self._dev_url)

                app_logger.debug("Создание вкладки через _create_tab()...")
                self._chrome_tab = self._create_tab()

                app_logger.debug("Запуск вкладки с timeout=30...")
                # ВАЖНО: Запуск вкладки с таймаутом 30 секунд для предотвращения зависаний
                self._start_tab_with_timeout(self._chrome_tab, timeout=30)

                # Проверка работоспособности соединения после подключения
                if not self._verify_connection():
                    app_logger.warning("Проверка соединения не пройдена, повторная попытка")
                    self._cleanup_interface()
                    if attempt < max_attempts - 1:
                        time.sleep(attempt_delay)
                        continue
                    app_logger.error(
                        "Все попытки подключения исчерпаны (проверка соединения не пройдена)"
                    )
                    return False

                app_logger.info("Успешное подключение к Chrome DevTools Protocol")
                return True

            except (RequestException, WebSocketException, ChromeException) as e:
                # Обработка всех связанных с подключением ошибок
                app_logger.error(
                    "Ошибка подключения к Chrome DevTools Protocol (%s): %s", self._dev_url, e
                )
                # Очистка ресурсов при ошибке
                self._cleanup_interface()
                if attempt < max_attempts - 1:
                    time.sleep(attempt_delay)
                continue

        # Все попытки исчерпаны
        app_logger.error("Все %d попыток подключения исчерпаны", max_attempts)
        return False

    def _cleanup_interface(self) -> None:
        """Очищает ресурсы Chrome interface при ошибке.

        Примечание:
            Метод безопасно закрывает вкладку и интерфейс,
            игнорируя любые ошибки для предотвращения утечек ресурсов.
        """
        try:
            if self._chrome_tab is not None:
                try:
                    if self._chrome_tab.status == pychrome.Tab.status_started:
                        self._chrome_tab.stop()
                    # Закрываем вкладку через API
                    if self._dev_url:
                        # ИСПОЛЬЗУЕМ rate-limited запрос для предотвращения блокировок
                        _safe_external_request(
                            "put",
                            "%s/json/close/%s" % (self._dev_url, self._chrome_tab.id),
                            timeout=5,
                            verify=True,  # Явная валидация SSL сертификатов
                        )
                except Exception as e:
                    app_logger.debug("Ошибка при очистке вкладки: %s", e)
                finally:
                    self._chrome_tab = None

            if self._chrome_interface is not None:
                try:
                    self._chrome_interface.close()
                except Exception as e:
                    app_logger.debug("Ошибка при закрытии интерфейса: %s", e)
                finally:
                    self._chrome_interface = None

        except Exception as e:
            app_logger.warning("Непредвиденная ошибка при очистке ресурсов: %s", e)

    def _verify_connection(self) -> bool:
        """Проверяет работоспособность соединения с Chrome.

        Returns:
            True если соединение работоспособно, False иначе.

        Примечание:
            Метод выполняет простой JavaScript запрос для проверки
            работоспособности соединения с вкладкой.
        """
        try:
            # Проверяем, что вкладка существует
            if self._chrome_tab is None:
                app_logger.error("Chrome tab не инициализирован при проверке соединения")
                return False

            # Выполняем простой JavaScript запрос
            result = self._chrome_tab.Runtime.evaluate(
                expression="1+1",
                returnByValue=True,
                timeout=5000,  # 5 секунд таймаут
            )

            # Проверяем результат
            if result and result.get("result", {}).get("value") == 2:
                app_logger.debug("Проверка соединения пройдена")
                return True
            else:
                app_logger.warning("Проверка соединения вернула неожиданный результат: %s", result)
                return False

        except Exception as e:
            app_logger.warning("Ошибка при проверке соединения: %s", e)
            return False

    def start(self) -> None:
        """Открывает браузер, создаёт новую вкладку, настраивает удалённый интерфейс.

        Оптимизация:
        - Адаптивная задержка вместо фиксированной
        - Уменьшенное количество проверок порта

        Raises:
            ChromeException: Если не удалось подключиться к Chrome.
        """
        try:
            # Открываем браузер
            self._chrome_browser = ChromeBrowser(self._chrome_options)

            # Валидируем порт перед использованием
            remote_port = _validate_remote_port(self._chrome_browser.remote_port)
            self._dev_url = f"http://127.0.0.1:{remote_port}"

            # Оптимизация: адаптивная задержка для запуска Chrome
            # Начинаем с меньшей задержки и увеличиваем при необходимости
            startup_delay = CHROME_STARTUP_DELAY
            max_startup_attempts = 3

            for attempt in range(max_startup_attempts):
                app_logger.debug(
                    "Ожидание запуска Chrome (%.1f сек, попытка %d)...", startup_delay, attempt + 1
                )
                time.sleep(startup_delay)

                # Проверяем доступность порта
                if _check_port_available(remote_port, timeout=1.0, retries=1):
                    app_logger.debug("Порт %d доступен для подключения", remote_port)
                    break

                # Увеличиваем задержку для следующей попытки
                startup_delay = min(startup_delay * 1.5, 3.0)
            else:
                raise ChromeException(
                    f"Порт {remote_port} недоступен после {max_startup_attempts} попыток. "
                    "Возможно, Chrome не запустился."
                )

            # Подключаем браузер к CDP с проверкой результата
            if not self._connect_interface():
                raise ChromeException("Не удалось подключиться к Chrome DevTools Protocol")

            self._setup_tab()
            self._init_tab_monitor()

        except Exception as e:
            # При любой ошибке закрываем браузер для предотвращения утечки ресурсов
            app_logger.error("Ошибка запуска Chrome: %s", e)
            if self._chrome_browser:
                app_logger.warning("Закрытие браузера из-за ошибки при запуске")
                self._chrome_browser.close()
            raise  # Пробрасываем исключение дальше

    def _start_tab_with_timeout(self, tab: pychrome.Tab, timeout: int = 30) -> None:
        """Запускает вкладку с таймаутом.

        Использует threading для установки таймаута на операцию start().
        Это предотвращает зависание при проблемах с WebSocket соединением.

        Args:
            tab: pychrome.Tab для запуска.
            timeout: Таймаут в секундах (по умолчанию 30).

        Raises:
            TimeoutError: Если запуск превысил таймаут.
        """
        import threading

        # ИСПРАВЛЕНИЕ 4: Явная типизация словаря result
        result: Dict[str, Optional[Exception]] = {"error": None}

        def start_target() -> None:
            try:
                tab.start()
            except Exception as e:
                result["error"] = e

        thread = threading.Thread(target=start_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Поток всё ещё активен - таймаут
            app_logger.error("Таймаут при запуске вкладки (%d секунд)", timeout)
            raise TimeoutError(f"Запуск вкладки превысил таймаут {timeout} секунд")

        if result["error"]:
            app_logger.error("Ошибка при запуске вкладки: %s", result["error"])
            raise result["error"]

        app_logger.debug("Вкладка успешно запущена")

    def _create_tab(self) -> pychrome.Tab:
        """Создаёт Chrome-вкладку с повторными попытками.

        Returns:
            Новый экземпляр pychrome.Tab.

        Raises:
            ChromeException: Если не удалось создать вкладку после всех попыток.

        Примечание:
            - Выполняется до 10 попыток создания вкладки
            - Задержка между попытками: 1.5 секунды
            - Увеличенный timeout для каждой попытки: 60 секунд
            - Детальное логирование для отладки
        """
        max_attempts = 10
        delay_seconds = 1.5

        for attempt in range(max_attempts):
            try:
                app_logger.debug("Попытка %d/%d: создание вкладки...", attempt + 1, max_attempts)
                # requests.put не принимает параметр json=True, используем данные запроса
                # ИСПОЛЬЗУЕМ rate-limited запрос для предотвращения блокировок
                resp = _safe_external_request(
                    "put",
                    "%s/json/new" % (self._dev_url),
                    json={},  # Пустой JSON для создания вкладки
                    timeout=60,  # Увеличенный timeout для стабильности
                    verify=True,  # Явная валидация SSL сертификатов
                )
                resp.raise_for_status()
                app_logger.debug("Вкладка успешно создана")
                return pychrome.Tab(**resp.json())

            except (RequestException, ValueError, KeyError) as e:
                if attempt < max_attempts - 1:
                    app_logger.warning(
                        "Не удалось создать вкладку (попытка %d): %s. Повторная попытка через %.1f сек...",
                        attempt + 1,
                        e,
                        delay_seconds,
                    )
                    time.sleep(delay_seconds)
                else:
                    raise ChromeException(
                        f"Не удалось создать вкладку после {max_attempts} попыток: {e}"
                    ) from e

        raise ChromeException("Не удалось создать вкладку")

    def _close_tab(self, tab: pychrome.Tab) -> None:
        """Закрывает Chrome-вкладку."""
        if tab.status == pychrome.Tab.status_started:
            tab.stop()
        # ИСПОЛЬЗУЕМ rate-limited запрос для предотвращения блокировок
        _safe_external_request(
            "put",
            "%s/json/close/%s" % (self._dev_url, tab.id),
            verify=True,  # Явная валидация SSL сертификатов
        )

    def _setup_tab(self) -> None:
        """Скрывает следы webdriver, включает перехват запросов/ответов, исправляет UA.

        Примечание:
            Метод устанавливает пользовательский агент, скрывает признаки webdriver
            и настраивает перехват сетевых запросов для последующей обработки.

        Raises:
            RuntimeError: Если вкладка не инициализирована (_chrome_tab is None).
        """
        # Строгая проверка, что вкладка существует
        if self._chrome_tab is None:
            error_msg = "Chrome tab не инициализирован в _setup_tab. Вкладка не была создана."
            app_logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Исправляем user agent для headless браузера
        original_useragent = self.execute_script("navigator.userAgent")

        # Проверяем успешность получения user agent
        if original_useragent:
            fixed_useragent = original_useragent.replace("Headless", "")
        else:
            # Запасной вариант: стандартный user agent Chrome
            fixed_useragent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            app_logger.warning("Не удалось получить user agent, используется запасной вариант")

        self._chrome_tab.Network.setUserAgentOverride(userAgent=fixed_useragent)

        # Скрываем следы webdriver
        self.add_start_script(r"""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        def responseReceived(**kwargs) -> None:
            """Собирает ответы."""
            # Извлекаем response до изменения kwargs
            response = kwargs["response"]
            request_id = kwargs["requestId"]
            resource_type = kwargs.get("type")

            # Сохраняем метаданные ответа
            response["meta"] = {k: v for k, v in kwargs.items() if k != "response"}

            # Пропускаем preflight запросы
            if resource_type == "Preflight":
                return

            # Добавляем ответ атомарно под блокировкой
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response

                    # Помещаем ответ в очередь атомарно, чтобы избежать гонки
                    for pattern in self._response_patterns:
                        if re.match(pattern, response["url"]):
                            self._response_queues[pattern].put(response)

        def loadingFailed(**kwargs) -> None:
            """Обрабатывает неудачные загрузки запросов."""
            error_text = kwargs.get("errorText")
            blocked_reason = kwargs.get("blockedReason")
            status_text = ""

            if error_text:
                status_text = f"error: {error_text}"
            if blocked_reason:
                if status_text:
                    status_text += ", "
                status_text += f"blocked_reason: {blocked_reason}"

            request_id = kwargs.get("requestId")
            response = {"status": -1, "statusText": status_text}

            # Унифицированный паттерн блокировки: всё под одним локом
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response
                    request_url = request["url"]

                    # Если ответ нужен, помещаем его в очередь атомарно
                    if request_url:
                        for pattern in self._response_patterns:
                            if re.match(pattern, request_url):
                                self._response_queues[pattern].put(response)

        def requestWillBeSent(**kwargs) -> None:
            request = kwargs.pop("request")
            request["meta"] = kwargs
            request_id = kwargs["requestId"]
            resource_type = kwargs.get("type")

            # Пропускаем preflight запросы
            if resource_type == "Preflight":
                return

            # Добавляем запрос
            with self._requests_lock:
                self._requests[request_id] = request

        self._chrome_tab.Network.responseReceived = responseReceived
        self._chrome_tab.Network.loadingFailed = loadingFailed
        self._chrome_tab.Network.requestWillBeSent = requestWillBeSent

        self._chrome_tab.Network.enable()
        self._chrome_tab.DOM.enable()
        self._chrome_tab.Page.enable()
        self._chrome_tab.Runtime.enable()
        self._chrome_tab.Log.enable()

    def _init_tab_monitor(self) -> None:
        """Мониторит здоровье вкладки Chrome.

        Оптимизация:
        - Увеличенный интервал опроса для снижения нагрузки
        - Пропуск проверок при активном использовании вкладки
        """
        # Проверяем, что вкладка существует
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в _init_tab_monitor")
            return
        if self._dev_url is None:
            app_logger.error("dev_url не установлен в _init_tab_monitor")
            return

        # Используем threading.Event для потокобезопасного флага
        tab_detached = threading.Event()

        # Оптимизация: увеличенный интервал мониторинга
        MONITOR_INTERVAL = 2.0  # Увеличено с 0.5 до 2.0 секунд

        def monitor_tab() -> None:
            """Мониторинг вкладки с оптимизированным интервалом."""
            if self._chrome_tab is None:
                return

            last_check_time: float = 0.0

            while not self._chrome_tab._stopped.is_set():
                current_time = time.time()

                # Проверяем вкладку только если прошло достаточно времени
                if current_time - last_check_time >= MONITOR_INTERVAL:
                    try:
                        # ИСПОЛЬЗУЕМ rate-limited запрос для предотвращения блокировок
                        ret = _safe_external_request(
                            "get",
                            "%s/json" % self._dev_url,
                            timeout=3,
                            verify=True,  # Явная валидация SSL сертификатов
                        )
                        tab_found = any(x["id"] == self._chrome_tab.id for x in ret.json())
                        if not tab_found:
                            tab_detached.set()
                            self._chrome_tab._stopped.set()
                        last_check_time = current_time
                    except (ConnectionError, RequestException, TimeoutError):
                        break

                # Ждём следующего интервала
                self._chrome_tab._stopped.wait(MONITOR_INTERVAL)

        self._ping_thread = threading.Thread(target=monitor_tab, daemon=True)
        self._ping_thread.start()

        # Устанавливаем обёртку для отправки с повторным выбросом исключения
        if self._chrome_tab is None:
            return
        original_send = self._chrome_tab._send

        def wrapped_send(*args, **kwargs) -> Any:
            try:
                return original_send(*args, **kwargs)
            except pychrome.UserAbortException as e:
                if tab_detached.is_set():
                    app_logger.debug("Вкладка была остановлена: %s", e)
                    raise pychrome.RuntimeException("Вкладка была остановлена") from e
                else:
                    app_logger.debug("UserAbortException при отправке: %s", e)
                    raise

        self._chrome_tab._send = wrapped_send

    def navigate(self, url: str, referer: str = "", timeout: int = 300) -> None:
        """Переходит по URL.

        Args:
            url: URL для навигации.
            referer: Установить заголовок referer.
            timeout: Таймаут ожидания в секундах (по умолчанию 5 минут).

        Raises:
            ChromeException: При ошибке навигации.
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в navigate")
            return
        try:
            ret = self._chrome_tab.Page.navigate(url=url, _timeout=timeout, referrer=referer)
            error_message = ret.get("errorText", None)
            if error_message:
                raise ChromeException(error_message)
        except Exception as e:
            app_logger.error("Ошибка навигации по URL %s: %s", url, e)
            raise

    @wait_until_finished(timeout=300, throw_exception=False)
    def wait_response(self, response_pattern: str) -> Optional[Response]:
        """Ждёт указанный ответ с предопределённым паттерном.

        Args:
            response_pattern: Паттерн URL ответа.

        Returns:
            Ответ или None в случае таймаута (5 минут) или ошибки.
        """
        try:
            if self._chrome_tab is None:
                app_logger.warning("Chrome tab не инициализирован")
                return None

            if self._chrome_tab._stopped.is_set():
                app_logger.warning("Вкладка Chrome была остановлена")
                return None

            return self._response_queues[response_pattern].get(block=False)
        except queue.Empty:
            return None
        except KeyError:
            app_logger.warning("Неизвестный паттерн ответа: %s", response_pattern)
            return None
        except Exception as e:
            app_logger.error("Ошибка при ожидании ответа: %s", e)
            return None

    def clear_requests(self) -> None:
        """Очищает все собранные запросы и очереди ответов."""
        with self._requests_lock:
            self._requests = {}
        # Очищаем очереди ответов для предотвращения утечки памяти
        for pattern_queue in self._response_queues.values():
            while not pattern_queue.empty():
                try:
                    pattern_queue.get_nowait()
                except queue.Empty:
                    break

    @wait_until_finished(timeout=60, throw_exception=False)
    def get_response_body(self, response: Response) -> str:
        """Получает тело ответа.

        Args:
            response: Ответ.

        Returns:
            Тело ответа или пустую строку при ошибке.

        Примечание:
            Функция гарантирует очистку временных данных для предотвращения утечки памяти.
        """
        # Проверяем, что вкладка существует
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_response_body")
            return ""

        response_data: Optional[Dict[str, Any]] = None
        response_body: str = ""

        try:
            # Проверяем наличие необходимых полей
            if "meta" not in response:
                app_logger.warning("Отсутствует поле meta в response")
                return ""

            if "requestId" not in response["meta"]:
                app_logger.warning("Отсутствует поле requestId в response.meta")
                return ""

            request_id = response["meta"]["requestId"]

            # Получаем тело ответа
            response_data = self._chrome_tab.call_method(
                "Network.getResponseBody", requestId=request_id
            )

            if not response_data:
                app_logger.debug("Тело ответа пустое для requestId: %s", request_id)
                return ""

            # Декодируем base64 если необходимо
            if response_data.get("base64Encoded"):
                try:
                    encoded_body = response_data.get("body", "")
                    if encoded_body:
                        decoded_bytes = base64.b64decode(encoded_body)
                        response_body = decoded_bytes.decode("utf-8")
                    else:
                        response_body = ""
                except (UnicodeDecodeError, ValueError) as decode_error:
                    app_logger.warning(
                        "Ошибка декодирования тела ответа (requestId: %s): %s",
                        request_id,
                        decode_error,
                    )
                    response_body = ""
            else:
                response_body = response_data.get("body", "")

            # Проверка размера ответа для предотвращения DoS атак
            # Проверяем размер полученного тела ответа
            if len(response_body) > MAX_RESPONSE_SIZE:
                app_logger.warning(
                    "Размер ответа превышает лимит (%d > %d байт) для requestId: %s. "
                    "Ответ отклонён.",
                    len(response_body),
                    MAX_RESPONSE_SIZE,
                    request_id,
                )
                raise ValueError(
                    f"Размер ответа превышает максимальный лимит "
                    f"({len(response_body)} > {MAX_RESPONSE_SIZE} байт). "
                    f"Это может быть DoS атака."
                )

            # Сохраняем тело в response для удобства
            response["body"] = response_body
            return response_body

        except pychrome.CallMethodException as e:
            # Ошибка вызова метода CDP
            app_logger.debug("CallMethodException при получении тела ответа: %s", e)
            return ""

        except KeyError as e:
            # Отсутствует необходимое поле
            app_logger.warning("Отсутствует поле в response при получении тела ответа: %s", e)
            return ""

        except Exception as e:
            # Любая другая ошибка
            app_logger.warning("Непредвиденная ошибка при получении тела ответа: %s", e)
            return ""

        finally:
            # Гарантированная очистка временных данных для предотвращения утечки памяти
            if response_data is not None:
                # Явно удаляем большие данные из памяти
                response_data.pop("body", None)
                # Обнуляем ссылку для помощи сборщику мусора
                response_data = None

    @wait_until_finished(timeout=None, throw_exception=False)
    def get_responses(self) -> List[Response]:
        """Получает собранные ответы.

        Returns:
            Список всех ответов с полем 'response'.
        """
        with self._requests_lock:
            return [x["response"] for x in self._requests.values() if "response" in x]

    def get_requests(self) -> List[Request]:
        """Получает записанные запросы.

        Returns:
            Список всех записанных запросов.
        """
        with self._requests_lock:
            return [*self._requests.values()]

    def get_document(self, full: bool = True) -> DOMNode:
        """Получает DOM-дерево документа.

        Args:
            full: Флаг, возвращать полное DOM или только корень.

        Returns:
            Корневой DOM-узел.
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_document")
            # Возвращаем пустой DOMNode как fallback, используя алиасы полей pydantic
            return DOMNode(
                nodeId=0, backendNodeId=0, nodeType=0, nodeName="", localName="", nodeValue=""
            )
        tree = self._chrome_tab.DOM.getDocument(depth=-1 if full else 1)
        return DOMNode(**tree["root"])

    def add_start_script(self, source: str) -> None:
        """Добавляет скрипт, выполняющийся на каждой новой странице.

        Args:
            source: Текст скрипта.

        Raises:
            ValueError: Если скрипт не прошёл валидацию безопасности.
            RuntimeError: Если превышен максимальный общий размер JS скриптов.

        Примечание безопасности:
            Перед выполнением скрипт проходит проверку на:
            - Тип данных (должен быть строкой)
            - Максимальную длину
            - Наличие опасных паттернов (eval, Function, document.write)
            - Общий размер всех добавленных скриптов (защита от DoS)

        - Добавлена проверка общего размера всех JS скриптов
        - Превышение MAX_TOTAL_JS_SIZE вызывает RuntimeError
        - Защита от DoS атак через множество маленьких скриптов
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в add_start_script")
            return

        # Валидация скрипта на безопасность
        is_valid, error_msg = _validate_js_code(source)
        if not is_valid:
            app_logger.error("Валидация скрипта не пройдена: %s", error_msg)
            raise ValueError(f"Небезопасный JavaScript код: {error_msg}")

        # Проверка общего размера всех JS скриптов
        js_code_size = len(source.encode("utf-8"))
        with self._js_size_lock:
            if self._total_js_size + js_code_size > MAX_TOTAL_JS_SIZE:
                raise RuntimeError(
                    f"Превышен максимальный общий размер JS скриптов "
                    f"({self._total_js_size + js_code_size} > {MAX_TOTAL_JS_SIZE} байт). "
                    f"Это может быть DoS атака."
                )
            self._total_js_size += js_code_size

        self._chrome_tab.Page.addScriptToEvaluateOnNewDocument(source=source)

    def add_blocked_requests(self, urls: List[str]) -> bool:
        """Блокирует нежелательные запросы.

        Args:
            urls: Шаблоны URL для блокировки. Поддерживаются подстановочные знаки ('*').

        Returns:
            `True` при успехе, `False` при неудаче.
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в add_blocked_requests")
            return False
        try:
            self._chrome_tab.Network.setBlockedURLs(urls=urls)
            return True
        except pychrome.CallMethodException:
            # Похоже, старая версия браузера, пропускаем
            return False

    def execute_script(self, expression: str, timeout: int = 30) -> Any:
        """Выполняет скрипт.

        Args:
            expression: Текст выражения.
            timeout: Таймаут выполнения в секундах (по умолчанию 30).

        Returns:
            Значение результата или None при ошибке.

        Raises:
            ValueError: Если выражение не прошло валидацию безопасности.
            TimeoutError: Если выполнение превысило таймаут.

        Примечание безопасности:
            Перед выполнением выражение проходит проверку на:
            - Тип данных (должен быть строкой)
            - Максимальную длину
            - Наличие опасных паттернов (eval, Function, document.write)

        - Добавлен rate limiting через декоратор @sleep_and_retry и @limits
        - Ограничение: 10 вызовов в секунду для предотвращения перегрузки CDP
        - Добавлен параметр timeout для предотвращения зависаний
        - Используется ThreadPoolExecutor для выполнения с таймаутом
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в execute_script")
            return None

        # ВАЖНО: Логирование всех вызовов execute_script для аудита безопасности
        app_logger.debug(
            "Выполнение JavaScript: %s",
            expression[:100] + "..." if len(expression) > 100 else expression,
        )

        # Валидация выражения на безопасность
        is_valid, error_msg = _validate_js_code(expression)
        if not is_valid:
            app_logger.error("Валидация выражения не пройдена: %s", error_msg)
            raise ValueError(f"Небезопасный JavaScript код: {error_msg}")

        return self._execute_script_internal(expression, timeout)

    @sleep_and_retry
    @limits(calls=EXTERNAL_RATE_LIMIT_CALLS, period=EXTERNAL_RATE_LIMIT_PERIOD)
    def _execute_script_internal(self, expression: str, timeout: int = 30) -> Any:
        """Внутренний метод выполнения скрипта с rate limiting.

        - Декораторы @sleep_and_retry и @limits обеспечивают rate limiting
        - Ограничение: 5 вызовов в секунду для внешних запросов к 2GIS
        - Автоматическая пауза при превышении лимита вызовов
        - Защита от перегрузки Chrome DevTools Protocol и внешних сервисов
        - Предотвращает блокировки со стороны 2GIS

        Args:
            expression: JavaScript выражение для выполнения.
            timeout: Таймаут выполнения в секундах.

        Returns:
            Результат выполнения или None при ошибке.
        """
        result = {"value": None, "error": None}

        def execute_target() -> None:
            """Внутренняя функция для выполнения скрипта."""
            try:
                eval_result = self._chrome_tab.Runtime.evaluate(
                    expression=expression, returnByValue=True
                )
                result["value"] = eval_result["result"].get("value", None)
            except Exception as e:
                result["error"] = e
                app_logger.warning("Ошибка при выполнении скрипта: %s", e)

        try:
            # Используем ThreadPoolExecutor для выполнения с таймаутом
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(execute_target)
                try:
                    future.result(timeout=timeout)
                except TimeoutError as timeout_err:
                    app_logger.error("Превышено время выполнения JavaScript (%d секунд)", timeout)
                    raise TimeoutError(
                        f"Выполнение скрипта превысило таймаут {timeout} секунд"
                    ) from timeout_err

            # Проверяем, не произошла ли ошибка при выполнении
            if result["error"]:
                return None

            return result["value"]

        except TimeoutError:
            # Пробрасываем TimeoutError дальше
            raise
        except Exception as e:
            app_logger.warning("Непредвиденная ошибка при выполнении скрипта: %s", e)
            return None

    def perform_click(self, dom_node: DOMNode, timeout: Optional[int] = None) -> None:
        """Выполняет клик мыши на DOM-узле.

        Args:
            dom_node: Элемент DOMNode.
            timeout: Таймаут операции в секундах (опционально).
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в perform_click")
            return
        try:
            resolved_node = self._chrome_tab.DOM.resolveNode(
                backendNodeId=dom_node.backend_id, _timeout=timeout
            )
            object_id = resolved_node["object"]["objectId"]
            self._chrome_tab.Runtime.callFunctionOn(
                objectId=object_id,
                functionDeclaration="""
                    (function() {
                        this.scrollIntoView({ block: "center", behavior: "instant" });
                        this.click();
                    })
                """,
            )
        except Exception as e:
            app_logger.error("Ошибка при выполнении клика: %s", e)

    def wait(self, timeout: Optional[float] = None) -> None:
        """Ожидает указанное время.

        Args:
            timeout: Время ожидания в секундах.
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в wait")
            return
        self._chrome_tab.wait(timeout)

    def stop(self) -> None:
        """Закрывает браузер, отключает интерфейс.

        Примечание:
            Функция гарантирует очистку всех ресурсов даже при ошибках.
            Включает очистку кэша портов для предотвращения утечек памяти.
            Использует блокировку finally для гарантии очистки ресурсов.
        """
        app_logger.info("Начало остановки ChromeRemote...")

        try:
            # Закрываем вкладку
            if self._chrome_tab is not None:
                try:
                    app_logger.debug("Закрытие Chrome вкладки...")
                    self._close_tab(self._chrome_tab)
                    app_logger.info("Chrome вкладка успешно закрыта")
                except (pychrome.RuntimeException, RequestException) as close_tab_error:
                    app_logger.error(
                        "Ошибка при закрытии вкладки: %s (тип: %s)",
                        close_tab_error,
                        type(close_tab_error).__name__,
                    )
                finally:
                    # Гарантированно обнуляем _chrome_tab
                    self._chrome_tab = None
                    app_logger.debug("_chrome_tab обнулён")

            # Закрываем браузер
            if self._chrome_browser is not None:
                try:
                    app_logger.debug("Закрытие Chrome браузера...")
                    self._chrome_browser.close()
                    app_logger.info("Chrome браузер успешно закрыт")
                except Exception as close_browser_error:
                    app_logger.error(
                        "Ошибка при закрытии браузера: %s (тип: %s)",
                        close_browser_error,
                        type(close_browser_error).__name__,
                    )
                finally:
                    # Гарантированно обнуляем _chrome_browser
                    self._chrome_browser = None
                    app_logger.debug("_chrome_browser обнулён")

            # Отключаем интерфейс
            if self._chrome_interface is not None:
                try:
                    app_logger.debug("Отключение Chrome интерфейса...")
                    self._chrome_interface.close()
                    app_logger.info("Chrome интерфейс успешно отключён")
                except Exception as close_interface_error:
                    app_logger.error(
                        "Ошибка при отключении интерфейса: %s (тип: %s)",
                        close_interface_error,
                        type(close_interface_error).__name__,
                    )
                finally:
                    # Гарантированно обнуляем _chrome_interface
                    self._chrome_interface = None
                    app_logger.debug("_chrome_interface обнулён")

        except Exception as outer_error:
            app_logger.critical(
                "Критическая ошибка при остановке ChromeRemote: %s (тип: %s)",
                outer_error,
                type(outer_error).__name__,
                exc_info=True,
            )
        finally:
            # Блок finally для гарантии очистки ресурсов даже при критических ошибках
            app_logger.debug("Выполнение финальной очистки ресурсов...")

            # Гарантированно обнуляем все ресурсы
            self._chrome_tab = None
            self._chrome_browser = None
            self._chrome_interface = None

            # Очищаем запросы и очереди
            try:
                self.clear_requests()
                app_logger.debug("Очередь запросов очищена")
            except Exception as clear_requests_error:
                app_logger.warning("Ошибка при очистке очереди запросов: %s", clear_requests_error)

            # Обнуляем очереди ответов
            self._response_queues = {}
            app_logger.debug("Очереди ответов обнулены")

            # Очищаем кэш портов
            try:
                _clear_port_cache()
                app_logger.debug("Кэш портов очищен")
            except Exception as clear_cache_error:
                app_logger.warning("Ошибка при очистке кэша портов: %s", clear_cache_error)

            app_logger.info("Завершение остановки ChromeRemote - все ресурсы очищены")

    def __enter__(self) -> ChromeRemote:
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.stop()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return f"{classname}(options={self._chrome_options!r}, response_patterns={self._response_patterns!r})"
