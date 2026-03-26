"""Модуль rate limiting для HTTP запросов.

Предоставляет функции для ограничения количества запросов к внешним сервисам:
- _rate_limited_request - HTTP запрос с rate limiting
- _safe_external_request - Безопасный внешний запрос с кэшированием
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
