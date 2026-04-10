"""Утилиты парсера.

Предоставляет функции для получения списка заблокированных запросов
(метрика, логирование, аналитика, реклама и т.д.).

ISSUE-130, ISSUE-131: Оптимизация - вынесены константы и добавлено кэширование.
"""

from __future__ import annotations

import functools

# ISSUE-130: Вынесены списки заблокированных запросов в константы
_BLOCKED_BASE_REQUESTS: tuple[str, ...] = (
    # Метрика, логирование, аналитика, счётчики, реклама и т.д.
    "https://favorites.api.2gis.*/*",
    "https://2gis.*/_/log",
    "https://2gis.*/_/metrics",
    "https://google-analytics.com/*",
    "https://www.google-analytics.com/*",
    "https://counter.yadro.ru/*",
    "https://www.tns-counter.ru/*",
    "https://mc.yandex.ru/*",
    "https://catalog.api.2gis.ru/3.0/ads/*",
    "https://d-assets.2gis.*/privacyPolicyBanner*.js",
    "https://vk.com/*",
)

_BLOCKED_EXTRA_REQUESTS: tuple[str, ...] = (
    # Стили, плитки карт, изображения и прочие ресурсы визуализации
    "https://d-assets.2gis.*/fonts/*",
    "https://mapgl.2gis.*/api/fonts/*",
    "https://tile*.maps.2gis.*",
    "https://s*.bss.2gis.*",
    "https://styles.api.2gis.*",
    "https://video-pr.api.2gis.*",
    "https://api.photo.2gis.*/*",
    "https://market-backend.api.2gis.*",
    "https://traffic*.edromaps.2gis.*",
    "https://disk.2gis.*/styles/*",
)


@functools.lru_cache(maxsize=2)
def blocked_requests(*, extended: bool = False) -> tuple[str, ...]:
    """Получить список заблокированных запросов.

    Включает метрику, логирование, аналитику, счётчики, рекламу и т.д.

    ISSUE-131: Кэширование результатов через lru_cache для предотвращения
    создания новых списков при каждом вызове.

    Во время парсинга нам не нужны запросы, которые могут замедлить
    скорость или увеличить потребление памяти, или отправлять
    логи автоматической активности бота.

    Списки разделены: базовый и расширенный, который включает
    изображения, стили, плитки карт, шрифты и другие визуальные
    ресурсы.

    Args:
        extended: Вернуть расширенный список или базовый.

    Returns:
        Кортеж блокируемых URL-шаблонов.

    """
    if extended:
        return _BLOCKED_BASE_REQUESTS + _BLOCKED_EXTRA_REQUESTS
    return _BLOCKED_BASE_REQUESTS
