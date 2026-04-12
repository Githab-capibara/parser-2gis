"""Модуль фасадов приложения Parser2GIS.  # noqa: RUF002.

Предоставляет фасады для упрощения взаимодействия с основными компонентами:
- ParserFacade: фасад для парсеров
- CacheFacade: фасад для кэширования
- BrowserFacade: фасад для браузера

H8: Выделение бизнес-логики и инфраструктуры через фасады.
ISSUE-014: Dependency Injection — зависимости внедряются через конструктор.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Self

from parser_2gis.shared_config_constants import CATALOG_API_PATTERN

if TYPE_CHECKING:
    from collections.abc import Callable

    from parser_2gis.cache import CacheManager
    from parser_2gis.chrome.options import ChromeOptions
    from parser_2gis.chrome.remote import ChromeRemote
    from parser_2gis.parser.options import ParserOptions
    from parser_2gis.parser.parsers.base import BaseParser
    from parser_2gis.parser.parsers.main import MainParser
    from parser_2gis.protocols import BrowserService
    from parser_2gis.writer import FileWriter


# =============================================================================
# PROTOCOLS ДЛЯ FACTORY (ISSUE-014: DIP)
# =============================================================================


class ParserFactoryProtocol(Protocol):
    """Protocol для фабрики парсеров.

    ISSUE-014: Позволяет внедрять mock фабрику для тестирования.
    """

    def __call__(
        self,
        url: str,
        chrome_options: ChromeOptions,
        parser_options: ParserOptions,
        browser: BrowserService | None = None,
    ) -> BaseParser:
        """Создаёт парсер."""


# =============================================================================
# PARSER FACADE (ISSUE-014: DIP)
# =============================================================================


class ParserFacade:
    """Фасад для работы с парсерами.

    Упрощает создание и использование парсеров, предоставляя
    единый интерфейс для всех операций парсинга.

    ISSUE-014: Dependency Injection — фабрика парсеров внедряется через конструктор.

    Example:
        >>> # Использование по умолчанию
        >>> facade = ParserFacade()
        >>> parser = facade.create_parser(url, chrome_options, parser_options)
        >>> parser.parse(writer)
        >>>
        >>> # Использование с внедрённой зависимостью (для тестирования)
        >>> mock_factory = MockParserFactory()
        >>> facade = ParserFacade(parser_factory=mock_factory)

    """

    def __init__(self, parser_factory: ParserFactoryProtocol | None = None) -> None:
        """Инициализация ParserFacade.

        ISSUE-014: Фабрика парсеров внедряется через конструктор.

        Args:
            parser_factory: Опциональная фабрика парсеров для DI.
                           Если не передана, используется по умолчанию.

        """
        self._parser_factory = parser_factory or self._default_parser_factory

    def _default_parser_factory(
        self,
        url: str,
        chrome_options: ChromeOptions,
        parser_options: ParserOptions,
        browser: BrowserService | None = None,
    ) -> BaseParser | MainParser:
        """Фабрика парсеров по умолчанию.

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

    def create_parser(
        self,
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
        return self._parser_factory(url, chrome_options, parser_options, browser)

    def parse_url(
        self,
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
        parser = self.create_parser(url, chrome_options, parser_options, browser)
        try:
            parser.parse(writer)
            return parser.get_stats()
        finally:
            if hasattr(parser, "close"):
                parser.close()


# =============================================================================
# CACHE FACADE (ISSUE-014: DIP)
# =============================================================================


class CacheFacade:
    """Фасад для работы с кэшем.

    Упрощает операции кэширования, предоставляя единый интерфейс
    для всех операций с кэшем.

    ISSUE-014: Dependency Injection — CacheManager внедряется через конструктор.

    Example:
        >>> # Использование по умолчанию
        >>> facade = CacheFacade(cache_path)
        >>> facade.get("key")
        >>>
        >>> # Использование с внедрённой зависимостью (для тестирования)
        >>> mock_cache = MockCacheManager()
        >>> facade = CacheFacade(cache_manager=mock_cache)

    """

    def __init__(
        self, cache_path: str | None = None, cache_manager: CacheManager | None = None
    ) -> None:
        """Инициализация фасада кэша.

        ISSUE-014: CacheManager внедряется через конструктор.

        Args:
            cache_path: Путь к файлу кэша (если cache_manager не передан).
            cache_manager: Опциональный CacheManager для DI.
                          Если не передан, создаётся по умолчанию.

        Raises:
            ValueError: Если не передан ни cache_path, ни cache_manager.

        """
        from parser_2gis.cache import CacheManager

        if cache_manager is not None:
            self._cache: CacheManager = cache_manager
        elif cache_path is not None:
            self._cache = CacheManager(Path(cache_path))
        else:
            error_msg = "cache_path или cache_manager обязателен"
            raise ValueError(error_msg)

    def get(self, key: str) -> dict[str, Any] | None:
        """Получает значение из кэша.

        Args:
            key: Ключ для получения.

        Returns:
            Значение из кэша или None.

        """
        return self._cache.get(key)

    def set(self, key: str, value: Any, _ttl: int = 3600) -> None:
        """Устанавливает значение в кэш.

        Args:
            key: Ключ для установки.
            value: Значение для кэширования.
            _ttl: Время жизни в секундах (не используется, оставлено для обратной совместимости).

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

    def __enter__(self) -> Self:
        """Входит в контекстный менеджер.

        Returns:
            Экземпляр CacheFacade для использования в блоке with.

        """
        return self

    def __exit__(self, *args: object) -> None:
        """Выходит из контекстного менеджера, закрывая кэш.

        Args:
            *args: Аргументы исключения (exc_type, exc_val, exc_tb).

        """
        self.close()


# =============================================================================
# BROWSER FACADE (ISSUE-014: DIP)
# =============================================================================


class BrowserFacade:
    """Фасад для работы с браузером.

    Упрощает создание и управление браузером, предоставляя
    единый интерфейс для всех браузерных операций.

    ISSUE-014: Dependency Injection — ChromeRemote factory внедряется через конструктор.

    Example:
        >>> # Использование по умолчанию
        >>> facade = BrowserFacade(chrome_options)
        >>> with facade.create_browser() as browser:
        >>>     browser.navigate("https://2gis.ru")
        >>>
        >>> # Использование с внедрённой зависимостью (для тестирования)
        >>> mock_browser_factory = MockBrowserFactory()
        >>> facade = BrowserFacade(browser_factory=mock_browser_factory)

    """

    def __init__(
        self,
        chrome_options: ChromeOptions | None = None,
        browser_factory: Callable[[], BrowserService] | None = None,
        response_patterns: list[str] | None = None,
    ) -> None:
        """Инициализация браузерного фасада.

        ISSUE-014: Browser factory внедряется через конструктор.

        Args:
            chrome_options: Опции Chrome (если browser_factory не передан).
            browser_factory: Опциональная фабрика браузеров для DI.
                            Если не передана, создаётся по умолчанию.
            response_patterns: Паттерны для перехвата ответов.

        Raises:
            ValueError: Если не передан ни chrome_options, ни browser_factory.

        """
        if browser_factory is not None:
            self._browser_factory = browser_factory
            self._chrome_options = None
        elif chrome_options is not None:
            self._chrome_options = chrome_options
            self._browser_factory = None  # type: ignore[assignment]
        else:
            error_msg = "Необходимо передать chrome_options или browser_factory"
            raise ValueError(error_msg)

        self._response_patterns = response_patterns or [CATALOG_API_PATTERN]

    def create_browser(self) -> ChromeRemote:
        """Создаёт экземпляр браузера.

        Returns:
            Экземпляр ChromeRemote.

        """
        if self._browser_factory is not None:
            return self._browser_factory()  # type: ignore[return-value]

        from parser_2gis.chrome.remote import ChromeRemote

        if self._chrome_options is None:
            error_msg = "chrome_options не передан"
            raise ValueError(error_msg)

        return ChromeRemote(self._chrome_options, self._response_patterns)

    def navigate(self, url: str, browser: BrowserService | None = None) -> None:
        """Выполняет навигацию по URL.

        Args:
            url: URL для навигации.
            browser: Опциональный браузер (если не передан, создаётся новый).

        """
        own_browser = browser
        if own_browser is None:
            own_browser = self.create_browser()  # type: ignore[assignment]
        own_browser.navigate(url)  # type: ignore[union-attr]

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
