"""
Пакет application для Parser2GIS.

Предоставляет фасады для упрощения взаимодействия с основными компонентами:
- ParserFacade: фасад для парсеров
- CacheFacade: фасад для кэширования
- BrowserFacade: фасад для браузера
"""

from parser_2gis.application.layer import BrowserFacade, CacheFacade, ParserFacade

__all__ = ["ParserFacade", "CacheFacade", "BrowserFacade"]
