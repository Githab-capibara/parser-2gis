"""Пакет application для Parser2GIS.  # noqa: RUF002.

Предоставляет фасады для упрощения взаимодействия с основными компонентами:
- ParserFacade: фасад для парсеров
- CacheFacade: фасад для кэширования
- BrowserFacade: фасад для браузера
"""

from parser_2gis.application.layer import BrowserFacade, CacheFacade, ParserFacade

__all__ = ["BrowserFacade", "CacheFacade", "ParserFacade"]
