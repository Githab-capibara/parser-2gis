"""Builder для ChromeBrowser (BrowserLifecycleManager).

ISSUE 114: Добавляет паттерн Builder для создания ChromeBrowser
с использованием fluent interface.

Пример использования:
    >>> from parser_2gis.chrome import ChromeBrowserBuilder
    >>> browser = ChromeBrowserBuilder().with_options(chrome_options).build()
    >>> browser.init()
    >>> browser.close()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .browser import ChromeBrowser
    from .options import ChromeOptions


class ChromeBrowserBuilder:
    """Builder для ChromeBrowser с fluent interface.

    ISSUE 114: Устраняет необходимость передавать много параметров,
    позволяя пошагово конфигурировать браузер через цепочку вызовов.

    Example:
        >>> builder = ChromeBrowserBuilder()
        >>> builder = builder.with_options(options)
        >>> browser = builder.build()

    """

    def __init__(self) -> None:
        """Инициализирует builder с параметрами по умолчанию."""
        self._chrome_options: ChromeOptions | None = None

    def with_options(self, options: ChromeOptions) -> ChromeBrowserBuilder:
        """Устанавливает опции Chrome.

        Args:
            options: Опции Chrome.

        Returns:
            Этот же экземпляр builder для цепочки вызовов.

        """
        self._chrome_options = options
        return self

    def build(self) -> ChromeBrowser:
        """Создаёт и возвращает экземпляр ChromeBrowser.

        Returns:
            Настроенный экземпляр ChromeBrowser.

        Raises:
            ValueError: Если не переданы опции Chrome.

        """
        from .browser import ChromeBrowser

        if self._chrome_options is None:
            raise ValueError("Опции Chrome обязательны. Используйте with_options().")

        return ChromeBrowser(chrome_options=self._chrome_options)


__all__ = ["ChromeBrowserBuilder"]
