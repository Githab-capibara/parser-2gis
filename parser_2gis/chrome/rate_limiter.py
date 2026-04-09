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


class RateLimiterState:
    """Класс для управления состоянием rate limiting с потокобезопасным доступом.

    ISSUE 061: Оборачивает модульное изменяемое состояние (_rate_limit_lock,
    _request_timestamps) в класс с thread-safe доступом.
    """

    def __init__(
        self,
        min_request_interval: float = 0.1,
        max_requests_per_second: int = 10,
    ) -> None:
        """Инициализирует состояние rate limiter.

        Args:
            min_request_interval: Минимальный интервал между запросами (секунды).
            max_requests_per_second: Максимум запросов в секунду.

        """
        self._lock: threading.Lock = threading.Lock()
        self._request_timestamps: deque[float] = deque()
        self._min_request_interval: float = min_request_interval
        self._max_requests_per_second: int = max_requests_per_second

    def enforce_rate_limit(self) -> None:
        """Принудительное применение rate limiting.

        Ограничивает количество запросов в секунду и минимальный интервал между запросами.
        Блокирует выполнение пока не будет разрешён следующий запрос.

        Все обращения к _request_timestamps строго внутри with _lock
        для предотвращения race condition.
        Sleep вынесен за пределы lock.
        """
        now = time.time()
        sleep_time = 0.0

        with self._lock:
            # Удаляем старые timestamps (старше 1 секунды)
            while self._request_timestamps and self._request_timestamps[0] < now - 1.0:
                self._request_timestamps.popleft()

            # Проверяем лимит запросов в секунду
            if len(self._request_timestamps) >= self._max_requests_per_second:
                # Ждём пока oldest timestamp не выйдет за 1 секунду
                oldest = self._request_timestamps[0]
                sleep_time = (oldest + 1.0) - now
                if sleep_time > 0:
                    # Обновляем now после предполагаемого sleep
                    now = now + sleep_time
                    # Снова очищаем старые timestamps (будут неактуальны после sleep)
                    while self._request_timestamps and self._request_timestamps[0] < now - 1.0:
                        self._request_timestamps.popleft()

            # Проверяем минимальный интервал между запросами
            if self._request_timestamps:
                last_request_time = self._request_timestamps[-1]
                time_since_last = now - last_request_time
                if time_since_last < self._min_request_interval:
                    min_sleep = self._min_request_interval - time_since_last
                    sleep_time = max(sleep_time, min_sleep)

            # Добавляем текущий timestamp (всегда внутри lock)
            self._request_timestamps.append(time.time())

        # Sleep вынесен за пределы lock для минимизации времени блокировки
        if sleep_time > 0:
            time.sleep(sleep_time)

    def clear(self) -> None:
        """Очищает timestamps (полезно для тестирования)."""
        with self._lock:
            self._request_timestamps.clear()

    @property
    def request_count(self) -> int:
        """Возвращает текущее количество timestamps в окне."""
        with self._lock:
            return len(self._request_timestamps)


# Глобальный экземпляр состояния для обратной совместимости
_default_state = RateLimiterState()


def _enforce_rate_limit() -> None:
    """HIGH 8: Принудительное применение rate limiting.

    Делегирует вызов глобальному экземпляру RateLimiterState.
    """
    _default_state.enforce_rate_limit()


def get_rate_limiter_state() -> RateLimiterState:
    """Возвращает глобальный экземпляр состояния rate limiter.

    Returns:
        Экземпляр RateLimiterState для управления rate limiting.

    """
    return _default_state


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


__all__ = [
    "RateLimiterState",
    "_enforce_rate_limit",
    "_safe_external_request",
    "get_rate_limiter_state",
]
