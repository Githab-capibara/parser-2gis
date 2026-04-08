"""Модуль rate limiting для HTTP запросов.

Предоставляет функции для ограничения количества запросов к внешним сервисам:
- _rate_limited_request - HTTP запрос с rate limiting
- _safe_external_request - Безопасный внешний запрос с кэшированием

HIGH 8: Принудительное применение rate limiting для предотвращения блокировок.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from .constants import DEFAULT_NETWORK_TIMEOUT

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


# =============================================================================
# RATE LIMITING ДЛЯ ВНЕШНИХ ЗАПРОСОВ
# =============================================================================

# ISSUE-003-#7: Инициализируем lock и timestamps при импорте для предотвращения race condition
# при ленивой инициализации из нескольких потоков
_rate_limit_lock: threading.Lock = threading.Lock()
_request_timestamps: deque[float] = deque()
_min_request_interval: float = 0.1  # Минимальный интервал между запросами (100ms)
_max_requests_per_second: int = 10  # Максимум запросов в секунду


def _enforce_rate_limit() -> None:
    """HIGH 8: Принудительное применение rate limiting.

    Ограничивает количество запросов в секунду и минимальный интервал между запросами.
    Блокирует выполнение пока не будет разрешён следующий запрос.

    ИСПРАВЛЕНИЕ #1: Все обращения к _request_timestamps строго внутри with _rate_limit_lock
    для предотвращения race condition при одновременных append/popleft операциях.

    ИСПРАВЛЕНИЕ #12: Sleep вынесен за пределы lock — сначала вычисляем время ожидания
    внутри lock, затем освобождаем lock и спим снаружи.
    """
    global _request_timestamps

    now = time.time()
    sleep_time = 0.0

    with _rate_limit_lock:
        # Удаляем старые timestamps (старше 1 секунды)
        while _request_timestamps and _request_timestamps[0] < now - 1.0:
            _request_timestamps.popleft()

        # Проверяем лимит запросов в секунду
        if len(_request_timestamps) >= _max_requests_per_second:
            # Ждём пока oldest timestamp не выйдет за 1 секунду
            oldest = _request_timestamps[0]
            sleep_time = (oldest + 1.0) - now
            if sleep_time > 0:
                # Обновляем now после предполагаемого sleep
                now = now + sleep_time
                # Снова очищаем старые timestamps (будут неактуальны после sleep)
                while _request_timestamps and _request_timestamps[0] < now - 1.0:
                    _request_timestamps.popleft()

        # Проверяем минимальный интервал между запросами
        if _request_timestamps:
            last_request_time = _request_timestamps[-1]
            time_since_last = now - last_request_time
            if time_since_last < _min_request_interval:
                min_sleep = _min_request_interval - time_since_last
                sleep_time = max(sleep_time, min_sleep)

        # Добавляем текущий timestamp (всегда внутри lock)
        _request_timestamps.append(time.time())

    # Sleep вынесен за пределы lock для минимизации времени блокировки
    if sleep_time > 0:
        time.sleep(sleep_time)


def _safe_external_request(
    method: str = "GET", url: str = "", timeout: int | None = None, **kwargs: Any
) -> requests.Response | None:
    """Безопасный внешний запрос с rate limiting.

    HIGH 8: Принудительное применение rate limiting перед каждым запросом.

    Args:
        method: HTTP метод.
        url: URL для запроса.
        timeout: Таймаут запроса (по умолчанию DEFAULT_NETWORK_TIMEOUT).
        **kwargs: Дополнительные аргументы для requests.

    Returns:
        requests.Response объект или None при ошибке.

    """
    if requests is None:
        raise ImportError("requests library is required for _safe_external_request")

    # HIGH 8: Принудительное применение rate limiting ПЕРЕД запросом
    _enforce_rate_limit()

    # Используем дефолтный таймаут если не указан
    if timeout is None:
        timeout = DEFAULT_NETWORK_TIMEOUT

    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        return response
    except requests.exceptions.RequestException as e:
        # Логируем ошибку, но не выбрасываем - пусть вызывающий код решает
        from parser_2gis.logger import logger as app_logger

        app_logger.debug("Ошибка HTTP запроса к %s: %s", url, e)
        return None
    except (KeyboardInterrupt, SystemExit):
        raise
    except (OSError, ValueError) as e:
        from parser_2gis.logger import logger as app_logger

        app_logger.error("Неожиданная ошибка HTTP запроса к %s: %s", url, e)
        return None
