"""Общие константы конфигурации для устранения циклических импортов.

ISSUE-031: Вынесено DEFAULT_TTL_HOURS из chrome.constants в общий модуль,
чтобы cache.manager и другие модули не зависели от chrome.constants.

ISSUE-034: Общий модуль констант для разрыва циклических зависимостей
между parser.options, cache.manager и chrome.constants.
"""

from __future__ import annotations

# TTL кэша по умолчанию в часах
# ОБОСНОВАНИЕ: 24 часа выбрано исходя из:
# - Типичное время актуальности данных парсинга: 1-7 дней
# - 24 часа обеспечивают баланс между актуальностью и производительностью
# - Снижает нагрузку на сервер при повторных запросах
DEFAULT_TTL_HOURS: int = 24

# Лимит оперативной памяти по умолчанию в мегабайтах
DEFAULT_MEMORY_LIMIT_MB: int = 2048

# Максимальный размер ответа от внешних сервисов для предотвращения DoS атак
MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# =============================================================================
# 2GIS URL КОНСТАНТЫ (ISSUE-200: Централизация всех URL)
# =============================================================================

# Базовый URL 2GIS для формирования ссылок на филиалы
# ISSUE-200: Вынесено в константу для устранения хардкода в writer/models/catalog_item.py
TWO_GIS_BASE_URL: str = "https://2gis.com"

# Шаблон URL филиала 2GIS
# Используется: writer/models/catalog_item.py::CatalogItem.url
TWO_GIS_FIRM_URL_TEMPLATE: str = "https://2gis.com/firm/{}"

# Паттерн для API каталога 2GIS
# Используется: application/layer.py::BrowserFacade, parser/parsers/main_parser.py
CATALOG_API_PATTERN: str = r"https://catalog\.api\.2gis\.[^/]+/.*/items/byid"
