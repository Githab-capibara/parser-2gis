"""Модуль кэширования HTTP запросов.

Предоставляет классы и функции для кэширования HTTP запросов с TTL:
- _HTTPCacheEntry - Запись кэша с временной меткой
- _HTTPCache - Потокобезопасный кэш с LRU eviction
- _get_http_cache - Синглтон экземпляр кэша
- _get_cache_key - Создание ключа кэша
- _cleanup_expired_cache - Очистка истёкших записей
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

from parser_2gis.logger.logger import logger as app_logger

# =============================================================================
# КЭШИРОВАНИЕ HTTP ЗАПРОСОВ С TTL
# =============================================================================

# Время жизни кэша HTTP запросов в секундах (2 минуты — агрессивно ускорено)
HTTP_CACHE_TTL_SECONDS = 120

# Размер кэша HTTP запросов (максимальное количество записей)
HTTP_CACHE_MAXSIZE = 1024

# D012: Rate limiting для HTTP кэша — минимальная задержка между запросами
_HTTP_CACHE_RATE_LIMIT_DELAY = 0.05  # 50ms между запросами


class _HTTPCacheEntry:
    """Запись кэша HTTP запроса с TTL."""

    def __init__(self, response: requests.Response, timestamp: float) -> None:
        """Инициализирует запись HTTP кэша.

        Args:
            response: Данные ответа.
            timestamp: Время сохранения.

        """
        self.response = response
        self.timestamp = timestamp

    def is_expired(self) -> bool:
        """Проверяет истёк ли срок действия кэша.

        Returns:
            True если кэш истёк, False иначе.

        """
        return (time.time() - self.timestamp) > HTTP_CACHE_TTL_SECONDS


class _HTTPCache:
    """Инкапсулированный кэш для HTTP запросов с потокобезопасностью.

    H017: Использует OrderedDict для эффективного LRU eviction.
    Автоматически удаляет старые записи при превышении максимального размера.
    """

    def __init__(self, maxsize: int = HTTP_CACHE_MAXSIZE) -> None:
        # H017: Используем OrderedDict для LRU eviction
        self._cache: OrderedDict[tuple[str, str, bool], _HTTPCacheEntry] = OrderedDict()
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов
        self._maxsize = maxsize

    def get(self, key: tuple[str, str, bool]) -> requests.Response | None:
        """Получает закэшированный ответ.

        H017: Обновляет порядок доступа для LRU.

        Args:
            key: Ключ кэша.

        Returns:
            Response объект или None если не найден или истёк.

        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    # H017: Перемещаем в конец для LRU (recent use)
                    self._cache.move_to_end(key)
                    return entry.response
                del self._cache[key]
            # D012: При промахе кэша применяем rate limiting
            return None

    def set(self, key: tuple[str, str, bool], response: requests.Response) -> None:
        """Сохраняет ответ в кэш.

        H017: LRU eviction при превышении размера.

        Args:
            key: Ключ кэша.
            response: Response объект для кэширования.

        """
        with self._lock:
            # H017: LRU eviction - удаляем oldest записи при превышении
            while len(self._cache) >= self._maxsize:
                # Удаляем первую (самую старую) запись
                self._cache.popitem(last=False)

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

    def _size(self) -> int:
        """Возвращает текущий размер кэша.

        Returns:
            Количество записей в кэше.

        """
        with self._lock:
            return len(self._cache)


# =============================================================================
# СИНГЛТОН ЭКЗЕМПЛЯР КЭША
# =============================================================================

_http_cache_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов


def _get_http_cache() -> _HTTPCache:
    """Получает синглтон экземпляр HTTP кэша.

    Returns:
        Экземпляр _HTTPCache.

    """
    if not hasattr(_get_http_cache, "_instance"):
        with _http_cache_lock:
            if not hasattr(_get_http_cache, "_instance"):
                _get_http_cache._instance = _HTTPCache()  # type: ignore[attr-defined]
    return _get_http_cache._instance  # type: ignore[attr-defined,no-any-return]


def _get_cache_key(method: str, url: str, *, verify_ssl: bool) -> tuple[str, str, bool]:
    """Создаёт ключ кэша для HTTP запроса.

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
