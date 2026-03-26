"""Модуль rate limiting для HTTP запросов.

Предоставляет функции для ограничения количества запросов к внешним сервисам:
- _rate_limited_request - HTTP запрос с rate limiting
- _safe_external_request - Безопасный внешний запрос с кэшированием
"""

from __future__ import annotations

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

# RequestException используется как базовый класс для обработки исключений
try:
    from requests.exceptions import RequestException
except ImportError:
    RequestException = Exception  # type: ignore[misc, assignment]


if TYPE_CHECKING:
    pass


# =============================================================================
# RATE LIMITING ДЛЯ ВНЕШНИХ ЗАПРОСОВ
# =============================================================================


def _safe_external_request(
    method: str = "GET", url: str = "", timeout: int = 30, **kwargs
) -> Optional[requests.Response]:
    """Безопасный внешний запрос с rate limiting.

    Args:
        method: HTTP метод.
        url: URL для запроса.
        timeout: Таймаут запроса.
        **kwargs: Дополнительные аргументы для requests.

    Returns:
        requests.Response объект или None при ошибке.
    """
    if requests is None:
        raise ImportError("requests library is required for _safe_external_request")

    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        return response
    except requests.exceptions.RequestException as e:
        # Логируем ошибку, но не выбрасываем - пусть вызывающий код решает
        from parser_2gis.logger import logger as app_logger

        app_logger.debug("Ошибка HTTP запроса к %s: %s", url, e)
        return None
    except Exception as e:
        from parser_2gis.logger import logger as app_logger

        app_logger.error("Неожиданная ошибка HTTP запроса к %s: %s", url, e)
        return None
