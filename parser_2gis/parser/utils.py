"""Утилиты парсера.

Предоставляет функции для получения списка заблокированных запросов
(метрика, логирование, аналитика, реклама и т.д.).
"""

from __future__ import annotations


def blocked_requests(extended: bool = False) -> list[str]:
    """Получить список заблокированных запросов: метрика, логирование,
    аналитика, счётчики, реклама и т.д.

    Во время парсинга нам не нужны запросы, которые могут замедлить
    скорость или увеличить потребление памяти, или отправлять
    логи автоматической активности бота.

    Списки разделены: базовый и расширенный, который включает
    изображения, стили, плитки карт, шрифты и другие визуальные
    ресурсы.

    Args:
        extended: Вернуть расширенный список или базовый.

    Returns:
        Список блокируемых URL-шаблонов.

    """
    # Метрика, логирование, аналитика, счётчики, реклама и т.д.
    base_requests: list[str] = [
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
    ]

    # Стили, плитки карт, изображения и прочие ресурсы визуализации
    extra_requests: list[str] = [
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
    ]

    # Возвращаем новый список для предотвращения изменения кэша
    result = base_requests.copy()
    if extended:
        result.extend(extra_requests)

    return result
