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
from typing import TYPE_CHECKING, Dict, Optional

from parser_2gis.logger.logger import logger as app_logger

if TYPE_CHECKING:
    import requests


# =============================================================================
# КЭШИРОВАНИЕ HTTP ЗАПРОСОВ С TTL
# =============================================================================

# Время жизни кэша HTTP запросов в секундах (2 минуты — агрессивно ускорено)
HTTP_CACHE_TTL_SECONDS = 120

# Размер кэша HTTP запросов (максимальное количество записей)
HTTP_CACHE_MAXSIZE = 1024


class _HTTPCacheEntry:
    """Запись кэша HTTP запроса с TTL."""

    def __init__(self, response: "requests.Response", timestamp: float) -> None:
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

    Использует RLock для поддержки реентрантных вызовов.
    Автоматически удаляет старые записи при превышении максимального размера.
    """

    def __init__(self, maxsize: int = HTTP_CACHE_MAXSIZE) -> None:
        self._cache: Dict[tuple, _HTTPCacheEntry] = {}
        self._lock = threading.RLock()  # RLock для поддержки реентрантных вызовов
        self._maxsize = maxsize

    def get(self, key: tuple) -> Optional["requests.Response"]:
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

    def set(self, key: tuple, response: "requests.Response") -> None:
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
        """Возвращает текущий размер кэша.

        Returns:
            Количество записей в кэше.
        """
        with self._lock:
            return len(self._cache)


# =============================================================================
# СИНГЛТОН ЭКЗЕМПЛЯР КЭША
# =============================================================================

_http_cache_instance: Optional[_HTTPCache] = None
_http_cache_lock = threading.RLock()  # RLock для поддержки реентрантных вызовов


def _get_http_cache() -> _HTTPCache:
    """Получает синглтон экземпляр HTTP кэша.

    Returns:
        Экземпляр _HTTPCache.
    """
    global _http_cache_instance
    with _http_cache_lock:
        if _http_cache_instance is None:
            _http_cache_instance = _HTTPCache()
        return _http_cache_instance


def _get_cache_key(method: str, url: str, verify_ssl: bool) -> tuple:
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
