"""Модуль rate limiting для HTTP запросов.

Предоставляет функции для ограничения количества запросов к внешним сервисам:
- _rate_limited_request - HTTP запрос с rate limiting
- _safe_external_request - Безопасный внешний запрос с кэшированием
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

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

from parser_2gis.logger.logger import logger as app_logger

from .constants import EXTERNAL_RATE_LIMIT_CALLS, EXTERNAL_RATE_LIMIT_PERIOD

if TYPE_CHECKING:
    import requests


# =============================================================================
# RATE LIMITING ДЛЯ ВНЕШНИХ ЗАПРОСОВ
# =============================================================================


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
    # Импортируем HTTPCache для кэширования
    from .http_cache import _cleanup_expired_cache, _get_cache_key, _get_http_cache

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
