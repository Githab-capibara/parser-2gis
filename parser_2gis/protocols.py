"""Protocol для callback и интерфейсов проекта parser-2gis.

Определяет стандартные интерфейсы для различных компонентов системы:
- Callback протоколы для обратных вызовов
- Протоколы данных для writer/parser
- Протоколы браузера для навигации и выполнения JS
- Протоколы кэширования
- Протоколы выполнения
- Протоколы параллельного парсинга

Пример использования:
    >>> from parser_2gis.protocols import LoggerProtocol, ProgressCallback
    >>> def my_logger(msg: str) -> None:
    ...     print(msg)
    >>> logger: LoggerProtocol = my_logger  # type: ignore
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any, Protocol, runtime_checkable
from collections.abc import Callable, Iterator

from typing import TypeAlias

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

UrlTuple: TypeAlias = tuple[str, str, str]  # (url, category_name, city_name)
UrlGeneratorResult: TypeAlias = list[UrlTuple]
ParserResult: TypeAlias = list[dict[str, Any]]
ParserStats: TypeAlias = dict[str, Any]
FutureResult: TypeAlias = Future[Any]

# =============================================================================
# CALLBACK PROTOCOLS
# =============================================================================


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol для логгера (разрыв циклических зависимостей).

    Определяет стандартный интерфейс для логгеров, позволяя использовать
    различные реализации (logging.Logger, кастомные логгеры и т.д.).

    Example:
        >>> import logging
        >>> logger: LoggerProtocol = logging.getLogger(__name__)
        >>> logger.info("Test message")

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

    Вызывается при обновлении прогресса выполнения парсинга.

    Example:
        >>> def on_progress(success: int, failed: int, filename: str) -> None:
        ...     print(f"Успешно: {success}, Ошибок: {failed}, Файл: {filename}")
        >>> callback: ProgressCallback = on_progress

    """

    def __call__(self, success: int, failed: int, filename: str) -> None:
        """Вызывается при обновлении прогресса.

        Args:
            success: Количество успешных операций.
            failed: Количество неудачных операций.
            filename: Имя текущего файла.

        """


@runtime_checkable
class LogCallback(Protocol):
    """Protocol для callback логирования.

    Example:
        >>> def on_log(message: str, level: str = "INFO") -> None:
        ...     print(f"[{level}] {message}")
        >>> callback: LogCallback = on_log

    """

    def __call__(self, message: str, level: str = "INFO") -> None:
        """Вызывается для логирования сообщения.

        Args:
            message: Сообщение для логирования.
            level: Уровень логирования (по умолчанию "INFO").

        """


@runtime_checkable
class CleanupCallback(Protocol):
    """Protocol для callback очистки ресурсов.

    Example:
        >>> def cleanup() -> None:
        ...     print("Очистка ресурсов")
        >>> callback: CleanupCallback = cleanup

    """

    def __call__(self) -> None:
        """Вызывается для очистки ресурсов."""


@runtime_checkable
class CancelCallback(Protocol):
    """Protocol для callback проверки отмены операции.

    Example:
        >>> def should_cancel() -> bool:
        ...     return False  # Никогда не отменять
        >>> callback: CancelCallback = should_cancel

    """

    def __call__(self) -> bool:
        """Проверяет необходимость отмены операции.

        Returns:
            True если операция должна быть отменена, False иначе.

        """


# =============================================================================
# DATA PROTOCOLS
# =============================================================================


@runtime_checkable
class Writer(Protocol):
    """Protocol для записи данных (CSV, XLSX, JSON)."""

    def write(self, records: list[dict]) -> None:
        """Записывает данные."""

    def close(self) -> None:
        """Закрывает writer и освобождает ресурсы."""


@runtime_checkable
class Parser(Protocol):
    """Protocol для парсеров."""

    def parse(self) -> list[dict]:
        """Выполняет парсинг данных."""

    def get_stats(self) -> dict:
        """Возвращает статистику парсинга."""


# =============================================================================
# BROWSER SERVICE PROTOCOLS
# =============================================================================


@runtime_checkable
class BrowserNavigation(Protocol):
    """Protocol для навигации браузера."""

    def navigate(self, url: str, **kwargs: Any) -> None:
        """Перейти на URL."""


@runtime_checkable
class BrowserContentAccess(Protocol):
    """Protocol для доступа к содержимому страницы."""

    def get_html(self) -> str:
        """Получить HTML страницы."""

    def get_document(self) -> Any:
        """Получить DOM дерево страницы."""


@runtime_checkable
class BrowserJSExecution(Protocol):
    """Protocol для выполнения JavaScript."""

    def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
        """Выполнить JavaScript код."""


@runtime_checkable
class BrowserScreenshot(Protocol):
    """Protocol для создания скриншотов."""

    def screenshot(self, path: str) -> None:
        """Сделать скриншот."""


@runtime_checkable
class BrowserService(
    BrowserNavigation, BrowserContentAccess, BrowserJSExecution, BrowserScreenshot, Protocol
):
    """Абстракция браузера для разрыва связи между chrome/ и parser/."""

    def close(self) -> None:
        """Закрыть браузер и освободить ресурсы."""


# =============================================================================
# CACHE PROTOCOLS
# =============================================================================


@runtime_checkable
class CacheReader(Protocol):
    """Protocol для чтения из кэша."""

    def get(self, key: str) -> Any | None:
        """Получает значение из кэша по ключу."""

    def exists(self, key: str) -> bool:
        """Проверяет наличие ключа в кэше."""


@runtime_checkable
class CacheWriter(Protocol):
    """Protocol для записи в кэш."""

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Устанавливает значение в кэш."""

    def delete(self, key: str) -> None:
        """Удаляет значение из кэша."""


@runtime_checkable
class CacheBackend(CacheReader, CacheWriter, Protocol):
    """Абстракция бэкенда кэширования."""


# =============================================================================
# EXECUTION PROTOCOLS
# =============================================================================


@runtime_checkable
class ExecutionBackend(Protocol):
    """Абстракция бэкенда для параллельного выполнения."""

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """Отправляет функцию на выполнение."""

    def map(
        self, fn: Callable[..., Any], *iterables: Any, timeout: float | None = None
    ) -> Iterator[Any]:
        """Выполняет функцию для каждого элемента итерации."""

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Останавливает executor и освобождает ресурсы."""


# =============================================================================
# PARALLEL PARSING PROTOCOLS
# =============================================================================


@runtime_checkable
class ErrorHandlerProtocol(Protocol):
    """Protocol для обработчика ошибок параллельного парсинга."""

    def handle_memory_error(self, error: MemoryError, temp_file: Any, url: str) -> tuple[bool, str]:
        """Обрабатывает MemoryError."""

    def handle_timeout_error(
        self, temp_file: Any, city_name: str, category_name: str, timeout: int
    ) -> tuple[bool, str]:
        """Обрабатывает таймаут."""

    def handle_other_error(
        self, error: Exception, temp_file: Any, city_name: str, category_name: str
    ) -> tuple[bool, str]:
        """Обрабатывает другие ошибки."""


@runtime_checkable
class MergerProtocol(Protocol):
    """Protocol для объединителя файлов."""

    def merge_csv_files(
        self, output_file: str, progress_callback: Callable[[str], None] | None = None
    ) -> bool:
        """Объединяет CSV файлы."""


@runtime_checkable
class ProgressReporterProtocol(Protocol):
    """Protocol для репортёра прогресса."""

    def update_progress(self, success: bool, filename: str) -> None:
        """Обновляет прогресс."""

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику."""


@runtime_checkable
class UrlGeneratorProtocol(Protocol):
    """Protocol для генератора URL."""

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """Генерирует все URL для парсинга."""


@runtime_checkable
class ThreadCoordinatorProtocol(Protocol):
    """Protocol для координатора потоков."""

    def run_parsing(
        self,
        all_urls: list[tuple[str, str, str]],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг."""

    def stop(self) -> None:
        """Останавливает парсинг."""

    @property
    def stats(self) -> dict[str, int]:
        """Возвращает статистику."""


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
    # Browser Protocols
    "BrowserNavigation",
    "BrowserContentAccess",
    "BrowserJSExecution",
    "BrowserScreenshot",
    "BrowserService",
    # Cache Protocols
    "CacheReader",
    "CacheWriter",
    "CacheBackend",
    # Backend Protocols
    "ExecutionBackend",
    # Parallel Parsing Protocols
    "ErrorHandlerProtocol",
    "MergerProtocol",
    "ProgressReporterProtocol",
    "UrlGeneratorProtocol",
    "ThreadCoordinatorProtocol",
]
