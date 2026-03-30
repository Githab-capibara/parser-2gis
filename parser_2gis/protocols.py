"""
Protocol для callback и интерфейсов проекта parser-2gis.

Этот модуль предоставляет Protocol для типизации callback функций
и других интерфейсов используемых в проекте.

Пример использования:
    >>> from parser_2gis.protocols import ProgressCallback, LogCallback, LoggerProtocol
    >>> def my_progress(success: int, failed: int, filename: str) -> None:
    ...     print(f"Прогресс: {success}/{failed}")
    >>> callback: ProgressCallback = my_progress  # type: check
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any, Callable, Iterator, Protocol, runtime_checkable

# =============================================================================
# CALLBACK PROTOCOLS
# =============================================================================


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol для логгера.

    Используется для разрыва циклической зависимости между
    common.py и logger.py.
    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование debug сообщения."""

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование info сообщения."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование warning сообщения."""

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование error сообщения."""

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование critical сообщения."""


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol для callback прогресса параллельного парсинга.

    Используется для уведомления о прогрессе выполнения задач.

    Example:
        >>> def progress_handler(success: int, failed: int, filename: str) -> None:
        >>> callback: ProgressCallback = progress_handler
    """

    def __call__(self, success: int, failed: int, filename: str) -> None:
        """Вызывается при обновлении прогресса.

        Args:
            success: Количество успешных операций.
            failed: Количество операций с ошибками.
            filename: Имя текущего файла (если применимо).
        """


@runtime_checkable
class LogCallback(Protocol):
    """Protocol для callback логирования.

    Используется для передачи сообщений логов между компонентами.

    Example:
        >>> def logger(message: str, level: str = "INFO") -> None:
        >>> callback: LogCallback = logger
    """

    def __call__(self, message: str, level: str = "INFO") -> None:
        """Вызывается для логирования сообщения.

        Args:
            message: Текст сообщения.
            level: Уровень логирования (DEBUG, INFO, WARNING, ERROR).
        """


@runtime_checkable
class CleanupCallback(Protocol):
    """Protocol для callback очистки ресурсов.

    Используется для вызова процедур очистки.

    Example:
        >>> def cleanup() -> None:
        >>> callback: CleanupCallback = cleanup
    """

    def __call__(self) -> None:
        """Вызывается для очистки ресурсов."""


@runtime_checkable
class CancelCallback(Protocol):
    """Protocol для callback проверки отмены операции.

    Используется для проверки флага отмены в длительных операциях.

    Example:
        >>> def should_cancel() -> bool:
        >>> callback: CancelCallback = should_cancel
    """

    def __call__(self) -> bool:
        """Проверяет необходимость отмены операции.

        Returns:
            True если операция должна быть отменена.
        """


# =============================================================================
# DATA PROTOCOLS
# =============================================================================


@runtime_checkable
class Writer(Protocol):
    """Protocol для записи данных.

    Определяет интерфейс для всех writers (CSV, XLSX, JSON).

    Example:
        >>> class CSVWriter:
        >>> writer: Writer = CSVWriter(...)
    """

    def write(self, records: list[dict]) -> None:
        """Записывает данные.

        Args:
            records: Список записей для записи.
        """

    def close(self) -> None:
        """Закрывает writer и освобождает ресурсы."""


@runtime_checkable
class Parser(Protocol):
    """Protocol для парсеров.

    Определяет интерфейс для всех парсеров.

    Example:
        >>> class FirmParser:
        >>> parser: Parser = FirmParser(...)
    """

    def parse(self) -> list[dict]:
        """Выполняет парсинг данных.

        Returns:
            Список спарсенных записей.
        """

    def get_stats(self) -> dict:
        """Возвращает статистику парсинга.

        Returns:
            Словарь со статистикой.
        """


# =============================================================================
# BROWSER SERVICE PROTOCOLS (разделены по ответственности)
# =============================================================================


@runtime_checkable
class BrowserNavigation(Protocol):
    """Protocol для навигации браузера.

    Определяет интерфейс для навигации по URL.

    Example:
        >>> from parser_2gis.chrome import ChromeRemote
        >>> nav: BrowserNavigation = ChromeRemote(...)  # type: check
        >>> nav.navigate("https://2gis.ru")
    """

    def navigate(self, url: str, **kwargs: Any) -> None:
        """Перейти на URL.

        Args:
            url: URL для навигации.
            **kwargs: Дополнительные параметры навигации.
        """


@runtime_checkable
class BrowserContentAccess(Protocol):
    """Protocol для доступа к содержимому страницы.

    Определяет интерфейс для получения HTML и DOM.

    Example:
        >>> from parser_2gis.chrome import ChromeRemote
        >>> content: BrowserContentAccess = ChromeRemote(...)  # type: check
        >>> html = content.get_html()
    """

    def get_html(self) -> str:
        """Получить HTML страницы.

        Returns:
            HTML содержимое текущей страницы.
        """

    def get_document(self) -> Any:
        """Получить DOM дерево страницы.

        Returns:
            DOM дерево текущей страницы.
        """


@runtime_checkable
class BrowserJSExecution(Protocol):
    """Protocol для выполнения JavaScript.

    Определяет интерфейс для выполнения JS кода.

    Example:
        >>> from parser_2gis.chrome import ChromeRemote
        >>> js: BrowserJSExecution = ChromeRemote(...)  # type: check
        >>> result = js.execute_js("document.title")
    """

    def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
        """Выполнить JavaScript код.

        Args:
            js_code: JavaScript код для выполнения.
            timeout: Таймаут выполнения в секундах (опционально).

        Returns:
            Результат выполнения JavaScript.
        """


@runtime_checkable
class BrowserScreenshot(Protocol):
    """Protocol для создания скриншотов.

    Определяет интерфейс для создания скриншотов страницы.

    Example:
        >>> from parser_2gis.chrome import ChromeRemote
        >>> screenshot: BrowserScreenshot = ChromeRemote(...)  # type: check
        >>> browser.screenshot("page.png")
    """

    def screenshot(self, path: str) -> None:
        """Сделать скриншот.

        Args:
            path: Путь для сохранения скриншота.
        """


@runtime_checkable
class BrowserService(
    BrowserNavigation, BrowserContentAccess, BrowserJSExecution, BrowserScreenshot, Protocol
):
    """Абстракция браузера для разрыва связи между chrome/ и parser/.

    Объединяет все браузерные протоколы:
    - BrowserNavigation: навигация по URL
    - BrowserContentAccess: получение HTML и DOM
    - BrowserJSExecution: выполнение JavaScript
    - BrowserScreenshot: создание скриншотов
    - close: закрытие браузера

    Example:
        >>> from parser_2gis.chrome import ChromeRemote
        >>> browser: BrowserService = ChromeRemote(...)  # type: check
        >>> browser.navigate("https://2gis.ru")
        >>> html = browser.get_html()
        >>> browser.close()
    """

    def close(self) -> None:
        """Закрыть браузер и освободить ресурсы."""


# =============================================================================
# CACHE PROTOCOLS
# =============================================================================


@runtime_checkable
class CacheReader(Protocol):
    """Protocol для чтения из кэша.

    Определяет интерфейс для операций чтения кэша.
    Позволяет использовать объекты кэша только для чтения.

    Example:
        >>> from parser_2gis.cache import CacheManager
        >>> reader: CacheReader = CacheManager(...)  # type: check
        >>> value = reader.get("key")
        >>> exists = reader.exists("key")
    """

    def get(self, key: str) -> Any | None:
        """Получает значение из кэша по ключу.

        Args:
            key: Ключ для получения.

        Returns:
            Значение из кэша или None если ключ не найден.
        """

    def exists(self, key: str) -> bool:
        """Проверяет наличие ключа в кэше.

        Args:
            key: Ключ для проверки.

        Returns:
            True если ключ существует.
        """


@runtime_checkable
class CacheWriter(Protocol):
    """Protocol для записи в кэш.

    Определяет интерфейс для операций записи и удаления из кэша.
    Позволяет использовать объекты кэша только для записи.

    Example:
        >>> from parser_2gis.cache import CacheManager
        >>> writer: CacheWriter = CacheManager(...)  # type: check
        >>> writer.set("key", "value", ttl=3600)
        >>> writer.delete("key")
    """

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Устанавливает значение в кэш.

        Args:
            key: Ключ для установки.
            value: Значение для кэширования.
            ttl: Время жизни кэша в секундах.
        """

    def delete(self, key: str) -> None:
        """Удаляет значение из кэша.

        Args:
            key: Ключ для удаления.
        """


@runtime_checkable
class CacheBackend(CacheReader, CacheWriter, Protocol):
    """Абстракция бэкенда кэширования.

    Объединяет CacheReader и CacheWriter для полного доступа к кэшу.
    Определяет интерфейс для всех бэкендов кэширования (Redis, SQLite, in-memory).
    Позволяет легко переключаться между различными реализациями кэша.

    Example:
        >>> from parser_2gis.cache import CacheManager
        >>> cache: CacheBackend = CacheManager(...)  # type: check
        >>> cache.set("key", "value", ttl=3600)
        >>> value = cache.get("key")
        >>> cache.delete("key")
    """


# =============================================================================
# EXECUTION PROTOCOLS
# =============================================================================


@runtime_checkable
class ExecutionBackend(Protocol):
    """Абстракция бэкенда для параллельного выполнения.

    Определяет интерфейс для всех бэкендов выполнения (ThreadPoolExecutor,
    ProcessPoolExecutor, asyncio). Позволяет легко переключаться между
    различными стратегиями параллелизма.

    Example:
        >>> from concurrent.futures import ThreadPoolExecutor
        >>> executor: ExecutionBackend = ThreadPoolExecutor(max_workers=10)  # type: check
        >>> future = executor.submit(my_function, arg1, arg2)
        >>> results = list(executor.map(process_function, items))
        >>> executor.shutdown(wait=True)
    """

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """Отправляет функцию на выполнение.

        Args:
            fn: Функция для выполнения.
            *args: Позиционные аргументы для функции.
            **kwargs: Именованные аргументы для функции.

        Returns:
            Future объект для получения результата.
        """

    def map(
        self, fn: Callable[..., Any], *iterables: Any, timeout: float | None = None
    ) -> Iterator[Any]:
        """Выполняет функцию для каждого элемента итерации.

        Args:
            fn: Функция для выполнения.
            *iterables: Итерируемые объекты с аргументами.
            timeout: Таймаут выполнения в секундах (опционально).

        Returns:
            Итератор с результатами выполнения.
        """

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Останавливает executor и освобождает ресурсы.

        Args:
            wait: Ждать завершения всех задач.
            cancel_futures: Отменить незавершённые задачи (Python 3.9+).
        """


__all__ = [
    # Callback Protocols
    "LoggerProtocol",
    "ProgressCallback",
    "LogCallback",
    "CleanupCallback",
    "CancelCallback",
    # Data Protocols
    "Writer",
    "Parser",
    # Browser Protocols (разделены по ответственности)
    "BrowserNavigation",
    "BrowserContentAccess",
    "BrowserJSExecution",
    "BrowserScreenshot",
    "BrowserService",
    # Cache Protocols (разделены по ответственности)
    "CacheReader",
    "CacheWriter",
    "CacheBackend",
    # Backend Protocols
    "ExecutionBackend",
]
