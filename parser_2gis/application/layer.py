"""Модуль фасадов приложения Parser2GIS.

Предоставляет фасады для упрощения взаимодействия с основными компонентами:
- ParserFacade: фасад для парсеров
- CacheFacade: фасад для кэширования
- BrowserFacade: фасад для браузера

H8: Выделение бизнес-логики и инфраструктуры через фасады.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from parser_2gis.protocols import BrowserService

if TYPE_CHECKING:
    from parser_2gis.cache import CacheManager
    from parser_2gis.chrome.options import ChromeOptions
    from parser_2gis.chrome.remote import ChromeRemote
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.parser.parsers.base import BaseParser
    from parser_2gis.writer import FileWriter


class ParserFacade:
    """Фасад для работы с парсерами.

    Упрощает создание и использование парсеров, предоставляя
    единый интерфейс для всех операций парсинга.

    Example:
        >>> facade = ParserFacade()
        >>> parser = facade.create_parser(url, chrome_options, parser_options)
        >>> parser.parse(writer)

    """

    @staticmethod
    def create_parser(
        url: str,
        chrome_options: ChromeOptions,
        parser_options: ParserOptions,
        browser: BrowserService | None = None,
    ) -> BaseParser:
        """Создаёт парсер для указанного URL.

        Args:
            url: URL для парсинга.
            chrome_options: Опции Chrome.
            parser_options: Опции парсера.
            browser: Опциональный браузер для DI.

        Returns:
            Экземпляр парсера.

        """
        from parser_2gis.parser.factory import get_parser

        return get_parser(url, chrome_options, parser_options, browser)

    @staticmethod
    def parse_url(
        url: str,
        writer: FileWriter,
        chrome_options: ChromeOptions,
        parser_options: ParserOptions,
        browser: BrowserService | None = None,
    ) -> dict[str, Any]:
        """Выполняет парсинг URL и возвращает статистику.

        Args:
            url: URL для парсинга.
            writer: Writer для записи результатов.
            chrome_options: Опции Chrome.
            parser_options: Опции парсера.
            browser: Опциональный браузер для DI.

        Returns:
            Словарь со статистикой парсинга.

        """
        parser = ParserFacade.create_parser(url, chrome_options, parser_options, browser)
        try:
            parser.parse(writer)
            return parser.get_stats()
        finally:
            if hasattr(parser, "close"):
                parser.close()


class CacheFacade:
    """Фасад для работы с кэшем.

    Упрощает операции кэширования, предоставляя единый интерфейс
    для всех операций с кэшем.

    Example:
        >>> facade = CacheFacade(cache_path)
        >>> facade.get("key")
        >>> facade.set("key", "value", ttl=3600)

    """

    def __init__(self, cache_path: str) -> None:
        """Инициализация фасада кэша.

        Args:
            cache_path: Путь к файлу кэша.

        """
        from parser_2gis.cache import CacheManager

        self._cache: CacheManager = CacheManager(cache_path)

    def get(self, key: str) -> Any | None:
        """Получает значение из кэша.

        Args:
            key: Ключ для получения.

        Returns:
            Значение из кэша или None.

        """
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Устанавливает значение в кэш.

        Args:
            key: Ключ для установки.
            value: Значение для кэширования.
            ttl: Время жизни в секундах (не используется, оставлено для обратной совместимости).

        """
        self._cache.set(key, value)

    def exists(self, key: str) -> bool:
        """Проверяет наличие ключа в кэше.

        Args:
            key: Ключ для проверки.

        Returns:
            True если ключ существует.

        """
        return self._cache.get(key) is not None

    def delete(self, key: str) -> None:
        """Удаляет значение из кэша.

        Args:
            key: Ключ для удаления.

        """
        self._cache.delete(key)

    def close(self) -> None:
        """Закрывает кэш и освобождает ресурсы."""
        self._cache.close()

    def __enter__(self) -> CacheFacade:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class BrowserFacade:
    """Фасад для работы с браузером.

    Упрощает создание и управление браузером, предоставляя
    единый интерфейс для всех браузерных операций.

    Example:
        >>> facade = BrowserFacade(chrome_options)
        >>> with facade.create_browser() as browser:
        >>>     browser.navigate("https://2gis.ru")
        >>>     html = browser.get_html()

    """

    def __init__(self, chrome_options: ChromeOptions) -> None:
        """Инициализация браузерного фасада.

        Args:
            chrome_options: Опции Chrome.

        """
        self._chrome_options = chrome_options
        self._response_patterns: list[str] = [r"https://catalog\.api\.2gis\.[^/]+/.*/items/byid"]

    def create_browser(self) -> ChromeRemote:
        """Создаёт экземпляр браузера.

        Returns:
            Экземпляр ChromeRemote.

        """
        from parser_2gis.chrome.remote import ChromeRemote

        return ChromeRemote(self._chrome_options, self._response_patterns)

    def navigate(self, url: str, browser: BrowserService | None = None) -> None:
        """Выполняет навигацию по URL.

        Args:
            url: URL для навигации.
            browser: Опциональный браузер (если не передан, создаётся новый).

        """
        own_browser = browser or self.create_browser()
        own_browser.navigate(url)

    def get_html(self, browser: BrowserService) -> str:
        """Получает HTML страницы.

        Args:
            browser: Браузер для получения HTML.

        Returns:
            HTML содержимое страницы.

        """
        return browser.get_html()

    def execute_js(self, browser: BrowserService, js_code: str, timeout: int | None = None) -> Any:
        """Выполняет JavaScript код.

        Args:
            browser: Браузер для выполнения JS.
            js_code: JavaScript код для выполнения.
            timeout: Таймаут выполнения в секундах.

        Returns:
            Результат выполнения JS.

        """
        return browser.execute_js(js_code, timeout)

    def close(self, browser: BrowserService) -> None:
        """Закрывает браузер.

        Args:
            browser: Браузер для закрытия.

        """
        if hasattr(browser, "close"):
            browser.close()


__all__ = ["BrowserFacade", "CacheFacade", "ParserFacade"]
